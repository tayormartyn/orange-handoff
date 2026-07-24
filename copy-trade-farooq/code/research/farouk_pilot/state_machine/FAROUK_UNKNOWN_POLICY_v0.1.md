# FAROUK UNKNOWN-INPUT POLICY — v0.1

Fail-closed handling for every unresolved input. **Unknown data must never silently pass a guard.**
Allowed handlings: `BLOCK_TRANSITION` (hard stop), `DEGRADE_CONFIDENCE` (proceed only where the transition
is not safety-relevant, lowering `evidence_confidence`), `RESEARCH_ONLY` (measure via the prospective test
matrix; not usable in a live guard), `NOT_APPLICABLE` (input irrelevant to this path).

| Unknown | Where it bites | Handling | Rationale | Resolves via |
|---|---|---|---|---|
| **POC "T" variant meaning** (1DT/1WT/1MT/3DT/2DT) | `AT_POC`, POC_VALUE_REJECTION | **BLOCK_TRANSITION** (`F_POC_T_UNKNOWN`) | a level of unknown definition cannot gate a candidate | companion video / settings Visibility tab; TM-09 |
| **Indicator repaint behaviour** (all objects) | SFP, ORB markers, VWAP, value levels | **BLOCK_TRANSITION** for *_CONFIRMED that depend on a marker; else **DEGRADE_CONFIDENCE** | a repainting marker is not trustworthy for confirmation | prospective capture (TM-01/02/03/08) |
| **Intrabar vs closed-bar timing** | `SFP_CANDIDATE→CONFIRMED`, `BREAKOUT_UNCONFIRMED→CONFIRMED` | **BLOCK_TRANSITION** unless `BAR_CLOSED` (Invariant I-2) | prevents acting on non-final state | TM-01/02/07 |
| **Exact MA trend filter** (which of 20/21/34/50/55; EMA vs SMA) | any bias guard using MAs | **RESEARCH_ONLY** (not used in v0.1 guards; Farouk says he never uses them) | not needed for the supported families | later video; not blocking |
| **Smart Zones internals** | any zone attributed to Smart Zones | **NOT_APPLICABLE** (no object assigned) + **BLOCK** if ever referenced | ownership UNKNOWN; do not attribute | settings capture |
| **Exact confluence threshold** (how many factors qualify) | `WAITING_FOR_TRIGGER→QUALIFIED_CANDIDATE` | **BLOCK_TRANSITION** (`F_CONFLUENCE_UNKNOWN`) | the core qualify rule is unquantified | live-trading videos / adjudication |
| **Exact stop rule** | `STRUCTURE_INVALIDATED` transitions | **DEGRADE_CONFIDENCE** (structural close-through is a proxy) | invalidation can use structure close-through as an interim proxy, flagged low-confidence | later video; TM-11/12 |
| **Canonical timezone** | all session/ORB start/end | **BLOCK_TRANSITION** (`F_TZ_UNKNOWN`) | session-dependent setups cannot qualify (Invariant I-6) | timezone reconciliation; TM-04/05 |
| **Value-area calculation** (VAH/VAL %, engine) | VALUE_LOCATION transitions | **BLOCK_TRANSITION** (`F_VALUE_CALC_UNKNOWN`) | levels of unknown construction cannot gate | TM-09 |
| **VWAP anchor / session reset** | VWAP alignment guards | **DEGRADE_CONFIDENCE** | bias usable at low confidence; reset-repaint unproven | TM-10 |
| **Wick-vs-close break rule (ORB)** | `ORB_LOCKED→BREAKOUT_UNCONFIRMED` | **DEGRADE_CONFIDENCE** (close path is deterministic; wick path degraded) | close-confirmed break is safe; wick-only is not | TM-07 |
| **Liquidity-sweep lookback ('8 bars')** | `LIQUIDITY_APPROACH→SWEEP_CANDIDATE` | **DEGRADE_CONFIDENCE** | approximate; confirm the setting | settings capture |

## Global rule
The composite veto **`G_ANY_UNKNOWN_GUARD`** sits on every safety-relevant transition (notably
`SS-03 → ARMED` and `QU-02 → QUALIFIED_CANDIDATE`): if **any** required input for that path is UNKNOWN, the
transition is blocked and a `failure_reason_code` is recorded. `DEGRADE_CONFIDENCE` is permitted **only**
on non-terminal context transitions, never on the final `QUALIFIED_CANDIDATE` step.
