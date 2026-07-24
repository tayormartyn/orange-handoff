"""
Brick 3A — cTrader OAuth scope reconciliation. Offline, no network, no OAuth, no creds.

internal 'view' -> OAuth 'accounts'; OAuth 'trading' is never generated; returned
SCOPE_VIEW accepted; SCOPE_TRADE / unknown / absent rejected; invalid internal rejected.
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))        # campaign_extractor
PARENT = os.path.dirname(ROOT)                                            # signal-terminal
sys.path.insert(0, ROOT)
sys.path.insert(0, PARENT)

from broker_readonly.oauth_scope import (
    oauth_scope_for, assert_returned_scope_admissible, ScopeError,
    OAUTH_ACCOUNTS, OAUTH_TRADING, INTERNAL_VIEW,
)
from broker_readonly.source_scan import scan_no_order_code, scan_secret_leaks
from broker_readonly.adapter import CTraderDemoReadOnlyAdapter
import broker_readonly.config as cfg

PKG = os.path.join(ROOT, "broker_readonly")


# ---- internal -> OAuth mapping
def test_internal_view_maps_to_accounts():
    assert oauth_scope_for(INTERNAL_VIEW) == OAUTH_ACCOUNTS == "accounts"


def test_internal_setting_is_view():
    assert cfg.CTRADER_SCOPE == "view"            # internal safety setting preserved


def test_oauth_trading_never_generated():
    # over any input, the mapper returns 'accounts' or raises — never 'trading'
    for s in ["view", "trading", "accounts", "SCOPE_TRADE", "", None, "VIEW", "Trading"]:
        try:
            out = oauth_scope_for(s)
            assert out == OAUTH_ACCOUNTS
            assert out != OAUTH_TRADING
        except ScopeError:
            pass


def test_internal_trading_rejected():
    for s in ["trading", "trade", "TRADING"]:
        try:
            oauth_scope_for(s); assert False
        except ScopeError:
            pass


def test_invalid_internal_scope_rejected():
    for s in ["", None, "accounts", "full", "view ", "read"]:
        try:
            oauth_scope_for(s); assert False
        except ScopeError:
            pass


# ---- returned permission validation
def test_returned_scope_view_accepted():
    assert assert_returned_scope_admissible("SCOPE_VIEW") is True


def test_returned_scope_trade_rejected():
    try:
        assert_returned_scope_admissible("SCOPE_TRADE"); assert False
    except ScopeError:
        pass


def test_returned_unknown_scope_rejected():
    for r in ["SCOPE_FULL", "VIEW", "trade", "scope_view"]:
        try:
            assert_returned_scope_admissible(r); assert False
        except ScopeError:
            pass


def test_returned_absent_scope_rejected():
    for r in [None, ""]:
        try:
            assert_returned_scope_admissible(r); assert False
        except ScopeError:
            pass


# ---- corrected config + runtime path never emits trading
def test_config_default_scope_corrected_to_accounts():
    import ctrader_config as legacy
    assert legacy.DEFAULT_SCOPE == "accounts"      # stale 'trading' corrected


def test_build_auth_url_emits_accounts_not_trading():
    import ctrader_auth as auth
    url = auth.build_auth_url(client_id="TEST_PLACEHOLDER_CID")
    assert "scope=accounts" in url
    assert "trading" not in url


def test_build_auth_url_refuses_trading_scope():
    import ctrader_auth as auth
    try:
        auth.build_auth_url(scope="trading", client_id="TEST_PLACEHOLDER_CID"); assert False
    except RuntimeError as e:
        assert "trading" in str(e).lower()


def test_real_adapter_connect_resolves_view_scope_offline():
    a = CTraderDemoReadOnlyAdapter()
    assert a.connect() == "CREDENTIALS_MISSING"    # view->accounts resolved, no network


# ---- scans remain green for the new package (not loosened)
def test_no_order_code_scan_still_green():
    assert scan_no_order_code([PKG]) == []


def test_secret_leak_scan_green_for_new_package():
    assert scan_secret_leaks([PKG]) == []
