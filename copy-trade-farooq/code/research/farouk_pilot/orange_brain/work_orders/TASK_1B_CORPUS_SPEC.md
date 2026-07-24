# TASK 1B — CORPUS LAYER (operator-issued; reinstated 2026-07-20, decision D-010)

**Status:** QUEUED — next build task after Friday's FINAL H-FPL-05 score. Dropped off the plan twice before; may not be dropped again without an explicit operator decision recorded in decision_log (see D-010).
**Purpose:** the retrieval layer Stage 2 rule mining runs on; ends re-supplying of already-held videos/documents.

## Requirements (as issued)
1. Transcribe and ingest **every** training and breakdown video.
2. Resolve — or precisely list — the uncaptured Discord links.
3. Ingest the full training document set, the full historical Telegram archive as retrievable text, and all indicator captures.
4. Every corpus item carries: `source_id`, `source_class`, `source_tier`, `ingested_at`, `content_hash`, `provenance`, `supersedes`.
5. Ingestion is **idempotent**: re-submitting an ingested item returns `ALREADY_INGESTED`.
6. Provide a retrieval index.
7. Report corpus item counts by class and tier.

## Acceptance tests
- "What videos and documents do we hold?" returns a complete list.
- Re-submitting an ingested item returns `ALREADY_INGESTED`.
- An indicator query returns corpus material, not fresh analysis.

## Constraints
Read-only toward live stack; new research store only; gates unchanged (PAPER/PREVIEW/False/False, NOT_INTEGRATION_READY); no fitting; STOP AND REPORT on completion with full test counts (incl. skipped/deselected/xfail).

## Inputs already in hand
- Derived transcripts: `farouk_plus/derived/transcripts/*` (incl. breakdown_20260714, rescued_20260712), `derived/live_video_20260719/` (Sunday stream, full package).
- Indicator captures: `indicator_observatory/FP-INDICATOR-001..006`, `live_observations/FP-LIVE-OBSERVATION-001` (+ phone alert batch).
- Telegram: `campaign_extractor` signal_archive + prospective_evidence_v1.db (text + media index).
- Training docs: `FORMAL_DOCS_INGESTION_REPORT.md` lineage, FABLE5 training batches, video review docs.
- Martyn supplies: the consolidated material list for the one-and-only ingest (his action 3).
