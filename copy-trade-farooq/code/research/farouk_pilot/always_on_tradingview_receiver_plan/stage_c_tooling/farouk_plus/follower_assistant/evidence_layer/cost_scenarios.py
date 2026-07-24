"""Part 5 — shadow-only cost scenario VIEWS over a raw follower result.

No cost lane alters the raw authoritative outcome: each view takes the frozen realized/unrealized
pips and applies an EXPLICIT, VERSIONED assumption block, returning a derived number tagged as
a view. RAW_SHADOW is the untouched value. Assumptions are justified from repo evidence, not a
generic hard-coded 1-pip penalty.
"""
from __future__ import annotations

from decimal import Decimal as D

ASSUMPTIONS_VERSION = "cost_assumptions_v0_1"

# Justification: XAUUSD retail spread on Pepperstone-class feeds is commonly ~$0.10-0.30 (1-3
# pips) in liquid sessions, wider in Asia/rollover. Slippage on limit fills ~0; on
# instruction-driven market exits ~0.5-1 pip. These are STRESS BRACKETS, not truths — every
# campaign records which bracket applied so the band can be re-fit against real fills at n>=15.
ASSUMPTIONS = {
    "RAW_SHADOW": {"spread_pips": "0", "slippage_pips_per_fill": "0",
                   "note": "untouched raw follower result"},
    "BASE_COST": {"spread_pips": "1.5", "slippage_pips_per_fill": "0.5",
                  "justification": "typical liquid-session XAUUSD spread ~1.5 pip + modest exec slippage"},
    "STRESSED_COST": {"spread_pips": "3.0", "slippage_pips_per_fill": "1.5",
                      "justification": "Asia/rollover/news widening; VR-21 cross-feed divergence up to $2.9"},
    "FEED_SENSITIVITY": {"spread_pips": "0", "slippage_pips_per_fill": "0", "feed_shift_pips": "30",
                         "justification": "±$3 (30 pip) cross-feed level shift per VR-21; applies to touch/graze outcomes, not spread"},
}


def apply_views(*, realized_pips, unrealized_pips, n_fills, n_partial_exits, feed_sensitive_events=0):
    """Return one derived view per scenario. Deterministic, additive, never mutates inputs."""
    raw_r = D(str(realized_pips))
    raw_u = D(str(unrealized_pips)) if unrealized_pips not in (None, "UNKNOWN") else None
    out = {"record_type": "COST_SCENARIO_VIEWS", "assumptions_version": ASSUMPTIONS_VERSION,
           "raw_inputs": {"realized_pips": str(raw_r),
                          "unrealized_pips": str(raw_u) if raw_u is not None else "UNKNOWN"},
           "views": {}}
    fills = max(int(n_fills), 0)
    exits = max(int(n_partial_exits), 0)
    for name, a in ASSUMPTIONS.items():
        spread = D(a.get("spread_pips", "0"))
        slip = D(a.get("slippage_pips_per_fill", "0"))
        # cost model: spread charged once per fill (entry) + per partial exit; slippage per fill+exit
        cost = spread * (fills + exits) + slip * (fills + exits)
        view = {"assumptions": a}
        if name == "FEED_SENSITIVITY":
            view["realized_pips"] = str(raw_r)     # spread untouched; sensitivity is level-shift
            view["feed_sensitive_events"] = feed_sensitive_events
            view["note"] = ("outcome could flip on the other feed for events within the $3 band; "
                            "see second_feed_divergence records")
        else:
            view["realized_pips_after_cost"] = str((raw_r - cost).quantize(D("0.01")))
            view["applied_cost_pips"] = str(cost.quantize(D("0.01")))
            if raw_u is not None:
                view["unrealized_pips_after_cost"] = str((raw_u - cost).quantize(D("0.01")))
        out["views"][name] = view
    out["headline_unchanged"] = "RAW authoritative outcome is untouched; these are derived views only"
    return out
