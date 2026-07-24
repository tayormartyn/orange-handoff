"""
Human-review gate (Layer 1 candidate -> Layer 2 APPROVED_MEDIA_FACT). Human confirmation creates
ONLY an approved media fact — never a campaign event. A CORRECT value must be visibly supported by
the image; the reviewer may not insert an inferred number absent from the image. Every approved
fact traces to the original image sha256, region, and crop.
"""
from __future__ import annotations

APPROVING = ("CONFIRM", "CORRECT")


def apply_review(*, candidate, decision, reviewer_ref, image_sha256, review_db,
                 confirmed_value=None, review_note=None, image_supported=False):
    if decision not in ("CONFIRM", "CORRECT", "REJECT", "UNREADABLE", "WRONG_FIELD",
                        "WRONG_INSTRUMENT", "NOT_A_TRADE_FACT"):
        raise ValueError(f"unknown review decision: {decision}")
    review_id = f"rev:{candidate['candidate_field_id']}:{decision}"
    review_db.insert_review(
        review_id=review_id, candidate_field_id=candidate["candidate_field_id"],
        media_id=candidate["media_id"], reviewer_ref=reviewer_ref, decision=decision,
        confirmed_value=confirmed_value, review_note=review_note,
        source_crop_sha256=candidate.get("crop_sha256"))

    if decision not in APPROVING:
        return None                                    # REJECT/UNREADABLE/etc -> no approved fact
    if not confirmed_value:
        raise ValueError("CONFIRM/CORRECT requires a confirmed_value that is visible in the image")
    if decision == "CORRECT" and not image_supported:
        raise ValueError("a CORRECT value must be visibly supported by the image (no inferred numbers)")

    approved_fact_id = f"amf:{candidate['candidate_field_id']}"
    review_db.insert_approved_fact(
        approved_fact_id=approved_fact_id, candidate_field_id=candidate["candidate_field_id"],
        media_id=candidate["media_id"], field_type=candidate["field_type"],
        confirmed_value=str(confirmed_value), source_original_sha256=image_sha256,
        source_region_id=candidate["region_id"], source_crop_sha256=candidate.get("crop_sha256"),
        evidence_domain=candidate["evidence_domain"])
    return approved_fact_id                            # ONLY an approved media fact; no campaign event
