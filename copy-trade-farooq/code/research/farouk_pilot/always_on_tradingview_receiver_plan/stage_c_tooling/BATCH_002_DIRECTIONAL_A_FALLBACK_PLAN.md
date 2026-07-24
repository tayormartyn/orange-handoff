# Batch 002 — Directional-A Fallback Plan (design only)

**Mode: LOW-NOISE DIRECTIONAL-A FALLBACK DESIGN ONLY.** Claude changes nothing here. No TradingView alert
touched, no Worker deploy, no R2, no broker/cTrader/QST, no permit/lease/order, no gate change. **No webhook
URL / secret path printed.** `NOT_INTEGRATION_READY` unchanged.

## Problem

Every useful detector sequence ends in a **directional A** (`A_LONG` / `A_SHORT`). The Farouk Playbook
indicator exposes **no discrete A LONG / A SHORT condition** (confirmed by Martyn), so `LIVE006`/`LIVE007`
cannot be built. The A-directional texts (`A LONG`, `A SHORT`) only fire through the indicator's
**`alert()` catch-all**, i.e. the noisy `LIVE001_ANY_ALERT` (Engulfing + A + everything, ~6.4/h).

## Recommendation (safest, lowest-risk) — NO Worker change

**Pair four discrete mirrors with ONE time-boxed, locally-filtered ANY_ALERT fallback, all pointed at the
existing PURE logging-only Worker path. Filter A LONG / A SHORT OFFLINE. No Worker change.**

1. **Four discrete mirrors → main pure path** (clean, low-volume, permanent-ish until captured):
   `LIVE008_CHOCH_UP_MIRROR_BATCH002`, `LIVE009_CHOCH_DOWN_MIRROR_BATCH002`,
   `LIVE010_SWEEP_HIGH_MIRROR_BATCH002`, `LIVE011_SWEEP_LOW_MIRROR_BATCH002` (per
   `BATCH_002_LOW_NOISE_MIRROR_SETUP_CHECKLIST.md`).
2. **One time-boxed ANY_ALERT duplicate → main pure path**, for A LONG / A SHORT only:
   `LIVE012_ANY_ALERT_TIMEBOX_A_ONLY_BATCH002`. **Armed only during a short, controlled observation window**
   (e.g. one active session, hours not days), then **disabled/deleted immediately**. This bounds the flood
   to the window instead of running permanently.
3. **Local (offline) whitelist filter** extracts only `A LONG` / `A SHORT` raw texts from that window's R2
   objects; Engulfing / BPR / anything else is **ignored at processing time** (not fed to the pipeline). The
   discrete CHoCH/Sweep events come from the clean mirrors.

**Why this is safest:** the proven Worker stays **pure logging-only** (lossless, append-only, unchanged
invariant — sha `30bdc54d…`); **no deploy, no secret handling, no route change.** The only cost is a
*bounded* set of extra R2 objects during the time-box window (append-only, harmless), removed from
consideration by the local filter. Noise is controlled by **time-boxing (source side)** + **whitelist
(processing side)** — never a permanent unfiltered flood.

## Is ANY_ALERT unavoidable?

**As the only SOURCE of A LONG / A SHORT — yes, currently unavoidable** (no discrete condition exists). But
it must be **time-boxed and filtered**, **never permanent or unfiltered**.

## Rejected alternatives

- **Permanent ANY_ALERT mirror — REJECTED.** Continuous flood (~6.4/h, peak 14/h; Engulfing + A noise) buries
  the sequence structure and inflates R2 indefinitely. Defeats the low-noise goal.
- **Worker-side filter on the MAIN pure path (global whitelist) — REJECTED.** It breaks the main path's
  **lossless / append-only, never-discard-at-ingest** invariant, and a global "A-only" filter would wrongly
  drop the CHoCH/Sweep discrete-mirror events we want. Mutating the proven pure path is the highest risk.
- **Un-timeboxed local-only filter with permanent ANY_ALERT — REJECTED** (still a permanent flood).

## Optional (only if window R2 noise is unacceptable) — separate FILTERED endpoint

If bounded window-noise in R2 is still not wanted, a **separately-approved, documented, tested filtered
endpoint** is the alternative: add a **NEW secret path** to the Worker that applies an **A-only whitelist**
(persist only raw texts containing `A LONG` / `A SHORT`; **do not persist** Engulfing/BPR/Sweep/CHoCH from
that path), while the **main pure path stays untouched**. The `LIVE012` time-box mirror would point at the
filtered path; the four discrete mirrors stay on the main pure path.
- **This IS a Worker change (additive route)** → requires explicit approval, a **test suite**, and a
  **revert plan** (below). Offered as an option, **not** the default. Default = no Worker change.

## Worker changes required?

- **Recommended path: NONE.** Worker remains pure logging-only; all mirrors use the existing main path;
  filtering is offline.
- **Optional filtered-endpoint path: YES** (additive, isolated, tested, reverted) — only if approved.

## Should the four discrete CHoCH/Sweep mirrors still be created?

**Yes.** They are clean, low-volume, and unaffected by this fallback. Create LIVE008–LIVE011 as planned.

## Exact alert names (if approved)

- Create: `LIVE008_CHOCH_UP_MIRROR_BATCH002`, `LIVE009_CHOCH_DOWN_MIRROR_BATCH002`,
  `LIVE010_SWEEP_HIGH_MIRROR_BATCH002`, `LIVE011_SWEEP_LOW_MIRROR_BATCH002`
  (discrete duplicates → main pure path).
- Create (time-boxed): `LIVE012_ANY_ALERT_TIMEBOX_A_ONLY_BATCH002` (duplicate of `LIVE001_ANY_ALERT`, →
  main pure path, armed only for a controlled window, disabled/deleted immediately after).
- **Do NOT create:** `LIVE006_A_LONG_MIRROR_BATCH002`, `LIVE007_A_SHORT_MIRROR_BATCH002` (no source
  condition); any **permanent** ANY_ALERT mirror; Engulfing mirrors.

## Risk assessment

| Path | Worker risk | R2 noise | Operator burden | Verdict |
|---|---|---|---|---|
| Recommended (time-box + local filter) | **none** (pure path unchanged) | bounded to window (append-only) | arm/disarm the time-box mirror | **LOW — recommended** |
| Optional filtered endpoint | medium (additive route; secret path; deploy) | near-zero | approve + test + revert | acceptable only if approved |
| Permanent ANY_ALERT | none (Worker) | **unbounded flood** | none | **rejected** |
| Global filter on main path | **high** (breaks invariant; drops wanted events) | — | — | **rejected** |

## Rollback plan

- **Time-box mirror:** disable/delete `LIVE012` in TradingView after the window. **No Worker state to
  revert** (Worker never changed). Originals untouched throughout.
- **If the optional filtered endpoint is ever used:** revert Worker to the pure logging-only baseline
  (src sha256 `30bdc54d…`), remove the filtered route, redeploy, and run negative checks (filtered path →
  404/405, wrong path → 404, GET → 405), exactly as done for the temporary read branches.

## Test plan

- **Recommended path (offline filter):** unit-test a pure `is_directional_A(raw_text)` whitelist — ACCEPT
  `"A LONG"` / `"A SHORT"`; REJECT `Engulfing` / `BPR tapped` / `CHoCH …` / `Sweep …` / empty; case/space
  tolerant. Pure function, **no Worker risk**. Validate the window's captured objects are filtered to A-only
  before pipeline entry.
- **Optional filtered endpoint (only if approved):** tests that the filtered path **persists** A LONG/A SHORT
  and **does not persist** Engulfing/BPR/Sweep/CHoCH; that the **main path is byte-identical to baseline**
  (still lossless); import-firewall / no-broker-imports; negative checks; secret never printed; revert
  restores baseline sha.

## Why permanent ANY_ALERT stays rejected

It is a continuous, unfiltered flood (Engulfing + A + all events) that buries structure, inflates R2
indefinitely, and re-introduces exactly the noise Batch 002 was designed to avoid. The fallback captures the
same A-directional signal with a **bounded window + filter** instead.

## Exact Martyn steps (if approved) — no webhook URL here

1. Create the **four discrete mirrors** (LIVE008–LIVE011) per the low-noise checklist (duplicate-first,
   webhook from your gitignored local file pasted **into TradingView only**, originals untouched).
2. For the A-directional fallback, **duplicate `LIVE001_ANY_ALERT`** → rename copy
   `LIVE012_ANY_ALERT_TIMEBOX_A_ONLY_BATCH002` → add the same Worker webhook (from the local file, into
   TradingView only) → **arm it for a short, agreed window only**.
3. Tell Claude when it's armed and when you disable it. Claude will (read-only) verify R2, then locally
   filter the window to `A LONG` / `A SHORT`, and run the pipeline.
4. **Disable/delete `LIVE012` immediately after the window.** Do **not** leave it running.

## Guardrails (unchanged)

Capture/observation-only; duplicate-first; originals never touched; no broker/order/execution/route/account/
risk/lot field anywhere; no permit/lease/order; Worker stays pure logging-only (recommended path); any
temporary Worker change (optional path) is tested + reverted; webhook secret never printed; gates stay
`PAPER/PREVIEW/False/False`; Telegram PREVIEW listener PID 16608 left running; `NOT_INTEGRATION_READY`
unchanged. **Nothing here is trade-ready.**
