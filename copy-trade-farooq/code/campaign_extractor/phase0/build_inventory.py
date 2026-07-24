"""
Phase 0 — Media Inventory + Immutable Fixture Builder  (campaign extractor layer)

READ-ONLY to data/signal_archive.db.  Writes ONLY inside campaign_extractor/phase0/.
Does NOT touch: permanent archive rows, the signed-off 28, coverage-waterfall,
the +0.17R baseline, the live stub, or any shadow/paper state.

What it does, deterministically (no AI, no guessing):
  1. Reads the exact Farouk fixture-date messages from the archive (read-only).
  2. Derives sender identity from the literal "<handle> Posted in <emoji>·<channel>"
     header line — sender is EVIDENCE, recorded per message.
  3. Classifies each message's media status (TEXT_ONLY / MEDIA_REFERENCE_ONLY /
     MEDIA_AVAILABLE / MEDIA_MISSING / MEDIA_UNREADABLE).
  4. Verifies the stored content_hash against a recomputed sha256 (tamper check).
  5. Emits immutable, hashed fixture-transcript JSON files (the "expected truth"
     skeleton — numeric truths to be filled in by MANUAL check, never by code here).
  6. Emits media_manifest.json and inventory_summary.json.

Re-running with the same archive bytes produces byte-identical outputs (idempotent),
EXCEPT the run wall-clock stamp, which is read from an env var so determinism holds.
"""
import sqlite3, hashlib, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ARCHIVE = os.path.normpath(os.path.join(HERE, "..", "..", "data", "signal_archive.db"))
FIX_DIR = os.path.join(HERE, "fixtures")
FIXTURE_DATES = ["2026-06-17", "2026-06-18", "2026-06-24", "2026-06-25", "2026-06-26"]

# The ONLY sender whose posts may produce campaign-state-mutating events.
FAROUK_HANDLE = "seascalperfarouk"
# Known non-Farouk voices -> ANALYSIS_ONLY context (recorded, never mutating).
KNOWN_VOICES = {
    "seascalperfarouk": "Farouk",
    ".ccolumbus": "Columbus",
    "kyledoops": "Kyle Dukes",
    "wazwithazed": "Azed (quant-flow)",
    "navigatorjosh": "Josh the Navigator",
    "wallstreetsingh": "Wall Street Singh",
    "terrilyn": "Terrilyn",
}
HANDLE_RE = re.compile(r"^([A-Za-z0-9_.]+)\s+Posted in\b")
# textual references that imply an image we may not possess
MEDIA_REF_RE = re.compile(r"\b(screenshot|screen shot|chart|image|photo|pic|picture|attached)\b", re.I)


def sha256(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def derive_sender(raw_text: str):
    first = ""
    for line in (raw_text or "").splitlines():
        if line.strip():
            first = line.strip()
            break
    m = HANDLE_RE.match(first)
    if m:
        h = m.group(1)
        return h, KNOWN_VOICES.get(h, "UNKNOWN_HANDLE")
    if "Posted in" in (raw_text or ""):
        return None, "AMBIGUOUS_NO_HANDLE"   # header present but no handle -> fail closed
    return None, "NO_HEADER"


def classify_media(raw_text: str) -> str:
    # No media bytes were ever captured at ingest (archive is text-only), so nothing
    # can be MEDIA_AVAILABLE here. A textual mention of an image => MEDIA_REFERENCE_ONLY.
    return "MEDIA_REFERENCE_ONLY" if MEDIA_REF_RE.search(raw_text or "") else "TEXT_ONLY"


def main():
    run_stamp = os.environ.get("PHASE0_RUN_STAMP", "UNSET_RUN_STAMP")
    if not os.path.exists(ARCHIVE):
        sys.exit(f"archive not found: {ARCHIVE}")
    con = sqlite3.connect(f"file:{ARCHIVE}?mode=ro", uri=True)
    cur = con.cursor()

    manifest = []
    summary = {
        "run_stamp": run_stamp,
        "archive_path": os.path.relpath(ARCHIVE, HERE),
        "archive_sha256_note": "see archive_fingerprint",
        "fixture_dates": FIXTURE_DATES,
        "media_capture_implemented_at_ingest": False,
        "media_available_count": 0,
        "per_date": {},
        "media_status_totals": {},
        "sender_totals": {},
        "hash_mismatches": [],
    }

    for d in FIXTURE_DATES:
        rows = cur.execute(
            "select message_key, message_id, content_hash, raw_text, sent_at_utc, "
            "edited_at_utc, version_number from raw_message_versions "
            "where sent_at_utc like ? order by message_key, version_number",
            (d + "%",),
        ).fetchall()

        # keep latest version per message_key (deterministic: highest version_number)
        latest = {}
        for mk, mid, chash, raw, sent, edited, ver in rows:
            cur_best = latest.get(mk)
            if cur_best is None or ver > cur_best[6]:
                latest[mk] = (mk, mid, chash, raw, sent, edited, ver)

        msgs = []
        for mk in sorted(latest):
            mk_, mid, chash, raw, sent, edited, ver = latest[mk]
            recomputed = sha256(raw)
            hash_ok = (recomputed == chash)
            if not hash_ok:
                summary["hash_mismatches"].append({"message_key": mk_, "stored": chash, "recomputed": recomputed})
            handle, voice = derive_sender(raw)
            media_status = classify_media(raw)
            is_farouk = (handle == FAROUK_HANDLE)
            role = "CAMPAIGN_SOURCE" if is_farouk else "ANALYSIS_ONLY_CONTEXT"
            msgs.append({
                "message_key": mk_,
                "message_id": mid,
                "sent_at_utc": sent,
                "edited_at_utc": edited,
                "version_number": ver,
                "content_hash_stored": chash,
                "content_hash_recomputed": recomputed,
                "content_hash_ok": hash_ok,
                "sender_handle": handle,
                "sender_voice": voice,
                "is_farouk": is_farouk,
                "role": role,
                "media_status": media_status,
                "raw_text": raw,
                # expected-truth slots: filled ONLY by manual review, never by code.
                "expected_truth": {
                    "manually_checked": False,
                    "events": None,          # list of expected campaign events (Farouk only)
                    "notes": None,
                },
            })
            summary["media_status_totals"][media_status] = summary["media_status_totals"].get(media_status, 0) + 1
            vkey = voice if handle else voice
            summary["sender_totals"][vkey] = summary["sender_totals"].get(vkey, 0) + 1

        # immutable fixture transcript: hash over the deterministic message payload
        payload = [{k: m[k] for k in ("message_key", "content_hash_stored", "raw_text",
                                       "sender_handle", "media_status")} for m in msgs]
        fixture_hash = sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True))
        fixture = {
            "fixture_date": d,
            "fixture_hash": fixture_hash,
            "message_count": len(msgs),
            "farouk_count": sum(1 for m in msgs if m["is_farouk"]),
            "non_farouk_count": sum(1 for m in msgs if not m["is_farouk"]),
            "messages": msgs,
        }
        with open(os.path.join(FIX_DIR, f"fixture_{d}.json"), "w", encoding="utf-8") as f:
            json.dump(fixture, f, ensure_ascii=False, indent=2)

        summary["per_date"][d] = {
            "messages": len(msgs),
            "farouk": fixture["farouk_count"],
            "non_farouk": fixture["non_farouk_count"],
            "fixture_hash": fixture_hash,
        }
        for m in msgs:
            manifest.append({
                "fixture_date": d,
                "message_key": m["message_key"],
                "sender_handle": m["sender_handle"],
                "sender_voice": m["sender_voice"],
                "role": m["role"],
                "media_status": m["media_status"],
                "media_bytes_present": False,
                "media_cache_path": None,   # nothing to cache: media was never captured
                "manual_confirmation": "PENDING",
            })

    with open(os.path.join(HERE, "media_manifest.json"), "w", encoding="utf-8") as f:
        json.dump({"run_stamp": run_stamp, "entries": manifest}, f, ensure_ascii=False, indent=2)
    with open(os.path.join(HERE, "inventory_summary.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
