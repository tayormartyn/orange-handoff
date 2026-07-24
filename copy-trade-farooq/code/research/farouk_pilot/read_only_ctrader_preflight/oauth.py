"""OAuth code->token acquisition (VIEW-ONLY). Two guarantees enforced structurally:

1. SCOPE IS HARDCODED. build_authorize_url takes NO scope argument; it always emits the
   view-only scope (config.OAUTH_EMIT_SCOPE == 'accounts'). There is no code path, parameter, or
   branch that can request a trading scope. A test asserts the function has no 'scope' parameter
   and that the built URL never contains the word 'trading'.
2. THE TOKEN EXCHANGE IS PHASE-2 GATED AND LAZY. exchange_code_for_token refuses unless
   config.PHASE2_CONNECT_OPT_IN is set; only then does it lazily import urllib and POST to the
   token endpoint. Phase 1 therefore imports this module with NO network module loaded and opens
   no socket. The client secret and the returned token NEVER touch stdout/logs/args/ledgers/chat
   (DPAPI storage via credentials; only a redacted summary is ever returned).
"""
from . import config, credentials


class OAuthNotAuthorised(Exception):
    """Phase-2 gate not satisfied (no accounts-scope opt-in). No network is attempted."""


class ExchangeFailed(Exception):
    """The token endpoint did not return a usable access token (error body / empty / bad shape).
    Nothing is stored. The caller must report [FAILED], never [TOKEN STORED]."""


def _finalize_token(token):
    """Validate the token-endpoint response. Store + return a redacted summary ONLY when a
    usable access token is present; otherwise raise ExchangeFailed and store NOTHING. This is
    the fix for the defect where an error body (e.g. errorCode=ACCESS_DENIED) was stored and
    reported as success."""
    if not isinstance(token, dict):
        raise ExchangeFailed("token endpoint returned a non-object body")
    err = token.get("errorCode") or token.get("error")
    at = token.get("accessToken") or token.get("access_token")
    if err or not (at and str(at).strip()):
        # sanitised: the errorCode is a non-secret diagnostic; never echo the code/secret.
        raise ExchangeFailed(f"no access token returned (errorCode={token.get('errorCode') or token.get('error')})")
    credentials.store_token(token)
    return credentials.redact_token(token)


def build_authorize_url(client_id):
    """Build the consent URL. NOTE: no 'scope' parameter exists here by design -- the emitted
    scope is fixed to config.OAUTH_EMIT_SCOPE ('accounts', view-only)."""
    from urllib.parse import urlencode      # stdlib, pure-string; no network
    assert config.OAUTH_EMIT_SCOPE == "accounts"          # invariant: view-only only
    q = urlencode({
        "client_id": client_id,
        "redirect_uri": config.OAUTH_REDIRECT_URI,
        "scope": config.OAUTH_EMIT_SCOPE,                  # HARDCODED accounts; never 'trading'
        "product": "web",
    })
    return f"{config.OAUTH_AUTH_URL}?{q}"


def exchange_code_for_token(code):
    """Phase-2 ONLY. Exchange an authorization code for a VIEW-ONLY token, store it via DPAPI,
    and return a REDACTED summary (never the token). Refuses (no network) unless opted in."""
    if not config.PHASE2_CONNECT_OPT_IN:
        raise OAuthNotAuthorised(
            "Phase 2 not authorised: set ORANGE_PREFLIGHT_CONNECT=1 only after the operator's "
            "accounts-scope (view-only) grant. Phase 1 performs no OAuth and opens no socket.")
    creds = credentials.load_credentials()
    if creds is None:
        raise OAuthNotAuthorised("no stored client credentials (run credentials.store_credentials first)")
    client_id, client_secret = creds
    # LAZY network import: nothing is imported until an authorised exchange actually runs.
    import json
    from urllib.parse import urlencode
    from urllib.request import urlopen, Request
    body = urlencode({
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": config.OAUTH_REDIRECT_URI,
        "client_id": client_id,
        "client_secret": client_secret,
    }).encode("utf-8")
    req = Request(config.OAUTH_TOKEN_URL, data=body,
                  headers={"Content-Type": "application/x-www-form-urlencoded"})
    with urlopen(req, timeout=30) as resp:          # Phase-2 network; never reached in Phase 1
        token = json.loads(resp.read().decode("utf-8"))
    return _finalize_token(token)                   # stores ONLY on a usable token; else raises
