"""Origin policy: autonomous-only, RESEARCH/REPLAY/SHADOW allowed, PAPER/DEMO/LIVE rejected, and any
sea-scalper-farouk / external-provider route fails closed. Autonomous origin has no route/authority."""
from __future__ import annotations
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _fixtures import valid_proposal, NOW
from campaign_extractor.alpha_intake import origin_policy as OP, qst_adapter as A


def test_allowed_modes_pass():
    for m in ("RESEARCH", "REPLAY", "SHADOW"):
        ok, codes = OP.check_origin({"kind": "AUTONOMOUS_ALPHA", "moduleId": "farouk-alpha@0.1.0"}, m)
        assert ok and not codes


def test_paper_demo_live_rejected():
    for m in ("PAPER", "DEMO", "LIVE"):
        r = A.evaluate(valid_proposal(generatedInMode=m), now_ms=NOW)
        assert r["ack"]["accepted"] is False and r["ack"]["reasonCode"] == "UNSUPPORTED_MODE"


def test_non_autonomous_origin_rejected():
    r = A.evaluate(valid_proposal(origin={"kind": "EXTERNAL_PROVIDER", "moduleId": "x"}), now_ms=NOW)
    assert r["ack"]["accepted"] is False and r["ack"]["reasonCode"] == "ORIGIN_REJECTED"


def test_sea_scalper_farouk_impersonation_rejected():
    # moduleId referencing the external route
    r = A.evaluate(valid_proposal(origin={"kind": "AUTONOMOUS_ALPHA", "moduleId": "sea-scalper-farouk"}), now_ms=NOW)
    assert r["ack"]["accepted"] is False and r["ack"]["reasonCode"] == "EXTERNAL_PROVIDER_ROUTE_REJECTED"
    # explicit route field on origin
    r2 = A.evaluate(valid_proposal(origin={"kind": "AUTONOMOUS_ALPHA", "moduleId": "m", "sourceRoom": "sea-scalper-farouk"}), now_ms=NOW)
    assert r2["ack"]["accepted"] is False


def test_transport_id_impersonation_rejected():
    ok, codes = OP.check_origin({"kind": "AUTONOMOUS_ALPHA", "moduleId": "uses -1001937743421"}, "SHADOW")
    assert (not ok) and "EXTERNAL_PROVIDER_ROUTE_SPOOF" in codes


def test_autonomous_origin_has_no_route_or_authority():
    rec = OP.origin_record({"kind": "AUTONOMOUS_ALPHA", "moduleId": "farouk-alpha@0.1.0"}, "SHADOW")
    assert rec["provider_route"] is None and rec["broker_route"] is None
    assert rec["inherited_from_sea_scalper_farouk"] is False and rec["execution_authority"] is False
