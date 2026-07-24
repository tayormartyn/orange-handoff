"""
Extraction pipeline (Layer 1 only). Persists regions, field candidates (all accepted=NULL, review
pending), and image semantics to the CandidateDB. Creates ZERO campaign events / open legs /
accepted events — it has no code path to them.
"""
from __future__ import annotations


def _review_status(cand):
    dual = cand.get("dual_reading_state")
    alts = cand.get("alternative_readings") or []
    if dual in ("READERS_DISAGREE", "UNREADABLE") or len({str(a) for a in alts}) > 1:
        return "AMBIGUOUS_DIGITS"                       # -> accepted value stays NULL
    return "PENDING"                                    # numerics always await human review


def run_extraction(media_id, sha256, extractor, candidate_db):
    res = extractor.extract(media_id, sha256)
    for r in res["regions"]:
        candidate_db.insert_region(media_id=media_id, extractor_version=extractor.version, **r)
    n = 0
    for c in res["candidates"]:
        n += 1
        cfid = f"{media_id}:cand:{n}:{c['field_type']}"
        provider = c["evidence_domain"] == "PROVIDER_DISPLAYED"
        candidate_db.insert_candidate(
            candidate_field_id=cfid, media_id=media_id, region_id=c["region_id"],
            field_type=c["field_type"], raw_visible_text=c["raw_visible_text"],
            candidate_value_string=c["candidate_value_string"],
            accepted_normalised_value=None,             # NEVER set at extraction
            bbox=c.get("bbox"), crop_sha256=c.get("crop_sha256"),
            extractor_confidence=c.get("extractor_confidence"),
            alternative_readings=c.get("alternative_readings"),
            extraction_method_version=extractor.version,
            review_status=_review_status(c), evidence_domain=c["evidence_domain"],
            dual_reading_state=c.get("dual_reading_state"),
            # nothing produced by vision is ever outcome-eligible; provider P/L explicitly not
            eligible_for_shadow_outcome=0, eligible_for_demo_outcome=0,
            eligible_for_account_r=0, eligible_for_expectancy=0)
    candidate_db.insert_semantics(media_id=media_id, **res["semantics"])
    return {"regions": len(res["regions"]), "candidates": n,
            "semantics": res["semantics"]["classification"],
            "new_campaign_events": 0, "open_leg_events": 0, "accepted_campaign_events": 0}
