"""Farouk level-RANKING evidence harness (research-only, deterministic, NO fitted weights).

Builds the DATA needed to one-day learn Farouk's zone-ranking function, without inventing any
weight or threshold. Reuses the causal reconstruction (full candidate universe) + smc_features.
Everything qualitative/undocumented is UNKNOWN (fail closed). Cannot touch the strict follower,
Smart Entry, outcomes, pre-marks, scorers, Constitution, or live processes.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from decimal import Decimal as D

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import smc_features as smc                                        # noqa: E402
import topdown_reconstruction as tr                              # noqa: E402

FEATURE_SCHEMA = "ranking_feature_v0_1"
UNKNOWN = smc.UNKNOWN
# minimum forward sample before ANY ranking-model fit is attempted (interpretable models only)
MIN_FORWARD_CAMPAIGNS_FOR_FIT = 15          # matches the ledger schema's min_forward_trades
MIN_SESSIONS_FOR_FIT = 5
ALLOWED_MODEL_FAMILIES = ["rule_based_lexicographic", "pairwise_logistic",
                          "shallow_decision_tree", "monotonic_scorecard"]   # NO black-box; NO autoparam search


# ---- Part 2: causal Weekly / Monthly context from the Daily history --------------------------
def resample_calendar(daily, unit, signal_ts):
    """Aggregate completed native daily bars into ISO-week or calendar-month candles, causal
    (a period is COMPLETE only if its last day closes before the signal)."""
    def key(ts):
        dt = datetime.fromtimestamp(ts, timezone.utc)
        return dt.isocalendar()[:2] if unit == "W" else (dt.year, dt.month)
    buckets = {}
    for t, o, h, l, c in daily:
        if t + 86400 > signal_ts:          # forming daily -> excludes forming period
            continue
        k = key(t)
        b = buckets.setdefault(k, {"o": o, "h": h, "l": l, "c": c, "last": t})
        b["h"] = max(b["h"], h); b["l"] = min(b["l"], l)
        if t >= b["last"]:
            b["c"] = c; b["last"] = t
    # a period is COMPLETE only if the NEXT period has started before the signal (i.e. not the last open one)
    keys = sorted(buckets)
    complete = keys[:-1] if keys else []   # last bucket may be forming; drop it (conservative)
    return [(buckets[k]["last"], buckets[k]["o"], buckets[k]["h"], buckets[k]["l"], buckets[k]["c"]) for k in complete]


def htf_context(signal_ts):
    daily = tr.load_ohlc(tr.D1_FILE)
    weekly = resample_calendar(daily, "W", signal_ts)
    monthly = resample_calendar(daily, "M", signal_ts)
    def struct(bars):
        if len(bars) < 6:
            return {"structure": UNKNOWN, "swing_highs": UNKNOWN, "swing_lows": UNKNOWN}
        sh, sl = smc.swing_points(bars, signal_ts + 10**9, lookback=1)
        return {"structure": smc.htf_bias(bars, signal_ts + 10**9, ema_len=min(10, len(bars)))["htf_bias"],
                "swing_highs": [(t, str(p)) for t, p in sh[-3:]] or UNKNOWN,
                "swing_lows": [(t, str(p)) for t, p in sl[-3:]] or UNKNOWN,
                "recent_high": str(max(b[2] for b in bars[-8:])), "recent_low": str(min(b[3] for b in bars[-8:]))}
    return {
        "weekly": {"completed_bars": len(weekly), **struct(weekly),
                   "sufficiency": "SUFFICIENT" if len(weekly) >= 52 else "MARGINAL" if len(weekly) >= 20 else "INSUFFICIENT_UNKNOWN"},
        "monthly": {"completed_bars": len(monthly), **struct(monthly),
                    "sufficiency": "MARGINAL" if 12 <= len(monthly) < 60 else "SUFFICIENT" if len(monthly) >= 60 else "INSUFFICIENT_UNKNOWN"},
        "long_term_mitigation_history": ("PARTIAL (~%d months of daily; deep multi-year mitigation UNKNOWN)" % len(monthly)),
        "weights_note": "context only; NO ranking weight assigned",
    }


# ---- Part 3: candidate ranking-feature contract ----------------------------------------------
def _nested_in(zone, htf_zones):
    lo, hi = D(zone["zone_low"]), D(zone["zone_high"])
    for z in (htf_zones if isinstance(htf_zones, list) else []):
        if D(z["zone_low"]) <= lo and hi <= D(z["zone_high"]):
            return {"tf": z["tf"], "zone": f"{z['zone_low']}-{z['zone_high']}"}
    return "NONE"


def feature_contract(candidate, recon, htf, price, decision_ts, direction):
    """Deterministic features per causal candidate. Qualitative/undocumented -> UNKNOWN. NO weights."""
    lo, hi = D(candidate["zone_low"]), D(candidate["zone_high"])
    age_s = decision_ts - candidate["at_ts"]
    d1c = recon["d1_context"]
    h4z = recon["h4_candidates"]
    # direction-compatibility: bullish zones compatible with LONG, bearish with SHORT (structural only)
    dir_compat = ("LONG" if "BULL" in candidate["type"] else "SHORT" if "BEAR" in candidate["type"] else UNKNOWN)
    cid = hashlib.sha256(f"{candidate['tf']}|{candidate['type']}|{candidate['zone_low']}|"
                         f"{candidate['zone_high']}|{candidate['at_ts']}|{decision_ts}".encode()).hexdigest()[:16]
    return {
        "schema": FEATURE_SCHEMA, "candidate_id": cid, "decision_ts": decision_ts,
        "instrument": "XAUUSD", "direction_compatibility": dir_compat,
        "tf_origin": candidate["tf"], "zone_low": candidate["zone_low"], "zone_high": candidate["zone_high"],
        "body_wick_basis": candidate.get("body_basis", "origin-candle body (VR-11)"),
        "distance_pips": candidate.get("distance_pips", UNKNOWN), "price_relation": candidate.get("price_relation", UNKNOWN),
        "age_bars": UNKNOWN, "age_elapsed_s": age_s,
        "touch_count": UNKNOWN,                       # requires a defined touch rule -> UNKNOWN
        "mitigation_count": UNKNOWN, "last_mitigation_ts": UNKNOWN,
        "fresh_mitigated_unknown": ("MITIGATED" if candidate["mitigated"] else "FRESH"),
        "displacement_magnitude": UNKNOWN, "displacement_defn_provenance": "DR-202 (no threshold) -> UNKNOWN",
        "fvg_overlap": ("FVG" if "FVG" in candidate["type"] else "OB"),
        "nested_htf_level": _nested_in(candidate, (d1c.get("daily_ob_fvg") if isinstance(d1c.get("daily_ob_fvg"), list) else []) + (h4z if isinstance(h4z, list) else [])),
        "monthly_alignment": htf["monthly"]["structure"], "weekly_alignment": htf["weekly"]["structure"],
        "daily_alignment": d1c.get("directional_bias", UNKNOWN),
        # the *_alignment values are an EMA-crossover PROXY for structure/bias, NOT a documented Farouk
        # rule (he uses swings/BOS). Categorical + weightless; tagged so it can never be read as a
        # Farouk-defined ranking input (red-team #1).
        "alignment_provenance": "EMA_PROXY_NOT_FAROUK_DOCUMENTED (categorical, weightless, research-only)",
        "h4_alignment": UNKNOWN, "h1_structure_alignment": (recon["h1_choch_bos"]["latest_choch_bos"] or UNKNOWN),
        "premium_discount": UNKNOWN,                  # no dealing-range defn -> UNKNOWN
        "external_liquidity_relationship": UNKNOWN, "internal_liquidity_relationship": UNKNOWN,
        "asia_relationship": recon.get("m15_asia", UNKNOWN),
        "sweep_status": recon.get("h1_sweeps", UNKNOWN),
        "bos_choch_state": (recon["h1_choch_bos"]["latest_choch_bos"] or UNKNOWN),
        "session": smc.session_of(decision_ts),
        "expected_target": UNKNOWN, "room_to_target_pips": UNKNOWN, "invalidation_distance": UNKNOWN,
        "opposing_level_before_target": UNKNOWN, "confirmation_available": UNKNOWN,
        "repaint_feed_sensitivity_risk": "FEED_SENSITIVE_$3_BAND (VR-21)",
        "unknown_features": ["age_bars", "touch_count", "mitigation_count/age", "displacement_magnitude",
                             "premium_discount", "liquidity relationships", "targets", "confirmation"],
        "dr_vr_provenance": ["DR-204", "DR-201", "DR-203", "VR-11", "VR-15", "R-STRONGWEAK", "DR-502"],
        "review_only": True, "executable": False, "trade_ready": False, "observation_only": True,
    }


# ---- Part 4: pairwise ranking evidence (Farouk-selected vs each competing) --------------------
def pairwise_records(features, published_zone, published_dir, decision_ts):
    """Identify which candidate best matches the published zone (SELECTED proxy), and pair it vs
    every competitor with feature DIFFS. Outcome is NEVER read here (frozen before outcome)."""
    zlo, zhi = D(str(published_zone[0])), D(str(published_zone[1]))
    def overlap(f):
        lo, hi = D(f["zone_low"]), D(f["zone_high"])
        return max(D(0), min(hi, zhi) - max(lo, zlo))
    selected = max(features, key=overlap) if features else None
    if selected is None:
        return {"selected": UNKNOWN, "pairs": [], "note": "no candidates"}
    pairs = []
    for comp in features:
        if comp["candidate_id"] == selected["candidate_id"]:
            continue
        diffs = {k: [selected.get(k), comp.get(k)] for k in
                 ("tf_origin", "fresh_mitigated_unknown", "distance_pips", "fvg_overlap",
                  "direction_compatibility", "nested_htf_level", "daily_alignment", "session")
                 if selected.get(k) != comp.get(k)}
        # HONEST: distance is NOT a ranking rule (it is a built-in artifact — the selected proxy is
        # nearest to the published zone by construction). No EXISTING RANKING rule with weights exists,
        # so the selection is UNKNOWN-explained. Distance is recorded separately, never as the reason.
        explained = "UNKNOWN — no existing RANKING rule explains this selection (distance is a built-in " \
                    "artifact of proxy-selection, not a ranking rule; freshness/nesting/confluence weights UNKNOWN)"
        pairs.append({"selected_id": selected["candidate_id"], "competitor_id": comp["candidate_id"],
                      "feature_diffs": diffs, "explainable_by_existing_rule": explained,
                      "distance_diff_pips_note": "recorded in feature_diffs; NOT treated as a ranking reason",
                      "unexplained_dimensions": [k for k in diffs],
                      "competitor_later_worked": "OUTCOME_EXCLUDED (frozen before outcome)"})
    return {"selected_candidate_id": selected["candidate_id"],
            "selected_zone": f"{selected['zone_low']}-{selected['zone_high']} ({selected['tf_origin']} {selected['fvg_overlap']})",
            "selected_is_proxy": "nearest-overlap to published zone; NOT proof Farouk reasoned this way",
            "published_zone": f"{zlo}-{zhi}", "n_pairs": len(pairs), "pairs": pairs,
            "outcome_excluded": True, "frozen_before_outcome": True}


# ---- Part 5: rejection / no-trade register ---------------------------------------------------
def rejection_record(kind, detail):
    valid = ("PLAUSIBLE_CANDIDATE_REJECTED", "CANDIDATE_IGNORED", "CANDIDATE_INVALIDATED_PRE_ENTRY",
             "CAMPAIGN_CANCELLED", "MISSED_TRADE", "FAROUK_EXPLICIT_NO_TRADE", "NO_PUBLISHED_CAMPAIGN")
    assert kind in valid, f"unknown rejection kind {kind}"
    return {"schema": "rejection_notrade_v0_1", "kind": kind, "detail": detail,
            "unpublished_disclaimer": "NO claim about private/unpublished decisions",
            "distinction": "NO_PUBLISHED_CAMPAIGN (silence) is NOT FAROUK_EXPLICIT_NO_TRADE (he said no-trade)",
            "review_only": True, "executable": False, "trade_ready": False, "observation_only": True}


# ---- Part 8/9: build the full ranking-evidence pack for a campaign ----------------------------
def build_campaign_ranking_pack(setup_id, signal_ts, direction, published_low, published_high,
                                prospective=True):
    recon = tr.reconstruct(signal_ts, direction)
    htf = htf_context(signal_ts)
    price = D(recon["signal_price"]) if recon["signal_price"] != UNKNOWN else UNKNOWN
    # ALL causal candidates preserved (Part 9: the full d1+h4+h1 universe, not just the nearest few)
    full = recon["d1_context"]["daily_ob_fvg"] + recon["h4_candidates"] + recon["h1_candidates"]
    for z in full:
        lo, hi = D(z["zone_low"]), D(z["zone_high"])
        if price != UNKNOWN:
            z["distance_pips"] = ("0" if lo <= price <= hi else
                                  str((price - hi) * 10) if price > hi else str((lo - price) * 10))
            z["price_relation"] = ("INSIDE" if lo <= price <= hi else "ABOVE" if price > hi else "BELOW")
        else:
            z["distance_pips"] = UNKNOWN; z["price_relation"] = UNKNOWN
    feats = [feature_contract(z, recon, htf, price, signal_ts, direction) for z in full]
    pair = pairwise_records(feats, (published_low, published_high), direction, signal_ts)
    pack = {
        "schema": "ranking_evidence_pack_v0_1", "setup_id": setup_id,
        "prospective": prospective,
        "provenance_class": ("PROSPECTIVE_CAMPAIGN" if prospective else "SCHEMA_BACKFILL_NOT_PROSPECTIVE"),
        "signal_ts": signal_ts, "signal_price": recon["signal_price"], "direction": direction,
        "candidate_universe_total": recon["candidate_universe_total"],
        "features_built": len(feats), "htf_context": htf,
        "candidate_features": feats, "pairwise": pair,
        "model_boundary": {"allowed_families": ALLOWED_MODEL_FAMILIES,
                           "min_forward_campaigns_for_fit": MIN_FORWARD_CAMPAIGNS_FOR_FIT,
                           "min_sessions_for_fit": MIN_SESSIONS_FOR_FIT,
                           "no_black_box": True, "no_autoparam_search": True,
                           "no_fit_against_F001_F002": True, "fit_status": "NOT_FITTED"},
        "cannot": ["modify strict follower", "activate Smart Entry", "assign ranking weights",
                   "claim ranking accuracy from backfill", "read outcome into ranking"],
        "review_only": True, "executable": False, "trade_ready": False, "observation_only": True,
    }
    pack["logical_hash"] = hashlib.sha256(
        json.dumps({k: pack[k] for k in ("setup_id", "candidate_features", "pairwise")},
                   sort_keys=True, default=str).encode()).hexdigest()
    return pack


RANKING_LEDGER = os.path.join(HERE, "ranking", "ranking_packs_v0_1.jsonl")


def _data_covers(signal_ts):
    """The reconstruction needs D1 through the signal + 1m lead-in covering the signal minute."""
    try:
        m1 = tr.load_ohlc(tr.M1_FILE)
        d1 = tr.load_ohlc(tr.D1_FILE)
    except Exception:                                            # noqa: BLE001
        return False
    have_m1 = any(b[0] + 60 <= signal_ts for b in m1) and any(b[0] < signal_ts <= b[0] + 3600 for b in m1)
    have_d1 = any(b[0] + 86400 <= signal_ts for b in d1)
    return have_m1 and have_d1


def emit_ranking_pack_for_campaign(setup_id, signal_ts, direction, zlo, zhi, done_ids):
    """Campaign-#3 automation (Part 8): for a REAL campaign (F-index>=3), freeze the ranking pack
    if the reconstruction data covers the signal; else record DATA_PENDING (fail closed). Append-only,
    idempotent. NEVER blocks the follower (separate process). Returns an action string."""
    if setup_id in done_ids:
        return f"RANKING_SKIP({setup_id} already packed)"
    os.makedirs(os.path.dirname(RANKING_LEDGER), exist_ok=True)
    if not _data_covers(signal_ts):
        rec = {"schema": "ranking_evidence_pack_v0_1", "setup_id": setup_id, "status": "DATA_PENDING",
               "why": "reconstruction requires D1 + recent 1m covering the signal; export the campaign-day "
                      "pack (per TOPDOWN_DATA_SUFFICIENCY_PLAN) then re-run",
               "logical_hash": hashlib.sha256(f"PENDING:{setup_id}".encode()).hexdigest(),
               "review_only": True, "executable": False, "trade_ready": False, "observation_only": True}
        _append_once(RANKING_LEDGER, rec)
        return f"RANKING_DATA_PENDING({setup_id})"
    pack = build_campaign_ranking_pack(setup_id, signal_ts, direction, zlo, zhi, prospective=True)
    # store the pack summary + the full pack alongside (pack is large -> separate file)
    os.makedirs(os.path.join(HERE, "ranking"), exist_ok=True)
    open(os.path.join(HERE, "ranking", f"{setup_id}_ranking_pack.json"), "w", encoding="utf-8").write(
        json.dumps(pack, indent=1, ensure_ascii=False, default=str))
    summary = {k: pack[k] for k in ("schema", "setup_id", "prospective", "provenance_class", "signal_ts",
                                    "candidate_universe_total", "features_built", "logical_hash")}
    summary["selected_zone"] = pack["pairwise"].get("selected_zone")
    summary["fit_status"] = "NOT_FITTED"
    summary["review_only"] = summary["executable"] = summary["trade_ready"] = None
    summary["review_only"], summary["executable"], summary["trade_ready"], summary["observation_only"] = True, False, False, True
    _append_once(RANKING_LEDGER, summary)
    return f"RANKING_PACK_EMITTED({setup_id}: {pack['features_built']} features)"


def _append_once(path, rec):
    lh = rec.get("logical_hash")
    if lh and os.path.exists(path):
        for line in open(path, encoding="utf-8"):
            if lh in line:
                return False
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, ensure_ascii=False, default=str) + "\n")
    return True


if __name__ == "__main__":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    F001 = int(datetime(2026, 7, 14, 8, 38, 6, tzinfo=timezone.utc).timestamp())
    F002 = int(datetime(2026, 7, 14, 13, 26, 21, tzinfo=timezone.utc).timestamp())
    for name, sig, dr, zl, zh in [("XAU-F001-20260714", F001, "LONG", 4007, 4019),
                                  ("XAU-F002-20260714", F002, "SHORT", 4084, 4094)]:
        p = build_campaign_ranking_pack(name, sig, dr, zl, zh, prospective=False)
        print(f"{name}: {p['provenance_class']} | universe {p['candidate_universe_total']} | "
              f"features {p['features_built']} | pairs {p['pairwise']['n_pairs']} | "
              f"selected {p['pairwise']['selected_zone']} | fit_status {p['model_boundary']['fit_status']}")
        htf = p["htf_context"]
        print(f"   HTF weekly {htf['weekly']['completed_bars']}bars/{htf['weekly']['sufficiency']} "
              f"monthly {htf['monthly']['completed_bars']}bars/{htf['monthly']['sufficiency']}")
