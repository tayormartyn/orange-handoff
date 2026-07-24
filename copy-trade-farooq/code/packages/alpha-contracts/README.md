# @signal-terminal/alpha-contracts

Methodology-agnostic, **suggests-only** contracts for the Signal Terminal Alpha
layer. This package is the narrow waist between *any* Alpha module (Farouk, ORB,
or a future one) and the downstream `QUALIFIED_STRIKE_AND_TRAP` qualifier.

## Governing principle

```
Alpha discovers intent.
QUALIFIED_STRIKE_AND_TRAP qualifies intent.
The risk engine sizes the campaign.
The authorisation layer permits or rejects the route.
The execution layer alone touches the broker.
```

This package sits entirely inside the first line. It contains **zero** broker,
execution, account-risk, route, credential, cTrader, TradingView, or
Farouk-specific code — and the architecture test in
`test/compatibility.test.ts` fails the build if any such import ever appears.

## What's here

| File | Purpose |
|---|---|
| `primitives.ts` | Branded shared types: UTC timestamps, decimal-string prices, ids, reproducibility metadata, operating mode. |
| `AlphaSignalProposal.ts` | The **only** thing a module may emit. `.strict()` + an explicit denylist forbid position size, account id, risk %, route, credentials, order ids, execution permission. |
| `AlphaSignalModule.ts` | The module interface. `evaluate(state, context) -> { nextState, proposals, trace }`. No method can touch a broker. |
| `AlphaEvaluationContext.ts` | Deterministic, **point-in-time** input. Refinement rejects any bar dated after `asOf` (look-ahead leak). |
| `AlphaModuleState.ts` | Snapshot/restore envelope for replay + restart equivalence. |
| `AlphaDecisionTrace.ts` | Symmetric audit trail — a *no-trade* is traced as fully as a proposal. |
| `AlphaResearchConclusion.ts` | Research outcome incl. `INSUFFICIENT_EVIDENCE` / `NOT_IDENTIFIABLE`, plus candidate-budget & multiple-testing accounting. |
| `QstAdapterBoundary.ts` | One-way port to the qualifier. Returns an intake ack only — never fills, sizing, or order ids back into Alpha. |
| `ValidationHarness.ts` | Ports for deterministic replay, look-ahead probing, and conclusion production. |
| `ObservationLedger.ts` | Four-layer evidence schema (A immutable source / B canonical observations / C features / D adjudications) with a **rights gate**: no derivation without `APPROVED` rights + covering permitted-use. |

## Key safety properties (all test-enforced)

- **Suggests-only:** 19 forbidden proposal keys are rejected at runtime; proven in `forbidden-fields.test.ts` and re-proven directly against `.strict()`.
- **No identity spoofing:** `origin.kind` must be `AUTONOMOUS_ALPHA`; a proposal cannot masquerade as the authorised human provider route `sea-scalper-farouk`.
- **Evidence-tier confidence cap:** `CLAIMED ≤ 0.34`, `SCREENSHOT_ONLY ≤ 0.67`, `TICK_VERIFIED ≤ 1.0`. A module cannot claim high confidence on thin evidence.
- **Point-in-time integrity:** context refinement rejects post-`asOf` bars; session highs/lows are *running* extremes, never the completed session's.
- **Budget-honest conclusions:** a `SUPPORTED` verdict whose `trialsAttempted` exceeds the registered `maxCandidateCount` is rejected.
- **Rights gate:** `mayDerive()` returns false unless the source asset is `APPROVED` and the specific permitted-use flag is set.

## Backward-compatibility strategy

The wire schema carries an explicit `schemaVersion` (`SCHEMA_VERSION`, currently
`1.0.0`), pinned by a test so an accidental bump fails CI.

- **PATCH** (`1.0.x`): docs/comments, added *optional* fields with safe defaults. Old consumers keep working.
- **MINOR** (`1.x.0`): additive, backward-compatible fields. Producers may emit; consumers must ignore unknown-but-optional additions. Because proposals are `.strict()`, additive fields require a coordinated consumer update first — see "strict + additive" below.
- **MAJOR** (`x.0.0`): any breaking change (removed/renamed/retyped field, tightened enum). Requires a migration note here and a new `SchemaVersion` literal; mixed-version traffic must be gated at the adapter.

**strict + additive:** because every object uses `.strict()`, a producer emitting
a new field against an old consumer will be *rejected*, not silently accepted.
This is deliberate — we prefer a loud failure to silent drift. The rollout order
for any additive change is therefore: (1) ship consumer that tolerates the field,
(2) bump MINOR, (3) enable producer. The adapter boundary is the enforcement point.

## Build & test

```bash
npm install       # zod (runtime), typescript + vitest (dev)
npm run typecheck # strict tsc, no emit
npm run test      # vitest
npm run build     # emit dist/
```

> Offline note: this package was authored and verified in a network-isolated
> environment. Types were checked with `tsc` under full `strict` mode and all
> 53 assertions were executed via a minimal test shim. In a normal environment
> `npm install && npm test` runs the same files under vitest unchanged.

## What this package intentionally does NOT do

- It does not extract, transcribe, or reproduce any proprietary channel/video/indicator content. That is Track B, gated behind the Rights & Permitted-Use Register.
- It does not size positions, hold credentials, choose routes, or execute. Those live downstream, by design and by test.
