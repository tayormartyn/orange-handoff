"""
shadow_config.py — SHADOW MODE Phase 1b, the FROZEN assumption set (Shadow Config v0).

Every number that could tilt the answer lives here, versioned and content-hashed, so
a result can always be traced back to the exact assumptions that produced it. The
config is FROZEN: you bump the version to change it, you do not edit v0 in place.

The single most important honesty rule this encodes: all 28 historical signals are
T-C (posted-time only, Phase 1a), so Phase 1b runs DELAY SCENARIOS and labels every
historical result RECONSTRUCTED_DELAY_SCENARIO — never one "exact executable" number.

PAPER mode. No execution. Nothing here reads a broker.
"""

import hashlib
import json
from decimal import Decimal

import config as base_config

CONFIG_VERSION = "shadow-v0"

# ----------------------------------------------------------------------------
# Provenance / freeze metadata
# ----------------------------------------------------------------------------
# The date the assumption set + the no-chase candidate thresholds were FROZEN.
# No-chase thresholds must be selected PROSPECTIVELY (on new signals), never tuned
# to flatter this 28-signal sample, so we stamp when they were fixed and the data
# cut-off they may NOT be optimised against.
RULE_SELECTION_DATE = "2026-06-28"
DATA_CUTOFF = "2026-06-28"      # no-chase rules may NOT be chosen using data <= this

# ----------------------------------------------------------------------------
# Delay scenarios (the historical answer is a RANGE, not a point)
# ----------------------------------------------------------------------------
# Seconds after the provider's POSTED time at which a follower might realistically
# have acted. Because the timestamp is posted-only (T-C), each is a scenario.
DELAY_SCENARIOS_SEC = [0, 2, 5, 10, 30]

# ----------------------------------------------------------------------------
# Slippage grid ($/side) — slippage only ever WORSENS a fill, never improves it
# ----------------------------------------------------------------------------
# Crossed with the delay scenarios for Ledger C. The middle value is the repo's
# existing single-source-of-truth gold slippage, so v0 stays consistent with the
# sizing engine; the outer values show sensitivity to the assumption.
_REPO_GOLD_SLIP = Decimal(str(base_config.ASSET_CLASSES["GOLD"]["slippage"]))   # "0.30"
SLIPPAGE_GRID_USD = [Decimal("0.10"), _REPO_GOLD_SLIP, Decimal("0.60")]

# ----------------------------------------------------------------------------
# Quote / fill discipline
# ----------------------------------------------------------------------------
# If the first usable tick at/after the effective execution time is further away
# than this, we record NO_EXECUTABLE_QUOTE rather than guess a fill. 5s mirrors the
# Phase 1a P-B/P-C boundary (a fill quoted >5s from the intended instant is not a
# fill we will pretend is real).
QUOTE_GAP_LIMIT_MS = 5000

# Phase 1a ticks already carry bid AND ask. Spread is therefore taken FROM the tick
# (enter ask / exit bid etc.) and must NOT be added a second time on top.
SPREAD_FROM_TICK = True

# Path replay: when stop and target could both have resolved inside one unobserved
# window (a 5s candle, or a tick gap that spans both levels), the order is unknown.
# The PRIMARY aggregate uses the PESSIMISTIC bound; the report always shows both.
PRIMARY_PATH_BOUND = "pessimistic"      # "pessimistic" | "optimistic"

# How far past the signal we replay the price path when looking for stop/target,
# capped additionally by the next same-asset signal (the re-entry boundary).
MAX_REPLAY_HORIZON_HOURS = 72

# ----------------------------------------------------------------------------
# No-chase candidate thresholds (LOGGED challengers — NOT decision-making yet)
# ----------------------------------------------------------------------------
# Adverse entry-deterioration thresholds (in R) we want to TEST prospectively. They
# are logged against every signal as challengers; NONE is selected as "the rule"
# using this sample. Winner selection is deferred to new signals only.
NOCHASE_CANDIDATE_THRESHOLDS_R = [Decimal("0.05"), Decimal("0.10"),
                                  Decimal("0.15"), Decimal("0.20")]

# ----------------------------------------------------------------------------
# Leakage decomposition — FIXED, documented order
# ----------------------------------------------------------------------------
# Each step adds one source of friction; the drop in R it causes is that step's
# attributed leakage. Order is fixed so the decomposition is reproducible.
LEAKAGE_DECOMPOSITION_ORDER = [
    "reference_entry_no_friction",   # Ledger B baseline (mid, no delay, no spread)
    "independent_bid_ask_no_delay",  # switch mid -> executable bid/ask, still no delay
    "receipt_delay",                 # + the delay scenario (posted -> acted)
    "parser_delay",                  # + parser processing (modelled; 0 for historical T-C)
    "approval_delay",                # + human approval pause (modelled; 0 for historical)
    "slippage",                      # + adverse slippage
    "management_delay",              # + management-exit timing friction
]

# Modelled processing delays (seconds) folded into the decomposition. For HISTORICAL
# T-C signals these are 0 (we have no receipt/parse/approval stamps); they exist so
# the live path (T-A/T-B) can populate them without changing the schema.
MODELLED_PARSER_DELAY_SEC = 0
MODELLED_APPROVAL_DELAY_SEC = 0

# ----------------------------------------------------------------------------
# Result provenance labels (kept strictly separate)
# ----------------------------------------------------------------------------
RECONSTRUCTED_DELAY_SCENARIO = "RECONSTRUCTED_DELAY_SCENARIO"   # T-C historical
OBSERVED_RECEIPT_TIME = "OBSERVED_RECEIPT_TIME"                 # future T-A/T-B


def as_dict():
    """The full frozen assumption set as plain JSON-able data."""
    return {
        "config_version": CONFIG_VERSION,
        "rule_selection_date": RULE_SELECTION_DATE,
        "data_cutoff": DATA_CUTOFF,
        "delay_scenarios_sec": DELAY_SCENARIOS_SEC,
        "slippage_grid_usd": [str(s) for s in SLIPPAGE_GRID_USD],
        "quote_gap_limit_ms": QUOTE_GAP_LIMIT_MS,
        "spread_from_tick": SPREAD_FROM_TICK,
        "primary_path_bound": PRIMARY_PATH_BOUND,
        "max_replay_horizon_hours": MAX_REPLAY_HORIZON_HOURS,
        "nochase_candidate_thresholds_r": [str(t) for t in NOCHASE_CANDIDATE_THRESHOLDS_R],
        "leakage_decomposition_order": LEAKAGE_DECOMPOSITION_ORDER,
        "modelled_parser_delay_sec": MODELLED_PARSER_DELAY_SEC,
        "modelled_approval_delay_sec": MODELLED_APPROVAL_DELAY_SEC,
    }


def config_hash():
    """Deterministic SHA-256 of the frozen assumption set (goes on every run/result
    so any output is traceable to the exact config that produced it)."""
    blob = json.dumps(as_dict(), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


if __name__ == "__main__":
    print(json.dumps(as_dict(), indent=2))
    print("config_hash:", config_hash())
