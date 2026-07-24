# FAROUK STATE-MACHINE — IMPLEMENTATION BLOCKERS — v0.1

What must be resolved **before** any deterministic detector could be coded. Ordered by how many transitions
each blocker gates. None of these is a coding task yet — each is an **evidence** task.

## Blocking (a coded detector cannot be correct without these)
1. **Canonical timezone / TZ-abstraction resolution** — blocks every session/ORB start-end transition
   (`SC-01, SC-04, OE-01, OE-06`) and, via Invariant I-6, any session-dependent qualification.
   Conflict: [kyle] v2 sessions = GMT, [kyle] v1 ORB = GMT+1, FP-001 chart = UTC+1, campaigns = UTC+2.
   *Resolve:* TM-04/05 + a stated canonical source.
2. **Value-area / POC calculation + POC "T" meaning** — blocks all VALUE_LOCATION transitions
   (`VL-01..VL-06`) and the POC_VALUE_REJECTION family. The engine (fixed-range per period), the VAH/VAL %,
   and the "T" variant are undefined. *Resolve:* settings Visibility tab + TM-09.
3. **Repaint / intrabar-vs-closed-bar timing** — blocks SFP confirmation (`LE-05, LE-06`) and constrains
   ORB confirmation (I-2). No video states it. *Resolve:* prospective capture TM-01/02/03/08.
4. **Confluence threshold** — blocks the terminal `QU-02 → QUALIFIED_CANDIDATE`. Farouk says "combine" but
   never states how many factors are mandatory. *Resolve:* live-trading videos + adjudication.

## Partial (interim proxy possible, flagged low-confidence)
5. **Exact stop / invalidation rule** — `SS-07/08` use structural close-through as a proxy (DEGRADE).
6. **Wick-vs-close break rule for the ORB** — close path deterministic; wick path degraded (`OE-03`).
7. **VWAP anchor / session-reset behaviour + which VWAP timeframe** — bias usable at low confidence.
8. **Proximity / retrace / mitigation / max-age thresholds** — all currently unset (`F_THRESHOLD_UNSET`).
9. **Liquidity-sweep lookback** (spoken "8 bars") — confirm the setting.

## Not-applicable / research-only (do not block v0.1 supported families)
10. **MA trend filter** (which of 20/21/34/50/55) — Farouk never uses them; RESEARCH_ONLY.
11. **Smart Zones / POC / POC Prototype internals** — no object attributed; NOT_APPLICABLE until opened.
12. **STRONG_OB_REVERSAL / FVG_CONTINUATION families** — HYPOTHESIS_ONLY; no indicator object owns them
    here; excluded from any near-term build.

## Feasibility roll-up
- **Deterministic now** (given a resolved level + closed bars): `BREAKOUT_CONFIRMED` (OE-04),
  `FAILED_BREAKOUT` (OE-05), immutable origin capture (SS-02), bias reset (QU-06), the fail-closed UNKNOWN
  veto, and session-close→reset (SC-05).
- **Blocked** until items 1–4 resolve: all value/POC transitions, SFP confirmation, session/ORB timing,
  and the final qualification step.

## Explicit non-goals for v0.1
No detector code; no probability/win-rate model; no QST wiring; no risk/size/broker/execution logic; no edit
to `FAROUK_METHODOLOGY_SPEC_v0.2.1`. The next evidence input expected: the promised **live-trading** videos
(should resolve confluence + some timing) and a **settings/Visibility** capture (value-area, POC "T",
Smart Zones).
