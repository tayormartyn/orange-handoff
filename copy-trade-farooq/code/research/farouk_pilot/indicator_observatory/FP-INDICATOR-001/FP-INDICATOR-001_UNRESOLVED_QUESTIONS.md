# FP-INDICATOR-001 — UNRESOLVED QUESTIONS

Open items after this interim evidence pass. Each is a gap the **three companion indicator videos** (expected
later) or a live prospective capture should resolve. Nothing here is guessed.

## Indicator identity & internals
1. **[kyle] v2** — present on the chart but its settings were never opened. How does it differ from v1?
   (Do NOT assume equivalent to v1.)
2. **Smart Zones Strategy PRO** — settings never opened. What zones does it compute, with what inputs?
   Are the pink/blue supply-demand zones seen all session from this indicator? (attribution UNCONFIRMED)
3. **POC Prototype vs POC** — two separate POC indicators are loaded. What distinguishes them?
4. **POC "T" suffix** — `1DT / 1WT / 1MT / 3DT / 2DT` plot different prices than `1D/1W/1M/3D/2D`. The "T"
   meaning was asked repeatedly in chat and never answered. (developing vs prior-period? "true"? UNKNOWN.)
5. **Author/publisher & version strings** — only the handle "kyle" (bracket convention) is visible. Full
   author, script version, and TradingView publication status = UNKNOWN.
6. **Moving-average usage** — v1 exposes EMA20/SMA21/SMA34/EMA50/SMA55 but ALL were unchecked in view.
   Which MA(s) does Farouk actually enable as the "Trend EMA" (per FP-EDU-004)?
7. **Marker sources** — small circle markers on candles and "SFP" labels: which indicator plots them, and
   what exactly triggers an SFP/circle?
8. **The CHoCH / Asia break / OB retest / Current OB / Fresh OB panel** from FP-CAMPAIGN-001/002/003 was NOT
   visible here. Is it a [kyle] v2 / Smart Zones feature, a different layout, or a different indicator set?

## Rule / terminology gaps
9. **"cluster" vs order block** — Farouk uses "cluster" for the origin level; is it identical to the OB of
   the docs, or a distinct (volume/POC) construct? (chat asked; unanswered.)
10. **"flat candle"** — precise definition (no-wick? body-only? equal high/low?) and how it becomes a level.
11. **ORB entry rules** — beyond the 15-min range, what are the exact break/retest entry, stop and target
    rules? (He said "signal times does nothing" — so what IS the trigger?)
12. **SFP** — exact definition and why it "gives a buy on the top and it's not good" (false-positive cases).
13. **Relationship of POC/ORB/cluster/flat-candle to the v0.2.1 OB/FVG/BPR/CHoCH framework** — this session
    barely used CHoCH/BPR/displacement. Are these two different modules of the same method?

## Data / provenance gaps
14. **Timezone reconciliation** — chart UTC+1, ORB setting GMT+1, an audience member GMT+2; the campaigns
    showed UTC+2. Which is canonical for signal timestamps? UNKNOWN.
15. **Feed variation** — this session used OANDA; campaigns used Pepperstone/Vantage/FXCM. Feed-dependent
    level differences not quantified.
16. **Repaint / intrabar / closed-bar / predictive behaviour** — NOT demonstrated or stated. Cannot be
    resolved from a historical recording — see `PROSPECTIVE_CAPTURE_PLAN`.

## Priority questions for the companion videos (ranked)
- **P1.** Open each indicator's settings on screen: [kyle] v1 (full), **[kyle] v2**, Smart Zones Strategy
  PRO, POC, POC Prototype — capture every input/default.
- **P2.** Define the **POC "T" variant** and the full POC period set.
- **P3.** State the **ORB entry / stop / target** rules and which session(s) are used.
- **P4.** Define **cluster, flat candle, SFP** precisely and show pass/fail examples.
- **P5.** Show which **MA(s)** are enabled as the Trend filter.
- **P6.** Any explicit statement on **repaint / closed-bar-only / alert timing**.
- **P7.** Reconcile **timezone** and confirm the **CHoCH/OB panel** indicator.
