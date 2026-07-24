# Mandatory pre-activation requirements (broker read-only)

These are MANDATORY and must be satisfied BEFORE any broker activation (the separately
approved cTrader Open API connection). Recorded here so they cannot be forgotten.

## 1. Secret scan must cover the COMPLETE runtime authentication path
The `scan_secret_leaks` check must run over the **entire runtime auth path**, not only the
new `broker_readonly` package. This explicitly includes the pre-existing
**`ctrader_auth.py`** (and `ctrader_config.py`) — the code that will actually perform OAuth
and hold tokens at activation.

- The scanner must NOT be loosened merely to silence informational warnings.
- As of Brick 3A, `ctrader_auth.py` produces 6 informational `secret-in-log` hits that were
  manually verified as FALSE POSITIVES (it masks via `cfg.mask(...)` and prints labels such
  as `'set (masked)'` / `'present'`, never raw values). The conservative scanner is kept
  as-is; this requirement ensures the full path is re-scanned and re-verified at activation,
  when real tokens exist and the risk is real.

## 2. Scope authority
`broker_readonly/oauth_scope.py` is the single authority for OAuth scope:
- internal `view` -> OAuth `accounts` (view-only)
- OAuth `trading` is NEVER emitted by our code
- returned `SCOPE_VIEW` accepted; `SCOPE_TRADE` / unknown / absent rejected

At activation, confirm from the returned token that permission is `SCOPE_VIEW`; reject
otherwise. Verify (do not assume) the exact read surface available under `accounts`.

## 3. Standing locks (must hold at activation)
`MODE=PAPER`, `EXECUTION_ENABLED=False`, `LISTENER_MODE=PREVIEW`,
`CTRADER_EXECUTION_ENABLED=False`; no order-code; demo environment only.
