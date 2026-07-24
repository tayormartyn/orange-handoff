# FAROUK STATE-MACHINE SPECIFICATION — v0.1

**DESIGN & ADJUDICATION ONLY. NO DETECTOR CODE. NOT CONNECTED TO QST. NO RISK/BROKER/EXECUTION.**
This spec formalises the 21 provisional candidate states (`FAROUK_STATE_MACHINE_CANDIDATES_v0.1.md`) into a
**hierarchical + orthogonal**, deterministic, evidence-traceable design. It is the Alpha *detector* design:
its single permitted output is an **observation** at `QUALIFIED_CANDIDATE`. It never sizes, routes, or
executes anything.

## 1. Architecture — orthogonal regions (not a flat enum)
Six Alpha regions run as coordinated automata; a seventh is reference-only and lives **outside** the detector:

| # | Region | Kind | States |
|---|---|---|---|
| 1 | SESSION_CONTEXT | concurrent context | 5 |
| 2 | VALUE_LOCATION | concurrent context (VWAP nested sub-axis) | 9 |
| 3 | LIQUIDITY_EVENT | concurrent context | 7 |
| 4 | ORB_EVENT | concurrent context | 7 |
| 5 | STRUCTURAL_SETUP | **per-setup-instance** lifecycle | 8 |
| 6 | QUALIFICATION | **per-setup-instance** lifecycle | 6 |
| 7 | CAMPAIGN_LIFECYCLE_REFERENCE_ONLY | **outside detector** | 6 |

- **Regions 1–4** are the market/context picture: exactly one active state each, advanced by events.
- **Regions 5–6** run once **per setup instance**; many instances may coexist, each with **immutable origin
  evidence**. This is why we do not collapse to one enum.
- **Region 7** documents the downstream trade lifecycle for reference; it is **NOT** part of the Alpha
  detector and carries **no** execution/broker/risk logic. `QUALIFIED_CANDIDATE → REF_HANDOFF` is an
  observation boundary only.

Counts: **42 Alpha states** (48 incl. reference), **45 transitions**, **45 guards**, **7 setup families**,
**18 event types**, **14 prospective tests**. Full data in the companion JSON/CSV files.

## 2. Supported component ownership (carried forward, not re-derived)
- **[kyle] v2** → relative-volume candles, Market-Session range boxes, multi-timeframe VWAP.
- **[kyle] v1** → POC, VAH, VAL, POC **"T" variants (meaning UNKNOWN)**, SFP, liquidity sweeps, ORB,
  MA inputs 20/21/34/50/55.
- **Smart Zones Strategy PRO / POC / POC Prototype** → present, internals unopened, **ownership UNKNOWN**.
  No unverified object is assigned to any indicator (`source_indicator` may be `UNKNOWN`, never guessed).

## 3. Setup families (each has its own branch — not one shared guard chain)
EVIDENCE_SUPPORTED: `ORB_CONTINUATION`, `ORB_FAILED_BREAKOUT`, `SFP_REVERSAL`. PARTIALLY_SUPPORTED:
`POC_VALUE_REJECTION`, `VWAP_RECLAIM_OR_REJECTION`. HYPOTHESIS_ONLY: `STRONG_OB_REVERSAL`,
`FVG_CONTINUATION`. (Feasibility is tracked separately — e.g. SFP_REVERSAL is evidence-supported but its
**implementation is BLOCKED** by repaint/timing unknowns.) See `FAROUK_SETUP_FAMILIES_v0.1.json`.

## 4. Event model
18 deterministic event types (`FAROUK_EVENT_SCHEMA_v0.1.json`). Every event carries the common envelope:
`event_id, timestamp_utc, source_timezone, symbol, timeframe, bar_open_time, bar_close_time, bid, ask, mid,
rule_version, source_indicator, evidence_confidence`. Intrabar events (`BAR_UPDATED`, and any marker) carry
an `INTRABAR_WARNING`; confirmation guards must wait for `BAR_CLOSED` unless future evidence explicitly
permits intrabar (Invariant I-2).

## 5. Timezone policy (abstraction layer — no canonical TZ selected)
All internal timestamps are **UTC**. Each event/state retains: **original chart timezone**, **indicator
timezone**, **session-definition timezone**, and **daylight-saving context**. A canonical "Farouk timezone"
is **deliberately NOT chosen** (evidence conflicts: [kyle] v2 sessions = GMT, [kyle] v1 ORB = GMT+1, FP-001
chart = UTC+1, campaigns = UTC+2). Every timezone-dependent transition (session/ORB start/end) is marked
**BLOCKED** with failure code `F_TZ_UNKNOWN` until the layer is resolved.

## 6. Unknown policy (fail-closed)
Unresolved inputs never silently pass a guard. Handling ∈ {`BLOCK_TRANSITION`, `DEGRADE_CONFIDENCE`,
`RESEARCH_ONLY`, `NOT_APPLICABLE`}. The catch-all veto `G_ANY_UNKNOWN_GUARD` **blocks** any transition whose
required input is UNKNOWN. Details in `FAROUK_UNKNOWN_POLICY_v0.1.md`.

## 7. Guards & transitions
Every transition (`FAROUK_TRANSITION_CATALOG_v0.1.json`) specifies source, destination, triggering event,
required guards, veto guards, timeout/expiry, evidence source, implementation feasibility, unresolved
threshold, and a failure reason code. Guards (`FAROUK_GUARD_CATALOG_v0.1.json`) are **Boolean / veto /
data-availability only** — see §8.

## 8. No probability model (v0.1)
v0.1 uses ONLY: Boolean guard status, evidence confidence (HIGH/MEDIUM/LOW/UNKNOWN), missing-data status,
veto reason, and setup-family classification. **No historical win-rate scoring and no machine-learned
probability.** Promotional phrases ("high probability", "beautiful") are never converted to validated
performance.

## 9. Invariants
See `FAROUK_INVARIANTS_v0.1.md` — including: no `QUALIFIED_CANDIDATE` before a registered zone/event; no
`BREAKOUT_CONFIRMED` on an unclosed candle; UNKNOWN timezone cannot qualify a session-dependent setup;
expired/invalidated setups cannot return to `ARMED` without a new identity; immutable setup origin; and
**no Alpha transition may create risk, size, or broker instructions**.

## 10. Feasibility snapshot
- **Deterministic now** (given levels + closed bars): `BREAKOUT_CONFIRMED`, `FAILED_BREAKOUT`, immutable
  origin capture, bias reset, and the fail-closed UNKNOWN veto.
- **Blocked**: everything gated on timezone, value-area/POC calc (+ "T"), SFP repaint/timing, and the
  confluence count. See `FAROUK_IMPLEMENTATION_BLOCKERS_v0.1.md`.

**This document and its companions are design artifacts only. No detector code exists; nothing is wired to
QST, risk, broker, or execution.**
