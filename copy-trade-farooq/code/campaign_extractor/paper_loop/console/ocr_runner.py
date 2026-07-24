"""
Runs UNDER .venv-vision (RapidOCR). Full-image blind OCR of an immutable image, then the pure
ocr_adapter.propose(). Prints the proposals as JSON to stdout. READ-ONLY: it writes no evidence,
creates no review/observation, and never mutates Vision V1.1. Invoked by the console as a subprocess.
"""
from __future__ import annotations
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)
import ocr_adapter


def main(image_path):
    try:
        from rapidocr_onnxruntime import RapidOCR
    except Exception as e:                          # noqa: BLE001
        print(json.dumps({"error": "RAPIDOCR_UNAVAILABLE", "detail": type(e).__name__}))
        return 0
    ocr = RapidOCR()
    result, _elapse = ocr(image_path)
    lines, full = [], []
    for item in (result or []):
        box = item[0] if len(item) > 0 else None
        text = item[1] if len(item) > 1 else ""
        score = item[2] if len(item) > 2 else None
        lines.append({"text": text, "box": box, "conf": score})
        full.append(text)
    prop = ocr_adapter.propose({"lines": lines, "full_text": "\n".join(full)})
    prop["ocr_engine"] = "rapidocr-onnxruntime (full-image blind)"
    print(json.dumps(prop, default=str))
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(json.dumps({"error": "USAGE"})); sys.exit(2)
    sys.exit(main(sys.argv[1]))
