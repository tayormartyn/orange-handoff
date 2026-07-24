"""Provider-verification gate + read-only cohort endpoint tests for the console."""
from __future__ import annotations
import hashlib
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_CON = os.path.join(_ROOT, "campaign_extractor", "paper_loop", "console")
for p in (_ROOT, os.path.join(_ROOT, "campaign_extractor"),
          os.path.join(_ROOT, "campaign_extractor", "q4_align"),
          os.path.join(_ROOT, "campaign_extractor", "paper_loop"),
          os.path.join(_ROOT, "campaign_extractor", "vision_v1"), _CON):
    if p not in sys.path:
        sys.path.insert(0, p)
os.chdir(_ROOT)

import server as C
import image_confirm
import farouk_cohort_monitor as M

MANIFEST = {"original_image_sha256": "a" * 64, "imported_media_id": "media-x"}


def _farouk(**over):
    a = {"intake_class": "SIGNAL", "semantic_class": "SIGNAL_ANNOUNCEMENT", "instrument": "XAUUSD",
         "direction": "BUY", "entry_low": "4000.00", "entry_high": "4000.20",
         "provider": "seascalperfarouk", "source_evidence_references": ["https://t.me/c/123/45"],
         "source_provenance": "MESSAGE_ID_OR_LINK", "source_attested": True,
         "reviewer_ref": "martyn", "explicit_confirmation": True}
    a.update(over)
    return a


def _rec(intake_id, **over):
    return image_confirm.build_review_record(intake_id, MANIFEST, _farouk(**over))


def _bundle(rec, has_obs=True, dup=False):
    return {"intake_id": rec["intake_id"], "review": rec,
            "manifest": {"intake_id": rec["intake_id"], "screenshot_imported_at": "2026-07-02T07:00:00Z",
                         "duplicate": dup},
            "paper_obs": ({"observation_id": "po", "status": "PAPER_READY", "reason_code": None,
                           "decision_timestamp": "t", "persisted_utc": "t"} if has_obs else None),
            "bridge_obs": ({"paper_observation_id": "po", "intake_id": rec["intake_id"],
                            "human_confirmed_actionable_result": {"reason": None},
                            "import_latency_s": 1, "actionable_latency_s": 2} if has_obs else None)}


# ---- provider gate ----
def test_provider_name_alone_unverified():
    rec = _rec("i1", source_evidence_references=[], source_provenance=None, source_attested=False)
    assert rec["provider"]["verification_state"] == "PROVIDER_UNVERIFIED"


def test_evidence_without_attestation_unverified():
    assert _rec("i1", source_attested=False)["provider"]["verification_state"] == "PROVIDER_UNVERIFIED"


def test_evidence_without_provenance_unverified():
    assert _rec("i1", source_provenance=None)["provider"]["verification_state"] == "PROVIDER_UNVERIFIED"


def test_evidence_and_attestation_verifies():
    rec = _rec("i1")
    assert rec["provider"]["verification_state"] == "PROVIDER_VERIFIED"
    assert rec["provider"]["source_provenance"] == "MESSAGE_ID_OR_LINK"
    assert rec["provider"]["source_attested"] is True


def test_uncertain_source_unverified():
    # a source string but no recognised provenance and no attestation -> UNVERIFIED
    assert _rec("i1", source_provenance="", source_attested=False
                )["provider"]["verification_state"] == "PROVIDER_UNVERIFIED"


# ---- console _answers wiring passes the new fields ----
def test_console_answers_passes_verification_fields():
    a = C._answers({"intake_class": "SIGNAL", "instrument": "XAUUSD", "provider": "seascalperfarouk",
                    "source_evidence": "https://t.me/c/1/2", "source_provenance": "MESSAGE_ID_OR_LINK",
                    "source_attested": True})
    assert a["source_provenance"] == "MESSAGE_ID_OR_LINK" and a["source_attested"] is True


# ---- cohort contribution ----
def test_unverified_farouk_contributes_zero():
    r = M.assess([_bundle(_rec("i1", source_attested=False))])
    assert r["complete"] == 0 and r["counts"]["provider_unverified"] == 1


def test_verified_farouk_with_obs_contributes_one():
    assert M.assess([_bundle(_rec("iF"))])["complete"] == 1


def test_five_verified_farouk_complete():
    r = M.assess([_bundle(_rec(f"iF{i}")) for i in range(5)])
    assert r["complete"] == 5 and r["headline"] == "COHORT ONE: 5 / 5 COMPLETE"


# ---- read-only endpoint ----
def _watch():
    ws = ["data/signal_archive.db", "data/shadow.db", "data/ctrader_quotes_v1.db"]
    return {p: (hashlib.sha256(open(p, "rb").read()).hexdigest() if os.path.exists(p) else None) for p in ws}


def test_cohort_endpoint_readonly_and_shape():
    before = _watch()
    res = C.do_cohort()
    after = _watch()
    assert set(res) >= {"headline", "complete", "target", "counts"}
    assert res["target"] == 5 and before == after            # read-only


def test_no_order_route_in_console():
    from broker_readonly.source_scan import scan_no_order_code
    assert scan_no_order_code([_CON]) == []
    cfg = open(os.path.join(_ROOT, "config.py"), encoding="utf-8").read()
    assert "EXECUTION_ENABLED = False" in cfg
