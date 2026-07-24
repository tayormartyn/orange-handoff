"""
Immutable import CLI for a Vision V1 fixture image.
Usage: python campaign_extractor/vision_v1/ingest_cli.py <path-to-image> [source_message_id]
Hashes + copies the original read-only to data/vision_fixtures_v1/<media_id>/original_<sha>.<ext>
and records it in data/media_candidates_v1.db. Idempotent by content hash. Never edits the original.
"""
from __future__ import annotations
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stores import CandidateDB
import ingest


def main():
    if len(sys.argv) < 2:
        print("usage: ingest_cli.py <path-to-image> [source_message_id]"); return 2
    src = sys.argv[1]
    if not os.path.isfile(src):
        print(f"BTC_FIXTURE_IMAGE_REQUIRED: not found: {src}"); return 2
    msg = sys.argv[2] if len(sys.argv) > 2 else None
    cdb = CandidateDB()
    mid, created = ingest.ingest_image(src, cdb, source_message_id=msg)
    print(("INGESTED " if created else "ALREADY_PRESENT ") + mid, "sha256=" + ingest.sha256_file(src)[:16] + "...")
    cdb.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
