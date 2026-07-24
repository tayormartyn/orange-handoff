"""Mapping: LONG->BUY, SHORT->SELL, XAUUSD->XAUUSD, entry-type vocabulary, invalidation->structural
stop (NOT risk-sized), and a clean autonomous shadow proposal accepted for evaluation."""
from __future__ import annotations
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _fixtures import valid_proposal, NOW, QUOTE_CTX
from campaign_extractor.alpha_intake import qst_adapter as A


def test_clean_autonomous_shadow_proposal_accepted():
    r = A.evaluate(valid_proposal(), now_ms=NOW, quote_ctx=QUOTE_CTX)
    assert r["ack"] == {"accepted": True, "reasonCode": "ACCEPTED", "idempotencyKey": "idem-abc-123456"}
    sh = r["shadow_qualification_record"]
    assert sh["shadow_only"] is True and sh["executable_campaign"] is False
    assert sh["routing_mode"] in ("PRE_TOUCH_PASSIVE_LADDER", "INSIDE_ZONE_QUALIFIED_STRIKE_TRAP",
                                  "INSIDE_ZONE_BLOCKED", "ZONE_CONSUMED")


def test_long_maps_to_buy():
    r = A.evaluate(valid_proposal(direction="LONG"), now_ms=NOW)
    assert r["audit"]["mapping"]["direction_qst"] == "BUY"


def test_short_maps_to_sell():
    r = A.evaluate(valid_proposal(direction="SHORT"), now_ms=NOW)
    assert r["audit"]["mapping"]["direction_qst"] == "SELL"


def test_entry_type_vocabulary_mapped():
    assert A.evaluate(valid_proposal(entry={"entryType": "LIMIT_IN_ZONE", "zoneLow": "4116.00", "zoneHigh": "4118.00", "maxChasePrice": "4120.00"}), now_ms=NOW)["audit"]["mapping"]["entry_route_hint"] == "PASSIVE_LIMIT_IN_ZONE"
    assert A.evaluate(valid_proposal(entry={"entryType": "MARKET_ON_TRIGGER", "zoneLow": "4116.00", "zoneHigh": "4118.00", "maxChasePrice": "4120.00"}), now_ms=NOW)["audit"]["mapping"]["entry_route_hint"] == "INSIDE_ZONE_MARKET_RANGE_STRIKE"


def test_stop_on_break_flagged_not_silently_mapped():
    r = A.evaluate(valid_proposal(entry={"entryType": "STOP_ON_BREAK", "zoneLow": "4116.00", "zoneHigh": "4118.00", "maxChasePrice": "4120.00"}), now_ms=NOW)
    assert r["audit"]["mapping"]["entry_route_hint"] is None
    assert any("ENTRY_TYPE_NO_QST_EQUIVALENT" in w for w in r["audit"]["mapping_warnings"])


def test_invalidation_mapped_as_structural_not_risk_sized():
    r = A.evaluate(valid_proposal(), now_ms=NOW)
    m = r["audit"]["mapping"]
    assert m["structural_stop_from_invalidation"] == 4110.0
    assert m["structural_stop_is_risk_sized"] is False       # semantic mismatch reported, not invented
    assert any("risk_policy" in n for n in r["audit"]["semantic_notes"])


def test_pure_route_invoked_only_with_quote_context():
    without = A.evaluate(valid_proposal(), now_ms=NOW)
    assert without["shadow_qualification_record"]["routing_mode"] == "NOT_EVALUATED_NO_QUOTE_CONTEXT"
    with_ctx = A.evaluate(valid_proposal(), now_ms=NOW, quote_ctx=QUOTE_CTX)
    assert with_ctx["shadow_qualification_record"]["routing_mode"] != "NOT_EVALUATED_NO_QUOTE_CONTEXT"
