"""Offline tests for the deterministic token-mint helper. No network, no code, no getpass."""
from __future__ import annotations
import json
import os
import shutil
import sys
import tempfile

_HERE = os.path.dirname(os.path.abspath(__file__))
_A2 = os.path.dirname(_HERE)
_CE = os.path.dirname(_A2)
_ROOT = os.path.dirname(_CE)
for p in (_A2, _CE, _ROOT):
    if p not in sys.path:
        sys.path.insert(0, p)

import mint_token as M

GOOD = dict(client_id_present=True, client_secret_present=True, redirect="http://localhost/",
            scope="accounts", token_endpoint="https://openapi.ctrader.com/apps/token")


def test_evaluate_config_good():
    rep, ok = M.evaluate_config(**GOOD)
    assert ok is True
    assert rep["redirect_uri_exact_http_localhost"] == "EXACT_MATCH"
    assert rep["scope_view_only"].startswith("accounts")
    assert rep["token_endpoint_official"] == "OK"


def test_evaluate_config_failures():
    assert M.evaluate_config(**{**GOOD, "redirect": "http://localhost"})[1] is False       # no slash
    assert M.evaluate_config(**{**GOOD, "redirect": "https://localhost/"})[1] is False       # https
    assert M.evaluate_config(**{**GOOD, "scope": "trading"})[1] is False                      # trade
    assert M.evaluate_config(**{**GOOD, "client_secret_present": False})[1] is False          # missing
    assert M.evaluate_config(**{**GOOD, "token_endpoint": "https://evil/token"})[1] is False  # endpoint


def test_parse_token_response():
    ok, tok, err = M.parse_token_response(200, json.dumps({"accessToken": "AAA", "refreshToken": "R",
                                                           "expiresIn": 2628000}))
    assert ok is True and tok["access_token"] == "AAA" and tok["refresh_token"] == "R" and err is None
    ok, tok, err = M.parse_token_response(200, json.dumps({"errorCode": "ACCESS_DENIED"}))
    assert ok is False and tok is None and err == "ACCESS_DENIED"
    ok, tok, err = M.parse_token_response(429, "")
    assert ok is False and err == "HTTP_429"
    ok, tok, err = M.parse_token_response(400, "not-json")
    assert ok is False and err == "HTTP_400"


def test_save_token_roundtrip():
    tmp = tempfile.mkdtemp(prefix="mint_")
    try:
        p = os.path.join(tmp, "data", "ctrader_token.json")
        M.save_token({"access_token": "AAA", "refresh_token": "R"}, path=p)
        d = json.load(open(p))
        assert d["access_token"] == "AAA" and d["refresh_token"] == "R" and d.get("saved_at_utc")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_official_endpoint_and_redirect_constants():
    assert M.OFFICIAL_TOKEN_URL == "https://openapi.ctrader.com/apps/token"
    assert M.REQUIRED_REDIRECT == "http://localhost/"
    assert M.TOKEN_FILE.endswith(os.path.join("data", "ctrader_token.json"))


def test_code_not_retained_structurally():
    src = open(os.path.join(_A2, "mint_token.py"), encoding="utf-8").read()
    assert "del code" in src                       # code discarded after exchange
    assert "getpass" in src                          # code read without echo
    # parse_token_response never receives the code
    import inspect
    assert "code" not in inspect.signature(M.parse_token_response).parameters
    # the code is never printed/logged
    for bad in ("print(code", "log(code", "print(f\"{code", "print(params"):
        assert bad not in src
