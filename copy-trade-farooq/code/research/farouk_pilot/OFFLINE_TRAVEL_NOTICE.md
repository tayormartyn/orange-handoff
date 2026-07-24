# OFFLINE TRAVEL NOTICE

Documentation only. No services started/stopped; no files changed except this notice; no alerts/webhooks/QST/
broker/risk/execution changes.

1. **Timestamp:** 2026-07-06 09:34 local (UTC+1) / 08:34 UTC.
2. **Going offline:** the laptop is about to be unplugged and may be **offline/asleep or without internet for
   several hours** while travelling.
3. **Local processes will NOT continue while asleep/offline:** the Telegram listener, the local quote watcher,
   Claude processing, local screen recording, and any local engine processes all **stop** when the laptop
   sleeps or loses connectivity.
4. **What may continue:** TradingView **server-side alerts** may keep logging / sending app notifications, but
   **no local screen recording or evidence capture occurs while offline** — those firings will not be captured
   locally until the laptop is back online.
5. **Webhook:** none configured.
6. **Broker execution:** not enabled.
7. **Risk cap:** the **1.0% campaign-wide risk cap remains unchanged.**
8. **Execution gates:** all remain **False**.
9. **FP-LIVE-OBSERVATION-001 — paused safely** at the latest checkpoint:
   - **22 events** logged
   - **A+ observed**
   - **A+++ NOT observed**
   - **CHoCH up observed**
   - **Sweep high / CHoCH down / BPR formed — NOT observed**
   - Verdict: **NOT_INTEGRATION_READY**
10. **Exact next action when the laptop is back online:**
    1. Reconnect internet.
    2. Open TradingView **XAUUSD · Pepperstone · 3m**.
    3. Confirm the alerts are still **Active**.
    4. Resume **observation / evidence capture only**.
    5. **Do NOT** connect a webhook, QST, or the broker.

Safe travels — evidence collection resumes when back online.
