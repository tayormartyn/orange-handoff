# Fable 5 — Farouk Training Recovery Index v1

**Mode: TRAINING RECOVERY INDEX ONLY — no reprocessing, single-session.** Observation-only. Date 2026-07-11.
Listener PID 87988 untouched. Nothing moved/deleted; Downloads inventoried only. Machine-readable:
`fable5_farouk_training_recovery_index.json`. Gates `PAPER/PREVIEW/False/False`; `NOT_INTEGRATION_READY`
unchanged.

## 1. Headline: the Sonic/4.8 corpus survives on disk — do NOT re-upload

The prior sessions wrote their work down thoroughly. Fable 5 can access, via files:

| layer | what exists | where |
|---|---|---|
| **Education register** | **33 FP-EDU records (001–004, 007–035)** with completeness/provenance/confidence per item | `educational/CORPUS_QA_v0.1/EDUCATION_MASTER_SOURCE_REGISTER_v0.1.{csv,json}` |
| **Method specs** | METHODOLOGY_SPEC v0.1/v0.2/v0.2.1 + LEVEL_CONSTRUCTION_SPEC v0.1/v0.2 | `specifications/` |
| **Synthesis v0.3** | METHODOLOGY_CANDIDATE, **RULE_LEDGER (jsonl)**, STATE_MACHINE_CANDIDATE v0.2, SETUP_FAMILY_SPECIFICATIONS, CROSS_EVIDENCE_RULE_MATRIX, **CONTRADICTION_ADJUDICATION**, INDICATOR_VS_DISCRETIONARY_MATRIX, PROMOTION_READINESS_MATRIX, UNRESOLVED_BLOCKERS | `synthesis_v0.3/` |
| **Campaign dossiers** | FP-CAMPAIGN-001…004 JSON dossiers + raw images + **3 raw breakdown videos** (001–003 .mov) | `dossiers/`, `raw/images/`, `raw/videos/` |
| **Indicator observatory** | FP-INDICATOR-001…004: inventory, claims, session map, visual index, comparison + **alert-conditions screenshot** + the Jul-5 indicator-update video (220MB) | `indicator_observatory/`, `raw/farouk_playbook_indicator_update/` |
| **Transcripts** | FP-EDU-007 full transcript (94KB) + 90 ref frames; Live-with-Farouk Jul-5 transcript + frames; OCR TRANSCRIPTIONS.md batches; PDF text extractions | `educational/FP-EDU-007/`, `raw/live_with_farouk_2026-07-05/_analysis/`, batch dirs |
| **Docs (PDFs)** | FP-EDU-002 Playbook (22pp, text extracted), FP-EDU-003 Trading Guide (12pp), FP-EDU-004 OB Strong-vs-Weak, Candlestick Patterns, compiled Farouk Education | `raw/documents/`, `education_batches/pdf_batch_02/` |
| **Claims/rights** | educational_claims.csv, rights_register.csv, asset_manifest.csv, CLAIMS_LEDGERs | `research/farouk_pilot/` + batch dirs |
| **Sonic-era stage-C tools** | methodology factor map + scorer, OB proxy policy, session policy, HTF bias resolver, state machine v0_1, HR system | `stage_c_tooling/` |

**Raw videos still local: 7** — FP-CAMPAIGN-001/002/003 breakdowns, Live Jul-5 (614MB, transcript exists),
indicator-update Jul-5 (220MB), + Downloads: Live Jul-10 + Schermopname Jul-8 (both Fable-reviewed today).

## 2. Per-item classification (summary; full table in the JSON)

- **FULLY_INGESTED / METHOD_RULES_EXTRACTED:** FP-EDU-002/003/004 (PDFs, rules in register+specs);
  FP-EDU-008–035 Discord education batch (OCR'd, claims ledgers, contradictions logged);
  FP-CAMPAIGN-001–004 (dossiers); FP-INDICATOR-001 (inventory+claims).
- **TRANSCRIPT_EXISTS + PARTIALLY_INGESTED (needs Fable-5 review):** FP-EDU-001/Live Jul-5 (276KB
  transcript never Fable-reviewed), FP-EDU-007 (EMA method — separate family, low priority).
- **RAW_VIDEO_EXISTS (no transcript):** FP-CAMPAIGN-001/002/003 breakdown videos (dossiers cover the
  trades; video audio never transcribed), indicator-update Jul-5 video (screenshots ingested; audio not).
- **FULLY_INGESTED (Fable 5, today):** FP-LIVE-VIDEO-EXPLAINER-001/002.
- **MISSING_OR_SESSION_ONLY:** FP-EDU-005/006 (IDs never registered — likely unassigned, check
  NEW_SOURCE_RECORDS), FP-CAMPAIGN-004 raw video (dossier exists, no .mov), EDU-033's NY leg (PDF cut),
  numeric displacement size (EDU-035 explicitly deferred), any un-written session reasoning (unknowable,
  but the file corpus is unusually complete).

## 3. Topic coverage matrix (evidence / rule / in-Orange / Fable-review-needed)

| topic | evidence | rule extracted | in Orange | needs Fable 5 |
|---|---|---|---|---|
| Asia H/L | EDU-033, videos, indicator | ✔ | ✔ 8F recipe, Lane 6 | — |
| London/US lows | EDU-033 (NY leg cut), video 001 | partial | ✔ 8F | minor |
| Liquidity sweep | EDU-030/014/015 | ✔ families | ✔ detector context | — |
| OB/FVG/BPR | EDU-002/004/011/012 + OB proxy policy | ✔ | ✔ Lane-6 sources | — |
| Mitigation | EDU-008 (no numeric depth) | partial | 8F level-type tag | **✔ join EDU-008 + video stop-width** |
| Strong/weak H/L | EDU-009/004 | ✔ attribute | not scored | ✔ candidate feature |
| BOS/CHoCH | EDU-010/016/021 + state machine | ✔ **but 016 vs 021 contradiction on candle-close** | ✔ context | **✔ adjudicate contradiction** |
| Displacement/retest | EDU-035 (numeric deferred) | ✘ numeric | R3 rejected-as-defined | **✔ weak topic** |
| HTF bias | EDU-024 + htf_bias_resolver | partial | R5 zero-weight flag | ✔ forward |
| Session timing | EDU-031/032/033 + session policy | ✔ **NY 13:30–15:00 UTC matches our NY-open winners** | R4b adopted | — |
| Invalidation/stop-width | EDU-028 (OTE: stop outside OTE, ≥2R) + videos | partial | 8F PROMISING | **✔ synthesize EDU-028 + video lessons** |
| Mitigated→wider stop | video-only | ✘ | 8F NEEDS_FORWARD | ✔ forward |
| Re-entry logic | video 001 doctrine + June empirics | ✔ | **R2/R2b adopted** | — |
| Layered entries | **EDU-003 "3-pt entry/BE+50/partials"** + video tutorial | ✔ | 8D schema; **independently validates Model B's +50 BE parameter** | — |
| Close-worst/hold-best | EDU-003 + 8D | ✔ | ✔ | — |
| SL-to-entry | EDU-003 BE+50 | ✔ | Model B + 8C timing capture | — |
| Multi-position mgmt | EDU-003 + 8D audit | ✔ | ✔ | — |
| Indicator price levels | FP-INDICATOR-001 + alert-conditions png + panel frames | ✔ inventory | 8F extraction feature | **✔ Lane-6 build input** |

**Well covered:** sessions, liquidity/sweeps, OB/FVG/BPR, layered-entry/management, re-entry, Asia frame.
**Weak/missing:** numeric displacement, mitigation depth, stop-width mapping (the Lane-6 binding
constraint), strong/weak-level scoring, BOS candle-close contradiction.

## 4. Already inside Orange (mapping)

RULESET v0_1 (R2/R2b/R4b/R6 + caution/reason features) · detector v0.2 (replayed) · R6 six-lane expectancy
(+fill_lag backlog) · Lane 6 (+indicator-price sources, invalidation track) · Cycle-002 schema
(8C timing + 8D legs + 8F level-type/feed/indicator capture) · Step-8F integration note. The Sonic-era
**synthesis_v0.3 rule ledger and state machine are NOT yet diffed against the Farouk-plus ruleset** — that
is the main un-merged inheritance.

## 5. Recovery plan — top 5 next training items (no re-upload needed for any)

1. **Diff `synthesis_v0.3/FAROUK_METHODOLOGY_RULE_LEDGER_v0.3.jsonl` + CONTRADICTION_ADJUDICATION against
   FAROUK_PLUS_RULESET_v0_1** — merge or retire each Sonic rule explicitly (incl. the EDU-016 vs 021
   BOS candle-close contradiction).
2. **FP-INDICATOR-001 claims + `farouk_indicator_alert_conditions.png`** — enumerate the exact alert
   conditions for the Lane-6 pre-mark builder (the machine-readable level source).
3. **FP-EDU-003 Trading Guide re-read (Fable)** — refine lane-4 playbook parameters from the source doc
   (3-pt entry, BE+50, partials); risk-% content excluded by policy.
4. **EDU-028 (OTE) + EDU-035 (displacement)** — synthesize with the video stop-width lessons into
   `stop_width_by_level_type` v0.1 (the weak-topic pair).
5. **FP-EDU-001 / Live Jul-5 transcript (276KB, on disk, never Fable-reviewed)** — the long teaching
   session; mine for stop-width, mitigation depth, and displacement numerics specifically.

## 6. Safety confirmation

Read-only inventory; no reprocessing; nothing moved/deleted; no execution built
(broker/QST/cTrader/nano/copy/demo/live absent); no execution fields recorded; no permits/leases/orders;
gates unchanged; listener PID 87988 running; no TradingView/Worker/R2/secret action.
`NOT_INTEGRATION_READY` unchanged.

## Next step

Item 1 of the recovery plan (rule-ledger diff) is the highest-value offline task while awaiting
gold-trades activity for Cycle 002.
