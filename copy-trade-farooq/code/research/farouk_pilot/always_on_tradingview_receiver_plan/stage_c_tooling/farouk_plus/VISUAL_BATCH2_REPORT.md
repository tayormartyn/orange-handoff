# Visual Batch 2 — ORB + Jul-3 level-construction + gold-ORB pass

**Mode: APPROVED VISUAL PASSES ×3, ONE AT A TIME — REVIEW-ONLY.** 2026-07-13 (~06:45Z). Live gates
before each item and before findings: store max 45657 throughout; listener PID 30268 single-instance;
cursor 45657. Sources hash-verified vs `downloads_video_inventory_20260713.json` (Zoom full mp4
5635e60e… — absolute timestamps used, split-relative = t−(part−1)×1200s; Jul-3 mp4 944789f9…).
Originals untouched. Frames: `derived/visual_batch2/<ID>/t<sec>s.jpg`. Gates
`PAPER/PREVIEW/False/False`; `NOT_INTEGRATION_READY` unchanged; pre-marks frozen.

## VE-Z2-VISUAL-03 — ORB (Zoom 3646–4633s; frames t03720/t03850/t03905/t04260/t04415)
**Definition (DIRECT_AUDIO_AND_VISUAL, GOLD):** ORB = the **first 15-minute candle** of a session
open — London 09:00, NY 15:30 (chart-local GMT+1); levels = that candle's **high, low and midpoint**
(3664–3744s); rendered as an **indicator-generated three-line set (green top / blue mid / red
bottom)** extending right — "you don't have to look at the 15 minutes, the indicator already provides
it — just set the time for your time zone" (4072–4091s; visible on XAUUSD 15m OANDA t03850 ~4209/4202/
4194.5 and XAUUSD 5m Pepperstone t07715 ~4244/4238/4232). Line placement tracks the candle's **wick
extremes** on the visuals (body-vs-wick not stated verbally → recorded as visual-inferred).
**Rules observed:** no-trade inside the orb (4250–4274s "inside of this orb I will do nothing");
trade = **breakout → retest** ("close above this high above the orb, they had a structure break and
now they retest it", 3901s — body-close phrasing + structure break); mid-level acts as internal
magnet (4274s); **unretested orb breakout = magnet** (3726s); FVG can "mitigate the orb" (3907s);
bias steps in at the orb (3936s). Multiple-false-break question (4633s) answered discretionally
(range-dependent) — DISCRETIONARY_SELECTION.
**Proposed ORB rule spec (offline candidate only — NOT for v0.3):**
A. Reproducible: session-open first-15m candle; H/L/mid lines; no-trade-inside; breakout+retest
   entry; unretested-breakout magnet; works Asia/London/US.
B. Discretionary: which session's orb to mark ("I only marked the US orb", 7713s); confluence
   weighting; "right breakout" after repeated falses.
C. Cross-asset: taught on gold here (t03850/t04260/t07715 all XAUUSD); companion examples on other
   assets exist in the same session.
D. Missing parameters: body-vs-wick anchoring (verbal), breakout-close timeframe (5m vs 15m),
   retest depth tolerance, orb validity horizon.

## VE-EDU001B-VISUAL — Jul-3 OB-marking lesson (605–951s; frames t00620/t00670/t00713/t00780/t00900)
**Headline (t00713, XAUUSD 15m FXCM, TradingView REPLAY mode):** two hand-drawn blue OB boxes with
live selection handles at **exact body-anchored decimals — 4089.47–4096.46** (lower box; the 4080
wick sits OUTSIDE the box) and an upper box text-labeled **"5 min ob"** (~4105–4112, black line at
4116.91). Confirms: **OB box = body range of the origin candle/cluster; wicks excluded; multi-TF OBs
stacked and text-labeled by TF; "the range between these two OBs is a strong level"** (773s audio =
the two stacked boxes; VISUAL_AUDIO_MATCH). Teaching in replay = levels constructed on historical
bars demonstrating the before-state (RETROSPECTIVE demonstration, stated). Also: OB flip
support/resistance (814–840s), old-OB/breaker-OB as support (899–904s), HTF-OB-is-king (808s).
**REPRODUCIBLE_RULE_CANDIDATE (VR-11): OB box boundaries = origin-candle BODY extremes (2nd
independent instance after Batch-1's VR-01).**

## VE-Z2-VISUAL-04 — third item (QUALIFIED: gold-specific ORB demo, Zoom 7501–7732s; frames t07540/t07690/t07715)
Qualified under the criteria (visible gold ORB/session demonstration): "orb breakout retest… you
never retested this level, 4100-something" (7693s); **Asia-orb vs US-orb choice explicit — "this was
the Asia orb; I only marked now the US orb"** (7713s); ~150–260-pip orb-retest swing examples
(7584–7679s); ORB triplet visible on gold 5m Pepperstone with **SFP marks on-chart** ([kyle]-era
sweep prints) and a gold-futures (MGC1!) tab present.

## Panel-version control (SPECIAL PANEL note)
The Dec-21 Zoom's indicator stack is the **[kyle] v1/v2 + POC + "Smart Zones Strategy PRO"** era —
NOT the current "Farouk's Playbook Smart Money Suite"; older panel displays must not be equated with
the current/future panel (FC-PANELWATCH active; formula/repaint remain UNKNOWN). **Bonus resolution
(VR-12):** the stacked labels "[kyle] v1: 1DT/2DT/3DT/5D/1W : POC <price>" (t04260) reveal the
formerly-unknown **POC "T-variants" as multi-window POC levels** (1-day-trailing/2/3/5-day/1-week);
their exact computation stays UNKNOWN — they remain excluded from Lane-6 anchoring.

## Cross-asset guard
No cross-asset finding was recorded as gold evidence this batch (all cited frames are XAUUSD; the
4633s multi-break Q&A and non-gold companion examples were not used for rules).

## Knowledge updates
Register addendum: visual findings VR-11 (OB-body-box rule candidate, 2nd instance), VR-12 (POC
T-variants = multi-window POCs), ORB candidate spec (A–D above) added to the level-construction/ORB
section; FC-PANELWATCH annotated (Dec-era stack identified); replay-test backlog += ORB-spec forward
test (deterministic once session times + 1m data present). Nothing enters v0.3.
