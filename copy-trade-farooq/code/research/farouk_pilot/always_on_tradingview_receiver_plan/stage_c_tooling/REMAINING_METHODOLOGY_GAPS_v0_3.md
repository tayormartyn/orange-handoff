# Remaining Methodology Gaps v0.3

Update after adding the session policy + session/HTF resolvers. **Observation-only; grants nothing.**
`NOT_INTEGRATION_READY` unchanged.

## Status of each factor

| Factor | v0.2 | v0.3 status |
|---|---|---|
| FVG | ⚠️ proxy | ⚠️ proxy (unchanged; NEEDS_HUMAN_REVIEW) |
| Displacement | ⚠️ proxy | ⚠️ proxy (unchanged; NEEDS_HUMAN_REVIEW) |
| Local structure/swings | ⚠️ proxy | ⚠️ proxy (unchanged) |
| **Session** | ❌ missing | ⚠️ **proxy resolved, but STILL UNCONFIRMED** — corpus has no Asia window and the timezone is deliberately unresolved (BLOCKED). Cannot satisfy the scorer's session factor. |
| **HTF bias** | ❌ missing | ⚠️ **proxy resolved (15m/1h EMA proxy), NOT corpus-confirmed** — no SMC HTF rule exists (only a separate RESEARCH_ONLY Vishal 50-EMA method). Kept as descriptive context; not scored. |

## Still HARD-blocked

| Factor | Why still blocked |
|---|---|
| **Confirmed session** | Canonical timezone "deliberately NOT chosen" (G_TZ_UNRESOLVED = BLOCKED); Asia clock window absent from corpus; DST unhandled (TM-05 BLOCKED). |
| **Order block** | No detector yet (MISSING_ORDER_BLOCK_DETECTOR); not claimed. **This is the single most valuable next build** — OB is Farouk's highest-supported entry family. |
| **Confirmed HTF bias** | Corpus defines no SMC EMA/bias rule ("which EMA / what bias" unresolved). Also data-limited (1h insufficient in an 11.6h window). |
| **Grade formula** | Not exposed by the indicator; 0 A+/A+++ observed. |
| **Confirmed FVG / displacement thresholds** | Sizes/fill UNKNOWN in corpus — proxies stay NEEDS_HUMAN_REVIEW. |
| **Sample size / outcomes** | n=3, one session, mixed-to-poor. |

## Net effect on scoring

Session/HTF resolution **as proxies** did not change any label — all 3 remain `SHADOW_CANDIDATE_LOW`.
This is correct: proxies for BLOCKED/UNKNOWN factors must not raise readiness. The build-up (alert → chart
context → session/HTF) has now surfaced *every* proxyable factor; the remaining blockers are the ones the
corpus itself marks unresolved plus **order block** (buildable next) and **sample size**.

## Corpus reality check (reaffirmed by this survey)

- "Asia 00:00–07:00 UTC" — **not in corpus** (Asia is a level).
- Canonical timezone — **deliberately unresolved**, BLOCKED.
- SMC HTF-bias EMA/period — **none defined** (Vishal 50-EMA is a different, research-only method).
- Displacement size / FVG fill / BPR tolerance / OB tap-count / grade formula — **BLOCKED/UNKNOWN**,
  "do NOT invent."

## Verdict

**Nothing trade-ready.** Best label `SHADOW_CANDIDATE_LOW`. Next highest-value observation-only build is
the **order-block proxy** — see `NEXT_ORDER_BLOCK_RESEARCH_PLAN.md` — alongside timezone validation and
accumulating more outcome-matched windows.
