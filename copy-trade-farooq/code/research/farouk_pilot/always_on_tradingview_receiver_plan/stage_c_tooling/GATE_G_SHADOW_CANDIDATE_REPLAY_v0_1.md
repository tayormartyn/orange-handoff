# Gate G — Shadow Candidate Replay v0.1

**Mode:** OFFLINE REPLAY. `shadow_candidate_detector_v0_1` run over the 74 v0.2-classified Gate G events
(window 2026-07-08T22:15:04Z → 2026-07-09T09:51:02Z). **Candidate-only; nothing here is a trade
instruction or execution recommendation.**

## Summary counts

| candidate_type | count |
|---|---|
| ALIGNED_CHOCH_TO_A | 1 |
| SWEEP_TO_CHOCH_CONTEXT | 1 |
| BPR_TO_A_CONTEXT | 1 |
| **Candidates total** | **3** |
| CONTRADICTORY_CLUSTER (disqualified/noisy) | **20** |

Safety audit over all 23 records: `candidate_only=true` and
`execution_allowed=broker_execution_allowed=qst_allowed=order_intent=risk_sizing_allowed=false` on
**every** record; every `confidence` is LOW or MEDIUM (no HIGH).

## Candidate list

**1. ALIGNED_CHOCH_TO_A — confidence MEDIUM (best case)**
- `04:00:00Z CHOCH_UP → 04:12:01Z A_LONG` — direction_hint LONG, same instrument (XAUUSD) + timeframe
  (3), **no contradictory opposite-A inside the window**. Disqualifiers: none.
- This is the single cleanest lead→lag observation in the sample — and it matches the sequence-analysis
  watch-item exactly. **It is a watch candidate for a future shadow study, not a signal.**

**2. SWEEP_TO_CHOCH_CONTEXT — confidence LOW (context)**
- `23:45:06Z SWEEP_LOW → 00:03:01Z CHOCH_UP` — direction_hint LONG, within 30m. Warning: sweep raw
  carries no timeframe (`TIMEFRAME_MISSING`). Liquidity→structure context only.

**3. BPR_TO_A_CONTEXT — confidence LOW (context)**
- `05:33:01Z BPR_TAPPED → 05:42:01Z A_SHORT` — proximity within 15m. Warning: BPR_TAPPED is
  directionless; proximity only, not a directional lead.

## Disqualified / noisy clusters (20)

Contradictory clusters (opposite LONG & SHORT hints, ≥3 events, within 15m) — **flagged NOT to follow**.
Examples:
- `23:48:03Z..00:03:01Z : CHOCH_DOWN, CHOCH_UP, BULLISH_ENGULFING`
- `00:03:01Z..00:09:01Z : CHOCH_UP, BULLISH_ENGULFING, SWEEP_HIGH`
- `00:48:02Z..00:57:01Z : BULLISH_ENGULFING, BEARISH_ENGULFING, A_SHORT, CHOCH_DOWN, SWEEP_LOW`

20 such clusters vs 3 candidates — **the stream is dominated by directionally-ambiguous activity**.

## Best aligned CHoCH→A case (detail)

`04:00:00Z CHOCH_UP on XAUUSD 3` → `04:12:01Z A_LONG on XAUUSD 3` — 12 min apart, aligned LONG bias,
same symbol/timeframe, no contradicting A in between. Still **MEDIUM observation confidence only**:
n=1, no price/outcome data, no confirmation across sessions.

## Conclusion — trade-ready?

**No.** 3 candidates (only 1 at MEDIUM, the rest LOW context), swamped by 20 contradictory clusters,
from a single ~11.6 h window with no price/outcome data and zero A+ / A+++ / BPR-formed observations.
This replay produces watch-list observations for a possible **future** shadow study only. **No candidate
is trade-ready.**

## Safety confirmations

- Candidate-only throughout; no execution field / order intent / broker route / lot size / account ID /
  risk sizing / permit / lease / order.
- Offline over existing evidence; no R2 read, no deploy, no live connection.
- **`NOT_INTEGRATION_READY` unchanged.**
