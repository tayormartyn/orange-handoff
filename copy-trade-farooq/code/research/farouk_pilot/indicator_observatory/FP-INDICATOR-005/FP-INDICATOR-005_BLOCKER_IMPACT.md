# FP-INDICATOR-005 — BLOCKER IMPACT

The update demo exposed only the **DISPLAY / CHART-LABELS / BOXES / PATTERNS** settings; the **detection-engine
inputs were never shown** (no scroll, no reset-to-default). So most of the requested verification targets remain
UNKNOWN, but a few pattern tolerances were captured.

## Verification of the requested targets
| Requested value | Status | Evidence |
|---|---|---|
| CHoCH pivot length | **NOT SHOWN → UNKNOWN** | detection section not scrolled to |
| FVG lookback | **NOT SHOWN → UNKNOWN** | — |
| minimum FVG size in ATR | **NOT SHOWN → UNKNOWN** | — |
| BPR overlap threshold | **NOT SHOWN → UNKNOWN** | — |
| automatic FVG/BPR removal | **NOT SHOWN → UNKNOWN** | — |
| maximum zones | **NOT SHOWN → UNKNOWN** | — |
| ordinary OB impulse threshold | **NOT SHOWN → UNKNOWN** | — |
| Strong OB impulse threshold | **NOT SHOWN → UNKNOWN** | — |
| equal-high/low lookback | **NOT SHOWN → UNKNOWN** | — |
| higher-timeframe OB selections | **PARTIAL** | OB **D/6H/4H/1H/15m** shown ON CHART; the selecting control not shown ("all vs default/high-time" spoken) |
| Asia-session hours + timezone field | **NOT SHOWN → UNKNOWN** | Asia range drawn, but the hours/timezone inputs not shown |
| box-extension settings | **VERIFIED** | Extend-to-right = OFF; **Box extension = 50 bars** |
| reversal-pattern tolerances | **VERIFIED** | TZ/ST 0.15×ATR; Tweezer 0.08×ATR; Star big body 0.6×ATR; Star small body 0.3×ATR; "Only show TZ/ST at OB edge/Asia H-L" ON |
| London and US high/low functionality | **VERIFIED** | toggles present (London ON/blue, US OFF/yellow) = session liquidity |
| IFVG functionality | **VERIFIED** | "Show IFVG" toggle (inverted FVG) — OFF in current config |
| chart-label sizing | **VERIFIED** | Tiny/Small/Normal/Large/Huge (set to Tiny) |
| alert and candle-close behaviour | **NOT SHOWN → UNKNOWN** | no alert/candle-close SETTING exposed; spoken notes only |

## Default vs current-config
**No reset-to-default was demonstrated → NONE of the visible values are proven factory defaults.** All are
recorded as Farouk's CURRENT on-screen configuration.

## Net effect on state-machine blockers
- **Value-area / OB-quality thresholds, CHoCH pivot, FVG lookback/min-ATR, BPR overlap, Asia hours/timezone**:
  **STILL_BLOCKED** — not exposed here.
- **Reversal-pattern (TZ/ST) tolerances**: narrowed to concrete numbers (0.15 / 0.08 / 0.6 / 0.3 ×ATR) — but
  these are Tweezer/Star reversal marks, a peripheral feature.
- **repaint / alert / candle-close**: **UNCHANGED** — still requires a live/forward capture (FP-LIVE-OBSERVATION-001).
- **Lineage**: the campaign/FP-INDICATOR-001 CHoCH/OB panel is now attributable to THIS indicator (not [kyle]).
