# FP-INDICATOR-006 — SYNTHESIS IMPACT

Proposal-level impact on the synthesis candidates. **No candidate file is modified here** (governance).

## Impact on FAROUK_METHODOLOGY_CANDIDATE_v0.3
- **Layer 2 (location objects)** — FVG/BPR object definitions gain concrete detection parameters: FVG needs
  **>= 0.5 ATR** and a **50-bar lookback**; BPR needs **>= 0.2 ATR overlap**; filled FVG/BPR are auto-removed;
  max 10 zones/type. (Recorded as INDICATOR_MECHANIC current-config, not universal law.)
- **Layer 3 (event primitives)** — CHoCH gains a concrete **pivot length = 5** (indicator mechanic); candle-close
  confirmation reinforced.
- **Layer 5 (qualification)** — **unchanged**: A+/A+++ formula/count still not exposed; "high probability" and
  the Asia-break percentages (80/85%) are EXPLANATORY_MARKET_NARRATIVE, not a promotable grade rule.
- **Layer 1 (context)** — Asia range 00-07 UTC (methodology note) + chart TZ user-local (UTC+2 here) reinforce
  that there is **no canonical timezone**.

## Impact on FAROUK_STATE_MACHINE_CANDIDATE_v0.2
- **ALERT_INTAKE region unchanged** — alarms confirmed to exist/fire on events, but timing/repaint/payload/
  duplicates still UNKNOWN → the untrusted-observation + fail-closed + repaint-guard design stands; still
  BLOCKED_BY_LIVE_VALIDATION.
- The **auto-remove filled + max-zones** mechanic supports a concrete **stale-event / dedup** basis for
  EVENT_DEDUPLICATED (a filled zone is retired by the tool) — helpful, though still indicator-side.

## Promotion-status deltas (proposal only)
- FVG/BPR/CHoCH detection params move from BLOCKED_BY_THRESHOLD → **RESEARCH_ONLY / CURRENT_VISIBLE_CONFIG**
  (known values, but single-session current config; not proven defaults or universal thresholds).
- A+/A+++, OB-impulse, mitigation-numeric, POC-T remain **BLOCKED**.
