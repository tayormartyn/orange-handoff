# A-grade hypothesis test — offline blinded reconstruction (INSUFFICIENT_SAMPLE / NOT_TESTABLE)

**Mode: OFFLINE VALIDATION — REVIEW-ONLY. SINGLE-SESSION.** Date 2026-07-13 (~04:05Z). Machine-readable:
`agrade_hypothesis_test_results.json`. Live gates clean throughout (store max 45657; listener PID
30268; Cycle 006 open). Gates `PAPER/PREVIEW/False/False`; `NOT_INTEGRATION_READY` unchanged;
v0.3/v0.2/v0.4 untouched. **No outcome/price data used anywhere in this test.**

## 1. Eligible-event inventory
- **`TradingView_Alerts_Log_2026-07-06.csv`** (server-side log, 05:24Z–21:00Z, 111 alerts, XAUUSD 3m
  Pepperstone): **4 A+ setups** (07:24Z + 07:27Z SHORT cluster; 16:30Z LONG; 18:33Z LONG — each =
  "A+ or better setup" trigger + same-bar "A+ LONG/SHORT" composite), **21 A-dir events**, plus
  context alerts (Sweep ×37, Engulfing ×26, BPR ×13, CHoCH ×6).
- **Gate-G R2 window** (Jul-8 22:15Z → Jul-9 09:51Z, 74 events): A SHORT ×14, A LONG ×10 — but
  **ZERO A+ / A+++** (documented in `GATE_G_RAW_EVENT_INVENTORY.md`); eligible-but-empty for the top
  tier; its A-dir rows were NOT re-parsed this pass (would refine the A-tier ratio only; noted).
- **A+++: has NEVER fired in any captured evidence** (phone batch + Gate-G + alert log concur).
- **Excluded:** all events lack chart-state evidence (payloads are plain condition names); the one
  phone screenshot near the 18:33Z A+ LONG shows price only (panel renders no grade) — no component
  extractable. Nothing manufactured; unobservables recorded as UNKNOWN.

## 2. Frozen hypotheses (defined from pages BEFORE computation; no tuning)
- **HYP-A (six-factor, Playbook p12 / DR-207):** A = FVG+pattern; A+ = BPR+pattern+trend;
  A+++ = BPR+OB+sweep+reversal+trend.
- **HYP-B (eight-box, p21 / DR-206):** grade = checklist count (≥6/8 = A+++, 5/8 half-tier, <5 skip).
- **Frozen observability proxy:** pattern = same-3m-bar Engulfing alert; BPR/Sweep/CHoCH/Asia-trap =
  same bar or ≤5-bar (15-min) lookback. **UNOBSERVABLE from payloads: FVG, OB, trend/EMA, freshness,
  session-position** — so only NECESSARY-condition checks are possible, never full grades.

## 3. Blinded per-event results (components computed only from OTHER alerts' timestamps)
| A+ setup (bar close) | dir | pattern same-bar | BPR ≤5 bars | sweep ≤5 bars | HYP-A necessary-check |
|---|---|---|---|---|---|
| 2026-07-06 07:24Z | (trigger) | no engulfing alert | **YES** | YES | BPR ✓; pattern UNOBSERVABLE |
| 2026-07-06 07:27Z | SHORT | **YES** | **YES** | YES | BPR+pattern ✓ (trend unobservable) |
| 2026-07-06 16:30Z | LONG | no engulfing alert | **YES** | no | BPR ✓; pattern UNOBSERVABLE |
| 2026-07-06 18:33Z | LONG | **YES** | **YES** | YES | BPR+pattern ✓ (trend unobservable) |

A-tier: 12/21 A-dir events had a same-bar Engulfing; the other 9 are UNOBSERVABLE (hammer/star/
tweezer patterns have no alert condition), not contradicted.

## 4. Metrics
- HYP-A: eligible A+ events 4; **fully-testable necessary condition (BPR for A+): 4/4 pass (100%)**;
  partial pattern check 2/4 observable-pass, 2/4 UNKNOWN; **contradictions: 0**;
  insufficient-evidence components dominate. Confusion matrix: not meaningful at n=4 (stated).
- HYP-B: **0 events computable** — only ~3 of 8 boxes observable by construction → NOT_TESTABLE.
- **Specificity check:** 5 bars had Engulfing+BPR co-occurrence; only 2 became A+ → the observable
  components are NOT sufficient for A+ — *consistent with* DR-207 requiring (unobservable) trend
  alignment as well; also consistent with a different hidden formula. Indistinguishable.
- A+++: never fired, even on the two bars where ALL observable A+++ components co-occurred
  (07:27Z, 18:33Z) — the unobservable gates (OB/trend) or a stricter internal threshold block it;
  cannot distinguish.
- Repaint: all events assumed bar-close-aligned from :00/:01 stamps; repaint status UNKNOWN
  (F5 binding) — excluding repaint-uncertain events would exclude EVERYTHING, so no
  post-exclusion metric exists (stated).

## 5. Verdicts (one each, as required)
- **HYP-A (six-factor): INSUFFICIENT_SAMPLE** — n=4 A+ with one fully-observable component;
  zero contradictions; weak directional support (4/4 BPR-necessity).
- **HYP-B (eight-box): NOT_TESTABLE** with the current capture surface.
- **Equivalence status: DOCUMENT_FORMULA_KNOWN / INDICATOR_EQUIVALENCE_UNKNOWN — UNCHANGED.**
  Not upgraded to PARTIALLY_SUPPORTED: n=4 with dominant unobservables does not justify it.
  Recorded plus-fact: **nothing observed contradicts the document formula.**

## 6. What closes the gap
Forward captures that pair A-grade alert events with bar-level chart state (panel values,
FVG/OB/BPR inventory, session context) — **exactly what the Cycle-006+ capture spec already
collects.** Each future A+ event with chart-state evidence is one clean test row.

## 7. Safety
No execution; no permits/leases/orders; no sizing fields; F5 guard respected (no repaint-dependent
claim); nothing entered v0.3; A-grade remains PROHIBITED from scoring; gates and
`NOT_INTEGRATION_READY` unchanged. Integrity test re-run after the register update: see run log.
