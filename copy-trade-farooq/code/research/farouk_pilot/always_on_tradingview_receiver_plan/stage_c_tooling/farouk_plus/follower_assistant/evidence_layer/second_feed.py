"""Part 7 — read-only SECOND-XAU-FEED divergence adapter (sensitivity ONLY).

Never replaces Pepperstone, never sets the headline result, never picks the more profitable
provider. It takes two bar series (Pepperstone = authoritative; comparison = any read-only second
feed) and reports boundary differences + touch DISAGREEMENTS at named levels, so feed-sensitive
outcomes are visible. If no second feed can be connected without credentials/architecture
expansion, the adapter + schema still stand and the comparison series is simply absent -> UNKNOWN.

The only real second source available credential-free is the existing DukascopyBarProvider (delayed,
non-Pepperstone). Live connection is NOT performed here; the adapter accepts whatever comparison
bars are supplied (offline-testable).
"""
from __future__ import annotations

from decimal import Decimal as D

UNKNOWN = "UNKNOWN"


def _index(bars):
    return {b[0]: b for b in bars} if bars else {}


def divergence_report(*, pepperstone_bars, comparison_bars, comparison_provider, levels):
    """levels: list of {name, price, direction} to test for touch agreement (e.g. stop, BE, zone edges).
    Returns per-level agreement + per-bar boundary deltas where both feeds have the same minute."""
    if not comparison_bars:
        return {"record_type": "SECOND_FEED_DIVERGENCE", "status": "NO_COMPARISON_FEED_CONNECTED",
                "comparison_provider": comparison_provider or UNKNOWN,
                "note": "adapter + schema present; no credentialed second feed connected (by design)",
                "authoritative_feed": "PEPPERSTONE_TV_BAR_FEED",
                "boundary_deltas": UNKNOWN, "touch_disagreements": UNKNOWN}
    pep, cmp_ = _index(pepperstone_bars), _index(comparison_bars)
    common = sorted(set(pep) & set(cmp_))
    deltas = []
    for ts in common:
        pb, cb = pep[ts], cmp_[ts]
        deltas.append({"ts": ts, "high_delta": str(cb[2] - pb[2]), "low_delta": str(cb[3] - pb[3]),
                       "close_delta": str(cb[4] - pb[4])})
    disagreements = []
    for lvl in (levels or []):
        p, name, dirn = D(str(lvl["price"])), lvl["name"], lvl.get("direction", "LONG")
        def touched(series):
            for ts in common:
                b = series[ts]
                if (b[3] <= p) if dirn == "LONG" else (b[2] >= p):
                    return ts
            return None
        pt, ct = touched(pep), touched(cmp_)
        if (pt is None) != (ct is None) or (pt is not None and ct is not None and pt != ct):
            disagreements.append({"level": name, "price": str(p),
                                  "pepperstone_touch_ts": pt, "comparison_touch_ts": ct,
                                  "class": "FEED_SENSITIVE_TOUCH_DISAGREEMENT"})
    maxabs = max((abs(D(d["high_delta"])) for d in deltas), default=D(0))
    return {"record_type": "SECOND_FEED_DIVERGENCE", "status": "COMPARED",
            "authoritative_feed": "PEPPERSTONE_TV_BAR_FEED",
            "comparison_provider": comparison_provider, "common_bars": len(common),
            "max_abs_high_delta": str(maxabs), "boundary_deltas_sample": deltas[:5],
            "touch_disagreements": disagreements,
            "sensitivity_only": "never replaces Pepperstone; never sets the headline; never picks the better feed"}
