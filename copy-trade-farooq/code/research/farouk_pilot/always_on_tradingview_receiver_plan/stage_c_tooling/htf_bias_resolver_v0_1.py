"""HTF BIAS RESOLVER v0.1 — OFFLINE / OBSERVATION-ONLY.

Aggregates imported 1m OHLC into 15m and 1h bars and computes a SIMPLE EMA-based
directional bias PROXY around an anchor. It NEVER claims a confirmed Farouk HTF bias
(the corpus does not define an exact EMA period / bias rule — see the session policy
and factor map). Labels are *_PROXY only.

NON-NEGOTIABLE (enforced by construction):
  * Output is candidate-only; execution / broker / qst / order_intent / risk_sizing = False.
  * Bias is HTF_BIAS_PROXY: BULLISH_PROXY / BEARISH_PROXY / NEUTRAL_OR_INSUFFICIENT_DATA.
    Never a confirmed HTF bias, never a signal.
  * No fabrication: too little data -> NEUTRAL_OR_INSUFFICIENT_DATA + warning.
  * Offline over provided rows. No network, no broker/cTrader/QST, no live download.

This module changes nothing about NOT_INTEGRATION_READY.
"""

import datetime as dt

RESOLVER_VERSION = "htf_bias_resolver_v0_1"

# proxy EMA period (documented default; NOT a corpus-confirmed Farouk parameter)
DEFAULT_EMA_PERIOD = 20
# minimum aggregated bars needed to compute a proxy at each timeframe
MIN_BARS_15M = DEFAULT_EMA_PERIOD + 2
MIN_BARS_1H = DEFAULT_EMA_PERIOD + 2


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


def _to_rows(ohlc):
    """Accept raw CSV-dict rows OR already-parsed {t,open,high,low,close}."""
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


def aggregate(ohlc_1m, minutes):
    """Aggregate 1m bars into `minutes`-buckets (floor to bucket start). Returns OHLC list."""
    rows = _to_rows(ohlc_1m)
    buckets = {}
    order = []
    for c in rows:
        epoch_min = int(c["t"].timestamp() // 60)
        key = (epoch_min // minutes) * minutes
        if key not in buckets:
            buckets[key] = {"t": dt.datetime.fromtimestamp(key * 60, dt.timezone.utc),
                            "open": c["open"], "high": c["high"], "low": c["low"], "close": c["close"]}
            order.append(key)
        else:
            b = buckets[key]
            b["high"] = max(b["high"], c["high"])
            b["low"] = min(b["low"], c["low"])
            b["close"] = c["close"]
    return [buckets[k] for k in order]


def _ema(values, period):
    if len(values) < period:
        return None
    k = 2.0 / (period + 1)
    ema = sum(values[:period]) / period  # seed with SMA
    for v in values[period:]:
        ema = v * k + ema * (1 - k)
    return ema


def _bias_at(bars, anchor_dt, ema_period):
    """Proxy bias from close vs EMA using only bars at/before the anchor."""
    upto = [b for b in bars if b["t"] <= anchor_dt] if anchor_dt else bars
    if len(upto) < ema_period + 1:
        return "NEUTRAL_OR_INSUFFICIENT_DATA", None, len(upto)
    closes = [b["close"] for b in upto]
    ema = _ema(closes, ema_period)
    if ema is None:
        return "NEUTRAL_OR_INSUFFICIENT_DATA", None, len(upto)
    last = closes[-1]
    if last > ema:
        return "BULLISH_PROXY", round(last - ema, 4), len(upto)
    if last < ema:
        return "BEARISH_PROXY", round(last - ema, 4), len(upto)
    return "NEUTRAL_OR_INSUFFICIENT_DATA", 0.0, len(upto)


def resolve_htf_bias(ohlc_1m, anchor_time_utc=None, ema_period=DEFAULT_EMA_PERIOD):
    """Resolve a proxy HTF bias at 15m and 1h around the anchor."""
    warnings = []
    anchor_dt = _parse(anchor_time_utc) if anchor_time_utc else None
    if anchor_time_utc and anchor_dt is None:
        warnings.append("unparseable anchor_time_utc; using full series")

    bars15 = aggregate(ohlc_1m, 15)
    bars1h = aggregate(ohlc_1m, 60)

    b15, d15, n15 = _bias_at(bars15, anchor_dt, ema_period)
    b1h, d1h, n1h = _bias_at(bars1h, anchor_dt, ema_period)

    if n15 < MIN_BARS_15M:
        warnings.append(f"15m window too short ({n15} bars < {MIN_BARS_15M}); NEUTRAL_OR_INSUFFICIENT_DATA")
    if n1h < MIN_BARS_1H:
        warnings.append(f"1h window too short ({n1h} bars < {MIN_BARS_1H}); NEUTRAL_OR_INSUFFICIENT_DATA")

    # combined proxy: agree -> that bias; disagree/insufficient -> neutral
    if b15 == b1h and b15 in ("BULLISH_PROXY", "BEARISH_PROXY"):
        combined = b15
    elif "NEUTRAL_OR_INSUFFICIENT_DATA" in (b15, b1h) and b15 != b1h:
        combined = next(b for b in (b15, b1h) if b != "NEUTRAL_OR_INSUFFICIENT_DATA")
        warnings.append("only one timeframe had sufficient data; combined = that timeframe (weak)")
    elif b15 != b1h:
        combined = "NEUTRAL_OR_INSUFFICIENT_DATA"
        warnings.append("15m and 1h proxies disagree; combined = NEUTRAL")
    else:
        combined = "NEUTRAL_OR_INSUFFICIENT_DATA"

    rec = {
        "resolver_version": RESOLVER_VERSION,
        "anchor_time_utc": anchor_time_utc,
        "ema_period_proxy": ema_period,
        "htf_bias_proxy": combined,           # BULLISH_PROXY / BEARISH_PROXY / NEUTRAL_OR_INSUFFICIENT_DATA
        "bias_15m_proxy": b15,
        "bias_1h_proxy": b1h,
        "close_minus_ema_15m": d15,
        "close_minus_ema_1h": d1h,
        "bars_15m": n15,
        "bars_1h": n1h,
        "confirmed_farouk_htf_bias": False,   # never claimed — corpus has no exact rule
        "note": "HTF_BIAS_PROXY only; corpus defines no exact EMA/bias rule (NEEDS_HUMAN_REVIEW)",
        "warnings": warnings,
    }
    rec.update(_safe_flags())
    return rec


if __name__ == "__main__":
    import json
    import sys
    import csv
    rows = list(csv.DictReader(open(sys.argv[1], newline="", encoding="utf-8")))
    anchor = sys.argv[2] if len(sys.argv) > 2 else None
    print(json.dumps(resolve_htf_bias(rows, anchor), indent=2))
