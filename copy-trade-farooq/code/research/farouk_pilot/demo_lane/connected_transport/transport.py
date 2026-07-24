"""ConnectedTransport — the connected cTrader-DEMO transport (OFFLINE build).

It SENDS approved requests and RETURNS broker facts. It does NOT reinterpret them: no sizing, no
price validation, no approval, no gate authority of its own, no reconciliation equality check, no
campaign interpretation — those single sources live in demo_lane (executor/sizing/prices/approval/
reconcile/gate) and in the follower interpreter. This layer owns ONLY wire mechanics.

Guarantees enforced here:
  * production composition is NOT_ARMED while the authoritative gates are False; test-enable binds
    to a fake/loopback connector only. No CLI/env/caller override of destination or arming.
  * ONLY the permitted request families are emittable (no generic console, no raw send).
  * deterministic correlation; duplicate/in-flight keys refused (no blind resend).
  * SEND CLASSIFICATION (Chuck gap correction 1): DEFINITELY_NOT_SENT is allowed ONLY when the
    failure provably occurs BEFORE the first attempt to transmit bytes (state/gate refusal,
    encoding/framing failure, connector not connected before send starts) — only that path may
    release the correlation. ANY error raised once connector.send begins is AMBIGUOUS (sendall
    proves nothing about bytes on the wire): the correlation is RETAINED and marked
    OUTCOME_UNKNOWN, there is NO automatic retry, READY is invalidated, the transport disconnects,
    and after reconnect it is RECONCILE_ONLY until reconciliation proves broker state.
  * ONE ALWAYS-ON I/O OWNER (Chuck gap correction 2): a single transport-owned reader thread is
    the only caller of connector.recv — it deframes everything inbound, routes matched responses
    by clientMsgId to waiting callers, and consumes async fills/events even when no request is
    awaiting. A single sender thread drains ONE outbound queue (all requests) and emits heartbeats
    automatically when the link idles past HEARTBEAT_INTERVAL_S. Request callers submit work and
    wait on a response future; they never touch the socket.
  * unknown order/position -> no-touch; known-owned-but-mismatch -> ratified containment (no
    destructive action); unknown inbound event -> fail-closed. Every alarm/log is sanitised.
  * broker identity: the account guard proves endpoint/ID/isLive/scope OFFLINE; the Pepperstone
    account binding itself is PENDING_READ_ONLY_PREFLIGHT (tc.BROKER_IDENTITY_CLAIMS) — a config
    value compared with itself is NOT broker attestation.
"""
import queue
import threading
import time

from . import credentials as cred
from . import egress_guard
from . import framing
from . import state as st
from . import transport_config as tc
from .framing import MsgType

# transport MAY import the approved mapper (executor may NOT import either transport or mapper).
from .. import protobuf_mapper
# gate + account allowlist are the SINGLE SOURCE (demo_lane) — reused, never redefined here.
from .. import config as demo_config
from .. import gate as demo_gate


class NotArmed(Exception):
    """The transport refused to connect/auth/act because gates are False (or a test policy was
    pointed at a non-mock connector)."""


class TransportPolicy:
    """Mirrors demo_lane.order_adapter.DispatchPolicy: constructed only via the two factories below,
    never with a caller-supplied armed flag on the production path."""
    def __init__(self, armed, requires_mock):
        self.armed = bool(armed)
        self.requires_mock = bool(requires_mock)


def production_policy():
    """AUTHORITATIVE gates ONLY (single source). All three hard False -> armed False -> NOT_ARMED."""
    return TransportPolicy(armed=tc.production_armed(), requires_mock=False)


def test_only_policy():
    """Test seam: armed, but BOUND to a fake/loopback (IS_MOCK) connector — it can never drive a
    real socket to a real endpoint."""
    return TransportPolicy(armed=True, requires_mock=True)


class Result:
    OK = "OK"
    REJECTED = "REJECTED"
    DEFINITELY_NOT_SENT = "DEFINITELY_NOT_SENT"   # provably zero bytes attempted (pre-transmit)
    OUTCOME_UNKNOWN = "OUTCOME_UNKNOWN"           # ambiguous: bytes may or may not have left
    NO_TOUCH = "NO_TOUCH"
    CONTAINED = "CONTAINED"


class _Pending:
    """A caller's wait slot: the reader/sender threads resolve it; the caller waits on the event."""
    __slots__ = ("event", "kind", "value")

    def __init__(self):
        self.event = threading.Event()
        self.kind = None       # "RESPONSE" | Result.OUTCOME_UNKNOWN | Result.DEFINITELY_NOT_SENT
        self.value = None      # Envelope for RESPONSE; reason string otherwise

    def resolve(self, kind, value):
        self.kind = kind
        self.value = value
        self.event.set()


class ConnectedTransport:
    def __init__(self, *, connector, codec, credential_provider, policy=None, clock=None):
        self.connector = connector
        self.codec = codec
        self.credentials = credential_provider
        self.policy = policy or production_policy()
        self.now = clock or time.monotonic
        self.cstate = st.ConnectionState()
        self.corr = st.CorrelationRegistry()
        self.deframer = framing.Deframer()
        self.alarms = []
        self.last_inbound_t = 0.0
        self.last_outbound_t = 0.0
        self.response_timeout_s = tc.RESPONSE_TIMEOUT_S   # injectable for tests (wall-clock wait)
        self._session_seq = 0
        self._hb_seq = 0
        self._known_orders = {}
        self._known_positions = {}
        # ---- the single I/O owner ----
        self._send_lock = threading.Lock()    # serialises the physical write (sender + manual hb)
        self._writes = 0
        self._out_q = queue.Queue()           # the ONE outbound queue (all requests)
        self._pending = {}                    # cmid -> _Pending
        self._pending_lock = threading.Lock()
        self._io_generation = 0               # bumped per (re)connect; stale loops exit
        self._io_running = False
        self._sender_ident = None             # thread id of the ONE thread allowed to write

    # ---- arming ---------------------------------------------------------------------------------
    def _assert_armed(self):
        if not self.policy.armed:
            raise NotArmed("NOT_ARMED — authoritative gates False; transport will not connect/auth/send")
        if self.policy.requires_mock and not getattr(self.connector, "IS_MOCK", False):
            raise NotArmed("test-only policy cannot drive a non-mock/non-loopback connector")

    def _alarm(self, kind, detail):
        self.alarms.append({"kind": kind, "detail": cred.sanitise(detail)})

    def _write(self, frame):
        """The SINGLE physical write — callable ONLY from the sender thread (strict single outbound
        owner). Any other thread (including the manual heartbeat seam and every request caller) must
        go through the outbound queue; a direct call from elsewhere fails closed."""
        if self._sender_ident is not None and threading.get_ident() != self._sender_ident:
            raise st.StateError("outbound write refused: only the sender thread may touch the socket "
                                "(submit to the outbound queue instead)")
        with self._send_lock:
            self.connector.send(frame)
            self._writes += 1

    def _connector_connected(self):
        return bool(getattr(self.connector, "connected", True))

    # ---- I/O loops (the one socket owner) -------------------------------------------------------
    def _start_io(self):
        self._io_generation += 1
        self._io_running = True
        self._out_q = queue.Queue()           # a fresh queue per session; stale frames never resent
        gen = self._io_generation
        threading.Thread(target=self._reader_loop, args=(gen,), daemon=True,
                         name=f"orange-transport-reader-{gen}").start()
        threading.Thread(target=self._sender_loop, args=(gen,), daemon=True,
                         name=f"orange-transport-sender-{gen}").start()

    def _stop_io(self):
        self._io_running = False              # loops exit on their next poll; daemon threads

    def _io_alive(self, gen):
        return self._io_running and gen == self._io_generation

    def _take_pending(self, cmid):
        with self._pending_lock:
            return self._pending.pop(cmid, None)

    def _reader_loop(self, gen):
        """The ONLY caller of connector.recv. Deframes all inbound (combined + fragmented), routes
        matched responses by clientMsgId, consumes async events even when nothing is awaiting."""
        while self._io_alive(gen):
            try:
                chunk = self.connector.recv(tc.READER_POLL_S)
            except BaseException as e:                       # noqa: BLE001 — socket died
                if self._io_alive(gen):
                    self._alarm("RECV_ERROR", {"why": str(e)})
                    self.on_disconnect()
                return
            if not chunk:
                time.sleep(0.005)                            # in-memory fakes return None instantly
                continue
            self.last_inbound_t = self.now()
            try:
                payloads = self.deframer.feed(chunk)
            except framing.FramingError as e:                # oversized/poisoned stream: fail-closed
                self._alarm("FRAMING_FAIL_CLOSED", {"why": str(e)})
                if self._io_alive(gen):
                    self.on_disconnect()
                return
            for payload in payloads:
                try:
                    env = self.codec.decode(payload)
                except framing.FramingError as e:
                    self._alarm("DECODE_FAIL_CLOSED", {"why": str(e)})
                    continue
                self._route(env)

    def _route(self, env):
        if env.msg_type not in framing.KNOWN_INBOUND:
            self._handle_unknown(env)
            return
        if env.msg_type == MsgType.HEARTBEAT:
            return                                           # in-stream heartbeat: skip
        if env.msg_type == MsgType.EXECUTION_EVENT:
            self._handle_event(env)                          # async even when no request waits
            return
        p = self._take_pending(env.client_msg_id) if env.client_msg_id else None
        if p is not None:
            p.resolve("RESPONSE", env)
        else:
            self._handle_event(env)                          # unmatched broker fact: record it

    def _sender_loop(self, gen):
        """Drains the ONE outbound queue — the ONLY thread that ever calls _write/connector.send.
        Heartbeats (automatic and manual) travel the same queue as requests. Send-phase exceptions
        are AMBIGUOUS by definition — classified here, never as clean failures."""
        self._sender_ident = threading.get_ident()           # arm the strict-owner guard
        while self._io_alive(gen):
            try:
                wire, cmid = self._out_q.get(timeout=tc.SENDER_POLL_S)
            except queue.Empty:
                self._auto_heartbeat()
                continue
            if not self._io_alive(gen):
                return                                       # on_disconnect already woke callers
            if cmid is None:                                 # queued heartbeat (no correlation)
                if not self._connector_connected():
                    continue                                 # never heartbeat a dead socket
                try:
                    self._write(wire)
                    self.last_outbound_t = self.now()
                except BaseException as e:                   # noqa: BLE001 — hb send died: link down
                    if self._io_alive(gen):
                        self._alarm("HEARTBEAT_SEND_FAILED", {"why": str(e)})
                        self.on_disconnect()
                continue
            if not self._connector_connected():
                self._resolve_not_sent(cmid, "connector not connected before transmit began")
                continue
            try:
                self._write(wire)                            # transmit begins HERE
            except BaseException as e:                       # noqa: BLE001 — AMBIGUOUS from now on
                self._ambiguous_send(cmid, e)
                continue
            self.last_outbound_t = self.now()

    def _auto_heartbeat(self):
        """Sender-owned idle heartbeat: enqueued (not written inline) so EVERY outbound operation
        passes through the single queue."""
        if not self.cstate.can_send(MsgType.HEARTBEAT):
            return
        if (self.now() - self.last_outbound_t) < tc.HEARTBEAT_INTERVAL_S:
            return
        self._enqueue_heartbeat()

    def _resolve_not_sent(self, cmid, why):
        """PRE-TRANSMIT failure: provably zero bytes attempted -> the ONLY path that releases the
        correlation (a deliberate re-issue is then permitted)."""
        try:
            self.corr.forget(cmid)
        except st.StateError:
            pass                                             # already resolved elsewhere
        self._alarm("DEFINITELY_NOT_SENT", {"client_msg_id": cmid, "why": why})
        p = self._take_pending(cmid)
        if p is not None:
            p.resolve(Result.DEFINITELY_NOT_SENT, why)

    def _ambiguous_send(self, cmid, exc):
        """Error during/after connector.send: bytes MAY have left. Retain the correlation, mark
        OUTCOME_UNKNOWN, no retry, invalidate READY (disconnect); reconcile-first after reconnect."""
        self.corr.mark_unknown(cmid)
        self._alarm("OUTCOME_UNKNOWN_AMBIGUOUS_SEND", {"client_msg_id": cmid, "why": str(exc)})
        p = self._take_pending(cmid)
        if p is not None:
            p.resolve(Result.OUTCOME_UNKNOWN, f"ambiguous send: {exc}")
        self.on_disconnect()

    # ---- lifecycle ------------------------------------------------------------------------------
    def open(self):
        self._assert_armed()
        self.connector.connect()
        self._session_seq += 1
        self.deframer = framing.Deframer()
        self.cstate.on_connected()
        self.last_inbound_t = self.last_outbound_t = self.now()
        self._start_io()

    def authenticate(self):
        """CONNECTED -> APPLICATION_AUTHENTICATED -> ACCOUNT_LIST_RECEIVED -> ACCOUNT_VALIDATED
        -> ACCOUNT_AUTHENTICATED. ProtoOAAccountAuthReq is NOT sent until the account-list response
        passes the single-source allowlist guard."""
        self._assert_armed()
        cid, _secret = self.credentials.app_credentials()
        r1 = self._request(MsgType.APP_AUTH_REQ, {"client_id": cid, "client_secret": _secret},
                           key=("app_auth", self._session_seq))
        if r1["status"] != Result.OK:
            self._alarm("APP_AUTH_FAILED", {"result": r1["status"]})
            raise NotArmed(f"application auth did not complete ({r1['status']})")
        self.cstate.on_app_authed()

        # account LIST (ProtoOAGetAccountListByAccessTokenReq) BEFORE any account auth
        r2 = self._request(MsgType.ACCOUNT_LIST_REQ,
                           {"access_token": self.credentials.account_access_token()},
                           key=("account_list", self._session_seq))
        if r2["status"] != Result.OK:
            self._alarm("ACCOUNT_LIST_FAILED", {"result": r2["status"]})
            raise NotArmed(f"account list did not complete ({r2['status']})")
        self.cstate.on_account_list()

        # ACCOUNT GUARD — must prove exactly one allowlisted, demo, correct-scope, correct-ID account
        self._validate_account_list(r2["payload"].get("accounts", []),
                                    r2["payload"].get("permissionScope"))
        self.cstate.on_account_validated()

        # ONLY NOW send ProtoOAAccountAuthReq
        r3 = self._request(MsgType.ACCOUNT_AUTH_REQ,
                           {"access_token": self.credentials.account_access_token(),
                            "ctid": self.credentials.ctid_trader_account_id()},
                           key=("account_auth", self._session_seq))
        if r3["status"] != Result.OK:
            self._alarm("ACCOUNT_AUTH_FAILED", {"result": r3["status"]})
            raise NotArmed(f"account auth did not complete ({r3['status']})")
        self.cstate.on_account_authed()

    def _validate_account_list(self, accounts, scope):
        """The account allowlist guard. Rejects (sanitised alarm + NotArmed, so NO account-auth, NO
        reconcile, NO trading request) on: missing / additional / live / wrong-ID / wrong-scope /
        wrong-broker. The five-field conjunction itself is the SINGLE SOURCE demo_lane.gate.

        CLAIM SCOPE (Chuck gap correction 3): endpoint + broker_environment here come from LOCAL
        CONFIG (the fixed connection context), so this guard proves the allowlist conjunction
        OFFLINE — it is NOT broker attestation of Pepperstone identity. That binding is
        PENDING_READ_ONLY_PREFLIGHT (tc.BROKER_IDENTITY_CLAIMS); the future connected composition
        must validate the immutable preflight binding via tc.validate_preflight_binding()."""
        if len(accounts) != 1:
            self._alarm("ACCOUNT_GUARD_REJECT",
                        {"why": "account list must contain EXACTLY the one allowlisted account",
                         "count": len(accounts)})
            raise NotArmed(f"account allowlist: expected exactly 1 account, saw {len(accounts)}")
        a = accounts[0]
        # endpoint + broker_environment come from the FIXED connection context (demo endpoint);
        # isLive + id from the account; scope from the response. Fed to the single-source guard.
        acc = {"endpoint": tc.DEMO_HOST, "isLive": a.get("isLive"),
               "ctidTraderAccountId": a.get("ctidTraderAccountId"),
               "broker_environment": demo_config.EXPECTED_BROKER_ENVIRONMENT,
               "permissionScope": scope}
        if a.get("ctidTraderAccountId") != demo_config.ALLOWED_CTID_TRADER_ACCOUNT_ID:
            self._alarm("ACCOUNT_GUARD_REJECT",
                        {"why": "account id not the allowlisted id",
                         "seen_id": a.get("ctidTraderAccountId")})
            raise NotArmed("account allowlist: wrong account id")
        if not demo_gate.account_guard_ok(acc):
            self._alarm("ACCOUNT_GUARD_REJECT",
                        {"why": "five-field account guard failed (isLive/scope/id/endpoint/broker)",
                         "isLive": a.get("isLive"), "scope": scope})
            raise NotArmed("account allowlist: guard rejected (live/wrong-scope/wrong-broker)")

    def reconcile(self):
        """RECONCILE-first: ACCOUNT_AUTHENTICATED -> RECONCILE_ONLY -> READY. Fetch Orange-owned
        pending orders + positions and record them. Actions are refused until READY."""
        self.cstate.on_reconcile_start()                     # enter the RECONCILE_ONLY window
        r = self._request(MsgType.RECONCILE_REQ,
                          {"ctid": self.credentials.ctid_trader_account_id()},
                          key=("reconcile", self._session_seq))
        if r["status"] != Result.OK:
            self._alarm("RECONCILE_FAILED", {"result": r["status"]})
            return r
        self._known_orders = dict(r["payload"].get("orders", {}))
        self._known_positions = dict(r["payload"].get("positions", {}))
        self.cstate.on_reconciled()
        return r

    def bring_up(self):
        """Full, ordered start: connect -> auth -> reconcile -> READY."""
        self.open()
        self.authenticate()
        self.reconcile()
        return self.cstate.state

    def close(self):
        self._stop_io()
        self._wake_all_pending("closed while awaiting")
        try:
            self.connector.close()
        finally:
            self.cstate.on_closed()

    # ---- reconnect (bounded backoff; reconcile-before-action enforced by re-running bring_up) ----
    def _wake_all_pending(self, why):
        with self._pending_lock:
            pend = list(self._pending.items())
            self._pending.clear()
        for cmid, p in pend:
            self.corr.mark_unknown(cmid)                     # retained, never forgotten
            p.resolve(Result.OUTCOME_UNKNOWN, why)

    def on_disconnect(self):
        self._stop_io()
        self._wake_all_pending("disconnected while awaiting response")
        self.cstate.on_disconnected()
        self._alarm("DISCONNECTED", {"session": self._session_seq})

    def reconnect(self, sleep=None):
        sleep = sleep or (lambda s: None)                    # injected; tests pass a no-op
        self.on_disconnect()
        for attempt in range(tc.RECONNECT_MAX_ATTEMPTS):
            sleep(tc.backoff_for(attempt))
            try:
                self.connector.close()
            except Exception:                                # noqa: BLE001
                pass
            try:
                if self.bring_up() == st.AuthState.READY:    # a timed-out reconcile is NOT success
                    return True
                self._alarm("RECONNECT_ATTEMPT_FAILED",
                            {"attempt": attempt, "why": f"bring_up ended in {self.cstate.state}"})
            except (NotArmed, st.StateError, ConnectionError, OSError) as e:
                self._alarm("RECONNECT_ATTEMPT_FAILED", {"attempt": attempt, "why": str(e)})
        self._alarm("RECONNECT_EXHAUSTED", {"attempts": tc.RECONNECT_MAX_ATTEMPTS})
        return False

    # ---- heartbeat ------------------------------------------------------------------------------
    def maybe_heartbeat(self):
        """Manual seam: SUBMITS a heartbeat to the outbound queue if the link is idle — it never
        writes to the socket itself (the sender thread is the only writer)."""
        if not self.cstate.can_send(MsgType.HEARTBEAT):
            return False
        if (self.now() - self.last_outbound_t) < tc.HEARTBEAT_INTERVAL_S:
            return False
        self._enqueue_heartbeat()
        return True

    def _enqueue_heartbeat(self):
        """Build + ENQUEUE a heartbeat frame. The sender thread performs the actual write."""
        self.cstate.assert_can_send(MsgType.HEARTBEAT)
        env = framing.Envelope(MsgType.HEARTBEAT, f"HB-{self._hb_seq}", {})
        self._hb_seq += 1
        self._out_q.put((framing.frame(self.codec.encode(env)), None))

    def is_stale(self):
        """No inbound traffic for HEARTBEAT_TIMEOUT_S -> the link is stale and must be dropped."""
        return (self.now() - self.last_inbound_t) >= tc.HEARTBEAT_TIMEOUT_S

    # ---- request/response core (submit to the queue; wait on the future) ------------------------
    def _request(self, msg_type, payload, key):
        self.cstate.assert_can_send(msg_type)                # ordering / raw-send guard
        if msg_type in framing.ACTION_OUTBOUND:
            self._assert_armed()                             # defence-in-depth on every action
        cmid = self.corr.register(key)                       # duplicate/in-flight -> StateError
        # ---- pre-transmit phase: any failure here is DEFINITELY_NOT_SENT (corr released) ----
        try:
            wire = framing.frame(self.codec.encode(framing.Envelope(msg_type, cmid, payload)))
        except Exception as e:                               # noqa: BLE001 — encode/frame failure
            self.corr.forget(cmid)
            self._alarm("DEFINITELY_NOT_SENT", {"msg_type": msg_type, "why": f"encode/frame: {e}"})
            return {"status": Result.DEFINITELY_NOT_SENT, "client_msg_id": cmid, "delivered": False}
        if not self._connector_connected():
            self.corr.forget(cmid)
            self._alarm("DEFINITELY_NOT_SENT",
                        {"msg_type": msg_type, "why": "not connected before send started"})
            return {"status": Result.DEFINITELY_NOT_SENT, "client_msg_id": cmid, "delivered": False}
        # ---- submit to the single outbound queue and wait on the future ----
        p = _Pending()
        with self._pending_lock:
            self._pending[cmid] = p
        self._out_q.put((wire, cmid))
        if not p.event.wait(self.response_timeout_s):
            # RESPONSE TIMEOUT — atomic resolution: either WE take the pending slot (and own the
            # ambiguous outcome), or the reader/sender took it first and its resolution is consumed
            # exactly once. A timed-out request NEVER leaves the transport READY.
            took = self._take_pending(cmid)
            if took is None:                                 # boundary race: resolved concurrently
                p.event.wait(2.0)                            # resolve() completes imminently
                if p.kind is not None:
                    return self._finish_resolved(cmid, p)
            self.corr.mark_unknown(cmid)                     # retained PERMANENTLY, never forgotten
            self._alarm("OUTCOME_UNKNOWN_TIMEOUT", {"msg_type": msg_type, "client_msg_id": cmid})
            self.on_disconnect()                             # fail-closed: READY invalidated, I/O
            return {"status": Result.OUTCOME_UNKNOWN, "client_msg_id": cmid}   # session stopped
        return self._finish_resolved(cmid, p)

    def _finish_resolved(self, cmid, p):
        """Consume a resolved pending slot exactly once (RESPONSE / not-sent / ambiguous)."""
        if p.kind == "RESPONSE":
            resp = p.value
            self.corr.resolve(cmid, resp.payload)
            status = (Result.REJECTED if resp.msg_type in (MsgType.ORDER_REJECT, MsgType.ERROR_RES)
                      else Result.OK)
            return {"status": status, "msg_type": resp.msg_type, "payload": resp.payload,
                    "client_msg_id": cmid}
        return {"status": p.kind, "client_msg_id": cmid, "why": p.value,
                "delivered": False if p.kind == Result.DEFINITELY_NOT_SENT else None}

    # ---- event handling -------------------------------------------------------------------------
    _KNOWN_EVENT_SUBTYPES = frozenset({"FILL", "PARTIAL_FILL", "STOP_MOVED", "ORDER_CANCELLED"})

    def _handle_event(self, env):
        sub = (env.payload or {}).get("subtype")
        if env.msg_type == MsgType.EXECUTION_EVENT and sub not in self._KNOWN_EVENT_SUBTYPES:
            return self._handle_unknown(env)
        self._alarm("EVENT", {"msg_type": env.msg_type, "subtype": sub})

    def _handle_unknown(self, env):
        """Fail-closed: an unrecognised inbound message/event NEVER mutates state or touches a
        position. It is recorded (sanitised) for human review only."""
        self._alarm("UNKNOWN_INBOUND_FAIL_CLOSED",
                    {"msg_type": getattr(env, "msg_type", None), "payload": getattr(env, "payload", None)})
        return None

    # ---- reconciled snapshot (read accessors; no equality check here — that lives in the executor) -
    def known_orders(self):
        return dict(self._known_orders)

    def known_positions(self):
        return dict(self._known_positions)

    # ---- permitted ACTION families (approved requests in; broker facts out) ---------------------
    def send_open(self, spec):
        """Approved LIMIT opening. `spec` is a demo_lane.broker_request.BrokerOrderRequest already
        built + approved upstream. Returns broker facts (or None on OUTCOME_UNKNOWN /
        DEFINITELY_NOT_SENT, so the adapter maps it to the executor's OUTCOME_UNKNOWN)."""
        correlation = {"side": spec.trade_side, "symbol": spec.symbol_id,
                       "limit": spec.limit_price, "stop": spec.stop_loss,
                       "expiry": spec.expiration_timestamp, "session": self._session_seq}
        client_order_id = protobuf_mapper.deterministic_client_order_id(correlation)
        payload = {"account_id": spec.ctid_trader_account_id, "symbol_id": spec.symbol_id,
                   "trade_side": spec.trade_side, "volume": spec.volume,
                   "limit_price": spec.limit_price, "stop_loss": spec.stop_loss,
                   "expiration_timestamp": spec.expiration_timestamp, "client_order_id": client_order_id}
        r = self._request(MsgType.OPEN_LIMIT_REQ, payload, key=("open", client_order_id))
        if r["status"] in (Result.OUTCOME_UNKNOWN, Result.DEFINITELY_NOT_SENT):
            return None
        if r["status"] == Result.REJECTED:
            return {"status": "REJECTED", "order_id": None, "stop_accepted": False,
                    "filled_volume": 0, "why": r["payload"].get("why")}
        return dict(r["payload"])                             # broker facts, verbatim

    def cancel_pending(self, order_id):
        if order_id not in self._known_orders:
            self._alarm("NO_TOUCH_UNKNOWN_ORDER", {"order_id": order_id})
            return {"status": Result.NO_TOUCH, "order_id": order_id, "why": "unknown/unowned order"}
        r = self._request(MsgType.CANCEL_PENDING_REQ,
                          {"order_id": order_id, "account_id": self.credentials.ctid_trader_account_id()},
                          key=("cancel", order_id, self._session_seq))
        return r

    def close_reduce(self, position_id, volume, owner="ORANGE"):
        pos = self._known_positions.get(position_id)
        if pos is None:
            self._alarm("NO_TOUCH_UNKNOWN_POSITION", {"position_id": position_id})
            return {"status": Result.NO_TOUCH, "position_id": position_id, "why": "unknown position"}
        if pos.get("owner") != owner:
            # known to us but ownership does not match -> ratified containment, NO destructive action
            self._alarm("CONTAINMENT_OWNERSHIP_MISMATCH",
                        {"position_id": position_id, "expected_owner": owner, "seen": pos.get("owner")})
            return {"status": Result.CONTAINED, "position_id": position_id,
                    "why": "known-owned mismatch — contained, no touch"}
        if not isinstance(volume, int) or volume <= 0 or volume > pos.get("volume", 0):
            self._alarm("CLOSE_REFUSED_QTY", {"position_id": position_id, "volume": volume})
            return {"status": Result.NO_TOUCH, "position_id": position_id,
                    "why": "reduce-only quantity invalid"}
        return self._request(MsgType.CLOSE_REDUCE_REQ,
                             {"position_id": position_id, "volume": volume,
                              "account_id": self.credentials.ctid_trader_account_id()},
                             key=("close", position_id, volume, self._session_seq))

    def amend_stop(self, order_id, stop_loss):
        if order_id not in self._known_orders:
            self._alarm("NO_TOUCH_UNKNOWN_ORDER", {"order_id": order_id})
            return {"status": Result.NO_TOUCH, "order_id": order_id, "why": "unknown/unowned order"}
        return self._request(MsgType.AMEND_STOP_REQ,
                             {"order_id": order_id, "stop_loss": stop_loss,
                              "account_id": self.credentials.ctid_trader_account_id()},
                             key=("amend", order_id, stop_loss, self._session_seq))


# ---- production composition (refuses while gates False; no real credential provider in this build) -
class ProductionConnector:
    """The ONLY production connector. Fixed demo endpoint; takes NO host/port. connect() runs the
    egress allow-rule, which raises NOT_ARMED while gates are False, so no socket is ever opened."""
    IS_MOCK = False
    connected = False

    def __init__(self):
        self.host, self.port = tc.DEMO_HOST, tc.DEMO_PORT

    def connect(self):
        egress_guard.assert_endpoint_allowed(self.host, self.port, gates_armed=tc.production_armed())
        raise NotArmed("production path unreachable in this build (gates False; no real transport)")

    def send(self, frame_bytes):                             # pragma: no cover - never reached
        raise NotArmed("not connected")

    def recv(self, timeout=None):                            # pragma: no cover
        raise NotArmed("not connected")

    def close(self):
        pass


def build_production_transport():
    """Assemble the production transport. It is NOT_ARMED (gates hard False) and carries NO real
    credential provider (the DPAPI-backed provider is a later, separately-reviewed step). Any attempt
    to bring it up raises NotArmed — prohibited-by-absence, proven by test."""
    return ConnectedTransport(connector=ProductionConnector(), codec=framing.FakeCodec(),
                              credential_provider=cred.FakeCredentialProvider(),
                              policy=production_policy())
