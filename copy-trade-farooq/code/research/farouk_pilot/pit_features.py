"""
Point-in-time (PIT) market-feature reconstruction for the pilot. HARD RULE: at evaluation time T, no
derived feature may use any candle occurring AFTER T. Every function filters strictly on `ts_ms <=
as_of_ms`, so mutating or appending future candles can never change an earlier feature, session
high/low, or decision. Prices are decimal strings, compared exactly via Decimal (no float drift).
Read-only over supplied market data; no network, no trading.
"""
from __future__ import annotations
import calendar
import re
import time
from decimal import Decimal

_ISO_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?Z$")


def parse_iso_utc_ms(iso):
    """Parse a strict ISO-8601 UTC instant ('...Z') to epoch milliseconds. Rejects non-UTC/malformed."""
    if not isinstance(iso, str) or not _ISO_RE.match(iso):
        raise ValueError("INVALID_ISO_UTC:" + str(iso))
    base = iso[:-1].split(".")[0]
    ms = 0
    if "." in iso:
        frac = iso[:-1].split(".")[1]
        ms = int((frac + "000")[:3])
    return calendar.timegm(time.strptime(base, "%Y-%m-%dT%H:%M:%S")) * 1000 + ms


def _d(s):
    return Decimal(str(s))


def _upto(candles, as_of_ms, since_ms=None):
    """Strictly causal slice: candles with (since_ms <=) ts_ms <= as_of_ms, sorted by ts."""
    out = [c for c in candles if c.get("ts_ms") is not None and c["ts_ms"] <= as_of_ms
           and (since_ms is None or c["ts_ms"] >= since_ms)]
    return sorted(out, key=lambda c: c["ts_ms"])


def session_high_low(candles, *, as_of_ms, session_start_ms):
    """Session high/low AS OF T, using only candles in [session_start_ms, as_of_ms]. Future candles
    are ignored by construction."""
    seg = _upto(candles, as_of_ms, since_ms=session_start_ms)
    if not seg:
        return {"session_high": None, "session_low": None, "candles_used": 0, "as_of_ms": as_of_ms}
    hi = max(_d(c["high"]) for c in seg)
    lo = min(_d(c["low"]) for c in seg)
    return {"session_high": str(hi), "session_low": str(lo), "candles_used": len(seg), "as_of_ms": as_of_ms}


def previous_day_levels(candles, *, as_of_ms, prev_day_start_ms, prev_day_end_ms):
    """Prior completed-day high/low/close from candles strictly BEFORE the current point, within the
    previous day's window. Never uses anything after T."""
    if prev_day_end_ms > as_of_ms:
        prev_day_end_ms = as_of_ms
    seg = _upto(candles, prev_day_end_ms, since_ms=prev_day_start_ms)
    if not seg:
        return {"prev_high": None, "prev_low": None, "prev_close": None}
    hi = max(_d(c["high"]) for c in seg)
    lo = min(_d(c["low"]) for c in seg)
    return {"prev_high": str(hi), "prev_low": str(lo), "prev_close": str(_d(seg[-1]["close"]))}


def features_as_of(candles, *, as_of_ms, session_start_ms):
    """Bundle of strictly-causal PIT features at T. Extend here; all consumers inherit the T cutoff."""
    shl = session_high_low(candles, as_of_ms=as_of_ms, session_start_ms=session_start_ms)
    seg = _upto(candles, as_of_ms, since_ms=session_start_ms)
    last = seg[-1] if seg else None
    return {"as_of_ms": as_of_ms, "session_high": shl["session_high"], "session_low": shl["session_low"],
            "last_close": (str(_d(last["close"])) if last else None), "candles_used": len(seg),
            "uses_only_past_or_present": all(c["ts_ms"] <= as_of_ms for c in seg)}


def excursion(candles, *, entry_decimal_string, direction, from_ms, to_ms):
    """MFE/MAE within [from_ms, to_ms] (needs market data). direction BUY/LONG or SELL/SHORT. Causal:
    only candles within the window. Returns decimal strings or None if no data."""
    seg = _upto(candles, to_ms, since_ms=from_ms)
    if not seg:
        return {"mfe": None, "mae": None, "candles_used": 0}
    entry = _d(entry_decimal_string)
    hi = max(_d(c["high"]) for c in seg)
    lo = min(_d(c["low"]) for c in seg)
    d = str(direction).upper()
    if d in ("BUY", "LONG"):
        mfe, mae = hi - entry, entry - lo
    else:                                                # SELL / SHORT
        mfe, mae = entry - lo, hi - entry
    return {"mfe": str(mfe), "mae": str(mae), "candles_used": len(seg)}
