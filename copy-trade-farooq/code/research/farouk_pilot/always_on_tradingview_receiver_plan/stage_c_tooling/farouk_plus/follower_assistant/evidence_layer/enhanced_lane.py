"""Part 8 — pre-registered Enhanced-Entry candidate, FROZEN and INACTIVE.

Exactly ONE candidate: ZONE_TOUCH_THEN_CHOCH_CONFIRMATION. This module only FREEZES the
specification (so it cannot be tuned to fit outcomes later) and provides a DISABLED evaluator.
It can never alter STRICT_FOLLOWER, never write an authoritative outcome, never call itself
Farouk's result. Live activation requires a separate ratified decision — the code cannot self-enable.
"""
from __future__ import annotations

import hashlib
import json

ENABLED = False           # hard constant; live activation is out of scope for this task

SPEC = {
    "candidate_id": "ZONE_TOUCH_THEN_CHOCH_CONFIRMATION",
    "version": "0.1.0", "status": "PRE_REGISTERED_INACTIVE",
    "timeframe": "1m (evaluation); zone from the Farouk post; CHoCH on 1m closes",
    "choch_definition": ("after price first TOUCHES the posted zone, a 1m bar CLOSES beyond the "
                         "most recent opposite 1m swing (fractal lookback=2) in the trade direction "
                         "— LONG: close above the last lower-high swing; SHORT: close below the last "
                         "higher-low swing"),
    "entry_bar": "the CLOSE of the confirming CHoCH bar (market-at-close), after zone touch",
    "stop": "the posted Farouk SL (unchanged; Enhanced never invents a stop)",
    "cancellation": "posted Farouk cancellation/invalidation, OR posted SL traded before CHoCH",
    "expiry": "24h after the setup post if no zone-touch+CHoCH sequence completes",
    "primary_comparison_metric": ("realized pips/unit of the Enhanced entry vs STRICT_FOLLOWER "
                                  "3-leg average, over the SAME campaign and SAME Pepperstone bars"),
    "guardrails": ["cannot alter STRICT_FOLLOWER", "cannot write authoritative outcome",
                   "separate evidence + expectancy ledger", "not Farouk's result",
                   "no live activation during this task"],
}
SPEC_SHA = hashlib.sha256(json.dumps(SPEC, sort_keys=True).encode()).hexdigest()


class EnhancedLaneDisabled(Exception):
    pass


def evaluate(*args, **kwargs):
    raise EnhancedLaneDisabled(
        "ZONE_TOUCH_THEN_CHOCH_CONFIRMATION is pre-registered but INACTIVE; activation requires a "
        "separate ratified decision. STRICT_FOLLOWER is never affected.")


def frozen_spec_record():
    return {"record_type": "ENHANCED_LANE_SPEC", "spec": SPEC, "spec_sha256": SPEC_SHA,
            "enabled": ENABLED}
