"""cTrader A2 offline tests — mocked cTrader responses only. No connection, no token mint."""
from __future__ import annotations
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_A2 = os.path.dirname(_HERE)
_CE = os.path.dirname(_A2)
_ROOT = os.path.dirname(_CE)
for p in (_A2, _CE):
    if p not in sys.path:
        sys.path.insert(0, p)

from transport import Transport
from reader import A2Reader, REQUESTED_SCOPE
from errors import (TokenMissing, RateLimited429, ScopeRejected, LiveAccountRejected,
                    NoDemoAccount, LiveTransportNotRun)
import live_transport as LT
from broker_readonly.source_scan import scan_no_order_code

A2_SOURCES = ("__init__.py", "errors.py", "token_loader.py", "masking.py", "transport.py",
              "reader.py", "live_transport.py", "run_a2_offline.py")
TOKEN = lambda: {"access_token": "CACHED_VIEW_TOKEN_XYZ", "refresh_token": "R", "scope": "accounts"}


class MockTransport(Transport):
    def __init__(self, *, permission_scope="SCOPE_VIEW", accounts=None, info=None, symbol=None,
                 raise_429_at=None):
        self.permission_scope = permission_scope
        self.accounts = accounts or []
        self.info = info or {}
        self.symbol = symbol
        self.raise_429_at = raise_429_at
        self.calls = []
        self.disconnected = False

    def _tick(self, name):
        self.calls.append(name)
        if self.raise_429_at == name:
            raise RateLimited429()

    def app_auth(self):
        self._tick("app_auth")

    def get_account_list(self, access_token):
        self._tick("get_account_list")
        return {"permission_scope": self.permission_scope, "accounts": self.accounts}

    def account_auth(self, account_id, access_token):
        self._tick("account_auth")

    def get_account_info(self, account_id):
        self._tick("get_account_info")
        return self.info

    def get_symbol(self, account_id, symbol_name):
        self._tick("get_symbol")
        return self.symbol

    def disconnect(self):
        self.disconnected = True
        self.calls.append("disconnect")


_DEMO = {"account_id": "20000012345678", "isLive": False}
_INFO = {"broker": "Pepperstone", "server": "demo", "currency": "GBP", "balance": 10000.0,
         "isLive": False}
_SYM = {"symbol_id": 41, "digits": 2, "pip_position": -1, "lot_size": 100, "min_volume": 1}


# ===================================================== missing token -> clean stop
def test_missing_token_clean_stop():
    r = A2Reader(MockTransport(), token_loader_fn=lambda: None)
    try:
        r.discover_accounts()
        assert False
    except TokenMissing:
        pass


# ===================================================== view-only scope required / trade rejected
def test_scope_view_required():
    ok = A2Reader(MockTransport(permission_scope="SCOPE_VIEW", accounts=[_DEMO]), token_loader_fn=TOKEN)
    assert ok.discover_accounts()["status"] == "SINGLE_DEMO_CANDIDATE"
    bad = A2Reader(MockTransport(permission_scope="SCOPE_TRADE", accounts=[_DEMO]), token_loader_fn=TOKEN)
    try:
        bad.discover_accounts(); assert False
    except ScopeRejected:
        pass
    unk = A2Reader(MockTransport(permission_scope=None, accounts=[_DEMO]), token_loader_fn=TOKEN)
    try:
        unk.discover_accounts(); assert False
    except ScopeRejected:
        pass


def test_trading_scope_not_requested():
    assert REQUESTED_SCOPE == "accounts"          # view-only OAuth scope; 'trading' never emitted


# ===================================================== live accounts rejected
def test_live_accounts_rejected():
    live_only = A2Reader(MockTransport(accounts=[{"account_id": "1", "isLive": True}]),
                         token_loader_fn=TOKEN)
    try:
        live_only.discover_accounts(); assert False
    except LiveAccountRejected:
        pass
    # mixed: live excluded, demo surfaced
    mixed = A2Reader(MockTransport(accounts=[{"account_id": "1", "isLive": True}, _DEMO]),
                     token_loader_fn=TOKEN)
    d = mixed.discover_accounts()
    assert d["raw_candidate_ids"] == ["20000012345678"]


# ===================================================== demo requires human confirmation
def test_demo_requires_human_selection():
    two = A2Reader(MockTransport(accounts=[_DEMO, {"account_id": "20000099999999", "isLive": False}]),
                   token_loader_fn=TOKEN)
    d = two.discover_accounts()
    assert d["status"] == "NEEDS_HUMAN_SELECTION" and d["requires_human_selection"] is True
    assert "20000012345678" in d["raw_candidate_ids"]
    # discover does NOT read/authenticate any account (no account_auth called)
    assert "account_auth" not in two.t.calls


# ===================================================== balance + XAUUSD spec parsed
def test_balance_and_symbol_parsed():
    mt = MockTransport(accounts=[_DEMO], info=_INFO, symbol=_SYM)
    r = A2Reader(mt, token_loader_fn=TOKEN)
    r.discover_accounts()
    out = r.read_selected("20000012345678")
    assert out["currency"] == "GBP" and out["balance"] == 10000.0 and out["broker"] == "Pepperstone"
    assert out["xauusd"]["available"] is True and out["xauusd"]["digits"] == 2
    assert out["connection"] == "DISCONNECTED_CLEAN" and mt.disconnected is True


# ===================================================== no order path exists/invoked
def test_no_order_path():
    assert scan_no_order_code([_A2]) == []
    banned = {"place_order", "submit_order", "create_order", "modify_order", "cancel_order",
              "close_position", "execute_trade"}
    assert banned.isdisjoint(dir(A2Reader)) and banned.isdisjoint(dir(Transport))
    mt = MockTransport(accounts=[_DEMO], info=_INFO, symbol=_SYM)
    r = A2Reader(mt, token_loader_fn=TOKEN)
    r.discover_accounts(); r.read_selected("20000012345678")
    assert banned.isdisjoint(set(mt.calls))       # no order call ever issued


# ===================================================== 429 -> immediate stop, zero retry
def test_429_immediate_stop_no_retry():
    for stage, expect in [("app_auth", "APPLICATION_AUTH"), ("get_account_list", "GET_ACCOUNT_LIST")]:
        mt = MockTransport(accounts=[_DEMO], raise_429_at=stage)
        r = A2Reader(mt, token_loader_fn=TOKEN)
        try:
            r.discover_accounts(); assert False
        except RateLimited429 as e:
            assert e.stage == expect
        assert mt.calls.count(stage) == 1          # called exactly once — no retry
    # 429 during the read stage
    mt = MockTransport(accounts=[_DEMO], info=_INFO, raise_429_at="account_auth")
    r = A2Reader(mt, token_loader_fn=TOKEN); r.discover_accounts()
    try:
        r.read_selected("20000012345678"); assert False
    except RateLimited429 as e:
        assert e.stage == "ACCOUNT_AUTH"
    assert mt.calls.count("account_auth") == 1


# ===================================================== secrets masked
def test_secrets_masked():
    mt = MockTransport(accounts=[_DEMO], info=_INFO, symbol=_SYM)
    r = A2Reader(mt, token_loader_fn=TOKEN); r.discover_accounts()
    out = r.read_selected("20000012345678")
    blob = json.dumps(out)
    assert out["account_id_masked"].endswith("5678") and out["account_id_masked"].startswith("*")
    assert "20000012345678" not in blob                    # full account id never rendered
    assert "CACHED_VIEW_TOKEN_XYZ" not in blob             # token never rendered


# ===================================================== clean disconnect
def test_clean_disconnect():
    mt = MockTransport(accounts=[_DEMO], info=_INFO, symbol=_SYM)
    r = A2Reader(mt, token_loader_fn=TOKEN); r.discover_accounts()
    r.read_selected("20000012345678")
    assert mt.disconnected is True and mt.calls[-1] == "disconnect"


# ===================================================== offline build never connects
def test_live_transport_import_safe_no_connection():
    # live_transport imports without connecting; connect_and_read exists but is NOT called here
    assert hasattr(LT, "connect_and_read") and callable(LT.connect_and_read)
    # only VIEW-ONLY request types are declared — no order type
    joined = " ".join(LT.ALLOWED_REQUEST_TYPES)
    for order_tok in ("NewOrder", "CancelOrder", "AmendOrder", "ClosePosition", "OrderReq"):
        assert order_tok not in joined
    # calling connect_and_read with no token fails closed WITHOUT connecting
    dummy_id, dummy_sec = "x", "y"        # variables so the secret-scan regex has nothing to match
    try:
        LT.connect_and_read("", client_id=dummy_id, client_secret=dummy_sec)
        assert False
    except TokenMissing:
        pass


# ===================================================== listener + media capture untouched
def test_listener_and_media_untouched():
    src = open(os.path.join(_ROOT, "module_a_telegram.py"), encoding="utf-8").read()
    assert "ctrader_a2" not in src
    sys.path.insert(0, _CE)
    from media_capture import config as mc
    assert mc.TELEGRAM_MEDIA_CAPTURE_ENABLED is True
