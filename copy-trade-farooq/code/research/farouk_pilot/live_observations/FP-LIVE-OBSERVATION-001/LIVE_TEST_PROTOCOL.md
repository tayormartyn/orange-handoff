# FP-LIVE-OBSERVATION-001 — LIVE TEST PROTOCOL

**Protocol preparation only.** This document describes how to run the P1 live-alert observation LATER. **No
TradingView alert is created by this document. No webhook. No detector code. Nothing connects to QST. No
broker/risk/permit/lease/execution change.** Everything here is observation-only.

## Test context
- **Symbol:** XAUUSD · **Feed:** Pepperstone · **Primary timeframe:** 3 minutes
- **Indicator:** Farouk's Playbook — Smart Money Suite (FP-INDICATOR-005)
- **Notifications (later):** app / toast **only** — **no webhook, no broker action**
- **P1 conditions to observe:** A+++ setup · A+ or better · Any alert() function call · Sweep low · Sweep high ·
  CHoCH up · CHoCH down
- Named conditions are tested with **Once per bar close**. **Any alert() function call** keeps its
  **script-controlled timing & payload** (do not attempt to force its frequency).

## Objective (P1 from LIVE_VALIDATION_PLAN_v0.1)
Determine, from live evidence: actual A+++ and Any alert() runtime payloads; bar-close vs intrabar timing;
repaint / post-alert mutation; duplicate alerts; and A+/A+++ grade behaviour. The integration verdict stays
**NOT_INTEGRATION_READY** unless the PASS_FAIL_CRITERIA are met.

---

## STEP 1 — Chart & feed verification
1. Open TradingView; load **XAUUSD** on the **Pepperstone** feed. Confirm the chart header literally reads
   "Gold Spot / U.S. Dollar · Pepperstone". If any other feed loads, **record it verbatim** and note the
   deviation (do not silently substitute).
2. Set the timeframe to **3m**. Confirm only the **Farouk's Playbook — Smart Money Suite** indicator is the
   subject; note any other indicators present (hidden or visible) — e.g. [kyle] v1/v2, SeaScalper Bias, BGS —
   so their objects are not mis-attributed.
3. Screenshot the header + indicator list → `01_chart_feed_verification` (see naming guide).

## STEP 2 — Chart timezone recording
1. Read the **TradingView clock (bottom-right)** and record the chart timezone verbatim (e.g. `UTC+1`).
2. Record the **UTC offset** and note that all `candle_*`/`alert_arrival_time` fields will be logged in **both**
   the chart TZ and UTC. Screenshot → `02_chart_timezone`.
3. This resolves the standing timezone-authority blocker for THIS session only (do not generalise it).

## STEP 3 — Indicator configuration snapshot
1. Open the indicator Settings (Inputs / Style / Visibility) and screenshot each visible section.
2. Record the current config exactly (compare to the FP-INDICATOR-005 register: DISPLAY toggles, chart-label
   size, box extension, TZ/ST tolerances, OB display). Mark values as **CURRENT_CONFIG**, not defaults.
3. Note which of the P1 conditions have their objects **displayed** (e.g. Sweep/CHoCH/Engulfing marks visible).
   Screenshot → `03_indicator_config_snapshot_*`.

## STEP 4 — Safe alert creation (LATER — see ALERT_CREATION_CHECKLIST)
**Do not perform now.** When the live window is scheduled: create the P1 alerts per ALERT_CREATION_CHECKLIST —
named conditions = **Once per bar close**, Notifications = **App + Toast only**, **Message left as-is**,
**no webhook URL**, expiry short. **Any alert() function call** = leave frequency script-controlled. Screenshot
each "Create alert" dialog BEFORE pressing Create → `04_alert_setup_<condition>`.

## STEP 5 — Pre-close observation (per firing bar)
When a candidate bar is forming (before it closes):
1. Screenshot the forming bar + panel + any provisional marker/grade → `05_preclose_<obsid>`.
2. Record the provisional `visible_direction`, `grade`, `panel_values`, and any object drawn intrabar.
3. Note whether a toast/app alert has ALREADY fired intrabar (this is the intrabar-vs-bar-close test).

## STEP 6 — Candle-close observation
1. At the bar **close**, screenshot the closed bar + panel + marker → `06_close_<obsid>`.
2. Record `candle_open_time`, `candle_close_time`, and — if the alert fired — `alert_arrival_time`.
   Compute `alert_arrival_time − candle_close_time` (the timing delta).
3. Capture the **exact message** delivered (verbatim). Record `condition`, `visible_price`, `grade`.

## STEP 7 — One-candle-later observation
1. One bar after close, screenshot → `07_plus1_<obsid>`.
2. Set `persist_after_1_candle` = yes / changed / removed. Note any marker/zone move (early repaint signal).

## STEP 8 — Five-candles-later observation
1. Five bars after close, screenshot → `08_plus5_<obsid>`.
2. Set `persist_after_5_candles` = yes / changed / removed. This is the primary **repaint / post-alert
   mutation** check on historical (now-closed) bars.

## STEP 9 — Exact runtime-message capture
1. For **each** fired alert, open the TradingView alert log / notification and copy the **literal** message.
2. Classify: plain condition-name text / JSON / other. For **A+++ setup** and **Any alert() function call**
   specifically, record whether the payload is parseable and what fields (if any) it contains.
3. Store verbatim in `exact_message`; screenshot the notification → `09_message_<obsid>`.

## STEP 10 — Panel & marker capture
1. For every observation, capture the panel row values verbatim: **TF · CHoCH · Asia break · OB retest ·
   Current OB · Fresh OB**.
2. Capture the relevant **OB / FVG / BPR / sweep / CHoCH** objects (price + label) into `objects_*`.
3. Screenshot the panel + objects → `10_panel_<obsid>`.

## STEP 11 — Duplicate-alert capture
1. Watch for the **same** condition firing more than once for the same bar (intrabar repeats, refresh repeats).
2. Set `duplicate_status` = unique / duplicate-of:<obsid> / repeated-on-refresh. Screenshot any duplicate →
   `11_duplicate_<obsid>`.

## STEP 12 — A+ vs A+++ grade changes
1. When a grade appears, record it; then re-check at +1 and +5 bars whether the grade **changed** (e.g. A+
   upgraded to A+++, or a grade withdrawn).
2. Record the grade at each checkpoint in `grade` + a note; screenshot transitions → `12_grade_<obsid>`.
3. If `Any alert() function call` fired, determine whether it **matched a named condition** at the same bar and
   set `any_alert_matched_named` accordingly.

## STEP 13 — Repaint / post-alert mutation checks
1. Re-open the historical signal bar after +5 (and later, if possible) and diff against the close screenshot.
2. Set `mutation_repaint_status` = stable / REPAINTED (describe) / moved / disappeared. Any REPAINTED result is
   a **hard fail** for that condition's bar-close reliability (see PASS_FAIL_CRITERIA).

## STEP 14 — Cleanup & alert deletion
1. After the window, follow CLEANUP_CHECKLIST: **delete every created alert**, confirm none remain active,
   confirm no webhook was ever set, and archive screenshots/recordings + the completed observation log.
2. Re-affirm the verdict **NOT_INTEGRATION_READY** unless PASS_FAIL_CRITERIA are all met.

---

## Recording rule (every event)
Each fired alert = one record in `EVENT_OBSERVATION_TEMPLATE.json/.csv` with all 24 fields. Fill only what is
directly visible; use **UNKNOWN** rather than guessing. Times in chart TZ **and** UTC. These records are
**observations of an untrusted source**, never trade signals.
