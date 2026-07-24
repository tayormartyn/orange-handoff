"""Part 18 — F001/F002 SCHEMA BACKFILL (RESEARCH-ONLY, NOT_PROSPECTIVE).

Freezes the router hierarchy for the two frozen campaigns SOLELY to validate schemas and causal
mechanics. Every record is marked SCHEMA_BACKFILL_NOT_PROSPECTIVE and written to a SEPARATE backfill
ledger. It does NOT fit weights, does NOT tune against published zones, does NOT use outcomes in
pre-signal classification, and does NOT count toward forward router accuracy. F001/F002 firewalls are
already CLOSED; this is a mechanical schema exercise off the live path.
"""
from __future__ import annotations

import csv
import io
import os
import sys
from decimal import Decimal as D
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import strategy_router as R                                        # noqa: E402
import evidence_schema as es                                      # noqa: E402

PRICE = os.path.join(HERE, "..", "..", "..", "price_data",
                     "XAUUSD_1M_PEPPERSTONE_2026-07-08_to_2026-07-15_CANONICAL.csv")

CAMPAIGNS = [
    {"setup_id": "XAU-F001-20260714", "direction": "LONG", "zone_low": "4007", "zone_high": "4019",
     "sl": "3985", "source": "2026-07-14T08:38:06"},
    {"setup_id": "XAU-F002-20260714", "direction": "SHORT", "zone_low": "4084", "zone_high": "4094",
     "sl": "4144", "source": "2026-07-14T13:26:21"},
]


def _load(path):
    out = []
    for r in csv.reader(open(path, encoding="utf-8-sig")):
        if not r or r[0] in ("time", ""):
            continue
        out.append((int(r[0]), D(r[1]), D(r[2]), D(r[3]), D(r[4])))
    out.sort()
    return out


def main():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    bars = _load(PRICE)
    for c in CAMPAIGNS:
        dts = int(datetime.fromisoformat(c["source"]).replace(tzinfo=timezone.utc).timestamp())
        rec = R.freeze_router(setup_id=c["setup_id"], direction=c["direction"], zone_low=c["zone_low"],
                              zone_high=c["zone_high"], sl=c["sl"], decision_ts=dts, bars=bars,
                              objective_lane="A_FOLLOWER", record_class="SCHEMA_BACKFILL_NOT_PROSPECTIVE",
                              campaign_provenance={"setup_id": c["setup_id"], "note": "F001/F002 frozen backfill"})
        assert rec["backfill_marker"] == "SCHEMA_BACKFILL_NOT_PROSPECTIVE"
        assert rec["eligible_for_prospective_evidence"] is False
        es.append_once(R.BACKFILL_LEDGER, rec)
        h = rec["hierarchy"]
        print(f"{c['setup_id']} {c['direction']}: sess={h['6_session_model']['session_utc']} "
              f"regime={[x.get('state') for x in h['5_market_regime']['candidate_values']]} "
              f"struct={h['9_structural_confirmation']['selected_value_if_predetermined']} "
              f"otePairs={rec['supplemental_contracts']['ote_shadow']['total_pairs_enumerated']} "
              f"vp={rec['supplemental_contracts']['volume_profile']['status']} "
              f"marker={rec['backfill_marker']}")
    print(f"\nwritten -> {R.BACKFILL_LEDGER}")


if __name__ == "__main__":
    main()
