# Classifier v0.1 — Gate G Replay Report

**Mode:** OFFLINE CLASSIFICATION PASS ONLY. `raw_farouk_text_classifier_v0_1` was replayed over the
existing Gate G captures loaded from local evidence. **No R2 read, no temp branch, no Worker deploy, no
TradingView touch, no broker/QST/execution.**

## Source of the raw texts

The 74 Gate G captured records were already held locally (full JSON records from the earlier Gate G
offline analysis, including `raw_payload`, `received_at_utc`, `event_id`). Object keys were reconstructed
exactly as the Worker writes them: `events/YYYY/MM/DD/<event_id>.jsonl` (the secret path is never stored;
provenance is `/tv/<redacted>`). **No R2 object read was required, so no temporary read/list branch was
added.**

## Result

- **Raw events classified: 74 / 74.**
- **Unknown / unclassified: 0.** Every capture matched a known Farouk family.
- Window: 2026-07-08T22:15:04Z → 2026-07-09T09:51:02Z.

### Family distribution (see summary for full counts)

| event_family | count |
|---|---|
| ENGULFING | 27 |
| A_SIGNAL | 24 |
| LIQUIDITY_SWEEP | 10 |
| BPR | 8 |
| STRUCTURE (CHoCH) | 5 |

- **A+ / A+ or better: 0. A+++: 0. BPR formed: 0.** (None present in the Gate G sample — consistent
  with the daily report v0 and with H1 not yet having fired.)
- Confidence: 64 rows at 0.9 (family + instrument + timeframe); 10 rows at 0.6 (see finding below).

## Key finding — Sweep alerts use a different raw format

The 10 Sweep captures are **not** in the `... on XAUUSD 3` shape. Their real raw text is:

- `Farouks Playbook: Sweep low (bullish) on XAUUSD`
- `Farouks Playbook: Sweep high (bearish) on XAUUSD`

i.e. an inline `(bullish)`/`(bearish)` bias tag and **no trailing timeframe number**. The v0.1 extractor
requires the `on <SYM> <TF>` pair, so for these rows it returns `instrument=null`, `timeframe=null`, plus
the warning `instrument/timeframe pattern 'on <SYM> <TF>' not found`, and confidence 0.6. This is
**correct, faithful behaviour** — the classifier flags the gap instead of guessing a timeframe. The
event_family/event_type/direction are still classified correctly, and the assigned direction hints
(`SWEEP_LOW → LONG_HINT`, `SWEEP_HIGH → SHORT_HINT`) match the raw's own `(bullish)`/`(bearish)` tags.

**v0.2 recommendation (not done in this pass):** add an instrument-only extractor (`on <SYM>` with no
TF) so `XAUUSD` is captured while `timeframe` stays null + warning. The classifier was left unchanged
here because this is a classification-only pass and its unit suite is locked at 16/16.

## Candidate-only watchlist (descriptive; NO execution recommendation)

Grouped by the observation lens only. **None of these is a signal to act. No execution recommendation is
made or implied.**

- **A signal events (A_SIGNAL, 24):** A LONG 10 / A SHORT 14. The graded trade-idea family; the
  ungraded "A" fires often. The dedicated **A+** grade (H1 mirror) was **0** in this sample.
- **Structural context (STRUCTURE / CHoCH, 5):** CHoCH DOWN 3 (SHORT_HINT) / CHoCH UP 2 (LONG_HINT).
  Low-volume structure-shift context; CHoCH DOWN is the H2 mirror target.
- **Liquidity sweep events (LIQUIDITY_SWEEP, 10):** Sweep high 6 (SHORT_HINT) / Sweep low 4 (LONG_HINT).
  Moderate-volume liquidity context.
- **Excluded / noisy context (not for continuous mirroring):** ENGULFING 27 and the ungraded A_SIGNAL
  volume together ≈ 69% of captures — high-frequency context, low standalone signal. BPR **tapped** 8
  is context, not the rarer BPR **formed** (0). These are recorded but flagged noisy.

## Safety confirmations

- **Raw text preserved as source of truth** — every table row shows the byte-exact `raw_text`; the
  classifier matched on a local copy and never altered the original.
- **All outputs candidate-only** — a programmatic check confirmed `candidate_only=true` and
  `execution_allowed=broker_execution_allowed=qst_allowed=false` for **all 74** rows.
- **No execution field / broker route / lot size / account ID / risk sizing / permit / lease / order**
  appears anywhere in the outputs or reports.
- **No I/O to any live system:** no R2 read, no temp branch, no deploy, no broker/cTrader/QST connection.
- **`NOT_INTEGRATION_READY` unchanged.**

## Outputs

- `GATE_G_CLASSIFIED_EVENT_TABLE_v0_1.md` — 74-row chronological classified table.
- `GATE_G_CLASSIFICATION_SUMMARY_v0_1.md` — counts by family / type / direction / confidence + unknown.
- `CLASSIFIER_v0_1_REPLAY_REPORT.md` — this report.

## Status

Replay complete. 74/74 classified, 0 unknown, all candidate-only. One faithful data finding (Sweep
format) logged with a v0.2 recommendation. Feeds the observation/evidence base only.
