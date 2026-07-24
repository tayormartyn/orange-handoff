# Gate G — Capture One Real Farouk Alert — PLAN (NOT STARTED)

**Mode: GATE G PLAN ONLY.** No Farouk alert edited, none duplicated, no webhook attached, no fire, no
Worker change. Requires Martyn's explicit approval before any execution. Gate G is the **first
production-touching step**, so this is deliberately conservative.

## Objective

Capture **one real Farouk TradingView alert** into the proven Worker → R2 logging-only lane **without
disrupting** the existing Farouk alert setup (its app/phone notifications and the CSV evidence lane
must keep working unchanged).

## Option comparison

### Option A — Duplicate-first (RECOMMENDED)

Duplicate one selected Farouk alert into a NEW capture-only alert; add the webhook to the **duplicate
only**; leave the original untouched.

| Dimension | Assessment |
|---|---|
| Operational risk | **Lowest** — the original Farouk alert is never opened/edited |
| Reversibility | **Full** — delete the duplicate; original unaffected either way |
| Chance of breaking existing phone alerts | **Near zero** — original's notifications untouched |
| Evidence value | High — captures the real Farouk condition firing (via the duplicate) |
| Ease for Martyn | Moderate — one duplicate + paste URL/message + delete after |
| Net | **Safest; preferred default** |

### Option B — Add-webhook-only (NOT recommended for first step)

Edit one existing Farouk production alert: keep condition + app notification, add the webhook + message.

| Dimension | Assessment |
|---|---|
| Operational risk | **Higher** — touches a live production alert (risk of an accidental condition/notification change, or a TradingView save quirk) |
| Reversibility | Reversible (remove webhook), but you've edited production |
| Chance of breaking existing phone alerts | Low but **non-zero** (any edit to a live alert carries risk) |
| Evidence value | High (same real firing) |
| Ease for Martyn | Slightly more direct (no duplicate) |
| Net | More direct but **unnecessary risk** for a first capture |

**Recommendation: Option A (duplicate-first).** It achieves the same evidence with the original alert
never touched and trivial rollback. Use Option B only if a technical reason blocks duplication.

## ⚠️ Key pre-approval technical check (message format)

Farouk alerts appear to be **`alert()`-function-based** (the indicator generates the message text, e.g.
"Farouks Playbook: A+ LONG on XAUUSD 3"). This matters:

- **If `alert()`-based:** the webhook body is the **indicator's own text string** — you **cannot** inject
  a custom JSON message in the alert dialog. The Worker will store it **raw** (`parse_status:
  INVALID_JSON`, raw_payload byte-preserved) — still a valid capture, just not our JSON structure.
- **If a plain condition alert (message editable):** we can send **structured JSON** with placeholders
  (`{{ticker}}`, `{{close}}`, `{{time}}`, `{{timenow}}`, etc.) like Gate E/F.

**Before Gate G, confirm which type the target alert is.** Either works for capture; it only changes
whether we get structured JSON or raw indicator text. (Raw text is fine — the raw-first store preserves
it, and the Worker's keyword classifier can be extended later, offline, to parse the Farouk text.)

## Candidate Farouk alert to mirror

Known Farouk alerts (from PHONE_ALERT_BATCH_001): `LIVE001_ANY_ALERT_XAUUSD_3M` (composite; richest text,
fires most often), `LIVE001_APLUS_XAUUSD_3M`, `LIVE001_SWEEP_HIGH/LOW_…`, `LIVE001_CHOCH_UP/DOWN_…`.

- **Recommended candidate: `LIVE001_ANY_ALERT_XAUUSD_3M`** (the composite) — carries the full
  descriptive event text and fires frequently, so a real capture arrives soon (fast, rich evidence).
  **Trade-off:** it's high-volume → many objects/day; **disable the mirror after the first confirmed
  capture** for Gate G (ongoing capture is Gate H).
- **Lower-noise alternative: `LIVE001_APLUS_XAUUSD_3M`** (~4×/day) — fewer captures, still soon enough.

Final candidate is Martyn's choice at approval time.

## Exact manual steps for Martyn (WHEN APPROVED — do not do yet)

1. In TradingView, open the **Alerts** list and locate the chosen Farouk alert (e.g.
   `LIVE001_ANY_ALERT_XAUUSD_3M`). **Do not edit it.**
2. Use TradingView's **Duplicate/Clone** on that alert → a copy is created.
3. **Rename the COPY** clearly, e.g. `LIVE003_FAROUK_MIRROR_GATE_G` (do **not** rename the original).
4. On the **DUPLICATE only** → Notifications: keep **Notify in app ON**, tick **Webhook URL**, paste the
   single bare URL line from `cloud_worker_dark/LOCAL_ONLY_GATE_F_WEBHOOK_URL.txt` (same proven
   endpoint; copy-proof file).
   - ✅ starts with `https://farouk-tv-webhook-logger-v1.taylormartyn70.workers.dev/tv/` — ❌ not the old
     trycloudflare URL.
5. **Message:**
   - If the duplicate lets you edit the message → paste a structured JSON (a Gate-G template can be
     prepared at approval time, `lane:LOGGING_ONLY`, `test:false`, `execution_allowed:false`, etc.).
   - If it's `alert()`-based (message not editable) → leave the indicator message; the webhook will
     send that raw text (captured raw). Confirm this is acceptable.
6. **Leave the ORIGINAL Farouk alert completely untouched** (condition, notifications, everything).
7. Let the Farouk condition **naturally trigger** the duplicate (do not force it) → webhook fires →
   captured to R2.
8. Tell Claude; Claude verifies (temp read-only branch or `wrangler tail`, then reverts to pure
   logging-only). Then **disable/delete the duplicate** `LIVE003_FAROUK_MIRROR_GATE_G`.

## What must be checked before approval

- [ ] Message type of the target alert (`alert()`-based vs editable-condition) — decide message format.
- [ ] TradingView permits duplicating that alert and adding a webhook to the copy.
- [ ] After duplication, the **original** remains armed and unaffected (Martyn confirms).
- [ ] App notification stays ON on both original and duplicate.
- [ ] Copy-proof webhook URL file current (it is; same proven endpoint).
- [ ] Candidate chosen (ANY_ALERT for rich/fast evidence, or APLUS for lower volume).
- [ ] Post-capture plan: disable/delete the duplicate after one confirmed capture (Gate G = one alert;
      ongoing/full set = Gate H).

## Hard guarantees (Gate G, when run)

- Original Farouk alerts **never edited**; webhook added to a **duplicate** only; fully reversible.
- Logging-only; **no broker/cTrader/QST; no permit/lease/order; no execution-gate change; no risk
  change; no shadow engine**; Telegram listener untouched; secret never exposed; `NOT_INTEGRATION_READY`
  unchanged.

## Status

**PLANNED ONLY — NOT STARTED.** Awaiting Martyn's explicit approval (and the pre-approval checks above)
before any duplication/fire.
