"""Pre-build safety hardening — TTL, entry-zone/market-path, cancellation intent, layered idempotency,
intent precedence. Deterministic offline; fake transports; no broker action; locks stay false."""
from __future__ import annotations
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DE = os.path.join(_ROOT, "campaign_extractor", "demo_executor")
for p in (_ROOT, _DE):
    if p not in sys.path:
        sys.path.insert(0, p)

import config as CFG
import signal_ttl as TTL
import entry_zone_guard as EZ
import cancel_intent as CI
import idempotency as ID
import position_provenance as PP
from models import ApprovedManagementPlan

NOW = 1_800_000_000_000
MIN = 60_000


def Q(bid, ask, ts=NOW):
    return type("Q", (), {"bid": bid, "ask": ask, "ts_ms": ts})()


# ---- 1-6 TTL ----
def test_ttl_4m59_fresh():
    r = TTL.evaluate_freshness(provider_ts_ms=NOW - 299 * 1000, now_ms=NOW, stage="proposal_construction")
    assert r["freshness_decision"] == "FRESH" and r["execution_eligible"] and r["remaining_validity_seconds"] > 0


def test_ttl_5m01_expired():
    r = TTL.evaluate_freshness(provider_ts_ms=NOW - 301 * 1000, now_ms=NOW)
    assert r["effective_state"] == "EXPIRED" and r["blocking_reason"] == "SIGNAL_TTL_EXCEEDED"


def test_valid_preview_expires_before_approval():
    pv = TTL.evaluate_freshness(provider_ts_ms=NOW, now_ms=NOW, stage="arming")
    assert pv["execution_eligible"]
    later = TTL.evaluate_freshness(provider_ts_ms=NOW, now_ms=NOW + 301 * 1000, stage="final_approval")
    assert later["effective_state"] == "EXPIRED"           # earlier preview does NOT override


def test_valid_proposal_expires_before_network():
    r = TTL.evaluate_freshness(provider_ts_ms=NOW, now_ms=NOW + 400 * 1000, stage="before_network_attempt")
    assert r["blocking_reason"] == "SIGNAL_TTL_EXCEEDED"


def test_missing_provider_ts_blocks():
    r = TTL.evaluate_freshness(provider_ts_ms=None, now_ms=NOW)
    assert r["blocking_reason"] == "PROVIDER_TIMESTAMP_UNVERIFIED" and not r["execution_eligible"]


def test_future_ts_beyond_tolerance_blocks():
    r = TTL.evaluate_freshness(provider_ts_ms=NOW + 200 * 1000, now_ms=NOW)   # 200s future > 60s skew
    assert r["blocking_reason"] == "PROVIDER_TIMESTAMP_UNVERIFIED"


# ---- 7-12 entry-zone / market-path ----
def _ez(**o):
    d = dict(direction="BUY", order_type="BUY_LIMIT", entry_low=4116.0, entry_high=4118.0,
             quote=Q(4110.0, 4110.2), now_ms=NOW, provider_ts_ms=NOW - 60000,
             quote_path=[{"bid": 4110.0, "ask": 4110.2, "ts_ms": NOW - 30000}], require_quote_path=True)
    d.update(o)
    return EZ.evaluate(**d)


def test_stale_quote_blocks():
    assert EZ.QUOTE_STALE in _ez(quote=Q(4110.0, 4110.2, NOW - 999999))["blockers"]


def test_excessive_spread_blocks():
    assert EZ.SPREAD_EXCEEDED in _ez(quote=Q(4110.0, 4112.0))["blockers"]


def test_would_cross_market_blocks():
    # BUY_LIMIT with ask already at/below entry -> marketable
    assert EZ.WOULD_CROSS in _ez(quote=Q(4116.5, 4116.7))["blockers"]


def test_zone_touched_blocks():
    path = [{"bid": 4117.0, "ask": 4117.2, "ts_ms": NOW - 20000}]   # inside 4116-4118
    assert EZ.ZONE_TOUCHED in _ez(quote_path=path)["blockers"]


def test_zone_traversed_blocks():
    path = [{"bid": 4110.0, "ask": 4110.2, "ts_ms": NOW - 40000},   # below
            {"bid": 4120.0, "ask": 4120.2, "ts_ms": NOW - 10000}]   # above
    assert EZ.ZONE_TRAVERSED in _ez(quote_path=path)["blockers"]


def test_no_quote_path_fails_closed():
    assert EZ.QUOTE_PATH_UNVERIFIED in _ez(quote_path=[], require_quote_path=True)["blockers"]


# ---- 13-20 idempotency ----
def _sig(msg="m1", chat="c1", att="a1", text="XAUUSD SELL 4116-4126 SL 4140", provider="farouk",
         instrument="XAUUSD", direction="SELL", intent="LIMIT", lo=4116.0, hi=4126.0, stop=4140.0,
         targets=(), ts=NOW, coid=None, state="ACTIVE", sid="sig-1"):
    return {"signal_id": sid, "state": state, "provider_ts_ms": ts,
            "source_fingerprint": ID.source_fingerprint(message_id=msg, chat_id=chat, attachment_sha256=att, raw_text=text),
            "semantic_fingerprint": ID.semantic_fingerprint(provider=provider, instrument=instrument, direction=direction,
                                                            order_intent=intent, entry_low=lo, entry_high=hi, stop=stop,
                                                            targets=targets, provider_ts_ms=ts),
            "execution_identity": ID.execution_identity(client_order_id=coid)}


def test_exact_repeated_message_ignored():
    r = ID.check_duplicate(_sig(sid="new"), [_sig(sid="canon")], now_ms=NOW)
    assert r["effective_state"] == "DUPLICATE_IGNORED" and r["canonical_signal"] == "canon"


def test_repeated_attachment_diff_spacing_ignored():
    a = _sig(sid="new", text="XAUUSD  SELL   4116-4126   SL 4140")     # different spacing, same attachment
    r = ID.check_duplicate(a, [_sig(sid="canon")], now_ms=NOW)
    assert r["effective_state"] == "DUPLICATE_IGNORED"


def test_equivalent_normalized_zone_ignored():
    a = _sig(sid="new", msg="m2", chat="c2", att="a2")                 # different source, same semantics
    r = ID.check_duplicate(a, [_sig(sid="canon")], now_ms=NOW)
    assert r["duplicate_layer"] == "SEMANTIC_DUPLICATE_WITHIN_WINDOW"


def test_changed_stop_routes_to_human_review():
    a = _sig(sid="new", msg="m2", chat="c2", att="a2", stop=4150.0)
    r = ID.check_duplicate(a, [_sig(sid="canon")], now_ms=NOW)
    assert r["effective_state"] == "POSSIBLE_REISSUE_OR_AMENDMENT" and r["blocking_reason"] == "HUMAN_REVIEW_REQUIRED"


def test_changed_order_type_routes_to_human_review():
    a = _sig(sid="new", msg="m2", chat="c2", att="a2", intent="STOP")
    r = ID.check_duplicate(a, [_sig(sid="canon")], now_ms=NOW)
    assert r["effective_state"] == "POSSIBLE_REISSUE_OR_AMENDMENT"


def test_duplicate_within_window_ignored_and_evidence_preserved():
    a = _sig(sid="new", msg="m2", chat="c2", att="a2", ts=NOW + 60000)  # 1 min later, same semantics
    r = ID.check_duplicate(a, [_sig(sid="canon")], now_ms=NOW + 60000)
    assert r["effective_state"] == "DUPLICATE_IGNORED" and r["evidence_preserved"] is True


def test_deterministic_client_order_id_prevents_repeat():
    a = _sig(sid="new", msg="m2", chat="c2", att="a2", coid="cli-X")
    r = ID.check_duplicate(a, [_sig(sid="canon", coid="cli-X")], now_ms=NOW)
    assert r["duplicate_layer"] == "SAME_CLIENT_ORDER_ID"


# ---- 21 timeout reconcile (entry transport, reused) ----
def test_timeout_reconciles_before_retry():
    import order_transport as OT
    src = open(os.path.join(_DE, "order_transport.py"), encoding="utf-8").read()
    assert "DO NOT RETRY" in src and "reconcile" in src


# ---- 22-30 cancellation ----
def test_ambiguous_ignore_creates_no_cancel():
    ok, reason = CI.detect_cancel("ignore")
    assert not ok and reason == "AMBIGUOUS_ISOLATED_WORD_NO_CONTEXT"


def test_explicit_cancellation_detected():
    for phrase in ("cancel gold", "cancel XAUUSD", "delete pending", "remove pending order",
                   "ignore that signal", "disregard previous gold entry", "scrap that setup"):
        ok, _ = CI.detect_cancel(phrase)
        assert ok, phrase


def _cplan(**o):
    d = dict(plan_id="c1", action="CANCEL_PENDING", signal_id="sig-1", proposal_id="prop-1",
             update_intake_id="u1", account_id=4257941, symbol_id=41, symbol_name="XAUUSD",
             direction="BUY", broker_order_id="ORD-9", client_order_id="cli-abc")
    d.update(o)
    return ApprovedManagementPlan(**d)


def test_symbol_only_cancel_match_blocks():
    p = _cplan(broker_order_id=None, client_order_id=None, signal_id="x", proposal_id="y")
    cands = [{"order_id": "O1", "symbol": "XAUUSD", "direction": "BUY", "account_id": 4257941, "state": "PENDING"}]
    status, *_ = PP.match_cancel_target(p, cands)
    assert status == "NO_MATCH"


def test_multiple_cancel_candidates_block():
    cands = [{"order_id": "ORD-9", "account_id": 4257941, "state": "PENDING"},
             {"order_id": "ORD-9", "account_id": 4257941, "state": "PENDING"}]
    assert PP.match_cancel_target(_cplan(), cands)[0] == "AMBIGUOUS"


def test_filled_order_cannot_cancel():
    cands = [{"order_id": "ORD-9", "account_id": 4257941, "state": "FILLED"}]
    status, oid, reason = PP.match_cancel_target(_cplan(), cands)
    assert status == "BLOCKED" and reason == "CANDIDATE_ALREADY_FILLED"


def test_already_cancelled_cannot_cancel_again():
    cands = [{"order_id": "ORD-9", "account_id": 4257941, "state": "CANCELLED"}]
    assert PP.match_cancel_target(_cplan(), cands)[2] == "CANDIDATE_ALREADY_CANCELLED"


def test_wrong_account_cancel_blocks():
    cands = [{"order_id": "ORD-9", "account_id": 9999, "state": "PENDING"}]
    assert PP.match_cancel_target(_cplan(), cands)[0] == "NO_MATCH"   # other account filtered out


def test_replay_cancellation_ineligible_and_live_gate():
    import management_transport as MT
    from models import AccountSnapshot
    ft = type("FT", (), {"send_management": lambda s, f: (_ for _ in ()).throw(AssertionError("SENT!")),
                         "reconcile": lambda s, a: None, "reconcile_compare": lambda s, a, b: []})()
    def send(**over):
        kw = dict(transport=ft, account=AccountSnapshot(4257941, False, 1.0, "GBP", "trade", "DEMO"),
                  endpoint_host="demo.ctraderapi.com", endpoint_port=5035, permission_scope="SCOPE_TRADE",
                  position_match="VERIFIED", quote_fresh=True, update_fresh=True, plan_unexpired=True,
                  replay_status="LIVE", operator_approval_completed=True, permit_valid=True, lease_valid=True,
                  order_management_enabled=False, now_ms=NOW)
        kw.update(over)
        return MT.send_management(_cplan(), **kw)
    assert send(replay_status="REPLAY_VALIDATION_ONLY")["final_state"] == "NO_BROKER_ACTION_SENT"
    assert send(account=AccountSnapshot(9999, False, 1.0, "GBP", "trade", "DEMO"))["final_state"] == "NO_BROKER_ACTION_SENT"
    assert send(endpoint_host="live.ctraderapi.com")["final_state"] == "NO_BROKER_ACTION_SENT"


# ---- 5 intent precedence ----
def test_intent_precedence():
    assert CI.classify_intent("cancel gold", is_result_card=True) == "TRADE_RESULT"   # result > cancel
    assert CI.classify_intent("cancel gold", is_trade_update=True) == "CANCEL_PENDING"  # cancel > update
    assert CI.classify_intent("move sl to be", is_trade_update=True) == "TRADE_UPDATE"
    assert CI.classify_intent("XAUUSD BUY entry 3300 sl 3295", is_new_signal=True) == "NEW_SIGNAL"


# ---- 32-34 locks / no protobuf / no send ----
def test_locks_all_false_and_no_send():
    assert CFG.ORDER_SENDING_ENABLED is False and CFG.ORDER_MANAGEMENT_ENABLED is False
    cfg = open(os.path.join(_ROOT, "config.py"), encoding="utf-8").read()
    cc = open(os.path.join(_ROOT, "ctrader_config.py"), encoding="utf-8").read()
    assert "EXECUTION_ENABLED = False" in cfg and "CTRADER_EXECUTION_ENABLED = False" in cc
    # new safety modules never call broker transport / construct protobuf
    for m in ("signal_ttl.py", "entry_zone_guard.py", "cancel_intent.py", "idempotency.py"):
        src = open(os.path.join(_DE, m), encoding="utf-8").read()
        for bad in ("ProtoOA", "send_management", "send_new_order", "SerializeToString"):
            assert bad not in src
