# Farouk Campaign State — Schema v0.1

**Observation-only.** Input = resolved evidence facts for one alert anchor; output = a campaign state result.
No execution/broker surface anywhere. `NOT_INTEGRATION_READY` unchanged.

## Input — `Observation`

| field | type / enum | meaning |
|---|---|---|
| `campaign_id` | str | identifier (e.g. `HR-0001`) |
| `alert_raw` | str | raw Farouk `alert()` text (source of truth; may be INVALID_JSON) |
| `classified_family` | str | classifier family (A_SIGNAL, STRUCTURE, LIQUIDITY_SWEEP, BPR, …) |
| `direction_hint` | `LONG` \| `SHORT` \| None | intended direction |
| `sweep` | `NONE` \| `PRESENT` \| `CONFIRMED` | liquidity sweep evidence |
| `sweep_late` | bool | entry taken well after the sweep (context only) |
| `structure_choch` | `NONE` \| `WEAK` \| `CONFIRMED` | CHoCH strength |
| `choch_in_chop` | bool | CHoCH sits inside a choppy range (low conviction) |
| `order_block` | `NONE` \| `FRESH` \| `FRESH_BREACHED` \| `MITIGATED_SPENT` | POI/OB status |
| `displacement` | `NONE` \| `WEAK` \| `MODERATE` \| `STRONG` \| `AGAINST` | displacement (`AGAINST` = opposite the direction) |
| `htf` | `UNKNOWN` \| `ALIGNED` \| `OPPOSED` | higher-timeframe bias vs direction |
| `contradiction` | bool | signal fired against the immediate/effective bias |
| `outcome` | `UNKNOWN` \| `FAVOURABLE` \| `MIXED` \| `UNFAVOURABLE` | observed outcome (descriptive, not PnL) |
| `human_review` | `{label, status}` \| None | optional human verdict (advances lifecycle to REVIEWED/JOURNALLED) |

**No input field carries broker/account/lot/order/route/risk-sizing/permit/lease data** — the schema has no
such fields.

## Output — `CampaignResult`

| field | type | meaning |
|---|---|---|
| `campaign_id` | str | echo |
| `state_path` | list[str] | ordered states visited |
| `campaign_state` | enum | terminal classification: `SHADOW_CANDIDATE_MEDIUM` \| `SHADOW_CANDIDATE_LOW` \| `WATCH_ONLY` \| `SHADOW_REJECTED` |
| `final_state` | enum | lifecycle terminal: `HUMAN_REVIEW_REQUIRED` \| `JOURNALLED` |
| `resolved_label` | str | machine label, or the human-review label if supplied |
| `reasons` | list[str] | human-readable rule trace |
| `machine_human_agree` | bool \| None | whether the human label maps to the machine state (when review supplied) |
| **safety flags (all hard-wired)** | | |
| `candidate_only` | `True` | |
| `trade_ready` | `False` | never true |
| `execution_allowed` | `False` | |
| `broker_execution_allowed` | `False` | |
| `qst_allowed` | `False` | |
| `order_intent` | `False` | |
| `risk_sizing_allowed` | `False` | |
| `observation_only` | `True` | |

## Human-review label → campaign state

`SHADOW_CANDIDATE_MEDIUM→MEDIUM`, `SHADOW_CANDIDATE_LOW→LOW`, `WATCH`/`WATCH_ONLY`/`CONTEXT_ONLY→WATCH_ONLY`,
`REJECT`/`SHADOW_REJECTED→SHADOW_REJECTED`.

## Invariants

- Deterministic: identical input → identical output; no time/randomness/I/O.
- The output dict may only contain an execution-substring key if it is one of the explicit negative safety
  flags and its value is `False` (enforced by `_assert_no_execution_surface`).
- `emits_execution(result)` is `False` by construction.
