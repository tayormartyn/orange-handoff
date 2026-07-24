# Shadow Observation Journal — Schema v0.1

Schema for the append-only journal of outcome-matched shadow candidates. **Observation/evidence only —
every row is candidate-only and authorises nothing.** `NOT_INTEGRATION_READY` unchanged.

## One row = one outcome-matched candidate

| Field | Type | Meaning |
|---|---|---|
| `observation_id` | string | Journal PK, `SOJ-NNNN` (append order). |
| `candidate_id` | string | Source shadow-candidate id. |
| `candidate_type` | string | ALIGNED_CHOCH_TO_A / SWEEP_TO_CHOCH_CONTEXT / BPR_TO_A_CONTEXT / … |
| `detector_version` | string | e.g. `shadow_candidate_detector_v0_1`. |
| `classifier_version` | string | e.g. `raw_farouk_text_classifier_v0_2`. |
| `anchor_time_utc` | ISO8601 UTC | Confirming-event time (matcher anchor). |
| `direction_hint` | LONG / SHORT | Bias descriptor — **NOT an order side**. |
| `event_sequence_raw` | string | Raw Farouk texts in order (source of truth), ` \| `-joined. |
| `event_sequence_classified` | string | Classified types/directions in order. |
| `entry_reference_price` | float | Close of first candle at/after anchor (USD/oz). |
| `MFE_15m` / `MAE_15m` / `final_close_delta_15m` | float | Max favourable / max adverse / close-Δ at 15m, oriented to hint (price units). |
| `MFE_30m` / `MAE_30m` / `final_close_delta_30m` | float | …at 30m. |
| `MFE_60m` / `MAE_60m` / `final_close_delta_60m` | float | …at 60m. |
| `MFE_120m` / `MAE_120m` / `final_close_delta_120m` | float | …at 120m. |
| `adverse_heat_note` | string | Free text: drawdown-before-follow-through, etc. |
| `outcome_label` | enum | `FAVOURABLE` / `UNFAVOURABLE` / `MIXED` / `INCONCLUSIVE`. |
| `data_quality` | enum | `FULL` / `PARTIAL` / `NO_DATA`. |
| `warnings` | string | Matcher warnings (or `none`). |
| `candidate_only` | bool | Always `true`. |
| `execution_allowed` | bool | Always `false`. |
| `broker_execution_allowed` | bool | Always `false`. |
| `qst_allowed` | bool | Always `false`. |
| `order_intent` | bool | Always `false`. |
| `risk_sizing_allowed` | bool | Always `false`. |

## outcome_label rubric (descriptive, at the 120m close unless noted)

- **FAVOURABLE** — final_close_delta_120m clearly positive **and** adverse heat modest.
- **UNFAVOURABLE** — final_close_delta_120m negative (moved against the hint) or dominated by adverse.
- **MIXED** — ended favourable but only after material adverse heat (drawdown-then-follow-through), or
  favourable at one horizon and adverse at another.
- **INCONCLUSIVE** — `PARTIAL`/`NO_DATA`, or move within noise (no clear direction).

Labels are **descriptions of observed price behaviour**, never a rating of trade quality or a signal.

## Rules

- **Append-only.** Never edit/delete a past observation; raw sequence is preserved verbatim.
- All values are descriptive **price** stats (USD/oz) — **not** PnL, pips-as-profit, sizing, or SL/TP.
- UTC everywhere. No fabrication: missing data → `NO_DATA`/`PARTIAL` + warning, never invented numbers.
- Files: markdown `SHADOW_OBSERVATION_JOURNAL_v0_1.md` (human) + `shadow_observation_journal_v0_1.csv`
  (aggregation). Same rows.
