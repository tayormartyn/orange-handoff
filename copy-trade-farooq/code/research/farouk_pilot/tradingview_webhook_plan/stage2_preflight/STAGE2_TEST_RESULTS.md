# Stage 2 — Controlled Webhook Test Results

**Run:** 2026-07-07 (fires at 10:09Z and 16:15Z). Report written 17:23 local (Italy UTC+1).
**Mode: CONTROLLED STAGE 2 TEST.** One NEW harmless test alert only. No Farouk production alert
edited. No broker/QST/execution/permit/lease/order. No execution-gate change. Telegram PREVIEW
listener PID 40416 untouched throughout.

## Outcome: PASS

TradingView → cloudflared tunnel → local logging-only receiver (`PATH_ONLY`) → append-only JSONL,
**path-authenticated with no custom header**, **JSON parsed**, **all placeholders resolved**,
**timezone confirmed UTC**. Then torn down.

## Setup

- **Receiver:** `stage1_local_receiver/receiver.py`, `AUTH_MODE=PATH_ONLY`, `127.0.0.1:8791`,
  fresh long random secret path (`secrets.token_urlsafe(36)`).
- **Tunnel:** cloudflared 2026.6.1 (installed via winget, with Martyn's explicit approval), quick
  tunnel `cloudflared tunnel --url http://127.0.0.1:8791` →
  `https://deleted-precise-maps-reading.trycloudflare.com` (now torn down / dead).
- **Alert:** `LIVE001_WEBHOOK_TEST_STAGE2` — a NEW harmless XAUUSD price-crossing alert, "Only Once",
  app notification ON, webhook to the secret path. Created and later re-armed by Martyn; no Farouk
  alert touched.

## Two firings

### Firing 1 (10:09:00Z) — default-message finding
- Result: **ACCEPTED**, but `parse_status: INVALID_JSON`.
- Raw body: `XAUUSD Crossing 4,134.00` (content-type `text/plain`, 24 bytes) — **TradingView's default
  alert message**, because the Message box had not been set to the JSON.
- **Finding:** transport/auth/capture all worked; only the message content was wrong. Raw-first
  storage captured it byte-exact, so nothing was lost. Led to the JSON retest.

### Firing 2 (16:15:00Z) — JSON retest, full success
- Result: **ACCEPTED**, `parse_status: PARSED`, content-type `application/json`, 431 bytes,
  user-agent `TradingView Webhook`.
- Auth: `PATH_ONLY` — correct secret path, **no X-TV-Token header** (note recorded:
  "authenticated by secret path; no header (expected for TradingView)").
- Received `2026-07-07T16:15:39.7Z`; `{{timenow}}` = `16:15:38Z` → **~1s delivery latency**.

**Placeholder resolution (all resolved, none literal):**

| Placeholder | Resolved to |
|---|---|
| `{{ticker}}` | `XAUUSD` |
| `{{exchange}}` | `PEPPERSTONE` |
| `{{interval}}` | `1` |
| `{{close}}` | `4142.14` |
| `{{time}}` | `2026-07-07T16:15:00Z` |
| `{{timenow}}` | `2026-07-07T16:15:38Z` |

## Key findings (resolve prior TO_VERIFY items)

1. **Placeholders `{{ticker}}` / `{{exchange}}` / `{{interval}}` / `{{close}}` / `{{time}}` /
   `{{timenow}}` all resolve** in a real Farouk-chart TradingView webhook. CONFIRMED.
2. **Timezone = UTC (ISO-8601 `Z`).** `{{time}}` and `{{timenow}}` arrive in UTC — same basis as the
   alert-log CSV / PHONE_ALERT_BATCH_001 lane. **Resolves the timezone TO_VERIFY**; webhook times
   align with the CSV evidence with no offset guessing.
3. **`{{interval}}` reflects the chart the alert lives on** — came through as `1` (the test alert was
   on a 1-minute chart), not the 3m we discussed. Not a problem; just means interval = actual chart
   interval. For a real 3m Farouk alert it would read `3`.
4. **PATH_ONLY works against real TradingView** — no custom header needed, secret path is sufficient.
   Confirms the Stage 1B compatibility fix was correct.
5. `event_type`/`direction`/`grade` were `None` because the harmless test payload intentionally omits
   them (delivery/format test, not a signal).

## Event count

Baseline at Stage 2 start: 4. After firing 1: 5. After firing 2 (JSON): 6. **Exactly one accepted
event per firing**, both to the exact secret path; no stray/duplicate events.

## Safety audit (pre and post)

| Check | Pre | Post |
|---|---|---|
| Execution gates (`MODE`/`LISTENER_MODE`/`EXECUTION_ENABLED`/`CTRADER_EXECUTION_ENABLED`) | PAPER/PREVIEW/False/False | **unchanged** |
| Permit/lease/order artifacts | none | **none** |
| Receiver imports | stdlib only | stdlib only (no broker/QST/execution) |
| Broker/QST/execution process | none | none |
| Telegram listener PID 40416 | running | **running, untouched** |

## Teardown (my side — done)

- cloudflared tunnel: **stopped** (public URL now dead — verified `HTTP 000`/timeout).
- Receiver: **stopped** (kill).
- Evidence JSONL: **preserved** (append-only; the two Stage 2 events kept as legitimate evidence).
- **Note:** I proactively closed the tunnel + receiver once the retest was confirmed, to remove the
  live public endpoint (a mild security exposure). Fully reversible — can be restarted if needed.

## Still on Martyn's side

- **Delete/disable `LIVE001_WEBHOOK_TEST_STAGE2`** (and `_JSON` if a second was created) in
  TradingView. With the tunnel down, any further firing just gets a failed webhook status — harmless —
  but tidy up the test alert to finish teardown. **Do not touch any Farouk production alert.**

## Verdict

- **Stage 2: PASS.** The logging-only webhook lane is proven end-to-end with real TradingView,
  including JSON payload + UTC placeholders, with zero execution surface.
- **This does NOT change the `NOT_INTEGRATION_READY` execution verdict.** It is capture only. Grade
  formula (A+++ never observed), C4 repaint, C7, and single-day scope remain open — unchanged.
