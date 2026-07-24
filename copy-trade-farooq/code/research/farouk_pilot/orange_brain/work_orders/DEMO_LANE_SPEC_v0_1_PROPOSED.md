# DEMO LANE SPECIFICATION v0.2 — PROPOSED FOR RATIFICATION

**Status: PROPOSED_FOR_RATIFICATION — NOT AUTHORISED, NOT BUILT, NOT EXECUTED.**
**v0.2 (2026-07-21):** adds §6a broker-native protective stop at placement + host-death survivability tests + restart reconcile-first, per reviewer material-gap finding ("kill switch and dead-man halting require the executor to be alive; host death is the measured norm, not hypothetical — 21% of bars arrive as post-outage catch-up batches"). v0.1 was superseded before circulation; this is the ratification text.
Written 2026-07-21 per operator directive (revised-order item A). Requires sign-off by **Martyn AND the reviewer** before any build work begins. Until ratified, nothing in this document changes any gate, config, or behaviour. Inputs: master-vNEXT `demo_readiness_blockers` (research-proposed, D-009 — blocking direction only), the read-only cTrader groundwork (`ctrader_auth.py` / `ctrader_config.py`, Pepperstone DEMO, read-only conn established, OAuth pending), the reviewer's directive of 2026-07-21, and fill_lag_cost v0.1 results (see §9).

---

## 1. Purpose and scope
A **demo-execution lane**: Lane A strict-follower proposals placed as real orders on a **cTrader DEMO account only** (Pepperstone demo), to measure end-to-end execution fidelity (fills, slippage, lifecycle correctness) with zero real-money exposure. It is an **instrumentation lane, not a strategy lane**: no signal generation, no model, no discretion — it executes exactly what Lane A already proposes on paper, subject to per-campaign human approval.

**Instrument scope: XAUUSD only.** Nothing else — not the limit-order channel (DIFFERENT_SPECIES, D-023), not forex/nasdaq/silver (OQ-11, uncharacterised), never crypto (K-047 hard isolation).

## 2. Governance and gates (the load-bearing section)
- `EXECUTION_ENABLED = False` and `CTRADER_EXECUTION_ENABLED = False` **remain hard False, untouched, permanently, in this proposal.** This spec does NOT propose changing either.
- A **new, separate gate `DEMO_EXECUTION_ENABLED`** (default `False`) is proposed. It gates ONLY the demo lane. Flipping it to `True` requires: this spec ratified by Martyn AND reviewer; all §8 prerequisites green; a signed entry in the human-ratification record. Any change to the gate's semantics is itself a gate change requiring the same sign-off.
- The existing hard gates (`MODE=PAPER`, `LISTENER_MODE=PREVIEW`, `NOT_INTEGRATION_READY`) stay as-is for the existing stack; the demo executor is a **separate process** so that no existing service acquires execution capability. The seven live services never gain broker code.
- Autonomy ceiling: **per-campaign human approval** (§4). Any increase beyond that triggers the registered future items (terminal-marker canonicalisation; push-based alert-lane monitoring — see FUTURE_ITEM_TERMINAL_MARKER_CANONICAL_SHAPE.md and the pull-based-monitoring limitation).

## 3. Hard demo-account-type check
At every startup AND before every order call, the executor verifies via the cTrader API that the connected account is `accountType == DEMO` (and the expected known account id). Live account, unknown id, or unverifiable type → **process refuses to start / halts immediately, loud alarm, no order path exists**. This check is code-enforced and unit-tested with a mocked LIVE response (test must prove refusal). Credentials for any live account are never present in config.

## 4. Per-campaign approval mechanics
- A new Lane A campaign (XAU_F_SETUP) produces a **DEMO_APPROVAL_REQUEST** record and an operator prompt. **No order is placed until Martyn approves that specific campaign** (explicit token: campaign id + approval timestamp, recorded in the demo ledger).
- Approval covers that campaign's lifecycle (entry legs + subsequent Lane-A-derived management on the same campaign). It does NOT roll over to the next campaign.
- No approval → the campaign runs paper-only exactly as today. Ambiguity (wire FAIL_CLOSED_REVIEW / NEEDS_HUMAN_REVIEW / pause records) → demo lane takes **no action** on that message; fail-closed inherits.

## 5. Sizing — fixed nominal
**Fixed nominal size per leg, identical for every campaign: the broker minimum (0.01 lots per leg).** No scaling, no risk-based sizing, no compounding, no operator override upward. Farouk's stated sizes are never copied (constitution: sizing is out of scope). Rationale: execution-fidelity measurement needs constant size; any sizing logic would be unauthorised model territory.

## 6. Kill switch
- **File-based kill switch** (`DEMO_KILL`): if present, the executor cancels all open demo orders, flattens demo positions, writes a terminal ledger record, and exits. Checked every loop iteration (≤5s cadence).
- **Passive dead-man behaviour:** on any unhandled exception, lock conflict, gate re-read failure, account-type re-check failure, or broker disconnect beyond a grace window → same cancel-flatten-halt path. Halt is always the safe direction (demo money; missed follow-up is acceptable, unmanaged orders are not).
- Martyn can also simply close the account session broker-side; the executor must tolerate that (reconcile on reconnect, never re-place without fresh approval).

## 6a. Broker-native protective stop at placement (v0.2 — host-death survivability)
§6's kill switch and dead-man halting only work while the executor process is alive. fill_lag_cost v0.1 measured host death as the operating norm, not the exception (21% of bars arrived as post-outage catch-up batches). Therefore:

- **Every demo order carries a broker-native protective stop attached at the moment of placement**, sized to the published follower stop for that campaign (the same posted stop Lane A holds). The position is protected by the broker's own servers with **zero dependence on Orange being alive, connected, or correct**.
- **A position must never exist at the broker without a broker-side stop.** If the API cannot attach the stop atomically with the order, the executor must use the broker's stop-loss-on-order fields (cTrader supports SL at order placement); if a placement ever results in a stop-less position (rejected SL, partial modify failure), the executor immediately closes that position and alarms — stop-less exposure is never carried, not even on demo.
- Orange may later **modify** the broker-side stop under a Lane-A instruction (SL_TO_ENTRY, REVISED_STOP) — modification only, never removal. An instruction whose effect would be to remove protection entirely fails closed to human review.
- **On executor restart after any outage: reconcile FIRST.** Broker state is read and adopted as truth before ANY action — no placements, no modifications, until reconciliation completes. Any position or order discovered at the broker that Orange has no ledger record of → **loud alarm + no touch** (it is never adopted silently, never closed silently; operator decides).
- **Mandatory tests (added to §10.5):** (i) kill the executor process (hard kill, no cleanup) mid-campaign with an open demo position and PROVE the broker-side stop remains in force and executes if the level trades; (ii) restart-after-kill and prove reconcile-first ordering (no action before broker state adopted); (iii) inject an unknown broker-side order and prove the loud-alarm-no-touch path.

## 7. Idempotency and broker-as-truth reconciliation
- Every order carries a **deterministic client id** derived from (campaign id, leg id, instruction id, revision). Restart/replay can never double-place: before any placement the executor queries the broker for existing orders/positions with that client id.
- **The broker is the source of truth for fills.** fill_lag_cost v0.1 proved why: our bar feed runs a median 94s (p90 124s) behind real time in steady state and 21% of bars arrived as post-outage catch-up batches — bar-inferred fills are structurally late and outage-blind. The executor therefore consumes broker execution events (or polls broker state) for fill/position truth, and a **reconciliation pass** compares broker state against the demo ledger every cycle; any mismatch (unknown order, size drift, unexpected fill) → alarm + kill-switch path, never silent repair.
- Lane A paper remains the *interpretation* truth (what should have happened); the demo ledger records what *did* happen at the broker; divergences between them are the lane's primary research output.

## 8. Ledger — DEMO_EXECUTION, separate and non-evidential
- New append-only ledger `demo_execution_ledger_v0_1.jsonl`, physically separate from the forward-validation ledger. Existing ledgers are never written by the demo lane.
- **Every record carries `eligible_for_prospective_evidence: false`** plus the standard `review_only/observation_only` stamps. Demo results are execution-fidelity instrumentation only. They never enter expectancy, ranking, freezes, or campaign statistics. The genuine prospective count for expectancy purposes is governed by the freeze ledger alone (currently **3 resolved: F004 +15.18, F005 NO_FILL, F007 +5.38** — F007 flagged MODEL_ARTEFACT_TERMINAL; F006 excluded by named defect; no expectancy figure computed at n=3).
- Record types: DEMO_APPROVAL_REQUEST / DEMO_APPROVED / DEMO_ORDER_PLACED / DEMO_FILL / DEMO_MGMT_APPLIED / DEMO_RECON_MISMATCH / DEMO_KILL / DEMO_HALT.

## 9. Design inputs from fill_lag_cost v0.1 (measured 2026-07-21)
- Message→actuation lag 3–34s across all 9 measured management actions; listener lag sub-second-to-seconds. Instruction latency is NOT the risk.
- Bar delivery: steady-state median 94s / p90 124s / max 561s; 21% of bars catch-up (>600s) after host outages — hence §7 broker-as-truth and §6 dead-man halting, and why **OQ-7 (host reboot reliability) is a hard prerequisite**: a reboot mid-campaign with resting demo orders = unmanaged position until restart.
- Entry legs are resting limits at posted prices — entry fill-lag cost structurally ~0; drift exposure concentrates in management actions, worst-case bounded by the actuation bar's range (12–44 pips on the measured n=9). Demo lane exists to measure the realised (not bounded) number.

## 10. Prerequisites before DEMO_EXECUTION_ENABLED can flip (all must be green)
1. This spec ratified (Martyn + reviewer), recorded in the human-ratification record.
2. LIVE_EDIT_EVENTS_NOT_CAPTURED fixed, proven, deployed (edit-after-transition alarm live).
3. OQ-8 quarantine review tool live with durable resolution format; queue drained.
4. OQ-7 host-reboot mitigation decided and in place (operator action).
4a. **TERMINAL-MARKER CANONICAL SHAPE built, proven and deployed** (pulled forward from "before autonomy increase" by operator ratification 2026-07-21, D-043): outcome-based terminals (P10 BE scratches etc.) are the COMMON case, the nominal-open set grows with most campaigns, and consecutive-day campaigns (F006→F007: 17.6h apart, inside the 18h window) make P02 pause-noise the expected state — unacceptable under demo operation. See FUTURE_ITEM_TERMINAL_MARKER_CANONICAL_SHAPE.md.
5. Demo-account-type refusal test, kill-switch test, idempotency restart test, reconciliation mismatch test, AND the §6a host-death suite (hard-kill stop-survival, restart reconcile-first, unknown-position no-touch alarm) — all with recorded proof runs (against the demo API; mocked live-account case).
6. Read-only broker connection (existing groundwork) upgraded to demo-trade scope by Martyn's own OAuth grant — never by stored live credentials.

## 11. Explicitly out of scope
Live execution in any form; sizing logic; multi-instrument; multi-trader; autonomy beyond per-campaign approval; any model fitting (D-009 unchanged); any change to the seven existing services beyond reading the same ledgers they read today.
