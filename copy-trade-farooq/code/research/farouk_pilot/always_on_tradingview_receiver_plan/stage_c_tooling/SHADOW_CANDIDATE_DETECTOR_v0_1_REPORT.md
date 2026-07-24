# SHADOW CANDIDATE DETECTOR v0.1 — Report

**Mode:** OFFLINE SHADOW-CANDIDATE DETECTOR BUILD. Marks *possible study candidates* from classified
Farouk event sequences. **It creates no trade, order, permit/lease, or execution object.** No R2 read,
no deploy, no TradingView touch, no broker/QST.

## Files

- `shadow_candidate_detector_v0_1.py` — the detector (pure function over a list of dicts, no I/O).
- `test_shadow_candidate_detector_v0_1.py` — tests.

## Input

A chronological list of v0.2-classified events (each with `received_at_utc`, `raw_text`,
`event_family`, `event_type`, `direction`, `instrument`, `timeframe`, `confidence`).

## Output — candidate record fields

`candidate_id`, `detector_version` (`shadow_candidate_detector_v0_1`), `candidate_type`,
`window_start_utc`, `window_end_utc`, `events_in_sequence`, `direction_hint`, `confidence` (LOW/MEDIUM
only), `reason`, `disqualifiers`, `warnings`, and the hard-wired safety block: `candidate_only=true`,
`execution_allowed=false`, `broker_execution_allowed=false`, `qst_allowed=false`, `order_intent=false`,
`risk_sizing_allowed=false`.

## Candidate patterns

| Type | Rule | Confidence |
|---|---|---|
| **ALIGNED_CHOCH_TO_A** | CHoCH_UP→A_LONG or CHoCH_DOWN→A_SHORT within 15m | **MEDIUM** iff same instrument+timeframe and no contradictory opposite-A in window, else **LOW** |
| **SWEEP_TO_CHOCH_CONTEXT** | Sweep low→CHoCH_UP or Sweep high→CHoCH_DOWN within 30m | LOW (context-only) |
| **BPR_TO_A_CONTEXT** | BPR tapped→A_LONG/A_SHORT within 15m | LOW (context-only; BPR is directionless) |
| **CONTRADICTORY_CLUSTER** | opposite LONG & SHORT hints (≥3 events) within 15m | LOW — **disqualifier, NOT a candidate to follow** |

## Explicitly NOT promoted to trade candidates

Engulfing→A, ANY_ALERT clusters, A LONG/A SHORT alone, BPR tapped alone, Sweep alone. (A dedicated test
asserts Engulfing→A yields no candidate.)

## Design guarantees

- `confidence` is forced to LOW/MEDIUM — the detector **cannot** emit HIGH.
- `direction_hint` is a bias descriptor, never an order side.
- Every record carries the safety block; a test asserts all six flags are false on all records.
- Pure function, offline; no network, no broker/cTrader/QST import, no R2, no deploy.

## Test results — ✅ PASS

`python test_shadow_candidate_detector_v0_1.py` → **12 tests, OK.** Covers: CHoCH_UP→A_LONG and
CHoCH_DOWN→A_SHORT aligned (MEDIUM); CHoCH_UP→A_SHORT gives no aligned candidate; aligned-but-contradicted
downgraded to LOW; Sweep low→CHoCH_UP and Sweep high→CHoCH_DOWN context; BPR tapped→A context;
contradictory cluster detected; A-alone and Engulfing→A produce no trade candidate; all safety flags
false; summary-counts shape.

## Safety confirmations

- All outputs candidate-only; no trade instruction / order intent / broker route / lot size / account ID
  / risk sizing / permit / lease / order anywhere.
- Raw text preserved (events carry verbatim `raw_text`).
- **`NOT_INTEGRATION_READY` unchanged.**

## Status

v0.1 — implemented, tested (12/12), offline.
