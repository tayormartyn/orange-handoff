"""Shared fixtures for alpha_intake adapter tests. Deterministic; no side effects."""
from __future__ import annotations
import copy
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from campaign_extractor.alpha_intake import qst_adapter as A  # noqa: E402

NOW = A._iso_to_ms("2026-07-04T09:01:00Z")

QUOTE_CTX = {
    "quote": {"bid": 4124.0, "ask": 4124.2, "ts_ms": NOW - 2000},
    "quote_path": [{"bid": 4125.0, "ask": 4125.2, "ts_ms": NOW - 40000},
                   {"bid": 4124.0, "ask": 4124.2, "ts_ms": NOW - 2000}],
    "quote_health_state": "QUOTES_ACTIVE",
}

_BASE = {
    "schemaVersion": "1.0.0",
    "signalId": "11111111-1111-4111-8111-111111111111",
    "idempotencyKey": "idem-abc-123456",
    "origin": {"kind": "AUTONOMOUS_ALPHA", "moduleId": "farouk-alpha@0.1.0"},
    "instrument": "XAUUSD",
    "direction": "LONG",
    "setupFamily": "BREAK_AND_RETEST",
    "observedAt": "2026-07-04T09:00:00Z",
    "effectiveMarketTime": "2026-07-04T09:00:05Z",
    "expiresAt": "2026-07-04T09:05:00Z",
    "campaignKey": "camp-1",
    "entry": {"entryType": "LIMIT_IN_ZONE", "zoneLow": "4116.00", "zoneHigh": "4118.00", "maxChasePrice": "4120.00"},
    "invalidationPrice": "4110.00",
    "objectives": [{"label": "prior high", "price": "4130.00"}],
    "triggerConfirmed": True,
    "marketSnapshotRef": "snap-1",
    "featureSnapshotRef": "feat-1",
    "evidenceQuality": {"tier": "TICK_VERIFIED", "confidence": 0.8, "verifiedPrecedentCount": 3},
    "decisionTrace": {"steps": []},
    "reproducibility": {"moduleVersion": "0.1.0", "configHash": "h", "featureSetVersion": "f",
                        "codeCommit": "c", "seed": 0},
    "generatedInMode": "SHADOW",
}


def valid_proposal(**overrides):
    p = copy.deepcopy(_BASE)
    p.update(overrides)
    return p
