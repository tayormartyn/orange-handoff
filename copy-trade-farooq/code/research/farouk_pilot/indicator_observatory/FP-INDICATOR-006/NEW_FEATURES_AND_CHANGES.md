# FP-INDICATOR-006 — NEW FEATURES & CHANGES

Same indicator as FP-INDICATOR-005 ("Farouk's Playbook — Smart Money Suite"). Classification of each item per:
CONFIRMED_NEW · CONFIRMED_EXISTING · FULLER_VERSION · CURRENT_VISIBLE_CONFIG · POSSIBLE_DEFAULT · CONTRADICTION · UNRESOLVED.

## Newly VISIBLE settings (the detection engine — never shown in FP-INDICATOR-005)
| Setting | Value | Class |
|---|---|---|
| Show CHoCH | ON | CURRENT_VISIBLE_CONFIG |
| **CHoCH pivot length** | **5** | CONFIRMED_NEW / CURRENT_VISIBLE_CONFIG |
| **FVG lookback (bars)** | **50** | CONFIRMED_NEW / CURRENT_VISIBLE_CONFIG |
| **Min FVG size (x ATR)** | **0.5** | CONFIRMED_NEW / CURRENT_VISIBLE_CONFIG |
| **Min BPR overlap (x ATR)** | **0.2** | CONFIRMED_NEW / CURRENT_VISIBLE_CONFIG |
| **Auto-remove filled FVG/BPR** | **ON** | CONFIRMED_NEW / CURRENT_VISIBLE_CONFIG |
| **Max zones kept per type** | **10** | CONFIRMED_NEW / CURRENT_VISIBLE_CONFIG |

**No POSSIBLE_DEFAULT / no proven default:** a "Defaults" dropdown is visible at the dialog bottom but was
**never clicked** — no reset-to-default action → none of the above are proven factory defaults. Farouk: "I did
this in the input… you can change it on your own" → CURRENT config.

## Reconfirmed (same as FP-INDICATOR-005) — CONFIRMED_EXISTING / CURRENT_VISIBLE_CONFIG
Chart label size = Tiny; Box extension = 50; TZ/ST tol 0.15; Tweezer 0.08; Star big 0.6; Star small 0.3; Only
show TZ/ST at OB edge/Asia H-L = ON; DISPLAY toggles (FVG/BPR/OB/Asia ON, London toggled, US/IFVG/engulfing OFF).

## Features (verbal + visual)
- **London high/low + US high/low liquidity** — CONFIRMED_EXISTING (re-demonstrated; "I added London/US high-low").
- **Extend-box / remove** and **chart-label sizing** — CONFIRMED_EXISTING (re-demonstrated).
- **Alarms fire on events** (e.g. Asia-high break) — CONFIRMED_EXISTING (existence; no timing detail).
- **Weekly reset** ("Monday the chart will reset") — CONFIRMED_NEW behavioural note.
- **Auto-zone management** (auto-remove filled, keep max 10) — CONFIRMED_NEW (partial answer to level-validity).
- **The CHoCH/Asia-break/OB-retest/Current-OB/Fresh-OB panel** — CONFIRMED_EXISTING (shown live).

## NOT shown (still UNRESOLVED settings)
Normal/Strong OB impulse thresholds; equal-high/low lookback; ORDER BLOCK/LIQUIDITY numeric values (section
header seen, values below the cut-off); Asia/London/US session-hours field; timezone field; HTF-OB selection
control; alert timing/message/repaint settings.
