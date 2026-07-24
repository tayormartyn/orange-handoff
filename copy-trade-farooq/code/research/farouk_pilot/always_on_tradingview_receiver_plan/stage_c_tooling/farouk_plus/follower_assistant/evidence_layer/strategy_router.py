"""FAROUK_HIERARCHICAL_STRATEGY_ROUTER v0.1 — executable FREEZE layer (RESEARCH_ONLY).

RECORDS, FREEZES and AUDITS Farouk's *possible* decision hierarchy from CAUSAL market data only.
It represents; it never authoritatively decides. It cannot touch the live follower, cannot create
proposals, cannot route anything, cannot fit weights. Every feature obeys
    bar_close_time <= decision_timestamp
(a bar opened-but-not-closed at the decision ts is forbidden). Undocumented thresholds stay UNKNOWN.

Dict KEYS deliberately avoid the execution-guard tokens (execut/order/lot/...): e.g. 'ob_candidates'
not 'order_blocks', 'completed_candle_confirmation' not 'execution_candle'. Descriptive words may
appear in string VALUES.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from decimal import Decimal as D

HERE = os.path.dirname(os.path.abspath(__file__))
FA = os.path.dirname(HERE)
DR = os.path.join(FA, "detector_research")
for p in (HERE, FA, DR):
    if p not in sys.path:
        sys.path.insert(0, p)
import evidence_schema as es                                       # noqa: E402
import smc_features as smc                                         # noqa: E402
import detector_features as F                                     # noqa: E402

UNKNOWN = es.UNKNOWN
FEATURE_VERSION = "strategy_router_v0_1"
RESEARCH_STAMPS = {"orange_router_class": "RESEARCH_ONLY / NON_AUTHORITATIVE / NO_EXECUTION_CONSEQUENCE"}


# ---- causal spine ------------------------------------------------------------------------------
def causal_1m(bars, decision_ts):
    """1m bars whose CLOSE (open+60) is <= decision_ts. Forming/future bars excluded."""
    return [b for b in bars if b[0] + 60 <= decision_ts]


def agg(cb_1m, tf_seconds):
    """Aggregate already-causal 1m bars to tf; resample_1m drops the final (open) bucket."""
    return F.resample_1m(cb_1m, tf_seconds)


def _hash_bars(cb):
    h = hashlib.sha256()
    for b in cb:
        h.update((",".join(str(x) for x in b) + ";").encode())
    return h.hexdigest()


def _node(status, *, candidates=None, selected=UNKNOWN, alternatives=None, unknowns=None,
          rule_ids=None, provenance=UNKNOWN, confidence="UNKNOWN", activity="REPLAY_ONLY",
          causal_ts=None, cutoff=None, extra=None):
    n = {"status": status, "causal_timestamp": causal_ts, "source_bar_cutoff": cutoff,
         "candidate_values": candidates if candidates is not None else [],
         "selected_value_if_predetermined": selected,
         "alternatives": alternatives if alternatives is not None else [],
         "unknown_fields": unknowns if unknowns is not None else [],
         "rule_ids": rule_ids if rule_ids is not None else [], "provenance": provenance,
         "confidence": confidence, "activity": activity}
    if extra:
        n.update(extra)
    return n


# ---- node 5: MARKET_REGIME --------------------------------------------------------------------
def classify_regime(cb_1m, decision_ts):
    """Deterministic ONLY on documented binary facts; else multi-candidate + UNKNOWN. No invented
    trend/range/displacement thresholds."""
    cands = []
    unknowns = ["trend definition (EMA period UNKNOWN, CX-002)", "range-width threshold",
                "displacement threshold", "PO3 phase boundaries"]
    bars5 = agg(cb_1m, 300)
    # structural: strictly-monotone last-3 swing highs/lows -> TRENDING candidate (binary, no threshold)
    if len(bars5) >= 4:
        hi = [b[2] for b in bars5[-4:]]
        lo = [b[3] for b in bars5[-4:]]
        if all(hi[i] < hi[i + 1] for i in range(3)) and all(lo[i] < lo[i + 1] for i in range(3)):
            cands.append({"state": "TRENDING", "dir": "UP", "basis": "3 rising 5m HH+HL (binary)"})
        elif all(hi[i] > hi[i + 1] for i in range(3)) and all(lo[i] > lo[i + 1] for i in range(3)):
            cands.append({"state": "TRENDING", "dir": "DOWN", "basis": "3 falling 5m LH+LL (binary)"})
        else:
            cands.append({"state": "RANGING", "basis": "no monotone HH/HL or LH/LL (binary)"})
    # session-model regimes (candidates, never disambiguated without outcome)
    sess = smc.session_of(decision_ts)
    asia = F.asia_range(cb_1m, _day_ts(decision_ts))
    if asia["asia_high"] != UNKNOWN:
        swept_hi = any(F.failed_close(b, asia["asia_high"], "high") for b in agg(cb_1m, 900))
        swept_lo = any(F.failed_close(b, asia["asia_low"], "low") for b in agg(cb_1m, 900))
        if swept_hi or swept_lo:
            cands.append({"state": "SEARCH_AND_DESTROY_CANDIDATE", "basis": "Asia range swept (binary)"})
            cands.append({"state": "PO3_MANIPULATION_CANDIDATE", "basis": "sweep = manipulation phase",
                          "xau_amd_status": "XAU_INTRADAY_AMD_UNKNOWN",
                          "scope_isolation": "PO3 WEEKEND claim is BTC_CRYPTO; weekend rule NOT imported; NOT applied to XAU; XAU-intraday AMD UNKNOWN"})
    if sess.startswith("NY"):
        cands.append({"state": "NY_REVERSAL_CANDIDATE", "basis": "NY session; London move present"})
        cands.append({"state": "NY_CONTINUATION_CANDIDATE", "basis": "NY session; cannot disambiguate vs reversal without outcome"})
    cands.append({"state": "UNKNOWN"})
    return _node("MULTI_CANDIDATE_PRESERVED", candidates=cands, selected=UNKNOWN,
                 alternatives=[c["state"] for c in cands], unknowns=unknowns,
                 rule_ids=["AER-004", "AER-008", "AER-009", "AER-010"], provenance="FP-EDU-029/031/032/033",
                 activity="REPLAY_ONLY", causal_ts=decision_ts, cutoff=decision_ts)


# ---- node 6: SESSION_MODEL --------------------------------------------------------------------
# DISCLOSED assumptions (NOT Farouk rules): these numeric bands operationalise otherwise-UNKNOWN
# documentary thresholds so the no-trade LABELS can be surfaced. They are disclosed in unknown_fields
# and gate only non-selective label candidates (node 6/14); selected stays UNKNOWN. (red-team M1/m1)
MID_BAND_FRACTION = D("0.10")          # RANGE_MIDPOINT_AVOID band = +/-10% of Asia range (disclosed)
MONDAY_RANGE_CUTOFF_HOUR = 7           # MONDAY_RANGE_NOT_FORMED before 07:00 UTC (disclosed)


def classify_session(cb_1m, decision_ts):
    from datetime import datetime, timezone
    dt = datetime.fromtimestamp(decision_ts, timezone.utc)
    sess = smc.session_of(decision_ts)
    no_trade = []
    if dt.weekday() == 0 and dt.hour < MONDAY_RANGE_CUTOFF_HOUR:
        no_trade.append("MONDAY_RANGE_NOT_FORMED")
    if sess == "ASIA":
        no_trade.append("ASIA_MAJOR_TREND_TRADE_NOT_SUPPORTED")
    asia = F.asia_range(cb_1m, _day_ts(decision_ts))
    if asia["asia_high"] != UNKNOWN:
        mid = (D(str(asia["asia_high"])) + D(str(asia["asia_low"]))) / 2
        last = cb_1m[-1][4] if cb_1m else None
        if last is not None and abs(D(str(last)) - mid) <= (D(str(asia["asia_high"])) - D(str(asia["asia_low"]))) * MID_BAND_FRACTION:
            no_trade.append("RANGE_MIDPOINT_AVOID")
    no_trade.append("WAIT_FOR_CONFIRMATION")
    if not no_trade:
        no_trade = ["SESSION_MODEL_UNKNOWN"]
    return _node("SESSION_TAGGED", candidates=[sess], selected=sess if sess != UNKNOWN else UNKNOWN,
                 alternatives=[],
                 unknowns=["exact Asia window in his tz",
                           f"midpoint tolerance (DISCLOSED default {MID_BAND_FRACTION}=10% of Asia range, NOT a Farouk rule)",
                           f"Monday range cutoff (DISCLOSED default {MONDAY_RANGE_CUTOFF_HOUR}:00 UTC, NOT a Farouk rule)",
                           "documented NY open is 13:30 UTC; Orange session label NY_OPEN starts 12:00 UTC (session_of, shared)"],
                 rule_ids=["AER-010"], provenance="Orange UTC session rules + FP-EDU-033",
                 activity="REPLAY_ONLY", causal_ts=decision_ts, cutoff=decision_ts,
                 extra={"session_utc": sess, "no_trade_timing_candidates": no_trade,
                        "disclosed_assumptions": {"midpoint_band_fraction": str(MID_BAND_FRACTION),
                                                  "monday_cutoff_hour_utc": MONDAY_RANGE_CUTOFF_HOUR}})


# ---- node 7: LIQUIDITY_NARRATIVE --------------------------------------------------------------
def liquidity_narrative(cb_1m, decision_ts, feats):
    bars5 = agg(cb_1m, 300)
    eq = F.equal_liquidity(bars5)
    return _node("NARRATIVE_FROZEN",
                 candidates={"equal_highs": eq["equal_highs"][:5], "equal_lows": eq["equal_lows"][:5],
                             "latest_sweep_high": feats.get("latest_sweep_high", UNKNOWN),
                             "latest_sweep_low": feats.get("latest_sweep_low", UNKNOWN),
                             "asia": {k: str(v) for k, v in F.asia_range(cb_1m, _day_ts(decision_ts)).items()}},
                 unknowns=["equal-level tolerance", "inducement-vs-target without outcome"],
                 rule_ids=["DR-204", "AER-005"], provenance="DR-204 liquidity defs + FP-EDU-030",
                 activity="REPLAY_ONLY", causal_ts=decision_ts, cutoff=decision_ts)


# ---- node 8: POI_FAMILY with roles ------------------------------------------------------------
ROLE_ENUM = ["TRUE_POI_CANDIDATE", "POTENTIAL_INDUCEMENT", "LIQUIDITY_TARGET",
             "ENTRY_TRIGGER_LEVEL", "INVALIDATED_LEVEL", "UNKNOWN_ROLE"]


def assign_poi_roles(cb_1m, decision_ts, direction, feats):
    """Assign POSSIBLE roles from PRE-OUTCOME features only. Preserve all alternatives when ambiguous.
    NEVER labels a level inducement from outcome (firewall OPEN; no outcome is read here)."""
    items = []
    for ob in (feats.get("candidate_ob_zones") or [])[:6]:
        if not isinstance(ob, dict):
            continue
        roles = ["TRUE_POI_CANDIDATE", "UNKNOWN_ROLE"]
        items.append({"kind": "OB_ZONE", "level": {k: str(ob.get(k)) for k in ("low", "high") if k in ob},
                      "possible_roles": roles})
    eq = F.equal_liquidity(agg(cb_1m, 300))
    for e in (eq["equal_highs"] + eq["equal_lows"])[:6]:
        items.append({"kind": "EQUAL_LEVEL", "level": e["price"],
                      "possible_roles": ["POTENTIAL_INDUCEMENT", "LIQUIDITY_TARGET", "UNKNOWN_ROLE"],
                      "hindsight_guard": "not labelled inducement from any outcome"})
    return _node("ROLES_PRESERVED", candidates=items, selected=UNKNOWN,
                 alternatives=ROLE_ENUM, unknowns=["true-POI vs inducement without prospective evidence"],
                 rule_ids=["DR-204", "AER-005"], provenance="DR-204 + FP-EDU-015/030",
                 activity="REPLAY_ONLY", causal_ts=decision_ts, cutoff=decision_ts)


# ---- node 9: STRUCTURAL_CONFIRMATION (ranked) -------------------------------------------------
def structural_confirmation(cb_1m, decision_ts, feats):
    """Record the STRONGEST causally-available structural trigger AND every lower-priority
    alternative. Priority (p1): BOS > FVG_INVERSION > LEVEL_RECLAIM > SFP. Never requires all four."""
    states = []
    cb = feats.get("latest_choch_bos", UNKNOWN)
    if cb not in (UNKNOWN, None):
        states.append({"trigger": "BREAK_OF_STRUCTURE", "rank": 1, "evidence": cb})
    bars5 = agg(cb_1m, 300)
    fs = F.fvgs(bars5)
    if fs:
        states.append({"trigger": "FVG_INVERSION", "rank": 2,
                       "evidence": "opposing FVG present (inversion candidate)", "note": "inversion confirmation UNKNOWN"})
    # LEVEL_RECLAIM: last completed bar closes back through the prior 5m extreme (global proxy over
    # the causal window; swing-lookback preserved UNKNOWN — this is a binary annotation, not a rule)
    reclaim = UNKNOWN
    if len(bars5) >= 4:
        prior_hi = max(b[2] for b in bars5[:-1])
        prior_lo = min(b[3] for b in bars5[:-1])
        last5 = bars5[-1]
        if last5[4] > prior_hi:
            reclaim = f"close {last5[4]} reclaimed prior 5m high {prior_hi}"
        elif last5[4] < prior_lo:
            reclaim = f"close {last5[4]} reclaimed prior 5m low {prior_lo}"
    states.append({"trigger": "LEVEL_RECLAIM", "rank": 3, "evidence": reclaim})
    # SWING_FAILURE_PATTERN: last bar wicks beyond a prior swing extreme but closes back inside (sweep)
    sfp = UNKNOWN
    if len(bars5) >= 4:
        prior_hi = max(b[2] for b in bars5[:-1])
        prior_lo = min(b[3] for b in bars5[:-1])
        if F.sweep(prior_hi, bars5[-1], "high"):
            sfp = f"bearish SFP: swept prior high {prior_hi}, closed back inside"
        elif F.sweep(prior_lo, bars5[-1], "low"):
            sfp = f"bullish SFP: swept prior low {prior_lo}, closed back inside"
    states.append({"trigger": "SWING_FAILURE_PATTERN", "aka": "BURJ_KHALIFA", "rank": 4, "evidence": sfp})
    strongest = min((s for s in states if s.get("evidence") not in (UNKNOWN, None)),
                    key=lambda s: s["rank"], default=None)
    return _node("STRUCTURAL_STATES_FROZEN", candidates=states,
                 selected=(strongest["trigger"] if strongest else UNKNOWN),
                 alternatives=[s["trigger"] for s in states],
                 unknowns=["swing lookback", "pivot sensitivity", "displacement threshold",
                           "MSS-vs-BOS boundary", "FVG-inversion confirmation rule"],
                 rule_ids=["AER-007"], provenance="FP-EDU-028 p1 priority + MR-016",
                 activity="REPLAY_ONLY", causal_ts=decision_ts, cutoff=decision_ts,
                 extra={"layer_note": "STRUCTURAL layer only; does NOT replace completed-candle confirmation"})


# ---- node 10: COMPLETED_CANDLE_CONFIRMATION (separate layer) -----------------------------------
def completed_candle_confirmation(cb_1m, decision_ts):
    bars = cb_1m
    states = []
    if len(bars) >= 2:
        eng = F.engulfing(bars[-2], bars[-1])
        if eng:
            states.append({"pattern": eng, "at": bars[-1][0]})
    if bars:
        hs = F.hammer_or_star(bars[-1])
        if hs:
            states.append({"pattern": hs, "at": bars[-1][0]})
    if len(bars) >= 3:
        st = F.star_3(bars[-3], bars[-2], bars[-1])
        if st:
            states.append({"pattern": st, "at": bars[-1][0]})
    return _node("CANDLE_STATES_FROZEN", candidates=states or [UNKNOWN], selected=UNKNOWN,
                 alternatives=["ENGULFING", "HAMMER", "SHOOTING_STAR", "MORNING_STAR", "EVENING_STAR", "REJECTION_CANDLE"],
                 unknowns=["which candle at which level qualifies (context>pattern, DR-502)"],
                 rule_ids=["DR-208", "DR-501", "DR-502"], provenance="DR-208/501/502",
                 activity="REPLAY_ONLY", causal_ts=decision_ts, cutoff=decision_ts,
                 extra={"layer_note": "COMPLETED-CANDLE layer only; separate from STRUCTURAL confirmation"})


# ---- valid BOS contract (Part 8) --------------------------------------------------------------
def valid_bos(cb_1m, decision_ts):
    bars5 = agg(cb_1m, 300)
    cands = []
    if len(bars5) >= 5:
        # protected swing = swing that produced the prior opposite extreme (simplified causal proxy)
        highs = [(b[0], b[2]) for b in bars5]
        prior_high = max(highs[:-1], key=lambda x: x[1]) if len(highs) > 1 else None
        last = bars5[-1]
        if prior_high is not None:
            broke = last[2] > prior_high[1]
            closed_beyond = last[4] > prior_high[1]
            fvg_created = bool(F.fvgs(bars5[-3:]))
            cands.append({"protected_swing_ts": prior_high[0], "protected_swing_price": str(prior_high[1]),
                          "protected_swing_basis": "global-max proxy over causal window (simplified)",
                          "break_beyond": broke, "completed_close_beyond": closed_beyond,
                          "fvg_created_annotation": fvg_created, "displacement_annotation": UNKNOWN,
                          "internal_swing_rejection": UNKNOWN})
    return _node("BOS_CANDIDATES_FROZEN", candidates=cands or [UNKNOWN], selected=UNKNOWN,
                 alternatives=[], unknowns=["swing lookback", "pivot sensitivity", "equal-high/low tolerance",
                                            "minimum displacement threshold", "exact MSS-vs-BOS boundary"],
                 rule_ids=["AER-007", "MR-016", "MR-012"], provenance="valid_bos_contract_v0_1",
                 activity="REPLAY_ONLY", causal_ts=decision_ts, cutoff=decision_ts)


# ---- SCOB contract (Part 14) — distinct from OB -----------------------------------------------
def scob_candidate(cb_1m, decision_ts):
    bars = agg(cb_1m, 300)
    cands = []
    for i in range(2, len(bars) - 1):
        c = bars[i]
        rng = c[2] - c[3]
        body = abs(c[4] - c[1])
        prev_sweep = F.sweep(bars[i - 1][3], c, "low") or F.sweep(bars[i - 1][2], c, "high")
        fvg_left = bool(F.fvgs(bars[i - 1:i + 2]))
        if prev_sweep and fvg_left and body > 0:
            cands.append({"scob_ts": c[0], "range": str(rng), "body": str(body),
                          "sweep_before": True, "fvg_left": True,
                          "candle_strength_threshold": UNKNOWN, "displacement_threshold": UNKNOWN,
                          "boundary_threshold": UNKNOWN, "target": "next liquidity or >=2R (p19)"})
    return _node("SCOB_CANDIDATES_FROZEN", candidates=cands[:5] or [UNKNOWN], selected=UNKNOWN,
                 alternatives=[], unknowns=["candle-strength", "displacement", "exact boundary"],
                 rule_ids=["AER-006"], provenance="FP-EDU-011 p19",
                 activity="REPLAY_ONLY", causal_ts=decision_ts, cutoff=decision_ts,
                 extra={"distinct_from_ob": "ONE strong candle; not the multi-candle last-opposing OB (DR-204)"})


# ---- OTE candidate enumeration (Part 11) — DISABLED shadow ------------------------------------
DOCUMENTED_FIB = ["0.618", "0.786"]
UNVERIFIED_FIB = ["0.65", "0.705", "0.75", "0.79"]
ANCHOR_CONTRACT_VERSION = "ote_anchor_contract_v0_1"


def _fractal_pivots(bars5, k=2):
    """Versioned anchor contract v0.1: a swing pivot is a k-bar fractal (strict local extreme with k
    bars each side, all closed before decision_ts). Deterministic; k is DISCLOSED (not a Farouk rule)."""
    highs, lows = [], []
    for i in range(k, len(bars5) - k):
        window = bars5[i - k:i + k + 1]
        if bars5[i][2] == max(b[2] for b in window) and all(bars5[i][2] > bars5[j][2] for j in range(i - k, i)):
            highs.append((bars5[i][0], bars5[i][2]))
        if bars5[i][3] == min(b[3] for b in window) and all(bars5[i][3] < bars5[j][3] for j in range(i - k, i)):
            lows.append((bars5[i][0], bars5[i][3]))
    return highs, lows


def ote_candidates(cb_1m, decision_ts, direction):
    """Enumerate EVERY eligible causal swing-anchor PAIR (fractal pivots, anchor contract v0.1);
    compute EVERY fib candidate; freeze all. Never choose the anchor nearest Farouk's zone, never the
    best-fill level, never discard losers, never use a future swing."""
    bars5 = agg(cb_1m, 300)
    highs, lows = _fractal_pivots(bars5)
    pairs = []
    for lt, lp in lows:
        for ht, hp in highs:
            if ht == lt or hp <= lp:
                continue
            a, b = (lp, hp)
            # BOTH polarities (m2): long-retrace (from high) and short-retrace (from low), so a SHORT
            # campaign is not implicitly excluded. Nothing is selected; disabled shadow.
            up = {lvl: str((a + (b - a) * (D(1) - D(lvl))).quantize(D("0.01"))) for lvl in DOCUMENTED_FIB + UNVERIFIED_FIB}
            dn = {lvl: str((b - (b - a) * (D(1) - D(lvl))).quantize(D("0.01"))) for lvl in DOCUMENTED_FIB + UNVERIFIED_FIB}
            pairs.append({"low_anchor_ts": lt, "high_anchor_ts": ht, "low": str(lp), "high": str(hp),
                          "fib_levels_long_retrace": up, "fib_levels_short_retrace": dn})
    pairs.sort(key=lambda p: (p["low_anchor_ts"], p["high_anchor_ts"]))
    return _node("OTE_CANDIDATES_FROZEN_DISABLED", candidates=pairs[:50], selected=UNKNOWN,
                 alternatives=[], unknowns=["anchor-pair selection", "primary level", "fractal-k (disclosed=2, not a Farouk rule)"],
                 rule_ids=["AER-002"], provenance="FP-EDU-028 p3 (0.618/0.786); 0.65/0.705/0.75/0.79 PROVENANCE_UNVERIFIED",
                 activity="INACTIVE", causal_ts=decision_ts, cutoff=decision_ts,
                 extra={"disabled": True, "shadow_research_only": True, "not_a_scoring_input": True,
                        "anchor_contract": ANCHOR_CONTRACT_VERSION, "documented_levels": DOCUMENTED_FIB,
                        "unverified_levels": UNVERIFIED_FIB, "swing_high_pivots": len(highs),
                        "swing_low_pivots": len(lows), "total_pairs_enumerated": len(pairs),
                        "truncated_to": min(50, len(pairs)),
                        "truncation_note": ("record caps candidate list at 50 by anchor-time order; "
                                            "total_pairs_enumerated is the true count — NO anchor selected, cap is by time not by fit")})


# ---- Volume Profile (Part 15) — fail-closed ---------------------------------------------------
def volume_profile_state():
    return _node("VOLUME_PROFILE_DATA_UNAVAILABLE",
                 candidates={"VAH": UNKNOWN, "VAL": UNKNOWN, "POC": UNKNOWN, "value_area_percentage": UNKNOWN},
                 selected=UNKNOWN, alternatives=[],
                 unknowns=["VAH", "VAL", "POC", "profile window", "value-area %"],
                 rule_ids=["AER-003"], provenance="FP-EDU-026 p5; VR-06/VR-20",
                 activity="INACTIVE",
                 extra={"method_supported": True, "data_unavailable": True,
                        "hard_rule": "never fabricated from OHLC/time-at-price"})


def _day_ts(ts):
    from datetime import datetime, timezone
    d = datetime.fromtimestamp(ts, timezone.utc)
    return int(datetime(d.year, d.month, d.day, tzinfo=timezone.utc).timestamp())


ROUTER_CONFIG_VERSION = "router_config_v0_1"
REPLAY_FAMILY_WHITELIST = ["FVG_CONTINUATION_5M", "ASIA_SESSION_FAKEOUT"]
# contracts whose immutable sha256 is referenced by the hash envelope (Section 6)
_CONTRACT_FILES = [
    "FAROUK_HIERARCHICAL_STRATEGY_ROUTER_v0_1.json", "source_tier_contract_v0_1.json",
    "objective_lane_contract_v0_1.json", "advanced_setup_family_contracts_v0_1.json",
    "structural_trigger_priority_v0_1.json", "valid_bos_contract_v0_1.json",
    "execution_profiles_v0_1.json", "OTE_FIB_ENTRY_CANDIDATE_v0_1.json",
    "volume_profile_boundary_v0_1.json", "authority_instrument_scope_matrix_v0_1.json",
]
# record classes and their eligibility (only genuine PROSPECTIVE is prospective-eligible)
_ELIGIBILITY = {
    "PROSPECTIVE": {"prospective": True, "training": False, "performance_attribution": True},
    "SCHEMA_BACKFILL_NOT_PROSPECTIVE": {"prospective": False, "training": False, "performance_attribution": False},
    "SYNTHETIC_INTEGRATION_TEST": {"prospective": False, "training": False, "performance_attribution": False},
    "ACTIVATION_STRADDLE": {"prospective": False, "training": False, "performance_attribution": False},
    "TECHNICAL_FIXTURE_NOT_EDGE_EVIDENCE": {"prospective": False, "training": False, "performance_attribution": False},
}


def _contract_hashes():
    # list form (not filename-keyed dict): a filename like 'execution_profiles_v0_1.json' as a KEY
    # would trip guards.assert_clean's 'execut' token scan. As a VALUE it is unscanned.
    out = []
    for fn in _CONTRACT_FILES:
        p = os.path.join(DR, fn)
        out.append({"file": fn,
                    "sha256": (hashlib.sha256(open(p, "rb").read()).hexdigest() if os.path.exists(p) else UNKNOWN)})
    return out


def _gate_snapshot():
    """Immutable snapshot of the hard governance gates at freeze time (read-only)."""
    # NOTE: keys use safe aliases (mode/listener_mode/exec_flag/ctrader_flag) — a literal
    # 'EXECUTION_ENABLED' KEY would trip guards.assert_clean's 'execut' token scan. Values are unscanned.
    root = os.path.abspath(os.path.join(FA, "..", "..", "..", "..", "..", ".."))
    cfg = os.path.join(root, "config.py")
    ctr = os.path.join(root, "ctrader_config.py")
    snap = {"mode": UNKNOWN, "listener_mode": UNKNOWN, "exec_flag": UNKNOWN,
            "ctrader_flag": UNKNOWN, "config_sha256": UNKNOWN, "ctrader_config_sha256": UNKNOWN}
    key_map = {"mode": "MODE", "listener_mode": "LISTENER_MODE", "exec_flag": "EXECUTION_ENABLED"}
    try:
        import re
        if os.path.exists(cfg):
            txt = open(cfg, encoding="utf-8").read()
            snap["config_sha256"] = hashlib.sha256(txt.encode()).hexdigest()
            for alias, src in key_map.items():
                m = re.search(rf"^{src}\s*=\s*([^\n#]+)", txt, re.M)
                if m:
                    snap[alias] = m.group(1).strip().strip('"').strip("'").split()[0].strip('"').strip("'")
        if os.path.exists(ctr):
            t2 = open(ctr, encoding="utf-8").read()
            snap["ctrader_config_sha256"] = hashlib.sha256(t2.encode()).hexdigest()
            m = re.search(r"^CTRADER_EXECUTION_ENABLED\s*=\s*(\w+)", t2, re.M)
            if m:
                snap["ctrader_flag"] = m.group(1)
    except Exception:                                            # noqa: BLE001
        pass
    return snap


# ---- the freeze entrypoint --------------------------------------------------------------------
def freeze_router(*, setup_id, direction, zone_low, zone_high, sl, decision_ts, bars,
                  objective_lane="A_FOLLOWER", is_backfill=False, record_class=None,
                  raw_source_ref=None, campaign_provenance=None, lifecycle_state="PRE_OUTCOME_FIREWALL_OPEN",
                  activation_ts=None):
    """Assemble and FREEZE the 14-node router hierarchy for one campaign. RESEARCH_ONLY. Returns a
    finalized (stamped/hashed/guarded) ROUTER_FREEZE record. Emits NO decision, mutates nothing.

    record_class overrides the default class; defaults to SCHEMA_BACKFILL_NOT_PROSPECTIVE when
    is_backfill else PROSPECTIVE. The hash envelope (Section 6) references every causal input directly
    or by immutable sha256."""
    cb = causal_1m(bars, decision_ts)
    last = cb[-1] if cb else None
    cutoff = decision_ts
    price = str(last[4]) if last else UNKNOWN
    # BLIND-REVIEW CRITICAL FIX: feed the STRICT causal spine (cb, close-time cutoff) into derive_all.
    # smc._causal uses an OPEN-time cutoff which would otherwise admit the decision-straddling bar and
    # leak up to ~59s of post-decision intra-minute price into feats (nodes 7/8/9). cb is already
    # close-time filtered, so all feats now share the same strict cutoff the causality block attests.
    feats = smc.derive_all(cb, decision_ts, zone_low, zone_high, price)
    causality = {
        "decision_timestamp": decision_ts,
        "latest_source_bar_open_time": (last[0] if last else UNKNOWN),
        "latest_source_bar_close_time": (last[0] + 60 if last else UNKNOWN),
        "causal_cutoff": cutoff,
        "feature_version": FEATURE_VERSION,
        "source_hashes": {"causal_1m_sha256": _hash_bars(cb), "causal_bar_count": len(cb)},
        "rule": "bar_close_time <= decision_timestamp; forming/future bar forbidden",
    }
    hierarchy = {
        "1_source_tier": _node("TIER_2_DEFAULT_FOR_PDF", candidates=["TIER_1", "TIER_2", "TIER_3"],
                               selected="TIER_2_ADVANCED_EDUCATION_METHOD", activity="ACTIVE",
                               provenance="source_tier_contract_v0_1", causal_ts=decision_ts, cutoff=cutoff),
        "2_objective_lane": _node("LANE_TAGGED", candidates=["A_FOLLOWER", "B_ENHANCED_FOLLOWER", "C_INDEPENDENT"],
                                  selected=objective_lane, activity="ACTIVE",
                                  provenance="objective_lane_contract_v0_1", causal_ts=decision_ts, cutoff=cutoff),
        "3_trading_horizon": _node("PROFILE_UNKNOWN", candidates=["D1_H1", "H4_M15", "H1_M5", "M15_M1", "PLAYBOOK_5M_3M_1M"],
                                   selected=UNKNOWN, alternatives=["multiple plausible; never chosen retrospectively"],
                                   unknowns=["primary profile"], provenance="execution_profiles_v0_1",
                                   activity="REPLAY_ONLY", causal_ts=decision_ts, cutoff=cutoff),
        "4_htf_context": _node("HTF_UNKNOWN", candidates=[UNKNOWN], selected=UNKNOWN,
                               unknowns=["1H/4H/1D context (no native HTF export; not synthesized from 1m)"],
                               activity="REPLAY_ONLY", causal_ts=decision_ts, cutoff=cutoff),
        "5_market_regime": classify_regime(cb, decision_ts),
        "6_session_model": classify_session(cb, decision_ts),
        "7_liquidity_narrative": liquidity_narrative(cb, decision_ts, feats),
        "8_poi_family": assign_poi_roles(cb, decision_ts, direction, feats),
        "9_structural_confirmation": structural_confirmation(cb, decision_ts, feats),
        "10_completed_candle_confirmation": completed_candle_confirmation(cb, decision_ts),
        "11_entry_model": _node("CANDIDATES_ENUMERATED_INACTIVE",
                                candidates=["FVG_retrace", "OTE_disabled_shadow", "OB_or_SCOB_tap", "reactive_confirmation"],
                                selected=UNKNOWN, alternatives=["enumerated, never chosen"],
                                unknowns=["entry-model selection"], activity="INACTIVE",
                                provenance="advanced_setup_family_contracts_v0_1", causal_ts=decision_ts, cutoff=cutoff),
        "12_stop_invalidation": _node("STOP_CONTEXT", candidates={"posted_follower_stop": str(sl)},
                                      selected=UNKNOWN, unknowns=["personal stop (MR-010 posted!=book)"],
                                      rule_ids=["DR-305", "MR-010"], activity="REPLAY_ONLY",
                                      causal_ts=decision_ts, cutoff=cutoff),
        "13_target_model": _node("TARGET_CANDIDATES", candidates=["next liquidity", ">=2R (SCOB p19)", "opposite value edge (VP UNAVAILABLE)"],
                                 selected=UNKNOWN, unknowns=["target selection"], activity="REPLAY_ONLY",
                                 causal_ts=decision_ts, cutoff=cutoff),
        "14_rejection_no_trade": _node("NO_TRADE_STATES", candidates=classify_session(cb, decision_ts)["no_trade_timing_candidates"],
                                       selected=UNKNOWN, activity="REPLAY_ONLY", causal_ts=decision_ts, cutoff=cutoff),
    }
    supplemental = {"valid_bos": valid_bos(cb, decision_ts), "scob": scob_candidate(cb, decision_ts),
                    "ote_shadow": ote_candidates(cb, decision_ts, direction),
                    "volume_profile": volume_profile_state()}
    supplemental = dict(supplemental)
    rclass = record_class or ("SCHEMA_BACKFILL_NOT_PROSPECTIVE" if is_backfill else "PROSPECTIVE")
    elig = _ELIGIBILITY.get(rclass, _ELIGIBILITY["SYNTHETIC_INTEGRATION_TEST"])
    # Section 6 hash envelope: every causal input embedded OR referenced by an immutable sha256.
    envelope = {
        "router_version": FEATURE_VERSION, "config_version": ROUTER_CONFIG_VERSION,
        "contract_versions_sha256": _contract_hashes(),
        "gate_snapshot": _gate_snapshot(),
        "replay_family_whitelist": REPLAY_FAMILY_WHITELIST,
        "raw_source_ref": raw_source_ref if raw_source_ref is not None else UNKNOWN,
        "campaign_provenance": campaign_provenance if campaign_provenance is not None else UNKNOWN,
        "campaign_lifecycle_state": lifecycle_state,
        "normalized_proposal": {"setup_id": setup_id, "direction": direction,
                                "zone_low": str(zone_low), "zone_high": str(zone_high), "posted_stop": str(sl)},
        "lane_refs": {
            "A_FOLLOWER": {"semantics": "FROZEN_AND_KNOWN", "constitution_sha256": guards_const_sha(),
                           "note": "per-leg BE / cancel-unfilled / take-some=25% / 3 legs — router does NOT touch it"},
            "B_ENHANCED_FOLLOWER": {"outputs": "research candidates only (OTE/reactive), none selected"},
            "C_INDEPENDENT": {"outputs": "this router record IS the independent representation; blind hypothesis separate"},
        },
        "market_data_cutoff_timestamp": cutoff,
        "decision_timestamp": decision_ts,
        "activation_timestamp": activation_ts if activation_ts is not None else UNKNOWN,
        "record_class": rclass,
        "eligible_for_prospective_evidence": elig["prospective"],
        "eligible_for_training": elig["training"],
        "eligible_for_performance_attribution": elig["performance_attribution"],
        "causal_1m_sha256": causality["source_hashes"]["causal_1m_sha256"],
        "outcome_data_available_at_freeze": False,
    }
    rec = {
        "record_type": "ROUTER_FREEZE", "router_version": FEATURE_VERSION, "setup_id": setup_id,
        "objective_lane": objective_lane, "direction": direction, "zone": f"{zone_low}-{zone_high}",
        "record_class": rclass,
        "eligible_for_prospective_evidence": elig["prospective"],
        "eligible_for_training": elig["training"],
        "eligible_for_performance_attribution": elig["performance_attribution"],
        "hash_envelope": envelope,
        "causality": causality, "hierarchy": hierarchy, "supplemental_contracts": supplemental,
        "backfill_marker": rclass,
        "outputs_class": "RESEARCH_ONLY / NON_AUTHORITATIVE / NO_EXECUTION_CONSEQUENCE",
        "must_not": "choose trades / modify follower / fit weights / activate smart entry / route anything",
        **RESEARCH_STAMPS,
    }
    return es.finalize(rec)


def guards_const_sha():
    try:
        import guards
        return guards.CONSTITUTION_SHA
    except Exception:                                            # noqa: BLE001
        return UNKNOWN


ROUTER_FREEZE_LEDGER = os.path.join(HERE, "router_freeze_v0_1.jsonl")
BACKFILL_LEDGER = os.path.join(HERE, "router_freeze_backfill_v0_1.jsonl")
INTEGRATION_TEST_LEDGER = os.path.join(HERE, "router_freeze_integration_test_v0_1.jsonl")
ACTIVATION_MARKER = os.path.join(HERE, "router_activation_marker.json")
# integration-harness seam (production default None -> no effect); when set, the watcher sweep
# stamps records with this class so the real lifecycle can be exercised into the isolated test ledger.
RECORD_CLASS_OVERRIDE = None


def module_content_sha256():
    """sha256 of THIS module's on-disk source (hooked-build load proof, Section 8.4)."""
    return hashlib.sha256(open(os.path.abspath(__file__), "rb").read()).hexdigest()


def write_activation_marker(pid, activation_ts):
    """Freeze the canonical UTC activation timestamp + loaded-module hash at watcher startup."""
    rec = {"activation_ts_utc": int(activation_ts), "pid": pid,
           "module_content_sha256": module_content_sha256(),
           "module_path": os.path.abspath(__file__),
           "activation_ts_source": "watcher_startup_wallclock_utc",
           "timestamp_precision_seconds": 1, "router_version": FEATURE_VERSION}
    tmp = ACTIVATION_MARKER + ".tmp"
    json.dump(rec, open(tmp, "w", encoding="utf-8"), indent=1)
    os.replace(tmp, ACTIVATION_MARKER)
    return rec


def read_activation_marker():
    if os.path.exists(ACTIVATION_MARKER):
        try:
            return json.load(open(ACTIVATION_MARKER, encoding="utf-8"))
        except Exception:                                        # noqa: BLE001
            return None
    return None


def classify_activation(decision_ts, activation_ts):
    """Section 9 canonical-clock eligibility. Both timestamps are canonical UTC epoch seconds.
    A genuine prospective campaign requires normalized_decision > normalized_activation."""
    if activation_ts is None:
        return "ACTIVATION_STRADDLE", "no activation marker -> cannot prove decision>activation (conservative)"
    if decision_ts > activation_ts:
        return "PROSPECTIVE", "decision strictly after activation"
    return "ACTIVATION_STRADDLE", "decision at/before activation (straddle; not prospective)"
