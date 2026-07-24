# READ_ONLY_DEMO_PREFLIGHT_v0_1

A **separate, manually-invoked, view-only** preflight tool. It is **not** the execution
lane and shares none of its order-placing code. There is no persistent eighth process; you
run it by hand and it exits.

## What it does (and only this)
1. **Verifies the connection locally** against the allowlist and reports the granted OAuth
   permission **as observed, not as requested**:
   - `endpoint == demo.ctraderapi.com`
   - `isLive is False`
   - `ctidTraderAccountId ==` the allowlisted Pepperstone demo account
   - `broker_environment == PEPPERSTONE_DEMO`
   - granted scope is **`SCOPE_VIEW` (accounts) and NOT `SCOPE_TRADE` (trading)**.
   A `SCOPE_TRADE` grant is a **refusal** condition — the tool stops and tells you to
   revoke and re-grant view-only.
2. **Retrieves read-only XAUUSD metadata**: symbolId, name, enabled/trading status, digits/
   price precision, pip position, lotSize, minVolume, maxVolume, stepVolume, minimum
   stop-distance **and its unit** (flagged `UNSPECIFIED_CONFIRM_BEFORE_USE` if the broker
   omits the unit), and trading-session info where available.
3. **Reports CANDIDATE quantity conversions only.** For each candidate nominal it shows the
   exact human-readable quantity alongside the exact protocol volume. It **selects nothing,
   recommends nothing, ratifies nothing, and rounds in neither direction** — a nominal that
   does not land exactly on a protocol unit is reported `HALT` with the reason. You ratify a
   specific `(nominal_lots, protocol_volume)` pair knowingly.
4. **Redacts** the account identity in the returned package to a SHA-256 hash + last four.

## What it can never do (prohibited by absence — see the test suite)
- No OAuth `trading` scope is ever emitted (only `accounts`).
- No order-placement or position-close message is imported or defined (`ProtoOANewOrderReq`,
  `ProtoOAClosePositionReq`, `place_limit`, `close_position`, `cancel_order`, … all absent).
- No import of the execution-lane modules (`executor`, `mock_broker`, `approval_tool`,
  `reconcile`).
- No gate flip; `DEMO_EXECUTION_ENABLED = True` / `EXECUTION_ENABLED = True` appear nowhere.
- No credentials in the repo, `.env`, logs, or ledgers. Client id/secret are encrypted at
  rest with Windows **DPAPI** (`CryptProtectData`, CurrentUser) in `%LOCALAPPDATA%\Orange`,
  outside the repository tree.

## Modes
- **DRY_RUN_MOCK (default):** no network, no OAuth. Runs the full verification / metadata /
  conversion / redaction logic against an in-memory mock read broker. This is what the test
  suite proves. The observed values in this mode are **placeholders**, not the real account.
- **LIVE_READ:** requires Martyn's `accounts`-scope OAuth grant *and* an explicit opt-in
  (`ORANGE_PREFLIGHT_LIVE_READ=1`). The view-only read client that fills in the real observed
  values is attached during the **separately-authorised activation burn-in** — never by this
  tool, and never automatically.

## Run
```
python research/farouk_pilot/demo_lane/preflight/tests_preflight.py     # 64/64 pass
python -m research.farouk_pilot.demo_lane.preflight.preflight           # dry-run report
```

## Windows ACL two-identity separation
`acl.py` emits the `icacls` provisioning commands and a verifier that reads back
`icacls <dir>` output and asserts:
- the **executor** identity is **denied** create/modify/rename/delete on the immutable
  approvals store;
- the **approval-tool** identity is **denied** write on the executor outbox/intent store
  (so it cannot produce an order intent → cannot place orders);
- the **executor** identity may write **only** its consumption (receipts) and outbox stores.

The two OS principals are created by an administrator at deploy time (a system change
outside this read-only tool). The verifier's parser is proven here against real `icacls`
output before it is pointed at the provisioned principals.

See `OAUTH_INSTRUCTIONS_FOR_MARTYN.md` for the view-only grant steps.
