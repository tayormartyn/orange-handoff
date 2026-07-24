"""
Step 8 — Follower-fill expectancy table v0.1 (OBSERVATION-ONLY, review-only).

Applies R6_FOLLOWER_FILL_EXPECTANCY_MODEL_v0_1 across all matched XAU sprint setups using ONLY
already-computed deterministic OHLC facts (Day-2/4/5 matchers + J24 rematch). No new OHLC walk, no
AI call, no execution surface. Units: pips = 0.1 USD (pips01 convention of the matchers).

Lane-4 (management-instruction follower) deterministic approximation — documented:
  fill basis   : zone MEDIAN fill (zone mid). Day-2 gives MFE from top+bottom -> median = mean.
                 Day-4/5 give best-zone-fill only -> median = best - zone_halfwidth_pips (floor 0),
                 flagged BEST_FILL_ADJUSTED.
  1. SL touched, no TP before it  -> FOLLOWER_LOSS: -(median_fill<->SL) pips.
  2. TP1 touched                  -> 0.5 x (median_fill->TP1); runner:
        sl-to-entry instruction   -> +0   (SCRATCH_ASSUMED, per R6 J24/J30 modelling)
        TP2 touched               -> +0.5 x (median_fill->TP2)
        else last claim-snapshot  -> +0.5 x min(snapshot achievable, median MFE)
        else                      -> +0   (noted)
  3. no TP, no SL (manual close)  -> min(last snapshot achievable, median MFE); no snapshot ->
                                     0.5 x median MFE flagged APPROX_HALF_MFE; no MFE -> UNAVAILABLE.
  status: LOSS(SL) | SCRATCH |pips|<30 | PARTIAL 30..100 | WIN >100  (descriptive only)
"""
import json
import os
import re
import sys
import statistics

HERE = os.path.dirname(os.path.abspath(__file__))
SCT = os.path.dirname(HERE)
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(SCT))))
sys.path.insert(0, os.path.join(ROOT, "ai_review"))
import schema as AISCHEMA  # fail-closed forbidden-key guard

J = lambda p: json.load(open(p, encoding="utf-8"))

day1 = J(os.path.join(SCT, "SPRINT_DAY1_XAU_LEDGER_v1.json"))
day2 = J(os.path.join(SCT, "SPRINT_DAY2_XAU_OUTCOME_MATCHING_v1.json"))
day3 = J(os.path.join(SCT, "SPRINT_DAY3_JUNE_XAU_LEDGER_v1.json"))
day4 = J(os.path.join(SCT, "SPRINT_DAY4_JUNE_XAU_OUTCOME_MATCHING_v1.json"))
day5 = J(os.path.join(SCT, "SPRINT_DAY5_JUNE_XAU_5M_FALLBACK_OUTCOME_MATCHING_v1.json"))
j24 = J(os.path.join(HERE, "j24_deterministic_rematch_v1.json"))
det = J(os.path.join(HERE, "detector_v0_2_replay_results.json"))

ledger = {s["setup_id"]: s for s in day3["setups"]}
ledger.update({s["setup_id"]: s for s in day1["setups"]})
det_by_prefix = {}
for r in det.get("records", []):
    sid = (r.get("pack_id") or "").split(":")[0]
    det_by_prefix.setdefault(sid, r)

# deterministic matched rows (rich detail)
rows = {}
for r in day5["results"]:
    rows[r["setup_id"]] = dict(r, _basis="5m_best_zone_fill")
for r in day4["results"]:
    if "entry_zone" in r:
        rows[r["setup_id"]] = dict(r, _basis="1m_best_zone_fill")
for r in day2["results"]:
    rows[r["setup_id"]] = dict(r, _basis="1m_top_bottom")

# deterministic statuses (authority)
det_status = {}
for src in (day4["results"], day5["results"]):
    for r in src:
        if r.get("status"):
            det_status[r["setup_id"]] = r["status"]
for r in day2["results"]:
    det_status.setdefault(r["setup_id"], None)  # July statuses live in day2 report; fill below
# July deterministic statuses per Day-2 report
det_status.update({"XAU-S1-20260630": "VERIFIED_WIN", "XAU-S2-20260707": "VERIFIED_LOSS",
                   "XAU-S3-20260708": "VERIFIED_WIN", "XAU-S4-20260710": "VERIFIED_WIN"})
det_status["XAU-J24-20260623"] = j24.get("status", "VERIFIED_WIN(farouk_fill)")

# rule flags from the adopted ruleset evidence lists
R2B_RE_ENTRY = {"XAU-J08-20260610", "XAU-J10-20260611", "XAU-J17-20260615",
                "XAU-J14-20260615", "XAU-J19-20260616", "XAU-J29-20260626"}
R4B_AFTER_1530 = {"XAU-J03-20260604", "XAU-J17-20260615", "XAU-J06-20260609"}

FAROUK_FILLS = {  # lane-1, from MT5 widgets (screenshot review / J24 rematch / R6 doc)
    "XAU-J24-20260623": {"fill": 4132.02, "claim_pips": 170, "source": "j24 rematch widgets 45015/17/21"},
    "XAU-J30-20260629": {"fill": 4027.37, "claim_pips": 240, "source": "screenshot review (msg 45285)"},
    "XAU-J11-20260611": {"fill": 4056.64, "claim_pips": 800, "realised_pips": 629,
                         "source": "screenshot review (msgs 44525/44535)"},
}

def parse_zone(z):
    if not z: return None
    m = re.findall(r"[\d.]+", str(z))
    if len(m) < 2: return None
    a, b = float(m[0]), float(m[1])
    return (min(a, b), max(a, b))

def parse_claim_pips(led, row):
    best = None
    for sn in (row or {}).get("claim_snapshots", []) or []:
        cp = sn.get("claimed_pips")
        if cp is None:
            m = re.search(r"(\d{2,4})\s*\+?\s*pips", str(sn.get("claim", "")), re.I)
            cp = int(m.group(1)) if m else None
        if cp is not None:
            best = max(best or 0, cp)
    if best is None and led:
        m = re.findall(r"(\d{2,4})\s*\+?\s*pips", str(led.get("result_claim", "")), re.I)
        if m: best = max(int(x) for x in m)
    return best

def last_snapshot_achievable(row):
    vals = [sn.get("max_achievable_pips01") for sn in (row or {}).get("claim_snapshots", []) or []
            if sn.get("max_achievable_pips01") is not None]
    return vals[-1] if vals else None

def sl_to_entry_noted(led, row):
    text = " ".join([str((led or {}).get("management_notes", ""))] +
                    [str(sn.get("claim", "")) for sn in (row or {}).get("claim_snapshots", []) or []])
    return bool(re.search(r"sl\s*(to|at)?\s*entry|stops?\s*to\s*(entry|break\s*even|be\b)|\bbe\b\s*stop", text, re.I))

def build_record(sid):
    led = ledger.get(sid)
    row = rows.get(sid)
    direction = (led or {}).get("direction") or (row or {}).get("direction")
    zone = parse_zone((row or {}).get("entry_zone") or (led or {}).get("entry_zone"))
    sl = (row or {}).get("sl")
    if sl is None and led:
        m = re.findall(r"[\d.]+", str(led.get("sl") or ""));  sl = float(m[0]) if m else None
    rec = {
        "setup_id": sid,
        "session_date": sid.split("-")[-1],
        "direction": direction,
        "posted_time_utc": (row or {}).get("signal_utc") or (led or {}).get("entry_posted_at_utc") or (led or {}).get("first_msg_utc"),
        "posted_zone": (row or {}).get("entry_zone") or (led or {}).get("entry_zone"),
        "farouk_private_fill": FAROUK_FILLS.get(sid, {}).get("fill"),
        "farouk_fill_source": FAROUK_FILLS.get(sid, {}).get("source"),
        "post_time_market_price": (row or {}).get("signal_bar_close"),
        "management_instructions_used": (led or {}).get("management_notes"),
        "deterministic_outcome_status": det_status.get(sid),
        "detector_v0_2_label": (det_by_prefix.get(sid) or {}).get("verdict"),
        "fill_basis": None, "realistic_follower_fill": None, "sl_to_entry_effect": None,
        "tp1_reachable": None, "tp2_reachable": None,
        "max_follower_mfe_pips": None, "max_follower_mae_pips": None,
        "headline_claimed_pips": parse_claim_pips(led, row),
        "follower_achievable_pips": None, "divergence_pips": None, "inflation_ratio": None,
        "follower_outcome_status": "UNAVAILABLE", "notes": [],
    }

    # ---- J24 special case: no posted entry existed (widgets only) ----
    if sid == "XAU-J24-20260623":
        rec.update({
            "posted_zone": None, "fill_basis": "POST_TIME_PROXY (no entry post existed)",
            "realistic_follower_fill": 4128.4, "sl_to_entry_effect": "SCRATCHED_AT_2026-06-23T10:34Z",
            "max_follower_mfe_pips": j24.get("mfe_pips"), "max_follower_mae_pips": j24.get("mae_pips"),
            "follower_achievable_pips": 0, "follower_outcome_status": "FOLLOWER_SCRATCH",
            "divergence_pips": (rec["headline_claimed_pips"] or 170) - 0,
            "inflation_ratio": None,
            "notes": ["NO posted zone/entry msg — follower lane is POST-TIME PROXY only (R6 J24 case);"
                      " his +170p claim vs follower ~0p (sl-to-entry scratched before the move).",
                      "farouk private fill used ONLY for lane-1 comparison, never as follower fill."],
        })
        return rec

    if row is None or zone is None:
        rec["notes"].append("no deterministic matched row / zone — follower expectancy UNAVAILABLE")
        return rec

    lo, hi = zone
    halfw_p = (hi - lo) / 2 * 10
    median_fill = round((lo + hi) / 2, 2)
    rec["realistic_follower_fill"] = median_fill
    touched = row.get("entry_zone_touched_utc")
    if not touched:
        rec["follower_outcome_status"] = "FOLLOWER_NO_FILL"
        rec["notes"].append("posted zone never touched — follower never filled")
        return rec

    # median-fill MFE/MAE
    if row["_basis"] == "1m_top_bottom":
        mfe_med = (row["mfe_pips01_from_zone_top"] + row["mfe_pips01_from_zone_bottom"]) / 2
        rec["fill_basis"] = "ZONE_MEDIAN (mean of top/bottom 1m MFEs)"
        mae_med = (abs(row.get("mae_usd_from_zone_top") or 0) + abs(row.get("mae_usd_from_zone_bottom") or 0)) / 2 * 10
    else:
        mfe_med = max((row.get("mfe_pips01") or 0) - halfw_p, 0)
        rec["fill_basis"] = f"BEST_FILL_ADJUSTED (best-zone MFE minus halfwidth {halfw_p:.0f}p; {row['_basis']})"
        mae_med = abs(row.get("mae_usd_from_best_zone_fill") or 0) * 10 + halfw_p
    rec["max_follower_mfe_pips"] = round(mfe_med, 1)
    rec["max_follower_mae_pips"] = round(-abs(mae_med), 1)

    tps = row.get("tp_touches") or []
    tp_hit = [t for t in tps if t.get("touched_utc") and t.get("before_sl", True)]
    rec["tp1_reachable"] = bool(tp_hit)
    rec["tp2_reachable"] = len(tp_hit) >= 2
    sl_hit = bool(row.get("sl_touched_utc"))
    s2e = sl_to_entry_noted(led, row)
    rec["sl_to_entry_effect"] = ("SCRATCH_ASSUMED (instruction posted; runner modelled to 0 per R6)"
                                 if s2e and not sl_hit else ("NONE_NOTED" if not s2e else "MOOT_SL_HIT"))

    sign = 1 if (direction or "").upper() in ("SHORT", "SELL") else -1  # short: profit when price falls

    def dist_p(a, b):  # signed follower profit pips from a to b
        return (a - b) * 10 * sign

    if sl_hit and not tp_hit:
        pips = -abs(dist_p(median_fill, sl))
        rec["follower_achievable_pips"] = round(pips, 1)
        rec["follower_outcome_status"] = "FOLLOWER_LOSS"
    elif tp_hit:
        tp1 = tp_hit[0]["level"]
        base = 0.5 * dist_p(median_fill, tp1)
        runner, note = 0.0, None
        if s2e:
            note = "runner scratched (sl-to-entry, per R6)"
        elif rec["tp2_reachable"]:
            runner = 0.5 * dist_p(median_fill, tp_hit[1]["level"]); note = "runner to TP2"
        else:
            snap = last_snapshot_achievable(row)
            if snap is not None:
                runner = 0.5 * min(snap, mfe_med); note = "runner at last claim-snapshot achievable"
            else:
                note = "runner credited 0 (no snapshot)"
        pips = base + runner
        rec["notes"].append(note)
        rec["follower_achievable_pips"] = round(pips, 1)
    else:
        snap = last_snapshot_achievable(row)
        if snap is not None:
            pips = min(snap, mfe_med)
            rec["notes"].append("manual close at last claim-snapshot achievable")
        elif mfe_med:
            pips = 0.5 * mfe_med
            rec["notes"].append("APPROX_HALF_MFE (no snapshot; manual close approximated)")
        else:
            rec["notes"].append("no snapshot/MFE — UNAVAILABLE")
            return rec
        rec["follower_achievable_pips"] = round(pips, 1)

    p = rec["follower_achievable_pips"]
    if rec["follower_outcome_status"] == "UNAVAILABLE" and p is not None:
        rec["follower_outcome_status"] = ("FOLLOWER_LOSS" if p <= -30 else
                                          "FOLLOWER_SCRATCH" if abs(p) < 30 else
                                          "FOLLOWER_PARTIAL" if p <= 100 else "FOLLOWER_WIN")
    claimed = rec["headline_claimed_pips"]
    if claimed is not None and p is not None:
        rec["divergence_pips"] = round(claimed - p, 1)
        rec["inflation_ratio"] = round(claimed / max(p, 1), 2)
    return rec

# ---- build all records ----
all_ids = sorted(set(list(ledger.keys()) + list(rows.keys()) + ["XAU-J24-20260623"]))
records = [build_record(sid) for sid in all_ids]

# ---- aggregates ----
usable = [r for r in records if r["follower_achievable_pips"] is not None]
pips = [r["follower_achievable_pips"] for r in usable]
st = lambda s: sum(1 for r in records if r["follower_outcome_status"] == s)
div_claims = [r["divergence_pips"] for r in usable if r["divergence_pips"] is not None]

def lane_summary(ids_excluded, label):
    sub = [r for r in usable if r["setup_id"] not in ids_excluded]
    ps = [r["follower_achievable_pips"] for r in sub]
    return {"label": label, "n": len(sub),
            "mean_pips": round(statistics.mean(ps), 1) if ps else None,
            "median_pips": round(statistics.median(ps), 1) if ps else None,
            "total_pips": round(sum(ps), 1) if ps else None}

agg = {
    "setups_total": len(records),
    "setups_with_follower_expectancy": len(usable),
    "follower_wins": st("FOLLOWER_WIN"), "follower_partials": st("FOLLOWER_PARTIAL"),
    "follower_scratches": st("FOLLOWER_SCRATCH"), "follower_losses": st("FOLLOWER_LOSS"),
    "follower_no_fill": st("FOLLOWER_NO_FILL"), "unavailable": st("UNAVAILABLE"),
    "mean_follower_pips": round(statistics.mean(pips), 1) if pips else None,
    "median_follower_pips": round(statistics.median(pips), 1) if pips else None,
    "total_follower_pips": round(sum(pips), 1) if pips else None,
    "total_divergence_vs_claims_pips": round(sum(div_claims), 1) if div_claims else None,
    "n_with_claims": len(div_claims),
    "farouk_vs_follower_known_fill_cases": {
        "XAU-J24-20260623": {"farouk_pips": 170, "follower_pips": 0, "divergence": -170},
        "XAU-J30-20260629": {"farouk_pips": 240, "follower_note": "posted-zone <=175p MFE, mgmt lane below"},
        "XAU-J11-20260611": {"farouk_realised_pips": 629, "claimed": 800, "follower_note": "post-time ~= his fill"},
    },
    "rule_protection": {
        "baseline": lane_summary(set(), "all usable"),
        "R2b_first_attempt_only": lane_summary(R2B_RE_ENTRY, "excl. re-entry setups (J08,J10,J17,J14,J19,J29)"),
        "R4b_before_1530Z": lane_summary(R4B_AFTER_1530, "excl. after-15:30Z setups (J03,J17,J06)"),
        "R2b_plus_R4b": lane_summary(R2B_RE_ENTRY | R4B_AFTER_1530, "excl. both rule sets"),
    },
}

out = {
    "table_id": "follower_fill_expectancy_table_v0_1",
    "generated_on": "2026-07-11",
    "mode": "OBSERVATION_ONLY / REVIEW_ONLY / ANALYTIC_ONLY",
    "model": "R6_FOLLOWER_FILL_EXPECTANCY_MODEL_v0_1 (lane-4 deterministic approximation documented in script header)",
    "authority": "deterministic OHLC matchers (Day-2/4/5, J24 rematch); no new OHLC walk; no AI call",
    "units": "pips = 0.1 USD (pips01)",
    "lanes_note": "farouk fills used ONLY in lane-1 comparison; follower lanes computed from POSTED info; "
                  "J24 marked POST_TIME_PROXY (no posted entry existed)",
    "records": records,
    "aggregates": agg,
    "safety": {"review_only": True, "executable": False, "trade_ready": False, "observation_only": True,
               "forbidden_outputs_check": "passed (ai_review forbidden-key sweep)"},
}

# ---- fail-closed forbidden-key sweep (ai_review authority) ----
for keypath in AISCHEMA._walk_keys(out):
    leaf = keypath.split(".")[-1].split("[")[0].lower()
    for bad in AISCHEMA.FORBIDDEN_KEY_SUBSTRINGS:
        assert bad not in leaf, f"forbidden key in output: {keypath}"

dst = os.path.join(HERE, "follower_fill_expectancy_table_v0_1.json")
json.dump(out, open(dst, "w", encoding="utf-8"), indent=1)
print("written:", dst)
print(json.dumps(agg, indent=1))
