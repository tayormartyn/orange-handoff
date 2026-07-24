# Human Review Decision Rules v0.1

Binding rules for turning a human review into a `final_review_label`. **None of these permits trading.**
`NOT_INTEGRATION_READY` unchanged.

## Core rules

1. **No single reviewed proxy makes a candidate trade-ready.** Confirming an OB, FVG, or displacement can
   **only improve a shadow score** — never cross into execution. There is no "trade-ready" label.
2. **Confirmed OB / FVG / displacement → shadow improvement only.** A `CONFIRMED_FRESH` OB + `CONFIRMED`
   FVG + `CONFIRMED` displacement + aligned HTF can raise a candidate toward
   `SHADOW_CANDIDATE_MEDIUM`/`METHODOLOGY_ALIGNED_SHADOW` — both **observation-only**.
3. **Unfavourable outcome remains a strong negative.** Even with confirmed structure, an `UNFAVOURABLE`
   outcome caps the label low (≤ `SHADOW_CANDIDATE_LOW`). A confirmed-but-losing pattern is not evidence
   of an edge.
4. **Contradictory cluster remains a disqualifier → `REJECT`.** If opposite-direction signals cluster
   within the window, the candidate is rejected regardless of other confirmations.
5. **Missing Telegram/Discord confirmation stays missing evidence.** Its absence does not disqualify (it
   is not a methodology factor), but it cannot be counted as satisfied.
6. **`METHODOLOGY_ALIGNED_SHADOW` is NOT permission to trade.** It is the observation ceiling. It only
   marks "strongly aligned, keep studying," and feeds the (unmet) evidence-threshold review.
7. **Demo discussion stays blocked** until `NO_TRADE_TO_DEMO_EVIDENCE_THRESHOLDS_v0_1.md` is met
   (≥30 outcome-matched candidates across ≥5 sessions, per-type, adverse/false-positive/missed-signal
   review, manual sign-off, zero auto broker path). Currently **3/30 — NOT MET**.

## Additional gates

- **Spent/mitigated OB** cannot be treated as a fresh OB; downgrade accordingly.
- **Session UNRESOLVED** (timezone) → session factor stays unsatisfied; cannot reach the top label.
- **HTF against the direction hint** → note as a negative; do not confirm alignment.
- **Corpus-UNKNOWN thresholds** (displacement size, FVG fill, OB tap-count, grade formula) stay UNKNOWN —
  human review confirms *presence/credibility*, it does not invent numeric rules.
- **UNSURE / NEEDS_MORE_DATA** → keep the factor in `missing_evidence`; do not upgrade the label on doubt.

## Label ceiling table (per review)

| Situation | Max label |
|---|---|
| Any hard disqualifier / contradictory cluster | `REJECT` |
| Pure noise / lone primitive | `CONTEXT_ONLY` |
| Thin/unconfirmed evidence | `WATCH` / `SHADOW_CANDIDATE_LOW` |
| Unfavourable outcome (even with confirmed structure) | `SHADOW_CANDIDATE_LOW` |
| Multiple confirmed factors, session unresolved OR outcome not favourable | `SHADOW_CANDIDATE_MEDIUM` |
| Session confirmed + fresh confirmed OB + aligned HTF + favourable outcome | `METHODOLOGY_ALIGNED_SHADOW` (still observation-only) |

## Safety

Every review record stays candidate-only; execution / broker / qst / order_intent / risk_sizing = false.
No order/SL/TP/size/route is ever produced. `NOT_INTEGRATION_READY` unchanged by any review outcome.
