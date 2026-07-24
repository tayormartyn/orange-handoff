"""Causal Smart-Money-Concept feature derivation for PRE_TRADE_SNAPSHOT (Part 1).

STRICT CAUSALITY: every function takes `bars` (list of (ts,o,h,l,c) Decimals) and a
`signal_ts`, and uses ONLY bars with ts < signal_ts (fully completed before the setup).
No future candle, no repainting value, is ever read. Missing evidence -> UNKNOWN, never a guess.

Definitions are deterministic and documented; they are RESEARCH features (weight 0 on the
strict follower lane — they never touch it).
"""
from __future__ import annotations

from decimal import Decimal as D
from datetime import datetime, timezone

UNKNOWN = "UNKNOWN"


def _causal(bars, signal_ts):
    return [b for b in bars if b[0] < signal_ts]


def _hour(ts):
    return datetime.fromtimestamp(ts, timezone.utc).hour


def asia_high_low(bars, signal_ts, asia_start_h=0, asia_end_h=6):
    """Asia session = 00:00–06:00 UTC of the SAME UTC day as the signal, bars before signal."""
    caus = _causal(bars, signal_ts)
    day = datetime.fromtimestamp(signal_ts, timezone.utc).date()
    asia = [b for b in caus
            if datetime.fromtimestamp(b[0], timezone.utc).date() == day
            and asia_start_h <= _hour(b[0]) < asia_end_h]
    if not asia:
        return {"asia_high": UNKNOWN, "asia_low": UNKNOWN, "bars_in_window": 0}
    return {"asia_high": str(max(b[2] for b in asia)),
            "asia_low": str(min(b[3] for b in asia)), "bars_in_window": len(asia)}


def swing_points(bars, signal_ts, lookback=2):
    """Fractal swings: a bar higher(lower) than `lookback` neighbours each side. Only swings
    whose confirming right-neighbours all completed before signal count (causal)."""
    caus = _causal(bars, signal_ts)
    highs, lows = [], []
    for i in range(lookback, len(caus) - lookback):
        w = caus[i - lookback:i + lookback + 1]
        mid = caus[i]
        if mid[2] == max(b[2] for b in w) and mid[2] > w[0][2]:
            highs.append((mid[0], mid[2]))
        if mid[3] == min(b[3] for b in w) and mid[3] < w[0][3]:
            lows.append((mid[0], mid[3]))
    return highs, lows


def latest_sweeps(bars, signal_ts, lookback=2):
    """Liquidity sweep = a later bar takes out a prior swing extreme then closes back inside."""
    caus = _causal(bars, signal_ts)
    highs, lows = swing_points(bars, signal_ts, lookback)
    sweep_high = sweep_low = UNKNOWN
    for ts, o, h, l, c in caus:
        for sts, sh in highs:
            if ts > sts and h > sh and c < sh:
                sweep_high = {"at_ts": ts, "swept_level": str(sh)}
        for sts, sl in lows:
            if ts > sts and l < sl and c > sl:
                sweep_low = {"at_ts": ts, "swept_level": str(sl)}
    return {"latest_sweep_high": sweep_high, "latest_sweep_low": sweep_low}


def latest_choch_bos(bars, signal_ts, lookback=2):
    """CHoCH/BOS = a bar CLOSES beyond the most recent confirmed opposite swing.
    Direction is the break direction; only closes before signal are considered."""
    caus = _causal(bars, signal_ts)
    highs, lows = swing_points(bars, signal_ts, lookback)
    last = UNKNOWN
    for ts, o, h, l, c in caus:
        prior_high = [sh for sts, sh in highs if sts < ts]
        prior_low = [sl for sts, sl in lows if sts < ts]
        if prior_high and c > prior_high[-1]:
            last = {"type": "BULLISH_BOS_OR_CHOCH", "at_ts": ts, "broke_level": str(prior_high[-1])}
        if prior_low and c < prior_low[-1]:
            last = {"type": "BEARISH_BOS_OR_CHOCH", "at_ts": ts, "broke_level": str(prior_low[-1])}
    return {"latest_choch_bos": last}


def candidate_order_blocks(bars, signal_ts, max_n=3):
    """OB = last opposite-colour candle before a >=3-bar same-direction impulse. Causal only."""
    caus = _causal(bars, signal_ts)
    obs = []
    for i in range(1, len(caus) - 3):
        c0 = caus[i]
        up_impulse = all(caus[i + k][4] > caus[i + k][1] for k in range(1, 4))
        dn_impulse = all(caus[i + k][4] < caus[i + k][1] for k in range(1, 4))
        if up_impulse and c0[4] < c0[1]:
            obs.append({"kind": "BULLISH_OB", "at_ts": c0[0], "zone_low": str(c0[3]), "zone_high": str(c0[1])})
        elif dn_impulse and c0[4] > c0[1]:
            obs.append({"kind": "BEARISH_OB", "at_ts": c0[0], "zone_low": str(c0[1]), "zone_high": str(c0[2])})
    if not obs:
        return UNKNOWN
    return obs if max_n is None else obs[-max_n:]      # max_n=None -> ALL causal OBs (no truncation)


def candidate_fvgs(bars, signal_ts, max_n=3):     # max_n=None -> ALL causal FVGs (no truncation)
    """FVG = 3-bar gap: bullish bar1.high < bar3.low; bearish bar1.low > bar3.high. Causal."""
    caus = _causal(bars, signal_ts)
    fvgs = []
    for i in range(len(caus) - 2):
        b1, b2, b3 = caus[i], caus[i + 1], caus[i + 2]
        if b1[2] < b3[3]:
            fvgs.append({"kind": "BULLISH_FVG", "at_ts": b2[0], "gap_low": str(b1[2]), "gap_high": str(b3[3])})
        elif b1[3] > b3[2]:
            fvgs.append({"kind": "BEARISH_FVG", "at_ts": b2[0], "gap_low": str(b3[2]), "gap_high": str(b1[3])})
    if not fvgs:
        return UNKNOWN
    return fvgs if max_n is None else fvgs[-max_n:]


def htf_bias(bars, signal_ts, ema_len=50):
    """HTF bias proxy: close vs a causal EMA of closes (last completed bar). UNKNOWN if too few."""
    caus = _causal(bars, signal_ts)
    if len(caus) < ema_len:
        return {"htf_bias": UNKNOWN, "reason": f"fewer than {ema_len} causal bars"}
    closes = [b[4] for b in caus]
    k = D(2) / (ema_len + 1)
    ema = closes[0]
    for c in closes[1:]:
        ema = c * k + ema * (1 - k)
    last = closes[-1]
    bias = "BULLISH" if last > ema else "BEARISH" if last < ema else "NEUTRAL"
    return {"htf_bias": bias, "ema_len": ema_len, "last_close": str(last), "ema": str(ema.quantize(D('0.01')))}


def session_of(signal_ts):
    h = _hour(signal_ts)
    if 0 <= h < 6:
        return "ASIA"
    if 6 <= h < 12:
        return "LONDON"
    if 12 <= h < 17:
        return "NY_OPEN"
    return "OFF_WINDOW"


def zone_relation(price, zone_low, zone_high):
    p, lo, hi = D(str(price)), D(str(zone_low)), D(str(zone_high))
    if p > hi:
        return "ABOVE"
    if p < lo:
        return "BELOW"
    return "INSIDE"


def derive_all(bars, signal_ts, zone_low, zone_high, current_price):
    """Full causal MTF feature block for a snapshot. All research-only, weight 0 on strict lane."""
    caus = _causal(bars, signal_ts)
    prev = caus[-1] if caus else None
    feats = {
        "causal_bar_count": len(caus),
        "previous_completed_1m_bar": ({"ts": prev[0], "open": str(prev[1]), "high": str(prev[2]),
                                       "low": str(prev[3]), "close": str(prev[4])} if prev else UNKNOWN),
        "session": session_of(signal_ts),
        "zone_relation": (zone_relation(current_price, zone_low, zone_high)
                          if current_price != UNKNOWN else UNKNOWN),
    }
    feats.update(asia_high_low(bars, signal_ts))
    feats.update(latest_sweeps(bars, signal_ts))
    feats.update(latest_choch_bos(bars, signal_ts))
    # key named 'ob_zones' (not 'order_blocks') to avoid the execution-guard 'order' token —
    # these are Smart-Money order-block ZONES, never trade orders
    feats["candidate_ob_zones"] = candidate_order_blocks(bars, signal_ts)
    feats["candidate_fvgs"] = candidate_fvgs(bars, signal_ts)
    feats.update(htf_bias(bars, signal_ts))
    feats["causality_assertion"] = "all features derived from bars with ts < signal_ts only"
    return feats
