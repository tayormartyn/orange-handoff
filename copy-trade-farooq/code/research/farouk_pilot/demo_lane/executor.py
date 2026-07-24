"""Demo executor (bounded build). Writes DEMO_APPROVAL_REQUEST; is TECHNICALLY INCAPABLE
of writing DEMO_APPROVED (F3). Enforces the ADDENDUM item-1 ordering:
  validate -> atomically create consumption receipt -> write durable outbox intent -> send.
Failed receipt persistence blocks the request. Uses a MOCK broker adapter only."""
import hashlib
import json
import os

from . import config, gate, sizing, prices
from .approval_tool import APPROVED_TYPE, PLAN_FIELDS, _plan_hash

REQUEST_TYPE = "DEMO_APPROVAL_REQUEST"


class ExecutorHalt(Exception):
    pass


class Executor:
    def __init__(self, requests_dir, approvals_dir, receipts_dir, outbox_dir, ledger_path, adapter):
        self.requests_dir = requests_dir
        self.approvals_dir = approvals_dir      # executor has NO write capability here (see guard)
        self.receipts_dir = receipts_dir
        self.outbox_dir = outbox_dir
        self.ledger_path = ledger_path
        self.adapter = adapter                  # MOCK adapter
        self.trace = []                         # ordered event trace (GAP 2: success-path ordering)
        self._alarms = []                       # §6a: raised alarms (unprotected-position prevention)
        self._reconcile_only = False            # §6a: set when cancellation outcome is UNKNOWN
        for d in (requests_dir, receipts_dir, outbox_dir):
            os.makedirs(d, exist_ok=True)

    # ---- F3: the executor can request, and is architecturally unable to approve ----
    def write_approval_request(self, plan):
        rec = {"record_type": REQUEST_TYPE, **{k: plan[k] for k in PLAN_FIELDS}}
        p = os.path.join(self.requests_dir, f"{plan['campaign_id']}.request.json")
        with open(p, "w", encoding="utf-8") as f:
            json.dump(rec, f)
        return p

    def _refuse_approval_capability(self, *a, **k):
        # There is NO method on the executor that writes DEMO_APPROVED. This guard exists so
        # that any accidental call path raises rather than writes. In deploy, the executor's
        # OS account also lacks write ACL on approvals_dir (defence in depth).
        raise PermissionError("executor is technically incapable of writing DEMO_APPROVED (F3)")

    write_approval = _refuse_approval_capability

    # ---- validation ----
    def _validate_approval(self, approval, now_ts):
        if approval.get("record_type") != APPROVED_TYPE:
            raise ExecutorHalt("not a DEMO_APPROVED record")
        if approval.get("lifecycle") != "MARTYN_APPROVED":
            raise ExecutorHalt(f"approval lifecycle {approval.get('lifecycle')} not MARTYN_APPROVED")
        plan = approval["plan"]
        if _plan_hash(plan) != approval["plan_hash"]:
            raise ExecutorHalt("plan_hash mismatch — approval modified")
        recomputed = hashlib.sha256(json.dumps(
            {k: approval[k] for k in approval if k != "approval_record_hash"},
            sort_keys=True, default=str).encode()).hexdigest()
        if recomputed != approval["approval_record_hash"]:
            raise ExecutorHalt("approval_record_hash mismatch — approval tampered")
        if now_ts > approval["expiry_ts"]:
            raise ExecutorHalt("approval expired")
        return plan

    # ---- ADDENDUM item 1: atomic single-winner consumption receipt ----
    def _consume(self, approval):
        path = os.path.join(self.receipts_dir, f"{approval['nonce']}.receipt")
        try:
            fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)   # single winner
        except FileExistsError:
            raise ExecutorHalt("approval already consumed (replay/duplicate)")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(json.dumps({"nonce": approval["nonce"], "by": config.EXECUTOR_VERSION}))
        return path

    # ---- outbox (correction 7) ----
    def _write_intent(self, approval, leg):
        path = os.path.join(self.outbox_dir, f"{approval['nonce']}.leg{leg}.intent.json")
        rec = {"state": "INTENT_WRITTEN", "nonce": approval["nonce"], "leg": leg}
        with open(path, "w", encoding="utf-8") as f:
            json.dump(rec, f)
        return path

    def _set_state(self, path, state, extra=None):
        rec = json.load(open(path, encoding="utf-8"))
        rec["state"] = state
        if extra:
            rec.update(extra)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(rec, f)

    # ---- place one campaign (LIMIT-only opening, protection + GTD in the initial request) ----
    def place_campaign(self, approval, now_ts, account):
        if not gate.can_arm(account):
            raise ExecutorHalt("NOT_ARMED — gate/account guard refused")
        plan = self._validate_approval(approval, now_ts)
        self.trace.append("VALIDATE_IMMUTABLE_APPROVAL")
        caps = config.SAFETY_CAPS
        if plan["symbol_id"] != caps["instrument"]:
            raise ExecutorHalt("instrument not XAUUSD")
        if len(plan["entries"]) > caps["max_entry_orders"]:
            raise ExecutorHalt("more than max_entry_orders")
        # symbol / trading-session validity (addendum 3) — block placement if closed/untradeable
        meta0 = self.adapter.symbol_meta(plan["symbol_id"])
        if not meta0.get("tradeable", True):
            raise ExecutorHalt("symbol not tradeable — placement blocked")
        if not meta0.get("session_open", True):
            raise ExecutorHalt("trading session closed — placement blocked")

        # ORDERING (addendum 1): validate DONE -> receipt -> intent -> send
        try:
            self._consume(approval)                          # atomic; failure blocks the request
            self.trace.append("PERSIST_ATOMIC_CONSUMPTION_RECEIPT")
        except ExecutorHalt:
            raise
        except OSError as e:
            raise ExecutorHalt(f"receipt persistence failed -> request BLOCKED ({e})")

        meta = self.adapter.symbol_meta(plan["symbol_id"])
        results = []
        for i, entry in enumerate(plan["entries"]):
            vol = sizing.to_protocol_volume(plan["volume_per_leg"], meta)   # F1 exact-or-halt
            # price representability + min-stop-distance (addendum 3) — reject, never normalize
            prices.representable(entry, meta["tickSize"])
            prices.representable(plan["stop"], meta["tickSize"])
            prices.stop_distance_ok(entry, plan["stop"], plan["direction"], meta["minStopDistance"])
            intent = self._write_intent(approval, i)
            self.trace.append("PERSIST_DURABLE_ORDER_INTENT")
            req = {"account_id": plan["approved_account_id"],   # GAP 1: account_id is a reconciled field
                   "symbol": plan["symbol_id"], "side": plan["direction"], "type": "LIMIT",
                   "volume": vol, "entry_price": entry, "stop_price": plan["stop"],
                   "expiry_ts": plan["approval_expiry"], "time_in_force": "GOOD_TILL_DATE"}  # addendum 2
            self._set_state(intent, "SENT")
            ack = self.adapter.place_limit(req)              # MOCK
            self.trace.append("CALL_BROKER_ADAPTER")
            if ack is None:                                  # lost response (correction 7)
                self._set_state(intent, "OUTCOME_UNKNOWN")
                raise ExecutorHalt("OUTCOME_UNKNOWN — reconcile before any retry")
            # GAP 1: account_id checked FIRST and separately — a mismatch means the order landed on a
            # DIFFERENT account: detect, halt/NOT_ARMED, no silent adoption, no subsequent broker action.
            if ack.get("account_id") != req.get("account_id"):
                self._armed = False
                self._set_state(intent, "ACKED", {"reconcile": "ACCOUNT_ID_MISMATCH"})
                raise ExecutorHalt("ACCOUNT_ID_MISMATCH — order on a different account; NOT_ARMED, halt, no subsequent action")
            # §6a UNPROTECTED-POSITION PREVENTION (single-source orchestration here): if the broker
            # did not attach/verify the protective stop, actively UNWIND (close filled + cancel entry)
            # and halt — never leave an unprotected position. Runs BEFORE the generic reconcile
            # because stop-omission is a specific, known-dangerous case needing an active unwind.
            self._verify_protection_or_unwind(ack, intent)
            # addendum 3: exact-equality reconciliation on the remaining SEVEN fields (type retained as 8th)
            seven = ("symbol", "side", "type", "volume", "entry_price", "stop_price", "expiry_ts")
            if any(ack.get(k) != req.get(k) for k in seven):
                self._set_state(intent, "ACKED", {"reconcile": "SILENT_NORMALIZATION"})
                raise ExecutorHalt("silent normalization detected — cancel/close owned + halt")
            self._set_state(intent, "ACKED", {"broker_order_id": ack["order_id"]})
            self._ledger({"record_type": "DEMO_ORDER_PLACED", "leg": i, "order_id": ack["order_id"]})
            results.append(ack)
        return results

    def _ledger(self, rec):
        rec = {**rec, **config.LEDGER_ELIGIBILITY, "review_only": True, "observation_only": True}
        with open(self.ledger_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec) + "\n")

    def _alarm(self, code, extra=None):
        """Raise a durable alarm (§6a). Recorded in-memory and appended to the ledger."""
        rec = {"alarm": code, **(extra or {})}
        self._alarms.append(rec)
        try:
            self._ledger({"record_type": "DEMO_ALARM", **rec})
        except OSError:
            pass
        return rec

    # ---- §6a: NEVER leave an unprotected position (Chuck bounded-fix 1: fixed ordering) --------
    def _verify_protection_or_unwind(self, ack, intent_path):
        """If the protective stop is attached/verified, return (protected). Otherwise EMERGENCY
        UNWIND in EXACTLY this order - address the PENDING entry BEFORE the filled quantity:
          CANCEL_REMAINING_ENTRY -> CONFIRM_CANCELLATION -> CLOSE_CURRENT_FILLED_QUANTITY
          -> VERIFY_ZERO_PENDING_AND_POSITION -> ALARM -> HALT.
        A full fill with NO remainder has nothing to cancel and follows the close-only branch.
        If the cancellation outcome is UNKNOWN, do NOT claim containment: enter OUTCOME_UNKNOWN /
        RECONCILE_ONLY, make NO close and NO new placement, and reconcile broker state first.
        Legacy acks without 'stop_attached' are treated as protected (no behaviour change)."""
        if ack.get("stop_attached", True):
            return
        oid = ack.get("order_id")
        filled = int(ack.get("filled_volume", 0) or 0)
        pending = int(ack.get("pending_volume", 0) or 0)
        pid = ack.get("position_id")

        # STEP 1+2: PENDING entry FIRST — cancel, then confirm. (Skip only when nothing is pending.)
        if pending > 0 or filled == 0:
            self.trace.append("CANCEL_REMAINING_ENTRY")
            cancel_res = self.adapter.cancel_order(oid) if oid is not None else {"cancelled": True}
            if self._cancellation_confirmed(oid, cancel_res) is not True:
                # UNKNOWN cancellation -> NO containment claim, NO close, NO new placement.
                self._reconcile_only = True
                self._set_state(intent_path, "OUTCOME_UNKNOWN",
                                {"phase": "CANCEL_OUTCOME_UNKNOWN", "reconcile_only": True})
                self._alarm("CANCELLATION_OUTCOME_UNKNOWN_RECONCILE_ONLY", {"order_id": oid})
                raise ExecutorHalt("CANCELLATION_OUTCOME_UNKNOWN — RECONCILE_ONLY: reconcile broker "
                                   "state before any containment; no close, no new placement")
            self.trace.append("CONFIRM_CANCELLATION")

        # STEP 3: CLOSE the current filled quantity — ONLY after the pending entry is addressed.
        if filled > 0 and pid is not None and hasattr(self.adapter, "close_reduce"):
            self.adapter.close_reduce(pid, filled, owner_check="ORANGE")
            self.trace.append("CLOSE_CURRENT_FILLED_QUANTITY")

        # STEP 4: VERIFY zero pending AND zero position (fail closed if either remains).
        self._verify_zero_pending_and_position(oid, pid)
        self.trace.append("VERIFY_ZERO_PENDING_AND_POSITION")

        # STEP 5 + 6: ALARM then HALT.
        self._alarm("UNPROTECTED_POSITION_PREVENTED", {"order_id": oid, "closed_volume": filled})
        self._set_state(intent_path, "CONTAINED",
                        {"reason": "UNPROTECTED_STOP_NOT_ATTACHED", "closed_volume": filled})
        raise ExecutorHalt("UNPROTECTED_POSITION_PREVENTED — pending cancelled+confirmed, filled qty "
                           "closed, zero pending+position, halt")

    def _cancellation_confirmed(self, oid, cancel_res):
        """True only when the cancellation is confirmed. None (UNKNOWN) if the channel reported an
        ambiguous outcome OR the order is still present in the broker's open orders."""
        if isinstance(cancel_res, dict) and cancel_res.get("cancelled") is None:
            return None
        if oid is not None and hasattr(self.adapter, "list_orders") and oid in self.adapter.list_orders():
            return None
        return True

    def _verify_zero_pending_and_position(self, oid, pid):
        orders = self.adapter.list_orders() if hasattr(self.adapter, "list_orders") else {}
        o = orders.get(oid)
        if o is not None:
            pend = o.get("pending_volume")
            if pend is None:
                pend = (o.get("volume", 0) or 0) - (o.get("filled_volume", 0) or 0)
            if pend and pend > 0:
                raise ExecutorHalt("containment verification failed — pending remainder present")
        if pid is not None and hasattr(self.adapter, "list_positions"):
            pos = self.adapter.list_positions().get(pid)
            if pos is not None and pos.get("volume", 0) > 0:
                raise ExecutorHalt("containment verification failed — position still open")

    # ---- restart: reconcile BEFORE any action; NOT_ARMED until done (correction 13 #11) ----
    def restart_reconcile_first(self, account, owned_order_ids):
        """On restart the executor is NOT_ARMED and performs reconciliation before any placement.
        Returns True only if reconciliation completed and state is safe."""
        self._armed = False
        broker_orders = set(self.adapter.list_orders().keys())
        unknown = broker_orders - set(owned_order_ids)
        if unknown:
            raise ExecutorHalt(f"restart: unknown broker order(s) {sorted(unknown)} — NO TOUCH, NOT_ARMED")
        self._reconciled = True
        # arming still requires the normal gate/guard afterwards
        return gate.can_arm(account)

    # ---- stale / expired pending-order cancellation (correction 13 #13, addendum 2) ----
    def cancel_stale_orders(self, now_ts):
        cancelled = []
        for oid in self.adapter.orders_past_expiry(now_ts):
            self.adapter.cancel_order(oid)
            cancelled.append(oid)
            self._ledger({"record_type": "DEMO_STALE_ORDER_CANCELLED", "order_id": oid})
        return cancelled

    def cancel_campaign_pending(self, nonce):
        """Terminal campaign state cancels its pending entries (correction 13 #13)."""
        cancelled = []
        for oid, o in list(self.adapter.list_orders().items()):
            self.adapter.cancel_order(oid); cancelled.append(oid)
        return cancelled
