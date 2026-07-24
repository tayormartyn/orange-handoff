"""Final pre-activation tests — field limits, all-in risk, trade preflight, one-shot permit.
NO order is sent; ORDER_SENDING_ENABLED stays False."""
from __future__ import annotations
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
import risk_presentation as RP
import trade_preflight as TP
import one_shot_permit as OSP
from models import ApprovedDemoOrderRequest

NOW = 1_800_000_000_000


def approved(label="ST-FAROUK", comment="signal=s;proposal=p;leg=1"):
    cid = OT.make_client_order_id("sig-1", "demoprop-x", 4257941, 41)
    return ApprovedDemoOrderRequest("sig-1", "demoprop-x", cid, 4257941, 41, "XAUUSD", "BUY", "LIMIT",
                                    1200, 12, 0.12, 4116.55, None, 4111.55, None, label, comment,
                                    47.40, 0.005, 390.25, NOW)


def _state(**o):
    d = dict(account_id=4257941, is_live=False, currency="GBP", balance=10000.0,
             permission_scope="SCOPE_TRADE", environment="DEMO")
    d.update(o)
    return lambda: d


# 1 — official vs internal field limits
def test_official_and_internal_limits_distinguished():
    r = OT.field_limit_report()
    assert r["official_contract_max"] == {"label": 100, "comment": 512, "clientOrderId": 50}
    assert r["internal_conservative_limit"]["label"] == 30 and r["internal_conservative_limit"]["comment"] == 255
    assert "INTERNAL_CONSERVATIVE_LIMIT" in r["internal_conservative_limit"]["note"]
    # a 40-char label is within the official 100 but over our internal 30
    assert OT.validate_field_lengths(approved(label="X" * 40)) == ["LABEL_OVER_INTERNAL_CONSERVATIVE_LIMIT"]
    assert OT.validate_field_lengths(approved()) == []


# 2 — all-in risk never hides commission exclusion
def test_all_in_risk_does_not_hide_commission():
    r = RP.all_in_risk(risk_budget=50.0, planned_stop_loss_risk=47.40)          # no commission known
    assert r["COMMISSION_ESTIMATE_STATUS"] == "UNKNOWN" and r["strict_all_in_claim_allowed"] is False
    assert r["remaining_risk_headroom"] == 2.60 and r["headroom_covers_commission"] is None
    assert r["PLANNED_STOP_LOSS_RISK"] == 47.40 and "Commission EXCLUDED" in r["note"]
    # with a conservative reserve applied, the strict claim is allowed and all-in grows
    rr = RP.all_in_risk(risk_budget=50.0, planned_stop_loss_risk=47.40, use_reserve=True)
    assert rr["CONSERVATIVE_COMMISSION_RESERVE"] == 5.0 and rr["ALL_IN_ESTIMATED_RISK"] == 52.40
    assert rr["strict_all_in_claim_allowed"] is True


# 3 / 4 — scope preflight
def test_scope_view_blocked_and_trade_passes():
    view = TP.preflight_trade_permission(fetch_account_state=_state(permission_scope="SCOPE_VIEW"),
                                         endpoint_host="demo.ctraderapi.com")
    assert not view["ok"] and "SCOPE_NOT_TRADE" in view["issues"]
    trade = TP.preflight_trade_permission(fetch_account_state=_state(), endpoint_host="demo.ctraderapi.com")
    assert trade["ok"] and trade["permission_scope"] == "SCOPE_TRADE"


# 5 — secrets never in preflight/readiness payloads
def test_no_secret_in_payloads():
    v = TP.preflight_trade_permission(fetch_account_state=_state(), endpoint_host="demo.ctraderapi.com")
    blob = str(v).lower()
    assert v["token_value_exposed"] is False
    for leak in ("access_token", "refresh_token", "bearer", "secret", "clientsecret"):
        assert leak not in blob
    rr = TP.one_order_readiness_preflight(fetch_account_state=_state(), symbol_ok=True, balance_ok=True,
                                          volume_metadata_ok=True, expected_margin_healthy=True,
                                          endpoint_host="demo.ctraderapi.com")
    assert rr["token_value_exposed"] is False and rr["order_constructed"] is False and rr["NO_ORDER_SENT"] is True
    assert rr["all_ok"] and rr["checks"]["endpoint_port"] == 5035


# 6 / 7 — wrong account / live endpoint rejected
def test_wrong_account_and_live_endpoint_rejected():
    wa = TP.preflight_trade_permission(fetch_account_state=_state(account_id=9999),
                                       endpoint_host="demo.ctraderapi.com")
    assert not wa["ok"] and "ACCOUNT_NOT_ALLOWLISTED" in wa["issues"]
    le = TP.preflight_trade_permission(fetch_account_state=_state(), endpoint_host="live.ctraderapi.com")
    assert not le["ok"] and "ENDPOINT_NOT_DEMO" in le["issues"]
    lv = TP.preflight_trade_permission(fetch_account_state=_state(is_live=True),
                                       endpoint_host="demo.ctraderapi.com")
    assert not lv["ok"] and "ACCOUNT_IS_LIVE" in lv["issues"]


# 8-13 — one-shot permit
def _permit(**o):
    d = dict(account_id=4257941, signal_id="sig-1", proposal_id="demoprop-x",
             client_order_id="cli-abc", now_ms=NOW)
    d.update(o)
    return OSP.make_permit(**d)


def test_permit_proposal_bound():
    st = OSP.PermitStore()
    ok, reason = OSP.validate_permit(_permit(), account_id=4257941, signal_id="sig-1",
                                     proposal_id="OTHER", client_order_id="cli-abc", now_ms=NOW, store=st)
    assert not ok and reason == "PROPOSAL_MISMATCH"


def test_permit_expired_rejected():
    st = OSP.PermitStore()
    ok, reason = OSP.validate_permit(_permit(), account_id=4257941, signal_id="sig-1",
                                     proposal_id="demoprop-x", client_order_id="cli-abc",
                                     now_ms=NOW + OSP.PERMIT_TTL_MS + 5000, store=st)
    assert not ok and reason == "PERMIT_EXPIRED"


def test_permit_single_use_reused_rejected():
    st = OSP.PermitStore()
    p = _permit()
    kw = dict(account_id=4257941, signal_id="sig-1", proposal_id="demoprop-x",
              client_order_id="cli-abc", now_ms=NOW, store=st, order_sending_enabled=True)
    first = OSP.try_consume(p, **kw)
    second = OSP.try_consume(p, **kw)
    assert first["consumed"] is True and second["consumed"] is False and second["reason"] == "PERMIT_ALREADY_CONSUMED"


def test_permit_replay_rejected():
    st = OSP.PermitStore()
    ok, reason = OSP.validate_permit(_permit(), account_id=4257941, signal_id="sig-1",
                                     proposal_id="demoprop-x", client_order_id="cli-abc", now_ms=NOW,
                                     store=st, fresh_signal=False)
    assert not ok and reason == "STALE_OR_REPLAY_SIGNAL_INELIGIBLE"


def test_emergency_disable_overrides_permit():
    def f(tmp):
        df = os.path.join(tmp, "DEMO_EXECUTION_DISABLED"); open(df, "w").write("x")
        st = OSP.PermitStore()
        ok, reason = OSP.validate_permit(_permit(), account_id=4257941, signal_id="sig-1",
                                         proposal_id="demoprop-x", client_order_id="cli-abc", now_ms=NOW,
                                         store=st, disable_path=df)
        assert not ok and reason == "EMERGENCY_DISABLE_FILE_OVERRIDES_EVERYTHING"
    tmp = tempfile.mkdtemp()
    try:
        f(tmp)
    finally:
        import shutil
        shutil.rmtree(tmp, ignore_errors=True)


def test_permit_alone_insufficient_and_sending_disabled():
    st = OSP.PermitStore()
    p = _permit()
    res = OSP.try_consume(p, account_id=4257941, signal_id="sig-1", proposal_id="demoprop-x",
                          client_order_id="cli-abc", now_ms=NOW, store=st, order_sending_enabled=False)
    # a valid permit is consumed, but global sending is still off and the full firewall is still required
    assert res["consumed"] is True and res["order_sending_enabled"] is False and res["global_enable_sufficient"] is False


# 15 — locks
def test_locks_false():
    cfg = open(os.path.join(_ROOT, "config.py"), encoding="utf-8").read()
    cc = open(os.path.join(_ROOT, "ctrader_config.py"), encoding="utf-8").read()
    assert "EXECUTION_ENABLED = False" in cfg and "CTRADER_EXECUTION_ENABLED = False" in cc
    assert CFG.ORDER_SENDING_ENABLED is False and CFG.DEMO_ENDPOINT_PORT == 5035
