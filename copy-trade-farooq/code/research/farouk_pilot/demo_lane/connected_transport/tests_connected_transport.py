"""OFFLINE test suite for connected_transport. The FIRST thing it does is install the process-wide
external-egress guard, so NOTHING in this suite can reach a non-loopback host (DNS included). All
'broker' interaction is the in-memory FakeBroker or a real 127.0.0.1 loopback server. No OAuth, no
real credential, no real endpoint, no order to any real venue.

Run:  python -m demo_lane.connected_transport.tests_connected_transport
"""
import ast
import io
import os
import socket
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DEMO_LANE = os.path.dirname(HERE)
FAROUK_PILOT = os.path.dirname(DEMO_LANE)
if FAROUK_PILOT not in sys.path:
    sys.path.insert(0, FAROUK_PILOT)

from demo_lane.connected_transport import egress_guard          # noqa: E402
# ---- install the egress booby-trap BEFORE anything else can touch a socket ----
egress_guard.install_test_egress_guard()

from demo_lane.connected_transport import (                     # noqa: E402
    credentials as cred, fake_wire, framing, state as st, transport as T, transport_config as tc)
from demo_lane.connected_transport.framing import Envelope, MsgType   # noqa: E402
from demo_lane.broker_request import BrokerOrderRequest         # noqa: E402

PASS = 0


def ok(cond, name):
    global PASS
    assert cond, f"FAIL: {name}"
    PASS += 1


class FakeClock:
    def __init__(self, t=1000.0):
        self.t = float(t)

    def __call__(self):
        return self.t

    def advance(self, dt):
        self.t += dt


class StaticRecvConnector:
    """Returns pre-baked byte chunks from recv (for controlled framing/await tests)."""
    IS_MOCK = True

    def __init__(self, chunks):
        self._chunks = list(chunks)
        self.host, self.port = "in-memory", 0

    def connect(self):
        pass

    def send(self, b):
        pass

    def recv(self, timeout=None):
        return self._chunks.pop(0) if self._chunks else None

    def close(self):
        pass


CODEC = framing.FakeCodec()
FAKE_CREDS = cred.FakeCredentialProvider(ctid=1_000_001)
SPEC = BrokerOrderRequest(ctid_trader_account_id=1_000_001, symbol_id=42, trade_side="SELL",
                          volume=100, limit_price=4161.0, stop_loss=4187.0,
                          expiration_timestamp=99_999_999)


def fresh(**broker_kw):
    """A test-armed transport wired to a FakeConnector+FakeBroker."""
    broker = fake_wire.FakeBroker(**broker_kw)
    conn = fake_wire.FakeConnector(broker)
    t = T.ConnectedTransport(connector=conn, codec=CODEC, credential_provider=FAKE_CREDS,
                             policy=T.test_only_policy(), clock=FakeClock())
    t.response_timeout_s = 1.0                   # wall-clock future wait; keep tests fast
    return t, conn, broker


def wait_for(cond, timeout=2.0):
    """Poll for an I/O-loop-produced condition (reader/sender threads are asynchronous)."""
    import time as _time
    end = _time.monotonic() + timeout
    while _time.monotonic() < end:
        if cond():
            return True
        _time.sleep(0.01)
    return bool(cond())


# ================================================================================================
# 1. FRAMING — roundtrip, combined, fragmented, oversized (fail-closed)
# ================================================================================================
p1 = b"hello"; p2 = b"world!!"
ok(framing.Deframer().feed(framing.frame(p1)) == [p1], "frame/deframe single roundtrip")
ok(framing.Deframer().feed(framing.frame(p1) + framing.frame(p2)) == [p1, p2],
   "combined: two frames in one read -> two payloads")
df = framing.Deframer(); got = []
for byte in framing.frame(p1):
    got += df.feed(bytes([byte]))
ok(got == [p1], "fragmented: byte-by-byte feed yields the whole frame once complete")
try:
    framing.Deframer().feed(b"\xff\xff\xff\xff" + b"x")     # declares ~4GiB
    ok(False, "oversized length must fail closed")
except framing.FramingError:
    ok(True, "oversized declared frame length -> FramingError (fail-closed)")

# ================================================================================================
# 2. EXTERNAL-EGRESS GUARD — non-loopback connect + DNS refused; fixed-destination allow-rule
# ================================================================================================
try:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM); s.settimeout(0.2)
    s.connect(("8.8.8.8", 53)); s.close()
    ok(False, "non-loopback connect must be blocked")
except egress_guard.EgressRefused:
    ok(True, "ZERO EGRESS: connect to a public IP is blocked by the guard")
try:
    socket.getaddrinfo("demo.ctraderapi.com", 5035)
    ok(False, "resolving the demo host must be blocked")
except egress_guard.EgressRefused:
    ok(True, "ZERO EGRESS: DNS resolution of demo.ctraderapi.com is blocked")
try:
    egress_guard.assert_endpoint_allowed("evil.example.com", 5035, gates_armed=True)
    ok(False, "non-demo endpoint must be refused")
except egress_guard.EgressRefused:
    ok(True, "fixed destination: only demo.ctraderapi.com:5035 is dialable (no override)")
try:
    egress_guard.assert_endpoint_allowed(tc.DEMO_HOST, tc.DEMO_PORT, gates_armed=False)
    ok(False, "even the demo endpoint must be refused while gates False")
except egress_guard.EgressRefused:
    ok(True, "fixed destination + gates False -> refused (NOT_ARMED)")

# ================================================================================================
# 3. CREDENTIALS — provider redaction / sanitised logging
# ================================================================================================
ok("FAKE_CLIENT_SECRET" not in repr(FAKE_CREDS) and "REDACTED" in repr(FAKE_CREDS),
   "credential provider repr never renders the secret")
san = cred.sanitise({"client_secret": "SEKRET", "access_token": "TOK", "order_id": "O1"})
ok("SEKRET" not in str(san) and "TOK" not in str(san) and san["order_id"] == "O1",
   "sanitise() redacts secret-like keys, preserves the rest")
ok("plain" not in cred.redact_secret("plain"), "redact_secret never returns plaintext")

# ================================================================================================
# 4. GATES / ARMING — production NOT_ARMED; test policy binds to mock only
# ================================================================================================
ok(tc.gates_all_false() and tc.production_armed() is False,
   "authoritative gates all False; production_armed() False")
prod = T.build_production_transport()
try:
    prod.open()
    ok(False, "production open must refuse while gates False")
except T.NotArmed:
    ok(True, "send-refused-gates-false: production transport open() -> NotArmed")
try:
    T.ProductionConnector().connect()
    ok(False, "production connector must refuse")
except (T.NotArmed, egress_guard.EgressRefused):
    ok(True, "ProductionConnector.connect() -> refused (fixed endpoint, gates False)")


class _NonMock:
    def connect(self): pass
    def send(self, b): pass
    def recv(self, t=None): return None
    def close(self): pass


try:
    tt = T.ConnectedTransport(connector=_NonMock(), codec=CODEC, credential_provider=FAKE_CREDS,
                              policy=T.test_only_policy())
    tt.open()
    ok(False, "test policy must refuse a non-mock connector")
except T.NotArmed:
    ok(True, "test-enable binds to fake/loopback only (non-mock connector -> NotArmed)")

# ================================================================================================
# 5. LIFECYCLE + AUTH-STATE ORDERING + RECONCILE-ONLY
# ================================================================================================
t, conn, broker = fresh(owned_orders={"O9": {"order_id": "O9"}},
                        owned_positions={"P9": {"volume": 100, "owner": "ORANGE"}})
ok(t.bring_up() == st.AuthState.READY, "bring_up: connect->auth->reconcile->READY")
ok(t.known_orders() == {"O9": {"order_id": "O9"}} and "P9" in t.known_positions(),
   "reconcile populated the owned order/position snapshot")

# auth ordering: account-auth before app-auth is rejected by the state machine
cs = st.ConnectionState(); cs.on_connected()
try:
    cs.on_account_authed(); ok(False, "account auth before app auth must fail")
except st.StateError:
    ok(True, "auth-state ordering: ACCOUNT_AUTHED before APP_AUTHED -> StateError")

# send-refused-before-auth: connected only, action refused
t2, _, _ = fresh()
t2.open()
try:
    t2.send_open(SPEC); ok(False, "action before auth must be refused")
except st.StateError:
    ok(True, "send-refused-before-auth: send_open in CONNECTED -> StateError")

# reconcile-only: authed but not reconciled -> action refused; after reconcile -> allowed
t3, _, _ = fresh()
t3.open(); t3.authenticate()
ok(t3.cstate.state == st.AuthState.ACCOUNT_AUTHENTICATED and not t3.cstate.reconciled,
   "after auth, state is ACCOUNT_AUTHENTICATED and NOT reconciled (RECONCILE_ONLY window)")
try:
    t3.send_open(SPEC); ok(False, "action before reconcile must be refused")
except st.StateError:
    ok(True, "reconcile-only: send_open before reconcile -> StateError")
t3.reconcile()
ok(t3.cstate.state == st.AuthState.READY, "after reconcile -> READY (actions now permitted)")

# ================================================================================================
# 6. ACTIONS — open happy / rejection / correlation / duplicate-send
# ================================================================================================
t4, c4, b4 = fresh(fill_on_open=True)
t4.bring_up()
facts = t4.send_open(SPEC)
ok(facts and facts.get("order_id") and facts.get("stop_accepted") is True,
   "send_open happy -> broker facts returned (order_id + stop attached)")
ok(MsgType.OPEN_LIMIT_REQ in b4.seen, "the OPEN request reached the broker")

t5, _, _ = fresh(reject_open=True); t5.bring_up()
rej = t5.send_open(SPEC)
ok(rej and rej.get("status") == "REJECTED", "broker rejection surfaced as REJECTED (facts returned)")

k1 = ("open", "X"); k2 = ("open", "Y")
ok(st.CorrelationRegistry.client_msg_id(k1) == st.CorrelationRegistry.client_msg_id(k1)
   and st.CorrelationRegistry.client_msg_id(k1) != st.CorrelationRegistry.client_msg_id(k2),
   "correlation: deterministic + distinct per key")

t6, _, _ = fresh(fill_on_open=True); t6.bring_up(); t6.send_open(SPEC)
try:
    t6.send_open(SPEC); ok(False, "identical in-session resend must be refused")
except st.StateError:
    ok(True, "duplicate-send prevention: identical open (same correlation) -> refused (no blind resend)")

# raw/generic send is impossible: _request refuses a non-permitted family
t6b, _, _ = fresh(); t6b.bring_up()
try:
    t6b._request("GENERIC_RAW_SEND", {}, key=("raw", 1)); ok(False, "raw send must be refused")
except st.StateError:
    ok(True, "no generic console/raw send: a non-permitted family is refused")

# ================================================================================================
# 7. SEND CLASSIFICATION (Chuck gap correction 1) — DEFINITELY_NOT_SENT only when provably
#    BEFORE any transmit; ANY error once connector.send begins is AMBIGUOUS -> OUTCOME_UNKNOWN
#    (correlation retained, no retry, READY invalidated, reconcile-first after reconnect)
# ================================================================================================
def _open_cmid(t):
    """The correlation cmid an open of SPEC uses in t's CURRENT session."""
    return st.CorrelationRegistry.client_msg_id(
        ("open", __import__("demo_lane.protobuf_mapper", fromlist=["x"]).deterministic_client_order_id(
            {"side": SPEC.trade_side, "symbol": SPEC.symbol_id, "limit": SPEC.limit_price,
             "stop": SPEC.stop_loss, "expiry": SPEC.expiration_timestamp, "session": t._session_seq})))


# (a) encoding/framing failure -> provably zero bytes -> DEFINITELY_NOT_SENT, correlation RELEASED
class _EncodeBoomCodec:
    def __init__(self, inner):
        self.inner = inner
        self.boom = False

    def encode(self, env):
        if self.boom:
            self.boom = False
            raise framing.FramingError("simulated encode failure (before any transmit)")
        return self.inner.encode(env)

    def decode(self, data):
        return self.inner.decode(data)


t7, c7, b7 = fresh(fill_on_open=True); t7.bring_up()
t7.codec = _EncodeBoomCodec(CODEC); t7.codec.boom = True
before7 = c7.sent_frames
r = t7.send_open(SPEC)
ok(r is None and any(a["kind"] == "DEFINITELY_NOT_SENT" for a in t7.alarms),
   "encode failure BEFORE transmit -> DEFINITELY_NOT_SENT")
ok(c7.sent_frames == before7 and t7.cstate.state == st.AuthState.READY,
   "pre-transmit failure: nothing sent, session stays READY (no false disconnect)")
r2 = t7.send_open(SPEC)                                   # same key allowed again (was released)
ok(r2 and r2.get("order_id"),
   "DEFINITELY_NOT_SENT is the ONLY path that releases the correlation -> deliberate re-issue OK")

# (b) connector not connected BEFORE send starts -> DEFINITELY_NOT_SENT, released
t7b, c7b, b7b = fresh(fill_on_open=True); t7b.bring_up()
c7b.connected = False
rb = t7b.send_open(SPEC)
ok(rb is None and any(a["kind"] == "DEFINITELY_NOT_SENT" for a in t7b.alarms),
   "not-connected before send starts -> DEFINITELY_NOT_SENT")
c7b.connected = True
ok(t7b.send_open(SPEC) is not None, "pre-transmit refusal released the correlation (re-issue OK)")

# (c) sendall raises with ZERO/UNKNOWN bytes transmitted -> AMBIGUOUS -> OUTCOME_UNKNOWN
t8, c8, b8 = fresh(fill_on_open=True); t8.bring_up()
sess8 = t8._session_seq
cmid8 = _open_cmid(t8)
c8.lose_send = True
r3 = t8.send_open(SPEC)
ok(r3 is None and any(a["kind"] == "OUTCOME_UNKNOWN_AMBIGUOUS_SEND" for a in t8.alarms),
   "send-phase exception (zero/unknown bytes) -> OUTCOME_UNKNOWN, never a clean failure")
ok(t8.corr.status(cmid8) == st.Correlation.OUTCOME_UNKNOWN,
   "ambiguous send: correlation RETAINED and marked OUTCOME_UNKNOWN (never forgotten)")
ok(t8.cstate.state == st.AuthState.DISCONNECTED and not t8.cstate.reconciled,
   "ambiguous send: READY invalidated -> DISCONNECTED (no further action possible)")
try:
    t8.send_open(SPEC); ok(False, "no automatic retry after ambiguous send")
except st.StateError:
    ok(True, "ambiguous send: no retry — action refused until re-auth + reconcile")

# reconnect: full sequence + RECONCILE before anything may be sent again
c8.lose_send = False
ok(t8.reconnect(sleep=lambda s: None) and t8.cstate.state == st.AuthState.READY,
   "reconnect after ambiguous send: full auth + reconcile -> READY")
r4 = t8.send_open(SPEC)                                    # NEW session correlation, post-reconcile
last_recon = len(b8.seen) - 1 - b8.seen[::-1].index(MsgType.RECONCILE_REQ)
last_open = len(b8.seen) - 1 - b8.seen[::-1].index(MsgType.OPEN_LIMIT_REQ)
ok(r4 and r4.get("order_id") and last_recon < last_open,
   "resend decision only AFTER reconciliation proved broker state (reconcile precedes new open)")
ok(t8.corr.status(cmid8) == st.Correlation.OUTCOME_UNKNOWN,
   "the session-1 ambiguous correlation stays OUTCOME_UNKNOWN forever (no silent forget)")


# (d) a PREFIX of the frame is transmitted, then the socket raises -> AMBIGUOUS
class _PrefixThenRaise(fake_wire.FakeConnector):
    fail_next = False

    def send(self, frame_bytes):
        if self.fail_next:
            self.fail_next = False                          # a prefix left; frame never completed
            raise ConnectionError("connection reset after partial write")
        super().send(frame_bytes)


bp = fake_wire.FakeBroker(fill_on_open=True)
cp = _PrefixThenRaise(bp)
tp = T.ConnectedTransport(connector=cp, codec=CODEC, credential_provider=FAKE_CREDS,
                          policy=T.test_only_policy(), clock=FakeClock())
tp.response_timeout_s = 1.0
tp.bring_up()
cmid_p = _open_cmid(tp)
cp.fail_next = True
ok(tp.send_open(SPEC) is None and tp.corr.status(cmid_p) == st.Correlation.OUTCOME_UNKNOWN
   and any(a["kind"] == "OUTCOME_UNKNOWN_AMBIGUOUS_SEND" for a in tp.alarms),
   "prefix-transmitted-then-raise -> OUTCOME_UNKNOWN, correlation retained")


# (e) the COMPLETE frame is transmitted (broker saw it), then the socket raises -> AMBIGUOUS
class _CompleteThenRaise(fake_wire.FakeConnector):
    fail_next = False

    def send(self, frame_bytes):
        if self.fail_next:
            self.fail_next = False
            saved = self.lose_after_send
            self.lose_after_send = True                     # frame delivered; response lost
            try:
                super().send(frame_bytes)
            finally:
                self.lose_after_send = saved
            raise ConnectionError("connection reset after complete write")
        super().send(frame_bytes)


bc = fake_wire.FakeBroker(fill_on_open=True)
cc = _CompleteThenRaise(bc)
tcx = T.ConnectedTransport(connector=cc, codec=CODEC, credential_provider=FAKE_CREDS,
                           policy=T.test_only_policy(), clock=FakeClock())
tcx.response_timeout_s = 1.0
tcx.bring_up()
cmid_c = _open_cmid(tcx)
cc.fail_next = True
rc = tcx.send_open(SPEC)
ok(rc is None and MsgType.OPEN_LIMIT_REQ in bc.seen
   and tcx.corr.status(cmid_c) == st.Correlation.OUTCOME_UNKNOWN,
   "complete-frame-then-raise (broker DID receive) -> OUTCOME_UNKNOWN, correlation retained")
ok(tcx.cstate.state == st.AuthState.DISCONNECTED,
   "complete-frame-then-raise also invalidates READY (reconcile-first before any resend)")

# ================================================================================================
# 8. NO-TOUCH / CONTAINMENT
# ================================================================================================
t9, _, _ = fresh(); t9.bring_up()
ok(t9.cancel_pending("O_UNKNOWN")["status"] == T.Result.NO_TOUCH,
   "unknown order -> NO_TOUCH (no send)")
ok(t9.close_reduce("P_UNKNOWN", 50)["status"] == T.Result.NO_TOUCH,
   "unknown position -> NO_TOUCH")
t10, _, _ = fresh(owned_positions={"PX": {"volume": 100, "owner": "SOMEONE_ELSE"}}); t10.bring_up()
ok(t10.close_reduce("PX", 50)["status"] == T.Result.CONTAINED,
   "known-owned MISMATCH -> ratified containment (no destructive action)")
t11, _, b11 = fresh(owned_positions={"PY": {"volume": 100, "owner": "ORANGE"}}); t11.bring_up()
ok(t11.close_reduce("PY", 50)["status"] == T.Result.OK and MsgType.CLOSE_REDUCE_REQ in b11.seen,
   "owned position -> risk-reducing close sent")

# ================================================================================================
# 9. RECONNECT -> RECONCILE-before-action
# ================================================================================================
t12, c12, b12 = fresh(); t12.bring_up()
t12.on_disconnect()
ok(t12.cstate.state == st.AuthState.DISCONNECTED, "disconnect -> DISCONNECTED")
try:
    t12.send_open(SPEC); ok(False, "action while disconnected must be refused")
except st.StateError:
    ok(True, "reconnect: no action while disconnected")
did = t12.reconnect(sleep=lambda s: None)
ok(did and t12.cstate.state == st.AuthState.READY,
   "reconnect: bounded backoff -> re-auth -> RECONCILE -> READY (reconcile before any action)")

# ================================================================================================
# 10. HEARTBEAT — AUTOMATIC when idle (sender thread; no manual call) / in-stream skip / staleness
# ================================================================================================
clk = FakeClock()
t13, c13, b13 = fresh(); t13.now = clk; t13.bring_up()
t13.last_outbound_t = clk.t
clk.advance(tc.HEARTBEAT_INTERVAL_S + 1)
ok(wait_for(lambda: MsgType.HEARTBEAT in b13.seen) and tc.HEARTBEAT_INTERVAL_S <= 10,
   "heartbeat: emitted AUTOMATICALLY by the I/O owner when idle past the interval (<=10s)")
# in-stream heartbeat is skipped by the reader; the non-heartbeat message is still consumed
hb = framing.frame(CODEC.encode(Envelope(MsgType.HEARTBEAT, "HB-x", {})))
ack = framing.frame(CODEC.encode(Envelope(MsgType.ORDER_ACK, "ORG-unmatched", {"order_id": "OZ"})))
t14 = T.ConnectedTransport(connector=StaticRecvConnector([hb + ack]), codec=CODEC,
                           credential_provider=FAKE_CREDS, policy=T.test_only_policy())
t14.open()
ok(wait_for(lambda: any(a["kind"] == "EVENT" and a["detail"].get("msg_type") == MsgType.ORDER_ACK
                        for a in t14.alarms)),
   "reader: in-stream heartbeat skipped; the non-heartbeat message in the same batch is consumed")
ok(not any(a["detail"].get("msg_type") == MsgType.HEARTBEAT for a in t14.alarms
           if a["kind"] == "EVENT"),
   "reader: heartbeats are never surfaced as events")
clk2 = FakeClock(); t15, _, _ = fresh(); t15.now = clk2; t15.bring_up()
t15.last_inbound_t = clk2.t; clk2.advance(tc.HEARTBEAT_TIMEOUT_S + 1)
ok(t15.is_stale(), "heartbeat timeout: no inbound past the timeout -> link reported stale")

# ================================================================================================
# 11. UNKNOWN INBOUND EVENT -> fail-closed (no state change / no touch)
# ================================================================================================
t16, _, _ = fresh(fill_on_open=True, unknown_event=True); t16.bring_up()
pos_before = t16.known_positions()
facts16 = t16.send_open(SPEC)
ok(facts16 and facts16.get("order_id")
   and wait_for(lambda: any(a["kind"] == "UNKNOWN_INBOUND_FAIL_CLOSED" for a in t16.alarms)),
   "response + async event in the SAME frame batch: both processed (ack resolved, event fail-closed)")
ok(t16.known_positions() == pos_before,
   "unknown event mutated NO state / touched NO position")

# alarms never contain a raw secret
t16._alarm("PROBE", {"access_token": "TOPSECRET"})
ok(all("TOPSECRET" not in str(a) for a in t16.alarms), "sanitised logging: no raw secret in any alarm")

# ================================================================================================
# 12. REAL 127.0.0.1 LOOPBACK — framing over an actual socket (egress guard permits loopback only)
# ================================================================================================
srv = fake_wire.LoopbackServer(fake_wire.FakeBroker(fill_on_open=True))
try:
    lconn = fake_wire.LoopbackConnector(srv.host, srv.port)
    tl = T.ConnectedTransport(connector=lconn, codec=CODEC, credential_provider=FAKE_CREDS,
                              policy=T.test_only_policy())
    ok(tl.bring_up() == st.AuthState.READY, "loopback: full lifecycle to READY over a real socket")
    lf = tl.send_open(SPEC)
    ok(lf and lf.get("order_id"), "loopback: send_open over 127.0.0.1 returns broker facts")
    tl.close()
finally:
    srv.stop()

# ================================================================================================
# 13. ISOLATION — executor import-closure has ZERO edge to transport/mapper/socket/twisted
# ================================================================================================
def _local_imports(modname):
    path = os.path.join(DEMO_LANE, modname + ".py")
    if not os.path.isfile(path):
        return set()
    tree = ast.parse(open(path, encoding="utf-8").read())
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if node.level and node.module is None:
                for al in node.names:
                    names.add(al.name)                        # from . import a, b
            elif node.module:
                names.add(node.module.split(".")[0])
        elif isinstance(node, ast.Import):
            for al in node.names:
                names.add(al.name.split(".")[0])
    return names


seen_mod, all_names, work = set(), set(), ["executor"]
LOCAL = {f[:-3] for f in os.listdir(DEMO_LANE) if f.endswith(".py")}
while work:
    m = work.pop()
    if m in seen_mod:
        continue
    seen_mod.add(m)
    for n in _local_imports(m):
        all_names.add(n)
        if n in LOCAL and n not in seen_mod:
            work.append(n)
ok("connected_transport" not in all_names and "connected_transport" not in seen_mod,
   "isolation: executor import-closure has NO edge to connected_transport")
ok("protobuf_mapper" not in all_names,
   "isolation: executor import-closure never reaches protobuf_mapper")
ok("socket" not in all_names and "twisted" not in all_names and "ctrader_open_api" not in all_names,
   "isolation: executor import-closure imports no socket/twisted/ctrader_open_api")
# and the intended edge DOES exist: the transport imports the approved mapper
ok(getattr(T, "protobuf_mapper", None) is not None,
   "transport MAY import the approved mapper (edge present, by design)")

# ================================================================================================
# 14. AUTH + ACCOUNT GUARD — exact state sequence + allowlist rejections + single send queue
# ================================================================================================
seq = st.ConnectionState()
order = []
seq.on_connected(); order.append(seq.state)
seq.on_app_authed(); order.append(seq.state)
seq.on_account_list(); order.append(seq.state)
seq.on_account_validated(); order.append(seq.state)
seq.on_account_authed(); order.append(seq.state)
seq.on_reconcile_start(); order.append(seq.state)
seq.on_reconciled(); order.append(seq.state)
ok(order == [st.AuthState.CONNECTED, st.AuthState.APPLICATION_AUTHENTICATED,
             st.AuthState.ACCOUNT_LIST_RECEIVED, st.AuthState.ACCOUNT_VALIDATED,
             st.AuthState.ACCOUNT_AUTHENTICATED, st.AuthState.RECONCILE_ONLY, st.AuthState.READY],
   "exact sequence: CONNECTED->APP_AUTH'D->ACCT_LIST->ACCT_VALIDATED->ACCT_AUTH'D->RECONCILE_ONLY->READY")

# account-auth is NOT permitted before validation, only after
g = st.ConnectionState(); g.on_connected(); g.on_app_authed(); g.on_account_list()
ok(not g.can_send(framing.MsgType.ACCOUNT_AUTH_REQ), "account-auth REFUSED before ACCOUNT_VALIDATED")
g.on_account_validated()
ok(g.can_send(framing.MsgType.ACCOUNT_AUTH_REQ), "account-auth permitted ONLY after ACCOUNT_VALIDATED")

# the account LIST request is actually sent, and BEFORE account-auth
tL, cL, bL = fresh(); tL.bring_up()
ok(MsgType.ACCOUNT_LIST_REQ in bL.seen
   and bL.seen.index(MsgType.ACCOUNT_LIST_REQ) < bL.seen.index(MsgType.ACCOUNT_AUTH_REQ),
   "account-list (GetAccountListByAccessToken) sent, and before account-auth")

# allowlist REJECTIONS: each -> sanitised alarm + NotArmed + NO account-auth + NO reconcile +
# NO trading request + not READY
_ACTION_MSGS = {MsgType.OPEN_LIMIT_REQ, MsgType.CANCEL_PENDING_REQ, MsgType.CLOSE_REDUCE_REQ,
                MsgType.AMEND_STOP_REQ}

def _guard_rejects(label, **bkw):
    tr, cr, br = fresh(**bkw)
    tr.open()
    try:
        tr.authenticate(); ok(False, f"{label}: must reject")
    except T.NotArmed:
        ok(any(a["kind"] == "ACCOUNT_GUARD_REJECT" for a in tr.alarms)
           and MsgType.ACCOUNT_AUTH_REQ not in br.seen
           and MsgType.RECONCILE_REQ not in br.seen
           and not (_ACTION_MSGS & set(br.seen))
           and tr.cstate.state != st.AuthState.READY,
           f"account guard: {label} -> alarm + NOT_ARMED; no account-auth, no reconcile, "
           f"no trading request, not READY")

_guard_rejects("missing (0 accounts)", account_list=[])
_guard_rejects("additional (2 accounts)",
               account_list=[{"ctidTraderAccountId": 1_000_001, "isLive": False},
                             {"ctidTraderAccountId": 1_000_002, "isLive": False}])
_guard_rejects("live account", account_list=[{"ctidTraderAccountId": 1_000_001, "isLive": True}])
_guard_rejects("wrong id", account_list=[{"ctidTraderAccountId": 9_999_999, "isLive": False}])
_guard_rejects("wrong scope (SCOPE_VIEW)", account_scope="SCOPE_VIEW")

# WRONG BROKER — the transport composes broker_environment from the SINGLE-SOURCE config constant,
# so a broker response cannot inject it. Prove (a) the single-source five-field conjunction rejects
# a non-Pepperstone environment, and (b) a connection context reporting a wrong environment is
# rejected end-to-end by the transport's guard path.
from demo_lane import gate as demo_gate, config as demo_config      # noqa: E402
_acc_good = {"endpoint": demo_config.DEMO_ENDPOINT, "isLive": False,
             "ctidTraderAccountId": demo_config.ALLOWED_CTID_TRADER_ACCOUNT_ID,
             "broker_environment": demo_config.EXPECTED_BROKER_ENVIRONMENT,
             "permissionScope": demo_config.REQUIRED_SCOPE}
ok(demo_gate.account_guard_ok(_acc_good) is True, "single-source guard passes the allowlisted account")
ok(demo_gate.account_guard_ok({**_acc_good, "broker_environment": "OTHERBROKER_DEMO"}) is False,
   "wrong broker environment -> single-source five-field guard REJECTS")

_wrong_env = __import__("types").SimpleNamespace(
    EXPECTED_BROKER_ENVIRONMENT="OTHERBROKER_DEMO",
    ALLOWED_CTID_TRADER_ACCOUNT_ID=demo_config.ALLOWED_CTID_TRADER_ACCOUNT_ID)
_saved_cfg = T.demo_config
T.demo_config = _wrong_env                      # simulate a NON-Pepperstone connection context
try:
    twb, _, bwb = fresh()
    twb.open()
    try:
        twb.authenticate(); ok(False, "wrong broker environment: must reject")
    except T.NotArmed:
        ok(any(a["kind"] == "ACCOUNT_GUARD_REJECT" for a in twb.alarms)
           and MsgType.ACCOUNT_AUTH_REQ not in bwb.seen and MsgType.RECONCILE_REQ not in bwb.seen,
           "account guard: wrong-broker context -> alarm + NOT_ARMED, no account-auth, no reconcile")
finally:
    T.demo_config = _saved_cfg

# disconnect INVALIDATES account-validation
td, _, _ = fresh(); td.bring_up()
ok(td.cstate.account_validated, "validated flag set at READY")
td.on_disconnect()
ok(not td.cstate.account_validated and td.cstate.state == st.AuthState.DISCONNECTED,
   "disconnect invalidates account-validation (full sequence required again)")

# ONE serialised send queue: every outbound funnels through _write (sender thread only)
tw, _, _ = fresh(); tw.bring_up()
ok(tw._writes == 4, "single send queue: bring_up funnelled exactly 4 writes (app,list,acct-auth,reconcile)")
tw._enqueue_heartbeat()                                      # manual seam SUBMITS, never writes
ok(wait_for(lambda: tw._writes == 5),
   "single send queue: a manual heartbeat is queued and written by the SENDER thread")
ok(tc.HEARTBEAT_INTERVAL_S <= 10, "heartbeat interval is at most 10s")

# ================================================================================================
# 16. THE ONE ALWAYS-ON I/O OWNER (Chuck gap correction 2)
# ================================================================================================
import threading                                             # noqa: E402

# 16a. order ack now, FILL LATER with NO second request -> the reader consumes it
ta, ca, ba = fresh(owned_orders={}); ta.bring_up()
fa = ta.send_open(SPEC)                                      # ack only (no fill_on_open)
ok(fa and fa.get("order_id"), "16a setup: open acknowledged")
ca.inject(Envelope(MsgType.ORDER_FILL, None,
                   {"order_id": fa["order_id"], "filled_volume": 100, "position_id": "PLATE"}))
ok(wait_for(lambda: any(a["kind"] == "EVENT" and a["detail"].get("msg_type") == MsgType.ORDER_FILL
                        for a in ta.alarms)),
   "async fill arriving LATER with no request awaiting -> consumed by the always-on reader")

# 16b. async stop/cancel event while completely IDLE -> consumed
ca.inject(Envelope(MsgType.EXECUTION_EVENT, None, {"subtype": "STOP_MOVED"}))
ok(wait_for(lambda: any(a["kind"] == "EVENT" and a["detail"].get("subtype") == "STOP_MOVED"
                        for a in ta.alarms)),
   "async STOP_MOVED event while idle -> consumed (no request in flight)")


# 16c. two distinct requests answered in REVERSE order -> each routed to its own caller by cmid
class _ReorderConnector(fake_wire.FakeConnector):
    """After arming `hold`, buffers request envelopes and answers them in REVERSE arrival order."""
    def __init__(self, broker, **kw):
        super().__init__(broker, **kw)
        self.hold = False
        self._held = []

    def send(self, frame_bytes):
        if not self.hold:
            return super().send(frame_bytes)
        self.sent_frames += 1
        for payload in framing.Deframer().feed(frame_bytes):
            self._held.append(self.codec.decode(payload))
        if len(self._held) >= 2:
            held, self._held = self._held, []
            with self._inbox_lock:
                for env in reversed(held):
                    for r in self.broker.handle(env):
                        self._inbox.extend(framing.frame(self.codec.encode(r)))


br = fake_wire.FakeBroker(owned_orders={"O1": {"order_id": "O1"}, "O2": {"order_id": "O2"}})
cr = _ReorderConnector(br)
tr = T.ConnectedTransport(connector=cr, codec=CODEC, credential_provider=FAKE_CREDS,
                          policy=T.test_only_policy(), clock=FakeClock())
tr.response_timeout_s = 3.0
tr.bring_up()
cr.hold = True
res = {}
th1 = threading.Thread(target=lambda: res.update(a=tr.cancel_pending("O1")))
th2 = threading.Thread(target=lambda: res.update(b=tr.cancel_pending("O2")))
th1.start(); th2.start(); th1.join(4); th2.join(4)
ok(res.get("a", {}).get("status") == T.Result.OK
   and res["a"]["payload"]["order_id"] == "O1"
   and res.get("b", {}).get("status") == T.Result.OK
   and res["b"]["payload"]["order_id"] == "O2",
   "reverse-order responses: each routed to ITS caller by clientMsgId (no cross-wiring)")

# 16d. exactly ONE reader thread and ONE sender thread ever touch the socket; callers never do
ts, cs, bs = fresh(fill_on_open=True)
recv_threads, send_threads = set(), set()
_orig_recv, _orig_send = cs.recv, cs.send


def _rec_recv(timeout=None):
    recv_threads.add(threading.get_ident())
    return _orig_recv(timeout)


def _rec_send(fb):
    send_threads.add(threading.get_ident())
    return _orig_send(fb)


cs.recv, cs.send = _rec_recv, _rec_send
ts.bring_up()
ok(ts.send_open(SPEC) is not None, "16d setup: request served through the loop")
hb_writes_before = ts._writes
ts._enqueue_heartbeat()                                      # manual heartbeat seam from the CALLER
ok(wait_for(lambda: ts._writes == hb_writes_before + 1),
   "manual heartbeat seam -> SENDER-thread output (caller only submitted to the queue)")
wait_for(lambda: len(recv_threads) >= 1)
main_id = threading.get_ident()
ok(len(recv_threads) == 1 and main_id not in recv_threads,
   "SINGLE READER: exactly one thread (never the caller) calls connector.recv")
ok(len(send_threads) == 1 and main_id not in send_threads,
   "STRICT SINGLE SENDER: one thread identity calls connector.send across auth, actions AND "
   "heartbeats — never the caller")
try:
    ts._write(b"\x00\x00\x00\x00")
    ok(False, "a caller thread must not be able to write directly")
except st.StateError:
    ok(True, "direct _write from a caller thread -> refused (sender-thread-only guard)")

# 16e. disconnect WAKES pending callers as OUTCOME_UNKNOWN (well before the response timeout)
tw2, cw2, bw2 = fresh(fill_on_open=True); tw2.bring_up()
cw2.lose_after_send = True
tw2.response_timeout_s = 6.0
slot = {}


def _blocked_open():
    import time as _time
    t0 = _time.monotonic()
    slot["res"] = tw2.send_open(SPEC)
    slot["dt"] = _time.monotonic() - t0


thb = threading.Thread(target=_blocked_open); thb.start()
wait_for(lambda: tw2.corr.pending_cmids())                   # the request is in flight
tw2.on_disconnect()
thb.join(3)
ok(slot.get("res") is None and slot.get("dt", 99) < 3.0,
   "disconnect wakes the pending caller promptly as OUTCOME_UNKNOWN (no timeout wait)")
ok(all(tw2.corr.status(c) != st.Correlation.PENDING for c in [])
   and not tw2.corr.pending_cmids(),
   "disconnect: no correlation left PENDING (all marked OUTCOME_UNKNOWN, none forgotten)")

# 16f. reconnect completes FULL auth + reconciliation before queued actions resume
cw2.lose_after_send = False
tw2.response_timeout_s = 1.0
ok(tw2.reconnect(sleep=lambda s: None) and tw2.cstate.state == st.AuthState.READY,
   "reconnect: full sequence to READY")
rr = tw2.cancel_pending("O_UNKNOWN")                         # unknown -> NO_TOUCH (no send), READY OK
ok(rr["status"] == T.Result.NO_TOUCH and tw2.cstate.state == st.AuthState.READY,
   "after reconnect the queue serves actions again (READY; reconcile happened first)")

# ================================================================================================
# 17. BROKER-IDENTITY CLAIMS (Chuck gap correction 3) — no self-comparison passed off as attestation
# ================================================================================================
ok(tc.BROKER_IDENTITY_CLAIMS == {
    "DEMO_ENDPOINT": "OFFLINE_PROVEN",
    "ALLOWLISTED_ACCOUNT_ID": "OFFLINE_GUARD_PROVEN",
    "IS_LIVE_FALSE": "OFFLINE_GUARD_PROVEN",
    "SCOPE_TRADE": "OFFLINE_GUARD_PROVEN",
    "PEPPERSTONE_ACCOUNT_BINDING": "PENDING_READ_ONLY_PREFLIGHT",
}, "broker-identity claims recorded EXACTLY as specified (binding deferred to preflight)")
try:
    tc.validate_preflight_binding(None)
    ok(False, "absent binding must fail closed")
except ValueError:
    ok(True, "preflight binding absent -> fail-closed (composition stays NOT_ARMED)")
try:
    tc.validate_preflight_binding({"account_id_sha256": "ab", "is_live": False})
    ok(False, "incomplete binding must fail closed")
except ValueError:
    ok(True, "preflight binding incomplete -> fail-closed")
_FAKE_BINDING = {                                            # obviously-fake shape-validation data
    "account_id_sha256": "f" * 64, "account_id_last4": "8849", "is_live": False,
    "broker_identity": "PEPPERSTONE_DEMO (FAKE TEST RECORD)", "endpoint": tc.DEMO_HOST,
    "preflight_source": "read_only_preflight_FAKE", "preflight_timestamp_utc": "2026-07-24T00:00:00Z",
    "binding_sha256": "e" * 64,
}
ok(tc.validate_preflight_binding(_FAKE_BINDING) is True,
   "a complete sanitised binding passes SHAPE validation (real one only from the preflight lane)")
for bad_key, bad_val, label in (("is_live", True, "isLive true"),
                                ("endpoint", "live.ctraderapi.com", "non-demo endpoint"),
                                ("broker_identity", "OTHERBROKER_DEMO", "non-Pepperstone identity")):
    try:
        tc.validate_preflight_binding({**_FAKE_BINDING, bad_key: bad_val})
        ok(False, f"binding with {label} must fail")
    except ValueError:
        ok(True, f"binding with {label} -> fail-closed")

# ================================================================================================
# 18. RESPONSE-TIMEOUT FAIL-CLOSED (Chuck correction 2) — a timeout NEVER leaves the transport READY
# ================================================================================================
t18, c18, b18 = fresh(fill_on_open=True, owned_orders={"O9": {"order_id": "O9"}})
t18.bring_up()
c18.lose_after_send = True
t18.response_timeout_s = 0.3
cmid18 = _open_cmid(t18)
r18 = t18.send_open(SPEC)
ok(r18 is None and any(a["kind"] == "OUTCOME_UNKNOWN_TIMEOUT" for a in t18.alarms),
   "response timeout -> OUTCOME_UNKNOWN (ambiguous, no auto-resend)")
ok(t18.cstate.state == st.AuthState.DISCONNECTED and not t18.cstate.reconciled,
   "timed-out request leaves the transport fail-closed (DISCONNECTED), never READY")
ok(t18.corr.status(cmid18) == st.Correlation.OUTCOME_UNKNOWN,
   "timed-out correlation marked OUTCOME_UNKNOWN and RETAINED")
try:
    t18.cancel_pending("O9")
    ok(False, "another action after a timeout must be refused")
except st.StateError:
    ok(True, "a DIFFERENT action is refused after the timeout (no sends until re-auth + reconcile)")
c18.lose_after_send = False
t18.response_timeout_s = 1.0
ok(t18.reconnect(sleep=lambda s: None) and t18.cstate.state == st.AuthState.READY,
   "after timeout: reconnect completes full auth + reconciliation -> READY")
rc18 = t18.cancel_pending("O9")
last_recon18 = len(b18.seen) - 1 - b18.seen[::-1].index(MsgType.RECONCILE_REQ)
last_cancel18 = len(b18.seen) - 1 - b18.seen[::-1].index(MsgType.CANCEL_PENDING_REQ)
ok(rc18["status"] == T.Result.OK and last_recon18 < last_cancel18,
   "actions resume only AFTER reconciliation (reconcile precedes the next action)")
ok(t18.corr.status(cmid18) == st.Correlation.OUTCOME_UNKNOWN,
   "the timed-out correlation is never forgotten or automatically resent")


# boundary race: a response arriving AT the timeout boundary is resolved EXACTLY once —
# either consumed as the RESPONSE (transport stays READY) or the timeout owns it
# (OUTCOME_UNKNOWN + fail-closed) — never both, never neither.
class _DelayedResponseConnector(fake_wire.FakeConnector):
    delay_s = 0.0
    armed = False

    def send(self, frame_bytes):
        if not self.armed:
            return super().send(frame_bytes)
        self.sent_frames += 1
        envs = [self.codec.decode(p) for p in framing.Deframer().feed(frame_bytes)]

        def deliver():
            import time as _time
            _time.sleep(self.delay_s)
            with self._inbox_lock:
                for env in envs:
                    for resp in self.broker.handle(env):
                        self._inbox.extend(framing.frame(self.codec.encode(resp)))

        threading.Thread(target=deliver, daemon=True).start()


race_ok, outcomes = True, []
for delay in (0.02, 0.10, 0.14, 0.16, 0.30):
    bx = fake_wire.FakeBroker(fill_on_open=True)
    cx = _DelayedResponseConnector(bx)
    tx = T.ConnectedTransport(connector=cx, codec=CODEC, credential_provider=FAKE_CREDS,
                              policy=T.test_only_policy(), clock=FakeClock())
    tx.response_timeout_s = 0.15
    tx.bring_up()
    cx.armed = True
    cx.delay_s = delay
    cmid_x = _open_cmid(tx)
    rx = tx.send_open(SPEC)
    status_x = tx.corr.status(cmid_x)
    if rx is not None:                                       # response consumed -> stays READY
        this_ok = (status_x == st.Correlation.RESOLVED
                   and tx.cstate.state == st.AuthState.READY and rx.get("order_id"))
        outcomes.append("RESPONSE")
    else:                                                    # timeout owned it -> fail-closed
        this_ok = (status_x == st.Correlation.OUTCOME_UNKNOWN
                   and tx.cstate.state == st.AuthState.DISCONNECTED)
        outcomes.append("UNKNOWN")
    race_ok = race_ok and this_ok
ok(race_ok and "RESPONSE" in outcomes and "UNKNOWN" in outcomes,
   f"timeout-boundary race: exactly-once resolution at every delay ({'/'.join(outcomes)}); "
   f"both sides of the boundary exercised")

egress_guard.uninstall_test_egress_guard()

if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    print(f"PASS {PASS} connected-transport checks")
