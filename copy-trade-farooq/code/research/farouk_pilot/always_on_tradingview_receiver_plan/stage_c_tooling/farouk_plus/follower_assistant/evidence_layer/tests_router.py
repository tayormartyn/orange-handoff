"""Part 20 — deterministic tests for the hierarchical strategy router (RESEARCH-ONLY).

Sandboxes all ledger writes to a temp dir; NEVER touches live ledgers or the running watcher.
"""
from __future__ import annotations

import csv
import io
import json
import os
import sys
import tempfile
from decimal import Decimal as D
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
FA = os.path.dirname(HERE)
DR = os.path.join(FA, "detector_research")
for p in (HERE, FA, DR):
    if p not in sys.path:
        sys.path.insert(0, p)
import strategy_router as R                                        # noqa: E402
import evidence_schema as es                                      # noqa: E402
import evidence_watcher as W                                      # noqa: E402
import guards                                                     # noqa: E402

PASS = 0
FAIL = 0
PRICE = os.path.join(FA, "..", "..", "price_data",
                     "XAUUSD_1M_PEPPERSTONE_2026-07-08_to_2026-07-15_CANONICAL.csv")


def ok(name, cond):
    global PASS, FAIL
    if cond:
        PASS += 1
    else:
        FAIL += 1
        print(f"FAIL: {name}")


def load_bars():
    out = []
    for r in csv.reader(open(PRICE, encoding="utf-8-sig")):
        if not r or r[0] in ("time", ""):
            continue
        out.append((int(r[0]), D(r[1]), D(r[2]), D(r[3]), D(r[4])))
    out.sort()
    return out


BARS = load_bars()
DTS_F001 = int(datetime.fromisoformat("2026-07-14T08:38:06").replace(tzinfo=timezone.utc).timestamp())
DTS_F002 = int(datetime.fromisoformat("2026-07-14T13:26:21").replace(tzinfo=timezone.utc).timestamp())


def freeze(dts=DTS_F001, direction="LONG", lane="A_FOLLOWER", bars=None, backfill=True):
    return R.freeze_router(setup_id="XAU-FTEST-1", direction=direction, zone_low="4007",
                           zone_high="4019", sl="3985", decision_ts=dts, bars=bars if bars is not None else BARS,
                           objective_lane=lane, is_backfill=backfill)


# ---- 1) completed-bar cutoff + forming-candle exclusion ---------------------------------------
def test_completed_bar_cutoff():
    cb = R.causal_1m(BARS, DTS_F001)
    ok("every causal bar closes <= decision_ts", all(b[0] + 60 <= DTS_F001 for b in cb))
    ok("no bar opens at/after decision_ts survives", all(b[0] < DTS_F001 for b in cb))
    # a bar opening exactly at decision_ts (closes after) must be excluded
    synth = BARS + [(DTS_F001, D("1"), D("1"), D("1"), D("1"))]
    ok("forming bar (opens at dts) excluded", (DTS_F001, D("1"), D("1"), D("1"), D("1")) not in R.causal_1m(synth, DTS_F001))


# ---- 2) future-bar invariance (metamorphic) ---------------------------------------------------
def test_future_bar_invariance():
    base = freeze()
    future = [(DTS_F001 + 60 * i, D("9999"), D("9999"), D("9999"), D("9999")) for i in range(1, 200)]
    withfut = freeze(bars=BARS + future)
    ok("appending future bars leaves logical_hash unchanged", base["logical_hash"] == withfut["logical_hash"])
    ok("causal source hash unchanged", base["causality"]["source_hashes"] == withfut["causality"]["source_hashes"])


# ---- 2b) BLIND-REVIEW CRITICAL regression: decision-straddling bar cannot leak into feats -------
def test_straddling_bar_excluded():
    # the bar that opens before decision_ts but closes after it (open <= dts < open+60) must NOT
    # influence any frozen feature. smc._causal (open-time) would admit it; the fix feeds strict cb.
    straddle_idx = next((i for i, b in enumerate(BARS) if b[0] < DTS_F001 <= b[0] + 60), None)
    ok("a straddling bar exists in the data for this decision_ts", straddle_idx is not None)
    if straddle_idx is None:
        return
    poisoned = list(BARS)
    b = poisoned[straddle_idx]
    poisoned[straddle_idx] = (b[0], b[1], D("99999"), D("0.01"), D("99999"))  # extreme H/L/close
    base = freeze()
    withpoison = freeze(bars=poisoned)
    ok("straddling-bar poison does not change the freeze (excluded)",
       base["logical_hash"] == withpoison["logical_hash"])
    ok("poisoned extreme absent from frozen record", "99999" not in json.dumps(withpoison))


# ---- 3) source-tier + objective-lane isolation ------------------------------------------------
def test_tier_and_lane():
    a = freeze(lane="A_FOLLOWER")
    c = freeze(lane="C_INDEPENDENT")
    ok("source tier default TIER_2", "TIER_2" in a["hierarchy"]["1_source_tier"]["selected_value_if_predetermined"])
    ok("objective lane tagged A", a["objective_lane"] == "A_FOLLOWER")
    ok("objective lane tagged C", c["objective_lane"] == "C_INDEPENDENT")
    ok("lanes produce independent records (no shared mutable state)",
       a["hierarchy"]["2_objective_lane"]["selected_value_if_predetermined"] == "A_FOLLOWER"
       and c["hierarchy"]["2_objective_lane"]["selected_value_if_predetermined"] == "C_INDEPENDENT")


# ---- 4) regime/session UNKNOWN handling + no invented thresholds -------------------------------
def test_regime_session_unknown():
    rec = freeze()
    reg = rec["hierarchy"]["5_market_regime"]
    ok("regime selected UNKNOWN (never chosen)", reg["selected_value_if_predetermined"] == es.UNKNOWN)
    ok("regime always includes UNKNOWN candidate", any(c.get("state") == "UNKNOWN" for c in reg["candidate_values"]))
    ok("regime lists threshold unknowns", any("threshold" in u or "EMA" in u for u in reg["unknown_fields"]))
    sess = rec["hierarchy"]["6_session_model"]
    ok("session no-trade candidates present", len(sess["no_trade_timing_candidates"]) >= 1)
    # red-team M1/m1 regression: numeric session bands must be DISCLOSED, not silently baked
    uf = " ".join(sess["unknown_fields"])
    ok("midpoint tolerance disclosed in unknown_fields", "midpoint tolerance" in uf and "DISCLOSED" in uf)
    ok("Monday cutoff disclosed in unknown_fields", "Monday range cutoff" in uf)
    ok("disclosed assumptions block present", "disclosed_assumptions" in sess
       and sess["disclosed_assumptions"]["midpoint_band_fraction"] == "0.10")
    ok("NY-open discrepancy disclosed", "13:30" in uf and "NY_OPEN starts 12:00" in uf)


# ---- 5) crypto/weekend isolation --------------------------------------------------------------
def test_crypto_weekend_isolation():
    rec = freeze()
    blob = json.dumps(rec)
    ok("no weekend rule applied to XAU", "great strategy for the weekend" not in blob)
    po3 = [c for c in rec["hierarchy"]["5_market_regime"]["candidate_values"] if "PO3" in str(c.get("state"))]
    ok("PO3 candidate carries scope isolation", all("scope_isolation" in c for c in po3) if po3 else True)
    mtx = json.load(open(os.path.join(DR, "authority_instrument_scope_matrix_v0_1.json"), encoding="utf-8"))
    weekend = [s for s in mtx["statements"] if s.get("weekend_flag")]
    ok("matrix flags weekend statement as BTC_CRYPTO", all(s["scope"] == "BTC_CRYPTO" for s in weekend))


# ---- 6) structural priority + separation from candle layer ------------------------------------
def test_structural_priority_and_separation():
    rec = freeze()
    st = rec["hierarchy"]["9_structural_confirmation"]
    ranks = {c["trigger"]: c["rank"] for c in st["candidate_values"]}
    ok("BOS rank 1", ranks.get("BREAK_OF_STRUCTURE") == 1)
    ok("SFP rank 4", ranks.get("SWING_FAILURE_PATTERN") == 4)
    # strongest selected = lowest rank WITH evidence
    ev = [c for c in st["candidate_values"] if c.get("evidence") not in (es.UNKNOWN, None)]
    if ev:
        ok("selected = lowest-rank with evidence", st["selected_value_if_predetermined"] == min(ev, key=lambda c: c["rank"])["trigger"])
    cc = rec["hierarchy"]["10_completed_candle_confirmation"]
    ok("structural layer note present", "does NOT replace" in st["layer_note"])
    ok("candle layer separate", "separate from STRUCTURAL" in cc["layer_note"])
    ok("not all four structural required", len(st["candidate_values"]) == 4 and st["status"] == "STRUCTURAL_STATES_FROZEN")


# ---- 7) valid vs invalid BOS ------------------------------------------------------------------
def test_valid_bos():
    bos = freeze()["supplemental_contracts"]["valid_bos"]
    ok("BOS displacement stays UNKNOWN", any("displacement" in u for u in bos["unknown_fields"]))
    c0 = bos["candidate_values"][0]
    if isinstance(c0, dict):
        ok("records protected swing", "protected_swing_ts" in c0)
        ok("break flag boolean", isinstance(c0["break_beyond"], bool))
        ok("completed-close-beyond flag boolean", isinstance(c0["completed_close_beyond"], bool))
        ok("internal-swing rejection not hardcoded True (m5)", c0["internal_swing_rejection"] == es.UNKNOWN)


# ---- 8) execution-profile outcome-selection rejection -----------------------------------------
def test_execution_profile_no_selection():
    th = freeze()["hierarchy"]["3_trading_horizon"]
    ok("primary profile UNKNOWN", th["selected_value_if_predetermined"] == es.UNKNOWN)
    ok("multiple profiles preserved", len(th["candidate_values"]) >= 4)
    prof = json.load(open(os.path.join(DR, "execution_profiles_v0_1.json"), encoding="utf-8"))
    ok("profile contract forbids most-profitable pick", any("most profitable" in r for r in prof["rules"]))


# ---- 9) OTE cherry-picking rejection + all preserved ------------------------------------------
def test_ote_no_cherry_pick():
    ote = freeze()["supplemental_contracts"]["ote_shadow"]
    ok("OTE disabled", ote["disabled"] is True)
    ok("OTE not a scoring input", ote["not_a_scoring_input"] is True)
    ok("OTE anchor selection UNKNOWN", ote["selected_value_if_predetermined"] == es.UNKNOWN)
    ok("OTE documented levels 0.618/0.786", ote["documented_levels"] == ["0.618", "0.786"])
    ok("OTE extra levels flagged unverified", ote["unverified_levels"] == ["0.65", "0.705", "0.75", "0.79"])
    ok("OTE enumerates all pairs (count recorded)", ote["total_pairs_enumerated"] >= len(ote["candidate_values"]))
    # anchors must NOT be filtered toward the posted zone
    ok("no anchor chosen near Farouk zone", ote["activity"] == "INACTIVE")
    # m2 regression: BOTH polarities enumerated (SHORT not implicitly excluded)
    c0 = ote["candidate_values"][0] if ote["candidate_values"] else {}
    ok("OTE enumerates both long+short retrace polarities",
       "fib_levels_long_retrace" in c0 and "fib_levels_short_retrace" in c0)


# ---- 10) inducement not outcome-labelled ------------------------------------------------------
def test_inducement_no_hindsight():
    poi = freeze()["hierarchy"]["8_poi_family"]
    eq = [i for i in poi["candidate_values"] if isinstance(i, dict) and i.get("kind") == "EQUAL_LEVEL"]
    ok("equal levels carry hindsight guard", all("hindsight_guard" in e for e in eq) if eq else True)
    ok("POI preserves all role alternatives", set(poi["alternatives"]) == set(R.ROLE_ENUM))
    ok("inducement role never solely selected from outcome", poi["selected_value_if_predetermined"] == es.UNKNOWN)


# ---- 11) SCOB distinct from OB ----------------------------------------------------------------
def test_scob_distinct():
    rec = freeze()
    scob = rec["supplemental_contracts"]["scob"]
    ok("SCOB notes distinctness from OB", "not the multi-candle" in scob["distinct_from_ob"])
    ok("SCOB thresholds UNKNOWN", set(scob["unknown_fields"]) >= {"candle-strength", "displacement", "exact boundary"})


# ---- 12) Volume Profile fabrication rejection -------------------------------------------------
def test_vp_fail_closed():
    vp = freeze()["supplemental_contracts"]["volume_profile"]
    ok("VP data unavailable", vp["status"] == "VOLUME_PROFILE_DATA_UNAVAILABLE")
    ok("VAH/VAL/POC UNKNOWN", all(vp["candidate_values"][k] == es.UNKNOWN for k in ("VAH", "VAL", "POC")))
    ok("VP never fabricated from OHLC", "never fabricated" in vp["hard_rule"])


# ---- 13) inactive setup families cannot emit decisions ----------------------------------------
def test_inactive_families():
    fams = json.load(open(os.path.join(DR, "advanced_setup_family_contracts_v0_1.json"), encoding="utf-8"))
    ok("families declared inactive", fams["declared_inactive"] is True and fams["feature_capture_only"] is True)
    em = freeze()["hierarchy"]["11_entry_model"]
    ok("entry-model node INACTIVE", em["activity"] == "INACTIVE")
    ok("entry-model selects nothing", em["selected_value_if_predetermined"] == es.UNKNOWN)


# ---- 14) no live-state mutation + no execution/sizing fields (assert_clean) --------------------
def test_no_mutation_no_exec_fields():
    rec = freeze()
    # es.finalize already ran guards.assert_clean; re-assert explicitly
    guards.assert_clean(rec, "router_freeze")
    ok("stamps research-only", rec["review_only"] and not rec["executable"] and not rec["trade_ready"] and rec["observation_only"])
    ok("outputs class stamped", "NO_EXECUTION_CONSEQUENCE" in rec["outputs_class"])
    # constitution sha unchanged by importing/using the router
    import hashlib
    cpath = os.path.join(FA, "follower_constitution_v0_1.json")
    ok("constitution sha unchanged", hashlib.sha256(open(cpath, "rb").read()).hexdigest() == guards.CONSTITUTION_SHA)


# ---- 15) automatic campaign activation + watcher restart/idempotency (SANDBOXED) --------------
def test_sweep_activation_and_idempotency():
    tmp = tempfile.mkdtemp(prefix="router_test_")
    pre_path = os.path.join(tmp, "pre.jsonl")
    router_path = os.path.join(tmp, "router.jsonl")
    sid = "XAU-F900-SWEEPTEST"
    pre = {"record_type": "PRE_TRADE_SNAPSHOT", "setup_id": sid, "direction": "LONG",
           "zone": "4007-4019", "posted_stop": "3985",
           "timestamps": {"source_message_utc": "2026-07-14T08:38:06+00:00"}}
    open(pre_path, "w", encoding="utf-8").write(json.dumps(pre) + "\n")
    # sandbox the two ledger paths + firewall + analytical gate
    save = (es.PRE_TRADE_LEDGER, R.ROUTER_FREEZE_LEDGER, es.firewall_state, W.bq.is_analytical)
    es.PRE_TRADE_LEDGER = pre_path
    R.ROUTER_FREEZE_LEDGER = router_path
    es.firewall_state = lambda s: "OPEN"
    W.bq.is_analytical = lambda s: True
    try:
        cur = {"done": {}}
        a1 = W._router_freeze_sweep(sid, cur, BARS)
        ok("sweep activates a fresh OPEN analytical campaign", isinstance(a1, str) and a1.startswith(f"ROUTER_FREEZE({sid}"))
        n1 = sum(1 for _ in open(router_path, encoding="utf-8"))
        ok("one router record written", n1 == 1)
        # restart/idempotency: fresh cursor, same durable state -> NO duplicate
        a2 = W._router_freeze_sweep(sid, {"done": {}}, BARS)
        n2 = sum(1 for _ in open(router_path, encoding="utf-8"))
        ok("idempotent: no duplicate on re-run", n2 == 1 and a2 is None)
        # firewall CLOSED -> no freeze (blind ordering: only while OPEN)
        es.firewall_state = lambda s: "CLOSED"
        a3 = W._router_freeze_sweep("XAU-F901-CLOSED", {"done": {}}, BARS)
        ok("firewall CLOSED -> no freeze", a3 is None)
    finally:
        es.PRE_TRADE_LEDGER, R.ROUTER_FREEZE_LEDGER, es.firewall_state, W.bq.is_analytical = save


# ---- 16) router failure never blocks follower (fail-closed) -----------------------------------
def test_router_failure_isolated():
    save = R.ROUTER_FREEZE_LEDGER
    save_pre = es.PRE_TRADE_LEDGER
    save_fw = es.firewall_state
    save_an = W.bq.is_analytical
    try:
        es.firewall_state = lambda s: "OPEN"
        W.bq.is_analytical = lambda s: True
        # PRE_TRADE points at a valid file but freeze_router will be forced to throw
        tmp = tempfile.mkdtemp(prefix="router_fail_")
        pre_path = os.path.join(tmp, "pre.jsonl")
        sid = "XAU-F902-FAIL"
        open(pre_path, "w", encoding="utf-8").write(json.dumps({
            "record_type": "PRE_TRADE_SNAPSHOT", "setup_id": sid, "direction": "LONG",
            "zone": "4007-4019", "posted_stop": "3985",
            "timestamps": {"source_message_utc": "2026-07-14T08:38:06+00:00"}}) + "\n")
        es.PRE_TRADE_LEDGER = pre_path
        R.ROUTER_FREEZE_LEDGER = os.path.join(tmp, "router.jsonl")
        orig = R.freeze_router
        R.freeze_router = lambda **k: (_ for _ in ()).throw(RuntimeError("boom"))
        try:
            res = W._router_freeze_sweep(sid, {"done": {}}, BARS)
        finally:
            R.freeze_router = orig
        ok("sweep swallows freeze error (returns string, does not raise)", isinstance(res, str) and "ERROR" in res)
    finally:
        R.ROUTER_FREEZE_LEDGER = save
        es.PRE_TRADE_LEDGER = save_pre
        es.firewall_state = save_fw
        W.bq.is_analytical = save_an


# ---- 17) F001/F002 excluded from prospective metrics ------------------------------------------
def test_backfill_marked_not_prospective():
    rec = freeze(backfill=True)
    ok("backfill marker present", rec["backfill_marker"] == "SCHEMA_BACKFILL_NOT_PROSPECTIVE")
    ok("backfill not prospective-eligible", rec["eligible_for_prospective_evidence"] is False)
    ok("backfill not training-eligible", rec["eligible_for_training"] is False)
    prospective = freeze(backfill=False)
    ok("prospective marker distinct", prospective["backfill_marker"] == "PROSPECTIVE")
    ok("prospective is prospective-eligible", prospective["eligible_for_prospective_evidence"] is True)
    ok("prospective NEVER training-eligible", prospective["eligible_for_training"] is False)


# ---- 18) Section 6 — canonical serialization / tamper / reproducibility / envelope -------------
def test_hash_reproducibility_and_tamper():
    import strategy_router as _R
    a = freeze(); b = freeze()
    ok("HASH_REPRODUCIBILITY: identical inputs -> identical hash", a["logical_hash"] == b["logical_hash"])
    # canonical serialization: recomputing logical_hash from the record reproduces it byte-for-byte
    ok("CANONICAL_SERIALIZATION: deterministic recompute", es.logical_hash(a) == a["logical_hash"])
    # tamper-sensitivity across each covered causal input class
    poisoned_bars = list(BARS); poisoned_bars[200] = (poisoned_bars[200][0], D("1"), D("88888"), D("1"), D("1"))
    ok("TAMPER: bar edit changes hash", freeze(bars=poisoned_bars)["logical_hash"] != a["logical_hash"])
    ok("TAMPER: direction change changes hash", freeze(direction="SHORT")["logical_hash"] != a["logical_hash"])
    ok("TAMPER: decision_ts change changes hash", freeze(dts=DTS_F001 + 60)["logical_hash"] != a["logical_hash"])
    ok("TAMPER: lane change changes hash", freeze(lane="C_INDEPENDENT")["logical_hash"] != a["logical_hash"])


def test_hash_envelope_completeness():
    env = freeze()["hash_envelope"]
    required = ["router_version", "config_version", "contract_versions_sha256", "gate_snapshot",
               "replay_family_whitelist", "raw_source_ref", "campaign_provenance",
               "campaign_lifecycle_state", "normalized_proposal", "lane_refs",
               "market_data_cutoff_timestamp", "decision_timestamp", "activation_timestamp",
               "record_class", "eligible_for_prospective_evidence", "causal_1m_sha256",
               "outcome_data_available_at_freeze"]
    for k in required:
        ok(f"envelope has {k}", k in env)
    ok("contracts referenced by immutable sha256", all(c["sha256"] != es.UNKNOWN for c in env["contract_versions_sha256"]))
    ok("gate snapshot captures PAPER/PREVIEW/False/False", env["gate_snapshot"]["mode"] == "PAPER"
       and env["gate_snapshot"]["exec_flag"] == "False" and env["gate_snapshot"]["ctrader_flag"] == "False")
    ok("replay whitelist is exactly the 2 authorised families",
       env["replay_family_whitelist"] == ["FVG_CONTINUATION_5M", "ASIA_SESSION_FAKEOUT"])
    ok("lane A semantics frozen+known in envelope", env["lane_refs"]["A_FOLLOWER"]["semantics"] == "FROZEN_AND_KNOWN")
    ok("outcome data NOT available at freeze", env["outcome_data_available_at_freeze"] is False)
    ok("causal bar hash present in envelope", len(env["causal_1m_sha256"]) == 64)


# ---- 19) Section 9 — activation-clock classification (straddle protection) ---------------------
def test_activation_clock_classification():
    import strategy_router as _R
    act = 1_000_000
    ok("decision after activation -> PROSPECTIVE", _R.classify_activation(act + 60, act)[0] == "PROSPECTIVE")
    ok("decision at activation -> STRADDLE", _R.classify_activation(act, act)[0] == "ACTIVATION_STRADDLE")
    ok("decision before activation -> STRADDLE", _R.classify_activation(act - 60, act)[0] == "ACTIVATION_STRADDLE")
    ok("no marker -> conservative STRADDLE", _R.classify_activation(act, None)[0] == "ACTIVATION_STRADDLE")
    # straddle record is not prospective-eligible
    straddle = R.freeze_router(setup_id="XAU-FSTRAD", direction="LONG", zone_low="4007", zone_high="4019",
                               sl="3985", decision_ts=DTS_F001, bars=BARS, record_class="ACTIVATION_STRADDLE",
                               activation_ts=DTS_F001 + 999)
    ok("ACTIVATION_STRADDLE not prospective-eligible", straddle["eligible_for_prospective_evidence"] is False)


if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    for fn in [test_completed_bar_cutoff, test_future_bar_invariance, test_straddling_bar_excluded,
               test_tier_and_lane,
               test_regime_session_unknown, test_crypto_weekend_isolation,
               test_structural_priority_and_separation, test_valid_bos,
               test_execution_profile_no_selection, test_ote_no_cherry_pick,
               test_inducement_no_hindsight, test_scob_distinct, test_vp_fail_closed,
               test_inactive_families, test_no_mutation_no_exec_fields,
               test_sweep_activation_and_idempotency, test_router_failure_isolated,
               test_backfill_marked_not_prospective, test_hash_reproducibility_and_tamper,
               test_hash_envelope_completeness, test_activation_clock_classification]:
        fn()
    print(f"\n{PASS} passed, {FAIL} failed")
    sys.exit(1 if FAIL else 0)
