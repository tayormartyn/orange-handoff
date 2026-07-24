"""OUTCOME MATCHER v0.1 — OFFLINE / RESEARCH-ONLY.

Pairs shadow-candidate records with XAUUSD OHLC candles to measure, descriptively,
whether the price moved favourably or adversely (relative to each candidate's
direction_hint) after the sequence completed. This is MEASUREMENT, not trading.

NON-NEGOTIABLE (enforced by construction):
  * Every result is candidate-only. execution_allowed / broker_execution_allowed /
    qst_allowed / order_intent / risk_sizing_allowed are hard-wired False.
  * Excursions/deltas are descriptive PRICE statistics in price units — NOT PnL, NOT
    position sizing, NOT SL/TP, NOT a trade instruction.
  * If OHLC data is missing for a window, the result is flagged (data_quality /
    warnings) with metrics = None. It NEVER fabricates a price outcome.
  * Runs offline over provided rows. No I/O in the compute path: no network, no broker/
    cTrader/QST import, no live download.

Anchor convention: anchor_time_utc = candidate['window_end_utc'] (the confirming event
that completes the sequence, e.g. the A signal in ALIGNED_CHOCH_TO_A). entry_reference
price is the close of the first candle at/after the anchor.

This module changes nothing about NOT_INTEGRATION_READY.
"""

import datetime as dt

MATCHER_VERSION = "outcome_matcher_v0_1"
HORIZONS_MIN = [15, 30, 60, 120]


def _parse(ts):
    if not ts:
        return None
    s = str(ts).strip().rstrip("Z")
    if "." in s:
        s = s[:26]
        fmt = "%Y-%m-%dT%H:%M:%S.%f"
    else:
        fmt = "%Y-%m-%dT%H:%M:%S"
    return dt.datetime.strptime(s, fmt).replace(tzinfo=dt.timezone.utc)


def _safe_flags():
    return {
        "candidate_only": True,
        "execution_allowed": False,
        "broker_execution_allowed": False,
        "qst_allowed": False,
        "order_intent": False,
        "risk_sizing_allowed": False,
    }


def _load_ohlc(rows):
    """Normalise OHLC rows to a sorted list of dicts with parsed datetime + floats.

    Skips rows that cannot be parsed (recorded via the caller's warnings if needed).
    """
    out = []
    for r in rows or []:
        t = _parse(r.get("timestamp_utc"))
        if t is None:
            continue
        try:
            o = float(r.get("open"))
            h = float(r.get("high"))
            low = float(r.get("low"))
            c = float(r.get("close"))
        except (TypeError, ValueError):
            continue
        out.append({"t": t, "open": o, "high": h, "low": low, "close": c})
    out.sort(key=lambda x: x["t"])
    return out


def _empty_metrics():
    m = {"entry_reference_price": None}
    for h in HORIZONS_MIN:
        m[f"max_favourable_excursion_{h}m"] = None
        m[f"max_adverse_excursion_{h}m"] = None
    for h in HORIZONS_MIN:
        m[f"final_close_delta_{h}m"] = None
    return m


def match_one(candidate, ohlc, index=0):
    """Outcome-match a single candidate against normalised OHLC candles."""
    warnings = []
    anchor = candidate.get("window_end_utc")
    hint = candidate.get("direction_hint")
    rec = {
        "candidate_id": candidate.get("candidate_id", f"CAND-{index:04d}"),
        "matcher_version": MATCHER_VERSION,
        "candidate_type": candidate.get("candidate_type"),
        "direction_hint": hint,
        "anchor_time_utc": anchor,
    }
    rec.update(_empty_metrics())
    rec["data_quality"] = "NO_DATA"
    rec["warnings"] = warnings
    rec.update(_safe_flags())

    at = _parse(anchor)
    if at is None:
        warnings.append("candidate has no parseable window_end_utc anchor")
        return rec
    if not ohlc:
        warnings.append("no OHLC rows supplied — cannot compute; NOT fabricated")
        return rec
    if hint not in ("LONG", "SHORT"):
        warnings.append(f"direction_hint '{hint}' is not directional; excursions oriented as LONG "
                        "for description only")

    # entry candle: first candle at/after the anchor
    entry = next((c for c in ohlc if c["t"] >= at), None)
    if entry is None:
        warnings.append("no candle at/after anchor time — outside available OHLC range; NOT fabricated")
        return rec
    gap_min = (entry["t"] - at).total_seconds() / 60.0
    if gap_min > 5:
        warnings.append(f"first candle is {gap_min:.1f} min after anchor (data gap)")
    entry_px = entry["close"]
    rec["entry_reference_price"] = round(entry_px, 4)

    long_like = (hint != "SHORT")  # LONG or non-directional -> orient upward
    horizon_ok = True
    last_t = ohlc[-1]["t"]

    for h in HORIZONS_MIN:
        end = at + dt.timedelta(minutes=h)
        # Only report a horizon when the OHLC data actually spans it — otherwise the
        # "at horizon" close and excursions would be taken from an earlier candle and
        # mislabelled. Honest: uncovered horizon -> None + warning (never fabricated).
        if last_t < end:
            rec[f"max_favourable_excursion_{h}m"] = None
            rec[f"max_adverse_excursion_{h}m"] = None
            rec[f"final_close_delta_{h}m"] = None
            horizon_ok = False
            warnings.append(f"{h}m horizon not covered (data ends {last_t.isoformat()}); left null")
            continue
        window = [c for c in ohlc if entry["t"] <= c["t"] <= end]
        if not window:
            rec[f"max_favourable_excursion_{h}m"] = None
            rec[f"max_adverse_excursion_{h}m"] = None
            rec[f"final_close_delta_{h}m"] = None
            continue
        hi = max(c["high"] for c in window)
        lo = min(c["low"] for c in window)
        close_h = window[-1]["close"]
        if long_like:
            fav = hi - entry_px          # best move up (favourable for LONG)
            adv = lo - entry_px          # worst move down (<=0, adverse for LONG)
            fcd = close_h - entry_px
        else:  # SHORT: favourable = price falling
            fav = entry_px - lo          # best move down (favourable for SHORT)
            adv = entry_px - hi          # worst move up (<=0, adverse for SHORT)
            fcd = entry_px - close_h
        rec[f"max_favourable_excursion_{h}m"] = round(fav, 4)
        rec[f"max_adverse_excursion_{h}m"] = round(adv, 4)
        rec[f"final_close_delta_{h}m"] = round(fcd, 4)

    covered_full = [h for h in HORIZONS_MIN if rec[f"final_close_delta_{h}m"] is not None]
    if not covered_full:
        rec["data_quality"] = "NO_DATA"
    elif horizon_ok and len(covered_full) == len(HORIZONS_MIN):
        rec["data_quality"] = "FULL"
    else:
        rec["data_quality"] = "PARTIAL"
    return rec


def match_all(candidates, ohlc_rows):
    """Outcome-match a list of candidates. Returns list of result dicts.

    Metrics are descriptive price statistics only. Never fabricates on missing data.
    """
    ohlc = _load_ohlc(ohlc_rows)
    return [match_one(c, ohlc, i) for i, c in enumerate(candidates)]


def read_ohlc_csv(path):
    """Read an OHLC CSV matching XAUUSD_OHLC_IMPORT_SCHEMA_v0_1. Returns list of row dicts.

    Header required: timestamp_utc,open,high,low,close,source,timeframe.
    Returns [] if the file is missing or has only a header (no fabricated data).
    """
    import csv
    import os
    if not os.path.exists(path):
        return []
    with open(path, newline="", encoding="utf-8") as f:
        return [row for row in csv.DictReader(f)]


if __name__ == "__main__":
    import json
    import sys
    cands = json.load(open(sys.argv[1], encoding="utf-8"))
    if isinstance(cands, dict):
        cands = cands.get("candidates", [])
    rows = read_ohlc_csv(sys.argv[2]) if len(sys.argv) > 2 else []
    print(json.dumps(match_all(cands, rows), indent=2))
