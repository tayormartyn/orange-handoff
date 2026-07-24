# Farouk-Plus Forward Scoring Workflow v0.2 (Review-Only, Observation-Only)

**Mode: STEP 5 FORWARD SCORING WORKFLOW ONLY.** Date 2026-07-11.
This workflow applies detector v0.2 to **newly captured** XAU/Gold posts, forward-facing. It is
**observation-only**: no broker, no QST, no cTrader, no nano account, no copy trading, no demo/live
execution, no orders/permits/leases, no lot sizes, no risk sizing, no trade instructions, no gate changes.
Deterministic OHLC matching remains the sole outcome authority. Every machine-produced record passes the
ai_review fail-closed validator + the extended forbidden-token guard proven in the Step-4 replay
(4/4 negative checks). The live listener **PID 87988 is the only capture process and is never touched** —
this workflow only READS what it stores.

## 1. New-setup detection (read-only over the existing evidence store)

Daily (or on demand), query `prospective_evidence_v1.db` **read-only** (`file:...?mode=ro`) for messages
newer than the last processed rowseq where the raw text matches the gold-trades lane
(`"gold-trades" in raw_text`, author `seascalperfarouk`) and contains a trade-like entry pattern
(`XAU`/`gold` + `BUY|SELL` + a numeric zone `dddd-dddd` or `SL`). Non-entry messages (management,
results, commentary) attach to the most recent open setup thread of the same campaign. **A cursor file
(`farouk_plus/forward_cursor.json`) stores the last processed rowseq — append-only processing, no
reprocessing of anything as a signal.**

## 2. Evidence-pack construction (review-only)

Each detected setup becomes an evidence pack in the exact `ai_review` input schema (pack_id `XAU-F###-<date>`,
instrument, source_channel, messages[{message_id, timestamp_utc, raw_text}], media[{message_id, sha256,
path}] from `prospective_media_v1.db` where captured). Packs are validated by
`schema.validate_evidence_pack` before scoring. Screenshots are linked by sha256 only — never interpreted
as instructions.

## 3. Forward scoring (v0.2 — forward-available features ONLY)

| feature | source | weight |
|---|---|---|
| attempt_number / re_entry_flag (R2/R2b) | count of prior same-campaign entry announcements that day (explicit "re-enter" or same/near zone) | first attempt +1 · re-entry −1 · attempt ≥3 additional −2 |
| entry_time_utc → after_1530z_flag (R4b) | entry message timestamp | before 15:30Z +1 · after −1 |
| caution_language (f2∪f4) | entry-message text (safe-named; values may quote "low lot" etc., keys never contain forbidden tokens) | +1 |
| reason_stated (f7) | "Reason for the buy/sell" post, applied on arrival (label may upgrade once) | +1 |
| claim_quality (R6) | **only when prior claim history exists**: rolling inflation_ratio over the poster's PRIOR matched claims; >1.25 ⇒ claim_quality=DEGRADED ⇒ HUMAN_REVIEW_REQUIRED | routing, not score |

**Explicitly EXCLUDED from forward entry scoring (outcome-side / lookahead):** BE-stop language after
profit exists · realised MAE · realised MFE · any TP/SL touch knowledge · anything derived from OHLC after
the entry timestamp. These fields are recorded later in the ledger for diagnostics, clearly marked
`outcome_side=true`, and never feed a label.

**Labels (the complete allowed set):** `REJECT` · `WATCH` · `SHADOW_CANDIDATE_LOW` ·
`SHADOW_CANDIDATE_MEDIUM` · `HUMAN_REVIEW_REQUIRED` (override on missing fields, contradiction, or
DEGRADED claim quality). Score mapping as ruleset v0.1 (≤−2 REJECT · −1..0 WATCH · +1 LOW · ≥+2 MEDIUM).
Labels expire when the entry window passes; a stale label is re-marked `EXPIRED_UNREVIEWED`, never
presented as live.

## 4. Human-review routing

Every **non-REJECT** label is appended to the existing HR queue
(`stage_c_tooling/human_review_queue_v0_1.csv` convention, HR-####-F ids) with the pack, label, score, and
flags. REJECTs are logged in the ledger only (auditable, not queued). Nothing skips human review; no label
exceeds SHADOW_CANDIDATE_MEDIUM.

## 5. Daily checklist (each capture day, ~10 min)

1. **Audit**: read-only scan for new gold-trades messages since cursor; confirm listener PID 87988 alive
   (`Get-Process -Id 87988` — read-only; if dead, report to Martyn — do NOT restart from this workflow).
2. **Score**: build packs → validate → score v0.2 → emit labels through validator+guard.
3. **Media check**: confirm photos on the new messages have `MEDIA_CAPTURED` rows; list any failures.
4. **OHLC request**: append the day's required window (entry −60 min → 22:00Z, 1m, Pepperstone, UTC) to
   `farouk_plus/ohlc_export_requests.md` for Martyn (TradingView "Go to date" method; ~1 file/day).
5. **Outcome-match within 48h**: once the file lands, run the deterministic matcher (Day-2 semantics) and
   write the outcome into the forward ledger. If no OHLC after 48h → `outcome_status=PENDING_OHLC` (flagged,
   never guessed).
6. **Ledger append**: one record per setup in `forward_validation_ledger_v0_2.jsonl` (schema below),
   append-only.
7. **Weekly**: tally forward W/L/P per label tier vs the replay's in-sample numbers (out-of-sample drift
   check); note any TV-alert alignment (CHoCH/Sweep/A ids) when the indicator lane fires near an entry.

## 6. Forward evidence thresholds (from Day-6, restated)

≥ **15 forward-captured XAU trades** scored at entry time and outcome-matched · ≥ **10 alert-aligned**
examples if available · ≥ **5 sessions** · OHLC match within 48h wherever possible. Only when met does
out-of-sample evaluation of ruleset v0.1 happen — and only THAT evaluation may feed any future
demo-readiness *discussion*.

## 7. What this is NOT

Not execution. Not copy trading. Not a nano/broker/cTrader/QST connection. Not trade-ready and unable to
emit anything trade-shaped (validator + extended guard reject TRADE_READY / EXECUTE / ORDER / LOT_SIZE /
BROKER_ROUTE / ACCOUNT_ID / RISK_SIZE / COPY_TRADE / NANO / LIVE / DEMO_EXECUTE keys and labels — proven
by negative tests in Step 4). `NOT_INTEGRATION_READY` stays until governance explicitly lifts it; this
workflow has no path to change gates.

## Next step

Run the first daily cycle on the next capture day (first new gold-trades setup after 2026-07-10), producing
`XAU-F001-*` — while Step 6 (June 1–21 1m upgrade + 77-screenshot review) proceeds as data arrives.
