"""
Deterministic initialiser for the two empty MPK canonical databases.

Creates mpk/data/mpk_registry_v1.db and mpk/data/mpk_campaigns_v1.db with the full
append-only schema and ZERO business rows (only the schema-control mpk_schema_meta row).
Idempotent: re-running creates nothing new and inserts no business data.

Run: python init_db.py
"""
from __future__ import annotations
import os

import sys as _sys
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in _sys.path:
    _sys.path.insert(0, _HERE)
from registry_db import RegistryDB
from campaigns_db import CampaignsDB

DATA_DIR = os.path.join(_HERE, "data")
REGISTRY_DB_PATH = os.path.join(DATA_DIR, "mpk_registry_v1.db")
CAMPAIGNS_DB_PATH = os.path.join(DATA_DIR, "mpk_campaigns_v1.db")


def initialise(applied_at_utc=None):
    """Create (or no-op open) both canonical DBs and return a report dict."""
    reg = RegistryDB(REGISTRY_DB_PATH, applied_at_utc=applied_at_utc)
    cam = CampaignsDB(CAMPAIGNS_DB_PATH, applied_at_utc=applied_at_utc)
    report = {
        "registry": {
            "path": REGISTRY_DB_PATH,
            "tables": reg.table_names(),
            "triggers": reg.trigger_names(),
            "business_counts": reg.business_counts(),
            "schema_meta": reg.schema_meta_rows(),
            "schema_fingerprint": reg.schema_fingerprint(),
        },
        "campaigns": {
            "path": CAMPAIGNS_DB_PATH,
            "tables": cam.table_names(),
            "triggers": cam.trigger_names(),
            "business_counts": cam.business_counts(),
            "schema_meta": cam.schema_meta_rows(),
            "schema_fingerprint": cam.schema_fingerprint(),
        },
    }
    reg.close()
    cam.close()
    return report


if __name__ == "__main__":
    import json
    rep = initialise()
    print(json.dumps(rep, indent=2, sort_keys=True))
    # assert empty of business data
    allcounts = {**{f"registry.{k}": v for k, v in rep["registry"]["business_counts"].items()},
                 **{f"campaigns.{k}": v for k, v in rep["campaigns"]["business_counts"].items()}}
    bad = {k: v for k, v in allcounts.items() if v != 0}
    print("\nBUSINESS ROW COUNTS:", allcounts)
    print("ALL ZERO:", not bad if True else bad)
