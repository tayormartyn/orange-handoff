"""Demo trade-MANAGEMENT transport tests — FAKE transport only. NO broker amend/close/cancel is ever
sent. ORDER_MANAGEMENT_ENABLED stays False; tests pass an explicit override to exercise the fake
accept/reject/timeout/mismatch/composite paths."""
from __future__ import annotations
import glob
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DE = os.path.join(_ROOT, "campaign_extractor", "demo_executor")
for p in (_ROOT, _DE):
    if p not in sys.path:
        sys.path.insert(0, p)

import config as CFG
import management_transport as MT
import management_adapter as MADP
import management_permit as MP
import position_provenance as PP
from models import AccountSnapshot, ApprovedManagementPlan

NOW = 1_800_000_000_000


def acct(**o):
    d = dict(account_id=4257941, is_live=False, balance=10000.0, currency="GBP", trade_scope="trade",
             environment="DEMO")
    d.update(o)
    return AccountSnapshot(**d)


def plan(action="MOVE_SL_BREAKEVEN", **o):
    d = dict(plan_id="mplan-1", action=action, signal_id="sig-1", proposal_id="prop-1",
             update_intake_id="upd-1", account_id=4257941, symbol_id=41, symbol_name="XAUUSD",
             direction="BUY", client_order_id="cli-abc", broker_position_id="POS-9", broker_order_id="ORD-9",
             label="ST-FAROUK", comment="signal=sig-1;proposal=prop-1;leg=1", broker_vwap=4117.0,
             current_stop=4110.0, new_stop_loss=4117.0, open_volume_raw=1200, close_volume_raw=300,
             close_volume_units=3, close_volume_lots=0.03, remaining_volume_raw=900, created_at_ms=NOW)
    d.update(o)
    return ApprovedManagementPlan(**d)


class FakeMgmt:
    def __init__(self, mode="ACCEPTED", returned=None, error_code="MARKET_CLOSED", mismatch=None,
                 reconcile_result=None):
        self.mode, self.returned, self.error_code = mode, returned, error_code
        self.mismatch, self.reconcile_result = mismatch, reconcile_result
        self.sends = []

    def send_management(self, fields):
        self.sends.append(fields)
        if self.mode == "TIMEOUT":
            return {"status": "TIMEOUT"}
        if self.mode == "REJECTED":
            return {"status": "REJECTED", "error_code": self.error_code}
        return {"status": "ACCEPTED", "broker_ref": "POS-9", "returned": self.returned}

    def reconcile(self, approved):
        return self.reconcile_result

    def reconcile_compare(self, approved, returned):
        return self.mismatch or []


def _send(p, ft, **over):
    kw = dict(transport=ft, account=acct(), endpoint_host="demo.ctraderapi.com", endpoint_port=5035,
              permission_scope="SCOPE_TRADE", position_match="VERIFIED", quote_fresh=True, update_fresh=True,
              plan_unexpired=True, replay_status="LIVE", operator_approval_completed=True, permit_valid=True,
              lease_valid=True, order_management_enabled=True, now_ms=NOW)
    kw.update(over)
    return MT.send_management(p, **kw)


def _blocked(r, ft):
    assert r["sent"] is False and r["protobuf_constructed"] is False
    assert r["final_state"] == "NO_BROKER_ACTION_SENT" and ft.sends == []


# ---- firewall blocks (one failure blocks, before any construction) ----
def test_management_gate_disabled_blocks_before_construction():
    ft = FakeMgmt()
    _blocked(_send(plan(), ft, order_management_enabled=False), ft)


def test_view_only_token_blocks():
    ft = FakeMgmt()
    _blocked(_send(plan(), ft, permission_scope="SCOPE_VIEW"), ft)


def test_wrong_account_live_and_live_endpoint_block():
    for over in ({"account": acct(account_id=9999)}, {"account": acct(is_live=True)},
                 {"endpoint_host": "live.ctraderapi.com"}, {"endpoint_port": 5036}):
        ft = FakeMgmt()
        _blocked(_send(plan(account_id=(9999 if "account" in over and over["account"].account_id == 9999 else 4257941)), ft, **over), ft)


def test_missing_permit_or_lease_blocks():
    ft = FakeMgmt(); _blocked(_send(plan(), ft, permit_valid=False), ft)
    ft2 = FakeMgmt(); _blocked(_send(plan(), ft2, lease_valid=False), ft2)


def test_ambiguous_or_no_position_match_blocks():
    ft = FakeMgmt(); _blocked(_send(plan(), ft, position_match="AMBIGUOUS"), ft)
    ft2 = FakeMgmt(); _blocked(_send(plan(), ft2, position_match="NO_MATCH"), ft2)


def test_replay_update_ineligible():
    ft = FakeMgmt()
    _blocked(_send(plan(), ft, replay_status="REPLAY_VALIDATION_ONLY"), ft)


def test_stale_quote_or_update_or_expired_plan_blocks():
    for over in ({"quote_fresh": False}, {"update_fresh": False}, {"plan_unexpired": False}):
        ft = FakeMgmt()
        _blocked(_send(plan(), ft, **over), ft)


def test_disable_file_blocks(tmp_path=None):
    import tempfile
    d = tempfile.mkdtemp()
    try:
        df = os.path.join(d, "DEMO_EXECUTION_DISABLED"); open(df, "w").write("x")
        ft = FakeMgmt()
        _blocked(_send(plan(), ft, disable_path=df), ft)
    finally:
        import shutil
        shutil.rmtree(d, ignore_errors=True)


# ---- fake transport accept / reject / timeout / mismatch ----
def test_amend_accepted_via_fake():
    ft = FakeMgmt(mode="ACCEPTED")
    r = _send(plan("MOVE_SL_BREAKEVEN"), ft)
    assert r["final_state"] == "MGMT_ACCEPTED" and len(ft.sends) == 1
    assert ft.sends[0]["_req"] == "ProtoOAAmendPositionSLTPReq" and ft.sends[0]["stopLoss"] == 4117.0


def test_close_rejected_via_fake():
    ft = FakeMgmt(mode="REJECTED", error_code="TRADING_DISABLED")
    r = _send(plan("PARTIAL_CLOSE"), ft)
    assert r["final_state"] == "MGMT_REJECTED" and r["error_code"] == "TRADING_DISABLED"
    assert ft.sends[0]["_req"] == "ProtoOAClosePositionReq" and ft.sends[0]["volume"] == 300


def test_timeout_reconciles_not_retry():
    ft = FakeMgmt(mode="TIMEOUT", reconcile_result={"position_id": "POS-9"})
    r = _send(plan("PARTIAL_CLOSE"), ft)
    assert r["final_state"] == "MGMT_RECONCILIATION_REQUIRED" and r["no_retry"] is True
    assert len(ft.sends) == 1


def test_state_mismatch_reported():
    ft = FakeMgmt(mode="ACCEPTED", mismatch=["stopLoss"])
    r = _send(plan("MOVE_SL_BREAKEVEN"), ft)
    assert r["final_state"] == "MGMT_STATE_MISMATCH" and r["manual_review_required"] is True


def test_cancel_serializes_order_id():
    ft = FakeMgmt(mode="ACCEPTED")
    r = _send(plan("CANCEL_PENDING"), ft)
    assert r["final_state"] == "MGMT_ACCEPTED" and ft.sends[0]["_req"] == "ProtoOACancelOrderReq"
    assert ft.sends[0]["orderId"] == "ORD-9"


# ---- composite stops on first failure ----
def test_composite_stops_on_first_failure():
    steps = (plan("MOVE_SL_BREAKEVEN", plan_id="s1"), plan("PARTIAL_CLOSE", plan_id="s2"))
    comp = plan("COMPOSITE", plan_id="comp", steps=steps)

    class SeqFake(FakeMgmt):
        def __init__(self):
            super().__init__(); self.n = 0
        def send_management(self, fields):
            self.sends.append(fields); self.n += 1
            return {"status": "ACCEPTED", "broker_ref": "POS-9"} if self.n == 1 else {"status": "REJECTED", "error_code": "X"}
    ft = SeqFake()
    r = _send(comp, ft)
    assert r["final_state"] == "MANAGEMENT_PLAN_PARTIAL_SUCCESS" and r["failed_step"] == 1
    assert r["new_approval_required"] is True and r["atomic"] is False


# ---- breakeven uses broker VWAP, not provider entry ----
def test_breakeven_uses_broker_vwap_not_provider_entry():
    import management_planner as PLAN
    class Pos:
        price = 4117.35        # broker VWAP (NOT Farouk's screenshot entry)
        direction = "BUY"
        position_id = "POS-9"
        stop_loss = 4110.0
    prop = PLAN.breakeven_proposal(Pos(), quote=type("Q", (), {"bid": 4120.0, "ask": 4120.2})(),
                                   symbol_digits=2, point=0.01, min_stop_distance_points=10)
    assert prop.detail["proposed_stop"] == 4117.35 and prop.detail["actual_vwap_entry"] == 4117.35
    assert "BREAKEVEN" in prop.detail["label"]


# ---- partial-close volume respects min/step; cannot exceed open; take-one-out not one lot ----
def test_partial_close_volume_min_step_and_bounds():
    ft = FakeMgmt()
    # close 300 raw of 1200 open -> remaining 900 (valid); serialized as 300
    r = _send(plan("PARTIAL_CLOSE", close_volume_raw=300, open_volume_raw=1200, remaining_volume_raw=900), ft)
    assert r["final_state"] == "MGMT_ACCEPTED" and ft.sends[0]["volume"] == 300


def test_take_one_out_is_not_silently_one_lot():
    import management_planner as PLAN
    class Pos:
        price = 4117.0
        direction = "BUY"
        volume_units = 12          # 0.12 lot open
        position_id = "POS-9"
        stop_loss = 4110.0
    q = type("Q", (), {"bid": 4120.0, "ask": 4120.2})()
    # "take one out" as a literal 1 lot (=100 units) != the 12-unit position -> NOT silently applied
    unmapped = PLAN.partial_close_proposal(Pos(), min_volume_units=1, step_volume_units=1, units_per_lot=100,
                                           quote=q, provider_literal_lots=1, provider_wording="take one out")
    assert unmapped.reason == "PROVIDER_LITERAL_UNMAPPED"
    # with no provider size, operator-policy choices are presented (operator must choose)
    choices = PLAN.partial_close_proposal(Pos(), min_volume_units=1, step_volume_units=1, units_per_lot=100,
                                          quote=q, requested_fraction=None)
    assert choices.reason == "CHOICES_PRESENTED"


# ---- position provenance: symbol-alone / ambiguous ----
def test_symbol_alone_position_match_blocked():
    p = plan(broker_position_id=None, broker_order_id=None, client_order_id=None,
             signal_id="sig-x", proposal_id="prop-x")
    cands = [{"position_id": "P1", "symbol": "XAUUSD", "direction": "BUY", "label": "", "comment": ""}]
    status, mid, method, ev = PP.match_target(p, cands)
    assert status == "NO_MATCH"                         # symbol+direction alone (no provenance) -> no match


def test_ambiguous_position_match_blocked():
    p = plan(broker_position_id="POS-9")
    cands = [{"position_id": "POS-9"}, {"position_id": "POS-9"}]   # two matches
    status, *_ = PP.match_target(p, cands)
    assert status == "AMBIGUOUS"


def test_verified_by_broker_id():
    status, mid, method, _ = PP.match_target(plan(broker_position_id="POS-9"),
                                             [{"position_id": "POS-9"}, {"position_id": "POS-2"}])
    assert status == "VERIFIED" and mid == "POS-9" and method == "BROKER_ID"


# ---- permit / lease + relock ----
def test_permit_lease_bound_and_relock():
    permit = MP.make_permit(account_id=4257941, parent_signal_id="sig-1", update_intake_id="upd-1",
                            management_plan_id="mplan-1", broker_ref="POS-9", now_ms=NOW)
    lease = MP.make_lease(permit=permit, now_ms=NOW)
    ledger = MP.UseLedger()
    for st in ("MGMT_ACCEPTED", "MGMT_REJECTED", "MGMT_RECONCILIATION_REQUIRED", "MGMT_STATE_MISMATCH",
               "MGMT_AUTHENTICATION_FAILURE"):
        led = MP.UseLedger()
        r = MP.execute_one_attempt(lease, send_fn=lambda order_management_enabled: {"final_state": st},
                                   ledger=led, now_ms=NOW)
        assert r["order_management_enabled_after"] is False and r["management_gate"] == "DISABLED"
        assert led.is_closed(lease.lease_id)
    # exception path relocks too
    led = MP.UseLedger()
    def boom(order_management_enabled):
        raise RuntimeError("x")
    r = MP.execute_one_attempt(lease, send_fn=boom, ledger=led, now_ms=NOW)
    assert r["final_state"] == "MGMT_NETWORK_EXCEPTION" and r["order_management_enabled_after"] is False
    # reuse blocked
    led2 = MP.UseLedger(); led2.use(lease.lease_id)
    r2 = MP.execute_one_attempt(lease, send_fn=lambda **k: {}, ledger=led2, now_ms=NOW)
    assert r2["attempted"] is False and r2["reason"] == "LEASE_ALREADY_CONSUMED"


def test_permit_expired_and_plan_mismatch():
    permit = MP.make_permit(account_id=4257941, parent_signal_id="sig-1", update_intake_id="upd-1",
                            management_plan_id="mplan-1", broker_ref="POS-9", now_ms=NOW)
    led = MP.UseLedger()
    ok, reason = MP.validate_permit(permit, account_id=4257941, parent_signal_id="sig-1",
                                    update_intake_id="upd-1", management_plan_id="OTHER", broker_ref="POS-9",
                                    now_ms=NOW, ledger=led)
    assert not ok and reason == "PLAN_MISMATCH"
    ok2, r2 = MP.validate_permit(permit, account_id=4257941, parent_signal_id="sig-1",
                                 update_intake_id="upd-1", management_plan_id="mplan-1", broker_ref="POS-9",
                                 now_ms=NOW + MP.PERMIT_TTL_MS + 5000, ledger=led)
    assert not ok2 and r2 == "PERMIT_EXPIRED"


# ---- safety ----
def test_no_market_entry_or_amend_order_constructor():
    for pth in glob.glob(os.path.join(_DE, "management_adapter.py")):
        src = open(pth, encoding="utf-8").read()
        for bad in ("ProtoOANewOrderReq", "ProtoOAAmendOrderReq", "ProtoOASubscribeSpots"):
            assert bad not in src
    # the three authorised management constructors are present
    src = open(os.path.join(_DE, "management_adapter.py"), encoding="utf-8").read()
    for good in ("ProtoOAAmendPositionSLTPReq", "ProtoOAClosePositionReq", "ProtoOACancelOrderReq"):
        assert good in src


def test_locks_independent_and_false():
    assert CFG.ORDER_SENDING_ENABLED is False and CFG.ORDER_MANAGEMENT_ENABLED is False
    cfg = open(os.path.join(_ROOT, "config.py"), encoding="utf-8").read()
    cc = open(os.path.join(_ROOT, "ctrader_config.py"), encoding="utf-8").read()
    de = open(os.path.join(_DE, "config.py"), encoding="utf-8").read()
    assert "EXECUTION_ENABLED = False" in cfg and "CTRADER_EXECUTION_ENABLED = False" in cc
    assert "ORDER_SENDING_ENABLED = False" in de and "ORDER_MANAGEMENT_ENABLED = False" in de
