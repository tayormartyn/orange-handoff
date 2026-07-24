# Causal Top-Down Reconstruction — XAU-F001 / F002 (research-only, pre-signal only)

Deterministic replay from **completed bars strictly before each signal** (forming candle excluded).
Sources: native D1 (2022-11-13→2026-07-14, 946 bars) + 1m (2026-07-08→07-15, 6524 bars), **Pepperstone
only**. No outcome, management, result-claim, or retrospective-video data entered the reconstruction
(compared against the published zone only AFTER freezing). Cannot touch follower/lanes/outcomes/pre-marks/
scorers/Constitution/live processes. Frozen: `topdown_reconstruction_F001_F002_v0_1.json` (hash 8c193218…).

## Phase 4-5 — Causal history available at each signal
| campaign | D1 | H4 | H1 | M15 | M5 | M1 |
|---|---|---|---|---|---|---|
| F001 (08:38:06Z) | 944 daily | 24 | 86 | 343 | 1029 | 5141 |
| F002 (13:26:21Z) | 944 daily | 25 | 91 | 362 | 1087 | 5429 |
All completed-before-signal; H4/H1/M15/M5 resampled from the causal 1m (UTC-floored), D1 native.

## Phase 5 — D1 context (both signals; ~3.7yr daily)
Directional bias (20-EMA on daily closes) = **BEARISH** at both signals; 944 completed daily bars;
external liquidity = recent daily highs/lows; premium/discount = **UNKNOWN** (no evidence-fixed dealing-range
definition → fail closed). Daily OB/FVG candidates listed in the register. Mitigation-age threshold UNKNOWN.

## Phase 6-8 — H4/H1/M15-M5 (per campaign)
**F001 (signal price 4020.09):** H1 latest structure = **BULLISH_BOS/CHoCH (broke 4006.31)** — a bullish
shift just before the long; Asia H **4034.21** / L **3983.23** (the 3983 low was swept then reclaimed).
M5/M15 sweep-then-reclaim of the Asia low is the execution context (DR-204). Direction implied by causal
structure = **LONG-consistent** (H1 bullish BOS), matching the published LONG.
**F002 (signal price 4084.58):** D1 bias BEARISH; H1 = BULLISH_BOS (broke Asia high 4034.21) i.e. price
rallied; **price rallied INTO a D1 BEARISH_FVG (4044.36–4090.83)** — shorting a rally into a daily bearish
imbalance, D1-bias-consistent = **SHORT-consistent**, matching the published SHORT.

## Phase 9-10 — Orange zones & comparison vs published (v0.2, red-teamed)
| | F001 | F002 |
|---|---|---|
| Published | 4007–4019 LONG | 4084–4094 SHORT |
| Signal price (completed 1m) | 4019.74 | 4083.91 |
| Candidate universe (all causal) | 378 | 381 |
| Orange primary (nearest-to-price) | **D1 BULLISH_OB 3944.49–4040.39** (overlap **$12**) | **D1 BULLISH_FVG 4022.89–4090.5** (overlap **$6.5**) |
| overlap verdict | **PARTIAL_MATCH** | **PARTIAL_MATCH** |
| direction | **N/A** — engine emits zones, not a direction | **N/A** |

**HONEST CAVEAT (post red-team):** these PARTIAL_MATCHes are **weak, largely built-in — NOT strong
corroboration.** The signal price is already *inside/at* the published zone when Farouk posts (he signals
at his zone), and the ranking is **nearest-to-price only** (fresh-first is inert — 99.7% of candidates
are mitigated with no defensible age threshold, so the only "fresh" zones are ancient far-away levels like
a 2554 OB). So "the nearest causal zone overlaps the published zone" is close to tautological. Do NOT read
the primary zone's OB/FVG polarity as a direction (F001's nearest is a *bullish* OB, F002's a *bullish*
FVG; the earlier "direction-consistent" narrative was a post-hoc fit and is withdrawn). What IS genuinely
established: the pre-signal MTF context is real and causal (D1 bias BEARISH; F001 H1 BULLISH_BOS broke
4006.31; Asia H 4034.21 / L 3983.23 swept) — but it does not, by itself, reproduce Farouk's zone SELECTION
or RANKING.

## Phase 11 — Rejected-level register (mandatory; top candidates — full set in JSON)
**F001 (18 candidates):** H4 BEAR_FVG 4018–4046 (INSIDE, primary) · H1 BEAR_FVG 4020–4042 (2.7p) ·
H1 BULL_FVG 4019.2–4019.6 (4.7p) · D1 BULL_OB 3942–4018 (19.2p) · H4 BULL_FVG 4006–4013 (67.8p) · … all
mitigated=True; ranked fresh-first then nearest.
**F002 (18):** D1 BEAR_FVG 4044–4090 (INSIDE, primary) · **H4 BEAR_FVG 4091–4108 (64.8p, just above the
published short)** · H4 BEAR_OB 4060–4072 · D1 BEAR_FVG 4115–4136 · … 
Each candidate carries tf/type/boundaries/body-basis/mitigation/price-relation/distance. **Ranking weights
UNKNOWN → alternatives retained, no fabricated score** (VR-15 fresh>mitigated + nearest neutral tiebreak
are the only orderings applied). Why each ranks below primary = distance/mitigation only; deeper rejection
logic = **UNKNOWN** (Farouk's private ranking).

## Phase 12 — Engine components built (research-only, disabled from strict follower)
`topdown_reconstruction.py`: causal MTF resample (D1 native + 1m→M5/M15/H1/H4), completed-before-signal
firewall, candidate-level register (OB+FVG, mitigation-state, price-relation, distance), fail-closed ranking,
Orange primary/alternative hypothesis, published-zone comparison. No scoring weights/thresholds invented;
cannot create orders, activate Smart Entry, or mutate live/campaign state.

## Rules supported / contradicted / UNKNOWN
- **SUPPORTED (weak, causal instance):** DR-204 (F001 Asia-low sweep is real, pre-signal), DR-201/VR-11
  (FVG/OB body zones exist near both published zones). These are consistent, NOT corroborative (see caveat).
- **UNKNOWN (fail closed):** ranking weights, premium/discount range, exact zone-boundary discretion,
  **mitigation-age threshold (makes fresh-first inert)**, A-grade formula, **the level-SELECTION function**.
- **CONTRADICTED:** none, but "consistency" here is weak (nearest-to-price ≈ published by construction).

## Red-team pass (read-only agent) — 3 MATERIAL findings, all FIXED
1. **signal_price used the forming 1m candle** (close post-signal) → fixed to the last COMPLETED 1m
   (F001 4020.09→4019.74; F002 4084.58→4083.91). 2. **Candidate pool silently truncated to 3-most-recent**
   (dropped 300+ D1 levels, recency-biased) → now the FULL causal universe (378/381), nearest-15 registered.
   3. **Degenerate ranking + over-claimed direction** → ranking relabeled NEAREST-TO-PRICE-only (mitigation
   is annotation, not a key), direction set to N/A, and the PARTIAL_MATCH explicitly downgraded to
   weak/built-in. Regressions: `tests_topdown_recon.py`. Clean categories confirmed by the agent: no
   Farouk-zone hint in the blind path, no provider mixing, correct resampling/timezone, no campaign
   conflation, no live/frozen mutation. Frozen v0.2 hash `79e8f0c4…`.

## Safety
Research-only; no post-signal/outcome/video data used; live processes + frozen artifacts untouched;
gates PAPER/PREVIEW/False/False; NOT_INTEGRATION_READY unchanged; no broker/demo/execution.
