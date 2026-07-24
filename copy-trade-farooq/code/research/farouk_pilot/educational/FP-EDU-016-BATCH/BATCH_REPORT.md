# FP-EDU-016 BATCH — BATCH REPORT

## Source
`research/farouk_pilot/education_batches/batch_01` — **77 images** (Windows Snipping-Tool names). Distinct from
`evidence_images/batch_01` (the 3-image repair set). **9** are exact-hash duplicates of already-processed
FP-EDU-008–015/repair images; **68** transcribed (RapidOCR, spot-verified). Originals unmodified.

## Method
Recursive inventory + SHA256 for all 77. Text read via RapidOCR (verbatim-verified on Mitigation + Inducement).
Posts reconstructed from **visible titles, author (SeaScalper-Farouk WR), Discord timestamps, numbered steps,
overlapping text, and chronological order**. Generic filenames were **not** used as identity. Cropped/obscured
text was **not** invented (`[cropped]`/partial noted).

## Outputs (this folder)
`SOURCE_MANIFEST.json` · `IMAGE_SOURCE_MAP.csv` (all 68 mapped) · `TRANSCRIPTIONS.md` · `CLAIMS_LEDGER.jsonl`
(26) · `FINDINGS.md` · `CONTRADICTIONS.json` · `CAMPAIGN_CROSS_REFERENCE.json` · `STATE_MACHINE_IMPACT.json` ·
`UNRESOLVED_QUESTIONS.md` · `BATCH_REPORT.md`.

## Result
- **12 new posts** assigned **FP-EDU-016 … FP-EDU-027**.
- **Provenance resolved** for FP-EDU-008 (Mitigation, CONFIRMED), 010, 013 (author+timestamp), and fuller
  bodies for 009/011/012/014/015. (Recorded in this batch's manifest; the original FP-EDU-008–015 records and
  frozen dossiers were **not overwritten**.)
- References re-seen (campaign-004, indicator-overview, STX/LINK/cluster, BTC example) mapped, not re-IDed.

## Completeness / confidence
Readable and sufficiently complete to ingest. Author identity HIGH (visible on the headered posts). Per-post
timestamps HIGH where in-frame, otherwise MEDIUM. Transcription = OCR spot-verified; no wording invented.

## Guardrails
No detector code; nothing wired to QST; no risk/broker/execution/permit/lease change. **NOT modified:**
FAROUK_METHODOLOGY_SPEC_v0.2.1, FAROUK_STATE_MACHINE_SPEC_v0.1, frozen campaign dossiers, the prior
FP-EDU-008–015 records, FP-EDU-007 EMA records, and the [kyle]/SpaceMan indicator records.
