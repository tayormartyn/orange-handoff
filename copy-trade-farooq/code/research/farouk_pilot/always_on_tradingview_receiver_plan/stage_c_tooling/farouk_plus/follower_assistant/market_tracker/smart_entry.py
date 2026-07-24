"""ORANGE_SMART_ENTRY — experimental interface boundary (Part 12). DISABLED.

Rules (enforced structurally, not by promises):
  * ENABLED is hardcoded False; enable() raises. Activation requires a NEW ratified
    constitution revision — code cannot flip it.
  * The interface can NEVER write the authoritative strict lane: it has no reference to
    tracker_ledger/follower_ledger paths and its only output goes to its OWN evidence file.
  * Its output is never labeled Farouk's result and never enters STRICT_FOLLOWER.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
SMART_ENTRY_LEDGER = os.path.join(HERE, "smart_entry_experimental_v0_1.jsonl")
ENABLED = False          # hard constant; see module docstring

FUTURE_INPUTS = ("order_block", "fair_value_gap", "mitigation_point", "liquidity_sweep",
                 "choch", "asia_high_low", "htf_structure", "indicator_grade", "session_context")


class SmartEntryDisabled(Exception):
    pass


def propose(candidate_inputs: dict) -> dict:
    """Future signature: candidate zone inputs -> experimental entry suggestion.
    DISABLED: always raises; nothing is computed, nothing is written."""
    raise SmartEntryDisabled(
        "ORANGE_SMART_ENTRY is disabled by design; activation requires a ratified "
        "constitution revision. STRICT_FOLLOWER is never affected by this module.")


def record_observation_only(note: str) -> None:
    """The ONLY permitted write: an observation note to the experimental ledger."""
    with open(SMART_ENTRY_LEDGER, "a", encoding="utf-8") as fh:
        fh.write(json.dumps({"at_utc": datetime.now(timezone.utc).isoformat(),
                             "note": note, "experimental": True,
                             "not_farouk_result": True, "strict_lane_untouched": True}) + "\n")
