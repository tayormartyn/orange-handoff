# FP-INDICATOR-001 — INTERIM FINDINGS

**Status: INTERIM evidence pass. NOT_A_TRADE — excluded from Gold statistics.** No detector built; Methodology
v0.2.1 NOT updated; no QST/risk/broker/execution change. Three companion indicator videos are expected later;
this pass prepares the precise gaps they must close (see §Gaps).

## Source
- Full MP4 `GMT20251221-181518_Recording_2240x1260.mp4` — `sha256 5635e60e…965917` — asset `sa-5635e60e29be4868`
- Audio `GMT20251221-181518_Recording.m4a` — `sha256 c5508175…966a64` — asset `sa-c5508175ec0d635b`
- Chat `GMT20251221-181518_RecordingnewChat.txt` — `sha256 249ac9a3…91664d` — asset `sa-249ac9a39b2bb93c`
- Duration processed: **02:45:25.76**. Transcript: **local** faster-whisper base.en, **2549 segments**, mean
  confidence **0.71** (from the M4A). The `.txt` is the **Zoom CHAT log** (audience), **not** a speech
  transcript — used as supplementary evidence only.

## Indicator identity (directly visible)
Applied indicators (on-chart list, scene_00-58-30): **`POC Prototype`, `POC`, `Smart Zones Strategy PRO`,
`[kyle] v2`, `[kyle] v1`**. Only **`[kyle] v1`** had its settings opened (scene_01-29-10):
- **Liquidity Sweeps** (Bull green / Bear red)
- **Moving Average** — EMA 20, SMA 21, SMA 34, EMA 50, SMA 55 (all *unchecked* in view)
- **Opening Range Breakout** — Timezone **GMT+1**; Asia 03:00–03:15, London 09:00–09:15, **NY 15:30–15:45
  (enabled)**; per-session "Signal Times"
- **POC** plotted on the price scale for `1M/1W/3D/2D/1D` and **"T" variants** `1DT/1WT/3DT/2DT` (different
  prices); "T" meaning **UNKNOWN**.
`[kyle] v2`, `Smart Zones Strategy PRO`, `POC`, `POC Prototype` internals were **not opened** — **not assumed**.
Acquisition: via **Whop membership** (chat). Platform TradingView; symbol **XAUUSD (OANDA)**; TZ **UTC+1**.

## Strongest EXPLICIT spoken rules (SourceClaims — not promoted to rules)
1. **ORB = the first 15 minutes of a session**, GMT+1 (London 09:00–09:15, NY 15:30) [01:00–01:01].
2. **"Signal times does nothing — I'm going to remove it; the ORB is just the 15 minutes"** [01:26–01:27] —
   Farouk deprecates a specific [kyle] v1 setting.
3. **Candle close above = confirmation** ("no candle close above → short") [00:04, 00:22] — matches v0.2.1 §6.
4. **Sweep equal lows / flat candles / gaps, then look for longs** [00:22:30].
5. **"Cluster" = the level that made the high** (≈ order block) [00:02, 00:07].
6. **"Flat candle"** = a no-wick candle marking a level that holds liquidity ("they swept it") [00:11].
7. **Golden pocket / 50% retrace** keeps structure valid [00:48]; **SFP** "really nice… but false at tops"
   [01:26]; **breakeven** "staircase up" [01:51].

## Strongest DIRECTLY VISIBLE observations
- The indicator stack **names** (above) — resolves the chat's "Kyle V1".
- The **full [kyle] v1 input set** (Liquidity Sweeps / 5 MAs / ORB sessions+timezone / multi-period POC+T).
- **Volume-profile / POC histogram** view used to derive POC levels (~01:31–01:34).
- **SFP** text markers on the 5m chart.

## Contradictions / divergences with existing documents & campaigns
- **Emphasis divergence:** this session centres on **POC + ORB + clusters + flat-candles + SFP**. Term scan:
  **0 "CHoCH", 0 "BPR", 0 "displacement"** spoken — yet those are core to `FAROUK_METHODOLOGY_SPEC_v0.2.1`
  (from the PDFs/other videos). Likely a **different teaching module**, not a contradiction of fact — flagged,
  not reconciled (v0.2.1 deliberately not edited).
- **New constructs not in v0.2.1:** ORB session-breakout framework, POC/volume-profile levels (+ "T" variant),
  "golden pocket", "SFP", "flat candle", "cluster" terminology.
- **Panel absence:** the CHoCH/Asia-break/OB-retest/Current-OB/Fresh-OB panel seen in FP-CAMPAIGN-001/002/003
  was **not visible** here — source indicator of that panel remains UNKNOWN.
- **Timezone:** chart/ORB **GMT+1/UTC+1** here vs **UTC+2** in the campaigns — unreconciled.

## Limitations (must not be overstated)
No repaint / intrabar / closed-bar-only / predictive claim is made — none was demonstrated or stated. See
`FP-INDICATOR-001_PROSPECTIVE_CAPTURE_PLAN.md`.

## Gaps the companion videos must close (priority)
1. Open **[kyle] v2**, **Smart Zones Strategy PRO**, **POC**, **POC Prototype** settings (full inputs).
2. Define the **POC "T" variant** and full period set.
3. State **ORB entry/stop/target** rules (given "signal times does nothing").
4. Precisely define **cluster / flat candle / SFP** with pass/fail examples.
5. Show which **MA(s)** are enabled as the trend filter.
6. Any explicit **repaint / closed-bar / alert-timing** statement.
7. Reconcile **timezone** and identify the **CHoCH/OB panel** indicator.

## Deliverables produced
`FP-INDICATOR-001_SESSION_MAP.md`, `_INDICATOR_INVENTORY.json`, `_CLAIMS.json` (20 claims),
`_VISUAL_INDEX.csv` (109 frames), `_UNRESOLVED_QUESTIONS.md`, `_PROSPECTIVE_CAPTURE_PLAN.md`, this file,
plus `_SOURCE_REGISTRATION.json`, the local transcript, and 108 frames + contact sheet.
