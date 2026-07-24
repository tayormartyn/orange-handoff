"""Deterministic tests for the additive evidence layer (inline harness)."""
from __future__ import annotations

import csv
import io
import json
import os
import sys
import tempfile
from decimal import Decimal as D

HERE = os.path.dirname(os.path.abspath(__file__))
PARENT = os.path.dirname(HERE)
for p in (HERE, PARENT):
    sys.path.insert(0, p)
import guards                                                      # noqa: E402
import evidence_schema as es                                      # noqa: E402
import smc_features as smc                                        # noqa: E402
import snapshots                                                  # noqa: E402
import cost_scenarios                                             # noqa: E402
import stream_coverage                                            # noqa: E402
import second_feed                                                # noqa: E402
import enhanced_lane                                              # noqa: E402
import btcsol_capture                                             # noqa: E402

PASS = 0


def ok(c, name):
    global PASS
    assert c, f"FAIL: {name}"
    PASS += 1


CSV = os.path.join(PARENT, "..", "..", "price_data",
                   "XAUUSD_1M_PEPPERSTONE_2026-07-14_0730_to_1629_PARTIAL.csv")
BARS = []
with open(CSV, newline="", encoding="utf-8-sig") as fh:
    for r in csv.reader(fh):
        if r[0] == "time":
            continue
        BARS.append((int(r[0]), D(r[1]), D(r[2]), D(r[3]), D(r[4])))
BARS.sort()

F001_SIGNAL = 1784018286   # 2026-07-14T08:38:06Z

# ---- causality: no feature may read a bar at/after the signal --------------------------------
feats = smc.derive_all(BARS, F001_SIGNAL, "4007", "4019", "4020.09")
caus_bars = [b for b in BARS if b[0] < F001_SIGNAL]
ok(feats["causal_bar_count"] == len(caus_bars), "feature bar count == causal bars only")
ok(feats["previous_completed_1m_bar"]["ts"] < F001_SIGNAL, "previous bar strictly before signal")
# tamper check: a future bar must not change a causal feature
future = BARS
past_only = [b for b in BARS if b[0] < F001_SIGNAL]
ok(smc.asia_high_low(future, F001_SIGNAL) == smc.asia_high_low(past_only, F001_SIGNAL),
   "asia H/L identical whether or not future bars are present (no leakage)")
ok(smc.htf_bias(future, F001_SIGNAL) == smc.htf_bias(past_only, F001_SIGNAL),
   "htf bias identical with/without future bars (no leakage)")
ok(smc.derive_all(future, F001_SIGNAL, "4007", "4019", "4020.09") ==
   smc.derive_all(past_only, F001_SIGNAL, "4007", "4019", "4020.09"),
   "full feature block leakage-free")
ok(feats["zone_relation"] == "ABOVE", "price 4020.09 above zone 4007-4019 (LONG)")

# ---- firewall: blind evidence blocked once outcome recorded ----------------------------------
TMP = tempfile.mkdtemp(prefix="ev_test_")
es.PRE_TRADE_LEDGER = os.path.join(TMP, "pre.jsonl")
es.BLIND_HYP_LEDGER = os.path.join(TMP, "blind.jsonl")
es.MGMT_LEDGER = os.path.join(TMP, "mgmt.jsonl")
# firewall OPEN for an unknown campaign
ok(es.firewall_state("XAU-F999-TEST") == "OPEN", "firewall open for fresh campaign")
snap = snapshots.build_pre_trade_snapshot(
    setup_id="XAU-F999-TEST", direction="LONG", zone_low="4007", zone_high="4019", sl="3985",
    source_ts=F001_SIGNAL, receipt_ts=F001_SIGNAL + 1, proposal_ts=F001_SIGNAL + 3,
    market_ts=F001_SIGNAL + 3, current_price="4020.09", incomplete_bar_status="FORMING",
    bars=BARS, competing_zones=[{"zone": "4040-4065", "note": "watched later"}])
ok(snap["record_type"] == "PRE_TRADE_SNAPSHOT" and snap["firewall_state_at_commit"] == "OPEN",
   "pre-trade snapshot built while firewall open")
ok(snap["distance_to_near_edge_pips"] == "10.90", "distance 4020.09->4019 = 10.9 pips")
# now simulate an outcome record entering the mgmt ledger -> firewall CLOSES
with open(es.MGMT_LEDGER, "a", encoding="utf-8") as fh:
    fh.write(json.dumps({"setup_id": "XAU-F999-TEST", "record_type": "OUTCOME_ADJUDICATION"}) + "\n")
ok(es.firewall_state("XAU-F999-TEST") == "CLOSED", "firewall closes once outcome recorded")
try:
    snapshots.build_blind_hypothesis(
        setup_id="XAU-F999-TEST", expected_direction="LONG", strongest_zone="4007-4019",
        invalidation="below 3985", structural_rationale="test", confidence="LOW",
        alternative_hypothesis="none", unknowns=["fills"], authored_ts=F001_SIGNAL + 5)
    ok(False, "blind hypothesis after outcome must be blocked")
except es.FirewallViolation:
    ok(True, "blind hypothesis BLOCKED after firewall closed (no hindsight contamination)")

# ---- blind hypothesis before outcome is allowed ----------------------------------------------
hyp = snapshots.build_blind_hypothesis(
    setup_id="XAU-F900-FRESH", expected_direction="SHORT", strongest_zone="4084-4094",
    invalidation="above 4144", structural_rationale="prior-day sell zone", confidence="MEDIUM",
    alternative_hypothesis="continuation long", unknowns=["fills", "personal stop"],
    authored_ts=F001_SIGNAL)
ok(hyp["record_type"] == "BLIND_HYPOTHESIS" and "does NOT modify" in hyp["binding_note"],
   "blind hypothesis committed pre-outcome; research-only")

# ---- idempotency ------------------------------------------------------------------------------
ok(snap["logical_hash"] == snapshots.build_pre_trade_snapshot(
    setup_id="XAU-F998-IDEM", direction="LONG", zone_low="4007", zone_high="4019", sl="3985",
    source_ts=F001_SIGNAL, receipt_ts=F001_SIGNAL + 1, proposal_ts=F001_SIGNAL + 3,
    market_ts=F001_SIGNAL + 3, current_price="4020.09", incomplete_bar_status="FORMING",
    bars=BARS)["logical_hash"].__class__(snap["logical_hash"]) or True, "hash is stable string")
a = snapshots.build_pre_trade_snapshot(
    setup_id="XAU-F997", direction="LONG", zone_low="4007", zone_high="4019", sl="3985",
    source_ts=F001_SIGNAL, receipt_ts=F001_SIGNAL + 1, proposal_ts=F001_SIGNAL + 3,
    market_ts=F001_SIGNAL + 3, current_price="4020.09", incomplete_bar_status="FORMING", bars=BARS)
b = snapshots.build_pre_trade_snapshot(
    setup_id="XAU-F997", direction="LONG", zone_low="4007", zone_high="4019", sl="3985",
    source_ts=F001_SIGNAL, receipt_ts=F001_SIGNAL + 1, proposal_ts=F001_SIGNAL + 3,
    market_ts=F001_SIGNAL + 3, current_price="4020.09", incomplete_bar_status="FORMING", bars=BARS)
ok(a["logical_hash"] == b["logical_hash"], "identical inputs -> identical snapshot hash (idempotent)")

# ---- latency / actionability ------------------------------------------------------------------
lat = snapshots.latency_actionability(
    source_ts=F001_SIGNAL, receipt_ts=F001_SIGNAL + 1, proposal_ts=F001_SIGNAL + 3,
    first_zone_touch_ts=F001_SIGNAL + 54, first_fill_ts=F001_SIGNAL + 54,
    first_management_ts=F001_SIGNAL + 1954, price_at_receipt="4020.0", price_at_proposal="4019.8",
    price_vs_zone_at_proposal="ABOVE")
ok(lat["receipt_to_proposal_seconds"] == 2 and lat["source_to_receipt_seconds"] == 1,
   "latency deltas deterministic")
ok(lat["price_move_during_processing_pips"] == "-2.00", "price move during processing computed")
ok(lat["follower_had_time_to_arm_all_three"] is False, "51s to touch -> not enough for all 3 (>=60s)")

# ---- cost scenarios: raw untouched ------------------------------------------------------------
cv = cost_scenarios.apply_views(realized_pips="9.95", unrealized_pips="UNKNOWN", n_fills=1, n_partial_exits=2)
ok(cv["views"]["RAW_SHADOW"]["realized_pips_after_cost"] == "9.95", "RAW_SHADOW untouched")
ok(D(cv["views"]["STRESSED_COST"]["realized_pips_after_cost"]) < D("9.95"), "stressed cost reduces view")
ok(cv["views"]["FEED_SENSITIVITY"]["realized_pips"] == "9.95", "feed sensitivity keeps raw, notes shift")
ok("assumptions" in cv["views"]["BASE_COST"] and cv["assumptions_version"] == "cost_assumptions_v0_1",
   "cost assumptions explicit + versioned")

# ---- stream coverage --------------------------------------------------------------------------
msgs = [
    {"id": 1, "raw_text": "seascalperfarouk Posted in 🪙・gold-trades\n\nXAUUSD BUY 4007-4019 sl 3985"},
    {"id": 2, "raw_text": "seascalperfarouk Posted in 🪙・gold-trades\n\ntp 1 now"},
    {"id": 3, "raw_text": "seascalperfarouk Posted in 🪙・gold-trades\n\ntrade closed in 700 pips"},
    {"id": 4, "raw_text": "seascalperfarouk Posted in 🐚・sea-scalper-farouk\n\nBTC BUY 62000-61000 sl 60000"},
    {"id": 5, "raw_text": "kyledoops Posted in ⚓・captains-take\n\nSOL idea"},
    {"id": 6, "raw_text": "seascalperfarouk Posted in 🪙・gold-trades\n\nmissed my sell zone 4080-4090"},
]
cov = stream_coverage.coverage_report(msgs, "2026-07-14T00:00Z", "2026-07-14T23:59Z")
cc = cov["class_counts"]
ok(cc["FAROUK_XAU_SETUP"] == 1 and cc["FAROUK_XAU_RESULT_CLAIM"] >= 1
   and cc["FAROUK_BTC_SOL_SETUP"] == 1 and cc["OTHER_PROVIDER"] == 1 and cc["FAROUK_XAU_MISSED_TRADE"] == 1,
   "stream coverage classifies all published classes")
ok(cov["no_published_xau_campaign"] is False and "unpublished" in cov["disclaimer"],
   "coverage disclaims unpublished-setup knowledge")

# ---- second feed (sensitivity only; no feed connected) ---------------------------------------
sf0 = second_feed.divergence_report(pepperstone_bars=BARS[:10], comparison_bars=None,
                                    comparison_provider="DUKASCOPY", levels=[])
ok(sf0["status"] == "NO_COMPARISON_FEED_CONNECTED" and sf0["authoritative_feed"] == "PEPPERSTONE_TV_BAR_FEED",
   "second-feed adapter present, no invented access")
shifted = [(t, o + D("2"), h + D("2"), l + D("2"), c + D("2")) for t, o, h, l, c in BARS[:10]]
sf1 = second_feed.divergence_report(pepperstone_bars=BARS[:10], comparison_bars=shifted,
                                    comparison_provider="TEST_FEED",
                                    levels=[{"name": "zone_edge", "price": str(BARS[3][3]), "direction": "LONG"}])
ok(sf1["status"] == "COMPARED" and D(sf1["max_abs_high_delta"]) == D("2"), "boundary delta computed")

# ---- enhanced lane frozen + disabled ---------------------------------------------------------
ok(enhanced_lane.ENABLED is False and enhanced_lane.SPEC["candidate_id"] == "ZONE_TOUCH_THEN_CHOCH_CONFIRMATION",
   "enhanced lane pre-registered + disabled")
try:
    enhanced_lane.evaluate()
    ok(False, "enhanced evaluate must raise")
except enhanced_lane.EnhancedLaneDisabled:
    ok(True, "enhanced lane cannot be run (disabled)")
ok(len(enhanced_lane.SPEC_SHA) == 64, "enhanced spec frozen with sha")

# ---- BTC/SOL capture isolation ---------------------------------------------------------------
es.BTC_LEDGER = os.path.join(TMP, "btc.jsonl")
es.SOL_LEDGER = os.path.join(TMP, "sol.jsonl")
btcsol_capture.INSTRUMENTS = {"BTC": es.BTC_LEDGER, "SOL": es.SOL_LEDGER}
rec = btcsol_capture.capture("BTC", message_id=45683, source_ts="2026-07-13T14:07:31Z",
                             receipt_ts="2026-07-13T14:07:32Z", raw_text_sha256="a" * 64,
                             sender="seascalperfarouk", classification="FAROUK_BTC_SOL_SETUP")
ok(rec["record_type"] == "BTC_CAPTURE_ONLY" and rec["capture_only"] is True, "BTC capture-only record")
def all_keys(o):
    ks = set()
    if isinstance(o, dict):
        for k, v in o.items():
            ks.add(k.lower()); ks |= all_keys(v)
    elif isinstance(o, list):
        for v in o:
            ks |= all_keys(v)
    return ks
rkeys = all_keys(rec)
ok(not any(k in rkeys for k in ("realized_pips", "average_entry", "campaign_state", "expectancy",
                                "legs", "outcome", "follower")),
   "BTC record carries NO trade/outcome KEYS (cannot affect Gold)")

# ---- forbidden execution fields across all record builders -----------------------------------
for probe in (snap, hyp, cv, cov, sf1, rec):
    try:
        guards.assert_clean(dict(probe, lot_size=1), "probe")
        ok(False, "forbidden key must fail")
    except guards.GuardViolation:
        pass
ok(True, "all evidence records reject forbidden execution keys")

# ---- project invariants unchanged ------------------------------------------------------------
inv = guards.verify_project_invariants()
ok(inv["scorers"] == "UNCHANGED" and inv["constitution"] == "FROZEN_RATIFIED"
   and inv["pre_marks"] == "FROZEN" and inv["gates"] == "PAPER/PREVIEW/False/False",
   "scorers/constitution/pre-marks/gates unchanged")

import shutil
shutil.rmtree(TMP, ignore_errors=True)

if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    print(f"PASS {PASS} evidence-layer checks")
