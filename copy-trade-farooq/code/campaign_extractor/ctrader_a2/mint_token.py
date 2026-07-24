"""
Deterministic ONE-SHOT local token-mint helper (view-only). Run by Martyn in his terminal.

The authorisation code is read from a WAITING prompt (getpass — not echoed) and exchanged
IMMEDIATELY in the same process — no LLM round-trip, so the ~60s code window is not consumed.
The code is never printed, logged, or retained beyond the single exchange. Exactly ONE token
POST, zero retry. On HTTP 429 / ACCESS_DENIED / any failure -> stop with a sanitised line
(HTTP status, error code, elapsed ms). Caches the token at PROJECT_ROOT/data/ctrader_token.json.
Does NOT connect to the broker.
"""
from __future__ import annotations
import getpass
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

_HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(_HERE))
sys.path.insert(0, os.path.join(PROJECT_ROOT, "campaign_extractor"))
sys.path.insert(0, PROJECT_ROOT)

OFFICIAL_TOKEN_URL = "https://openapi.ctrader.com/apps/token"
REQUIRED_REDIRECT = "http://localhost/"
TOKEN_FILE = os.path.join(PROJECT_ROOT, "data", "ctrader_token.json")


def load_env():
    from ctrader_a1 import dotenv_loader as DL
    env = DL.load_ctrader_env()
    DL.apply_to_environ(env)
    return env


def evaluate_config(*, client_id_present, client_secret_present, redirect, scope, token_endpoint):
    """Pure masked verification. Returns (report_dict, all_ok). No values revealed."""
    rep = {
        "client_id": "PRESENT" if client_id_present else "MISSING",
        "client_secret": "PRESENT" if client_secret_present else "MISSING",
        "redirect_uri_exact_http_localhost": "EXACT_MATCH" if redirect == REQUIRED_REDIRECT
        else "MISMATCH",
        "scope_view_only": "accounts (view-only)" if scope == "accounts" else f"UNEXPECTED:{scope}",
        "token_endpoint_official": "OK" if token_endpoint == OFFICIAL_TOKEN_URL else "MISMATCH",
    }
    ok = (rep["client_id"] == "PRESENT" and rep["client_secret"] == "PRESENT"
          and rep["redirect_uri_exact_http_localhost"] == "EXACT_MATCH"
          and rep["scope_view_only"].startswith("accounts")
          and rep["token_endpoint_official"] == "OK")
    return rep, ok


def verify_config(env):
    import ctrader_config as cfg
    from broker_readonly.oauth_scope import oauth_scope_for
    return evaluate_config(
        client_id_present=bool(env.get("CTRADER_CLIENT_ID")),
        client_secret_present=bool(env.get("CTRADER_CLIENT_SECRET")),
        redirect=cfg.DEFAULT_REDIRECT_URI,
        scope=oauth_scope_for("view"),                    # 'accounts'; 'trading' never emitted
        token_endpoint=cfg.OAUTH_TOKEN_URL)


def parse_token_response(status_code, body_text):
    """Return (ok, token_dict_or_None, error_code_str). Deterministic; never sees the code."""
    try:
        data = json.loads(body_text) if body_text else {}
    except ValueError:
        data = {}
    access = data.get("accessToken") or data.get("access_token")
    err = data.get("errorCode") or data.get("error") or data.get("description")
    if status_code == 200 and access:
        return True, {
            "access_token": access,
            "refresh_token": data.get("refreshToken") or data.get("refresh_token"),
            "expires_in": data.get("expiresIn") or data.get("expires_in"),
            "token_type": data.get("tokenType") or data.get("token_type"),
        }, None
    return False, None, str(err or f"HTTP_{status_code}")


def save_token(tok, path=None):
    path = path or TOKEN_FILE
    os.makedirs(os.path.dirname(path), exist_ok=True)
    payload = dict(tok)
    payload["saved_at_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass
    return path


def _exchange_once(code, *, client_id, client_secret, redirect_uri):
    """ONE POST to the official token endpoint. Returns (status_code, body_text, elapsed_ms).
    The code is used here and nowhere else; it is never printed or stored."""
    params = {"grant_type": "authorization_code", "code": code, "redirect_uri": redirect_uri,
              "client_id": client_id, "client_secret": client_secret}
    body = urllib.parse.urlencode(params).encode("utf-8")
    req = urllib.request.Request(OFFICIAL_TOKEN_URL, data=body,
                                 headers={"Content-Type": "application/x-www-form-urlencoded",
                                          "Accept": "application/json"})
    t0 = time.monotonic()
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, r.read().decode("utf-8"), int((time.monotonic() - t0) * 1000)
    except urllib.error.HTTPError as e:
        txt = e.read().decode("utf-8") if e.fp else ""
        return e.code, txt, int((time.monotonic() - t0) * 1000)


def main():
    env = load_env()
    rep, ok = verify_config(env)
    print("=== A2 token mint — masked config verification ===")
    for k, v in rep.items():
        print(f"  {k:38} {v}")
    if not ok:
        print("STOP: configuration verification failed (see above).")
        return 2

    import ctrader_auth
    url = ctrader_auth.build_auth_url()                   # exactly one fresh view-only URL
    with open(os.path.join(PROJECT_ROOT, "data", "ctrader_auth_url.txt"), "w",
              encoding="utf-8") as f:
        f.write(url + "\n")
    try:
        import webbrowser
        webbrowser.open(url)
        print("Opened the authorisation URL in your browser (also saved to "
              "data\\ctrader_auth_url.txt).")
    except Exception:
        print("Auth URL saved to data\\ctrader_auth_url.txt — open it in your browser.")

    print("\nAuthorise in the browser (accounts / view-only), then paste the fresh code below.")
    print("The code is NOT echoed and is exchanged the instant you press Enter.\n")
    code = getpass.getpass("Paste fresh authorisation code: ").strip()
    if not code:
        print("STOP: no code entered.")
        return 2

    import ctrader_config as cfg
    status_code, body, elapsed_ms = _exchange_once(
        code, client_id=cfg.client_id(), client_secret=cfg.client_secret(),
        redirect_uri=cfg.DEFAULT_REDIRECT_URI)
    del code                                              # never retained beyond exchange
    ok, tok, err = parse_token_response(status_code, body)
    if ok:
        save_token(tok)
        del tok
        cached = os.path.exists(TOKEN_FILE)
        print("TOKEN CACHED SUCCESSFULLY" if cached else
              f"STOP: exchange OK but token not written (HTTP {status_code}, {elapsed_ms}ms)")
        return 0 if cached else 1
    print(f"STOP: token exchange failed — HTTP {status_code}, errorCode={err}, "
          f"elapsed={elapsed_ms}ms (zero retry)")
    return 1


if __name__ == "__main__":
    sys.exit(main())
