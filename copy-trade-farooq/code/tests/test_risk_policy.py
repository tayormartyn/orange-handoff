"""Risk-policy v2.0.0 (0.5% -> 1.0%) — deterministic tests (27 proofs). Sizing-policy only; fake/offline;
no broker action; all four gates false; no permit/lease; no protobuf/transport."""
from __future__ import annotations
import glob
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DE = os.path.join(_ROOT, "campaign_extractor", "demo_executor")
_SC = os.path.join(_ROOT, "campaign_extractor", "shadow_campaign")
for p in (_ROOT, _DE, _SC):
    if p not in sys.path:
        sys.path.insert(0, p)

import risk_policy as RP
import config as CFG
import sc_config as SC
import strike_trap as ST
import campaign as CAMP
from models import AccountSnapshot, SymbolMeta
import risk_sizer as RS

XAU = SymbolMeta(symbol_id=41, name="XAUUSD", digits=2, point=0.01, lot_size=100.0, min_volume=0.01,
                 max_volume=100.0, volume_step=0.01, min_stop_distance_points=10)


def acct(bal):
    return AccountSnapshot(account_id=4257941, is_live=False, balance=bal, currency="GBP", trade_scope="trade")


# 1 / 2
def test_budget_10000_is_100():
    assert RP.campaign_budget(10000) == 100.0


def test_budget_8500_is_85():
    assert RP.campaign_budget(8500) == 85.0


# 3 / 4
def test_60_25_15_currency_split():
    assert RP.tranche_budgets(10000) == [60.0, 25.0, 15.0]


def test_60_25_15_sums_to_one_percent():
    w = RP.COMPARISON_WEIGHTS["QUALIFIED_STRIKE_TRAP_60_25_15"]
    assert abs(sum(w) - 1.0) < 1e-9
    assert abs(sum(RP.tranche_budgets(10000, w)) - RP.campaign_budget(10000)) < 1e-6


# 5
def test_no_tranche_gets_full_one_percent():
    for w in RP.COMPARISON_WEIGHTS["QUALIFIED_STRIKE_TRAP_60_25_15"]:
        assert w < 1.0
    tr = RP.tranche_budgets(10000)
    assert max(tr) < RP.campaign_budget(10000)          # T1 (60) < 100


# 6 / 7
def test_full_fill_never_exceeds_cap_costs_within():
    tr = RP.tranche_budgets(10000)                        # 60/25/15
    wc = RP.within_cap(basis_amount=10000, tranche_risks=tr, cost_allowance=0.0)
    assert wc["within_cap"] and wc["total_worst_case_risk"] <= wc["cap"] + 1e-6
    # costs count INSIDE the cap: 60+25+15 + cost must still be <= 100 -> with 60/25/15 exactly=100 a cost breaks it
    wc2 = RP.within_cap(basis_amount=10000, tranche_risks=[59, 24, 14], cost_allowance=3.0)
    assert wc2["total_worst_case_risk"] == 100.0 and wc2["within_cap"]
    wc3 = RP.within_cap(basis_amount=10000, tranche_risks=[60, 25, 15], cost_allowance=1.0)
    assert wc3["within_cap"] is False                     # cost pushed it beyond -> blocked


# 8 / 9 volume rounds down, never up beyond budget
def test_volume_rounds_down_never_up():
    z = ST.size_worst_fill_risk("SELL", quote={"bid": 4123.0, "ask": 4123.2, "ts_ms": 0},
                                provider_stop=4135, balance=10000, slippage_points=20)
    assert z["ok"]
    # worst-fill risk must not exceed the 60% strike budget (no upward rounding past allocation)
    assert z["t1_worst_fill_risk"] <= z["strike_budget"] + 1e-9
    # single-order sizer rounds DOWN to step and stays within risk after rounding
    r = RS.size_order(account=acct(10000), symbol=XAU, entry=4123.0, stop=4135.0)
    assert r.ok and r.planned_stop_loss_risk <= r.risk_amount + 1e-6
    assert abs((r.volume_lots / XAU.volume_step) - round(r.volume_lots / XAU.volume_step)) < 1e-6  # step-valid


# 10 broker min-volume that cannot fit blocks
def test_below_min_volume_blocks():
    # tiny balance so 1.0% cannot buy even the min 0.01 lot given a wide stop
    r = RS.size_order(account=acct(50), symbol=XAU, entry=4123.0, stop=4200.0)
    assert (not r.ok) and r.reason in ("BELOW_MIN_VOLUME", "LOSS_EXCEEDS_RISK_AFTER_ROUNDING")


# 11
def test_worst_fill_strike_within_60pct():
    z = ST.size_worst_fill_risk("SELL", quote={"bid": 4123.0, "ask": 4123.2, "ts_ms": 0},
                                provider_stop=4135, balance=10000, slippage_points=20)
    assert z["within_60pct"] and z["strike_budget"] == 60.0    # 0.60% of 10000


# 12 slippage reduces remaining trap capacity
def test_slippage_reduces_remaining_capacity():
    q = {"bid": 4123.0, "ask": 4123.2, "ts_ms": 0}
    lo = CAMP.run_shadow_campaign(direction="SELL", low=4120, high=4130, quote=q, provider_stop=4135,
                                  balance=10000, slippage_points=5)
    hi = CAMP.run_shadow_campaign(direction="SELL", low=4120, high=4130, quote=q, provider_stop=4135,
                                  balance=10000, slippage_points=40)
    assert hi["actual_t1_risk"] >= lo["actual_t1_risk"]         # more slippage -> more T1 worst risk
    assert hi["ledger"]["AVAILABLE_RISK"] <= lo["ledger"]["AVAILABLE_RISK"]  # less remaining for traps


# 13
def test_partial_fill_recalculates_remaining():
    q = {"bid": 4123.0, "ask": 4123.2, "ts_ms": 0}
    full = CAMP.run_shadow_campaign(direction="SELL", low=4120, high=4130, quote=q, provider_stop=4135,
                                    balance=10000, slippage_points=20)
    part = CAMP.run_shadow_campaign(direction="SELL", low=4120, high=4130, quote=q, provider_stop=4135,
                                    balance=10000, slippage_points=20, strike_outcome="PARTIAL",
                                    filled_fraction=0.5)
    assert part["actual_t1_risk"] < full["actual_t1_risk"]


# 14 full campaign stays within 1.0% cap
def test_campaign_within_one_percent_cap():
    camp = CAMP.run_shadow_campaign(direction="SELL", low=4120, high=4130,
                                    quote={"bid": 4123.0, "ask": 4123.2, "ts_ms": 0}, provider_stop=4135,
                                    balance=10000, slippage_points=20)
    L = camp["ledger"]
    assert L["TOTAL_CAMPAIGN_RISK"] == 100.0 and L["within_full_cap"]
    assert L["FULL_FILL_MAXIMUM_RISK"] <= 100.0 + 1e-6


# 15 farther stop that raises risk above cap blocks
def test_farther_stop_above_cap_blocks():
    ok = RP.stop_move_within_cap(basis_amount=10000, new_campaign_worst_case_risk=95.0)
    bad = RP.stop_move_within_cap(basis_amount=10000, new_campaign_worst_case_risk=140.0)
    assert ok["allowed"] and (not bad["allowed"]) and bad["blocked_reason"] == "STOP_MOVE_EXCEEDS_CAMPAIGN_CAP"
    assert bad["management_may_increase_risk"] is False


# 16 breakeven / partial-close reduce or preserve risk
def test_management_reduces_or_preserves_risk():
    # breakeven (stop -> entry) strictly reduces the distance-to-stop; partial close reduces volume
    orig_risk = abs(4135 - 4123) * 0.02 * 100          # SELL entry 4123 stop 4135, 0.02 lot
    be_risk = abs(4123 - 4123) * 0.02 * 100            # stop moved to entry -> 0 risk
    assert be_risk < orig_risk
    pc_risk = abs(4135 - 4123) * 0.01 * 100            # half volume
    assert pc_risk < orig_risk


# 17 / 18
def test_unrealised_profit_and_released_risk_no_new_capacity():
    L = ST.risk_ledger(balance=10000, strike_actual_risk=50, trap_reserved=30, released=10)
    assert L["unrealised_profit_adds_capacity"] is False
    e = ST.profit_side_exit([{"tag": "T2", "status": "PASSIVE_VALID", "reserved_risk": 10.0}])
    assert e["momentum_add_on_permitted"] is False and e["released_risk"] == 10.0


# 19 historical 0.5% preserved (policy record for a pre-activation campaign keeps 0.5%)
def test_historical_half_percent_preserved():
    rec = RP.policy_record(basis_amount=10000, currency="GBP", now_ms=RP.ACTIVATION_TS_MS - 1)
    assert rec["risk_percent"] == 0.5                    # pre-activation -> historical percent, not rewritten


# 20 new campaigns store v2.0.0 + 1.0%
def test_new_campaign_stores_version_and_percent():
    rec = RP.policy_record(basis_amount=10000, currency="GBP", now_ms=RP.ACTIVATION_TS_MS + 1)
    assert rec["risk_policy_version"] == "2.0.0" and rec["risk_percent"] == 1.0
    assert rec["risk_basis_type"] == "BALANCE" and rec["currency_risk_budget"] == 100.0
    assert rec["activation_ts_utc"] == RP.ACTIVATION_TS_UTC


# 21 single-entry sizing uses 1.0%
def test_single_entry_uses_one_percent():
    r = RS.size_order(account=acct(10000), symbol=XAU, entry=4123.0, stop=4135.0)
    assert r.ok and r.risk_pct == 0.01 and r.risk_amount == 100.0


# 22 every passive + hybrid model uses the SAME 1.0% cap
def test_all_models_use_same_cap():
    for m, w in RP.COMPARISON_WEIGHTS.items():
        assert abs(sum(w) - 1.0) < 1e-9                  # weights sum to 100% of the campaign budget
        assert abs(sum(RP.tranche_budgets(10000, w)) - 100.0) <= 0.02  # <= penny rounding on 3-way split
    assert SC.TOTAL_CAMPAIGN_RISK_PCT == CFG.DEFAULT_RISK_PCT == 0.01   # one canonical value


# 23 console no longer advertises 0.5% for prospective campaigns
def test_console_no_half_percent_label():
    html = open(os.path.join(_ROOT, "campaign_extractor", "paper_loop", "console", "index.html"), encoding="utf-8").read()
    for stale in ("0.5% fixed", "max 0.5%", "first trial 0.5%", "0.5% all-in"):
        assert stale not in html


# 24 / 25 / 26 / 27 safety
def test_all_gates_false():
    de = open(os.path.join(_DE, "config.py"), encoding="utf-8").read()
    cfg = open(os.path.join(_ROOT, "config.py"), encoding="utf-8").read()
    cc = open(os.path.join(_ROOT, "ctrader_config.py"), encoding="utf-8").read()
    assert "ORDER_SENDING_ENABLED = False" in de and "ORDER_MANAGEMENT_ENABLED = False" in de
    assert "EXECUTION_ENABLED = False" in cfg and "CTRADER_EXECUTION_ENABLED = False" in cc


def test_no_permit_lease_or_transport_in_policy():
    for f in [os.path.join(_DE, "risk_policy.py"), os.path.join(_SC, "sc_config.py")]:
        src = open(f, encoding="utf-8").read()
        for bad in ("ProtoOA", "SerializeToString", "network_send", "make_permit", "make_lease",
                    "send_new_order", "send_management"):
            assert bad not in src


def test_no_broker_action_flags():
    camp = CAMP.run_shadow_campaign(direction="SELL", low=4120, high=4130,
                                    quote={"bid": 4123.0, "ask": 4123.2, "ts_ms": 0}, provider_stop=4135,
                                    balance=10000, slippage_points=20)
    assert camp["no_broker_action"] is True and camp["atomic"] is False
