"""Causal feature library for the documented detector spec (RESEARCH-ONLY, offline).

Deterministic features for DOCUMENTED concepts only. Completed candles only; no forming candle;
no future bar. MTF (3m/5m) derived from the existing 1m Pepperstone feed (no new webhook).
Undocumented thresholds stay UNKNOWN (the caller decides; nothing invented here).
"""
from __future__ import annotations

from decimal import Decimal as D

UNKNOWN = "UNKNOWN"
PIP = D("0.10")   # XAUUSD: 1 pip = $0.10 (DR-301). Used by callers converting price deltas to pips.


def resample_1m(m1, tf_seconds):
    """1m -> tf bars, UTC-floored, COMPLETED only relative to the last 1m bar seen."""
    buckets = {}
    for t, o, h, l, c in m1:
        b = (t // tf_seconds) * tf_seconds
        x = buckets.get(b)
        if x is None:
            buckets[b] = [t, o, h, l, c, t]
        else:
            x[2] = max(x[2], h); x[3] = min(x[3], l)
            if t >= x[5]:
                x[4] = c; x[5] = t
    out = [(b, x[1], x[2], x[3], x[4]) for b, x in sorted(buckets.items())]
    # a tf bar is COMPLETE only if the NEXT tf bucket has begun (i.e. not the final open one)
    return out[:-1] if out else out


def completed_before(bars, ts, tf_seconds):
    return [b for b in bars if b[0] + tf_seconds <= ts]


# ---- three-candle FVG (DR-201) ---------------------------------------------------------------
def fvgs(bars):
    out = []
    for i in range(len(bars) - 2):
        b1, b3 = bars[i], bars[i + 2]
        if b1[2] < b3[3]:
            out.append({"kind": "BULLISH_FVG", "at": bars[i + 1][0], "low": b1[2], "high": b3[3]})
        elif b1[3] > b3[2]:
            out.append({"kind": "BEARISH_FVG", "at": bars[i + 1][0], "low": b3[2], "high": b1[3]})
    return out


# ---- BPR = overlap of opposing FVGs (DR-203); tolerance UNKNOWN -> exact-overlap only ----------
def bprs(bars):
    fs = fvgs(bars)
    out = []
    for i in range(len(fs)):
        for j in range(i + 1, len(fs)):
            a, b = fs[i], fs[j]
            if a["kind"] != b["kind"]:
                lo = max(a["low"], b["low"]); hi = min(a["high"], b["high"])
                if hi > lo:
                    out.append({"kind": "BPR", "low": lo, "high": hi, "components": [a["at"], b["at"]],
                                "overlap_tolerance": UNKNOWN})
    return out


# ---- OB = last opposing candle before a >=3-bar impulse (DR-204); displacement threshold UNKNOWN
def order_blocks(bars):
    out = []
    for i in range(1, len(bars) - 3):
        c0 = bars[i]
        up = all(bars[i + k][4] > bars[i + k][1] for k in range(1, 4))
        dn = all(bars[i + k][4] < bars[i + k][1] for k in range(1, 4))
        if up and c0[4] < c0[1]:
            out.append({"kind": "BULLISH_OB", "at": c0[0], "low": c0[3], "high": c0[1], "displacement_threshold": UNKNOWN})
        elif dn and c0[4] > c0[1]:
            out.append({"kind": "BEARISH_OB", "at": c0[0], "low": c0[1], "high": c0[2], "displacement_threshold": UNKNOWN})
    return out


# ---- equal high/low liquidity pools (tolerance UNKNOWN -> exact-equal only) --------------------
def equal_liquidity(bars, atol=None):
    highs, lows = {}, {}
    for b in bars:
        highs.setdefault(b[2], []).append(b[0]); lows.setdefault(b[3], []).append(b[0])
    return {"equal_highs": [{"price": str(p), "n": len(ts)} for p, ts in highs.items() if len(ts) >= 2],
            "equal_lows": [{"price": str(p), "n": len(ts)} for p, ts in lows.items() if len(ts) >= 2],
            "tolerance": UNKNOWN if atol is None else str(atol)}


# ---- sweep = wick-through + close-back-inside (DR-204) -----------------------------------------
def sweep(prev_extreme, bar, side):
    """side='high': wick above prev_extreme but close back below. 'low': mirror."""
    ts, o, h, l, c = bar
    if side == "high":
        return h > prev_extreme and c < prev_extreme
    return l < prev_extreme and c > prev_extreme


# ---- Asia range (00:00-06:00 UTC; his exact tz UNKNOWN) ---------------------------------------
def asia_range(m1_or_bars, day_ts, start_hour=0, end_hour=6):
    """Asia H/L over [start_hour, end_hour) UTC. The window is UNKNOWN in his tz; the 00-06 UTC
    default is a DISCLOSED assumption, NOT a validated value — callers may override it."""
    from datetime import datetime, timezone
    day = datetime.fromtimestamp(day_ts, timezone.utc).date()
    win = [b for b in m1_or_bars if datetime.fromtimestamp(b[0], timezone.utc).date() == day
           and start_hour <= datetime.fromtimestamp(b[0], timezone.utc).hour < end_hour]
    label = f"{start_hour:02d}-{end_hour:02d} UTC (his tz UNKNOWN; default assumption, not validated)"
    if not win:
        return {"asia_high": UNKNOWN, "asia_low": UNKNOWN, "window": label}
    return {"asia_high": max(b[2] for b in win), "asia_low": min(b[3] for b in win), "window": label}


# ---- failed-close fakeout (DR-205): wick beyond level, body fails to close beyond ----------------
def failed_close(bar, level, side):
    ts, o, h, l, c = bar
    if side == "high":
        return h > level and c <= level and max(o, c) <= level
    return l < level and c >= level and min(o, c) >= level


# ---- first HH / LL confirmation ----------------------------------------------------------------
def first_lower_low(bars, ref_low, after_ts):
    for b in bars:
        if b[0] > after_ts and b[3] < ref_low:
            return b[0]
    return None


def first_higher_high(bars, ref_high, after_ts):
    for b in bars:
        if b[0] > after_ts and b[2] > ref_high:
            return b[0]
    return None


# ---- candlestick patterns (DR-501/208) --------------------------------------------------------
def _body(o, c):
    return abs(c - o)


def hammer_or_star(bar):
    ts, o, h, l, c = bar
    body = _body(o, c) or D("0.0001")
    upper, lower = h - max(o, c), min(o, c) - l
    if lower >= 2 * body and upper <= body:
        return "HAMMER"
    if upper >= 2 * body and lower <= body:
        return "SHOOTING_STAR"
    return None


def engulfing(prev, cur):
    ts, o, h, l, c = cur
    po, pc = prev[1], prev[4]
    covers = min(o, c) <= min(po, pc) and max(o, c) >= max(po, pc)
    twice = _body(o, c) >= 2 * (_body(po, pc) or D("0.0001"))
    if covers and twice:
        return "BULLISH_ENGULFING" if c > o else "BEARISH_ENGULFING"
    return None


def star_3(b1, b2, b3):
    mid = (b1[1] + b1[4]) / 2
    if b1[4] < b1[1] and b3[4] > b3[1] and b3[4] > mid:
        return "MORNING_STAR"
    if b1[4] > b1[1] and b3[4] < b3[1] and b3[4] < mid:
        return "EVENING_STAR"
    return None
