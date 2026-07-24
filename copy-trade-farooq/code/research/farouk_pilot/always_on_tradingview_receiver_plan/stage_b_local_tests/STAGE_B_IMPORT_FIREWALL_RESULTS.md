# Stage B — Import Firewall Results

**Run:** 2026-07-07 (test B9). **Mode: LOCAL UNIT TEST ONLY.** No deployment, no network exposure.

## What the firewall does

The receiver's `_startup_safety_check()` (in
`tradingview_webhook_plan/stage1_local_receiver/receiver.py`, reused as the Stage B oracle) enumerates
loaded modules at start and **refuses to start (fail-closed, `SystemExit(2)`)** if any loaded module
name contains a forbidden marker:

```
ctrader, broker, qst, module_execution, module_c_risk, module_d_logger,
pipeline, shadow_run, shadow_db, archive, management_permit, one_shot_permit, activation_lease
```

## Test B9 — two-part check

| Part | Setup | Expected | Result |
|---|---|---|---|
| Clean pass | no forbidden module loaded | `_startup_safety_check()` returns normally | ✅ passed (no exit) |
| Fail-closed | inject `sys.modules["ctrader_fake_injected"]` | `_startup_safety_check()` raises `SystemExit(2)` | ✅ refused (`code==2`) |

**Observed output during the run:**
```
REFUSING TO START — forbidden module(s) loaded: ['ctrader_fake_injected']
```
This line is the firewall **working correctly** — it detected the injected forbidden module and
refused. `B9: PASS  clean_pass=True forbidden_refused=True`.

## Why this matters

- Proves the receiver **cannot start** if any broker / cTrader / QST / execution / permit / lease /
  order module is present — a structural guarantee that the always-on receiver has **no execution
  surface**.
- Combined with the import audit (harness + oracle import **stdlib only**), there is no code path from
  the receiver to a broker/QST/execution/permit/lease/order module, and no outbound trading request is
  possible.

## Scope note

B9 tests the firewall logic locally. The same fail-closed check is specified for the future
Cloudflare Worker at cold start (see `../stage_b_c_preparation/ALWAYS_ON_RECEIVER_SAFETY_SPEC_v0.1.md`
and `CLOUDFLARE_WORKERS_R2_IMPLEMENTATION_NOTES.md`) — a Worker additionally cannot import the Python
engine at all, and its bindings are limited to the one R2 bucket.
