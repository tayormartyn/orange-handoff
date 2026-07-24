"""READ_ONLY_DEMO_PREFLIGHT_v0_1 — a SEPARATE, manually-invoked, view-only preflight tool.

This package is NOT the execution lane and shares NONE of its order-placing code. It
imports only pure read-only helpers (sizing math, price representability). It contains
no order-placement or position-close message, no real executor adapter, and no gate flip.

Hard scope (binding):
  * OAuth scope emitted MUST be 'accounts' (view-only). 'trading' is NEVER emitted.
  * The GRANTED permission is verified to be SCOPE_VIEW and NOT SCOPE_TRADE, and is
    reported AS OBSERVED, not as requested. A SCOPE_TRADE grant is REFUSED.
  * Connects only to demo.ctraderapi.com; isLive must be False; the account must be the
    allowlisted Pepperstone demo account in the expected broker environment.
  * Retrieves read-only XAUUSD metadata and reports CANDIDATE quantity conversions only —
    it never selects, ratifies, or rounds a quantity.
"""
__all__ = ["preflight_config", "verify", "metadata", "conversions", "credentials", "acl"]
