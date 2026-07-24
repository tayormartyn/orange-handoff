"""
Brick 3 — offline tests for the read-only cTrader adapter. No network, no credentials,
no Telegram activation. Covers the full required test list + source scans + determinism.
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import broker_readonly.config as cfg
from broker_readonly.states import ConnectionStateMachine, InvalidTransition
from broker_readonly.quotes import QuoteContext, RawQuote, classify
from broker_readonly.secrets import safe_record, safe_correlation_hash, SecretLeak, is_secret_key
from broker_readonly.source_scan import scan_no_order_code, scan_secret_leaks
from broker_readonly.adapter import (
    MockCTraderReadOnlyAdapter, ReplayCTraderQuoteAdapter, CTraderDemoReadOnlyAdapter,
    BrokerReadOnlyAdapter, BrokerSafetyError, SymbolError, assert_demo_safety,
)

PKG = os.path.join(ROOT, "broker_readonly")


def _clock():
    n = {"i": 0}

    def c():
        n["i"] += 1
        return f"T{n['i']:04d}"
    return c


def demo_scenario(**over):
    s = dict(app_approved=True, credentials=True, endpoint="demo.ctraderapi.com",
             env="demo", scope="view",
             accounts=[{"id": "A1", "environment": "demo", "currency": "GBP",
                        "balance": 10000, "type": "demo"}],
             symbols=[{"id": 1, "name": "XAUUSD", "digits": 2}],
             positions=[{"id": "P1", "symbol": "XAUUSD", "direction": "BUY", "volume": 1}])
    s.update(over)
    return s


def _bring_to_ready(scn):
    a = MockCTraderReadOnlyAdapter(scn, clock=_clock())
    a.connect()
    a.authenticate_application()
    a.list_accounts()
    a.authenticate_account()
    return a


def ctx_ready():
    return QuoteContext(connected=True, auth_ready=True, env_verified_demo=True,
                        symbol_verified=True, max_age_ms=5000)


def Q(bid, ask, bt="2026-06-29T10:00:00+00:00", lt="2026-06-29T10:00:00.100+00:00"):
    return RawQuote(symbol="XAUUSD", bid=bid, ask=ask, broker_ts=bt, local_ts=lt)


# ---------------------------------------------------------------- credentials / state
def test_no_credentials_real_adapter_controlled_no_network():
    a = CTraderDemoReadOnlyAdapter(clock=_clock())
    assert a.connect() == "CREDENTIALS_MISSING"          # controlled, no crash, no network
    assert cfg.credentials_present() is False


def test_partial_credentials_stays_controlled():
    a = MockCTraderReadOnlyAdapter(demo_scenario(credentials=False), clock=_clock())
    assert a.connect() == "CREDENTIALS_MISSING"


def test_invalid_credentials_state_fails_to_auth_failed():
    sm = ConnectionStateMachine(clock=_clock())
    sm.transition("CREDENTIALS_MISSING", "x")
    sm.transition("AUTHORISATION_REQUIRED", "x")
    sm.transition("AUTH_FAILED", "invalid_credentials")
    assert sm.state == "AUTH_FAILED"


def test_expired_token_state_then_reconnect():
    sm = ConnectionStateMachine(clock=_clock())
    for s in ["CREDENTIALS_MISSING", "AUTHORISATION_REQUIRED", "AUTHORISATION_CODE_RECEIVED",
              "TOKEN_EXCHANGE_REQUIRED", "TOKEN_AVAILABLE"]:
        sm.transition(s, "x")
    sm.transition("AUTH_FAILED", "expired_token")
    sm.transition("CREDENTIALS_MISSING", "reauth")
    assert sm.state == "CREDENTIALS_MISSING"


def test_invalid_state_transition_fails_closed():
    sm = ConnectionStateMachine(clock=_clock())
    sm.transition("CREDENTIALS_MISSING", "x")
    try:
        sm.transition("READ_ONLY_READY", "skip")           # illegal skip
        assert False, "should have raised"
    except InvalidTransition:
        pass
    assert sm.state == "CREDENTIALS_MISSING"                # unchanged


def test_reconnect_after_simulated_loss():
    sm = ConnectionStateMachine(clock=_clock())
    for s in ["CREDENTIALS_MISSING", "AUTHORISATION_REQUIRED", "AUTHORISATION_CODE_RECEIVED",
              "TOKEN_EXCHANGE_REQUIRED", "TOKEN_AVAILABLE", "APPLICATION_AUTHENTICATED",
              "ACCOUNTS_DISCOVERED", "DEMO_ACCOUNT_SELECTED", "ACCOUNT_AUTHENTICATED",
              "READ_ONLY_READY"]:
        sm.transition(s, "x")
    sm.transition("DISCONNECTED", "loss")
    for s in ["APPLICATION_AUTHENTICATED", "ACCOUNTS_DISCOVERED", "DEMO_ACCOUNT_SELECTED",
              "ACCOUNT_AUTHENTICATED", "READ_ONLY_READY"]:
        sm.transition(s, "reconnect")
    assert sm.state == "READ_ONLY_READY"


# ---------------------------------------------------------------- demo/live + scope
def test_demo_account_accepted():
    a = _bring_to_ready(demo_scenario())
    assert a.get_connection_state() == "READ_ONLY_READY"
    assert a.get_account()["currency"] == "GBP"


def test_live_account_rejected():
    scn = demo_scenario(accounts=[{"id": "L1", "environment": "live", "currency": "GBP"}])
    a = MockCTraderReadOnlyAdapter(scn, clock=_clock())
    a.connect(); a.authenticate_application(); a.list_accounts()
    try:
        a.authenticate_account(); assert False
    except BrokerSafetyError as e:
        assert "live" in str(e).lower()


def test_unknown_account_environment_rejected():
    scn = demo_scenario(accounts=[{"id": "U1", "environment": None, "currency": "GBP"}])
    a = MockCTraderReadOnlyAdapter(scn, clock=_clock())
    a.connect(); a.authenticate_application(); a.list_accounts()
    try:
        a.authenticate_account(); assert False
    except BrokerSafetyError as e:
        assert "unknown" in str(e).lower() or "not demo" in str(e).lower()


def test_view_scope_accepted():
    a = _bring_to_ready(demo_scenario(scope="view"))
    assert a.get_connection_state() == "READ_ONLY_READY"


def test_trade_scope_rejected():
    a = MockCTraderReadOnlyAdapter(demo_scenario(scope="trading"), clock=_clock())
    try:
        a.connect(); assert False
    except BrokerSafetyError as e:
        assert "scope" in str(e).lower()


def test_non_demo_env_rejected():
    a = MockCTraderReadOnlyAdapter(demo_scenario(env="live"), clock=_clock())
    try:
        a.connect(); assert False
    except BrokerSafetyError:
        pass


def test_endpoint_not_allowlisted_rejected():
    a = MockCTraderReadOnlyAdapter(demo_scenario(endpoint="live.ctraderapi.com"), clock=_clock())
    try:
        a.connect(); assert False
    except BrokerSafetyError:
        pass


# ---------------------------------------------------------------- symbols
def test_no_symbol_match():
    a = _bring_to_ready(demo_scenario(symbols=[{"id": 9, "name": "EURUSD"}]))
    try:
        a.resolve_symbol("XAUUSD"); assert False
    except SymbolError as e:
        assert "no symbol" in str(e).lower()


def test_ambiguous_duplicate_symbol_names_not_assumed():
    a = _bring_to_ready(demo_scenario(symbols=[{"id": 1, "name": "XAUUSD"},
                                               {"id": 2, "name": "XAUUSD"}]))
    try:
        a.resolve_symbol("XAUUSD"); assert False
    except SymbolError as e:
        assert "ambiguous" in str(e).lower()


def test_verified_symbol_selection():
    a = _bring_to_ready(demo_scenario())
    sym = a.resolve_symbol("XAUUSD")
    assert sym["id"] == 1 and a._symbol_verified is True


def test_malformed_symbol_metadata_controlled():
    a = _bring_to_ready(demo_scenario(symbols=[{"id": 1}]))   # no 'name'
    try:
        a.resolve_symbol("XAUUSD"); assert False
    except SymbolError:
        pass


# ---------------------------------------------------------------- subscription
def test_quote_subscription_and_unsubscription():
    a = _bring_to_ready(demo_scenario())
    a.resolve_symbol("XAUUSD")
    assert a.subscribe_quotes(1) == {"subscribed": 1}
    assert 1 in a._subscriptions
    assert a.unsubscribe_quotes(1) == {"unsubscribed": 1}
    assert 1 not in a._subscriptions


def test_subscribe_before_symbol_verified_rejected():
    a = _bring_to_ready(demo_scenario())
    try:
        a.subscribe_quotes(1); assert False
    except BrokerSafetyError:
        pass


# ---------------------------------------------------------------- quote status model
def test_complete_admissible():
    assert classify(Q(2000.0, 2000.5), None, ctx_ready())[0] == "COMPLETE_ADMISSIBLE"


def test_bid_only():
    assert classify(Q(2000.0, None), None, ctx_ready())[0] == "BID_ONLY"


def test_ask_only():
    assert classify(Q(None, 2000.5), None, ctx_ready())[0] == "ASK_ONLY"


def test_duplicate_quote():
    p = Q(2000.0, 2000.5)
    assert classify(Q(2000.0, 2000.5), p, ctx_ready())[0] == "DUPLICATE"


def test_stale_quote():
    s = classify(Q(2000.0, 2000.5, bt="2026-06-29T10:00:00+00:00",
                   lt="2026-06-29T10:00:10+00:00"), None, ctx_ready())   # 10s > 5s
    assert s[0] == "STALE" and s[1]["stale"]


def test_out_of_order_quote():
    p = Q(2000.0, 2000.5, bt="2026-06-29T10:00:05+00:00")
    s = classify(Q(2000.0, 2000.5, bt="2026-06-29T10:00:00+00:00"), p, ctx_ready())
    assert s[0] == "OUT_OF_ORDER" and s[1]["out_of_order"]


def test_crossed_market():
    assert classify(Q(2001.0, 2000.0), None, ctx_ready())[0] == "INVALID_CROSSED_MARKET"


def test_invalid_negative_and_non_numeric():
    assert classify(Q(-1, 2000.0), None, ctx_ready())[0] == "INVALID_VALUE"
    assert classify(Q("x", 2000.0), None, ctx_ready())[0] == "INVALID_VALUE"


def test_quote_gated_when_not_connected_or_unverified():
    assert classify(Q(2000, 2000.5), None, QuoteContext())[0] == "BROKER_NOT_CONNECTED"
    assert classify(Q(2000, 2000.5), None, QuoteContext(connected=True))[0] == "AUTH_NOT_AVAILABLE"
    assert classify(Q(2000, 2000.5), None, QuoteContext(connected=True, auth_ready=True))[0] == "ENVIRONMENT_UNVERIFIED"
    assert classify(Q(2000, 2000.5), None, QuoteContext(connected=True, auth_ready=True,
                    env_verified_demo=True))[0] == "SYMBOL_UNVERIFIED"


# ---------------------------------------------------------------- disconnect / positions
def test_controlled_disconnection():
    a = _bring_to_ready(demo_scenario())
    assert a.disconnect() == "DISCONNECTED"


def test_get_positions_read_only():
    a = _bring_to_ready(demo_scenario())
    pos = a.get_positions()
    assert pos and pos[0]["symbol"] == "XAUUSD"


def test_reads_before_ready_rejected():
    a = MockCTraderReadOnlyAdapter(demo_scenario(), clock=_clock())
    a.connect()
    try:
        a.get_account(); assert False
    except BrokerSafetyError:
        pass


# ---------------------------------------------------------------- source scans
def test_prohibited_order_code_source_scan():
    violations = scan_no_order_code([PKG])
    assert violations == [], f"order code found in broker layer: {violations}"


def test_secret_leakage_source_scan():
    findings = scan_secret_leaks([PKG])
    assert findings == [], f"secret leakage in source: {findings}"


def test_no_order_methods_on_interface():
    banned = {"place_order", "submit_order", "create_order", "modify_order",
              "cancel_order", "close_position", "execute_trade"}
    assert banned.isdisjoint(dir(BrokerReadOnlyAdapter))
    assert banned.isdisjoint(dir(MockCTraderReadOnlyAdapter))
    assert banned.isdisjoint(dir(CTraderDemoReadOnlyAdapter))


# ---------------------------------------------------------------- secret-field rejection
def test_secret_field_record_rejected():
    for bad in ({"access_token": "x"}, {"client_secret": "y"}, {"refresh_token": "z"},
                {"bearer_header": "b"}):
        try:
            safe_record(bad); assert False
        except SecretLeak:
            pass


def test_secret_field_redaction_mode():
    out = safe_record({"access_token": "abc", "state": "READ_ONLY_READY"}, redact=True)
    assert out["access_token"] == "[REDACTED]" and out["state"] == "READ_ONLY_READY"


def test_safe_correlation_hash_does_not_reveal():
    h = safe_correlation_hash("super-secret-token")
    assert "super-secret-token" not in h and len(h) == 16


def test_safe_record_allows_non_secret():
    rec = {"connection_state": "READ_ONLY_READY", "reason_code": "ok", "adapter_version": "v"}
    assert safe_record(rec) == rec


# ---------------------------------------------------------------- determinism
def test_deterministic_replay_identical_hashes():
    quotes = [Q(2000, 2000.5), Q(2000, 2000.5), Q(2001, 2001.5, bt="2026-06-29T10:00:01+00:00",
              lt="2026-06-29T10:00:01.100+00:00")]
    a = ReplayCTraderQuoteAdapter(quotes, ctx_ready())
    b = ReplayCTraderQuoteAdapter(quotes, ctx_ready())
    assert a.logical_hash() == b.logical_hash()
    # and the classification sequence is stable & sensible
    seq = [r["status"] for r in a.replay()]
    assert seq[0] == "COMPLETE_ADMISSIBLE" and seq[1] == "DUPLICATE"


def test_state_machine_logical_hash_excludes_wallclock():
    a = ConnectionStateMachine(clock=lambda: "WALL-A")
    b = ConnectionStateMachine(clock=lambda: "WALL-B")
    for m in (a, b):
        m.transition("CREDENTIALS_MISSING", "x")
        m.transition("AUTHORISATION_REQUIRED", "x")
    assert a.logical_hash() == b.logical_hash()    # different clocks, same logical hash


def test_execution_lock_assertion():
    # assert_demo_safety hard-fails if execution were ever not exactly False
    try:
        assert_demo_safety(env="demo", endpoint="demo.ctraderapi.com", scope="view",
                           execution_enabled=True)
        assert False
    except BrokerSafetyError:
        pass
    assert cfg.execution_is_locked_off() is True
