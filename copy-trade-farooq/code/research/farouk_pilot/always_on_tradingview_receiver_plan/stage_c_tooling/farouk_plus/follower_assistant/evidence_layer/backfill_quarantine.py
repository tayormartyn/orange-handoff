"""Deterministic NON_ANALYTICAL_BACKFILL quarantine.

The append-only evidence records written for F001/F002 and the placeholder-id historical entries
are preserved (never deleted/rewritten) but are permanently EXCLUDED from analytics: campaign
#3–#15 counts, expectancy, hypothesis agreement, enhanced-entry comparisons, profitability. Any
analytics consumer must gate on `is_analytical(setup_id)`.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
MANIFEST = os.path.join(HERE, "backfill_quarantine_v0_1.json")

# explicit, frozen exclusion set + rule
NON_ANALYTICAL_IDS = {"XAU-F001-20260714", "XAU-F002-20260714"}
PLACEHOLDER_PREFIX = "XAU-F???"
CAMPAIGN3_MIN_SETUP_NUM = 3          # analytics scope begins at F003


def is_analytical(setup_id: str) -> bool:
    """True only for genuine campaign-#3-onward setups. Deterministic, no I/O."""
    if not setup_id or not isinstance(setup_id, str):
        return False
    if setup_id in NON_ANALYTICAL_IDS:
        return False
    if setup_id.startswith(PLACEHOLDER_PREFIX):
        return False
    # parse the F### index; anything below F003 is pre-layer backfill
    try:
        num = int(setup_id.split("-")[1][1:])
        return num >= CAMPAIGN3_MIN_SETUP_NUM
    except (IndexError, ValueError):
        return False


def classification(setup_id: str) -> str:
    return "ANALYTICAL_CAMPAIGN" if is_analytical(setup_id) else "NON_ANALYTICAL_BACKFILL"


def analytical_only(setup_ids):
    return [s for s in setup_ids if is_analytical(s)]


def write_manifest():
    """Append-only manifest documenting the quarantine rule (idempotent write)."""
    rec = {
        "manifest": "backfill_quarantine_v0_1",
        "written_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "rule": "is_analytical: setup_id not in explicit set, not placeholder, and F-index >= 3",
        "non_analytical_explicit_ids": sorted(NON_ANALYTICAL_IDS),
        "placeholder_prefix": PLACEHOLDER_PREFIX,
        "campaign3_min_setup_num": CAMPAIGN3_MIN_SETUP_NUM,
        "excluded_from": ["campaign_3_to_15_counts", "expectancy", "hypothesis_agreement",
                          "enhanced_entry_comparisons", "profitability_reports"],
        "append_only_note": "quarantined records are preserved; never deleted or rewritten",
    }
    with open(MANIFEST, "w", encoding="utf-8") as fh:
        json.dump(rec, fh, indent=1)
    return rec
