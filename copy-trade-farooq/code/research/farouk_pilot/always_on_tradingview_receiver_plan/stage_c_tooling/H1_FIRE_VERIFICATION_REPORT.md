# H1 Fire — R2 Capture Verification Report

**Mode: H1 FIRE VERIFICATION ONLY.** Observation/verification only. No broker/cTrader/QST/execution, no
permit/lease/order, no gate change, no trade instruction. `NOT_INTEGRATION_READY` unchanged. Date 2026-07-10.

## Fired alert

- **`LIVE004_APLUS_MIRROR_GATE_H1`** — the capture-only mirror of the original A+ / A+-or-better Farouk
  alert. Original A+ alert **NOT touched**; H2 `LIVE005_CHOCH_DOWN_MIRROR_GATE_H2` **NOT touched**.

## R2 verification result — ✅ CONFIRMED

The H1 A+ mirror POST reached the Cloudflare Worker and was written to the private R2 bucket
`farouk-tv-webhook-evidence-v1`.

- **Bucket object count: 90** (was ~75 at the last Gate G baseline → **increased**, consistent with H1
  and H2 mirrors delivering since).
- **H1 A+ capture object:**
  - key: `events/2026/07/10/0130f3b3-a8ae-4178-ab47-f4c0bb5d8ec0.jsonl`
  - `received_at_utc`: **2026-07-10T04:57:02.069Z** (UTC) — object uploaded 2026-07-10T04:57:02.508Z
  - `event_id`: `0130f3b3-a8ae-4178-ab47-f4c0bb5d8ec0`
  - `validation_status`: **ACCEPTED** · `mode`: **LOGGING_ONLY**
- **Newest object overall** is `events/2026/07/10/173c541f-…` @ 07:09:02Z, raw `CHoCH down (bearish)` — an
  **H2** capture, not H1. On Jul 10 the **only A+ object is the 04:57Z one above** → that is the H1 fire.

## Raw alert text (secret-redacted)

- **`raw_payload` = `"A+ or better setup"`** — preserved byte-exact.
- **A+ / A+-or-better?** **YES** — the text explicitly reads "A+ or better setup".
- **JSON or raw?** **INVALID_JSON** — i.e. raw indicator `alert()` text, **which is expected/acceptable**
  for the Farouk A+ alert (same as the Gate G real captures). `symbol`/`timeframe` are null because the raw
  text carries no `on <SYM> <TF>` suffix; the raw text is the source of truth.
- **instrument:** not embedded in this alert's text (null) — consistent with the raw A+ alert format.

## Secret / webhook-path exposure — NONE

- Stored object `path` field = **`/tv/<redacted>`** — the Worker deliberately does not store the secret
  path; **0 secret occurrences** in the object.
- Verification did **not** use the webhook secret at all: the temporary read branch was gated by a
  **throwaway token on a non-secret path** (`/__verify_list__?t=…`), and object fetches used wrangler
  **account auth** (not the secret). No webhook URL/secret printed to logs or reports.

## Worker restoration — pure logging-only ✅

- A **temporary, secret-free, token-gated, read-only list branch** was deployed **only** to enumerate object
  keys (R2 has no `wrangler` list command), then **reverted immediately**.
- Baseline captured before change: `src/index.js` sha256 `30bdc54d…`. After revert, src sha256 **matches
  baseline exactly**; the `__verify_list__` branch is **absent from source** (grep count 0). Backup file
  removed.
- Deploy versions (record): temp list branch `1f57e052-…` → reverted pure logging-only `92071676-…`.
- POST capture logic was left intact throughout (a real webhook arriving during the window would still be
  captured).

### Post-revert negative checks (live endpoint)

| Check | Expect | Result |
|---|---|---|
| `GET /__verify_list__?t=dummy` (temp branch gone) | 405 | **405** ✅ |
| `GET /__verify_list__` (no token) | 405 | **405** ✅ |
| `POST /tv/WRONG_NOT_THE_SECRET` (wrong path) | 404 | **404** ✅ |
| `GET /` | 405 | **405** ✅ |

## Safety confirmations

- Local gates: `MODE=PAPER`, `LISTENER_MODE=PREVIEW`, `EXECUTION_ENABLED=False`,
  `CTRADER_EXECUTION_ENABLED=False`; `ORDER_SENDING_ENABLED`/`ORDER_MANAGEMENT_ENABLED` **absent** (not
  defined). No broker/cTrader/QST; no permit/lease/order (data/ scanned — none). 1.0% risk cap unchanged.
- Telegram PREVIEW listener **PID 16608 running and untouched** (not started/stopped/restarted).
- Original A+ alert and H2 mirror **untouched**. No TradingView alert changed by Claude.
- No shadow engine; no classify/score/OHLC import performed (deferred — verification-first).
- `NOT_INTEGRATION_READY` **unchanged**.

## Next step

1. **Martyn:** delete/disable **ONLY** the fired H1 mirror `LIVE004_APLUS_MIRROR_GATE_H1`. **Do NOT** touch
   the original A+ alert; **do NOT** touch H2 `LIVE005_CHOCH_DOWN_MIRROR_GATE_H2`.
2. **Then (offline):** the A+ capture is verified — proceed with the observation cycle: import the Jul-10
   XAUUSD 1m OHLC, run classifier → detector → matcher → scorer on the new A+ (and the H2 CHoCH-down
   captures), append any outcome-matched candidates to the journal and enqueue for review batch 002.
   Observation-only.
