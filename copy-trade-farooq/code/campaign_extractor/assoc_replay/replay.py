"""
ASSOC-1R replay orchestrator. Builds the ephemeral XAUUSD campaign snapshot, classifies the
live messages deterministically, and runs them through the verified ASSOC-1 engine. Writes
decisions ONLY to the isolated association_real_replay_v1.db. Mutates nothing.
"""
from __future__ import annotations
import os

import sys as _sys
_HERE = os.path.dirname(os.path.abspath(__file__))
_ASSOC = os.path.join(os.path.dirname(_HERE), "assoc")
for p in (_HERE, _ASSOC):
    if p not in _sys.path:
        _sys.path.insert(0, p)
from model import CampaignSnapshot, OPEN
from engine import associate
from decisions_db import AssociationDecisionsDB
from candidates import classify, build_candidate, FAROUK, CHANNEL
import provenance

DATA_DIR = os.path.join(_HERE, "data")
REPLAY_DB_PATH = os.path.join(DATA_DIR, "association_real_replay_v1.db")

# Ephemeral, isolated candidate-campaign snapshot. NOT a canonical campaign; never inserted
# into the campaigns DB. venue is implicitly NOT_ROUTED and broker confirmation NONE (ASSOC-1
# has no venue/broker concept at all).
EPHEMERAL_GOLD = CampaignSnapshot(
    campaign_uid="ephemeral_farouk_xauusd_20260630",
    provider_id=FAROUK, lifecycle_status=OPEN,
    canonical_underlying_id="underlying_gold",
    canonical_instrument_id="instrument_xauusd_spot_reference",
    direction="SHORT", origin_channel_id=CHANNEL,
    provider_campaign_reference=None, linked_message_uids=("45331",),
    opened_at="2026-06-30T14:25:23+00:00")


def build_decisions(rows, *, tracking_status="TRACKED_PROVIDER", approved=True, campaigns=None):
    """Return [{message_id, candidate_type, intent, metadata, decision}] for each row."""
    campaigns = campaigns if campaigns is not None else [EPHEMERAL_GOLD]
    results = []
    for row in rows:
        ctype, intent, meta = classify(row)
        decision = None
        if ctype == "ORIGINAL_SIGNAL":
            pass  # campaign origin, not a management candidate
        elif ctype == "FOLLOWER":
            cand = build_candidate(row, "FOLLOWER_QUESTION", tracking_status="DENIED",
                                   source_identity_approved=False, provider_id="unknown_follower")
            decision = associate(cand, campaigns)
        elif ctype == "MANAGEMENT":
            cand = build_candidate(row, intent, tracking_status=tracking_status,
                                   source_identity_approved=approved)
            decision = associate(cand, campaigns)
        else:  # MILESTONE_CLAIM / ANALYSIS_ONLY / COMMENTARY / OTHER_PROVIDER -> non-management
            cand = build_candidate(row, ctype, tracking_status=tracking_status,
                                   source_identity_approved=approved)
            decision = associate(cand, campaigns)
        results.append({"message_id": row["message_id"], "candidate_type": ctype,
                        "intent": intent, "metadata": meta, "decision": decision})
    return results


def census(results):
    tally, rules = {}, {}
    for r in results:
        d = r["decision"]
        if d is None:
            tally["ORIGINAL_SIGNAL"] = tally.get("ORIGINAL_SIGNAL", 0) + 1
            continue
        tally[d["association_status"]] = tally.get(d["association_status"], 0) + 1
        rules[d["rule_fired"]] = rules.get(d["rule_fired"], 0) + 1
    return tally, rules


def run(write_db=True):
    rows = provenance.load_live_rows()
    results = build_decisions(rows)
    if write_db:
        db = AssociationDecisionsDB(REPLAY_DB_PATH)
        for r in results:
            if r["decision"] is not None:
                db.append(r["decision"], created_at="2026-06-30T15:00:00+00:00")
        db.close()
    tally, rules = census(results)
    return {"rows": len(rows), "results": results, "census": tally, "rules": rules,
            "manual_fixtures": provenance.MANUAL_SCREENSHOT_FIXTURES}
