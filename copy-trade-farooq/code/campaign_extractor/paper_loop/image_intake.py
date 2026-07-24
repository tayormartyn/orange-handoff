"""
Automation-ready MANUAL intake (Phase 1). Every inbox image is imported IMMUTABLY via the existing
Vision importer before it is ever treated as evidence, and linked to an intake manifest. The inbox
is a future drop location only — this brick does NOT watch it. Folder names never prove provider
identity. Duplicate image hashes are detected and handled idempotently.
"""
from __future__ import annotations
import json
import os
import sys
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
_CE = os.path.dirname(_HERE)
_ROOT = os.path.dirname(_CE)
_VIS = os.path.join(_CE, "vision_v1")
for p in (_ROOT, _CE, _VIS):
    if p not in sys.path:
        sys.path.insert(0, p)

import ingest as vision_ingest                          # Vision V1.1 immutable importer (unchanged)
from stores import CandidateDB

INTAKE_ROOT = os.path.join(_ROOT, "data", "manual_image_intake_v1")
SUBDIRS = ("inbox", "manifests", "review", "processed", "rejected")


def ensure_structure(root=None):
    root = root or INTAKE_ROOT
    for d in SUBDIRS:
        os.makedirs(os.path.join(root, d), exist_ok=True)
    return root


def import_intake_image(src_path, *, provider_candidate="UNKNOWN", source_server_channel_text=None,
                        discord_message_ref=None, screenshot_captured_at=None,
                        claimed_provider_posted_at=None, claimed_timezone=None, human_notes=None,
                        candidate_db=None, root=None):
    """Immutably import an image and write an intake manifest. Idempotent by content hash: a
    duplicate image returns the existing media_id and a manifest marked DUPLICATE_OF."""
    root = ensure_structure(root)
    cdb = candidate_db or CandidateDB()
    sha = vision_ingest.sha256_file(src_path)
    pre_existing = cdb.get_image_by_sha(sha) is not None
    media_id, created = vision_ingest.ingest_image(src_path, cdb)   # immutable + recorded
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    intake_id = f"intake-{sha[:16]}"
    manifest = {
        "intake_id": intake_id, "original_filename": os.path.basename(src_path),
        "imported_media_id": media_id, "original_image_sha256": sha,
        "provider_candidate": provider_candidate,          # NOT proven by folder placement
        "platform": "DISCORD", "source_server_channel_text": source_server_channel_text,
        "discord_message_ref": discord_message_ref,
        "screenshot_captured_at": screenshot_captured_at, "screenshot_imported_at": now,
        "claimed_provider_posted_at": claimed_provider_posted_at, "claimed_timezone": claimed_timezone,
        "human_notes": human_notes,
        "intake_status": "DUPLICATE_OF_EXISTING" if pre_existing else "IMPORTED_PENDING_REVIEW",
        "duplicate": pre_existing,
    }
    mpath = os.path.join(root, "manifests", f"{intake_id}.json")
    if not os.path.exists(mpath):
        with open(mpath, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)
    return manifest, mpath


def load_manifest(intake_id, root=None):
    root = root or INTAKE_ROOT
    p = os.path.join(root, "manifests", f"{intake_id}.json")
    return json.load(open(p, encoding="utf-8")) if os.path.exists(p) else None
