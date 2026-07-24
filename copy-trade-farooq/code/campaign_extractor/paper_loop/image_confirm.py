"""
Minimal interactive human-review CLI for a manually-imported screenshot intake. Loads the existing
immutable manifest, verifies the original image SHA-256, asks Martyn one field at a time (UNKNOWN
allowed; NO guessed defaults), and — only after the exact phrase `CONFIRM OBSERVATION` — writes an
immutable, timestamped review-decision SIDECAR (the manifest is never overwritten). Image-import
time is NEVER treated as screenshot-captured or provider-posted time. No execution, no broker I/O.
"""
from __future__ import annotations
import hashlib
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

import image_intake
import ingest as vision_ingest

FIXTURES = os.path.join(_ROOT, "data", "vision_fixtures_v1")
REVIEW_DIR = os.path.join(image_intake.INTAKE_ROOT, "review")
CONFIRM_PHRASE = "CONFIRM OBSERVATION"
FIELDS = ("instrument", "direction", "entry_low", "entry_high", "stop_price", "target_prices")
INTAKE_CLASSES = ("SIGNAL", "TRADE_UPDATE", "TRADE_RESULT", "UNKNOWN")
EXCLUSION_REASONS = {"TRADE_UPDATE": "MANAGEMENT_OF_EXISTING_POSITION",
                     "TRADE_RESULT": "KNOWN_RESULT_OR_CLOSED_TRADE_IMAGE",
                     "UNKNOWN": "REQUIRES_LATER_REVIEW"}


class IntakeError(Exception):
    pass


def _now():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def load_and_verify_intake(intake_id):
    """Return (manifest, original_abs_path). Raises IntakeError on missing manifest or SHA mismatch."""
    manifest = image_intake.load_manifest(intake_id)
    if manifest is None:
        raise IntakeError(f"no manifest for {intake_id}")
    media_id, sha = manifest["imported_media_id"], manifest["original_image_sha256"]
    mdir = os.path.join(FIXTURES, media_id)
    orig = None
    if os.path.isdir(mdir):
        for fn in os.listdir(mdir):
            if fn.startswith(f"original_{sha}."):
                orig = os.path.join(mdir, fn)
                break
    if not orig or not os.path.isfile(orig):
        raise IntakeError(f"immutable original not found for {media_id}")
    actual = vision_ingest.sha256_file(orig)
    if actual != sha:
        raise IntakeError(f"IMAGE_HASH_MISMATCH manifest={sha[:16]} actual={actual[:16]}")
    return manifest, orig


def _field_state(v):
    return ("UNKNOWN", None) if v in (None, "", "UNKNOWN", "unknown") else ("CONFIRMED", str(v))


PROVIDER_SOURCE_PROVENANCE = ("VISIBLE_FAROUK_IDENTITY", "TELEGRAM_CHANNEL_REF",
                              "MESSAGE_ID_OR_LINK", "HUMAN_ATTESTED_VISIBLE_SOURCE")


def _provider_verification(provider, evidence_refs, source_provenance=None, source_attested=False):
    """Verified ONLY with (named provider) + (genuine source evidence) + (a recognised source
    provenance) + (explicit reviewer attestation). Name alone / uncertain source -> UNVERIFIED.
    Never inferred from filename, folder or upload time."""
    if not provider or str(provider).upper() in ("UNKNOWN", ""):
        return "PROVIDER_UNVERIFIED"
    has_evidence = bool(evidence_refs) and any(str(e).strip() and str(e).upper() != "UNKNOWN"
                                               for e in (evidence_refs or []))
    prov_ok = source_provenance in PROVIDER_SOURCE_PROVENANCE
    return ("PROVIDER_VERIFIED" if (has_evidence and prov_ok and source_attested is True)
            else "PROVIDER_UNVERIFIED")


def _post_time_provenance(posted_at, provenance):
    valid = ("DISCORD_MESSAGE_ID_OR_LINK", "VISIBLE_ABSOLUTE_TIMESTAMP",
             "VISIBLE_TIME_HUMAN_DATE_CONFIRMED", "HUMAN_ATTESTED_AGAINST_ORIGINAL")
    if posted_at and provenance in valid:
        return posted_at, provenance
    return None, "UNVERIFIABLE"                        # never substitute capture/import/confirm time


def build_review_record(intake_id, manifest, answers):
    """Deterministic, content-addressed review record (idempotent by intake+reviewer+answers).
    The FIRST-class gate is `intake_class` in {SIGNAL, TRADE_RESULT, UNKNOWN}; only SIGNAL may
    become a signal. TRADE_RESULT/UNKNOWN are PIPELINE_EXCLUDED (preserved as evidence only)."""
    intake_class = str(answers.get("intake_class") or "UNKNOWN").upper()
    if intake_class not in INTAKE_CLASSES:
        intake_class = "UNKNOWN"
    pipeline_excluded = intake_class != "SIGNAL"
    exclusion_reason = EXCLUSION_REASONS.get(intake_class)
    visible_result_fields = answers.get("visible_result_fields") or {}   # entry/exit/pnl if TRADE_RESULT
    reviewer = answers.get("reviewer_ref") or "UNKNOWN"
    evidence = answers.get("source_evidence_references") or []
    if isinstance(evidence, str):
        evidence = [evidence] if evidence.strip() else []
    posted_at, post_prov = _post_time_provenance(answers.get("provider_posted_at"),
                                                 answers.get("provider_posted_provenance"))
    fields = {}
    for f in FIELDS:
        st, val = _field_state(answers.get(f))
        fields[f] = {"value": val, "confirmation_state": st,
                     "provenance": "HUMAN_READ_FROM_IMAGE" if st == "CONFIRMED" else "UNRESOLVED"}
    provider = answers.get("provider") or "UNKNOWN"
    source_provenance = answers.get("source_provenance")
    source_attested = answers.get("source_attested") is True
    prov_state = _provider_verification(provider, evidence, source_provenance, source_attested)
    confirmed = answers.get("explicit_confirmation") is True

    payload = {"intake_id": intake_id, "reviewer_ref": reviewer, "intake_class": intake_class,
               "semantic_class": answers.get("semantic_class") or "UNKNOWN",
               "fields": {k: fields[k]["value"] for k in FIELDS}, "provider": provider,
               "provider_posted_at": posted_at, "post_prov": post_prov,
               "visible_result_fields": visible_result_fields, "source_provenance": source_provenance,
               "source_attested": source_attested, "evidence": sorted(evidence), "confirmed": confirmed}
    review_id = "review-img-" + hashlib.sha256(
        json.dumps(payload, sort_keys=True).encode()).hexdigest()[:16]
    return {
        "review_id": review_id, "intake_id": intake_id,
        "original_image_sha256": manifest["original_image_sha256"],
        "imported_media_id": manifest["imported_media_id"],
        "reviewer_ref": reviewer, "review_created_at_utc": _now(),
        "intake_class": intake_class,
        "pipeline_excluded": pipeline_excluded, "exclusion_reason": exclusion_reason,
        "visible_result_fields": visible_result_fields,
        "semantic_class": answers.get("semantic_class") or "UNKNOWN",
        "fields": fields,
        "provider": {"value": provider, "verification_state": prov_state,
                     "evidence_references": evidence, "source_provenance": source_provenance,
                     "source_attested": source_attested},
        "provider_posted_at": {"value": posted_at, "timezone": answers.get("provider_posted_timezone"),
                               "provenance": post_prov},
        "source_evidence_references": evidence,
        "explicit_confirmation_state": "CONFIRMED" if confirmed else "NOT_CONFIRMED",
        "labels": ["OBSERVATION_ONLY", "PAPER_ONLY", "NOT_A_FILL", "NOT_AN_OUTCOME"],
    }


def save_review(record):
    """Immutable append-only sidecar. Never overwrites; a re-save returns the existing record."""
    os.makedirs(REVIEW_DIR, exist_ok=True)
    path = os.path.join(REVIEW_DIR, f"{record['review_id']}.json")
    if os.path.exists(path):
        return json.load(open(path, encoding="utf-8")), path, False
    with open(path, "w", encoding="utf-8") as f:
        json.dump(record, f, indent=2)
    with open(os.path.join(REVIEW_DIR, "review_events.jsonl"), "a", encoding="utf-8") as f:
        f.write(json.dumps({"event": "REVIEW_SAVED", "review_id": record["review_id"],
                            "intake_id": record["intake_id"],
                            "confirmed": record["explicit_confirmation_state"], "at": _now()}) + "\n")
    return record, path, True


def load_review(review_id):
    p = os.path.join(REVIEW_DIR, f"{review_id}.json")
    return json.load(open(p, encoding="utf-8")) if os.path.exists(p) else None


# ---------------------------------------------------------------- interactive CLI (not run by tests)
def _ask(label, allow_unknown=True):
    raw = input(f"  {label}{' (blank/UNKNOWN allowed)' if allow_unknown else ''}: ").strip()
    return None if raw == "" or raw.upper() == "UNKNOWN" else raw


def interactive(intake_id):
    manifest, orig = load_and_verify_intake(intake_id)
    print(f"\nINTAKE {intake_id}  media={manifest['imported_media_id']}")
    print(f"  immutable original : {orig}")
    print(f"  sha256[:16]        : {manifest['original_image_sha256'][:16]}  (verified)")
    print(f"  screenshot_imported_at (NOT posted/captured time): {manifest['screenshot_imported_at']}")
    try:
        os.startfile(orig)                             # open in Windows image viewer (best-effort)
    except Exception as e:                             # noqa: BLE001
        print(f"  (could not auto-open viewer: {type(e).__name__}; open manually: {orig})")
    # ---- MANDATORY FIRST STEP: semantic classification gate ----
    print("\nSTEP 1 — classify this image. Type exactly one of: SIGNAL / TRADE_RESULT / UNKNOWN")
    print("  SIGNAL       = a fresh actionable entry signal")
    print("  TRADE_RESULT = a completed/closed trade or result/P&L card (NOT a signal)")
    print("  UNKNOWN      = unsure -> blocked for later review")
    ic = input("  classification: ").strip().upper()
    if ic not in INTAKE_CLASSES:
        print(f"ABORTED — '{ic}' is not one of {INTAKE_CLASSES}; no record created."); return None
    reviewer = _ask("Reviewer reference (e.g. martyn)", allow_unknown=False)

    if ic == "UNKNOWN":
        rec = build_review_record(intake_id, manifest, {"intake_class": "UNKNOWN",
              "reviewer_ref": reviewer, "explicit_confirmation": False})
        saved, path, new = save_review(rec)
        print(f"BLOCKED — classified UNKNOWN (requires later review). Recorded {saved['review_id']}; "
              f"NOT processed as a signal.")
        return saved

    if ic == "TRADE_RESULT":
        print("\nTRADE_RESULT — preserving as EVIDENCE ONLY (no signal, no Q4A, no paper obs).")
        vrf = {"instrument": _ask("Visible instrument"), "entry": _ask("Visible entry"),
               "exit": _ask("Visible exit/close"), "pnl": _ask("Visible P&L (evidence only)")}
        rec = build_review_record(intake_id, manifest, {"intake_class": "TRADE_RESULT",
              "reviewer_ref": reviewer, "visible_result_fields": vrf, "explicit_confirmation": False})
        print("\n===== TRADE_RESULT CLASSIFICATION =====")
        print(json.dumps({"visible_result_fields": vrf,
                          "exclusion_reason": rec["exclusion_reason"]}, indent=2, default=str))
        print("\nType exactly 'CONFIRM CLASSIFICATION' to record this exclusion (anything else aborts):")
        if input("> ").strip() != "CONFIRM CLASSIFICATION":
            print("ABORTED — no classification record created."); return None
        rec = build_review_record(intake_id, manifest, {"intake_class": "TRADE_RESULT",
              "reviewer_ref": reviewer, "visible_result_fields": vrf, "explicit_confirmation": True})
        saved, path, new = save_review(rec)
        print(("CREATED" if new else "ALREADY EXISTS (idempotent)") + f" TRADE_RESULT classification "
              f"{saved['review_id']} -> {path}  (PIPELINE_EXCLUDED, {saved['exclusion_reason']})")
        return saved

    # ic == "SIGNAL"
    print("\nSTEP 2 — enter what you can VISIBLY read. Blank/UNKNOWN if unsure — no guessing.\n")
    a = {"intake_class": "SIGNAL", "reviewer_ref": reviewer,
         "instrument": _ask("Instrument (e.g. XAUUSD)"), "direction": _ask("Direction (BUY/SELL)"),
         "entry_low": _ask("Entry low (or the single entry)"),
         "entry_high": _ask("Entry high (repeat single entry if one price)"),
         "stop_price": _ask("Stop-loss"), "target_prices": _ask("Targets (comma-separated)"),
         "provider": _ask("Provider identity (e.g. FAROUK, or UNKNOWN)"),
         "provider_posted_at": _ask("Provider-posted time (ISO, only if you can prove date+tz)"),
         "provider_posted_timezone": _ask("Timezone of that post time"),
         "provider_posted_provenance": _ask("Post-time provenance (DISCORD_MESSAGE_ID_OR_LINK/"
                                            "VISIBLE_ABSOLUTE_TIMESTAMP/... or blank=UNVERIFIABLE)"),
         "source_evidence_references": _ask("Source/channel/Discord message evidence"),
         "source_provenance": _ask("Source provenance (VISIBLE_FAROUK_IDENTITY/TELEGRAM_CHANNEL_REF/"
                                   "MESSAGE_ID_OR_LINK/HUMAN_ATTESTED_VISIBLE_SOURCE, blank=none)"),
         "source_attested": (input("  Do you EXPLICITLY confirm the visible source? (yes/no): ")
                             .strip().lower() == "yes")}
    rec = build_review_record(intake_id, manifest, {**a, "explicit_confirmation": False})
    print("\n===== SIGNAL REVIEW SUMMARY =====")
    print(json.dumps({k: rec[k] for k in ("fields", "provider", "provider_posted_at",
                                          "source_evidence_references")}, indent=2, default=str))
    print(f"\nType exactly '{CONFIRM_PHRASE}' to create the immutable review decision (anything else aborts):")
    if input("> ").strip() != CONFIRM_PHRASE:
        print("ABORTED — no review decision created."); return None
    rec = build_review_record(intake_id, manifest, {**a, "explicit_confirmation": True})
    saved, path, new = save_review(rec)
    print(("CREATED" if new else "ALREADY EXISTS (idempotent)") + f" SIGNAL review {saved['review_id']} -> {path}")
    print(f"Next: python campaign_extractor/paper_loop/image_paper_run.py {intake_id} {saved['review_id']}")
    return saved


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage: image_confirm.py <intake_id>"); sys.exit(2)
    interactive(sys.argv[1])
