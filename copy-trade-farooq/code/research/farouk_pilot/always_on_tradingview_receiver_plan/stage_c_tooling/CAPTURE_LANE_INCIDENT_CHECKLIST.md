# Capture-Lane Incident Checklist

**Read-only diagnosis first. Never enable execution, connect a broker/QST, or edit a Farouk production
alert as part of triage.** All fixes stay capture-only.

---

## 1. TradingView alert fired (phone notification) but NO R2 object

Most common cause (seen in Gate E): **malformed/wrong webhook URL** on the alert.
1. Confirm the alert's **Webhook URL is enabled** and matches the bare line in the gitignored
   `LOCAL_ONLY_*_WEBHOOK_URL.txt` **exactly** (no `webhook_url:` label, no trailing space/newline).
2. Confirm it starts with `https://farouk-tv-webhook-logger-v1.taylormartyn70.workers.dev/tv/` (not the
   old `trycloudflare.com`).
3. Definitive test: run `wrangler tail farouk-tv-webhook-logger-v1` (read-only) and re-fire — expect:
   - **POST 200** → object should exist (verify via temp read branch);
   - **POST 404** → secret path wrong (fix the pasted URL);
   - **no request** → TradingView not delivering (webhook not enabled/saved).
4. Reminder: `wrangler r2 object get` defaults to **local** — always use `--remote`. And `wrangler r2
   bucket info` object_count **lags** — use the temp list branch for a live count.

## 2. Worker rejects a request (wrong path → 404 / non-POST → 405)

- This is **correct** behaviour (PATH_ONLY, POST-only). Not an incident by itself.
- If a legitimate TradingView POST gets 404 → the alert's secret path is wrong (see #1).
- If everything 503s → `TV_WEBHOOK_ENABLED` is `0`, or the secret is unset (`not_configured`). Re-set
  `TV_WEBHOOK_ENABLED=1` / the secret via `wrangler secret put` (never printed).

## 3. R2 list / count mismatch

- Remember lagged metrics: `wrangler r2 bucket info` object_count can trail by up to ~an hour. Trust
  the **temp read-only list branch** (`EVIDENCE.list`) for a live, strongly-consistent count.
- If the temp list branch is deployed → **remove it and redeploy pure logging-only** (it must never be
  left deployed). Confirm `GET ?list` → 405 afterward.
- If a duplicate-fire wrote two objects → both are valid (report-time dedupe; distinct event_ids).

## 4. Telegram PREVIEW listener stopped

- Confirm: `Get-Process -Id 40416`. If gone, the laptop slept / it was closed.
- It is **observation-only**; restart is a **separate, explicitly-approved** action (do not auto-restart
  under an incident). Restart command is the documented preview command; `LISTENER_MODE=PREVIEW`.
- Note the gap in `MONITORING_RESUME_STATUS.md` (capture pauses while it's down).

## 5. Duplicate alert accidentally left running

- Any `*_GATE_G` / `*_GATE_H` duplicate not meant to persist → **disable/delete the duplicate** (never
  the original). Capture stops for that alert; original unaffected.
- If unsure which is original vs duplicate → the original is `LIVE001_ANY_ALERT_XAUUSD_3M` (and the
  other `LIVE001_*`); duplicates carry the `*_GATE_x` suffix.

## 6. Secret exposure concern (URL/secret path leaked)

- **Rotate immediately:** `wrangler secret put TV_WEBHOOK_SECRET_PATH` with a new value; update the
  gitignored `LOCAL_ONLY_*_WEBHOOK_URL.txt` and any mirrored alerts' webhook URLs; the old path then
  404s.
- Blast radius is **bounded**: the endpoint is logging-only — a leaker can at most POST junk that gets
  stored as noise. **No execution, no broker reach, no credential exfiltration** is possible.
- Review recent captures for unexpected POSTs; annotate (append-only) — never delete raw.
- Confirm the secret never landed in git (only in `LOCAL_ONLY_*` / `LOCAL_SECRET_*`, both gitignored)
  and never in an R2 object (`path` is stored as `/tv/<redacted>`).

---

## Golden rules during any incident

- Read-only diagnosis first; smallest reversible fix.
- Never enable execution, connect broker/QST, or create a permit/lease/order to "fix" capture.
- Never edit an original Farouk production alert; only touch duplicates.
- Never leave a temp read/list branch deployed — revert to pure logging-only.
- Keep gates `PAPER/PREVIEW/False/False`; `NOT_INTEGRATION_READY` stays unchanged.
