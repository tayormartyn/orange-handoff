"""Item-1 tests: the REAL ProtoCodec against the GENERATED cTrader message classes. Runs under
.venv-ctrader (real protobuf). NO socket to cTrader — pure in-memory encode/decode + a fake-wire
lifecycle. Covers every family + framing + fail-closed (mismatch/malformed/unknown) + clientMsgId.

Run:  .venv-ctrader/Scripts/python.exe -m demo_lane.connected_transport.tests_proto_codec
"""
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
FAROUK_PILOT = os.path.dirname(os.path.dirname(HERE))
if FAROUK_PILOT not in sys.path:
    sys.path.insert(0, FAROUK_PILOT)

from demo_lane.connected_transport import (                     # noqa: E402
    egress_guard, fake_wire, framing, proto_codec, state as st, transport as T)
from demo_lane.connected_transport.framing import Envelope, MsgType, FramingError   # noqa: E402
from demo_lane.connected_transport import credentials as cred   # noqa: E402

egress_guard.install_test_egress_guard()                        # no socket may leave, even here
PASS = 0


def ok(cond, name):
    global PASS
    assert cond, f"FAIL: {name}"
    PASS += 1


C = proto_codec.ProtoCodec()
ok(C.IS_FAKE is False, "ProtoCodec is the REAL codec (IS_FAKE False)")


def rt(env):
    """encode via real protobuf -> decode via real protobuf."""
    return C.decode(C.encode(env))


# ---- per-family roundtrip through real ProtoMessage + generated classes -----------------------
d = rt(Envelope(MsgType.APP_AUTH_REQ, "m1", {"client_id": "cid", "client_secret": "sec"}))
ok(d.msg_type == MsgType.APP_AUTH_REQ and d.client_msg_id == "m1", "APP_AUTH_REQ roundtrip + cmid")
ok(rt(Envelope(MsgType.APP_AUTH_RES, "m", {})).msg_type == MsgType.APP_AUTH_RES, "APP_AUTH_RES roundtrip")

d = rt(Envelope(MsgType.ACCOUNT_LIST_REQ, "m", {"access_token": "tok"}))
ok(d.msg_type == MsgType.ACCOUNT_LIST_REQ, "ACCOUNT_LIST_REQ (GetAccountListByAccessToken) roundtrip")
d = rt(Envelope(MsgType.ACCOUNT_LIST_RES, "m",
                {"accounts": [{"ctidTraderAccountId": 1_000_001, "isLive": False}],
                 "permissionScope": "SCOPE_TRADE"}))
ok(d.msg_type == MsgType.ACCOUNT_LIST_RES and d.payload["accounts"][0]["ctidTraderAccountId"] == 1_000_001
   and d.payload["accounts"][0]["isLive"] is False and d.payload["permissionScope"] == "SCOPE_TRADE",
   "ACCOUNT_LIST_RES roundtrip (account id + isLive + scope preserved)")

d = rt(Envelope(MsgType.ACCOUNT_AUTH_REQ, "m", {"ctid": 1_000_001, "access_token": "tok"}))
ok(d.msg_type == MsgType.ACCOUNT_AUTH_REQ and d.payload["ctid"] == 1_000_001, "ACCOUNT_AUTH_REQ roundtrip")
ok(rt(Envelope(MsgType.ACCOUNT_AUTH_RES, "m", {})).msg_type == MsgType.ACCOUNT_AUTH_RES, "ACCOUNT_AUTH_RES roundtrip")
ok(rt(Envelope(MsgType.HEARTBEAT, "m", {})).msg_type == MsgType.HEARTBEAT, "HEARTBEAT roundtrip")

d = rt(Envelope(MsgType.RECONCILE_REQ, "m", {"ctid": 1_000_001}))
ok(d.msg_type == MsgType.RECONCILE_REQ and d.payload["ctid"] == 1_000_001, "RECONCILE_REQ roundtrip")
d = rt(Envelope(MsgType.RECONCILE_RES, "m",
                {"ctid": 1_000_001, "orders": {"5": {"order_id": 5}}, "positions": {"9": {"position_id": 9}}}))
ok(d.msg_type == MsgType.RECONCILE_RES and "5" in d.payload["orders"] and "9" in d.payload["positions"],
   "RECONCILE_RES roundtrip (orders + positions)")

d = rt(Envelope(MsgType.OPEN_LIMIT_REQ, "mo",
                {"account_id": 1_000_001, "symbol_id": 42, "trade_side": "SELL", "volume": 100,
                 "limit_price": 4161.0, "stop_loss": 4187.0, "expiration_timestamp": 99_999_999,
                 "client_order_id": "ORG-xyz"}))
ok(d.msg_type == MsgType.OPEN_LIMIT_REQ and d.payload["trade_side"] == "SELL"
   and d.payload["volume"] == 100 and d.payload["stop_loss"] == 4187.0,
   "LIMIT-open roundtrip via the ACCEPTED mapper (side/volume/stop preserved)")

d = rt(Envelope(MsgType.CANCEL_PENDING_REQ, "m", {"account_id": 1_000_001, "order_id": 12345}))
ok(d.msg_type == MsgType.CANCEL_PENDING_REQ and d.payload["order_id"] == 12345, "cancel-pending roundtrip")
d = rt(Envelope(MsgType.CLOSE_REDUCE_REQ, "m",
                {"account_id": 1_000_001, "position_id": 777, "volume": 50}))
ok(d.msg_type == MsgType.CLOSE_REDUCE_REQ and d.payload["position_id"] == 777 and d.payload["volume"] == 50,
   "close-reduce roundtrip via the ACCEPTED mapper")
d = rt(Envelope(MsgType.AMEND_STOP_REQ, "m", {"account_id": 1_000_001, "order_id": 888, "stop_loss": 4190.0}))
ok(d.msg_type == MsgType.AMEND_STOP_REQ and d.payload["stop_loss"] == 4190.0, "allowed stop-mod roundtrip")

d = rt(Envelope(MsgType.ORDER_ACK, "ma", {"order_id": 111, "client_order_id": "ORG-c", "stop_loss": 4187.0}))
ok(d.msg_type == MsgType.ORDER_ACK and d.payload["order_id"] == 111 and d.payload["stop_accepted"] is True,
   "ORDER_ACK (ExecutionEvent ORDER_ACCEPTED) roundtrip")
d = rt(Envelope(MsgType.ORDER_FILL, "mf", {"order_id": 111, "filled_volume": 100, "position_id": 222}))
ok(d.msg_type == MsgType.ORDER_FILL and d.payload["filled_volume"] == 100 and d.payload["position_id"] == 222,
   "ORDER_FILL (ExecutionEvent ORDER_FILLED) roundtrip")
d = rt(Envelope(MsgType.ORDER_REJECT, "mr", {"why": "no funds", "order_id": 111}))
ok(d.msg_type == MsgType.ORDER_REJECT and "no funds" in d.payload["why"], "ORDER_REJECT (OrderErrorEvent) roundtrip")
d = rt(Envelope(MsgType.ERROR_RES, "me", {"why": "maintenance", "errorCode": "E1"}))
ok(d.msg_type == MsgType.ERROR_RES and "maintenance" in d.payload["why"], "ERROR_RES roundtrip")
# a non-order execution event -> EXECUTION_EVENT with a subtype (transport treats unknown subtype fail-closed)
d = rt(Envelope(MsgType.EXECUTION_EVENT, "mx", {"subtype": "SWAP"}))
ok(d.msg_type == MsgType.EXECUTION_EVENT and d.payload["subtype"] == "SWAP", "generic ExecutionEvent roundtrip")

# ---- framing over real protobuf bytes: fragmented + combined ----------------------------------
b1 = framing.frame(C.encode(Envelope(MsgType.HEARTBEAT, "h", {})))
b2 = framing.frame(C.encode(Envelope(MsgType.APP_AUTH_RES, "a", {})))
ok([C.decode(p).msg_type for p in framing.Deframer().feed(b1 + b2)] == [MsgType.HEARTBEAT, MsgType.APP_AUTH_RES],
   "combined framing over real protobuf -> both messages")
dfr = framing.Deframer(); collected = []
for byte in b1:
    collected += dfr.feed(bytes([byte]))
ok(len(collected) == 1 and C.decode(collected[0]).msg_type == MsgType.HEARTBEAT,
   "fragmented framing over real protobuf -> reassembled")

# ---- clientMsgId preservation + correlation ---------------------------------------------------
cmid = st.CorrelationRegistry.client_msg_id(("open", "ORG-xyz"))
ok(C.decode(C.encode(Envelope(MsgType.OPEN_LIMIT_REQ, cmid,
   {"account_id": 1_000_001, "symbol_id": 42, "trade_side": "BUY", "volume": 100, "limit_price": 1.0,
    "stop_loss": 0.5, "expiration_timestamp": 1, "client_order_id": "c"}))).client_msg_id == cmid,
   "clientMsgId preserved end-to-end (correlation intact)")

# ---- fail-closed: malformed / payloadType mismatch / unknown payload --------------------------
try:
    C.decode(b"\x08\x80\x80")                              # truncated varint -> not a ProtoMessage
    ok(False, "malformed must fail closed")
except FramingError:
    ok(True, "malformed ProtoMessage -> FramingError (fail-closed)")

pb = proto_codec._load()
bad_inner = pb["ErrorRes"](errorCode="X", description="Y"); bad_inner.payloadType = pb["PT"].PROTO_OA_ERROR_RES
wrap = pb["ProtoMessage"](payloadType=pb["PT"].PROTO_OA_APPLICATION_AUTH_RES)  # envelope says AUTH_RES
wrap.payload = bad_inner.SerializeToString()                                   # payload is ERROR_RES
try:
    C.decode(wrap.SerializeToString())
    ok(False, "payloadType mismatch must fail closed")
except FramingError:
    ok(True, "payloadType mismatch (envelope vs payload) -> FramingError (fail-closed)")

unk = pb["ProtoMessage"](payloadType=9999, clientMsgId="u")
env_unknown = C.decode(unk.SerializeToString())
ok(env_unknown.msg_type.startswith("UNKNOWN_PAYLOAD") and env_unknown.msg_type not in framing.KNOWN_INBOUND,
   "unmapped payloadType -> UNKNOWN_PAYLOAD envelope (not KNOWN_INBOUND -> transport fail-closes)")

# ---- lifecycle over the REAL codec + fake wire (no socket to cTrader) --------------------------
broker = fake_wire.FakeBroker()
conn = fake_wire.FakeConnector(broker, codec=C)              # connector uses the SAME real codec
t = T.ConnectedTransport(connector=conn, codec=C,
                         credential_provider=cred.FakeCredentialProvider(ctid=1_000_001),
                         policy=T.test_only_policy())
ok(t.bring_up() == st.AuthState.READY,
   "REAL codec drives the full state machine to READY (app-auth->list->validate->acct-auth->reconcile)")
ok(MsgType.ACCOUNT_LIST_REQ in broker.seen and MsgType.ACCOUNT_AUTH_REQ in broker.seen,
   "account-list AND account-auth exchanged as real ProtoMessages over the fake wire")

egress_guard.uninstall_test_egress_guard()

if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    print(f"PASS {PASS} proto-codec checks")
