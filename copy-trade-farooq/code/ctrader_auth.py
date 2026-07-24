"""
ctrader_auth.py — READ-ONLY OAuth helper for the cTrader Open API (stdlib only).

Handles the OAuth 2.0 authorization-code flow to obtain (and refresh) an access token
for a Pepperstone DEMO cTrader account. It does NOTHING else — no trading, no order
messages, no market socket. Secrets are read from the environment and NEVER logged;
the token is stored in a gitignored file.

MANUAL STEP (only you can do this — a browser login):
  1) Ensure CTRADER_CLIENT_ID and CTRADER_CLIENT_SECRET are set in THIS environment.
  2) python ctrader_auth.py url           # prints the authorize URL
  3) Open it in a browser, log into your cTrader ID (Pepperstone DEMO), authorize.
  4) The browser redirects to <redirect_uri>?code=XXXX — copy the code.
  5) python ctrader_auth.py token XXXX    # exchanges the code for a token (stored)
  6) python ctrader_auth.py status        # confirm a token is cached (masked)
Later, `python ctrader_auth.py refresh` renews the access token without a browser.

Token endpoint: POST https://openapi.ctrader.com/apps/token. Reachability proven.
PAPER/DEMO, read-only. config.MODE / EXECUTION_ENABLED / LISTENER_MODE + LIVE stub
are untouched by this module.
"""

import json
import os
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone

import ctrader_config as cfg


def build_auth_url(scope=None, redirect_uri=None, client_id=None):
    """Construct the browser authorization URL. VIEW-ONLY: emits the `accounts` scope
    (cTrader's view-only scope). OAuth `trading` is NEVER emitted — a defense-in-depth
    guard hard-fails if a trading scope is ever supplied. See ctrader_config /
    broker_readonly/oauth_scope (the scope authority)."""
    cid = client_id or cfg.client_id()
    if not cid:
        raise RuntimeError("CTRADER_CLIENT_ID is not set in this environment.")
    resolved_scope = scope or cfg.DEFAULT_SCOPE
    if "trade" in resolved_scope.lower() or "trading" in resolved_scope.lower():
        raise RuntimeError(
            f"refused to emit a trading OAuth scope ({resolved_scope!r}); this build is "
            f"view-only ('accounts'). OAuth 'trading' is never emitted.")
    params = {
        "client_id": cid,
        "redirect_uri": redirect_uri or cfg.DEFAULT_REDIRECT_URI,
        "scope": resolved_scope,
    }
    return cfg.OAUTH_AUTH_URL + "?" + urllib.parse.urlencode(params)


def _post_token(data):
    """POST form-encoded data to the token endpoint, return parsed JSON.
    `data` includes the client_secret — it is sent over TLS and NEVER logged."""
    body = urllib.parse.urlencode(data).encode("utf-8")
    req = urllib.request.Request(
        cfg.OAUTH_TOKEN_URL, data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded",
                 "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


def _extract(resp):
    """Pull access/refresh token from the response (handle camel/snake variants)."""
    def pick(*keys):
        for k in keys:
            if resp.get(k):
                return resp[k]
        return None
    return {
        "access_token": pick("accessToken", "access_token"),
        "refresh_token": pick("refreshToken", "refresh_token"),
        "expires_in": pick("expiresIn", "expires_in"),
        "token_type": pick("tokenType", "token_type"),
        "error": pick("errorCode", "error", "description"),
    }


def exchange_code(code, redirect_uri=None):
    """Exchange an authorization `code` for tokens, then store them (gitignored)."""
    cid, secret = cfg.client_id(), cfg.client_secret()
    if not cid or not secret:
        raise RuntimeError("CTRADER_CLIENT_ID / CTRADER_CLIENT_SECRET not set in env.")
    resp = _post_token({
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": redirect_uri or cfg.DEFAULT_REDIRECT_URI,
        "client_id": cid,
        "client_secret": secret,
    })
    tok = _extract(resp)
    if not tok["access_token"]:
        raise RuntimeError(f"token exchange failed: {resp.get('errorCode') or resp}")
    _save(tok)
    return tok


def refresh_access_token():
    """Renew the access token using the stored refresh token (no browser needed)."""
    cur = load_token()
    if not cur or not cur.get("refresh_token"):
        raise RuntimeError("no stored refresh_token — run the browser authorize flow first.")
    cid, secret = cfg.client_id(), cfg.client_secret()
    resp = _post_token({
        "grant_type": "refresh_token",
        "refresh_token": cur["refresh_token"],
        "client_id": cid,
        "client_secret": secret,
    })
    tok = _extract(resp)
    if not tok["access_token"]:
        raise RuntimeError(f"refresh failed: {resp.get('errorCode') or resp}")
    # keep the old refresh token if a new one wasn't returned
    if not tok["refresh_token"]:
        tok["refresh_token"] = cur["refresh_token"]
    _save(tok)
    return tok


def _save(tok):
    os.makedirs(os.path.dirname(cfg.TOKEN_FILE) or ".", exist_ok=True)
    tok = dict(tok)
    tok["saved_at_utc"] = datetime.now(timezone.utc).isoformat()
    with open(cfg.TOKEN_FILE, "w", encoding="utf-8") as f:
        json.dump(tok, f, indent=2)
    try:                                   # best-effort tighten perms (POSIX)
        os.chmod(cfg.TOKEN_FILE, 0o600)
    except OSError:
        pass


def load_token():
    if not os.path.exists(cfg.TOKEN_FILE):
        return None
    with open(cfg.TOKEN_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def status():
    print("cTrader OAuth status (read-only build):")
    print(f"  env: BROKER_ENV={cfg.BROKER_ENV}  host={cfg.host()}:{cfg.PORT_PROTOBUF}  "
          f"CTRADER_EXECUTION_ENABLED={cfg.CTRADER_EXECUTION_ENABLED}")
    print(f"  CTRADER_CLIENT_ID    : {cfg.mask(cfg.client_id()) or 'NOT SET'}")
    print(f"  CTRADER_CLIENT_SECRET: {'set (masked)' if cfg.client_secret() else 'NOT SET'}")
    print(f"  redirect_uri         : {cfg.DEFAULT_REDIRECT_URI}")
    print(f"  scope                : {cfg.DEFAULT_SCOPE}  (read-only enforced client-side)")
    tok = load_token()
    if tok:
        print(f"  token cache          : {cfg.TOKEN_FILE}")
        print(f"    access_token       : {cfg.mask(tok.get('access_token')) or '-'}")
        print(f"    refresh_token      : {'present' if tok.get('refresh_token') else '-'}")
        print(f"    saved_at_utc       : {tok.get('saved_at_utc')}")
    else:
        print(f"  token cache          : none yet ({cfg.TOKEN_FILE})")
    if not cfg.client_id() or not cfg.client_secret():
        print("\n  -> Set CTRADER_CLIENT_ID and CTRADER_CLIENT_SECRET in THIS environment,")
        print("     then: python ctrader_auth.py url")


def _usage():
    print("usage: python ctrader_auth.py [status | url | token <CODE> | refresh]")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    try:
        if cmd == "status":
            status()
        elif cmd == "url":
            print(build_auth_url())
            print("\n  ^ open in a browser, authorize, copy the ?code= from the redirect,")
            print("    then: python ctrader_auth.py token <CODE>")
        elif cmd == "token":
            if len(sys.argv) < 3:
                _usage(); sys.exit(2)
            t = exchange_code(sys.argv[2])
            print(f"OK — access token stored (masked {cfg.mask(t['access_token'])}), "
                  f"refresh_token {'stored' if t.get('refresh_token') else 'absent'}.")
        elif cmd == "refresh":
            t = refresh_access_token()
            print(f"OK — refreshed (masked {cfg.mask(t['access_token'])}).")
        else:
            _usage(); sys.exit(2)
    except RuntimeError as e:
        print(f"STOP: {e}")
        sys.exit(1)
