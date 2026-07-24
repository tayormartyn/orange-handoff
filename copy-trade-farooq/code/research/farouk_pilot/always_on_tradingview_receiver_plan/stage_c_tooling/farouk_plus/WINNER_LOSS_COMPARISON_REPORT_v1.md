# Farouk-Plus Shadow Engine Step 1 — Winner/Loss Comparison Report v1

**Mode: STEP 1 WINNER/LOSS COMPARISON ONLY.** Observation-only, review-only, offline. Date 2026-07-11.
Listener PID 87988 untouched. Deterministic OHLC matching remains the authority (all outcome statuses come
from the Day-2/4/5 matchers); this analysis adds derived features and rule tests, promotes nothing to
trade-ready, and builds no execution. Gates `PAPER/PREVIEW/False/False`; `NOT_INTEGRATION_READY` unchanged.

**Data:** `winner_loss_comparison_v1.json` — 33 matched trades (29 June + 4 July; J24 excluded, no numeric
entry), normalised features per trade (zone, SL, attempt number, session, media, claim accuracy) + price
features recomputed deterministically from the imported 1m/5m exports (MFE/MAE from zone mid over
signal→+6h; displacement timing; 4h pre-traded check). Groups: **20 VERIFIED_WIN · 6 losses (3 verified SL
+ 3 self-admitted manual cuts J03/J08/J23) · 7 non-loss PARTIALs** (2 no-zone setups carry limited features).

## 1. What actually separates winners from losses

| feature | winners (20) | losses (6) | partials (7) |
|---|---|---|---|
| MAE from zone mid (median) | **70p** | **284p** | 387p |
| MFE from zone mid (median) | 336p | 133p | 151p |
| idea attempt (mean) | **1.2** | **2.0** | 1.7 |
| 50p displacement ≤60min | 20/20 | 5/5 | 6/6 |
| retrospective "first touch" | 0/20 | 1/5 | 1/6 |

Two honest surprises:

1. **Displacement timing does NOT discriminate** — every measurable trade, winners and losers alike, printed
   $5-from-mid within the hour (median 0 min; his zones are posted mid-move so the mid trades immediately).
   The separator is **how far price goes AGAINST** (MAE 70p vs 284p): winners simply never travel far
   adverse. That is a management-era property, not an entry-timing deadline.
2. **Even the losses averaged 157p MFE before failing** — nearly every trade offered profit first. A large
   share of the observable edge therefore lives in **management mechanics** (TP1 banking ~50p + SL-to-entry)
   rather than entry selection. This is quantitatively why his scratch-heavy style produces so few full losses.

## 2. Rule tests (what each filter would have removed)

| rule | removes | costs | verdict |
|---|---|---|---|
| **R1 first-touch only** (zone untraded 4h prior) | 29/33 trades incl. ALL 20 winners | everything | **INSUFFICIENT_DATA — definition flawed.** Farouk posts zones at/after price arrival, so a retrospective freshness proxy can't test the concept. Needs forward pre-marked levels (TV alerts). |
| **R2 attempt-cap ≤2** | J17 (SL loss) + 2 scratches | J29 (~150p winner) | **PROMISING (risk-adjusted).** ~pip-neutral, removes tail risk. **Corrects Day-6:** J10 was attempt 2 → NOT filtered by ≤2. |
| **R2b no re-entries (cap ≤1)** | **all 3 re-entry losses** (J08 −~40p, J10 −250–400p, J17 −120–210p) + 2 scratches | 3 winners (J14 ~100p, J19 ~130p, J29 ~150p) | **PROMISING.** Rough net +50…+300p AND removes both verified SL losses; loss sample is tiny (6) — needs forward confirmation. |
| **R3 50p-displacement ≤60min deadline** | nothing (0 removed — no discrimination) | — | **REJECT as defined.** See §1; retest later from fill levels with a follower-fill model. |
| **R4 session windows (London 07–11:30Z / NY 13:30–15:30Z)** | 2 losses | **5 winners** (J02, J04, J06, J07, S3 — lunch/pre-London wins are real) | **REJECT as defined.** |
| **R4b late-day cutoff (no entries ≥15:30Z)** | J03 (manual loss) + J17 (SL loss) + 1 scratch | J06 (~53p small winner) | **PROMISING.** Cleanly matches the late-session-fatigue pattern; clearly net-positive on this sample. |
| **R5 HTF veto** | (qualitative only) 1 counter-trend loss (S2) vs 1 counter-trend WIN campaign (Jun-26, half-size) | would remove winner J29 | **INSUFFICIENT_DATA.** Farouk's own control is size-reduction, not a veto. Needs forward HTF context capture. |
| **R6 claim discount** | nothing (analytic control) | none | **PROMISING.** 3 documented inflation cases (J30 +33–56%, S1 +8%, J11 fill-dependent). Expectancy must be computed on TP1/TP2 + scratch modelling, never runner claims. |

**Strongest candidates going forward: R2b (or R2) + R4b + R6.** Combined R2b+R4b on this sample: removes 4
of 6 losses (J03, J08, J10, J17) and 3 scratches, at the cost of 4 winners (J06, J14, J19, J29 ≈ 430p
realistic TP1-centric) vs ≈ 450–700p of losses avoided — directionally positive with materially lower tail
risk, but the loss sample (n=6) is far too small to lock in; these become *scoring features* in the detector
(Step 4), not gates.

## 3. Attribution honesty / limitations

- Outcome statuses are deterministic; the *features* partially depend on conventions (zone-mid reference,
  4h freshness, +6h horizon) — all stated in the JSON, all recomputable.
- MAE within +6h includes post-exit movement for manually-closed trades → loss-group MAE is an upper bound.
- Pip-impact estimates for removed trades use TP1-centric realistic outcomes, not runner claims (per R6).
- 2 setups (J10, J11 — no posted zones) carry limited features; J24 excluded entirely.
- Nothing here is validated forward. All rules await ≥15 forward-captured trades (Day-6 thresholds).

## 4. Safety confirmation

Offline analysis of already-captured data only. Listener PID 87988 running/untouched (start 2026-07-10
21:54:45 unchanged). No broker/QST/cTrader/execution; no permits/leases/orders; gates unchanged; no
TradingView/Worker/R2/secret action; AI narrative review-only; deterministic matchers remain authority;
nothing promoted to trade-ready. `NOT_INTEGRATION_READY` unchanged.

## Next step

**Step 2 — rule extraction:** formalise R2/R2b, R4b, R6 (+ the MAE-based management insight) as testable
predicates in `FAROUK_PLUS_RULESET_v0_1.md`, then Step 3 (AI-assisted filter sweep through the ai_review
validator) and Step 4 (shadow-candidate detector v0_2 replay with these as scoring features).
