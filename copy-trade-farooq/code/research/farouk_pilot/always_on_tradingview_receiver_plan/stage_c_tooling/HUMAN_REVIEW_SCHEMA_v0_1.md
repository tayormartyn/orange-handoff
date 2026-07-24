# Human Review Schema v0.1

Schema for a human-review record that validates/rejects the machine **proxies** around a shadow
candidate. **Observation-only; candidate-only; human confirms EVIDENCE, not trades.**
`NOT_INTEGRATION_READY` unchanged.

## Fields

| Field | Type | Meaning |
|---|---|---|
| `review_id` | string | PK, `HR-NNNN`. |
| `candidate_id` | string | Shadow candidate under review. |
| `reviewer` | string | Who reviewed (name/initials). |
| `review_status` | enum | `PENDING` / `REVIEWED` / `NEEDS_MORE_DATA`. |
| `chart_window_start_utc` | ISO8601 UTC | Start of the chart window reviewed. |
| `chart_window_end_utc` | ISO8601 UTC | End of the chart window reviewed. |
| `screenshot_required` | bool | Whether screenshots must accompany the review (default true). |
| `raw_alert_sequence` | list[string] | Raw Farouk alert texts in order (source of truth). |
| `classified_sequence` | list[string] | Classified event_type(direction) in order. |
| `outcome_summary` | string | From the outcome matcher (MFE/MAE/close per horizon; outcome_label). |
| `session_review` | enum | `CONFIRMED` / `DENIED` / `UNSURE` / `UNRESOLVED` (TZ). |
| `liquidity_review` | enum | Sweep credible? `CONFIRMED` / `DENIED` / `UNSURE`. |
| `structure_review` | enum | BOS/CHoCH in meaningful structure? `CONFIRMED` / `DENIED` / `UNSURE`. |
| `displacement_review` | enum | Real displacement vs volatility? `CONFIRMED` / `DENIED` / `UNSURE`. |
| `fvg_review` | enum | FVG meaningful vs tiny/noisy? `CONFIRMED` / `DENIED` / `UNSURE`. |
| `bpr_review` | enum | BPR overlap real? `CONFIRMED` / `DENIED` / `UNSURE` / `N/A`. |
| `order_block_review` | enum | OB credible & fresh (not spent)? `CONFIRMED_FRESH` / `CONFIRMED_MITIGATED` / `DENIED` / `UNSURE`. |
| `htf_bias_review` | enum | HTF bias direction (human read): `BULLISH` / `BEARISH` / `NEUTRAL` / `UNSURE`. |
| `contradiction_review` | enum | Contradictory cluster present? `PRESENT` / `ABSENT` / `UNSURE`. |
| `telegram_discord_context_review` | enum | Channel confirmation? `CONFIRMED` / `NONE` / `NOT_CHECKED`. |
| `final_review_label` | enum | `REJECT` / `CONTEXT_ONLY` / `WATCH` / `SHADOW_CANDIDATE_LOW` / `SHADOW_CANDIDATE_MEDIUM` / `METHODOLOGY_ALIGNED_SHADOW`. |
| `reviewer_notes` | string | Free text. |
| `missing_evidence` | list[string] | Factors still unconfirmed/unavailable. |
| `disqualifiers` | list[string] | Hard-gate failures found on review. |
| `candidate_only` | bool | Always `true`. |
| `execution_allowed` | bool | Always `false`. |
| `broker_execution_allowed` | bool | Always `false`. |
| `qst_allowed` | bool | Always `false`. |
| `order_intent` | bool | Always `false`. |
| `risk_sizing_allowed` | bool | Always `false`. |

## Rules

- **Append-only.** Machine proxies are never overwritten; the human verdict is recorded alongside.
- `final_review_label` may use **only** the six allowed labels — **none is trade-ready**. Even
  `METHODOLOGY_ALIGNED_SHADOW` is observation-only.
- A review confirms **evidence**, never a trade. No order/SL/TP/size/route field exists in this schema.
- Verdicts of `UNSURE` / `NEEDS_MORE_DATA` keep the factor in `missing_evidence`.
- `NOT_INTEGRATION_READY` unchanged by any review outcome.
