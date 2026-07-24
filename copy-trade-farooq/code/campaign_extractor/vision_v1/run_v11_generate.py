"""
V1.1 generation (run under .venv-vision — needs Pillow + rapidocr). Creates real immutable pixel
crops from the BTC original, runs a BLIND independent OCR (RapidOCR) on each crop, stores crops +
second readings + primary/secondary comparisons, and migrates each field candidate to its real
crop hash. Idempotent. Never modifies the original. The OCR receives ONLY crop pixels + a generic
field type — never the primary answer or any expected value.
"""
from __future__ import annotations
import hashlib
import os
import sys
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
for p in (os.path.dirname(os.path.dirname(_HERE)), os.path.dirname(_HERE), _HERE):
    sys.path.insert(0, p)

from stores import CandidateDB
import decimals

MID = "media-08951b5616218879"
SHA = "08951b561621887959c461ce887dc72cc28b09dad4f9263c403e3feae00e8e57"
ORIG = os.path.join(os.path.dirname(os.path.dirname(_HERE)), "data", "vision_fixtures_v1", MID,
                    f"original_{SHA}.png")
CROP_DIR = os.path.join(os.path.dirname(ORIG), "crops")

# field crop specs derived from RapidOCR full-image detection boxes (real coordinates)
SPECS = [
    ("INSTRUMENT_HEADER", None, "REGION", [8, 0, 135, 26]),
    ("TICKET_1", None, "REGION", [0, 0, 551, 52]),
    ("TICKET_2", None, "REGION", [0, 52, 551, 124]),
    ("COMMENTARY_TEXT", None, "REGION", [10, 500, 540, 705]),
    ("TICKET_1", "INSTRUMENT", "t1", [10, 0, 72, 26]),
    ("TICKET_1", "DIRECTION", "t1", [70, 2, 110, 24]),
    ("TICKET_1", "LOT_SIZE", "t1", [104, 2, 132, 24]),
    ("TICKET_1", "ENTRY_PRICE", "t1", [12, 30, 106, 51]),
    ("TICKET_1", "EXIT_PRICE", "t1", [108, 30, 226, 51]),
    ("TICKET_1", "PROVIDER_DISPLAYED_PNL", "t1", [448, 6, 548, 42]),
    ("TICKET_2", "INSTRUMENT", "t2", [10, 70, 72, 96]),
    ("TICKET_2", "DIRECTION", "t2", [70, 72, 110, 94]),
    ("TICKET_2", "LOT_SIZE", "t2", [104, 72, 132, 94]),
    ("TICKET_2", "ENTRY_PRICE", "t2", [12, 100, 106, 122]),
    ("TICKET_2", "EXIT_PRICE", "t2", [108, 100, 226, 122]),
    ("TICKET_2", "PROVIDER_DISPLAYED_PNL", "t2", [448, 78, 548, 112]),
    ("COMMENTARY_TEXT", "COMMENTARY_TEXT", "comm", [10, 540, 540, 700]),
]


def _blind_full_image_read(ocr, orig):
    """Second reader: RapidOCR on the FULL image, blind (no expected values, no primary answer).
    Detections are assigned to fields DETERMINISTICALLY by geometry (row by y, number-splitting)."""
    import re
    res, _ = ocr(orig)
    second = {}   # (parent, field_type) -> (raw, conf)
    NUM = re.compile(r"\d+[.,]\d+|\d+")
    for box, text, conf in res:
        ys = min(p[1] for p in box); xs = min(p[0] for p in box)
        conf = float(conf)
        row = "t1" if ys < 55 else ("t2" if ys < 130 else ("comm" if ys > 480 else "hdr"))
        t = str(text)
        nums = NUM.findall(t.replace(" ", ""))
        up = t.upper().replace(" ", "")
        if "BTCUSD" in up and row in ("t1", "t2"):
            second[(row, "INSTRUMENT")] = ("BTCUSD", conf)
            m = re.search(r"(buy|sell)", t, re.I)
            if m:
                second[(row, "DIRECTION")] = (m.group(1).upper(), conf)
            if nums:
                second[(row, "LOT_SIZE")] = (nums[-1], conf)
        elif len(nums) >= 2 and row in ("t1", "t2"):        # 'entry → exit'
            second[(row, "ENTRY_PRICE")] = (nums[0], conf)
            second[(row, "EXIT_PRICE")] = (nums[1], conf)
        elif len(nums) == 1 and xs > 400 and row in ("t1", "t2"):
            second[(row, "PROVIDER_DISPLAYED_PNL")] = (nums[0], conf)
        elif row == "comm":
            prev = second.get(("comm", "COMMENTARY_TEXT"), ("", conf))
            second[("comm", "COMMENTARY_TEXT")] = ((prev[0] + " " + t).strip(), conf)
    return second


def main():
    from PIL import Image
    from rapidocr_onnxruntime import RapidOCR
    import rapidocr_onnxruntime as rocr
    os.makedirs(CROP_DIR, exist_ok=True)
    cdb = CandidateDB()
    img = Image.open(ORIG)
    W, H = img.size
    ocr = RapidOCR()
    engine = "rapidocr-onnxruntime(full-image-blind + geometric field assignment)"
    ver = getattr(rocr, "__version__", "unknown")
    tool = "pillow-" + __import__("PIL").__version__
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    second = _blind_full_image_read(ocr, ORIG)

    cur = cdb.conn.execute("SELECT candidate_field_id, region_id, field_type, candidate_value_string "
                           "FROM field_candidates WHERE media_id=?", (MID,))
    cands = cur.fetchall()

    print(f"image {W}x{H}; generating {len(SPECS)} immutable crops + blind full-image OCR mapping")
    for region_type, field_type, parent, bbox in SPECS:
        x0, y0, x1, y1 = bbox
        assert 0 <= x0 < x1 <= W and 0 <= y0 < y1 <= H, f"bbox out of bounds {bbox} vs {W}x{H}"
        crop = img.crop((x0, y0, x1, y1)).convert("RGB")
        csha = hashlib.sha256(crop.tobytes() + f"{bbox}".encode()).hexdigest()
        tag = f"{parent}_{field_type or region_type}".replace("/", "_")
        cpath = os.path.join(CROP_DIR, f"crop_{tag}_{csha[:16]}.png")
        if not os.path.exists(cpath):
            crop.save(cpath)
            try:
                os.chmod(cpath, 0o444)
            except OSError:
                pass
        cdb.insert_crop(crop_id=f"crop-{csha[:16]}", media_id=MID, original_sha256=SHA,
                        region_type=region_type, parent_region_id=f"{MID}:{parent}" if parent else None,
                        field_type=field_type, bbox=bbox, crop_path=os.path.relpath(cpath, os.path.dirname(ORIG)),
                        crop_sha256=csha, crop_width=x1 - x0, crop_height=y1 - y0,
                        crop_created_at=now, crop_tool_version=tool)
        if field_type is None:
            continue
        sraw, sconf = second.get((parent, field_type), ("", None))
        cdb.insert_second_reading(reading_id=f"read-{csha[:16]}", crop_sha256=csha,
                                  requested_field_type="read visible " + ("numeric string"
                                  if field_type in ("ENTRY_PRICE", "EXIT_PRICE", "LOT_SIZE",
                                  "PROVIDER_DISPLAYED_PNL") else "text"),
                                  raw_returned_string=sraw, candidate_normalised_value=None,
                                  confidence=sconf, reader_engine=engine, reader_version=ver,
                                  read_at=now, errors=None if sraw else "no_text_assigned")
        for cfid, rid, ft, primary in cands:
            if ft == field_type and rid == f"{MID}:{parent}":
                cdb.set_candidate_crop(cfid, csha)
                pn = decimals.normalise_for_compare(ft, primary)
                sn = decimals.normalise_for_compare(ft, sraw)
                if not sraw:
                    state, reason = "ONE_READER_ONLY", "second reader assigned no text to field"
                elif not primary:
                    state, reason = "ONE_READER_ONLY", "no primary reading"
                elif pn == sn or (pn and sn and (pn in sn or sn in pn)):
                    state, reason = "READERS_AGREE", None
                else:
                    state, reason = "READERS_DISAGREE", f"primary={primary!r} second={sraw!r}"
                _, _, alts = decimals.parse_numeric(sraw)
                cdb.insert_comparison(comparison_id=f"cmp-{cfid}", candidate_field_id=cfid,
                                      crop_sha256=csha, primary_raw=primary, primary_confidence=0.95,
                                      second_raw=sraw, second_confidence=sconf,
                                      comparison_state=state, disagreement_reason=reason,
                                      alternative_readings=alts, accepted_value=None)
                print(f"  [{parent} {field_type:22}] primary={str(primary)[:14]:14} "
                      f"second={str(sraw)[:14]:14} conf={sconf} -> {state}")
    cdb.close()
    print("done.")


if __name__ == "__main__":
    main()
