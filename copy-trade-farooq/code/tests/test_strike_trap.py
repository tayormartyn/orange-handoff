"""Qualified Strike & Trap — SHADOW-ONLY tests (35 proofs). Deterministic; fake/offline; no broker
action; all four gates false; no permit/lease; no protobuf constructed."""
from __future__ import annotations
import glob
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SC = os.path.join(_ROOT, "campaign_extractor", "shadow_campaign")
_DE = os.path.join(_ROOT, "campaign_extractor", "demo_executor")
for p in (_ROOT, _SC, _DE):
    if p not in sys.path:
        sys.path.insert(0, p)

import sc_config as CFG
import strike_trap as ST
import campaign as CAMP
import compare as CMP

NOW = 1_800_000_000_000
PROV = NOW - 60_000


def sell_inside_path():                              # entered from below, now inside, first traversal
    return [{"bid": 4118, "ask": 4118.2, "ts_ms": NOW - 50_000},
            {"bid": 4121, "ask": 4121.2, "ts_ms": NOW - 30_000},
            {"bid": 4123, "ask": 4123.2, "ts_ms": NOW - 5_000}]


def sell_quote():
    return {"bid": 4123.0, "ask": 4123.2, "ts_ms": NOW - 2_000}


def _route(**o):
    d = dict(direction="SELL", low=4120, high=4130, quote=sell_quote(), quote_path=sell_inside_path(),
             provider_ts_ms=PROV, now_ms=NOW, quote_health_state="QUOTES_ACTIVE", approval_latency_s=5)
    d.update(o)
    return ST.route(**d)


def _qual(**o):
    d = dict(direction="SELL", low=4120, high=4130, quote=sell_quote(), quote_path=sell_inside_path(),
             provider_ts_ms=PROV, now_ms=NOW, quote_health_state="QUOTES_ACTIVE", approval_latency_s=5)
    d.update(o)
    return ST.qualify(**d)


# 1
def test_pre_zone_routes_passive_ladder():
    path = [{"bid": 4110, "ask": 4110.2, "ts_ms": NOW - 40_000}, {"bid": 4112, "ask": 4112.2, "ts_ms": NOW - 5_000}]
    r = _route(quote={"bid": 4112, "ask": 4112.2, "ts_ms": NOW - 2_000}, quote_path=path)
    assert r["routing_mode"] == CFG.PRE_TOUCH_PASSIVE_LADDER


# 2
def test_first_valid_inside_routes_strike_trap():
    assert _route()["routing_mode"] == CFG.INSIDE_ZONE_QUALIFIED_STRIKE_TRAP


# 3
def test_second_touch_blocks():
    path = [{"bid": 4121, "ask": 4121.2, "ts_ms": NOW - 60_000}, {"bid": 4115, "ask": 4115.2, "ts_ms": NOW - 40_000},
            {"bid": 4123, "ask": 4123.2, "ts_ms": NOW - 5_000}]
    r = _route(quote_path=path)
    assert r["routing_mode"] == CFG.ZONE_CONSUMED and "SECOND_TOUCH_BLOCKED" in r["blockers"]


# 4
def test_prior_profit_exit_blocks():
    path = [{"bid": 4121, "ask": 4121.2, "ts_ms": NOW - 60_000}, {"bid": 4115, "ask": 4115.2, "ts_ms": NOW - 5_000}]
    _, blk, _ = _qual(quote_path=path, quote={"bid": 4115, "ask": 4115.2, "ts_ms": NOW - 2_000})
    assert "ZONE_ALREADY_EXITED" in blk


# 5
def test_full_traversal_blocks():
    path = [{"bid": 4115, "ask": 4115.2, "ts_ms": NOW - 60_000}, {"bid": 4123, "ask": 4123.2, "ts_ms": NOW - 30_000},
            {"bid": 4137, "ask": 4137.2, "ts_ms": NOW - 5_000}]   # profit(low) -> inside -> stop(above)
    _, blk, _ = _qual(quote_path=path, quote={"bid": 4137, "ask": 4137.2, "ts_ms": NOW - 2_000})
    assert "ZONE_ALREADY_TRAVERSED" in blk


# 6
def test_stop_side_breach_blocks():
    path = [{"bid": 4123, "ask": 4123.2, "ts_ms": NOW - 40_000}, {"bid": 4137, "ask": 4137.2, "ts_ms": NOW - 5_000}]
    _, blk, _ = _qual(quote_path=path, quote={"bid": 4137, "ask": 4137.2, "ts_ms": NOW - 2_000})
    assert "STOP_SIDE_BREACHED" in blk


# 7
def test_excessive_residence_blocks():
    _, blk, _ = _qual(residence_seconds=999)
    assert "INSIDE_ZONE_RESIDENCE_EXCEEDED" in blk


# 8
def test_excessive_approval_latency_blocks():
    _, blk, _ = _qual(approval_latency_s=999)
    assert "APPROVAL_LATENCY_EXCEEDED" in blk


# 9
def test_excessive_penetration_blocks():
    # price deep into zone (bid 4129 in 4120-4130 -> penetration 0.9 > 0.6)
    q = {"bid": 4129.0, "ask": 4129.2, "ts_ms": NOW - 2_000}
    path = [{"bid": 4121, "ask": 4121.2, "ts_ms": NOW - 30_000}, {"bid": 4129, "ask": 4129.2, "ts_ms": NOW - 5_000}]
    _, blk, _ = _qual(quote=q, quote_path=path)
    assert "STRIKE_PENETRATION_EXCEEDED" in blk


# 10
def test_stale_or_disconnected_quotes_block():
    _, blk, _ = _qual(quote_health_state="QUOTES_DISCONNECTED")
    assert "QUOTE_HEALTH_NOT_ACTIVE" in blk


# 11
def test_quote_path_gap_blocks():
    path = [{"bid": 4121, "ask": 4121.2, "ts_ms": NOW - 300_000}, {"bid": 4123, "ask": 4123.2, "ts_ms": NOW - 5_000}]
    _, blk, _ = _qual(quote_path=path)
    assert "QUOTE_PATH_UNVERIFIED" in blk


# 12 / 13 / 14 executable side + midpoint
def test_sell_uses_bid_buy_uses_ask_never_midpoint():
    q = {"bid": 4123.0, "ask": 4123.8, "ts_ms": NOW}
    assert ST.exec_price("SELL", q) == 4123.0 and ST.exec_price("BUY", q) == 4123.8
    src = open(os.path.join(_SC, "strike_trap.py"), encoding="utf-8").read()
    # midpoint only appears as labelled analytics, never drives penetration/region/exec
    assert "LABELLED ANALYTICS ONLY" in src
    assert "midpoint(" not in src.split("def penetration_ratio")[1].split("def _region")[0]


# 15
def test_strike_uses_market_range_not_fake_limit():
    s = ST.strike_shadow("SELL", sell_quote(), slippage_points=20)
    assert {"STRIKE_REQUESTED_PRICE", "BEST_ALLOWED_FILL", "WORST_ALLOWED_FILL", "SHADOW_FILL_PRICE",
            "SLIPPAGE_POINTS", "REJECTED_OUTSIDE_RANGE"} <= set(s)
    assert s["execution_state"] in ("SHADOW_FILL_UNCERTAIN", "REJECTED_OUTSIDE_RANGE")   # never assume full fill


# 16
def test_t1_worst_fill_within_60pct():
    z = ST.size_worst_fill_risk("SELL", quote=sell_quote(), provider_stop=4135, balance=10000, slippage_points=20)
    assert z["ok"] and z["within_60pct"] and z["t1_worst_fill_risk"] <= z["strike_budget"] + 1e-9


# 17
def test_full_campaign_within_half_percent():
    camp = CAMP.run_shadow_campaign(direction="SELL", low=4120, high=4130, quote=sell_quote(),
                                    provider_stop=4135, balance=10000, slippage_points=20)
    assert camp["ledger"]["within_full_cap"] and camp["ledger"]["FULL_FILL_MAXIMUM_RISK"] <= camp["ledger"]["TOTAL_CAMPAIGN_RISK"] + 1e-9


# 18
def test_slippage_ceiling_violation_rejects_strike():
    # a shadow fill beyond the worst-allowed range -> REJECTED_OUTSIDE_RANGE
    s = ST.strike_shadow("SELL", sell_quote(), slippage_points=20, shadow_fill_offset=40)  # 40pts worse than req
    assert s["REJECTED_OUTSIDE_RANGE"] is True and s["SHADOW_FILL_PRICE"] is None


# 19
def test_provisional_protection_never_looser_than_provider():
    p = ST.provisional_stop("SELL", best_fill=4123.0, worst_fill=4122.8, provider_stop=4135)
    assert p["ok"] and p["provisional_tighter_or_equal"] is True
    assert p["stop_at_best_fill"] <= 4135 and p["stop_at_worst_fill"] <= 4135


# 20
def test_no_strike_when_protection_unavailable():
    camp = CAMP.run_shadow_campaign(direction="SELL", low=4120, high=4130, quote=sell_quote(),
                                    provider_stop=4135, balance=10000, slippage_points=20, protection_ok=False)
    assert camp["aborted"] and camp["result"] == "STRIKE_PROTECTION_UNAVAILABLE" and camp["traps"] == []


# 21
def test_traps_not_calculated_before_reconciliation():
    camp = CAMP.run_shadow_campaign(direction="SELL", low=4120, high=4130, quote=sell_quote(),
                                    provider_stop=4135, balance=10000, slippage_points=20)
    s = camp["states"]
    assert s.index("EXACT_STOP_CONFIRMED") < s.index("TRAPS_CALCULATED")   # protection before traps
    assert s.index("STRIKE_SHADOW_FILLED") < s.index("TRAPS_CALCULATED")


# 22
def test_strike_rejection_aborts_campaign():
    camp = CAMP.run_shadow_campaign(direction="SELL", low=4120, high=4130, quote=sell_quote(),
                                    provider_stop=4135, balance=10000, slippage_points=20, strike_outcome="REJECTED")
    assert camp["aborted"] and "CAMPAIGN_ABORTED" in camp["states"] and camp["traps"] == []


# 23
def test_uncertain_strike_blocks_traps():
    camp = CAMP.run_shadow_campaign(direction="SELL", low=4120, high=4130, quote=sell_quote(),
                                    provider_stop=4135, balance=10000, slippage_points=20, strike_outcome="UNCERTAIN")
    assert camp["no_traps_allowed"] and "STRIKE_RECONCILIATION_REQUIRED" in camp["states"] and camp["traps"] == []


# 24
def test_partial_fill_recalculates_risk():
    full = CAMP.run_shadow_campaign(direction="SELL", low=4120, high=4130, quote=sell_quote(),
                                    provider_stop=4135, balance=10000, slippage_points=20, strike_outcome="FILLED")
    part = CAMP.run_shadow_campaign(direction="SELL", low=4120, high=4130, quote=sell_quote(),
                                    provider_stop=4135, balance=10000, slippage_points=20,
                                    strike_outcome="PARTIAL", filled_fraction=0.5)
    assert "STRIKE_SHADOW_PARTIAL_FILL" in part["states"]
    assert part["actual_t1_risk"] < full["actual_t1_risk"]   # only filled volume consumes risk


# 25 / 26 passive traps
def test_traps_passive_and_non_passive_omitted():
    camp = CAMP.run_shadow_campaign(direction="SELL", low=4120, high=4130, quote=sell_quote(),
                                    provider_stop=4135, balance=10000, slippage_points=20)
    for t in camp["placed_traps"]:
        assert t["status"] == "PASSIVE_VALID" and t["inside_zone"]
    # a trap that is no longer passive is flagged, never market-converted
    traps = ST.passive_traps(direction="SELL", low=4120, high=4130,
                             quote={"bid": 4131, "ask": 4131.2, "ts_ms": NOW}, remaining_risk=100,
                             provider_stop=4135, balance=10000)
    non_passive = [t for t in traps if t.get("status") == "TRAP_LEVEL_NO_LONGER_PASSIVE"]
    assert non_passive and all(t.get("do_not_place_child") for t in non_passive)
    src = open(os.path.join(_SC, "strike_trap.py"), encoding="utf-8").read()
    assert "market" not in src.split("def passive_traps")[1].lower() or "market-converted" in open(os.path.join(_SC, "passive_ladder.py")).read().lower()


# 27 / 28 profit-side exit
def test_profit_side_exit_cancels_traps_no_momentum():
    traps = [{"tag": "T2", "status": "PASSIVE_VALID", "reserved_risk": 12.0},
             {"tag": "T3", "status": "PASSIVE_VALID", "reserved_risk": 8.0}]
    e = ST.profit_side_exit(traps)
    assert e["event"] == "PROFIT_SIDE_EXIT" and e["released_risk"] == 20.0
    assert e["t1_preserved"] and e["re_entry_blocked"] and e["momentum_add_on_permitted"] is False


# 29
def test_no_second_campaign_from_same_signal():
    latch = ST.first_touch_latch(sell_inside_path(), "SELL", 4120, 4130, PROV)
    assert latch["zone_consumed"] is True and latch["campaign_generation"] == 1
    # a later re-entry never qualifies (routing -> ZONE_CONSUMED)
    path = sell_inside_path() + [{"bid": 4115, "ask": 4115.2, "ts_ms": NOW - 3_000},
                                 {"bid": 4123, "ask": 4123.2, "ts_ms": NOW - 1_000}]
    assert _route(quote_path=path)["routing_mode"] == CFG.ZONE_CONSUMED


# 30
def test_passive_and_hybrid_identical_quote_path():
    c = CMP.compare_models(direction="SELL", low=4120, high=4130, quote=sell_quote(),
                           quote_path=sell_inside_path(), provider_ts_ms=PROV, now_ms=NOW,
                           quote_health_state="QUOTES_ACTIVE", provider_stop=4135, balance=10000)
    assert c["identical_quote_path"] is True
    models = {r["model"] for r in c["results"]}
    assert "QUALIFIED_STRIKE_TRAP_60_25_15" in models and "PASSIVE_60_25_15" in models
    assert "declared superior" in c["note"].lower()


# 31 / 34 no broker execution / no protobuf
def test_no_broker_execution_or_protobuf_constructed():
    for f in glob.glob(os.path.join(_SC, "*.py")):
        src = open(f, encoding="utf-8").read()
        for bad in ("ProtoOA", "send_new_order", "send_management", "SerializeToString", "network_send",
                    "make_permit", "make_lease"):
            assert bad not in src, (os.path.basename(f), bad)


# 32 / 33 / 35 gates + permit/lease + no send
def test_all_gates_false_no_permit_no_send():
    de = open(os.path.join(_DE, "config.py"), encoding="utf-8").read()
    cfg = open(os.path.join(_ROOT, "config.py"), encoding="utf-8").read()
    cc = open(os.path.join(_ROOT, "ctrader_config.py"), encoding="utf-8").read()
    assert "ORDER_SENDING_ENABLED = False" in de and "ORDER_MANAGEMENT_ENABLED = False" in de
    assert "EXECUTION_ENABLED = False" in cfg and "CTRADER_EXECUTION_ENABLED = False" in cc
    camp = CAMP.run_shadow_campaign(direction="SELL", low=4120, high=4130, quote=sell_quote(),
                                    provider_stop=4135, balance=10000, slippage_points=20)
    assert camp["no_broker_action"] is True and camp["atomic"] is False


def test_buy_uses_ask_and_penetration():
    # BUY zone 4110-4120 BELOW market; price fell into it; executable = ask
    q = {"bid": 4114.8, "ask": 4115.0, "ts_ms": NOW}
    assert ST.exec_price("BUY", q) == 4115.0
    assert ST.penetration_ratio("BUY", 4110, 4120, 4115) == 0.5   # from high edge downward
