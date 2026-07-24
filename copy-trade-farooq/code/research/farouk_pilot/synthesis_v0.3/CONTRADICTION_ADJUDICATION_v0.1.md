# CONTRADICTION ADJUDICATION — v0.1

Each classified as TRUE_CONTRADICTION · CONTEXT_DEPENDENT · SETUP_FAMILY_SPECIFIC · INDICATOR_SPECIFIC ·
TERMINOLOGY_CONFLICT · UNRESOLVED.

1. **BOS candle close required vs not mandatory** — FP-EDU-016 ("wait for a candle close; wicks = fakeouts")
   vs FP-EDU-021 ("a candle close is preferred but not mandatory"). → **TRUE_CONTRADICTION** (same concept,
   same author, opposite modality). Blocks R-BOS-CANDLECLOSE until resolved.
2. **CHoCH optional vs required** — some docs list CHoCH as a confirmation; C003/C004 qualified with panel
   CHoCH=X on the entry TF. → **SETUP_FAMILY_SPECIFIC** (CHoCH is required in some families, absent-tolerant in
   others). Not a true contradiction.
3. **FVG full fill vs IFVG conversion** — FVG "invalid once filled" (Playbook) vs IFVG = an inverted/used FVG
   that keeps acting as a level (FP-INDICATOR-005 "Show IFVG"). → **TERMINOLOGY_CONFLICT** (a filled FVG can
   become an IFVG; "invalid" and "inverted" describe different post-fill states). Needs the fill/partial rule.
4. **Mitigation vs zone spent** — mitigation = price returns to rebalance a zone (008) vs a "spent"/mitigated OB
   should be avoided (FP-EDU-004 weak-OB). → **CONTEXT_DEPENDENT** (first mitigation = tradable; repeated
   mitigation = spent). Blocked by the touch-count threshold.
5. **Fixed timeframe pairs vs flexible hierarchy** — Playbook "5m→3m→1m"; Vishal "1H→15→5→1"; campaigns "H4/H1/
   3m/5m". → **SETUP_FAMILY_SPECIFIC / method-specific** (each method uses its own TF set). Not a contradiction.
6. **All-boxes veto vs graded confluence** — Playbook "every box must pass / if one fails, skip" (pp.14/21) vs
   the 6/6 & 6/8 graded stack rules (5/6 & 5/8 = half lot) and the A+++/A+ letter grades. → **TRUE_CONTRADICTION**
   within the Playbook (all-or-nothing veto vs graded partial-pass), documented in the errata; unresolved.
7. **Manual discretionary rules vs indicator mechanics** — Farouk's spoken discretion (session choice, "I don't
   trade inside the orb", "signal times do nothing") vs the indicator's fixed alertconditions/objects. →
   **INDICATOR_SPECIFIC / CONTEXT_DEPENDENT** (the indicator draws objects/emits grades; Farouk applies
   discretion on top). Not a contradiction; a layer boundary (see INDICATOR_VS_DISCRETIONARY_MATRIX).
8. **Selectable bar-close frequency vs script-controlled alert timing** — named alertconditions offer "Once per
   bar close" (user-selectable) vs "Any alert() function call" whose frequency/timing is script-controlled and
   not UI-settable. → **INDICATOR_SPECIFIC** (two different alert mechanisms coexist). Not a contradiction, but
   the actual timing/repaint of both is UNRESOLVED → BLOCKED_BY_LIVE_VALIDATION.

## Summary
TRUE_CONTRADICTION: #1 (BOS candle-close), #6 (all-boxes vs graded). SETUP_FAMILY_SPECIFIC: #2, #5.
CONTEXT_DEPENDENT: #4, (#7). TERMINOLOGY_CONFLICT: #3. INDICATOR_SPECIFIC: #7, #8. UNRESOLVED live-dependency: #8.
