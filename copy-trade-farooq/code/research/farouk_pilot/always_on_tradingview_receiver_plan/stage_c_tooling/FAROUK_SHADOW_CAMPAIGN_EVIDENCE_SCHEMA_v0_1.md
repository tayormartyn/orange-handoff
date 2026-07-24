# Farouk Shadow-Campaign Evidence Schema v0.1

Schema for one methodology-scored shadow-campaign evidence record. **Observation-only; candidate-only.**
Every record is descriptive; none authorises action. `NOT_INTEGRATION_READY` unchanged.

## Fields

| Field | Type | Meaning |
|---|---|---|
| `candidate_id` | string | Source shadow-candidate id. |
| `raw_alerts` | list[string] | Raw Farouk alert texts in order (source of truth). |
| `classified_alerts` | list[string] | Classified event_type(direction) in order. |
| `session` | enum/string/null | Session/killzone context (e.g. `ASIA`,`LONDON`,`NY`,`UNKNOWN`). **null until we derive it.** |
| `liquidity_event` | enum/string/null | Sweep high/low present? (`SWEEP_HIGH`,`SWEEP_LOW`,`none`). |
| `structure_event` | enum/string/null | CHoCH/BOS present? (`CHOCH_UP`,`CHOCH_DOWN`,`BOS`,`none`). |
| `displacement_evidence` | bool/null | Displacement confirmed? **null = not available from pipeline.** |
| `fvg_evidence` | bool/null | Fair Value Gap present? **null = not captured.** |
| `bpr_evidence` | enum/string/null | BPR state (`BPR_FORMED`,`BPR_TAPPED`,`none`). |
| `order_block_evidence` | bool/null | Order Block present? **null = not captured.** |
| `alert_grade` | enum/string/null | `A`,`A+`,`A+++` — only if literally in raw text, else null. |
| `direction_hint` | LONG/SHORT/null | Bias descriptor — NOT an order side. |
| `telegram_confirmation` | bool/null | Farouk channel confirmation matched? **null until cross-checked.** |
| `contradiction_flags` | list[string] | Contradictory/invalidation flags (e.g. opposite-direction cluster). |
| `outcome_stats` | object/null | From outcome matcher (MFE/MAE/final per horizon, outcome_label) or null. |
| `methodology_score` | float | 0.0–1.0 confluence-coverage fraction (descriptive, NOT profit prob). |
| `score_label` | enum | One of the six rubric labels (REJECT…METHODOLOGY_ALIGNED_SHADOW). |
| `missing_evidence` | list[string] | Documented factors not available/not satisfied. |
| `disqualifiers` | list[string] | Hard-gate failures. |
| `candidate_only` | bool | Always `true`. |
| `execution_allowed` | bool | Always `false`. |
| `broker_execution_allowed` | bool | Always `false`. |
| `qst_allowed` | bool | Always `false`. |
| `order_intent` | bool | Always `false`. |
| `risk_sizing_allowed` | bool | Always `false`. |

## Rules

- **`null` means "not available from our current pipeline"** — distinct from `false`/`none` ("checked,
  absent"). The scorer treats null as *missing evidence*, never as a satisfied factor.
- Raw alerts preserved verbatim. Grades never inferred (literal-only).
- All numbers descriptive; no PnL/sizing/order/broker/account field ever present.
- Append-only alongside the shadow observation journal; feeds only the (unmet) evidence-threshold review.
