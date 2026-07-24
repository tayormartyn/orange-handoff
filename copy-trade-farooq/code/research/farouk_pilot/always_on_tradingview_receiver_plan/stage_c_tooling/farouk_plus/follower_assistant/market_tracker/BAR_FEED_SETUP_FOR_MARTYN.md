# ORANGE_XAUUSD_1M_BAR_FEED — TradingView setup (≈3 minutes, click-by-click)

This creates ONE new alert that posts one JSON per completed 1-minute XAUUSD bar to the
existing logging-only receiver. **It does not touch any Farouk alert.** No broker action of
any kind is possible through this path.

## Step 1 — chart

1. Open TradingView and load the chart **PEPPERSTONE:XAUUSD** (your usual gold chart).
2. Set the timeframe to **1 minute**.

## Step 2 — add the Pine indicator

1. Open the **Pine Editor** (bottom panel).
2. Delete any template text and paste the entire contents of the file
   `ORANGE_XAUUSD_1M_BAR_FEED.pine` (in this folder — open it in Notepad and copy all).
3. Click **Save** (name it `ORANGE_XAUUSD_1M_BAR_FEED`) then **Add to chart**.
   It draws nothing — that is correct.

## Step 3 — create the alert

1. Click the **Alert (⏰) button** (or press Alt+A).
2. **Condition:** select `ORANGE_XAUUSD_1M_BAR_FEED` → **Any alert() function call**.
   (With this condition the frequency is controlled by the script: exactly once per bar close.)
3. **Expiration:** Open-ended (or the maximum your plan allows).
4. **Alert name:** `ORANGE_XAUUSD_1M_BAR_FEED`
5. **Message:** leave EXACTLY as-is (the script supplies the JSON — do not type anything).
6. **Notifications tab:** tick **Webhook URL** and paste the SAME URL you used for the
   Farouk mirror alerts — the bare line from your Notepad file
   `LOCAL_ONLY_GATE_F_WEBHOOK_URL.txt` (starts with
   `https://farouk-tv-webhook-logger-v1.taylormartyn70.workers.dev/tv/`).
   Untick app/email notifications if you don't want a ping every minute.
7. Click **Create**.

## Step 4 — verify (do this once, ~3 minutes after creating)

Tell Fable "bar feed armed" — verification is automatic (the tracker is already polling and
will report the first three consecutive live bars). Nothing else to do.

## Notes

- Volume on PEPPERSTONE:XAUUSD is tick volume; it's optional in the payload.
- If TradingView shows "alert fired" but Orange sees nothing, the webhook URL line was
  pasted with a label or trailing space — re-paste the bare line (same fix as Gate E).
- To pause the feed (e.g. holiday), just pause this one alert; Farouk alerts are unaffected.
  The tracker records the gap and fast-forwards when the feed resumes.
