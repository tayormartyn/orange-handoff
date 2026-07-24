"""Phase-1 essential tests for READ_ONLY_CTRADER_PREFLIGHT_v0_1, incl. the Phase-2
token-acquisition path (step 1) proven zero-connect. No OAuth, no socket, no connect.
Run: python research/farouk_pilot/read_only_ctrader_preflight/tests_preflight.py
"""
import inspect
import json
import os
import socket
import sys
import tempfile

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

# Isolate all on-disk state (allowlist pin, DPAPI blobs) to a throwaway dir OUTSIDE the repo.
os.environ["ORANGE_PREFLIGHT_STORE_DIR"] = tempfile.mkdtemp(prefix="orange_preflight_test_")

from research.farouk_pilot.read_only_ctrader_preflight import (          # noqa: E402
    config, guard, credentials, allowlist, oauth, read_ops, transport, preflight,
    loopback_exchange)

_DIR = os.path.dirname(os.path.abspath(__file__))

# The importable RUNTIME tool (what the executor-isolation + absence claims are about).
# scan_executor_network.py and tests are dev tooling and legitimately name demo_lane/network
# tokens, so they are excluded from the runtime source scans.
_RUNTIME = ("__init__.py", "config.py", "guard.py", "credentials.py", "allowlist.py",
            "oauth.py", "read_ops.py", "transport.py", "preflight.py", "loopback_exchange.py")


def pkg_src():
    return "\n".join(open(os.path.join(_DIR, fn), encoding="utf-8").read() for fn in _RUNTIME)


SRC = pkg_src()
_p = _f = 0
def check(name, cond):
    global _p, _f
    print(("  ok  " if cond else "FAIL  ") + name)
    _p += bool(cond); _f += (not cond)


def _raises(thunk, exc):
    try:
        thunk(); return False
    except exc:
        return True


def acct(**over):
    a = {"endpoint": "demo.ctraderapi.com", "port": 5035, "granted_scope": "SCOPE_VIEW",
         "isLive": False, "ctidTraderAccountId": 1_000_001, "environment": "PEPPERSTONE_DEMO",
         "xauusd_symbol_count": 1}
    a.update(over)
    return a


# 1. fixed DEMO destination
check("fixed demo destination host:port", config.DEMO_HOST == "demo.ctraderapi.com" and config.DEMO_PORT == 5035)
check("no live host anywhere in package source", "live.ctraderapi.com" not in SRC)

# 2. view-only scope required; trading never emitted
check("emit scope is 'accounts' (view-only)", config.OAUTH_EMIT_SCOPE == "accounts")
check("required granted scope SCOPE_VIEW", config.REQUIRED_GRANTED_SCOPE == "SCOPE_VIEW")

# ---- GUARD 3 (allowlist): starts UNPINNED and REFUSES until the real id is pinned ----
allowlist.clear_pin()
check("allowlist starts UNPINNED", allowlist.is_pinned() is False and allowlist.pinned_ctid() is None)
_u = guard.assess(acct())
check("UNPINNED allowlist REFUSES an otherwise-perfect account", _u["ok"] is False)
check("...and it is specifically the account field that fails (all others pass)",
      _u["fields"]["account_allowlisted"]["ok"] is False
      and all(_u["fields"][k]["ok"] for k in _u["fields"] if k != "account_allowlisted"))
try:
    guard.require_or_exit(acct()); check("require_or_exit refuses while UNPINNED", False)
except guard.PreflightRefusal:
    check("require_or_exit refuses while UNPINNED", True)
# pin the id the (hypothetical) first account-list read returned, then it can match
allowlist.pin_ctid(1_000_001)
check("after pin, allowlist is pinned", allowlist.is_pinned() is True)
check("pin refuses SILENT overwrite with a different id",
      _raises(lambda: allowlist.pin_ctid(999999), ValueError))
check("pinned store lives OUTSIDE the repo", allowlist.store_is_outside_repo(_REPO_ROOT))

# now the scope/account guard behaves as before, against the pinned id
check("guard rejects SCOPE_TRADE grant", guard.assess(acct(granted_scope="SCOPE_TRADE"))["ok"] is False)
check("good view-only PINNED account passes", guard.assess(acct())["ok"] is True)

# 3. live-account rejection
check("isLive=True rejected", guard.assess(acct(isLive=True))["ok"] is False)

# 4. wrong-account rejection (pinned id != observed id)
check("wrong account id rejected", guard.assess(acct(ctidTraderAccountId=42))["ok"] is False)

# extra fail-closed fields
check("wrong endpoint rejected", guard.assess(acct(endpoint="live.ctraderapi.com"))["ok"] is False)
check("wrong port rejected", guard.assess(acct(port=443))["ok"] is False)
check("wrong environment rejected", guard.assess(acct(environment="OTHER"))["ok"] is False)
check("ambiguous XAUUSD (count!=1) rejected", guard.assess(acct(xauusd_symbol_count=2))["ok"] is False)

# fail-closed RAISES (-> non-zero exit) on failure and on a trade grant
try:
    guard.require_or_exit(acct(granted_scope="SCOPE_TRADE")); check("require_or_exit refuses SCOPE_TRADE", False)
except guard.PreflightRefusal as e:
    check("require_or_exit refuses SCOPE_TRADE", "SCOPE_TRADE" in str(e))
try:
    guard.require_or_exit(acct(isLive=True)); check("require_or_exit refuses isLive True", False)
except guard.PreflightRefusal:
    check("require_or_exit refuses isLive True", True)
check("require_or_exit passes a good account", guard.require_or_exit(acct())["ok"] is True)

# ---- GUARD 1: incapable of requesting anything but scope=accounts (hardcoded, not a param) ----
check("build_authorize_url has NO 'scope' parameter",
      "scope" not in inspect.signature(oauth.build_authorize_url).parameters)
_url = oauth.build_authorize_url("CLIENT-ID-ABC")
check("authorize URL emits scope=accounts", "scope=accounts" in _url)
check("authorize URL never contains 'trading'", "trading" not in _url.lower())
check("no 'scope=trading' literal anywhere in package source", "scope=trading" not in SRC)
check("no OAuth builder accepts a scope/permission kwarg",
      not any("scope" in inspect.signature(fn).parameters
              for fn in (oauth.build_authorize_url,)))

# ---- GUARD 2: secret/token never hits stdout/logs/args/chat; DPAPI only; redaction ----
_tok = {"accessToken": "AAAA-BBBB-CCCC-WXYZ", "refreshToken": "SECRET-REFRESH", "scope": "accounts", "expiresIn": 2628000}
_red = credentials.redact_token(_tok)
check("redact_token exposes only last4 + scope (no token body)",
      _red["access_token_last4"] == "WXYZ" and _red["granted_scope"] == "accounts"
      and "AAAA-BBBB-CCCC-WXYZ" not in json.dumps(_red) and "SECRET-REFRESH" not in json.dumps(_red))
credentials.store_token(_tok)                       # DPAPI round-trip (blob outside repo)
check("token DPAPI round-trips (stored/loaded equal)", credentials.load_token() == _tok)
check("token blob path is OUTSIDE the repo", credentials.store_is_outside_repo(_REPO_ROOT))
check("no token/secret is ever printed in package source",
      not any(x in SRC for x in ("print(token", "print(client_secret", "print(access_token",
                                 "print(creds", "print(self._client")))

# DEFECT FIX: an error/empty token-endpoint body must RAISE and store NOTHING (never "stored").
if os.path.exists(credentials.token_blob_path()):
    os.remove(credentials.token_blob_path())
check("error body (errorCode) RAISES ExchangeFailed",
      _raises(lambda: oauth._finalize_token({"errorCode": "ACCESS_DENIED", "description": "x"}), oauth.ExchangeFailed))
check("...and an error body stores NOTHING (no token blob written)", credentials.load_token() is None)
check("empty body (no access token) RAISES ExchangeFailed",
      _raises(lambda: oauth._finalize_token({"tokenType": "bearer"}), oauth.ExchangeFailed))
check("non-dict body RAISES ExchangeFailed", _raises(lambda: oauth._finalize_token("nope"), oauth.ExchangeFailed))
_good = oauth._finalize_token({"accessToken": "tok-WXYZ", "scope": "accounts", "expiresIn": 100})
check("USABLE token is stored + redacted (last4 only)",
      _good["access_token_last4"] == "WXYZ" and _good["granted_scope"] == "accounts"
      and credentials.load_token() is not None)
if os.path.exists(credentials.token_blob_path()):
    os.remove(credentials.token_blob_path())

# ---- GUARD 4: no network capability added; zero-connect (offline import, no socket) ----
check("no ctrader_open_api imported at package import time", "ctrader_open_api" not in sys.modules)
check("ctrader_open_api imports are all LAZILY indented (never module-level)",
      all(line != line.lstrip() for line in SRC.splitlines()
          if line.lstrip().startswith(("import ctrader_open_api", "from ctrader_open_api"))))
check("ssl/socket imports are all LAZILY indented (never module-level)",
      all(line != line.lstrip() for line in SRC.splitlines()
          if line.lstrip().startswith(("import ssl", "import socket", "from ssl", "from socket"))))
check("urllib (network) imports are all LAZILY indented (never module-level)",
      all(line != line.lstrip() for line in SRC.splitlines()
          if line.lstrip().startswith(("import urllib", "from urllib"))))
check("http.server/webbrowser imports are all LAZILY indented (never module-level)",
      all(line != line.lstrip() for line in SRC.splitlines()
          if line.lstrip().startswith(("import http", "from http", "import webbrowser", "from webbrowser"))))
check("no http.server/webbrowser imported at package import time",
      "http.server" not in sys.modules and "webbrowser" not in sys.modules)

# ---- LOOPBACK exchange: pure capture parse, opt-in gate, and a real local capture selftest ----
check("loopback _parse_code_from_path extracts code from a redirect URL",
      loopback_exchange._parse_code_from_path("/?code=ABC123&state=x") == {"code": "ABC123"})
check("loopback _parse_code_from_path surfaces an error redirect",
      loopback_exchange._parse_code_from_path("/?error=access_denied") == {"error": "access_denied"})
check("loopback run() REFUSES without opt-in (binds nothing, no network)",
      loopback_exchange.run() == 2)
check("loopback capture SELFTEST passes (code captured via local redirect; no broker/OAuth)",
      loopback_exchange.selftest() == 0)
# the token exchange refuses (no network) unless Phase-2 opted in
check("connect opt-in is OFF by default (Phase 1)", config.PHASE2_CONNECT_OPT_IN is False)
check("exchange_code_for_token REFUSES without opt-in (no network attempted)",
      _raises(lambda: oauth.exchange_code_for_token("any-code"), oauth.OAuthNotAuthorised))
check("transport.connect REFUSES without opt-in", _raises(lambda: transport.ViewOnlyTransport().connect(), transport.NotConnected))
# HARD PROOF: exercise the whole Phase-1 surface with socket.socket booby-trapped to raise.
_real_socket = socket.socket
def _no_socket(*a, **k):
    raise AssertionError("Phase 1 opened a socket!")
socket.socket = _no_socket
try:
    preflight.static_report(acct())
    oauth.build_authorize_url("X")
    credentials.redact_token(_tok); credentials.redact_account("1234567890")
    guard.assess(acct()); allowlist.pinned_ctid()
    check("Phase-1 surface opens NO socket (socket.socket booby-trapped)", True)
except AssertionError:
    check("Phase-1 surface opens NO socket (socket.socket booby-trapped)", False)
finally:
    socket.socket = _real_socket

# 5. trade-message imports ABSENT
for t in ("ProtoOANewOrderReq", "ProtoOAClosePositionReq", "ProtoOACancelOrderReq",
          "ProtoOAAmendOrderReq", "ProtoOAAmendPositionSLTPReq", "NewOrderReq", "ClosePositionReq"):
    check(f"trade message absent: {t}", t not in SRC)

# 6. arbitrary-send path ABSENT
tsrc = open(os.path.join(_DIR, "transport.py"), encoding="utf-8").read()
check("no public send/write/dispatch/execute method on transport",
      not any(f"def {m}(" in tsrc for m in ("send", "write", "dispatch", "execute", "raw_send", "send_message")))
check("no raw-payload (SerializeToString / bytes) send path", "SerializeToString" not in SRC)
class _Fake: pass
_Fake.__name__ = "ProtoOANewOrderReq"
try:
    transport.ViewOnlyTransport()._send_whitelisted(_Fake())
    check("whitelist rejects a non-read message", False)
except transport.ArbitrarySendRefused:
    check("whitelist rejects a non-read message", True)
except transport.NotConnected:
    check("whitelist rejects a non-read message", False)   # must fail at the NAME check, before connect
check("all 7 whitelisted messages are read-only names",
      all(not any(k in m for k in ("Order", "Position", "Close", "Cancel", "Amend")) for m in read_ops.ALLOWED_READ_MESSAGES))

# 7. credential redaction + no secrets in source
red = credentials.redact_account("1234567890")
check("account redacted to hash+last4", red["last4"] == "7890" and len(red["sha256"]) == 64 and red["redacted"])
check("credential blob store OUTSIDE the repo", credentials.store_is_outside_repo(_REPO_ROOT))
check("no hardcoded secret value in package",
      not any(x in SRC for x in ('clientSecret = "', 'accessToken = "', 'password = "', 'client_secret = "')))

# 8. no ledger or live-service writes; no import of live services / demo_lane / campaign pipeline
for forbidden in ("forward_validation_ledger", "router_freeze", "prospective_evidence",
                  "module_a_telegram", "live_wire", "evidence_watcher", "intake_observer",
                  "outcome_companion", "tracker", "demo_lane", "paper_log", "dataset_pipeline"):
    check(f"no reference to live/ledger target: {forbidden}", forbidden not in SRC)

# static report renders Phase 1 + fixed authority + guard + redaction + allowlist state
rep = preflight.static_report(acct())
check("static report: phase 1, demo authority, no live path",
      rep["phase"] == "1_STATIC" and rep["authority"]["host"] == "demo.ctraderapi.com"
      and rep["authority"]["port"] == 5035 and rep["authority"]["live_path_exists"] is False)
check("static report: guard ok + account redacted + allowlist shown",
      rep["guard"]["ok"] is True and rep["account_redacted"]["redacted"] and rep["allowlist"]["pinned"] is True)

allowlist.clear_pin()   # leave no pinned state behind
print(f"\n{_p} passed, {_f} failed")
sys.exit(1 if _f else 0)
