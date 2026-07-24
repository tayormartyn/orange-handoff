# FP-LIVE-OBSERVATION-001 — REPAINT & MUTATION ANALYSIS (first set)

Method: compare the same chart objects across the post-event frames 06:41:10 → 06:57:52 → 07:02:15
(≈ +2 to +21 candles after the 06:33 events, and +2..+5 after 06:57).

## Marker / zone persistence
- Historical **OB / FVG / BPR** zones (the 03:00–05:00 region: BPR ~4194, FVG ~4188, OB ~4183) appear in the
  **same price positions** in all three frames — no shift, no disappearance.
- **CHoCH / TZ / ST** labels on historical bars are in the same positions across frames.
- **Asia High / Asia Low** lines unchanged.
- A new lower **FVG** appeared near price as the market fell — this is normal forward drawing, not a mutation of
  a prior object.
→ **No visible repaint of already-formed markers/zones** over the observed window.

## Panel mutation
Panel values **Current OB 4183.43 / Fresh OB 4183.43 / CHoCH X / Asia break LOW / OB retest X** are identical in
the 06:41, 06:49 and 06:57 frames. → **Panel stable**, no mutation across the window. (CHoCH stayed X through both
the LONG (06:33) and SHORT (06:57) composites.)

## +1 / +5 candle persistence
- **+1 candle:** the 06:33 markers/zones and panel persist unchanged into the next frame.
- **+5 candles:** the 06:33 objects still present and unmoved at 06:57/07:02 (≈ +8..+21 candles); the 06:57
  objects persist into 07:00/07:02. → **persistence PASS on the available frames.**

## Repaint verdict (careful)
- **No repaint OBSERVED** in the post-alert screenshots.
- **NOT fully proven "non-repainting"**: the captures are post-hoc; there is no frame captured at the exact firing
  instant showing the marker forming intrabar and then confirming at close. A marker that repaints *before* the
  first screenshot would not be visible here. → repaint remains **NOT_FULLY_VERIFIED** (needs an at-firing
  capture / screen recording across the close).

## Net
Post-alert **state stability is strong** (zones, marks, panel all stable +1..+~21 candles); **intrabar repaint at
the moment of firing is unverified**.


---
# CONTINUATION SET 002 — repaint/mutation
- Panel stable across the window and in Recording 2 (CHoCH X / Asia break LOW / Current OB 4183.43 / Fresh OB
  4183.43) — no mutation after firings.
- Historical OB/FVG/BPR zones + CHoCH/TZ/ST marks unchanged across the 06:37 (Rec2) and 07:45–08:19 frames; a
  new lower FVG drew forward as price fell (normal), no historical-object mutation.
- **Still no clean intrabar-at-firing marker capture**: Recording 1 was an alert-SETUP session (dialogs
  obscured the chart), so whether a marker flickers intrabar before confirming at close remains unproven.
- Net: post-alert state stability further corroborated (C4 improved but not fully verified).


---
# CONTINUATION SET 003 — panel field update on CHoCH
- At 08:42 the panel CHoCH field changed X -> 4159.66 with the CHoCH-up event, and a green "CHoCH" label appeared
  near price. This is an EXPECTED on-event field update, NOT a repaint of historical OB/FVG/BPR zones (stable
  across 08:35-08:47). Current/Fresh OB 4183.43, Asia break LOW, OB retest X otherwise stable.
- Still no clean intrabar-at-firing marker capture (set-3 = screenshots) -> C4 remains PARTIAL. The panel's CHoCH
  field is dynamic by design; panel-value changes are live state, not repaint.
