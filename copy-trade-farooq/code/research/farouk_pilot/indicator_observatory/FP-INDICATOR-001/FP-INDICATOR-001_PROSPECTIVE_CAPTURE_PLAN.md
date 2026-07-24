# FP-INDICATOR-001 — PROSPECTIVE CAPTURE PLAN

## Why this exists
A historical teaching recording **cannot** establish whether an indicator repaints, how it behaves intrabar,
whether its signals are closed-bar-only, or whether it has any predictive/causal value. Farouk did **not**
explicitly demonstrate or state any of these properties in this session. Therefore this document makes **no**
such claim; it specifies a **future, forward-only (prospective)** capture protocol to test them on live data.
This is an observation/measurement plan — **not** detector code and **not** a trading system.

## Governing rules
- Forward-only: capture state as bars form in real time; never rely on historical re-rendering.
- No execution: observation only. QST, risk policy, broker config and execution gates stay unchanged/OFF.
- No cloud upload of captured media; local storage under the pilot workspace.
- Every capture stamped with: wall-clock (UTC), symbol, feed, timeframe, bar-open time, and indicator name+version.

## What to capture (per indicator: [kyle] v1, [kyle] v2, Smart Zones Strategy PRO, POC, POC Prototype)

### 1. Intrabar state capture
- At fixed sub-bar intervals (e.g. every 5–15 s) during a forming bar, record every plotted value/level/marker
  (POC lines, ORB range, SFP/circle markers, MA values, zone edges, bias colour).
- Goal: does a level/marker **appear, move, or disappear mid-bar** before the bar closes?

### 2. Bar-close state capture
- At each bar close, snapshot the same objects.
- Compare the last intrabar snapshot to the closed-bar snapshot: did anything **change at close**?

### 3. Historical-state persistence (repaint / recalculation)
- Re-open the identical chart/timeframe/feed **N hours and N days later** and snapshot the SAME historical bars.
- Diff against the originally captured live state for those bars. **Any difference = repaint/recalculation.**
- Test across: timeframe change, symbol reload, layout reload, and TradingView session restart.

### 4. Alert timing
- Configure the indicator's native alerts (if any). Log alert-fire wall-clock vs bar-open and bar-close times.
- Goal: do alerts fire **intrabar** (potentially non-final) or **only on bar close**? Any re-fire / retraction?

### 5. Repaint / recalculation checks (targeted)
- POC & POC "T" variants: watch whether a session's POC line **shifts** as volume accumulates intrabar and
  whether it **freezes** at session end; whether the "T" variant locks at a different time than the base.
- ORB: confirm the range freezes after the stated 15-min window and does not later redraw.
- SFP / circle markers: confirm whether a marker printed intrabar **survives** the bar close or is removed.
- Smart Zones: whether a zone is **extended/removed retroactively** once mitigated.

## Deliverables of the prospective run (future)
- `prospective/<indicator>/<date>/intrabar_log.csv`, `barclose_log.csv`, `persistence_diff.json`,
  `alert_timing.csv`, and a short `REPAINT_VERDICT.md` per indicator (REPAINTS / NON-REPAINTING /
  INCONCLUSIVE — **evidence-graded, never assumed**).

## Explicit non-claims (until a prospective run proves otherwise)
- NON-REPAINTING — **not claimed**.
- Closed-bar-only behaviour — **not claimed**.
- Intrabar stability — **not claimed**.
- Predictive / causal value — **not claimed**.
