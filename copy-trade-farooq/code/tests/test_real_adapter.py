"""Real request adapter + network-send gate — FAIL-CLOSED. Fake/offline transport only. Every attempt
terminates before network transmission (the gate always has >=1 failing check), so the real protobuf
is never constructed and transport.send is never called. NO broker order is sent."""
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
import order_request_adapter as ADAPTER
import order_transport as OT
import network_send as NS
import one_shot_permit as OSP
import volume_terms as VT
from models import AccountSnapshot, ApprovedDemoOrderRequest

NOW = 1_800_000_000_000


def acct(**o):
    d = dict(account_id=4257941, is_live=False, balance=10000.0, currency="GBP", trade_scope="trade",
             environment="DEMO")
    d.update(o)
    return AccountSnapshot(**d)


def approved(**o):
    cid = OT.make_client_order_id("sig-1", "demoprop-x", 4257941, 41)
    d = dict(signal_id="sig-1", proposal_id="demoprop-x", client_order_id=cid, account_id=4257941,
             symbol_id=41, symbol_name="XAUUSD", trade_side="BUY", order_type="LIMIT",
             volume_raw_protocol=1200, volume_units_underlying=12, volume_lots=0.12, limit_price=4116.55,
             stop_price=None, stop_loss=4111.55, take_profit=None, label="ST-FAROUK",
             comment="signal=sig-1;proposal=demoprop-x;leg=1", planned_stop_loss_risk=47.40,
             risk_pct=0.005, expected_margin=390.25, created_at_ms=NOW)
    d.update(o)
    return ApprovedDemoOrderRequest(**d)


class FakeTransport:
    def __init__(self, existing=None):
        self.existing, self.sends = existing, []

    def find_order_by_client_id(self, cid):
        return self.existing

    def send(self, req):
        self.sends.append(req)                              # MUST never be called this phase
        return {"status": "ACCEPTED"}


def _permit(app):
    return OSP.make_permit(account_id=app.account_id, signal_id=app.signal_id,
                           proposal_id=app.proposal_id, client_order_id=app.client_order_id, now_ms=NOW)


def _send(app, ft, permit="valid", store=None, **over):
    store = store or OSP.PermitStore()
    permit = _permit(app) if permit == "valid" else permit
    kw = dict(approved=app, transport=ft, account=acct(), endpoint_host="demo.ctraderapi.com",
              endpoint_port=5035, permission_scope="SCOPE_TRADE", permit=permit, permit_store=store,
              quote_fresh=True, signal_fresh=True, proposal_unexpired=True, replay_status="LIVE_FRESH",
              human_approval_completed=True, order_sending_enabled=True, now_ms=NOW)
    kw.update(over)
    return NS.send_new_order(**kw)


def _blocked(r, ft):
    assert r["transmitted"] is False and r["protobuf_constructed"] is False
    assert r["final_state"] == "NO_ORDER_SENT" and ft.sends == []


# ---- adapter exists / immutable values / market unsupported ----
def test_real_adapter_exists():
    assert callable(ADAPTER.build_new_order_request) and callable(ADAPTER.serialize_fields)


def test_adapter_consumes_immutable_values_no_recompute():
    f = ADAPTER.serialize_fields(approved())
    a = approved()
    assert f["ctidTraderAccountId"] == a.account_id and f["volume"] == a.volume_raw_protocol
    assert f["limitPrice"] == a.limit_price and f["stopLoss"] == a.stop_loss
    assert f["clientOrderId"] == a.client_order_id and f["label"] == "ST-FAROUK"


def test_market_order_unsupported():
    try:
        ADAPTER.serialize_fields(approved(order_type="MARKET")); assert False
    except ADAPTER.UnsupportedOrder as e:
        assert str(e) == "UNSUPPORTED_ORDER_TYPE"


def test_volume_conversion_proof():
    assert VT.breakdown(1200, lot_size_raw_protocol=10000) == {
        "raw_protocol_volume": 1200, "underlying_xau_units": 12.0, "displayed_lots": 0.12}


# ---- network gate fail-closed (send never reached) ----
def test_order_sending_disabled_blocks_transmission():
    ft = FakeTransport()
    _blocked(_send(approved(), ft, order_sending_enabled=False), ft)


def test_missing_scope_trade_blocks():
    ft = FakeTransport()
    _blocked(_send(approved(), ft, permission_scope="SCOPE_VIEW"), ft)


def test_wrong_account_blocks():
    ft = FakeTransport()
    _blocked(_send(approved(account_id=9999), ft, account=acct(account_id=9999)), ft)


def test_live_endpoint_and_islive_block():
    ft = FakeTransport()
    _blocked(_send(approved(), ft, endpoint_host="live.ctraderapi.com"), ft)
    ft2 = FakeTransport()
    _blocked(_send(approved(), ft2, account=acct(is_live=True)), ft2)


def test_missing_permit_blocks():
    ft = FakeTransport()
    _blocked(_send(approved(), ft, permit=None), ft)


def test_expired_permit_blocks():
    ft = FakeTransport()
    app = approved()
    old = OSP.make_permit(account_id=app.account_id, signal_id=app.signal_id, proposal_id=app.proposal_id,
                          client_order_id=app.client_order_id, now_ms=NOW - OSP.PERMIT_TTL_MS - 10000)
    _blocked(_send(app, ft, permit=old), ft)


def test_consumed_permit_blocks():
    ft = FakeTransport()
    app = approved()
    store = OSP.PermitStore()
    permit = _permit(app)
    store.consume(permit.permit_id)                         # already used
    _blocked(_send(app, ft, permit=permit, store=store), ft)


def test_replay_and_stale_block():
    ft = FakeTransport()
    _blocked(_send(approved(), ft, replay_status="REPLAY_VALIDATION_ONLY"), ft)
    ft2 = FakeTransport()
    _blocked(_send(approved(), ft2, signal_fresh=False), ft2)


def test_duplicate_broker_order_blocks():
    ft = FakeTransport(existing={"broker_order_id": 5})
    _blocked(_send(approved(), ft), ft)


def test_disable_file_blocks(tmp_path=None):
    import tempfile
    tmp = tempfile.mkdtemp()
    try:
        df = os.path.join(tmp, "DEMO_EXECUTION_DISABLED"); open(df, "w").write("x")
        ft = FakeTransport()
        _blocked(_send(approved(), ft, disable_path=df), ft)
    finally:
        import shutil
        shutil.rmtree(tmp, ignore_errors=True)


# ---- safety ----
def test_no_amend_close_cancel_amendorder_constructor():
    for pth in glob.glob(os.path.join(_DE, "*.py")):
        if os.path.basename(pth) == "management_adapter.py":
            continue  # authorised gated management adapter (this build)
        src = open(pth, encoding="utf-8").read()
        for bad in ("ProtoOAAmendPositionSLTPReq", "ProtoOAClosePositionReq", "ProtoOACancelOrderReq",
                    "ProtoOAAmendOrderReq"):
            assert bad not in src


def test_no_secret_in_gate_output():
    ft = FakeTransport()
    r = _send(approved(), ft, order_sending_enabled=False)
    blob = str(r).lower()
    for leak in ("access_token", "refresh_token", "bearer", "secret", "clientsecret"):
        assert leak not in blob


def test_locks_false():
    cfg = open(os.path.join(_ROOT, "config.py"), encoding="utf-8").read()
    cc = open(os.path.join(_ROOT, "ctrader_config.py"), encoding="utf-8").read()
    assert "EXECUTION_ENABLED = False" in cfg and "CTRADER_EXECUTION_ENABLED = False" in cc
    assert CFG.ORDER_SENDING_ENABLED is False
