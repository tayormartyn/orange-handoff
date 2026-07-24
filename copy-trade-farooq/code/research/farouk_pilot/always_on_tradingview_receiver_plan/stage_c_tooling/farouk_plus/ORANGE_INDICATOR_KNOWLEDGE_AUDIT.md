# ORANGE — Indicator Knowledge Audit (what we know, what we infer, what we don't)

**Mode: INDICATOR KNOWLEDGE AUDIT — READ-ONLY / DOCUMENTATION ONLY. SINGLE-SESSION.** Date 2026-07-12
(~13:05Z). Machine-readable: `orange_indicator_knowledge_audit.json`. No alert touched; no Worker
action; listener **PID 23012 running/untouched**. Gates `PAPER/PREVIEW/False/False`;
`NOT_INTEGRATION_READY` unchanged.

**Live gate note:** during the audit the listener captured **msg 45649** (12:47:23Z, member "Thomas"
asking the admin to mirror the Discord news-feed channel into the Telegram relay). **No market
content → IRRELEVANT, non-triggering** (also live proof the new listener captures in real time).
Cursor stays 45648; 45649 will be formally examined by Cycle 006.

**Sources audited:** master vNEXT + 004B addendum · `FP_INDICATOR_001_ALERT_MAPPING_REPORT.*` ·
`LANE6_PRE_MARK_BUILDER_SPEC_v0_1.*` · Batch 003/004 reports · indicator observatory
(FP-INDICATOR-001..005 packages incl. `ALERT_INTERFACE_REGISTER.json`, `ALERT_PAYLOAD_FINDINGS.md`,
`FP-INDICATOR-005_SETTINGS_AND_FEATURE_REGISTER.json`) · monitoring narrative.

## 1. Indicator lineage (provenance-corrected)
- **FP-INDICATOR-001 era (Dec-2025):** "[kyle] v1/v2 + POC" — session-range boxes (top/mid/bottom),
  VWAP (session/D/W/M), POC/VAH/VAL (D/W), SFP dots, liquidity-sweep marks, ORB top/mid/bottom,
  yellow (market-maker/vector) candles. The CHoCH/OB panel did NOT exist there.
- **FP-INDICATOR-005 (current): "Farouk's Playbook — Smart Money Suite"** — the alert surface and
  panel Orange maps today; updated ~Jul-5 (London/US H/L, extended boxes).
- Era attribution matters: VWAP/POC/VAH/VAL are **confirmed for the Dec era**; their presence in the
  CURRENT suite is NOT confirmed (Z2/Dec-21 shows POC/VAH/VAL/VWAP in live use in that era).

## 2. CONFIRMED alert conditions (hashed screenshots + live captures)
**13 named Farouk conditions + the script channel** (from the Create-alert dropdown,
`farouk_indicator_alert_conditions.png` sha256 91679b89… and 9 sibling captures):
`Any alert() function call` · `Bullish BPR formed` · `Bearish BPR formed` · `Bullish Engulfing` ·
`Bearish Engulfing` · `Sweep low` · `Sweep high` · `Asia Trap Bearish` · `Asia Trap Bullish` ·
`A+++ setup` · `A+ or better` · `CHoCH up` · `CHoCH down`. Generic TradingView conditions
(Crossing…) begin after a separator — not Farouk's.
Also CONFIRMED: frequency options (Once only / per bar / **per bar close** / per minute —
**user-selected, not enforced**); default Message payload = the plain condition name (no
JSON/placeholders visible); `Any alert()` has NO frequency row (script-controlled); live Gate-G/H
captures hold real **CHoCH→Sweep→A sequences and an A+ payload**.

## 3. CONFIRMED panel / price-level fields
**Panel (owned by the suite):** `TF · CHoCH <price> · Asia break (LOW/HIGH/X) · OB retest <price/X> ·
Current OB <price> · Fresh OB <price>` — with visible numeric examples (15m: CHoCH 4174.34,
Current/Fresh OB 4022.13). **Display objects:** FVG · BPR · multi-TF OBs (D/6H/4H/1H/15m) · Asia
session range · **London H/L (blue)** · **US H/L (yellow)** · IFVG toggle · engulfing marks ·
Tweezer/Star marks (ATR tolerances 0.15/0.08/0.6/0.3 visible) · box extension 50 bars · extend-right.
**Settings caveat (standing):** all values are Farouk's on-screen CONFIG, **not proven factory
defaults**. **Spoken semantics confirmed:** "not a signal indicator — levels where the market maker
will bounce"; "the indicator only gives strong OBs"; ORB = **first 15 minutes** (London 09:00 GMT+1,
NY 15:30); unretested orb breakouts / unmitigated levels / unfilled gaps = magnets; flat candles =
mitigation-required class.

## 4. Indicator-derived fields Lane 6 uses today (builder spec v0.1)
`alert_type` (mapped enum) · `alert_timestamp_utc` · **`bar_close_confirmed` (REQUIRED true)** ·
`indicator_price_level_if_visible` (closed-bar panel value = the numeric pre-mark anchor) ·
`direction_hint` · structure/liquidity/OB-FVG-BPR context · confluence ranking (tiebreak) ·
`repaint_guard_status`. **HIGH-usefulness set:** Sweep low/high, CHoCH up/down (+panel price),
BPR formed, Asia Trap. **Weight-0 record-only:** A+++ / A+ or better (formula invisible).
**Excluded:** Engulfing-alone (no level), [kyle] POC "T-variants" (meaning unknown), SFP (attribution
unconfirmed), anything intra-bar (F5).

## 5. Indicator fields in Cycle-006 / XAU-F001 capture readiness
8F `indicator_price_level_extraction` + verbatim panel levels · `fill_lag_cost` (post-time fill vs
indicator-level first-touch) · 003B `indicator_level_source_kind` enum (SESSION_RANGE_BOX / VWAP /
POC / VAH / VAL / SFP_DOT / LIQUIDITY_SWEEP_MARK / ORB_TOP/MID/BOTTOM / YELLOW_CANDLE_CONTEXT /
PANEL_PRICE / NON_INDICATOR / UNKNOWN **+ 004B: LONDON_HIGH/LOW, US_HIGH/LOW, FLAT_CANDLE, GAP**) ·
004B `london_high_low_panel_evidence` / `us_high_low_panel_evidence` / `orb_timing_context` /
`magnet_logic_evidence` · bar-close-confirmed flags throughout · feed notes (Vantage vs Pepperstone).

## 6. CONFIRMED vs INFERRED vs UNKNOWN

**CONFIRMED:** §2 conditions + frequency/payload facts; §3 panel fields + feature set + visible
settings values; A-grade alerts exist; live CHoCH/Sweep/A payload sequences; Jul-5 update (London/US
H/L, extended boxes, Asia-trap alert usage on 5m); Dec-era semantics pack (for that era); ORB
definition + session times (spoken); indicator distributed free via his section (no public source).

**INFERRED (evidence-based, not proven):** A LONG/A SHORT arrive via `alert()` payload text
(dedicated named conditions below the fold UNCONFIRMED_BELOW_FOLD); closed-bar panel snapshots usable
as leak-free numeric anchors (design inference, untested live); the 001→005 lineage split; "only
strong OBs" as mechanism (his claim; internal threshold unverified); London/US H/L behaviour beyond
the settings toggle.

**UNKNOWN:** the **exact internal A+/A+++ formula** (Pine hidden — answer to Task 7: **NOT known**);
**repaint/intrabar behaviour of every marker and the panel** (never demonstrated — Task 8: **NOT
fully known**; bar-close alert option exists but is user-selected; F5 exists precisely for this);
runtime `alert()` message content/frequency argument; the detection-engine parameters (CHoCH pivot
length, FVG lookback/min size, BPR overlap threshold, zone removal/max, ordinary + STRONG OB impulse
thresholds, equal-H/L lookback, HTF-OB selection input, Asia session hours/timezone input, explicit
candle-close setting); below-the-fold named conditions; [kyle] POC T-variants; SFP attribution in the
current suite; webhook payload customisation; any numeric displacement threshold (none exists —
FVG-presence design stands).

## 7. Safety classification of indicator facts
- **Capture-only (safe now):** everything in §5 — verbatim panel values, payload records, level-source
  kinds, magnet/ORB/London-US context — always with `bar_close_confirmed` flags; A-grade events
  recorded at weight 0.
- **Lane-6 pre-marking (safe under guards):** HIGH-class conditions (Sweep/CHoCH/BPR/Asia-Trap) +
  closed-bar panel numeric anchors, under the **binding F5 repaint guard**, frozen-window hash,
  leakage checks, and the minimum-evidence rule; anything uncertain → PRE_MARK_INSUFFICIENT_CONTEXT.
- **v0.4/v0.5 backlog (offline only):** displacement FVG-presence test; fvg_claim_chain;
  TF-hierarchy grading; any indicator-derived confluence input — offline replay + promotion gate.
- **Never without forward proof (+ ratification where scoring):** A-grade correlation (formula
  invisible); ANY repaint-dependent use; session-break priors (Asia 78–80%, London/US claims); any
  scoring use of panel values; anything from the detection engine we cannot parameterise.

## 8. Can Orange pre-mark Farouk-style zones from the indicator WITHOUT Telegram?
**In principle partially — in practice NOT YET PROVEN.** For: his levels ARE the indicator's own
machine-readable outputs (doctrine + panel prices), pre-marking is HIS OWN workflow, and the alert
lane delivers HIGH-class events with numeric anchors. Against: (a) **zero indicator-sourced pre-marks
have been tested** (repaint guard untested live); (b) the **A-grade selection layer — his final
filter — is invisible**; (c) the **detection-engine parameters are unknown**, so Orange can READ
levels when alerts fire (market open) but cannot REGENERATE zones independently from raw OHLC;
(d) the retrospective is n≈3 with level-match 2/3 and 0 profitable fills — **stop-width, not level
identification, is the binding constraint**. Telegram remains the ground-truth comparator; the
forward alert-lane pre-marks (Cycle 006+) are the actual test.

## 9. Missing-evidence list (what would close the gaps)
1. Live repaint demonstration: alert-lane captures across bar closes vs chart state (first market-open
   session provides this free via Worker→R2 reads).
2. More runtime `alert()` payload samples (structure/frequency) from Gate-G/H-style captures.
3. The Create-alert dropdown scrolled BELOW "CHoCH down" (settle A LONG/A SHORT named conditions).
4. A settings video that scrolls to the DETECTION-ENGINE section (the 13 unknown parameters).
5. The A-grade formula — only obtainable via source access or forward correlation (record-only).
6. Asia session hours/timezone input value.
7. Current-suite status of SFP markers and POC/VAH/VAL (era attribution).
8. EDU-035's fuller displacement session (~Sept-2025, still missing).
9. Indicator changelog/version history (Dec era → Jul-5 update path).
10. Whether his own alert Messages are customised (webhook/JSON) — irrelevant to us operationally but
    closes the payload question.

## 10. Safety confirmation
Read-only audit; no alert created/modified; no Worker deploy; no execution built
(broker/QST/cTrader/nano/copy/demo/live absent); no permits/leases/orders; gates unchanged; v0.3
labels untouched; v0.4 offline. `NOT_INTEGRATION_READY` unchanged.

## Next step
**Cycle 006 / XAU-F001 at the first real XAU post after tonight's ~22:00Z reopen** — which also
delivers the first free evidence against §9 items 1–2 (live alert-lane reads) and the first live test
of the F5 repaint guard on an indicator-sourced pre-mark.
