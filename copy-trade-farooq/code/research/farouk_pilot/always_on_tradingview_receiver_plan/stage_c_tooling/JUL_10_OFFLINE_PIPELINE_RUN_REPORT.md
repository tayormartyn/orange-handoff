# Jul-10 Offline Pipeline Run Report

**Mode: JUL-10 OHLC IMPORT + OFFLINE PIPELINE RESUME ONLY.** Observation-only, deterministic. No
broker/cTrader/QST/execution, no permit/lease/order, no gate change, no trade instruction. `NOT_INTEGRATION_
READY` unchanged. Date 2026-07-10. **Result: OHLC imported; 4 captures outcome-characterised; detector = 0
campaign sequences → EVENT-CHARACTERISATION ONLY (no shadow candidate).**

## Source CSV + import

- Source: `C:\Users\Marty\Downloads\PEPPERSTONE_XAUUSD, 1 (1).csv` (newest XAUUSD/Pepperstone/1m export,
  saved 2026-07-10 09:09 local). Columns `time(epoch),open,high,low,close,Bull Engulf,Bear Engulf,Volume,CRSI`.
- Cleaned → `price_data/XAUUSD_1M_2026-07-10_IMPORT_HERE.csv` (schema
  `timestamp_utc,open,high,low,close,source,timeframe`; source `PEPPERSTONE_TradingView_export`; `1m`).
- **787 candles.**

## OHLC coverage + data quality

- **Coverage: 2026-07-09T18:01Z → 2026-07-10T08:09Z (UTC).**
- Quality: **0 bad-OHLC rows** (all `high≥o/c/l`, `low≤o/c/h`); **1m spacing** (1 benign gap, minute-aligned);
  price range 4104.30–4135.40.
- **Coverage caveat:** the export ends **08:09Z**, short of the requested 09:30Z. This fully covers the
  120m windows of the 01:39Z, 03:51Z and 04:57Z captures, but the **07:09Z capture is PARTIAL** (only 15m/30m
  covered; 60m/120m left **null — not fabricated**). A later re-export (through ~09:30Z) would complete it.

## Classifier (`raw_farouk_text_classifier_v0_2`) — 4/4

| time | raw | event_type | direction |
|---|---|---|---|
| 01:39Z | CHoCH down (bearish) | `CHOCH_DOWN` | SHORT_HINT |
| 03:51Z | CHoCH down (bearish) | `CHOCH_DOWN` | SHORT_HINT |
| 04:57Z | A+ or better setup | `A_PLUS_OR_BETTER` | (none — grade) |
| 07:09Z | CHoCH down (bearish) | `CHOCH_DOWN` | SHORT_HINT |

## Detector (`shadow_candidate_detector_v0_1`) — 0 sequences

`{candidates_total: 0, disqualified_total: 0}`. No `ALIGNED_CHOCH_TO_A` / `SWEEP_TO_CHOCH_CONTEXT` /
`BPR_TO_A_CONTEXT` sequence forms (the A+ is a grade with no direction; the CHoCH-downs are not followed by a
directional A within window; no sweeps captured). **No shadow campaign candidate exists — no fabrication.**

## Outcome matcher (`outcome_matcher_v0_1`) — event characterisation (descriptive USD/oz, NOT PnL)

Each capture treated as a pseudo-anchor; excursions oriented to the hint (SHORT for CHoCH-down; A+ oriented
LONG for description only, per the matcher warning).

| event | anchor | hint | DQ | entry | 15m closeΔ | 60m closeΔ | 120m closeΔ | MFE120 | MAE120 |
|---|---|---|---|---|---|---|---|---|---|
| EVT-01 CHOCH_DOWN | 01:39Z | SHORT | FULL | 4112.22 | −3.79 | −11.83 | **−11.02** | +3.22 | −22.72 |
| EVT-02 CHOCH_DOWN | 03:51Z | SHORT | FULL | 4120.53 | +0.94 | +3.75 | **+7.50** | +12.34 | −1.53 |
| EVT-03 A_PLUS_OR_BETTER | 04:57Z | none→LONG | FULL | 4115.22 | −1.23 | −0.12 | **−1.78** | +5.00 | −7.03 |
| EVT-04 CHOCH_DOWN | 07:09Z | SHORT | PARTIAL | 4111.49 | −2.64 | null | null | null | null |

Reading (oriented to hint; +closeΔ = favourable to the hint):
- **EVT-01 (bearish) FAILED** — price rose ~11 against the short (closeΔ −11.02, MAE −22.72).
- **EVT-02 (bearish) WORKED** — price fell ~7.5, minimal adverse (closeΔ +7.50, MAE −1.53).
- **EVT-03 (A+, undirected)** — roughly flat/slightly down (closeΔ −1.78; MFE +5.0 / MAE −7.03).
- **EVT-04 (bearish) INCONCLUSIVE** — 15m −2.64 / 30m −0.32; 60m/120m not covered (data ends 08:09Z).

**No consistent edge** across the 3 CHoCH-down events (1 failed, 1 worked, 1 partial). n tiny, single session.

## Methodology scorer + Campaign State Machine — NOT FED

Detector produced **0 campaign candidates**, so there is no sequence to score or to run the Farouk Campaign
State Machine v0.1 on. Per the rules, **no candidate was fabricated** and no all-UNKNOWN state-machine record
was manufactured. (These four items are lone events, not campaign sequences.) The state machine remains
verified (11/11) and ready once a real sequence candidate appears.

## Journal updates

**None.** No proper outcome-matched *candidate* exists (detector = 0). `SHADOW_OBSERVATION_JOURNAL_v0_1.*`
unchanged (still SOJ-0001 LOW / SOJ-0002 WATCH / SOJ-0003 REJECT). The Jul-10 event characterisation lives in
this report, not the candidate journal.

## Review queue Batch 002

`HUMAN_REVIEW_QUEUE_BATCH_002.md` / `.csv` remain **0 candidates** (nothing reached `WATCH_ONLY` /
`SHADOW_CANDIDATE_*`; detector = 0). Updated to record the OHLC import + characterisation status.

## Safety confirmations

- Observation-only; deterministic; **no fabricated outcomes/candidates**; all matcher safety flags
  candidate-only / execution flags False.
- Gates `MODE=PAPER`, `LISTENER_MODE=PREVIEW`, `EXECUTION_ENABLED=False`, `CTRADER_EXECUTION_ENABLED=False`.
- No broker/cTrader/QST; no permit/lease/order; no shadow engine.
- **No TradingView alert touched; Worker not deployed; R2 not accessed** (used already-verified capture facts
  + the imported local OHLC). Telegram PREVIEW listener **PID 16608 running/untouched**.
- `NOT_INTEGRATION_READY` unchanged.

## Next step

Optional: a **re-export through ~09:30Z** to complete the 07:09Z capture's 60m/120m window. Otherwise,
continue the observation cycle — the capture lane needs **directional A signals following structure/sweep
within window** (an actual `CHoCH→A_SHORT` or `Sweep→CHoCH→A` sequence) to produce a reviewable shadow
candidate; lone CHoCH-down / A+-grade alerts do not form one. Keep accumulating toward the ≥30-candidate /
≥5-session bar. Observation-only.
