# training-data — manifest only

Large media is NOT included in this handoff (videos, audio, images stay on the
source machine / in the permanent corpus store).

- `corpus_index_v1.jsonl` — the authoritative corpus manifest (47 items as of
  2026-07-21: 32 video / 7 doc / 2 audio / 1 chat / 4 indicator captures /
  1 transcript; each row carries sha256, source path, tier P/A/L).
- Permanent store on the source machine: `signal-terminal/research/farouk_pilot/corpus/`
  (ingest tool: `corpus_ingest.py`, idempotent by sha256).
- Transcripts live under `corpus/transcripts/` (small.en + domain prompt;
  see quality_gate_1b.py notes — normalize mishears at mining time, never
  auto-edit transcripts).
- Raw Telegram evidence (message + media DBs under `data/`) is deliberately
  excluded: it is account-derived evidence, not shareable training media.
