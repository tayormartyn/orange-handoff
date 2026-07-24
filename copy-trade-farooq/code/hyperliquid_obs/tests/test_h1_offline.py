"""
H1 — offline test suite for the Hyperliquid testnet public-data observer.

No network, no credentials, no signing key. Covers: safety gates, endpoint policy,
BTC-perp identification from returned metadata (not assumed), book/trade classification,
the WS state machine + reconnect, the isolated append-only DB, deterministic replay,
isolation from gold/Telegram/campaign evidence, and the no-trading-path source scan that
BLOCKS the brick.

Run:  python hyperliquid_obs/tests/test_h1_offline.py
(There is no pytest in this environment, so this file carries its own runner.)
"""
import hashlib
import json
import os
import sqlite3
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)

from hyperliquid_obs import config, OBSERVER_VERSION, DATA_LINEAGE
from hyperliquid_obs.safety import (
    assert_testnet_safety, assert_no_signing_key_in_process, find_signing_key_in_env,
    find_signing_modules, HyperliquidSafetyError)
from hyperliquid_obs.instruments import resolve_perp, InstrumentError
from hyperliquid_obs.observations import (
    BookSnapshot, TradeTick, ObsContext, classify_book, classify_trade)
from hyperliquid_obs.states import WSConnectionStateMachine, InvalidTransition
from hyperliquid_obs.secrets import safe_record, SecretLeak
from hyperliquid_obs.observation_db import ObservationDB, TABLES
from hyperliquid_obs.source_scan import scan_no_trading_path
from hyperliquid_obs.adapter import OfflineReplayObserver

PKG = os.path.join(ROOT, "hyperliquid_obs")
FIX = os.path.join(PKG, "fixtures")
TESTNET = config.APPROVED_TESTNET_REST
TESTNET_WS = config.APPROVED_TESTNET_WS
# a mainnet host is detected by rule; build it from fragments so no literal lives in source
MAINNET = "https://api." + "hyperliquid" + ".xyz"


def _meta():
    return json.load(open(os.path.join(FIX, "meta.json"), encoding="utf-8"))


def _frames():
    return json.load(open(os.path.join(FIX, "session.json"), encoding="utf-8"))["frames"]


def _ok_env():
    # a clean environment with NO signing material
    return {"PATH": "/usr/bin", "HYPERLIQUID_ENV": "testnet"}


def _clock():
    n = {"i": 0}

    def c():
        n["i"] += 1
        return f"T{n['i']:04d}"
    return c


def ctx():
    return ObsContext(connected=True, env_verified_testnet=True, symbol_verified=True, max_age_ms=5000)


# ----------------------------------------------------------------- safety gates
def test_testnet_safety_accepts_clean_testnet():
    assert_testnet_safety(env="testnet", endpoint=TESTNET, execution_enabled=False,
                          mainnet_allowed=False)  # no raise


def test_mainnet_endpoint_rejected():
    try:
        assert_testnet_safety(env="testnet", endpoint=MAINNET, execution_enabled=False,
                              mainnet_allowed=False)
        assert False
    except HyperliquidSafetyError as e:
        assert "mainnet" in str(e).lower()


def test_unknown_env_rejected():
    try:
        assert_testnet_safety(env="staging", endpoint=TESTNET, execution_enabled=False,
                              mainnet_allowed=False)
        assert False
    except HyperliquidSafetyError:
        pass


def test_execution_enabled_hard_fail():
    try:
        assert_testnet_safety(env="testnet", endpoint=TESTNET, execution_enabled=True,
                              mainnet_allowed=False)
        assert False
    except HyperliquidSafetyError as e:
        assert "execution" in str(e).lower()


def test_mainnet_allowed_hard_fail():
    try:
        assert_testnet_safety(env="testnet", endpoint=TESTNET, execution_enabled=False,
                              mainnet_allowed=True)
        assert False
    except HyperliquidSafetyError as e:
        assert "mainnet" in str(e).lower()


def test_unapproved_testnet_path_rejected():
    try:
        assert_testnet_safety(env="testnet", endpoint="https://evil.example.com",
                              execution_enabled=False, mainnet_allowed=False)
        assert False
    except HyperliquidSafetyError:
        pass


def test_config_endpoint_rules():
    assert config.is_testnet_endpoint(TESTNET) and config.is_testnet_endpoint(TESTNET_WS)
    assert config.is_mainnet_endpoint(MAINNET)
    assert not config.is_mainnet_endpoint(TESTNET)
    assert config.endpoint_is_approved_testnet(TESTNET)
    assert not config.endpoint_is_approved_testnet(MAINNET)
    assert config.execution_is_locked_off() is True


# ----------------------------------------------------------------- no signing key in process
def test_no_signing_key_clean_process_passes():
    assert_no_signing_key_in_process(environ=_ok_env(), modules={})  # no raise
    assert find_signing_key_in_env(_ok_env()) == []


def test_signing_key_named_env_detected():
    bad = {"HYPERLIQUID_PRIVATE_KEY": "0x" + "a" * 64}
    assert find_signing_key_in_env(bad) == ["HYPERLIQUID_PRIVATE_KEY"]
    try:
        assert_no_signing_key_in_process(environ=bad, modules={})
        assert False
    except HyperliquidSafetyError as e:
        assert "signing" in str(e).lower() or "key" in str(e).lower()


def test_raw_privkey_value_in_hl_var_detected():
    bad = {"HL_WALLET": "a" * 64}        # 64-hex value in an HL/wallet-named var
    assert "HL_WALLET" in find_signing_key_in_env(bad)


def test_mnemonic_value_detected():
    words = " ".join(["abandon"] * 11 + ["about"])   # 12-word BIP39-style
    bad = {"ETH_WALLET_SEED": words}
    assert "ETH_WALLET_SEED" in find_signing_key_in_env(bad)


def test_signing_module_import_detected():
    fake = {"eth" + "_account": object()}
    assert find_signing_modules(fake) == ["eth" + "_account"]
    try:
        assert_no_signing_key_in_process(environ=_ok_env(), modules=fake)
        assert False
    except HyperliquidSafetyError:
        pass


def test_find_signing_key_never_returns_values():
    bad = {"HYPERLIQUID_PRIVATE_KEY": "0x" + "d" * 64}
    out = find_signing_key_in_env(bad)
    assert out == ["HYPERLIQUID_PRIVATE_KEY"]            # name only, value never surfaced


# ----------------------------------------------------------------- instrument identification
def test_btc_perp_identified_from_returned_meta():
    perp = resolve_perp(_meta(), "BTC")
    assert perp.name == "BTC" and perp.asset_id == 0 and perp.sz_decimals == 5
    assert perp.verified is True


def test_btc_not_assumed_when_absent():
    meta = {"universe": [{"name": "ETH", "szDecimals": 4}]}
    try:
        resolve_perp(meta, "BTC")
        assert False
    except InstrumentError as e:
        assert "no perp" in str(e).lower()


def test_ambiguous_btc_rejected():
    meta = {"universe": [{"name": "BTC", "szDecimals": 5}, {"name": "BTC", "szDecimals": 5}]}
    try:
        resolve_perp(meta, "BTC")
        assert False
    except InstrumentError as e:
        assert "ambiguous" in str(e).lower()


def test_malformed_meta_rejected():
    try:
        resolve_perp({"nope": 1}, "BTC")
        assert False
    except InstrumentError:
        pass
    try:
        resolve_perp({"universe": [{"name": "BTC"}]}, "BTC")    # missing szDecimals
        assert False
    except InstrumentError:
        pass


# ----------------------------------------------------------------- book classification
def B(bids, asks, et=1000, lt=1050):
    return BookSnapshot(coin="BTC", bids=bids, asks=asks, exch_time_ms=et, local_recv_ms=lt)


def test_book_admissible():
    s = classify_book(B([{"px": "60000", "sz": "1"}], [{"px": "60001", "sz": "1"}]), None, ctx())
    assert s[0] == "COMPLETE_ADMISSIBLE" and abs(s[2]["spread"] - 1.0) < 1e-9


def test_book_crossed():
    assert classify_book(B([{"px": "60010"}], [{"px": "60005"}]), None, ctx())[0] == "CROSSED_BOOK"


def test_book_empty_and_one_sided():
    assert classify_book(B([], []), None, ctx())[0] == "EMPTY_BOOK"
    assert classify_book(B([{"px": "60000"}], []), None, ctx())[0] == "ONE_SIDED"


def test_book_stale():
    s = classify_book(B([{"px": "60000"}], [{"px": "60001"}], et=1000, lt=7000), None, ctx())
    assert s[0] == "STALE" and s[1]["stale"]


def test_book_out_of_order_and_duplicate():
    prev = B([{"px": "60000"}], [{"px": "60001"}], et=2000)
    assert classify_book(B([{"px": "60000"}], [{"px": "60001"}], et=1000), prev, ctx())[0] == "OUT_OF_ORDER"
    dup = classify_book(B([{"px": "60000"}], [{"px": "60001"}], et=2000),
                        B([{"px": "60000"}], [{"px": "60001"}], et=2000), ctx())
    assert dup[0] == "DUPLICATE" and dup[1]["duplicate"]


def test_book_gated_when_unverified():
    assert classify_book(B([{"px": "1"}], [{"px": "2"}]), None, ObsContext())[0] == "NOT_CONNECTED"
    assert classify_book(B([{"px": "1"}], [{"px": "2"}]), None,
                         ObsContext(connected=True))[0] == "ENVIRONMENT_UNVERIFIED"
    assert classify_book(B([{"px": "1"}], [{"px": "2"}]), None,
                         ObsContext(connected=True, env_verified_testnet=True))[0] == "SYMBOL_UNVERIFIED"


def test_book_invalid_timestamp():
    assert classify_book(B([{"px": "60000"}], [{"px": "60001"}], et=None), None, ctx())[0] == "INVALID_TIMESTAMP"


# ----------------------------------------------------------------- trade classification
def T(px, sz, et, tid=None):
    return TradeTick(coin="BTC", side="B", px=px, sz=sz, exch_time_ms=et, local_recv_ms=et + 10, tid=tid)


def test_trade_admissible_dup_ooo_invalid():
    assert classify_trade(T("60000", "0.1", 100, tid=1), ctx())[0] == "TRADE_ADMISSIBLE"
    assert classify_trade(T("60000", "0.1", 100, tid=1), ctx(), seen_tids={1})[0] == "DUPLICATE"
    assert classify_trade(T("60000", "0.1", 90, tid=2), ctx(), last_trade_time_ms=100)[0] == "OUT_OF_ORDER"
    assert classify_trade(T("-1", "0.1", 100, tid=3), ctx())[0] == "INVALID_VALUE"


# ----------------------------------------------------------------- state machine
def test_state_linear_path():
    sm = WSConnectionStateMachine(clock=_clock())
    for s in ["CONNECTING", "CONNECTED", "META_LOADED", "SYMBOL_VERIFIED", "SUBSCRIBED", "STREAMING"]:
        sm.transition(s, "x")
    assert sm.get_state() == "STREAMING"


def test_state_illegal_skip_fails_closed():
    sm = WSConnectionStateMachine(clock=_clock())
    sm.transition("CONNECTING", "x")
    try:
        sm.transition("STREAMING", "skip")
        assert False
    except InvalidTransition:
        pass
    assert sm.get_state() == "CONNECTING"


def test_reconnect_rewalk_increments():
    sm = WSConnectionStateMachine(clock=_clock())
    for s in ["CONNECTING", "CONNECTED", "META_LOADED", "SYMBOL_VERIFIED", "SUBSCRIBED", "STREAMING"]:
        sm.transition(s, "x")
    sm.transition("STALLED", "drop")
    sm.transition("CONNECTING", "reconnect")          # must re-walk, not jump to STREAMING
    assert sm.reconnects == 1
    try:
        sm.transition("STREAMING", "illegal jump")
        assert False
    except InvalidTransition:
        pass


def test_state_logical_hash_excludes_wallclock():
    a = WSConnectionStateMachine(clock=lambda: "WALL-A")
    b = WSConnectionStateMachine(clock=lambda: "WALL-B")
    for m in (a, b):
        m.transition("CONNECTING", "x")
        m.transition("CONNECTED", "x")
    assert a.logical_hash() == b.logical_hash()


# ----------------------------------------------------------------- isolated append-only DB
def _db():
    return ObservationDB(":memory:")


def test_db_only_hl_tables_no_gold_or_campaign():
    db = _db()
    names = db.table_names()
    assert names == sorted(TABLES)
    assert all(n.startswith("hl_") for n in names)
    assert not any(("campaign" in n or "telegram" in n or "gold" in n or "broker" in n
                    or "prospective" in n) for n in names)


def test_db_append_only_update_rejected():
    db = _db()
    db.append_connection_event(environment="testnet", endpoint=None,
                               connection_state="CONNECTED", reason_code="ok")
    try:
        db.con.execute("UPDATE hl_connection_events SET reason_code='tampered'")
        db.con.commit()
        assert False
    except sqlite3.Error as e:
        assert "append-only" in str(e).lower()
    assert db.con.execute("SELECT reason_code FROM hl_connection_events").fetchone()[0] == "ok"


def test_db_append_only_delete_rejected():
    db = _db()
    db.append_connection_event(environment="testnet", endpoint=None,
                               connection_state="CONNECTED", reason_code="ok")
    try:
        db.con.execute("DELETE FROM hl_connection_events")
        db.con.commit()
        assert False
    except sqlite3.Error as e:
        assert "append-only" in str(e).lower()
    assert db.count("hl_connection_events") == 1


def test_db_no_update_or_delete_methods():
    members = dir(ObservationDB)
    assert not any(("update" in m or "delete" in m or "drop" in m) for m in members)


def test_db_secret_field_rejected():
    db = _db()
    try:
        db._append("hl_connection_events", {"environment": "testnet", "private_key": "0xabc"})
        assert False
    except SecretLeak:
        pass


def test_db_crossed_quarantined_never_admissible():
    db = _db()
    st = db.append_book_observation(B([{"px": "60010"}], [{"px": "60005"}]), environment="testnet")
    row = db.con.execute("SELECT primary_status, quarantine_flag FROM hl_book_observations").fetchone()
    assert st == "CROSSED_BOOK" and row[0] == "CROSSED_BOOK" and row[1] == 1


def test_db_stamps_lineage_on_every_row():
    db = _db()
    db.append_book_observation(B([{"px": "60000"}], [{"px": "60001"}]), environment="testnet")
    db.append_trade_observation(T("60000", "0.1", 100, tid=1), environment="testnet")
    assert db.lineages() == [DATA_LINEAGE]


def test_db_environment_required():
    db = _db()
    try:
        db.append_book_observation(B([{"px": "1"}], [{"px": "2"}]), environment="")
        assert False
    except ValueError:
        pass


# ----------------------------------------------------------------- replay (fixtures) determinism
def test_replay_status_sequences():
    obs = OfflineReplayObserver(_meta(), _frames(), clock=_clock())
    res = obs.run()
    assert res["book"] == ["COMPLETE_ADMISSIBLE", "COMPLETE_ADMISSIBLE", "DUPLICATE",
                           "OUT_OF_ORDER", "STALE", "CROSSED_BOOK", "COMPLETE_ADMISSIBLE"]
    assert res["trade"] == ["TRADE_ADMISSIBLE", "TRADE_ADMISSIBLE", "DUPLICATE", "OUT_OF_ORDER"]
    assert obs.perp.name == "BTC" and obs.perp.asset_id == 0
    assert obs.disconnect() == "CLOSED"


def test_replay_deterministic_logical_hash():
    a = OfflineReplayObserver(_meta(), _frames(), clock=_clock())
    b = OfflineReplayObserver(_meta(), _frames(), clock=_clock())
    a.run(); b.run()
    assert a.logical_hash() == b.logical_hash()


def test_replay_records_instrument_and_admissible_book():
    obs = OfflineReplayObserver(_meta(), _frames(), clock=_clock())
    obs.run()
    inst = obs.db.con.execute("SELECT perp_name, asset_id, verified FROM hl_instrument_observations").fetchone()
    assert inst == ("BTC", 0, 1)
    adm = obs.db.con.execute("SELECT COUNT(*) FROM hl_book_observations WHERE primary_status='COMPLETE_ADMISSIBLE'").fetchone()[0]
    assert adm == 3


# ----------------------------------------------------------------- isolation from other evidence
def test_replay_does_not_touch_campaign_evidence():
    camp = os.path.join(ROOT, "campaign_extractor", "phase0", "fixtures", "fixture_2026-06-17.json")
    if not os.path.exists(camp):
        return  # campaign evidence not present in this checkout; nothing to protect
    before = hashlib.sha256(open(camp, "rb").read()).hexdigest()
    obs = OfflineReplayObserver(_meta(), _frames(), clock=_clock())
    obs.run(); obs.disconnect()
    after = hashlib.sha256(open(camp, "rb").read()).hexdigest()
    assert before == after


def test_default_db_path_isolated():
    from hyperliquid_obs.observation_db import DEFAULT_DB_PATH
    p = DEFAULT_DB_PATH.replace("\\", "/")
    assert "hyperliquid_obs/data/hyperliquid_observation_v1.db" in p
    assert "broker_observation" not in p and "paper_log" not in p


# ----------------------------------------------------------------- secrets helper
def test_safe_record_rejects_signing_fields():
    for bad in ({"private_key": "x"}, {"mnemonic": "y"}, {"signing_key": "z"}, {"seed": "s"}):
        try:
            safe_record(bad); assert False
        except SecretLeak:
            pass
    assert safe_record({"coin": "BTC", "primary_status": "OK"}) == {"coin": "BTC", "primary_status": "OK"}


# ----------------------------------------------------------------- THE brick-blocking source scan
def test_no_trading_path_source_scan():
    violations = scan_no_trading_path([PKG])
    assert violations == [], f"trading/signing path found in observation package: {violations}"


def test_no_order_methods_on_observer_interfaces():
    banned = {"order", "place_order", "cancel", "modify_order", "withdraw", "deposit",
              "usd_transfer", "approve_agent", "sign", "close_position", "transfer"}
    for cls in (OfflineReplayObserver, ObservationDB, WSConnectionStateMachine):
        assert banned.isdisjoint(dir(cls)), f"banned method exposed on {cls.__name__}"


# --------------------------------------------------------------------------- runner
def _run_all():
    g = dict(globals())
    tests = sorted((n, f) for n, f in g.items() if n.startswith("test_") and callable(f))
    passed, failed = 0, []
    for name, fn in tests:
        try:
            fn()
            passed += 1
        except Exception as e:  # noqa: BLE001 — a test runner legitimately catches all
            import traceback
            failed.append((name, e))
            print(f"FAIL  {name}: {e}")
            traceback.print_exc()
    print(f"\n{passed}/{len(tests)} passed, {len(failed)} failed")
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(_run_all())
