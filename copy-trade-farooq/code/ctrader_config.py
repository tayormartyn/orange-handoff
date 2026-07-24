"""
ctrader_config.py — configuration for the READ-ONLY cTrader Open API connection.

Pepperstone Europe DEMO (cTrader). This connection is READ-ONLY BY CONSTRUCTION:
  * No order placement / modification / cancellation code exists anywhere in this
    build. The protobuf order messages are never imported or sent.
  * CTRADER_EXECUTION_ENABLED is a hard lock (MUST stay False). Any future reader
    asserts it before connecting, mirroring the engine's EXECUTION_ENABLED safety.

This file holds NO secrets. Client id/secret come from environment variables and are
never written to disk or logged. The OAuth token is stored in a gitignored file.

Scope note (CORRECTED 2026-06-29 from cTrader Open API primary-source docs; supersedes a
stale earlier note that claimed cTrader had no view-only scope):
  * OAuth scope `accounts` = VIEW-ONLY (account info + statistics; trading not permitted).
  * OAuth scope `trading`  = full account AND trading access.
  * A returned token's permission is reported as `SCOPE_VIEW` or `SCOPE_TRADE`.
This build uses the VIEW-ONLY scope only. The single authority for scope handling is
campaign_extractor/broker_readonly/oauth_scope.py: internal 'view' -> OAuth 'accounts';
OAuth 'trading' is NEVER emitted; any returned permission that is not SCOPE_VIEW is
rejected. (Whether the precise read surface — quotes/positions — is available under
`accounts` must be VERIFIED during the separately-approved activation burn-in, not assumed.)
"""

import os

# ---- hard read-only lock (mirrors config.EXECUTION_ENABLED) -----------------
CTRADER_EXECUTION_ENABLED = False     # MUST stay False — there is no order path anyway
BROKER_ENV = "demo"                   # "demo" only in this build; LIVE not wired

# ---- endpoints (proven reachable) -------------------------------------------
HOST_DEMO = "demo.ctraderapi.com"
HOST_LIVE = "live.ctraderapi.com"
PORT_PROTOBUF = 5035                  # TLS protobuf socket (the live read channel)
OAUTH_AUTH_URL = "https://openapi.ctrader.com/apps/auth"
OAUTH_TOKEN_URL = "https://openapi.ctrader.com/apps/token"

# VIEW-ONLY scope only. cTrader's `accounts` scope is view-only; `trading` is NEVER emitted
# by our code. Authority: campaign_extractor/broker_readonly/oauth_scope.py. Read-only is
# enforced by BOTH this view-only scope AND client-side (no order code + execution lock).
DEFAULT_SCOPE = "accounts"

# Where the OAuth token is cached (gitignored — never commit). Refresh token kept
# alongside so the access token can be renewed without re-authorising in a browser.
TOKEN_FILE = os.path.join("data", "ctrader_token.json")

# Redirect URI must match the one registered on the cTrader app. For a manual flow,
# a localhost URI is fine — you copy the ?code=... back by hand.
DEFAULT_REDIRECT_URI = os.environ.get("CTRADER_REDIRECT_URI", "http://localhost/")

# The gold symbol to read (resolved to a numeric symbolId live).
GOLD_SYMBOL = os.environ.get("CTRADER_GOLD_SYMBOL", "XAUUSD")


def client_id():
    return os.environ.get("CTRADER_CLIENT_ID")


def client_secret():
    return os.environ.get("CTRADER_CLIENT_SECRET")


def host():
    return HOST_DEMO if BROKER_ENV == "demo" else HOST_LIVE


def mask(s):
    """Mask a secret for safe display — never reveal the full value."""
    if not s:
        return None
    s = str(s)
    return (s[:4] + "…" + s[-2:]) if len(s) > 8 else "***"
