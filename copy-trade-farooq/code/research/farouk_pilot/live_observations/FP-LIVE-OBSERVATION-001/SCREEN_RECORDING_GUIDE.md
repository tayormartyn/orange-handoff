# SCREEN RECORDING GUIDE

A continuous screen recording is the primary evidence for **timing** and **repaint**; screenshots are the
index. Store under `FP-LIVE-OBSERVATION-001/recordings/`.

## Setup
- Record the full TradingView window incl. the **bottom-right clock** (chart TZ) and the **notification toasts**.
- Keep the **indicator panel** (TF/CHoCH/Asia break/OB retest/Current/Fresh OB) in frame at all times.
- Capture a visible **UTC wall-clock** (OS clock or an on-screen UTC clock) so alert-arrival vs candle-close can
  be measured to the second.
- Frame rate: enough to see the bar close and the toast appear (>= 15 fps). Note resolution.

## During the window
- Start recording BEFORE the first bar of interest; keep running across at least +5 bars of each event.
- Do a brief cursor "point" at each toast as it arrives (helps locate events later).
- If an alert fires **intrabar**, let the bar finish on camera (do not cut) — that is the timing evidence.

## Naming
`recording_<UTCyyyymmddThhmmZ>_<segment>.mp4` (or .mov). Log start/stop UTC in the run log.

## After
- Do not edit/trim the master recording; derive clips if needed. Hash the master into the run log.
- Cross-reference each observation's obsid to a recording timestamp.
