"""Idempotency + expiry: expired proposals rejected; a duplicate idempotency key yields the correct
DUPLICATE acknowledgement (accepted, minimal shape, no re-evaluation)."""
from __future__ import annotations
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _fixtures import valid_proposal, NOW, QUOTE_CTX
from campaign_extractor.alpha_intake import qst_adapter as A


def test_expired_proposal_rejected():
    # now (09:01) is AFTER an expiry of 09:00:30
    r = A.evaluate(valid_proposal(observedAt="2026-07-04T08:59:00Z", expiresAt="2026-07-04T09:00:30Z"), now_ms=NOW)
    assert r["ack"]["accepted"] is False and r["ack"]["reasonCode"] == "EXPIRED"


def test_not_yet_expired_accepted():
    r = A.evaluate(valid_proposal(), now_ms=NOW)          # expiry 09:05, now 09:01
    assert r["ack"]["accepted"] is True and r["ack"]["reasonCode"] == "ACCEPTED"


def test_duplicate_idempotency_key_acknowledged():
    seen = set()
    first = A.evaluate(valid_proposal(), now_ms=NOW, quote_ctx=QUOTE_CTX, seen_idempotency_keys=seen)
    assert first["ack"]["reasonCode"] == "ACCEPTED" and "idem-abc-123456" in seen
    second = A.evaluate(valid_proposal(), now_ms=NOW, quote_ctx=QUOTE_CTX, seen_idempotency_keys=seen)
    assert second["ack"] == {"accepted": True, "reasonCode": "DUPLICATE", "idempotencyKey": "idem-abc-123456"}
    assert second["shadow_qualification_record"]["routing_mode"] == "NOT_RE_EVALUATED_DUPLICATE"


def test_ack_shape_is_minimal():
    r = A.evaluate(valid_proposal(), now_ms=NOW)
    assert set(r["ack"].keys()) == {"accepted", "reasonCode", "idempotencyKey"}
    # NEVER any execution/sizing/route/account data in the ack
    for forbidden in ("orderId", "fillPrice", "filledLots", "positionSize", "accountId", "route",
                      "executed", "executionPermission", "riskPercent", "lotSize"):
        assert forbidden not in r["ack"]
