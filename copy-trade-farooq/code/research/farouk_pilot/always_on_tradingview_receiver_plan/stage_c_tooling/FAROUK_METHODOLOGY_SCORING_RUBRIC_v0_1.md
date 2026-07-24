# Farouk Methodology Scoring Rubric v0.1

**Offline, observation-only.** Scores how well a shadow candidate aligns with Farouk's *documented*
methodology. **No label means trade-ready. No broker/action label exists.** The top label
(`METHODOLOGY_ALIGNED_SHADOW`) means only "worth continued observation," never "enter." Scoring changes
nothing about `NOT_INTEGRATION_READY`.

## Allowed labels (the ONLY permitted outputs)

Ordered weakest → strongest *observational* alignment. None authorises action.

| Label | Meaning | Trade-ready? |
|---|---|---|
| `REJECT` | Disqualified (contradiction, invalidation, or fails a hard gate). Not even worth logging as context. | ❌ never |
| `CONTEXT_ONLY` | Background/noise (e.g. lone Engulfing, ANY_ALERT churn, contradictory cluster). Recorded, not followed. | ❌ never |
| `WATCH` | One real ingredient present but far from a setup; keep an eye out. | ❌ never |
| `SHADOW_CANDIDATE_LOW` | A detected candidate with weak confluence / low outcome support. | ❌ never |
| `SHADOW_CANDIDATE_MEDIUM` | A detected candidate with partial confluence (e.g. aligned CHoCH→A) but material gaps. | ❌ never |
| `METHODOLOGY_ALIGNED_SHADOW` | Strong documented-methodology alignment AND supporting evidence. **Still observation-only** — the ceiling of this rubric. | ❌ never |

**Hard rule:** the scorer may emit ONLY these six strings. Any concept of "buy", "sell", "enter",
"execute", "size", "order", "broker", or "trade-ready" is prohibited and absent from the code.

## Score → label mapping (methodology_score is 0.0–1.0, descriptive only)

`methodology_score` is a **confluence-coverage fraction** (how many documented factors are satisfied,
weighted), NOT a probability of profit and NOT a trade signal.

| Condition | Label |
|---|---|
| Any hard disqualifier fires (contradiction/invalidation) | `REJECT` |
| No candidate / lone primitive / noise | `CONTEXT_ONLY` |
| score < 0.20 (a fragment of confluence) | `WATCH` |
| 0.20 ≤ score < 0.45 | `SHADOW_CANDIDATE_LOW` |
| 0.45 ≤ score < 0.70 | `SHADOW_CANDIDATE_MEDIUM` |
| score ≥ 0.70 **and** ≥1 favourable outcome observation **and** no disqualifier | `METHODOLOGY_ALIGNED_SHADOW` |

Even at the ceiling, if **required context is missing** (e.g. no FVG/OB/BPR/session evidence), the label
is **capped at `SHADOW_CANDIDATE_MEDIUM`** and the gaps are listed in `missing_evidence`. Strong
alignment cannot be claimed on absent data.

## Ceiling caps (never exceed the evidence)

- **Missing required-context factors** → cap at `SHADOW_CANDIDATE_MEDIUM`.
- **Zero or unfavourable outcome observations** → cap at `SHADOW_CANDIDATE_LOW`.
- **A grade claimed but not literally present in raw text** → grade ignored (never inferred).
- **n=1 for the candidate type** → note in `missing_evidence`; does not by itself raise the label.

## Non-negotiables

- Descriptive only; not a signal, not sizing, not PnL.
- `NOT_INTEGRATION_READY` unchanged; no label lifts it.
- Even `METHODOLOGY_ALIGNED_SHADOW` only feeds the shadow journal and the (unmet) evidence-threshold
  review — never an order path.
