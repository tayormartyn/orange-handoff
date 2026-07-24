# Remaining Methodology Gaps v0.2

Update to v0.1 after adding the chart-context extractor. **Observation-only; grants nothing.**
`NOT_INTEGRATION_READY` unchanged.

## What v0.2 closed (as PROXIES only)

| Factor | v0.1 | v0.2 status |
|---|---|---|
| FVG | ❌ missing | ⚠️ **proxy** (`fvg_candidate`, NEEDS_HUMAN_REVIEW; fill rule UNKNOWN) |
| Displacement | ❌ missing | ⚠️ **proxy** (range vs 20-ATR ratio, NEEDS_HUMAN_REVIEW; size threshold UNKNOWN) |
| Local structure/swings | ❌ missing | ⚠️ **proxy** (crude BOS/CHoCH + swing high/low; does not override raw alert) |
| Session | ❌ missing | ⚠️ **proxy** (`*_UTC_PROXY`, TIMEZONE_POLICY_UNCONFIRMED — still not *confirmed*) |

## What remains a HARD gap

| Factor | Status | Why still blocked |
|---|---|---|
| **Session (confirmed)** | ❌ | Chart→UTC timezone unresolved; proxy bucket cannot satisfy the scorer's session factor |
| **Order block** | ❌ | Deliberately not claimed (MISSING_ORDER_BLOCK_DETECTOR); needs a validated OB detector |
| **HTF / EMA bias** | ❌ | No 4H/Daily/EMA feed (MISSING_HTF_DATA); single 1m file only |
| **BPR geometry** | ❌ | Needs opposing-FVG overlap detector (only event-type BPR seen) |
| **Grade formula** | ❌ | Not exposed by the indicator ("do NOT invent"); 0 A+/A+++ observed |
| **Confirmed FVG / displacement thresholds** | ❌ | Corpus marks sizes/fill UNKNOWN — proxies stay NEEDS_HUMAN_REVIEW |
| **Sample size / outcomes** | ❌ | n=3, one session, mixed-to-poor outcomes |

## Net effect on scoring

Adding proxies raised methodology_scores (e.g. SWEEP_TO_CHOCH 0.37→0.59) but **every candidate stayed
`SHADOW_CANDIDATE_LOW`** — the ceiling caps hold because confirmed session and order block are still
missing and outcomes are not favourable. This is the intended, honest behaviour: **proxies inform, they
do not unlock**.

## Corpus reality check (unchanged)

Displacement magnitude, FVG size/fill, BPR tolerance, OB mitigation/tap-count, grade formula, confluence
count, and session timezone remain **BLOCKED/UNKNOWN — "do NOT invent."** Proxies are labelled
accordingly and never promoted to confirmed primitives.

## Verdict

**Nothing trade-ready.** Best label `SHADOW_CANDIDATE_LOW`. Next: validate the timezone→session mapping
and build an OB/HTF proxy (still observation-only) — see `NEXT_CHART_CONTEXT_COLLECTION_PLAN.md` — while
accumulating more outcome-matched windows toward the (unmet) evidence threshold.
