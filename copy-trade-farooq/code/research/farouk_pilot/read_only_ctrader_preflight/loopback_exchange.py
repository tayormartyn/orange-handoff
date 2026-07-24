"""Loopback-listener Phase-2 token exchange (OAuth loopback, RFC 8252 style). ONE command:
the operator runs it and clicks Allow; the code is captured automatically - no copy, no paste,
no getpass, no timing race.

Flow (run()):
  1. Requires ORANGE_PREFLIGHT_CONNECT=1 (session-only opt-in; read at import). Refuses otherwise
     and binds nothing.
  2. Binds a tiny local HTTP listener on the registered localhost redirect (host+port parsed from
     config.OAUTH_REDIRECT_URI), opens the scope=accounts authorize URL in the browser, waits.
  3. The browser's redirect to localhost hits the listener, which CAPTURES ?code= automatically,
     then the listener stops.
  4. The captured code is exchanged for a VIEW-ONLY token via oauth.exchange_code_for_token,
     which stores ONLY on success and RAISES on any error/empty body (the [TOKEN STORED]-on-
     failure defect is fixed in oauth._finalize_token).
  5. Prints ONLY the redacted summary. If the granted scope looks like trading -> [STOP], and any
     stored token is removed. The code, secret and token are NEVER printed or logged (the HTTP
     handler's request logging is silenced so the ?code= never reaches the console).

All network/browser modules (http.server, webbrowser, urllib in oauth) are imported LAZILY inside
run()/selftest, so this module imports offline and connects nothing until invoked.
"""
import sys

from . import config, credentials, oauth


def _parse_code_from_path(path):
    """Pure: extract {'code': ...} and/or {'error': ...} from a redirect path query string."""
    from urllib.parse import urlparse, parse_qs
    q = parse_qs(urlparse(path).query)
    out = {}
    if q.get("code"):
        out["code"] = q["code"][0]
    if q.get("error"):
        out["error"] = q["error"][0]
    return out


def _make_handler(captured):
    import http.server

    class _H(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            captured.update(_parse_code_from_path(self.path))
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(b"<html><body style='font-family:sans-serif'>"
                             b"<h3>Received - you can close this tab and return to the terminal.</h3>"
                             b"</body></html>")

        def log_message(self, *args):
            pass   # SILENCED: the request line contains ?code= and must never be logged
    return _H


def _bind(bind_host, port):
    import http.server
    captured = {}
    server = http.server.HTTPServer((bind_host, port), _make_handler(captured))
    return server, captured


def run():
    if not config.PHASE2_CONNECT_OPT_IN:
        print("[BLOCKED] ORANGE_PREFLIGHT_CONNECT is not '1' in this window; nothing bound, no network.")
        print('          Set it for THIS step only, then re-run:')
        print('            $env:ORANGE_PREFLIGHT_CONNECT = "1"')
        return 2
    creds = credentials.load_credentials()
    if creds is None:
        print("[BLOCKED] no stored client credentials; run store_secret first.")
        return 2
    client_id, _secret = creds

    import time
    import webbrowser
    from urllib.parse import urlparse
    pu = urlparse(config.OAUTH_REDIRECT_URI)
    port = pu.port or (80 if (pu.scheme or "http") == "http" else 443)
    bind_host = "127.0.0.1"                     # loopback only

    try:
        server, captured = _bind(bind_host, port)
    except OSError as e:
        print(f"[BIND-FAILED] could not bind {bind_host}:{port} ({e.__class__.__name__}: {e}).")
        print("  On Windows port 80 is often reserved by http.sys/System and needs no admin but")
        print("  is already held. CLEANEST FIX: register a high-port redirect on the cTrader app,")
        print("  e.g.  http://localhost:8123/  , then in THIS window set it and re-run:")
        print('        $env:ORANGE_PREFLIGHT_REDIRECT_URI = "http://localhost:8123/"')
        return 5

    auth_url = oauth.build_authorize_url(client_id)
    print(f"Listening on http://{('localhost' if pu.hostname in (None,'localhost') else pu.hostname)}:{port}/ for the redirect.")
    print("Opening the consent page in your browser - click ALLOW (account information / view-only).")
    print("If it does not open automatically, paste this URL into your browser:")
    print("  " + auth_url)
    try:
        webbrowser.open(auth_url)
    except Exception:
        pass

    server.timeout = 1
    deadline = time.time() + 300           # 5 min; single-use code is captured the instant you click
    try:
        while not captured and time.time() < deadline:
            server.handle_request()
    finally:
        server.server_close()

    if captured.get("error"):
        print(f"\n[FAILED] the grant returned an error (error={captured['error']}); nothing stored.")
        return 4
    code = captured.get("code")
    if not code:
        print("\n[FAILED] timed out with no code captured; nothing stored. Re-run and click Allow.")
        return 4

    try:
        summary = oauth.exchange_code_for_token(code)     # stores ONLY on a usable token; else raises
    except oauth.ExchangeFailed as e:
        print(f"\n[FAILED] token exchange rejected; NOTHING stored. Reason: {e}")
        print("         Verify the client_id/secret are a matched pair and the redirect_uri matches.")
        return 4

    scope = str(summary.get("granted_scope") or "")
    if "trad" in scope.lower():
        # never keep a trading token
        import os
        tp = credentials.token_blob_path()
        if os.path.exists(tp):
            os.remove(tp)
        print(f"\n[STOP] granted scope looks like TRADING ({scope}); token DELETED, nothing kept.")
        print("       Revoke the grant and re-grant 'accounts' (view-only) only.")
        return 3

    print("\n[TOKEN STORED] encrypted via DPAPI outside the repo. Redacted summary:")
    print(f"  granted_scope      : {summary.get('granted_scope')}")
    print(f"  expires_in         : {summary.get('expires_in')}")
    print(f"  access_token_last4 : {summary.get('access_token_last4')}")
    print("  (neither the code nor the token is printed)")
    print("\nNOTE: cTrader's token response does not carry the OAuth scope, so 'granted_scope' above")
    print("      is the token TYPE, not proof of view-only. View-only is DEFINITIVELY enforced at")
    print("      the next step (the account read: isLive==false + fail-closed guard). The authorize")
    print("      request used scope=accounts (hardcoded; there is no trading-scope path).")
    return 0


def selftest():
    """Prove the loopback capture works with NO broker and NO OAuth: bind an ephemeral local port,
    fire a simulated redirect at it, and confirm the code is captured. Local 127.0.0.1 only."""
    import threading
    import time
    from urllib.request import urlopen
    server, captured = _bind("127.0.0.1", 0)
    port = server.server_address[1]

    def _hit():
        time.sleep(0.2)
        try:
            urlopen(f"http://127.0.0.1:{port}/?code=SELFTEST123&state=x", timeout=5).read()
        except Exception:
            pass

    t = threading.Thread(target=_hit, daemon=True)
    t.start()
    server.timeout = 1
    deadline = time.time() + 10
    while not captured and time.time() < deadline:
        server.handle_request()
    server.server_close()
    ok = captured.get("code") == "SELFTEST123"
    print("loopback capture selftest:", "PASS" if ok else "FAIL",
          "- captured code via a local redirect (no broker, no OAuth, no token)")
    return 0 if ok else 1


def main(argv=None):
    argv = argv if argv is not None else sys.argv[1:]
    if "--selftest" in argv:
        return selftest()
    return run()


if __name__ == "__main__":
    sys.exit(main())
