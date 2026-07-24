"""
Signal-screenshot profile/adapter for the image bridge. Adds bridge-level semantic classes and
signal regions ON TOP of the unchanged Vision V1.1 core (it reuses V1.1 media/crop/candidate/
review/firewall interfaces — it does not modify them). Only a SIGNAL_ANNOUNCEMENT (or a clearly
isolated signal-announcement block inside MIXED) may propose a new signal.
"""
from __future__ import annotations

SEMANTIC_CLASSES = ("SIGNAL_ANNOUNCEMENT", "POSITION_TICKET", "POSITION_MANAGEMENT",
                    "RESULT_CLAIM", "ANALYSIS_ONLY", "MIXED", "UNKNOWN")
# classes that may NEVER create a new signal
NON_SIGNAL_CLASSES = ("POSITION_TICKET", "POSITION_MANAGEMENT", "RESULT_CLAIM",
                      "ANALYSIS_ONLY", "UNKNOWN")

SIGNAL_REGIONS = ("SIGNAL_BLOCK", "SIGNAL_INSTRUMENT", "SIGNAL_DIRECTION", "SIGNAL_ENTRY_RANGE",
                  "SIGNAL_STOP", "SIGNAL_TARGETS", "SIGNAL_RISK_LABEL", "SIGNAL_SIZE_COMMENT",
                  "SOURCE_TIMESTAMP", "PROVIDER_CONTEXT")

# non-numeric commentary fields — must NEVER be turned into numbers
NON_NUMERIC_FIELDS = ("SIGNAL_RISK_LABEL", "SIGNAL_SIZE_COMMENT")

PROVIDER_POST_PROVENANCE = ("DISCORD_MESSAGE_ID_OR_LINK", "VISIBLE_ABSOLUTE_TIMESTAMP",
                            "VISIBLE_TIME_HUMAN_DATE_CONFIRMED", "HUMAN_ATTESTED_AGAINST_ORIGINAL",
                            "UNVERIFIABLE")


def may_propose_signal(semantic_class, isolated_signal_block=False):
    """True only for SIGNAL_ANNOUNCEMENT, or an explicitly isolated signal block inside MIXED."""
    if semantic_class == "SIGNAL_ANNOUNCEMENT":
        return True
    if semantic_class == "MIXED" and isolated_signal_block:
        return True
    return False


def blocks_are_separated(blocks):
    """Multiple signal blocks must keep distinct signal_block_index and never share field crops."""
    idxs = [b.get("signal_block_index") for b in blocks]
    if len(idxs) != len(set(idxs)) or any(i is None for i in idxs):
        return False
    # no crop hash may appear in two different blocks
    seen = {}
    for b in blocks:
        for f in b.get("fields", []):
            h = f.get("crop_sha256")
            if h is None:
                continue
            if h in seen and seen[h] != b["signal_block_index"]:
                return False
            seen[h] = b["signal_block_index"]
    return True
