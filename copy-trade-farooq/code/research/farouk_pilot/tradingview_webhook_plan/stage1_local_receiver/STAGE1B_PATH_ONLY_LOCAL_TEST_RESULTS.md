# Stage 1B — PATH_ONLY Local Compatibility Test Results

**Run:** 2026-07-07 09:26 local (Italy UTC+1). **Mode: LOCAL TEST ONLY.**
Localhost only. No Stage 2, no tunnel, no public URL, no TradingView config, no broker/QST/execution,
no permit/lease/order, no execution-gate change. Telegram PREVIEW listener untouched.

## Purpose

Verify the receiver's new **`PATH_ONLY`** mode (TradingView-compatible: the exact long random secret
path authenticates, **no custom header required**) works locally before any real TradingView attempt.

## Setup

- **Receiver:** `research/farouk_pilot/tradingview_webhook_plan/stage1_local_receiver/receiver.py`
- **Auth mode:** `PATH_ONLY` (banner confirmed `Auth mode : PATH_ONLY`, `X-TV-Token : optional`).
- **Fresh long random secret path:** generated via `secrets.token_urlsafe(32)` →
  `/tv/dJxhnqM3h7b4vnnl3S8qkVEajUkhaTymFH5sskOgmqg` (single-use test value; not a real production
  secret).
- **Port:** 8791 (localhost). **Bind:** `127.0.0.1` only.
- **Test payload:** `sample_payloads/manual_post_pathonly.json` (distinct from the Stage 1 payload so
  it logs as a fresh `ACCEPTED`, not a `DUPLICATE`). No credentials, no broker instruction.

## Commands

**Start (PATH_ONLY, fresh secret, port 8791):**
```
TV_WEBHOOK_AUTH_MODE=PATH_ONLY \
TV_WEBHOOK_SECRET_PATH="dJxhnqM3h7b4vnnl3S8qkVEajUkhaTymFH5sskOgmqg" \
TV_WEBHOOK_PORT=8791 \
python research/farouk_pilot/tradingview_webhook_plan/stage1_local_receiver/receiver.py
```

**(1) Valid POST — correct secret path, NO X-TV-Token header:**
```
curl -s -X POST "http://127.0.0.1:8791/tv/dJxhnqM3h7b4vnnl3S8qkVEajUkhaTymFH5sskOgmqg" \
  -H "Content-Type: application/json" \
  --data-binary @sample_payloads/manual_post_pathonly.json
```

**(2) POST to incorrect path:**
```
curl -s -X POST "http://127.0.0.1:8791/tv/WRONG-...-WRONG" \
  -H "Content-Type: application/json" \
  --data-binary @sample_payloads/manual_post_pathonly.json
```

**(3) GET to correct path:**
```
curl -s "http://127.0.0.1:8791/tv/dJxhnqM3h7b4vnnl3S8qkVEajUkhaTymFH5sskOgmqg"
```

## Results

| # | Request | HTTP | Body | Stored record |
|---|---|---|---|---|
| 1 | Valid POST, **no** X-TV-Token, correct path | **200** | `{"ok":true,...,"validation_status":"ACCEPTED","parse_status":"PARSED","duplicate":false}` | **ACCEPTED** |
| 2 | POST to wrong path | **404** | `{"ok":false,"error":"not_found"}` | **none** (correct) |
| 3 | GET to correct path | **405** | `{"ok":false,"error":"method_not_allowed","allow":"POST"}` | **none** (correct) |

**New ACCEPTED record (item 1):**
- `validation_status: ACCEPTED`, `parse_status: PARSED`, `event_type: CHOCH_UP`, `direction: bullish`,
  `grade: NA`, `symbol: XAUUSD`, `timeframe: 3`, `method: POST`.
- `notes: "PATH_ONLY: authenticated by secret path; no header (expected for TradingView)"`.
- `raw_headers_safe` contains **no** X-TV-Token (confirmed the request carried no custom header).

**JSONL record count:** baseline **3** → post-test **4** (delta **+1**, exactly the single valid POST).
Full tally: `ACCEPTED ×2` (Stage 1 valid + this PATH_ONLY valid), `REJECTED_AUTH ×1` (Stage 1),
`DUPLICATE ×1` (Stage 1). The wrong-path and GET requests correctly added **no** records.

## Post-test safety check (read-only)

- **Receiver imports:** `hmac, http.server, json, os, sys, uuid, datetime, hashlib` only — **no
  broker/cTrader/QST/execution/permit** import. Start-up import firewall passed.
- **Broker/QST/execution processes:** **NONE.**
- **Permit/lease/order artifacts:** **NONE created.**
- **Execution gates (read-only):** `MODE=PAPER`, `LISTENER_MODE=PREVIEW`, `EXECUTION_ENABLED=False`,
  `CTRADER_EXECUTION_ENABLED=False` — **unchanged**.
- **Telegram PREVIEW listener:** **RUNNING, PID 40416, UNTOUCHED** (started 08:14:54).
- **Receiver:** stopped cleanly after the test (kill switch OK); not left running.

## Verdict

**PATH_ONLY local compatibility test: PASS.** The receiver accepts a header-less POST to the exact
long random secret path (as real TradingView would send), rejects a wrong path (404) and a non-POST
(405), stores exactly one append-only ACCEPTED record, and touches no execution/broker/QST path.

**Note:** this proves *local* PATH_ONLY behaviour only. It does **not** start Stage 2 — no tunnel, no
public URL, no TradingView alert. Stage 2 remains on HOLD pending explicit authorisation.
