# FP-INDICATOR-006 — FINDINGS

## Classification
**FP-INDICATOR-006**, **MIXED_SOURCE (indicator-primary)** — one physical source; separated evidence sections
(INDICATOR_WALKTHROUGH / METHODOLOGY_TEACHING / MARKET_UPDATE). Same indicator as FP-INDICATOR-005.

## Biggest wins
1. **Detection-engine settings revealed** (never seen before): CHoCH pivot **5**, FVG lookback **50**, Min FVG
   **0.5 ATR**, Min BPR overlap **0.2 ATR**, Auto-remove filled FVG/BPR **ON**, Max zones **10**. FULLER_VERSION
   of the FP-INDICATOR-005 settings — but CURRENT_VISIBLE_CONFIG, **not proven defaults** (Defaults never clicked).
2. **Campaign panel attribution CONFIRMED** — the CHoCH/Asia-break/OB-retest/Current-OB/Fresh-OB panel is shown
   live as this indicator's output (answers Q27).
3. **Candle-close corroborated** — Farouk requires a candle close (5m/15m/hourly) above the zone; "no candle
   close = no entry"; "CHoCH is the strongest form of confirmation."
4. **Timezone confirmed user-local** — chart TZ = UTC+2 (vs UTC+1 in the alert screenshots) → no canonical system TZ.

## Corroborated (existing)
London/US high-low liquidity feature; mitigation (valid-if-unmitigated, timeframe-relative); HTF OBs (D/1H/4H);
IFVG; extend-box; the alarms exist and fire on events.

## Not advanced
A+/A+++ formula, minimum confluence count, all-boxes-vs-graded, OB-impulse thresholds, equal-high/low lookback,
mitigation numeric, POC-T / Volume-Profile window, nBOS/OTE/RTO/EQH/EQL (absent), and **all alert timing/repaint/
payload/duplicate** questions.

## Narrative flags (excluded from rules)
"22-year gold edge; 80% continuation if break Asia high, 85% if break Asia low" — statistical/promotional
narrative (EXPLANATORY_MARKET_NARRATIVE), not a promotable grade/threshold.
