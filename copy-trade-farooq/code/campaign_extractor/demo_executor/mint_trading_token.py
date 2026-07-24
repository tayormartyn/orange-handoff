"""
TRADING-SCOPE local OAuth mint helper (execution side). Emits OAuth scope `trading` (SCOPE_TRADE) —
the observation-side helper deliberately never does this. Run ONLY by Martyn in his own terminal:
the authorisation code is read via getpass (never echoed), exchanged ONCE in the same process, and
the token is cached at data/ctrader_token.json (git-ignored). The access/refresh tokens are never
printed, logged, or returned. Does NOT connect to the broker and NEVER constructs/sends an order.

Usage (Martyn, local):  ! python campaign_extractor/demo_executor/mint_trading_token.py
"""
from __future__ import annotations
import sys

OFFICIAL_AUTH_URL = "https://openapi.ctrader.com/apps/auth"
OFFICIAL_TOKEN_URL = "https://openapi.ctrader.com/apps/token"
REQUIRED_REDIRECT = "http://localhost/"
TRADING_SCOPE = "trading"          # SCOPE_TRADE
DEMO_ENDPOINT = "demo.ctraderapi.com:5035"


def build_auth_url(*, client_id, redirect=REQUIRED_REDIRECT, scope=TRADING_SCOPE):
    from urllib.parse import urlencode
    return OFFICIAL_AUTH_URL + "?" + urlencode(
        {"client_id": client_id, "redirect_uri": redirect, "scope": scope, "response_type": "code"})


def evaluate_config(*, client_id_present, client_secret_present, redirect, scope, token_endpoint):
    rep = {
        "client_id_present": bool(client_id_present),
        "client_secret_present": bool(client_secret_present),
        "redirect_uri_exact_http_localhost": "EXACT_MATCH" if redirect == REQUIRED_REDIRECT else "MISMATCH",
        "scope_trading": "trading (SCOPE_TRADE)" if scope == TRADING_SCOPE else f"UNEXPECTED:{scope}",
        "token_endpoint_official": token_endpoint == OFFICIAL_TOKEN_URL,
        "demo_endpoint": DEMO_ENDPOINT, "no_live_fallback": True,
    }
    rep["ready"] = (rep["client_id_present"] and rep["client_secret_present"]
                    and rep["redirect_uri_exact_http_localhost"] == "EXACT_MATCH"
                    and rep["scope_trading"].startswith("trading") and rep["token_endpoint_official"])
    return rep


def _exchange_once(code, *, client_id, client_secret, redirect_uri):
    """Single token POST, zero retry. Token NEVER printed/returned; cached only. (Run locally.)"""
    import json
    import os
    import urllib.parse
    import urllib.request
    params = {"grant_type": "authorization_code", "code": code, "redirect_uri": redirect_uri,
              "client_id": client_id, "client_secret": client_secret}
    req = urllib.request.Request(OFFICIAL_TOKEN_URL, data=urllib.parse.urlencode(params).encode(),
                                 headers={"Content-Type": "application/x-www-form-urlencoded"})
    with urllib.request.urlopen(req, timeout=30) as r:
        tok = json.loads(r.read())
    if "access_token" not in tok:
        raise RuntimeError("token exchange failed (no access_token) — details suppressed")
    tok["saved_at_utc"] = __import__("time").strftime("%Y-%m-%dT%H:%M:%SZ", __import__("time").gmtime())
    tok["scope_requested"] = TRADING_SCOPE
    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    path = os.path.join(root, "data", "ctrader_token.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(tok, f)
    return {"cached": True, "path_basename": os.path.basename(path), "token_value_exposed": False}


def main():
    import getpass
    import os
    client_id = os.environ.get("CTRADER_CLIENT_ID")
    client_secret = os.environ.get("CTRADER_CLIENT_SECRET")
    cfg = evaluate_config(client_id_present=bool(client_id), client_secret_present=bool(client_secret),
                          redirect=REQUIRED_REDIRECT, scope=TRADING_SCOPE, token_endpoint=OFFICIAL_TOKEN_URL)
    if not cfg["ready"]:
        print("STOP: config not ready ->", {k: v for k, v in cfg.items() if k != "ready"}); return 2
    print("Open this URL in your browser, authorise ONLY demo account 4257941, then paste the code below:")
    print(build_auth_url(client_id=client_id))
    code = getpass.getpass("authorisation code (not echoed): ").strip()
    if not code:
        print("STOP: no code entered."); return 2
    res = _exchange_once(code, client_id=client_id, client_secret=client_secret, redirect_uri=REQUIRED_REDIRECT)
    print("trading-scope token cached (value NOT shown):", res)
    print("Next: run the non-trading preflight. NO ORDER is sent.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
