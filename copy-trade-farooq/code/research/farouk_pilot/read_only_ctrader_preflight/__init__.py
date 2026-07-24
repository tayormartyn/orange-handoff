"""READ-ONLY cTrader PREFLIGHT (ChatGPT-authorised; Phase 1 build).

A SEPARATE, manually-invoked, VIEW-ONLY tool. It is deliberately NOT importable by the
demo-lane executor, the seven Orange services, or the campaign/dataset pipelines: it shares
no module with them and imports nothing from them, so its (view-only) network capability can
never create a network path into the executor.

Hard scope (binding):
  * Network authority: demo.ctraderapi.com:5035 ONLY.
  * OAuth scope emitted: 'accounts' (view-only). 'trading' is NEVER emitted.
  * ONLY these read operations: application auth, account enumeration, demo-account session
    auth, account details, symbol list, XAUUSD metadata, heartbeat. There is NO generic
    protobuf send, NO arbitrary message type, NO raw-payload input, NO trade-capable class.
  * Fail-closed: proceed only when endpoint==demo.ctraderapi.com:5035 AND scope view-only AND
    isLive==False AND account==allowlisted demo AND environment==Pepperstone demo AND XAUUSD
    resolves unambiguously; otherwise stop with a sanitised error and a non-zero exit.
  * Credentials: never in repo/.env/args/history/stdout/stderr/reports/ledgers — Windows
    DPAPI/Credential Manager only; no unattended refresh service.

Phase 1 = build + STATIC proof only (no OAuth, no connect). Phase 2 (connect) is gated and
NOT executed here.
"""
__all__ = ["config", "guard", "credentials", "allowlist", "oauth",
           "read_ops", "transport", "preflight", "loopback_exchange"]
