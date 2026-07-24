# Gate G — Event Sequence Analysis v0.1

**Mode:** OFFLINE SEQUENCE ANALYSIS. Built from the 74 v0.2-classified Gate G events (single capture
window 2026-07-08T22:15:04Z → 2026-07-09T09:51:02Z, ~11.6 h). **Everything below is candidate-only,
context-only. NO trade instruction, NO order intent, NO execution recommendation.** Confidence tags rate
*pattern-observation quality only*, never trade conviction.

## Method

For each candidate pattern, ordered chains were counted in rolling windows of **5 / 15 / 30 / 60 min**
(chain span = last event − first event ≤ window). Direction bias per event:
LONG = {SWEEP_LOW, CHOCH_UP, BULLISH_ENGULFING, A_LONG}; SHORT = {SWEEP_HIGH, CHOCH_DOWN,
BEARISH_ENGULFING, A_SHORT}; NEUTRAL = {BPR_TAPPED}. Single session, single symbol, **no price/outcome
data** — so no pattern can exceed LOW–MEDIUM observation confidence.

## Pattern counts by window

| Candidate pattern | 5m | 15m | 30m | 60m | Obs. confidence |
|---|---|---|---|---|---|
| Sweep → CHoCH | 1 | 1 | 1 | 4 | LOW |
| **Sweep → CHoCH → A** | **0** | **0** | **0** | **0** | — (never occurred cleanly) |
| CHoCH → A | 0 | 2 | 2 | 3 | LOW–MEDIUM |
| Engulfing → A | 11 | 15 | 20 | 23 | LOW (co-firing / noise) |
| BPR tapped → A (near) | 0 | 1 | 5 | 8 | LOW (BPR is neutral) |

### Same-direction vs contradictory clusters (≥3 directional events in window)

| Window | Same-direction clusters | Contradictory clusters |
|---|---|---|
| 5m | 4 | 7 |
| 15m | 9 | 22 |
| 30m | 9 | 40 |
| 60m | 8 | 62 |

Contradictory clusters dominate at every window ≥15m — the composite stream mixes LONG- and
SHORT-bias events densely, so a bias cannot be inferred from clustering alone.

## Candidate sequences (representative, context-only)

**Sweep → CHoCH (60m), e.g.**
- `23:45:06Z SWEEP_LOW (LONG) → 23:48:03Z CHOCH_DOWN (SHORT)` — window 23:45–23:48Z. Context only.
  **Direction hint: contradictory** (LONG sweep then SHORT structure). Confidence **LOW**.
  Warnings: sweep rows carry `TIMEFRAME_MISSING`; opposing bias within the chain.
- `00:09:01Z SWEEP_HIGH (SHORT) → 00:54:02Z CHOCH_DOWN (SHORT)` — window 00:09–00:54Z. Aligned SHORT
  bias but 45 min apart (weak coupling). Confidence **LOW**.

**CHoCH → A (30m), e.g.**
- `04:00:00Z CHOCH_UP (LONG) → 04:12:01Z A_LONG (LONG)` — window 04:00–04:12Z. **Aligned LONG** bias;
  cleanest directional chain in the sample. Direction hint: LONG (context only). Confidence
  **MEDIUM** (as an observation worth watching — **not** actionable).
- `09:42:02Z CHOCH_DOWN (SHORT) → 09:51:02Z A_LONG (LONG)` — window 09:42–09:51Z. **Contradictory**
  (SHORT structure then LONG signal). Confidence **LOW**. Warning: opposing bias.

**BPR tapped → A (30m), e.g.**
- `00:27:00Z BPR_TAPPED (neutral) → 00:51:02Z A_SHORT` — 24 min apart. BPR carries no direction, so
  this is proximity, not a directional lead. Confidence **LOW**.

**Engulfing → A (5m), e.g.**
- `22:27:00Z BEARISH_ENGULFING → 22:27:00Z A_SHORT` (same second) and
  `00:51:02Z BEARISH_ENGULFING → 00:51:02Z A_SHORT`. These frequently share a timestamp — **co-firing**,
  not lead→lag. High count is a noise/context signature, not a predictive sequence. Confidence **LOW**.

**Contradictory cluster (15m), e.g.**
- `23:48:03Z CHOCH_DOWN (SHORT), 23:57:02Z BPR_TAPPED, 00:03:01Z CHOCH_UP (LONG),
  00:03:01Z BULLISH_ENGULFING (LONG)` — SHORT then LONG within ~15 min. Confidence **LOW**; flagged
  as directionally ambiguous.

**Same-direction cluster (15m), e.g.**
- `22:15:04Z BEARISH_ENGULFING, 22:21:00Z BEARISH_ENGULFING, 22:27:00Z BEARISH_ENGULFING,
  22:27:00Z A_SHORT` — sustained SHORT-bias run. Confidence **LOW–MEDIUM** as *context*, not a trigger.

## What this tells us

- **Context-only families:** ENGULFING and BPR_TAPPED are context/noise — Engulfing co-fires with A
  signals (often same second) and BPR_TAPPED is directionless. Neither is a standalone trigger.
- **Combinations that may deserve future shadow-campaign review:** **CHoCH → A** with *aligned*
  direction (e.g. the 04:00Z CHoCH_UP → A_LONG case) is the most coherent lead→lag candidate. **Sweep →
  CHoCH** appears but often with opposing bias. These are watch-list items for a *future* shadow study,
  not signals.
- **Too noisy to act on:** Engulfing → A (co-firing), any short-window clustering (contradictory
  clusters outnumber same-direction ~2–8×), and BPR-proximity chains.
- **The textbook Sweep → CHoCH → A chain did NOT occur cleanly (0 across all windows)** in this sample.
- **Is there enough evidence to trade? → No. Not yet.** One ~11.6 h window, one symbol, no price or
  outcome/PnL data, contradictory clusters dominant, and the key ideal chain absent. This analysis
  produces observations only.

## Safety confirmations

- Candidate-only throughout; no trade instruction, order intent, broker route, lot size, account ID, or
  risk sizing anywhere.
- Raw text preserved as source of truth; direction values are bias *hints*, not order sides.
- Offline over existing evidence; no R2 read, no deploy, no live connection.
- **`NOT_INTEGRATION_READY` unchanged.**

## Status

Sequence analysis v0.1 — complete, offline, observation-only. Feeds the evidence base; enables nothing.
