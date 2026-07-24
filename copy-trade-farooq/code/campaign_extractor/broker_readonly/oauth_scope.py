"""
Brick 3A — deterministic OAuth scope reconciliation (cTrader Open API).

PRIMARY-SOURCE facts (cTrader Open API documentation):
  * OAuth scope `accounts` = VIEW-ONLY access to account information and statistics;
    trading operations are NOT permitted.
  * OAuth scope `trading`  = full account AND trading access.
  * A returned token's permission is reported as `SCOPE_VIEW` or `SCOPE_TRADE`.

This corrects the earlier (stale) project belief that cTrader has no view-only scope.

This module is the SINGLE AUTHORITY for scope handling. Our internal safety setting stays
CTRADER_SCOPE='view'. We emit ONLY the view-only OAuth scope ('accounts'); OAuth 'trading'
is NEVER emitted by our code, and any returned permission that is not provably view-only is
rejected. No network, no OAuth, no credentials are involved here.
"""

INTERNAL_VIEW = "view"
OAUTH_ACCOUNTS = "accounts"        # view-only OAuth scope
OAUTH_TRADING = "trading"          # full trading scope — NEVER emitted by our code
RETURNED_VIEW = "SCOPE_VIEW"
RETURNED_TRADE = "SCOPE_TRADE"


class ScopeError(Exception):
    pass


def oauth_scope_for(internal_scope) -> str:
    """Map an internal scope to the OAuth query value.

    Only the internal 'view' scope is permitted; it maps to the view-only OAuth scope
    'accounts'. Everything else — including 'trading', empty, None, or any unknown value
    — is rejected. This function can NEVER return 'trading'."""
    if internal_scope == INTERNAL_VIEW:
        return OAUTH_ACCOUNTS
    raise ScopeError(
        f"refused internal scope {internal_scope!r}: only 'view' is permitted (maps to "
        f"OAuth '{OAUTH_ACCOUNTS}'); OAuth '{OAUTH_TRADING}' is never emitted by our code")


def assert_returned_scope_admissible(returned) -> bool:
    """Accept ONLY an explicit SCOPE_VIEW. Reject SCOPE_TRADE, unknown, or absent (None)."""
    if returned == RETURNED_VIEW:
        return True
    raise ScopeError(
        f"returned permission scope not admissible: {returned!r} — only {RETURNED_VIEW} is "
        f"accepted; {RETURNED_TRADE}, unknown, or absent permission is rejected")
