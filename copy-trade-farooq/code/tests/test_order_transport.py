"""Demo-order transport tests — FAKE cTrader transport only. NO broker order is ever sent.
ORDER_SENDING_ENABLED stays False; tests pass an explicit override to exercise the fake accept/
reject/timeout/reconcile paths."""
from __future__ import annotations
import glob
import os
import sys
import tempfile

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DE = os.path.join(_ROOT, "campaign_extractor", "demo_executor")
for p in (_ROOT, _DE):
    if p not in sys.path:
        sys.path.insert(0, p)

import config as CFG
import order_transport as OT
import submission_firewall as SFW
import expected_margin as EM
import trade_preflight as TP
import volume_terms as VT
from audit_db import AuditDB
from models import AccountSnapshot, ApprovedDemoOrderRequest

NOW = 1_800_000_000_000
CID = OT.make_client_order_id("sig-1", "demoprop-x", 4257941, 41)


def acct(**o):
    d = dict(account_id=4257941, is_live=False, balance=10000.0, currency="GBP", trade_scope="trade",
             environment="DEMO")
    d.update(o)
    return AccountSnapshot(**d)


def approved(**o):
    d = dict(signal_id="sig-1", proposal_id="demoprop-x", client_order_id=CID, account_id=4257941,
             symbol_id=41, symbol_name="XAUUSD", trade_side="BUY", order_type="LIMIT",
             volume_raw_protocol=1200, volume_units_underlying=12, volume_lots=0.12, limit_price=4116.55,
             stop_price=None, stop_loss=4111.55, take_profit=None, label="ST-FAROUK",
             comment="signal=sig-1;proposal=demoprop-x;leg=1", planned_stop_loss_risk=47.40,
             risk_pct=0.005, expected_margin=390.25, created_at_ms=NOW)
    d.update(o)
    return ApprovedDemoOrderRequest(**d)


class FakeTransport:
    def __init__(self, mode="ACCEPTED", returned=None, existing=None, broker_order_id=77001,
                 position_id=None, error_code="MARKET_CLOSED", reconcile_result=None):
        self.mode, self.returned, self.existing = mode, returned, existing
        self.broker_order_id, self.position_id, self.error_code = broker_order_id, position_id, error_code
        self.reconcile_result = reconcile_result
        self.new_order_calls = []

    def find_order_by_client_id(self, cid):
        return self.existing                              # pre-send idempotency lookup

    def new_order(self, fields):
        self.new_order_calls.append(fields)
        if self.mode == "TIMEOUT":
            return {"status": "TIMEOUT"}
        if self.mode == "REJECTED":
            return {"status": "REJECTED", "error_code": self.error_code, "error_description": "demo reject"}
        return {"status": "ACCEPTED", "broker_order_id": self.broker_order_id,
                "position_id": self.position_id, "returned": self.returned}

    def reconcile(self, cid):
        return self.reconcile_result                      # post-timeout reconcile (separate from pre-send)


def _submit(app, transport, tmp=None, **over):
    kw = dict(transport=transport, account=acct(), endpoint_host="demo.ctraderapi.com",
              permission_scope="SCOPE_TRADE", quote_fresh=True, signal_fresh=True, proposal_unexpired=True,
              expected_margin_ok=True, human_confirmed_signal=True, provider_evidence_displayed=True,
              operator_approval_completed=True, order_sending_enabled=True, now_ms=NOW,
              audit=(AuditDB(os.path.join(tmp, "a.db")) if tmp else None))
    kw.update(over)
    return OT.submit(app, **kw)


def _run(fn):
    tmp = tempfile.mkdtemp(prefix="ot_")
    try:
        return fn(tmp)
    finally:
        import shutil
        shutil.rmtree(tmp, ignore_errors=True)


def _matching_returned():
    return {"symbol": "XAUUSD", "direction": "BUY", "order_type": "LIMIT", "volume": 1200,
            "entry": 4116.55, "stop": 4111.55, "take_profit": None, "label": "ST-FAROUK",
            "comment": "signal=sig-1;proposal=demoprop-x;leg=1", "client_order_id": CID}


# ---- firewall blocks (one failure blocks) ----
def _blocked(over_submit=None, **fw_over):
    ft = FakeTransport()
    r = _submit(approved(**{k: v for k, v in fw_over.items() if k in approved().__dict__}), ft,
                **(over_submit or {}))
    return r, ft


def test_view_only_permission_blocks():
    r, ft = _blocked(over_submit={"permission_scope": "view-only"})
    assert not r["sent"] and r["reason"] == "FIREWALL_BLOCKED" and ft.new_order_calls == []


def test_order_sending_disabled_blocks_and_not_called():
    ft = FakeTransport()
    r = _submit(approved(), ft, order_sending_enabled=False)
    assert not r["sent"] and r["final_state"] == "NO_ORDER_SENT" and ft.new_order_calls == []


def test_live_endpoint_rejected():
    r, ft = _blocked(over_submit={"endpoint_host": "live.ctraderapi.com"})
    assert not r["sent"] and ft.new_order_calls == []


def test_islive_true_rejected():
    ft = FakeTransport()
    r = _submit(approved(), ft, account=acct(is_live=True))
    assert not r["sent"] and ft.new_order_calls == []


def test_wrong_account_rejected():
    ft = FakeTransport()
    r = _submit(approved(account_id=9999), ft, account=acct(account_id=9999))
    assert not r["sent"] and ft.new_order_calls == []


def test_disable_file_blocks():
    def f(tmp):
        df = os.path.join(tmp, "DEMO_EXECUTION_DISABLED"); open(df, "w").write("x")
        ft = FakeTransport()
        r = _submit(approved(), ft, disable_path=df)
        assert not r["sent"] and ft.new_order_calls == []
    _run(f)


def test_non_xauusd_rejected():
    ft = FakeTransport()
    r = _submit(approved(symbol_name="BTCUSD"), ft)
    assert not r["sent"] and ft.new_order_calls == []


def test_market_order_rejected():
    ft = FakeTransport()
    r = _submit(approved(order_type="MARKET"), ft)
    assert not r["sent"] and ft.new_order_calls == []


def test_missing_stop_rejected():
    ft = FakeTransport()
    r = _submit(approved(stop_loss=None), ft)
    assert not r["sent"] and ft.new_order_calls == []


def test_risk_above_one_percent_rejected():
    ft = FakeTransport()
    r = _submit(approved(risk_pct=0.02), ft)
    assert not r["sent"] and ft.new_order_calls == []


def test_stale_signal_quote_expired_margin_replay_blocked():
    for over in ({"signal_fresh": False}, {"quote_fresh": False}, {"proposal_unexpired": False},
                 {"expected_margin_ok": False}):
        ft = FakeTransport()
        r = _submit(approved(), ft, **over)
        assert not r["sent"] and ft.new_order_calls == []
    # a replay-validation screenshot is not a fresh signal -> blocked
    ft = FakeTransport()
    assert not _submit(approved(), ft, signal_fresh=False)["sent"] and ft.new_order_calls == []


def test_duplicate_broker_order_prevents_resubmission():
    ft = FakeTransport(existing={"broker_order_id": 5})
    r = _submit(approved(), ft)
    assert not r["sent"] and ft.new_order_calls == []       # existing order -> blocked


def test_hotkey_cannot_bypass_firewall():
    # even with operator approval "completed", ORDER_SENDING_ENABLED=False blocks everything
    ft = FakeTransport()
    r = _submit(approved(), ft, order_sending_enabled=False, operator_approval_completed=True)
    assert not r["sent"] and r["final_state"] == "NO_ORDER_SENT" and ft.new_order_calls == []


# ---- fake transport accept / reject / timeout / mismatch ----
def test_accepted_via_fake_transport():
    def f(tmp):
        ft = FakeTransport(mode="ACCEPTED", returned=_matching_returned(), broker_order_id=77001)
        r = _submit(approved(), ft, tmp=tmp)
        assert r["accepted"] and r["final_state"] == "ORDER_ACCEPTED" and r["broker_order_id"] == 77001
        assert len(ft.new_order_calls) == 1
    _run(f)


def test_rejected_via_fake_transport():
    ft = FakeTransport(mode="REJECTED", error_code="TRADING_DISABLED")
    r = _submit(approved(), ft)
    assert r["final_state"] == "ORDER_REJECTED" and r["error_code"] == "TRADING_DISABLED" and r["replacement_allowed"]


def test_timeout_triggers_reconcile_not_retry():
    # no pre-existing order (firewall passes) -> send -> TIMEOUT -> reconcile finds it landed
    ft = FakeTransport(mode="TIMEOUT", existing=None, reconcile_result={"broker_order_id": 9})
    r = _submit(approved(), ft)
    assert r["final_state"] == "ORDER_RECONCILIATION_REQUIRED" and r["no_retry"] is True
    assert len(ft.new_order_calls) == 1                     # sent once, NOT retried
    assert r["reconciled"] == {"broker_order_id": 9}


def test_broker_state_mismatch_reported():
    bad = _matching_returned(); bad["volume"] = 999
    ft = FakeTransport(mode="ACCEPTED", returned=bad)
    r = _submit(approved(), ft)
    assert r["final_state"] == "BROKER_STATE_MISMATCH" and "volume" in r["mismatch_fields"] and r["manual_review_required"]


# ---- preflight / margin / volume / ids ----
def test_trade_permission_preflight_mock_passes():
    v = TP.preflight_trade_permission(fetch_account_state=lambda: {
        "account_id": 4257941, "is_live": False, "currency": "GBP", "balance": 10000.0,
        "permission_scope": "SCOPE_TRADE", "environment": "DEMO"}, endpoint_host="demo.ctraderapi.com")
    assert v["ok"] and v["token_value_exposed"] is False and v["no_live_fallback"] is True


def test_view_only_preflight_fails():
    v = TP.preflight_trade_permission(fetch_account_state=lambda: {
        "account_id": 4257941, "is_live": False, "currency": "GBP", "balance": 10000.0,
        "permission_scope": "view-only", "environment": "DEMO"}, endpoint_host="demo.ctraderapi.com")
    assert not v["ok"] and "SCOPE_NOT_TRADE" in v["issues"]


def test_expected_margin_verify_and_failure():
    ok = EM.verify(get_margin_res=lambda: {"buy": 39025, "sell": 39025, "moneyDigits": 2},
                   side="BUY", request_ts_ms=NOW, now_ms=NOW)
    assert ok["ok"] and ok["converted_display_value"] == 390.25 and ok["source"] == "ProtoOAExpectedMarginRes"
    assert EM.verify(get_margin_res=lambda: None, side="BUY", request_ts_ms=NOW)["ok"] is False


def test_volume_conversion_correct():
    b = VT.breakdown(1200, lot_size_raw_protocol=10000)
    assert b == {"raw_protocol_volume": 1200, "underlying_xau_units": 12.0, "displayed_lots": 0.12}
    t = VT.symbol_terms(lot_size_raw_protocol=10000, min_volume_raw_protocol=100, step_volume_raw_protocol=100)
    assert t["min"]["underlying_xau_units"] == 1.0 and t["one_lot"]["underlying_xau_units"] == 100.0


def test_client_order_id_deterministic():
    assert OT.make_client_order_id("sig-1", "demoprop-x", 4257941, 41) == CID and CID.startswith("cli-")


# ---- safety ----
def test_no_amend_close_cancel_constructor():
    for pth in glob.glob(os.path.join(_DE, "*.py")):
        if os.path.basename(pth) == "management_adapter.py":
            continue  # authorised gated management adapter (this build)
        src = open(pth, encoding="utf-8").read()
        for bad in ("ProtoOAAmendPositionSLTPReq", "ProtoOAClosePositionReq", "ProtoOACancelOrderReq",
                    "ProtoOAAmendOrderReq"):
            assert bad not in src


def test_locks_false_and_sending_disabled():
    cfg = open(os.path.join(_ROOT, "config.py"), encoding="utf-8").read()
    cc = open(os.path.join(_ROOT, "ctrader_config.py"), encoding="utf-8").read()
    assert "EXECUTION_ENABLED = False" in cfg and "CTRADER_EXECUTION_ENABLED = False" in cc
    assert CFG.ORDER_SENDING_ENABLED is False
    assert CFG.DEMO_ENDPOINT_HOST == "demo.ctraderapi.com"
