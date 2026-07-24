"""CHART CONTEXT EXTRACTOR v0.1 — OFFLINE / OBSERVATION-ONLY.

Reads OHLC candles and produces CANDIDATE-ONLY context evidence around a shadow
candidate's anchor. It computes PROXIES, never confirmed Farouk primitives.

NON-NEGOTIABLE (enforced by construction):
  * Nothing here is a trade, order, or recommendation. All safety flags hard-wired False.
  * It NEVER claims a real Farouk order block / FVG / BPR / displacement. Every derived
    signal is a *_candidate / *_proxy and, where the corpus threshold is UNKNOWN, is
    marked NEEDS_HUMAN_REVIEW. Session buckets are *_UTC_PROXY with
    TIMEZONE_POLICY_UNCONFIRMED. Missing HTF data -> MISSING_HTF_DATA.
  * No fabrication: missing/short OHLC -> warnings + null fields, never invented evidence.
  * Runs offline over provided rows. No I/O in compute: no network, no broker/cTrader/QST.

This module changes nothing about NOT_INTEGRATION_READY.
"""

import csv
import datetime as dt
import os

EXTRACTOR_VERSION = "chart_context_extractor_v0_1"

# ---- documented-but-UNCONFIRMED UTC session buckets (see CHART_CONTEXT_SESSION_CONFIG) ----
# Corpus cites London open 08:00Z and NY 13:30-15:00Z, but the chart/Discord timezone is
# unresolved, so these are PROXIES only.
SESSION_BUCKETS = [
    ("ASIA_UTC_PROXY", 0, 8),        # 00:00-07:59Z
    ("LONDON_UTC_PROXY", 8, 13),     # 08:00-12:59Z
    ("NEW_YORK_UTC_PROXY", 13, 21),  # 13:00-20:59Z
    ("OFF_SESSION_UTC_PROXY", 21, 24),
]

# conservative, DOCUMENTED defaults (not corpus-validated thresholds)
DEFAULT_LOOKBACK_MIN = 60
DEFAULT_FORWARD_MIN = 30
DEFAULT_ATR_LOOKBACK = 20
DEFAULT_DISPLACEMENT_MULT = 2.0   # range must exceed 2.0x rolling avg true range
DEFAULT_SWING_STRENGTH = 2         # bars each side for a local swing


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
        "candidate_only": True,
        "execution_allowed": False,
        "broker_execution_allowed": False,
        "qst_allowed": False,
        "order_intent": False,
        "risk_sizing_allowed": False,
    }


def load_ohlc(rows):
    """Normalise rows -> sorted [{t,open,high,low,close}]. Skips unparseable rows."""
    out = []
    for r in rows or []:
        t = _parse(r.get("timestamp_utc"))
        if t is None:
            continue
        try:
            o, h, l, c = (float(r["open"]), float(r["high"]), float(r["low"]), float(r["close"]))
        except (TypeError, ValueError, KeyError):
            continue
        out.append({"t": t, "open": o, "high": h, "low": l, "close": c})
    out.sort(key=lambda x: x["t"])
    return out


def read_ohlc_csv(path):
    if not path or not os.path.exists(path):
        return []
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _session_proxy(at):
    h = at.hour
    for name, lo, hi in SESSION_BUCKETS:
        if lo <= h < hi:
            return name
    return "OFF_SESSION_UTC_PROXY"


def _true_range(c, prev_close):
    return max(c["high"] - c["low"],
              abs(c["high"] - prev_close),
              abs(c["low"] - prev_close))


def extract_context(ohlc, anchor_time_utc, direction_hint=None,
                    lookback_min=DEFAULT_LOOKBACK_MIN, forward_min=DEFAULT_FORWARD_MIN,
                    atr_lookback=DEFAULT_ATR_LOOKBACK,
                    displacement_mult=DEFAULT_DISPLACEMENT_MULT,
                    swing_strength=DEFAULT_SWING_STRENGTH):
    """Extract candidate-only chart context around an anchor. ohlc = load_ohlc(...) output."""
    warnings, missing = [], []
    rec = {
        "extractor_version": EXTRACTOR_VERSION,
        "anchor_time_utc": anchor_time_utc,
        "lookback_window_minutes": lookback_min,
        "forward_window_minutes": forward_min,
        "session_context": None,
        "session_warning": "TIMEZONE_POLICY_UNCONFIRMED",
        "local_swing_high": None,
        "local_swing_low": None,
        "liquidity_sweep_candidate": False,
        "structure_shift_candidate": False,
        "displacement_candidate": False,
        "displacement_measure": None,
        "fvg_candidate": False,
        "fvg_direction": None,
        "fvg_bounds": None,
        "bpr_candidate": False,
        "order_block_candidate": False,
        "order_block_warning": "MISSING_ORDER_BLOCK_DETECTOR",
        "htf_bias_available": False,
        "htf_bias_warning": "MISSING_HTF_DATA",
        "context_confidence": "LOW",
        "missing_evidence": missing,
        "warnings": warnings,
    }
    rec.update(_safe_flags())

    at = _parse(anchor_time_utc)
    if at is None:
        warnings.append("unparseable anchor_time_utc; no context extracted (not fabricated)")
        rec["context_confidence"] = "NONE"
        return rec
    if not ohlc:
        warnings.append("no OHLC supplied; no context extracted (not fabricated)")
        rec["context_confidence"] = "NONE"
        return rec

    # session proxy (always tentative)
    rec["session_context"] = _session_proxy(at)

    lo_t = at - dt.timedelta(minutes=lookback_min)
    hi_t = at + dt.timedelta(minutes=forward_min)
    window = [c for c in ohlc if lo_t <= c["t"] <= hi_t]
    pre = [c for c in ohlc if lo_t <= c["t"] <= at]
    if len(window) < 3:
        warnings.append("fewer than 3 candles in window; proxies limited (not fabricated)")
        rec["context_confidence"] = "NONE"
        return rec

    # local swings (proxy)
    highs = [c["high"] for c in window]
    lows = [c["low"] for c in window]
    rec["local_swing_high"] = round(max(highs), 4)
    rec["local_swing_low"] = round(min(lows), 4)

    # displacement proxy: window max range vs rolling ATR of prior candles
    idx0 = ohlc.index(window[0])
    atr_src = ohlc[max(0, idx0 - atr_lookback):idx0]
    if len(atr_src) >= 2:
        trs = [_true_range(atr_src[i], atr_src[i - 1]["close"]) for i in range(1, len(atr_src))]
        atr = sum(trs) / len(trs) if trs else None
    else:
        atr = None
        missing.append("displacement ATR baseline (insufficient prior candles)")
    if atr and atr > 0:
        max_rng = max(c["high"] - c["low"] for c in window)
        rec["displacement_measure"] = {"max_candle_range": round(max_rng, 4),
                                       "atr_baseline": round(atr, 4),
                                       "ratio": round(max_rng / atr, 3),
                                       "threshold_mult": displacement_mult,
                                       "note": "NEEDS_HUMAN_REVIEW (corpus displacement size UNKNOWN)"}
        rec["displacement_candidate"] = bool(max_rng >= displacement_mult * atr)
    else:
        rec["displacement_measure"] = None

    # liquidity sweep proxy: a candle wicks beyond prior swing then closes back inside
    swept = False
    if len(pre) >= 3:
        prior = pre[:-1]
        ph, pl = max(c["high"] for c in prior), min(c["low"] for c in prior)
        last = pre[-1]
        if (last["high"] > ph and last["close"] < ph) or (last["low"] < pl and last["close"] > pl):
            swept = True
    rec["liquidity_sweep_candidate"] = swept

    # structure shift proxy (crude BOS/CHoCH): close beyond the pre-window swing extreme
    if len(pre) >= 3:
        prior = pre[:-1]
        ph, pl = max(c["high"] for c in prior), min(c["low"] for c in prior)
        last = pre[-1]
        rec["structure_shift_candidate"] = bool(last["close"] > ph or last["close"] < pl)

    # FVG proxy: 3-candle imbalance within the window. Prefer the most recent imbalance
    # COMPLETED at/before the anchor (context leading INTO the signal); fall back to the
    # last one in the window if none completes before the anchor.
    fvg = None
    fvg_pre = None
    for i in range(len(window) - 2):
        c1, c2, c3 = window[i], window[i + 1], window[i + 2]
        found = None
        if c1["high"] < c3["low"]:
            found = ("bullish", round(c1["high"], 4), round(c3["low"], 4))
        elif c1["low"] > c3["high"]:
            found = ("bearish", round(c3["high"], 4), round(c1["low"], 4))
        if found:
            fvg = found
            if c3["t"] <= at:
                fvg_pre = found
    fvg = fvg_pre or fvg
    if fvg:
        rec["fvg_candidate"] = True
        rec["fvg_direction"] = fvg[0]
        rec["fvg_bounds"] = {"lower": fvg[1], "upper": fvg[2],
                             "note": "NEEDS_HUMAN_REVIEW (not corpus-confirmed FVG; fill rule UNKNOWN)"}

    # BPR proxy: requires overlapping opposing FVGs — not implemented at v0.1
    missing.append("bpr geometry (needs opposing-FVG overlap detector) NEEDS_HUMAN_REVIEW")

    # order block: deliberately NOT claimed at v0.1
    missing.append("order_block (MISSING_ORDER_BLOCK_DETECTOR; not claimed)")

    # HTF bias: not available from a single 1m file
    missing.append("htf_bias (MISSING_HTF_DATA; no 4H/Daily/EMA feed)")

    # session is a proxy -> always missing_evidence for a *confirmed* session
    missing.append("session_context confirmed (TIMEZONE_POLICY_UNCONFIRMED)")

    # context_confidence: proxy strength only (never trade confidence)
    hits = sum([rec["liquidity_sweep_candidate"], rec["structure_shift_candidate"],
                rec["displacement_candidate"], rec["fvg_candidate"]])
    rec["context_confidence"] = "MEDIUM_PROXY" if hits >= 2 else "LOW_PROXY"
    return rec


if __name__ == "__main__":
    import json
    import sys
    ohlc = load_ohlc(read_ohlc_csv(sys.argv[1]))
    anchor = sys.argv[2] if len(sys.argv) > 2 else None
    print(json.dumps(extract_context(ohlc, anchor), indent=2))
