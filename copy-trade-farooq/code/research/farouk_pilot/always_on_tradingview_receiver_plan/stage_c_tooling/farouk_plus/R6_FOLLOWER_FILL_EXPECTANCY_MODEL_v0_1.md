# R6 Follower-Fill Expectancy Model v0.1 (Design)

**Mode: STEP 7 FOLLOWER-FILL EXPECTANCY DESIGN ONLY.** Observation-only, analytic-only. Date 2026-07-11.
This model evaluates **what a follower could realistically have captured from the posted information** —
never what to do. It produces review-only expectancy numbers and claim discounts; it can never emit an
execution artefact (forbidden outputs below). Deterministic OHLC remains the authority for every price
fact. Listener PID 87988 untouched; gates `PAPER/PREVIEW/False/False`; `NOT_INTEGRATION_READY` unchanged.

## 1. Why this model exists (the Step-6/6A discovery)

Farouk's **claims track his own private fills, which systematically differ from the posted zones** (he
market-fills at post time; zones are follower instructions). Three quantified cases:

| case | Farouk (widgets) | follower (posted info) | divergence |
|---|---|---|---|
| **J24** | SHORT 4132.02 → +170.3p claimed at 12:14 (exact); MFE 267p | no entry post existed; post-time fill ≈4128.4 (10:25Z widget moment); the 10:25Z "sl to entry" instruction → **scratched ~0p at 10:34Z** when price returned to the fill, BEFORE the 267p move | **his +170p vs follower ~0p** — the literal instruction cost the whole move |
| **J30** | LONG 4027.37 (below the posted zone 4035–4045) → "240 pips" TRUE from his fill | posted-zone fills 4035–4045: max MFE **175p**; TP1 4050 partials only; sl-to-entry (11:57Z) scratched the runner ~13:50–14:00Z; holders of the posted SL 4010 were stopped 14:11Z | **his 240p (true) vs follower ≤175p, mostly scratch** |
| **J11** | LONG 4056.64 → realised **629p** (exit widget) | no zone posted; post-time proxy fill ≈ his fill (both ~4056); follower ≈600–660p max | divergence here is **claim-vs-realised**: "800 pips" ≈ +27% over his own realised — inflation affecting everyone |

Conclusion: **headline claims ≠ his outcomes ≠ follower outcomes.** Expectancy must be computed on the
follower lanes.

## 2. The five outcome lanes (always kept separate)

1. **farouk_fill_outcome** — from position widgets when screenshots exist. Descriptive only.
2. **posted_zone_follower_outcome** — limit fills inside the posted zone (Day-2/4/5 matcher semantics:
   achievable-fill capped at zone edges). Primary lane when a zone was posted.
3. **post_time_follower_outcome** — market fill at the first bar close after the entry post (for
   zone-less or already-running calls). Secondary lane.
4. **management_instruction_follower_outcome** — lanes 2/3 fills with the posted instructions applied
   literally and timestamped: partial at TP1/stated level, "sl to entry" at instruction time (→ scratch
   modelling), "close worst / hold best" as fraction transfers. **This is the realistic lane and the one
   expectancy is computed on.** Position fractions are dimensionless shares of one abstract unit — no
   sizing of any kind.
5. **headline_claim_outcome** — the claimed pips. Reference only; always discounted:
   `claim_discounted_pips = min(claimed, lane-2/3 achievable)`, `inflation_ratio = claimed / realised-or-achievable`.

## 3. Record fields (per setup; forbidden-token-safe names)

`setup_id · posted_time_utc · posted_zone · farouk_fill_if_known (+source sha256) · zone_touch_time ·
post_time_market_price · realistic_follower_fill_low / high / median (zone edges + post-time price) ·
management_instruction_times [(instruction, ts)] · sl_to_entry_effect (NONE | SCRATCHED_AT_ts |
SURVIVED) · tp1_reachable_from_follower_fill (bool + ts) · tp2_reachable_from_follower_fill ·
max_follower_mfe_pips · max_follower_mae_pips · headline_claim_discount (claimed, discounted,
inflation_ratio) · follower_outcome_status (FOLLOWER_WIN | FOLLOWER_SCRATCH | FOLLOWER_LOSS |
FOLLOWER_PARTIAL | UNCLEAR) · divergence_vs_farouk_pips · notes`

All records pass the ai_review fail-closed validator + extended guard. **Forbidden outputs (keys or
labels): TRADE_READY · EXECUTE · ORDER · LOT_SIZE · BROKER_ROUTE · ACCOUNT_ID · RISK_SIZE · COPY_TRADE ·
NANO · LIVE · DEMO_EXECUTE** (superset enforcement as in detector v0.2; safety stamp from the validator
only).

## 4. Expectancy definition (review-only)

Per setup: `follower_pips = Σ fraction_i × (exit_i − fill)` over the lane-4 simulation (SHORT sign
inverted), with fills from lane 2 (median zone fill) or lane 3 when no zone. Portfolio expectancy =
mean/median of follower_pips across setups, reported with the scratch rate and the divergence-vs-Farouk
distribution. **Numbers are descriptive review metrics** for the CONTINUE decision and human review —
never thresholds that trigger anything.

## 5. Retrospective verdicts for the three cases (design-stage, from already-computed data)

- **J24 → FOLLOWER_SCRATCH (~0p)** vs his +170p/267p MFE. Divergence ≈ −170 to −267p.
- **J30 → FOLLOWER_PARTIAL (TP1 partials ~15–50p, runner scratched; ≤175p best-case)** vs his true 240p.
- **J11 → FOLLOWER_WIN (~600–660p)**, close to his 629p; headline 800p discounted (ratio ≈ 1.27).

Pattern: follower capture is bounded by (a) zone-vs-his-fill divergence and (b) the literal "sl to entry"
instruction, which converts many of his wins into follower scratches. **The follower expectancy question —
"is the edge capturable from the posted information alone?" — is now the central open question of the
sprint**, and it is answerable deterministically once lane-4 is computed across all 34 matched setups.

## 6. Classification & forward use

**R6 (with follower-fill lanes): PROMISING_SCORING_FEATURE — ADOPTED as the expectancy engine**, with the
divergence-distribution component marked NEEDS_FORWARD_EVIDENCE (3 quantified cases; widgets appear only
when he posts them). Forward (Cycle 002+): every XAU-F record gets lanes 2–4 computed at outcome-matching
time; claims are discounted before entering claim_quality; a large his-vs-follower divergence or
inflation_ratio > 1.25 routes the setup to HUMAN_REVIEW; OHLC windows are requested exactly as today.
Never an execution signal.

## 7. Safety confirmation

Design + retrospective analysis of already-validated data only. No broker/QST/cTrader/nano/copy/demo/live
execution; no permits/leases/orders; gates unchanged; listener PID 87988 running (start 2026-07-10
21:54:45 unchanged); no TradingView/Worker/R2/secret action; nothing trade-ready.
`NOT_INTEGRATION_READY` unchanged.

## Next step

Implement lane-4 computation over the 34 matched setups (offline script, validator-guarded) to produce the
first **follower-expectancy table** — the number that actually decides whether the Farouk lane is worth
following from posted information — and run forward Cycle 002 when new gold-trades activity arrives.
