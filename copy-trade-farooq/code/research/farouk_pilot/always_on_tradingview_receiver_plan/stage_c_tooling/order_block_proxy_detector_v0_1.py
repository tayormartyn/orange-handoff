"""ORDER BLOCK PROXY DETECTOR v0.1 — OFFLINE / OBSERVATION-ONLY.

Looks for POSSIBLE order-block context around a candidate anchor using only OHLC.
It computes a PROXY (last opposite-colour candle before a displacement proxy) and
ALWAYS requires human review. It NEVER claims a confirmed Farouk order block, and
NEVER emits a tradeable entry zone.

NON-NEGOTIABLE (enforced by construction):
  * candidate_only=true; execution/broker/qst/order_intent/risk_sizing = False.
  * `order_block_proxy_found` is a PROXY; `requires_human_review=true`; confidence LOW only.
  * Zone bounds are DESCRIPTIVE evidence, not an entry zone. No SL/TP/size/route.
  * No invented thresholds (displacement size / mitigation count are UNKNOWN in corpus).
  * No fabrication: missing/short OHLC -> warnings + not-found, never invented.
  * Offline; no network, no broker/cTrader/QST.

This module changes nothing about NOT_INTEGRATION_READY.
"""

import datetime as dt

DETECTOR_VERSION = "order_block_proxy_detector_v0_1"

DEFAULT_LOOKBACK_MIN = 90
DEFAULT_ATR_LOOKBACK = 20
DEFAULT_DISPLACEMENT_MULT = 2.0   # documented default (NOT corpus-confirmed)


def _parse(ts):
    if not ts:
        return None
    s = str(ts).strip().rstrip("Z")
    if "." in s:
        s = s[:26]
        fmt = "%Y-%m-%dT%H:%M:%S.%f"
    else:
        fmt = "%Y-%m-%dT%H:%M:%S"
    try:
        return dt.datetime.strptime(s, fmt).replace(tzinfo=dt.timezone.utc)
    except ValueError:
        return None


def _safe_flags():
    return {
        "requires_human_review": True,
        "candidate_only": True,
        "execution_allowed": False,
        "broker_execution_allowed": False,
        "qst_allowed": False,
        "order_intent": False,
        "risk_sizing_allowed": False,
    }


def _to_rows(ohlc):
    out = []
    for r in ohlc or []:
        if "t" in r and isinstance(r["t"], dt.datetime):
            out.append(r)
            continue
        t = _parse(r.get("timestamp_utc"))
        if t is None:
            continue
        try:
            out.append({"t": t, "open": float(r["open"]), "high": float(r["high"]),
                        "low": float(r["low"]), "close": float(r["close"])})
        except (TypeError, ValueError, KeyError):
            continue
    out.sort(key=lambda x: x["t"])
    return out


def _true_range(c, prev_close):
    return max(c["high"] - c["low"], abs(c["high"] - prev_close), abs(c["low"] - prev_close))


def detect_order_block_proxy(ohlc, anchor_time_utc, direction_hint=None,
                             lookback_min=DEFAULT_LOOKBACK_MIN,
                             atr_lookback=DEFAULT_ATR_LOOKBACK,
                             displacement_mult=DEFAULT_DISPLACEMENT_MULT):
    """Detect a conservative OB proxy before the anchor. Returns a dict (proxy-only)."""
    warnings, missing = [], []
    rec = {
        "detector_version": DETECTOR_VERSION,
        "anchor_time_utc": anchor_time_utc,
        "direction_hint": direction_hint,
        "order_block_proxy_found": False,
        "proxy_direction": None,
        "candidate_candle_time_utc": None,
        "candidate_zone_high": None,
        "candidate_zone_low": None,
        "displacement_after_candidate": False,
        "displacement_ratio": None,
        "mitigation_touched": None,
        "distance_from_anchor_min": None,
        "confidence": "LOW",                 # never higher at v0.1
        "evidence_summary": None,
        "missing_evidence": missing,
        "warnings": warnings,
        "note": "PROXY only; NEEDS_HUMAN_REVIEW; not a confirmed Farouk order block; "
                "zone bounds are descriptive evidence, not an entry zone",
    }
    rec.update(_safe_flags())

    rows = _to_rows(ohlc)
    at = _parse(anchor_time_utc)
    if at is None:
        warnings.append("unparseable anchor_time_utc; no OB proxy (not fabricated)")
        return rec
    if not rows:
        warnings.append("no OHLC supplied; no OB proxy (not fabricated)")
        return rec
    if direction_hint not in ("LONG", "SHORT"):
        warnings.append(f"direction_hint '{direction_hint}' not directional; OB proxy needs a side")
        missing.append("directional hint required for OB side")
        return rec

    lo_t = at - dt.timedelta(minutes=lookback_min)
    window = [c for c in rows if lo_t <= c["t"] <= at]
    if len(window) < 5:
        warnings.append("fewer than 5 candles before anchor; OB proxy not evaluated (not fabricated)")
        return rec

    # ATR baseline from candles just before the window
    idx0 = rows.index(window[0])
    atr_src = rows[max(0, idx0 - atr_lookback):idx0]
    if len(atr_src) >= 2:
        trs = [_true_range(atr_src[i], atr_src[i - 1]["close"]) for i in range(1, len(atr_src))]
        atr = sum(trs) / len(trs) if trs else None
    else:
        atr = None
    if not atr or atr <= 0:
        missing.append("displacement ATR baseline (insufficient prior candles)")
        warnings.append("no ATR baseline; cannot assess displacement -> OB proxy not confirmed")
        return rec

    want_up = (direction_hint == "LONG")   # LONG -> bullish displacement; SHORT -> bearish
    # find displacement-proxy candles of the right colour; pick the LAST before the anchor
    disp_idx = None
    for i in range(len(window)):
        c = window[i]
        rng = c["high"] - c["low"]
        bullish = c["close"] > c["open"]
        bearish = c["close"] < c["open"]
        if rng >= displacement_mult * atr and ((want_up and bullish) or (not want_up and bearish)):
            disp_idx = i  # keep last (closest to anchor)
    if disp_idx is None:
        missing.append("displacement proxy after a candidate candle (none of required colour/size)")
        rec["evidence_summary"] = "no qualifying displacement proxy before anchor"
        return rec

    disp = window[disp_idx]
    rec["displacement_after_candidate"] = True
    rec["displacement_ratio"] = round((disp["high"] - disp["low"]) / atr, 3)

    # OB proxy = last OPPOSITE-colour candle immediately before the displacement
    ob = None
    for j in range(disp_idx - 1, -1, -1):
        c = window[j]
        opp = (c["close"] < c["open"]) if want_up else (c["close"] > c["open"])
        if opp:
            ob = c
            break
    if ob is None:
        missing.append("no opposite-colour candle before displacement (no OB proxy candle)")
        rec["evidence_summary"] = "displacement present but no preceding opposite candle"
        return rec

    zone_high = round(max(ob["open"], ob["close"]), 4)  # body bounds (descriptive only)
    zone_low = round(min(ob["open"], ob["close"]), 4)
    rec["order_block_proxy_found"] = True
    rec["proxy_direction"] = "BULLISH_OB_PROXY" if want_up else "BEARISH_OB_PROXY"
    rec["candidate_candle_time_utc"] = ob["t"].isoformat().replace("+00:00", "Z")
    rec["candidate_zone_high"] = zone_high
    rec["candidate_zone_low"] = zone_low
    rec["distance_from_anchor_min"] = round((at - ob["t"]).total_seconds() / 60.0, 1)

    # mitigation proxy: did price re-enter the zone AFTER the displacement (up to anchor)?
    after = window[disp_idx + 1:]
    touched = any(c["low"] <= zone_high and c["high"] >= zone_low for c in after)
    rec["mitigation_touched"] = bool(touched)
    if touched:
        rec["evidence_summary"] = ("OB proxy: opposite candle before displacement; zone re-entered after "
                                   "(mitigation proxy) -> degraded (may be 'spent'); NEEDS_HUMAN_REVIEW")
    else:
        rec["evidence_summary"] = ("OB proxy: opposite candle before displacement; zone not yet re-entered "
                                   "before anchor (fresh proxy); NEEDS_HUMAN_REVIEW")

    # corpus-UNKNOWN pieces we deliberately do not assert
    missing.append("FVG-left-behind confirmation (strong-OB precondition) NEEDS_HUMAN_REVIEW")
    missing.append("first-tap/mitigation numeric rule UNKNOWN in corpus")
    missing.append("trend/HTF alignment (no confirmed rule)")
    rec["confidence"] = "LOW"  # explicit: never above LOW at v0.1
    return rec


if __name__ == "__main__":
    import json
    import sys
    import csv
    rows = list(csv.DictReader(open(sys.argv[1], newline="", encoding="utf-8")))
    anchor = sys.argv[2] if len(sys.argv) > 2 else None
    hint = sys.argv[3] if len(sys.argv) > 3 else "LONG"
    print(json.dumps(detect_order_block_proxy(rows, anchor, hint), indent=2))
