# INDICATOR vs DISCRETIONARY MATRIX — v0.1

Separates what the indicator MECHANICALLY produces from what Farouk applies as DISCRETION.

| Element | Indicator (FP-INDICATOR-005 / [kyle]) | Discretionary (Farouk) |
|---|---|---|
| Asia/London/US session H-L, Asia range | DRAWS them (toggles) | chooses which to focus on |
| FVG / IFVG / BPR / OB (multi-TF D/6H/4H/1H/15m) | DETECTS + draws | picks the "best" OB / extends box |
| CHoCH / Asia break / OB retest / Current OB / Fresh OB panel | COMPUTES the panel values | reads them as context |
| Sweep low/high, Engulfing, Asia Trap, BPR formed | EMITS as alertconditions | interprets vs structure |
| A+++ / A+ or better grades | EMITS a grade (formula UNKNOWN) | decides whether to act (NOT auto-trade) |
| Reversal-pattern (TZ/ST) tolerances 0.15/0.08/0.6/0.3 ATR | fixed inputs (current config) | enables/disables marks |
| Entry timing / session choice / "don't trade inside the orb" | — | DISCRETIONARY |
| Confluence count to qualify | NOT exposed | DISCRETIONARY / UNKNOWN |
| Trade management (TP1/BE/partials/runner/contingency) | — | DISCRETIONARY (management layer) |

**Boundary rule:** the indicator supplies OBJECTS + EVENTS + GRADES (observations); qualification-count,
session/family choice, and management are DISCRETIONARY. The state machine treats indicator output as untrusted
observations, never as authorised trades. Separate indicators ([kyle] v1/v2, SpaceMan, Market Cipher B,
Craters-Reality/EMA) are NOT merged into this suite's mechanics.
