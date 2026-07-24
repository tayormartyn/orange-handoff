"""
Human-review package builder. For every field candidate assembles: the immutable original + a
highlighted-region overlay, the actual crop, all hashes + bbox, primary + blind-second readings,
comparison state, alternatives, evidence domain, and accepted=NULL. Read-only on evidence; writes
only review artifacts. Presents choices for a human — it does NOT decide anything.
"""
from __future__ import annotations
import json
import os

from __init__ import REVIEW_DECISIONS

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def build_review_package(media_id, candidate_db, out_dir=None, draw_highlights=True):
    c = candidate_db.conn
    img = c.execute("SELECT original_path, sha256, pixel_width, pixel_height FROM ingested_images "
                    "WHERE media_id=?", (media_id,)).fetchone()
    original_rel, original_sha, W, H = img
    fixtures_root = os.path.join(_ROOT, "data", "vision_fixtures_v1")
    original_abs = os.path.join(fixtures_root, original_rel)   # original_rel already includes media_id
    out_dir = out_dir or os.path.join(fixtures_root, media_id, "review_package")
    os.makedirs(out_dir, exist_ok=True)

    rows = c.execute("""
        SELECT fc.candidate_field_id, fc.field_type, fc.region_id, fc.candidate_value_string,
               fc.raw_visible_text, fc.evidence_domain, fc.review_status, fc.crop_sha256,
               cr.crop_path, cr.bbox, cr.crop_width, cr.crop_height, cr.region_type,
               sr.raw_returned_string, sr.confidence, sr.reader_engine,
               cmp.comparison_state, cmp.disagreement_reason, cmp.alternative_readings,
               cmp.primary_confidence, cmp.accepted_value
        FROM field_candidates fc
        LEFT JOIN crops cr ON cr.crop_sha256=fc.crop_sha256
        LEFT JOIN second_readings sr ON sr.crop_sha256=fc.crop_sha256
        LEFT JOIN reader_comparisons cmp ON cmp.candidate_field_id=fc.candidate_field_id
        WHERE fc.media_id=? ORDER BY fc.region_id, fc.field_type""", (media_id,)).fetchall()

    Image = ImageDraw = None
    if draw_highlights:
        try:
            from PIL import Image, ImageDraw
        except Exception:
            draw_highlights = False

    entries = []
    for r in rows:
        (cfid, ftype, rid, cval, rawtext, domain, rstatus, csha, cpath, bbox_json, cw, ch, rtype,
         second_raw, second_conf, engine, state, reason, alts, pconf, accepted) = r
        bbox = json.loads(bbox_json) if bbox_json else None
        highlight_rel = None
        if draw_highlights and bbox and Image is not None:
            hi = Image.open(original_abs).convert("RGB")
            d = ImageDraw.Draw(hi)
            d.rectangle(bbox, outline=(255, 0, 0), width=3)
            hp = os.path.join(out_dir, f"highlight_{cfid.split(':')[-2]}_{ftype}.png".replace("/", "_"))
            hi.save(hp)
            highlight_rel = os.path.relpath(hp, _ROOT)
        entries.append({
            "candidate_field_id": cfid, "field_type": ftype, "region_type": rtype,
            "parent_region": rid,
            "original_image_path": os.path.relpath(original_abs, _ROOT),
            "original_sha256": original_sha,
            "highlighted_region_path": highlight_rel, "bounding_box": bbox,
            "crop_path": (os.path.join(os.path.dirname(os.path.relpath(original_abs, _ROOT)), cpath)
                          if cpath else None),
            "crop_sha256": csha, "crop_pixel_dims": [cw, ch] if cw else None,
            "primary_raw_reading": rawtext if rawtext is not None else cval,
            "primary_candidate_value": cval, "primary_confidence": pconf,
            "second_reader_raw": second_raw, "second_reader_confidence": second_conf,
            "second_reader_engine": engine,
            "comparison_state": state, "disagreement_details": reason,
            "alternative_readings": json.loads(alts) if alts else None,
            "evidence_domain": domain, "review_status": rstatus,
            "accepted_value": accepted,          # always NULL until human review
            "allowed_decisions": list(REVIEW_DECISIONS),
            "labels": ["OBSERVATION_ONLY", "NOT_A_FILL", "NOT_AN_OUTCOME"],
            "note": ("provider-displayed profit figure — evidence only; NOT Martyn's result; "
                     "not eligible for R/expectancy/outcome"
                     if ftype == "PROVIDER_DISPLAYED_PNL" else None),
        })
    package = {"media_id": media_id, "original_sha256": original_sha,
               "original_dims": [W, H], "field_count": len(entries),
               "accepted_facts_so_far": 0, "instruction":
               "Human reviewer confirms/corrects each field against its crop. No inferred numbers. "
               "Confirmation creates only APPROVED_MEDIA_FACT — never a campaign event or outcome.",
               "entries": entries}
    out = os.path.join(out_dir, "review_package.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(package, f, indent=2)
    return out, len(entries)
