"""Schema validation: strict shape, forbidden execution/account/route fields, unsupported instrument."""
from __future__ import annotations
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _fixtures import valid_proposal, NOW, QUOTE_CTX
from campaign_extractor.alpha_intake import qst_adapter as A, schemas as S


def test_clean_proposal_validates():
    assert S.validate_proposal(valid_proposal()) is not None


def test_unknown_top_level_rejected():
    try:
        S.validate_proposal(valid_proposal(surpriseField=1))
        assert False
    except S.SchemaError as e:
        assert e.code == "UNKNOWN_FIELD"


def test_forbidden_execution_and_account_fields_rejected():
    for k in ("lotSize", "positionSize", "riskPercent", "accountId", "orderId", "executionPermission",
              "canExecute", "authorised", "brokerCredentials", "apiKey"):
        p = valid_proposal(); p[k] = "x"
        try:
            S.validate_proposal(p); assert False, k
        except S.SchemaError as e:
            assert e.code in ("FORBIDDEN_FIELD", "UNKNOWN_FIELD")
        # and the adapter rejects at intake
        assert A.evaluate(p, now_ms=NOW)["ack"]["accepted"] is False


def test_forbidden_broker_route_field_rejected():
    p = valid_proposal(); p["brokerRoute"] = "demo"
    assert A.evaluate(p, now_ms=NOW)["ack"]["reasonCode"] in ("FORBIDDEN_FIELD", "MALFORMED")
    p2 = valid_proposal(); p2["route"] = "x"
    assert A.evaluate(p2, now_ms=NOW)["ack"]["accepted"] is False


def test_nested_forbidden_field_rejected():
    p = valid_proposal(); p["entry"] = {**p["entry"], "lotSize": 0.1}
    r = A.evaluate(p, now_ms=NOW)
    assert r["ack"]["accepted"] is False and r["ack"]["reasonCode"] == "FORBIDDEN_FIELD"


def test_unsupported_instrument_rejected():
    r = A.evaluate(valid_proposal(instrument="BTCUSD"), now_ms=NOW)
    assert r["ack"]["accepted"] is False and r["ack"]["reasonCode"] == "UNSUPPORTED_INSTRUMENT"


def test_expires_not_after_observed_rejected():
    r = A.evaluate(valid_proposal(observedAt="2026-07-04T09:05:00Z", expiresAt="2026-07-04T09:05:00Z"), now_ms=NOW)
    assert r["ack"]["accepted"] is False and r["ack"]["reasonCode"] == "EXPIRES_NOT_AFTER_OBSERVED"


def test_bad_schema_version_rejected():
    r = A.evaluate(valid_proposal(schemaVersion="2.0.0"), now_ms=NOW)
    assert r["ack"]["reasonCode"] == "UNSUPPORTED_SCHEMA_VERSION"
