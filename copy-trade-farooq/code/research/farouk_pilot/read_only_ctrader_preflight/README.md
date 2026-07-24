# READ_ONLY_CTRADER_PREFLIGHT_v0_1

A **separate, manually-invoked, view-only** cTrader preflight (ChatGPT-authorised). Not
importable by the demo-lane executor, the seven Orange services, or the campaign/dataset
pipelines — it shares no module with them and imports nothing from them.

## Scope (binding)
- **Network authority:** `demo.ctraderapi.com:5035` only. No live path exists in the tool.
- **OAuth:** emits `accounts` (view-only); **never** `trading`. Requires the granted scope be
  `SCOPE_VIEW` and **refuses** `SCOPE_TRADE`.
- **Only these read operations** (`read_ops.ALLOWED_READ_MESSAGES`): application auth, account
  enumeration, demo-account session auth, account details, symbol list, XAUUSD metadata,
  heartbeat. **No** generic protobuf send, **no** arbitrary message type, **no** raw-payload
  input, **no** trade-capable request class. The transport's only dispatch path is private and
  name-checked against the whitelist.
- **Fail-closed** (`guard.require_or_exit`): proceed only when endpoint==`demo.ctraderapi.com:5035`
  AND scope view-only AND `isLive==false` AND account==allowlisted demo AND environment==Pepperstone
  demo AND XAUUSD resolves to exactly one symbol; otherwise stop, sanitised error, exit non-zero.
- **Credentials:** never in repo/.env/args/history/stdout/stderr/reports/ledgers — Windows DPAPI
  (`credentials.py`, blob in `%LOCALAPPDATA%\Orange`, outside the repo). No unattended refresh.

## Phases
- **Phase 1 (this build): static proof only** — no OAuth, no socket, no connect. `ctrader_open_api`
  and `ssl`/`socket` are imported **lazily inside `connect()`**, so the package imports offline.
- **Phase 2 (gated, NOT run):** `connect()` refuses unless the operator has done the accounts-scope
  OAuth grant AND set `ORANGE_PREFLIGHT_CONNECT=1`. See `OAUTH_INSTRUCTIONS.md`.

## Run
```
python research/farouk_pilot/read_only_ctrader_preflight/tests_preflight.py        # 46/46
python research/farouk_pilot/read_only_ctrader_preflight/scan_executor_network.py  # EXECUTOR_NETWORK_CAPABILITY = ZERO
python -m research.farouk_pilot.read_only_ctrader_preflight.preflight               # Phase-1 static report (no connect)
```

## Executor isolation
`scan_executor_network.py` proves the demo-lane executor's import closure contains **zero**
network imports and **zero** imports of this package — a shared import cannot create a network
path into the executor. Re-run it whenever either package changes.
