"""recap_bar_walk_matcher v0.1 — OFFLINE / REVIEW-ONLY.

Deterministic bar-walk over historical OHLC bars for RESULT-CLAIM-ONLY recap rows
(date-only anchors, zone + posted SL + claimed pips). Measurement of whether posted
claims are consistent with price history — NOT trading, NOT scoring, NOT execution.

Rules (hard):
  * zone-side-aware first touch: a LONG buy zone must be approached from ABOVE
    (price > zone top at walk start), a SHORT sell zone from BELOW. If the walk
    window OPENS already at/through the entry boundary -> AMBIGUOUS_ENTRY.
  * same-bar conflicts (fill+SL, or target+SL in one bar) -> AMBIGUOUS_SEQUENCE.
    Intra-bar order is NEVER guessed.
  * date-only anchor: walk starts at the trade date 00:00 UTC; fill accepted only
    on the anchor date itself for MISSED/REMOVED checks; outcome walk runs to
    anchor + 48 trading hours (weekend-aware: capped at window_end).
  * entry reference = the first-touched zone boundary; claimed-pips target is
    measured from that reference (conservative).
  * unknown stays UNKNOWN; every verdict carries the evidence bars.
  * 15m bars = FALLBACK precision (finer than 60m, coarser than the 1m standard);
    verdicts here are labelled *_AT_15M and never upgrade the June-ledger 1m tier.

No execution semantics: candidate_only=True, executable=False, trade_ready=False.
"""
import csv
import json
import os
import sys
from datetime import datetime, timedelta, timezone

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = os.path.dirname(os.path.abspath(__file__))
FP = os.path.dirname(HERE)
BARS_CSV = os.path.join(os.path.dirname(FP), "price_data", "XAUUSD_15M_2026-03-09_to_2026-07-10.csv")
OUT_JSON = os.path.join(FP, "febmar_export_cd_15m_match_results.json")

# Export C/D recap rows (FP-RECAP-001 via fable5_training_batch_003.json).
# zone = [low_price, high_price]; claim_usd = claimed pips / 10 (XAU $ move); None where N/A.
ROWS = [
    {"id": "12-03", "date": "2026-03-12", "dir": "LONG", "zone": [5035.0, 5050.0], "sl": 5010.0, "claim": "MISSED", "claim_usd": None},
    {"id": "17-03", "date": "2026-03-17", "dir": "LONG", "zone": [4980.0, 4992.0], "sl": 4966.0, "claim": "WIN +300p all TPs", "claim_usd": 30.0},
    {"id": "18-03", "date": "2026-03-18", "dir": "SHORT", "zone": [4870.0, 4870.0], "sl": 4925.0, "claim": "WIN +500p", "claim_usd": 50.0},
    {"id": "19-03", "date": "2026-03-19", "dir": "LONG", "zone": [4775.0, 4775.0], "sl": 4767.0, "claim": "LOSS ('SL hit at 4762')", "claim_usd": None,
     "special_levels": {"posted_sl": 4767.0, "claimed_exit": 4762.0}},
    {"id": "19-03b", "date": "2026-03-19", "dir": "SHORT", "zone": [4619.0, 4619.0], "sl": 4708.0, "claim": "WIN +400p", "claim_usd": 40.0},
    {"id": "19-03c", "date": "2026-03-19", "dir": "SHORT", "zone": [4624.0, 4624.0], "sl": 4708.0, "claim": "WIN +350p", "claim_usd": 35.0},
    {"id": "20-03", "date": "2026-03-20", "dir": "LONG", "zone": [4610.0, 4619.0], "sl": 4585.0, "claim": "WIN +90p SL-to-entry at TP1", "claim_usd": 9.0},
    {"id": "20-03b", "date": "2026-03-20", "dir": "LONG", "zone": [4583.0, 4583.0], "sl": 4560.0, "claim": "LOSS", "claim_usd": None},
    {"id": "25-03", "date": "2026-03-25", "dir": "LONG", "zone": [4548.0, 4554.0], "sl": 4530.0, "claim": "WIN TP1 (level unstated)", "claim_usd": None},
    {"id": "27-03", "date": "2026-03-27", "dir": "SHORT", "zone": [4433.0, 4433.0], "sl": 4472.0, "claim": "WIN +170p", "claim_usd": 17.0},
]
# 27-03-err (SHORT SL=5075) stays EXCLUDED: documented data error, never matched.

WALK_TRADING_HOURS = 48


def load_bars():
    bars = []
    with open(BARS_CSV, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            bars.append({"t": int(row["time"]), "o": float(row["open"]), "h": float(row["high"]),
                         "l": float(row["low"]), "c": float(row["close"])})
    bars.sort(key=lambda b: b["t"])
    return bars


def iso(t):
    return datetime.fromtimestamp(t, timezone.utc).strftime("%Y-%m-%d %H:%M")


def walk(bars, row):
    d = datetime.strptime(row["date"], "%Y-%m-%d").replace(tzinfo=timezone.utc)
    day_start, day_end = int(d.timestamp()), int((d + timedelta(days=1)).timestamp())
    # 48 TRADING hours: count only bars that exist (market bars) — walk max 192 15m bars beyond fill.
    window = [b for b in bars if b["t"] >= day_start]
    day_bars = [b for b in window if b["t"] < day_end]
    res = {"id": row["id"], "claim": row["claim"], "direction": row["dir"],
           "zone": row["zone"], "posted_sl": row["sl"],
           "candidate_only": True, "executable": False, "trade_ready": False, "review_only": True,
           "precision": "15m fallback"}
    if not day_bars:
        res["verdict"] = "NO_DATA_ON_ANCHOR_DATE"
        return res

    long_side = row["dir"] == "LONG"
    entry_boundary = row["zone"][1] if long_side else row["zone"][0]  # first boundary price reaches
    sl = row["sl"]

    # zone-side check at day open
    first = day_bars[0]
    opens_beyond = (first["o"] <= entry_boundary) if long_side else (first["o"] >= entry_boundary)

    # fill on the anchor date
    fill = None
    for b in day_bars:
        if (long_side and b["l"] <= entry_boundary) or (not long_side and b["h"] >= entry_boundary):
            fill = b
            break

    if row["claim"] in ("MISSED",) or row["claim"].startswith("REMOVED"):
        res["zone_traded_on_anchor_date"] = iso(fill["t"]) if fill else None
        # also report first touch AFTER the anchor date
        later = next((b for b in window if b["t"] >= day_end and
                      ((long_side and b["l"] <= entry_boundary) or (not long_side and b["h"] >= entry_boundary))), None)
        res["zone_first_traded_after_date"] = iso(later["t"]) if later else None
        res["verdict"] = ("MISSED_CLAIM_SUPPORTED_AT_15M (zone untraded on anchor date)" if not fill
                          else "MISSED_CLAIM_INCONSISTENT_AT_15M (zone traded on anchor date)")
        return res

    if fill is None:
        res["verdict"] = "NO_FILL_ON_ANCHOR_DATE (claim implies a fill -> INCONSISTENT_OR_LATER_FILL; not guessed)"
        return res
    if opens_beyond:
        res["entry_side_flag"] = "AMBIGUOUS_ENTRY (day opened at/through the entry boundary; approach side unproven)"
    res["fill_bar"] = iso(fill["t"])

    fill_idx = window.index(fill)
    walk_bars = window[fill_idx:fill_idx + int(WALK_TRADING_HOURS * 4) + 1]

    sl_bar = next((b for b in walk_bars if (long_side and b["l"] <= sl) or (not long_side and b["h"] >= sl)), None)
    res["sl_first_bar"] = iso(sl_bar["t"]) if sl_bar else None

    tgt_bar = None
    if row.get("claim_usd") is not None:
        target = entry_boundary + row["claim_usd"] if long_side else entry_boundary - row["claim_usd"]
        res["claim_target_price"] = target
        tgt_bar = next((b for b in walk_bars if (long_side and b["h"] >= target) or (not long_side and b["l"] <= target)), None)
        res["target_first_bar"] = iso(tgt_bar["t"]) if tgt_bar else None

    mfe = (max(b["h"] for b in walk_bars) - entry_boundary) if long_side else (entry_boundary - min(b["l"] for b in walk_bars))
    res["max_favorable_excursion_usd_48h"] = round(mfe, 2)

    # special levels (19-03 gap row)
    if "special_levels" in row:
        sp = row["special_levels"]
        for name, lvl in sp.items():
            bar = next((b for b in walk_bars if b["l"] <= lvl), None)
            res[f"first_bar_through_{name}_{lvl}"] = iso(bar["t"]) if bar else None
            if bar:
                res[f"same_bar_as_fill_{name}"] = bar["t"] == fill["t"]

    # verdict
    if row["claim"].startswith("LOSS"):
        if sl_bar is None:
            res["verdict"] = "LOSS_CLAIM_NOT_SUPPORTED_AT_15M (posted SL never traded in walk)"
        elif sl_bar["t"] == fill["t"]:
            res["verdict"] = "LOSS_CONSISTENT_AT_15M; fill->stop ordering AMBIGUOUS_SEQUENCE (same 15m bar)"
        else:
            res["verdict"] = "LOSS_CLAIM_SUPPORTED_AT_15M (SL traded after fill, distinct bars)"
        return res

    if tgt_bar is None and row.get("claim_usd") is not None:
        res["verdict"] = "WIN_CLAIM_NOT_SUPPORTED_AT_15M (claim target never traded in walk)"
    elif row.get("claim_usd") is None:
        res["verdict"] = "CLAIM_LEVEL_UNSTATED -> descriptive facts only (no TP price/pips to test)"
    elif sl_bar is None or tgt_bar["t"] < sl_bar["t"]:
        pre = "WIN_CLAIM_SUPPORTED_AT_15M (target strictly before any SL touch)"
        if fill["t"] == tgt_bar["t"]:
            pre += "; fill+target same bar (order immaterial: both favourable)"
        res["verdict"] = pre
    elif tgt_bar["t"] == sl_bar["t"]:
        res["verdict"] = "AMBIGUOUS_SEQUENCE_AT_15M (target and SL share one bar)"
    else:
        if fill["t"] == sl_bar["t"]:
            res["verdict"] = "AMBIGUOUS_SEQUENCE_AT_15M (fill and SL share one bar; target later)"
        else:
            res["verdict"] = "SL_BEFORE_TARGET_AT_15M (claim INCONSISTENT at this precision)"
    return res


def main():
    bars = load_bars()
    gaps = sorted({bars[i + 1]["t"] - bars[i]["t"] for i in range(min(200, len(bars) - 1))})
    meta = {"matcher": "recap_bar_walk_matcher_v0_1", "generated_on": "2026-07-12",
            "mode": "OFFLINE / REVIEW_ONLY / 15M_FALLBACK_PRECISION",
            "bars_file": os.path.basename(BARS_CSV), "bars": len(bars),
            "first_bar_utc": iso(bars[0]["t"]), "last_bar_utc": iso(bars[-1]["t"]),
            "cadence_gaps_sample_s": gaps,
            "excluded": "27-03-err (SL 5075 impossible - documented data error, never matched)",
            "rules": "zone-side-aware first touch; same-bar conflicts = AMBIGUOUS_SEQUENCE; intra-bar order never guessed; 15m verdicts never upgrade the 1m ledger tier",
            "candidate_only": True, "executable": False, "trade_ready": False}
    results = [walk(bars, r) for r in ROWS]
    out = {"meta": meta, "results": results}
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1)
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
