"""
cTrader A2 — VIEW-ONLY read-only reader (OFFLINE build).

Reads basic demo-account info over the cTrader Open API using an ALREADY-CACHED view-only
token. It NEVER mints or requests a token, never opens an authorisation URL, never retries,
and stops immediately on HTTP 429. It contains NO create/amend/cancel/close-position path and
requests NO trading scope.

The reader logic is transport-abstracted and offline-tested with a mock transport. The real
Twisted/protobuf transport (ctrader_open_api) is finalised and RUN only at the separately
authorised A2 connection step — not during this offline build.
"""
A2_VERSION = "ctrader-a2.0"
