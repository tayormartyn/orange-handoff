# FP-INDICATOR-005 — INDICATOR EVIDENCE REPORT

**Indicator: "Farouk's Playbook — Smart Money Suite"** — a NEW, distinct Farouk/Whale Room indicator, kept
separate from [kyle] v1/v2, SpaceMan, Market Cipher B, Craters-Reality/EMA and the discretionary Education
curriculum. Next available ID (no renumbering): **FP-INDICATOR-005**.

## 1. File inventory & hash
`raw/farouk_playbook_indicator_update/Schermopname 2026-07-05 om 12.53.09.mov` — **220,960,958 B** —
`sha256 e8a33802a013d74f4b01ac54a927b22ce481a444bc7f33df4df07683e5d99f8b` → asset `sa-e8a33802a013d74f`
(ingested, RR-FP-IND-005). *Only the .mov was in the folder — no separate "announcement" file; the announcement
is verbal at the start.*

## 2. Video technical metadata
00:05:31.92 · 4096×2184 · h264 (Main) · 39.99 fps · aac LC 48 kHz mono 129 kb/s. TradingView; XAUUSD (Pepperstone) 15m + 12h.

## 3. Timestamped visual timeline
See `FP-INDICATOR-005_VISUAL_TIMELINE.md` (10 segments): intro → DISPLAY toggles → London/US high-low → IFVG →
chart-label sizes → extended box → scalp example → 12h gold multi-TF OBs → close.

## 4. Audio transcription
Local (faster-whisper base.en), 76 segments, in `transcript/FP-INDICATOR-005_transcript.json`.

## 5. Settings & feature register
See `FP-INDICATOR-005_SETTINGS_AND_FEATURE_REGISTER.json`. **Shown:** DISPLAY toggles (FVG/BPR/OB/Asia/London ON;
US/IFVG/engulfing OFF), Chart label size = Tiny (of Tiny/Small/Normal/Large/Huge), Extend-to-right OFF, Box
extension 50 bars, TZ/ST tolerance 0.15×ATR, Tweezer 0.08×ATR, Star big 0.6×ATR, Star small 0.3×ATR, "Only show
TZ/ST at OB edge/Asia H-L" ON. Multi-TF OBs (D/6H/4H/1H/15m) shown on chart. This indicator owns the
**CHoCH/Asia-break/OB-retest/Current-OB/Fresh-OB panel**.

## 6. Verification of numerical values
**Verified (visible):** Box extension **50**; TZ/ST **0.15**, Tweezer **0.08**, Star big **0.6**, Star small
**0.3** (×ATR); panel prices CHoCH 4174.34 / Current OB 4022.13 / Fresh OB 4022.13 (15m); Current OB 2647.44 /
Fresh OB 1672.85 (12h). **NOT shown → UNKNOWN:** CHoCH pivot length, FVG lookback, min FVG ATR, BPR overlap,
auto FVG/BPR removal, max zones, ordinary/Strong OB impulse thresholds, equal-high/low lookback, HTF-OB selection
control, Asia-session hours + timezone, alert/candle-close settings. (Detection section never scrolled to.)

## 7. Visible values vs proven factory defaults
**No reset-to-default was demonstrated → NONE of the visible values are proven defaults.** All are recorded as
Farouk's **CURRENT on-screen configuration** (`DIRECTLY_VISIBLE_CURRENT_CONFIG`), not defaults.

## 8. Indicator lineage
See `FP-INDICATOR-005_LINEAGE_COMPARISON.json`. **Distinct from [kyle] v1/v2** (both present on the chart but
HIDDEN), SpaceMan, Market Cipher B, Craters-Reality/EMA. Other hidden indicators on the chart: BGS Liquidity
Inefficiency Indicator, SeaScalper — Bias Levels v2. **Key resolution:** the CHoCH/Asia-break/OB-retest/
Current-OB/Fresh-OB panel (logged as "UNKNOWN kyle-family" in FP-INDICATOR-001/campaigns) is produced by **this**
indicator — attribution updated to "Farouk's Playbook — Smart Money Suite" (strongly supported).

## 9. Campaign cross-reference
See `FP-INDICATOR-005_CAMPAIGN_CROSS_REFERENCE.json`. The Campaign 001–004 panel values (e.g. C004 OB retest
4036.56) share this indicator's panel schema → attributable to this indicator (strongly supported, not proven
per-campaign). London/US high-low liquidity (new here) matches the campaign session-liquidity framing.

## 10. Blocker-impact assessment
See `FP-INDICATOR-005_BLOCKER_IMPACT.md`. **Verified:** box-extension, reversal-pattern (TZ/ST) tolerances,
London/US high-low, IFVG, chart-label sizing. **STILL_BLOCKED (not shown):** CHoCH pivot, FVG lookback/min-ATR,
BPR overlap, auto removal, max zones, OB impulse thresholds, equal-high/low lookback, Asia hours/timezone, HTF-OB
selection control, alert/candle-close/repaint (needs live capture).

## Governance
No detector code; no QST connection; risk 1.0% (v2.0.0) unchanged; execution gates all False.
`FAROUK_METHODOLOGY_SPEC_v0.2.1`, `FAROUK_STATE_MACHINE_SPEC_v0.1`, the frozen Education corpus (33 sources,
highest FP-EDU-035) and campaign dossiers **unmodified**. Source video unmodified.


## ADDENDUM — Alert interface (completion pass)
10 alert-interface screenshots (added to the package folder AFTER the initial video pass) were later inventoried,
hashed and analysed. Deliverables: ALERT_INTERFACE_REGISTER.json, ALERT_INTERFACE_REGISTER.csv,
ALERT_PAYLOAD_FINDINGS.md, INTEGRATION_BOUNDARY.md.
- 13 Farouk-specific alert conditions (Any alert() call; Bullish/Bearish BPR formed; Bullish/Bearish Engulfing;
  Sweep low/high; Asia Trap Bearish/Bullish; A+++ setup; A+ or better; CHoCH up/down) + generic TradingView
  conditions (Crossing, ... SHOW MORE) kept separate.
- Message payloads = plain condition-name text (no JSON/placeholders visible); Any alert() = script-controlled.
- Frequency: standard Once only / Once per bar / Once per bar close / Once per minute (bar-close available).
- Webhook-capable (TradingView) but NOT integration-ready; NO alert/webhook created; nothing wired to QST.
