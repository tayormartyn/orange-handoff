"""demo_executor tests — firewall, risk sizing, pending-order planning, dry-run + audit, idempotency.
ALL trading is mocked; NO broker order is ever sent. Execution locks stay False."""
from __future__ import annotations
import os
import sqlite3
import sys
import tempfile

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DE = os.path.join(_ROOT, "campaign_extractor", "demo_executor")
for p in (_ROOT, _DE):
    if p not in sys.path:
        sys.path.insert(0, p)

import config as CFG
import account_guard
import risk_sizer
import order_planner
import proposals
import ctrader_demo_client as CLIENT
from audit_db import AuditDB
from models import AccountSnapshot, SymbolMeta, Quote, SignalInput

NOW = 1_800_000_000_000


def acct(**o):
    d = dict(account_id=4257941, is_live=False, balance=10000.0, currency="GBP",
             trade_scope="trade", environment="DEMO")
    d.update(o)
    return AccountSnapshot(**d)


def sym(**o):
    d = dict(symbol_id=41, name="XAUUSD", digits=2, point=0.01, lot_size=100.0, min_volume=0.01,
             max_volume=100.0, volume_step=0.01, min_stop_distance_points=50.0, quote_currency="USD")
    d.update(o)
    return SymbolMeta(**d)


def quote(bid=3301.00, ask=3301.20, ts_ms=NOW):
    return Quote(bid, ask, ts_ms)


def sig(**o):
    d = dict(signal_id="sig-1", intake_class="SIGNAL", confirmed=True, instrument="XAUUSD",
             direction="BUY", entry_low=3300.0, entry_high=3305.0, stop=3295.0, targets=[3315.0],
             provider_verified=True, confirmed_at_ms=NOW, duplicate=False, synthetic=False)
    d.update(o)
    return SignalInput(**d)


FX = 0.79   # USD->GBP


def _fw(**o):
    return account_guard.demo_firewall(account=o.get("account", acct()),
                                       instrument=o.get("instrument", "XAUUSD"),
                                       token_scope=o.get("token_scope", "trade"),
                                       disable_path=o.get("disable_path"))


# ---- firewall ----
def test_live_environment_rejected():
    fw = _fw(account=acct(environment="LIVE"))
    assert not fw.all_passed and not any(c.passed for c in fw.checks if c.name == "environment_is_demo")


def test_islive_true_rejected():
    assert not any(c.passed for c in _fw(account=acct(is_live=True)).checks if c.name == "account_not_live")


def test_wrong_account_rejected():
    assert not any(c.passed for c in _fw(account=acct(account_id=9999)).checks if c.name == "account_allowlisted")


def test_missing_trade_permission_rejected():
    assert not any(c.passed for c in _fw(token_scope="").checks if c.name == "token_trade_capable_demo_scope")


def test_disable_file_blocks_everything():
    def f(tmp):
        df = os.path.join(tmp, "DEMO_EXECUTION_DISABLED"); open(df, "w").write("x")
        fw = _fw(disable_path=df)
        assert not any(c.passed for c in fw.checks if c.name == "disable_file_absent")
        assert not account_guard.firewall_allows_preview(fw)   # kill-switch blocks preview too
    _run(f)


def test_non_xauusd_rejected():
    assert not any(c.passed for c in _fw(instrument="BTCUSD").checks if c.name == "instrument_is_xauusd")
    ok, reason = proposals.check_eligibility(sig(instrument="BTCUSD"))
    assert not ok and reason == "NOT_XAUUSD"


# ---- eligibility ----
def test_missing_stop_rejected():
    ok, reason = proposals.check_eligibility(sig(stop=None))
    assert not ok and reason == "STOP_UNKNOWN"


def test_ocr_alone_and_unconfirmed_cannot_create_proposal():
    ok, reason = proposals.check_eligibility(sig(confirmed=False))
    assert not ok and reason == "NOT_HUMAN_CONFIRMED"


def test_synthetic_rejected():
    ok, reason = proposals.check_eligibility(sig(synthetic=True))
    assert not ok and reason == "SYNTHETIC_OR_TEST"


# ---- order planning ----
def test_stop_wrong_side_rejected():
    p = order_planner.plan_order(direction="BUY", entry_low=3300, entry_high=3305, stop=3310,
                                 quote=quote(), symbol=sym(), now_ms=NOW, signal_confirmed_at_ms=NOW)
    assert not p.ok and p.reason == "STOP_WRONG_SIDE"


def test_stale_price_rejected():
    p = order_planner.plan_order(direction="BUY", entry_low=3300, entry_high=3305, stop=3295,
                                 quote=quote(ts_ms=NOW - 999999), symbol=sym(), now_ms=NOW)
    assert not p.ok and p.reason == "STALE_QUOTE"


def test_stale_signal_rejected():
    p = order_planner.plan_order(direction="BUY", entry_low=3300, entry_high=3305, stop=3295,
                                 quote=quote(), symbol=sym(), now_ms=NOW,
                                 signal_confirmed_at_ms=NOW - CFG.SIGNAL_STALE_SECONDS * 1000 - 5000)
    assert not p.ok and p.reason == "STALE_SIGNAL"


def test_entry_outside_zone_rejected():
    p = order_planner.plan_order(direction="BUY", entry_low=3300, entry_high=3305, stop=3295,
                                 quote=quote(), symbol=sym(), manual_entry=3310, now_ms=NOW)
    assert not p.ok and p.reason == "MANUAL_ENTRY_OUTSIDE_ZONE"


def test_limit_stop_selection():
    # BUY entry below ask -> LIMIT ; BUY entry above ask -> STOP
    lim = order_planner.plan_order(direction="BUY", entry_low=3298, entry_high=3299, stop=3295,
                                   quote=quote(bid=3301, ask=3301.2), symbol=sym(), now_ms=NOW)
    assert lim.ok and lim.order_type == "BUY_LIMIT"
    stp = order_planner.plan_order(direction="BUY", entry_low=3303, entry_high=3304, stop=3300,
                                   quote=quote(bid=3301, ask=3301.2), symbol=sym(), now_ms=NOW)
    assert stp.ok and stp.order_type == "BUY_STOP"
    # SELL entry above bid -> LIMIT ; below bid -> STOP
    sl = order_planner.plan_order(direction="SELL", entry_low=3303, entry_high=3304, stop=3308,
                                  quote=quote(bid=3301, ask=3301.2), symbol=sym(), now_ms=NOW)
    assert sl.ok and sl.order_type == "SELL_LIMIT"
    ss = order_planner.plan_order(direction="SELL", entry_low=3298, entry_high=3299, stop=3303,
                                  quote=quote(bid=3301, ask=3301.2), symbol=sym(), now_ms=NOW)
    assert ss.ok and ss.order_type == "SELL_STOP"


def test_min_distance_violation():
    p = order_planner.plan_order(direction="BUY", entry_low=3301.19, entry_high=3301.19, stop=3295,
                                 quote=quote(bid=3301, ask=3301.20), symbol=sym(min_stop_distance_points=50),
                                 now_ms=NOW)
    assert not p.ok and p.reason == "MIN_DISTANCE_VIOLATION"


# ---- risk sizing ----
def test_volume_obeys_min_max_step():
    r = risk_sizer.size_order(account=acct(), symbol=sym(), entry=3300, stop=3295, risk_pct=0.005,
                              fx_quote_to_account=FX)
    assert r.ok and abs((r.volume_lots / 0.01) - round(r.volume_lots / 0.01)) < 1e-6
    assert sym().min_volume <= r.volume_lots <= sym().max_volume


def test_loss_within_risk_after_rounding():
    r = risk_sizer.size_order(account=acct(), symbol=sym(), entry=3300, stop=3295, risk_pct=0.005,
                              fx_quote_to_account=FX)
    assert r.ok and r.planned_stop_loss_risk <= r.risk_amount + 1e-6


def test_risk_cannot_exceed_one_percent():
    r = risk_sizer.size_order(account=acct(), symbol=sym(), entry=3300, stop=3295, risk_pct=0.05,
                              fx_quote_to_account=FX)
    assert r.risk_pct == CFG.MAX_RISK_PCT and r.risk_amount == round(10000 * 0.01, 2)


def test_invalid_margin_blocks():
    # tiny leverage forces margin > balance
    r = risk_sizer.size_order(account=acct(), symbol=sym(), entry=3300, stop=3295, risk_pct=0.005,
                              fx_quote_to_account=FX, leverage=1.0)
    assert not r.ok and r.reason == "INVALID_OR_INSUFFICIENT_MARGIN"


def test_stop_distance_zero_blocked():
    r = risk_sizer.size_order(account=acct(), symbol=sym(), entry=3300, stop=3300, fx_quote_to_account=FX)
    assert not r.ok and r.reason == "STOP_DISTANCE_ZERO"


# ---- proposal / dry-run / audit / idempotency ----
def test_proposal_deterministic_idempotent():
    a = proposals.make_proposal_id("sig-1", 1, 4257941, "XAUUSD")
    b = proposals.make_proposal_id("sig-1", 1, 4257941, "XAUUSD")
    assert a == b and a.startswith("demoprop-")


def test_full_valid_dry_run_proposal_and_audit():
    def f(tmp):
        adb = AuditDB(os.path.join(tmp, "a.db"))
        p = proposals.build_proposal(sig(), acct(), sym(), quote(), risk_pct=0.005,
                                     token_scope="trade", now_ms=NOW, fx_quote_to_account=FX, audit=adb)
        assert p.status == "PROPOSAL_VALIDATED" and p.preview["valid_for_arming"] is True
        assert p.preview["order_type"] == "BUY_LIMIT" and p.preview["banner"] == "DEMO ORDER PREVIEW — NO ORDER SENT"
        assert proposals.arm(p, adb)["armed"] is True
        res = proposals.dry_run_approve(p, now_ms=NOW, audit=adb)
        assert res["result"] == "DRY_RUN_APPROVED" and res["order_sent"] is False and res["reason"] == "NO_ORDER_SENT"
        evs = [e["event_type"] for e in adb.events_for(p.proposal_id)]
        assert evs == ["PROPOSAL_CREATED", "PROPOSAL_VALIDATED", "PROPOSAL_ARMED", "DRY_RUN_APPROVED"]
    _run(f)


def test_missing_targets_preview_flags_no_tp():
    p = proposals.build_proposal(sig(targets=None), acct(), sym(), quote(), token_scope="trade",
                                 now_ms=NOW, fx_quote_to_account=FX)
    assert p.preview["take_profit"] == "NO TAKE PROFIT SET" and p.preview["manual_management_required"] is True


def test_expired_proposal():
    p = proposals.build_proposal(sig(), acct(), sym(), quote(), token_scope="trade", now_ms=NOW,
                                 fx_quote_to_account=FX)
    proposals.arm(p)
    res = proposals.dry_run_approve(p, now_ms=NOW + CFG.PROPOSAL_TTL_SECONDS * 1000 + 5000)
    assert res["result"] == "PROPOSAL_EXPIRED" and res["order_sent"] is False


def test_submit_never_sends():
    p = proposals.build_proposal(sig(), acct(), sym(), quote(), token_scope="trade", now_ms=NOW,
                                 fx_quote_to_account=FX)
    r = CLIENT.submit_order(p, account=acct(), token_scope="trade")
    assert r["sent"] is False and r["endpoint_called"] is False
    assert r["reason"] == "ORDER_SENDING_DISABLED_DRY_RUN_PHASE"


def test_audit_append_only():
    def f(tmp):
        adb = AuditDB(os.path.join(tmp, "a.db"))
        adb.record("PROPOSAL_CREATED", "demoprop-x", {})
        for sql in ("UPDATE proposal_events SET event_type='x'", "DELETE FROM proposal_events"):
            try:
                adb.conn.execute(sql); adb.conn.commit(); assert False
            except sqlite3.IntegrityError:
                pass
    _run(f)


# ---- safety ----
def test_execution_locks_false_and_sending_disabled():
    cfg = open(os.path.join(_ROOT, "config.py"), encoding="utf-8").read()
    cc = open(os.path.join(_ROOT, "ctrader_config.py"), encoding="utf-8").read()
    assert "EXECUTION_ENABLED = False" in cfg and "CTRADER_EXECUTION_ENABLED = False" in cc
    assert CFG.ORDER_SENDING_ENABLED is False


def test_no_live_endpoint_in_package():
    # no LIVE trading endpoint may appear anywhere in the package (demo host only, no live fallback)
    import glob
    for p in glob.glob(os.path.join(_DE, "*.py")):
        src = open(p, encoding="utf-8").read().lower()
        assert "live.ctraderapi.com" not in src            # the live endpoint host
        assert "host_live" not in src and "protobuf_live_host" not in src


def _run(fn):
    tmp = tempfile.mkdtemp(prefix="de_")
    try:
        return fn(tmp)
    finally:
        import shutil
        shutil.rmtree(tmp, ignore_errors=True)
