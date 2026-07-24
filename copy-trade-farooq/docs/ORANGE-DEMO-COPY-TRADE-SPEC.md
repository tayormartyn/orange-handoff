# ORANGE — DEMO COPY-TRADE LANE, BUILD SPEC (hand to Fable AFTER the Brain is signed off)

**Purpose:** let Martyn copy-trade Farouk's XAUUSD campaigns on a **Pepperstone demo account**, with a human approval gate, using the existing Constitution v0.1 management rules. Demo only. No real money.

**Bounded build. Do not widen it.**

---

## GATE CHANGE (deliberate, not drift)

Introduce a **new, separate** gate:

```
DEMO_EXECUTION_ENABLED = True      (new — demo account only)
HUMAN_APPROVAL_REQUIRED = True     (new — cannot be disabled in v0.1)
```

These remain **unchanged and hard False**:

```
EXECUTION_ENABLED = False          (live)
CTRADER_EXECUTION_ENABLED = False  (live)
MODE = PAPER
LISTENER_MODE = PREVIEW
NOT_INTEGRATION_READY
```

Live execution stays forbidden. This spec authorises demo only. Martyn and ChatGPT must both sign off this gate change before build.

---

## THE FLOW

```
Farouk Telegram signal
→ existing parser + campaign creation (unchanged)
→ existing Lane A interpretation (Constitution v0.1, unchanged)
→ ORDER PLAN built (entries, stop, targets, FIXED demo lot)
→ APPROVAL REQUEST to Martyn  ← he taps Approve or Reject
→ broker adapter places demo orders
→ fills reconciled from broker
→ Farouk management messages ("tp 1 now", "put sl to entry", "close 90% leave 10%", "full exit")
→ translated to order modifications
→ outcome reconciled and recorded
```

---

## HARD SAFETY REQUIREMENTS

1. **Credentials** live in the adapter's environment/secret store only. They must **never** appear in an AI context, prompt, log, ledger or report.
2. **Adapter isolation.** The broker adapter is a separate component. Research/intelligence code never calls the broker directly.
3. **Fixed lot only.** A single configured demo lot size. No dynamic sizing, no risk-percent calculation, no account-balance reading for sizing purposes in v0.1.
4. **Human approval** required for every campaign entry. Pre-authorised without a second tap: break-even moves and explicit TP1/scale-outs that follow Constitution v0.1 exactly. **Approval required** for anything ambiguous, any new entry, and any instruction that fails closed.
5. **Kill switch** — a single command that cancels all working orders and flattens all demo positions, operable without the AI, and drill-tested before first use.
6. **Caps** — max concurrent campaigns, max campaigns per day, both configured and enforced.
7. **Idempotency** — a restart, duplicate message or replayed event must never place a duplicate order. Every order carries an idempotency key.
8. **Broker is the source of truth** for fills, positions and state. Where Orange and the broker disagree, Orange follows the broker and raises a divergence alert. Fail closed.
9. **Ambiguity fails closed** — never guess an order action.

---

## EVIDENCE SEPARATION (critical — do not get this wrong)

Demo execution results go to their **own ledger**, tagged:

```
record_class = DEMO_EXECUTION
eligible_for_prospective_evidence = false
eligible_for_training = false
eligible_for_performance_attribution = false
```

The demo lane must **never** write into the Lane A shadow evidence ledger, the genuine prospective freeze ledger, or the learning dataset. Lane A shadow tracking continues **in parallel and unchanged** — demo running must not alter, delay or block it.

Rationale: the shadow lane measures *what a follower could theoretically capture*; the demo lane measures *what the plumbing actually did*. Mixing them destroys both.

---

## WHAT TO MEASURE (this is the payoff)

Per demo campaign, record:
- Telegram receipt timestamp → approval timestamp → order-placed timestamp → fill timestamp (**latency chain**)
- Requested price vs actual fill price (**slippage**)
- Spread at entry and at each exit
- Broker fill vs Lane A theoretical fill (**fidelity gap**)
- Every management instruction, its translation, and the resulting broker action
- Any divergence, rejection or failure

This finally produces evidence on `TRADINGVIEW_PRICE_SEMANTICS_UNVERIFIED` and `BROKER_EXECUTION_EQUIVALENCE_UNPROVEN`.

---

## ADAPTER NOTE

Build the adapter behind a broker-agnostic interface, with Pepperstone demo as the first implementation. Do not hard-couple research logic to any broker API.

---

## PROOF OF COMPLETION

1. One full Farouk campaign executed end to end on demo: approved, placed, filled, TP1 handled, break-even handled, scale-out handled, closed, reconciled.
2. Kill switch tested — cancels working orders and flattens positions.
3. Restart mid-campaign creates **zero** duplicate orders; state recovers from the broker.
4. An ambiguous instruction fails closed and raises an approval request rather than guessing.
5. Demo ledger is fully separate; Lane A shadow ledger provably unchanged by demo activity.
6. Live gates verified still False; no credential appears in any log, ledger or report.
7. Latency, slippage and spread captured for every leg.

---

## EXPLICIT NON-GOALS

No live execution. No real funds. No dynamic position sizing. No account-risk calculation. No model fitting. No autonomous approval. No strategy changes. No Constitution modification. No promotion of demo results into prospective or training evidence.

---

## WHAT THIS PROVES — AND WHAT IT DOES NOT

**Proves:** the end-to-end chain works; real timing, spread and fill behaviour; management translation is correct; the system is operationally trustworthy.

**Does not prove:** profitability, edge, or live fill quality. Demo servers fill more generously than live ones. A profitable demo run is **not** evidence for going live.
