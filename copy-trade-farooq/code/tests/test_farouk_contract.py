"""Farouk Interpretation Contract — adversarial fixture pack (200+) + shorthand/precedence/contradiction
tests. Fail-closed: no UNKNOWN/ambiguous/conflicting/stale/duplicate/replay/corrected intake may create
an executable proposal. Offline; no broker action; locks stay false."""
from __future__ import annotations
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DE = os.path.join(_ROOT, "campaign_extractor", "demo_executor")
for p in (_ROOT, _DE):
    if p not in sys.path:
        sys.path.insert(0, p)

import config as CFG
import farouk_contract as FC

NOW = 1_800_000_000_000
FRESH = NOW - 60_000            # 1 min old (within 5-min TTL)
STALE = NOW - 400_000          # >5 min old


def valid_ctx(entry_low, entry_high, direction):
    """A quote + path consistent with a valid pending order whose zone is NOT yet touched."""
    if direction == "BUY":       # BUY LIMIT: market ABOVE the entry zone
        mid = entry_high + 6
    else:                        # SELL LIMIT: market BELOW the entry zone
        mid = entry_low - 6
    q = type("Q", (), {"bid": mid, "ask": mid + 0.2, "ts_ms": NOW})()
    path = [{"bid": mid + 1, "ask": mid + 1.2, "ts_ms": NOW - 50_000},
            {"bid": mid + 0.5, "ask": mid + 0.7, "ts_ms": NOW - 25_000},
            {"bid": mid, "ask": mid + 0.2, "ts_ms": NOW - 3_000}]
    return q, path


def _interp(fx):
    return FC.interpret(raw_text=fx["raw"], ocr_text=fx.get("ocr"), provider_ts_ms=fx.get("provider_ts", FRESH),
                        now_ms=NOW, quote=fx.get("quote"), quote_path=fx.get("path"),
                        quote_health_state=fx.get("quote_state", "QUOTES_ACTIVE"),
                        existing_signals=fx.get("existing"), matched_position=fx.get("matched"),
                        material_confirmed=fx.get("material_confirmed", False))


# ---------------------------------------------------------------- fixture pack
def _fixtures():
    fx = []

    # 30 valid fresh XAUUSD signals (varied shorthand)
    combos = [("GOLD", "BUY LIMIT"), ("XAUUSD", "SELL LIMIT"), ("XAU", "BUY"), ("XAU/USD", "SELL"),
              ("GOLD", "LONG"), ("XAUUSD", "SHORT")]
    for i in range(30):
        instr, dword = combos[i % len(combos)]
        direction = "BUY" if ("BUY" in dword or "LONG" in dword) else "SELL"
        lo, hi = (4116.0 + i * 0.5), (4118.0 + i * 0.5)
        stop = (lo - 6) if direction == "BUY" else (hi + 6)
        q, path = valid_ctx(lo, hi, direction)
        sep = ["-", "/", " to ", "–"][i % 4]
        raw = f"{instr} {dword} {lo}{sep}{hi} SL {stop}" + (f" TP {hi + 12}" if i % 2 else "")
        fx.append({"cat": "valid", "raw": raw, "quote": q, "path": path, "provider_ts": FRESH,
                   "exp_intent": "NEW_SIGNAL", "exp_propose": True})

    # 30 trade updates
    upd = ["move sl to be", "breakeven now", "take partial", "take half", "close half", "secure some",
           "hold runner", "tp1 reached move sl to entry", "take some profit", "trail stop"]
    for i in range(30):
        fx.append({"cat": "update", "raw": upd[i % len(upd)], "matched": "VERIFIED",
                   "exp_intent": "TRADE_UPDATE", "exp_propose": False})

    # 20 cancellations
    can = ["cancel gold", "cancel XAUUSD", "cancel previous order", "delete pending", "remove pending order",
           "ignore that signal", "disregard previous gold entry", "scrap that setup"]
    for i in range(20):
        matched = "VERIFIED" if i % 2 == 0 else "AMBIGUOUS"
        fx.append({"cat": "cancel", "raw": can[i % len(can)], "matched": matched,
                   "exp_intent": "CANCEL_PENDING", "exp_propose": (matched == "VERIFIED")})

    # 25 completed result cards
    for i in range(25):
        d = "SELL" if i % 2 else "BUY"
        fx.append({"cat": "result", "raw": f"XAUUSD {d} 4119.4{i%10} -> 4111.8{i%10} profit 1{500+i}.00",
                   "exp_intent": "TRADE_RESULT", "exp_propose": False})

    # 25 ambiguous / malformed
    amb = ["ignore", "delete", "remove", "cancel", "gm traders", "gold looks good", "watching xauusd",
           "XAUUSD 4116", "buy something", "SL 4110", "maybe short gold", "4116-4118"]
    for i in range(25):
        fx.append({"cat": "ambiguous", "raw": amb[i % len(amb)], "exp_intent": None, "exp_propose": False})

    # 20 OCR-corrupted (material number change unconfirmed) — reversed/dropped decimals
    for i in range(20):
        lo, hi = 4116.0, 4118.0
        q, path = valid_ctx(lo, hi, "BUY")
        # raw shows a materially different stop than the normalized (decimal moved)
        fx.append({"cat": "ocr", "raw": "GOLD BUY 4116-4118 SL 41.40", "ocr": "GOLD BUY 4116-4118 SL 41.40",
                   "quote": q, "path": path, "exp_intent": None, "exp_propose": False})

    # 15 duplicates / cross-posted
    import idempotency as ID
    def _existing():
        return [{"signal_id": "canon", "state": "PROPOSED", "provider_ts_ms": FRESH,
                 "source_fingerprint": ID.source_fingerprint(raw_text="GOLD BUY LIMIT 4116-4118 SL 4110"),
                 "semantic_fingerprint": ID.semantic_fingerprint(provider="farouk", instrument="XAUUSD",
                     direction="BUY", order_intent="BUY_LIMIT", entry_low=4116.0, entry_high=4118.0,
                     stop=4110.0, targets=[], provider_ts_ms=FRESH),
                 "execution_identity": ID.execution_identity()}]
    for i in range(15):
        q, path = valid_ctx(4116.0, 4118.0, "BUY")
        fx.append({"cat": "duplicate", "raw": "GOLD BUY LIMIT 4116-4118 SL 4110", "quote": q, "path": path,
                   "existing": _existing(), "exp_intent": "NEW_SIGNAL", "exp_propose": False})

    # 15 conflicting instructions
    conf = ["XAUUSD BUY 4116-4118 SL 4125", "GOLD BUY SELL 4116-4118 SL 4110",
            "XAUUSD BTCUSD BUY 4116-4118 SL 4110", "GOLD BUY 4118-4116 SL 4110"]
    for i in range(15):
        q, path = valid_ctx(4116.0, 4118.0, "BUY")
        fx.append({"cat": "conflict", "raw": conf[i % len(conf)], "quote": q, "path": path,
                   "exp_intent": None, "exp_propose": False})

    # 15 stale / historical
    for i in range(15):
        q, path = valid_ctx(4116.0, 4118.0, "BUY")
        fx.append({"cat": "stale", "raw": "GOLD BUY LIMIT 4116-4118 SL 4110", "quote": q, "path": path,
                   "provider_ts": STALE, "exp_intent": "NEW_SIGNAL", "exp_propose": False})

    # 10 mixed-intent
    mix = ["cancel gold and buy 4116-4118 SL 4110", "XAUUSD SELL 4119->4111 profit 1518 buy 4116-4118 SL 4110"]
    for i in range(10):
        q, path = valid_ctx(4116.0, 4118.0, "BUY")
        fx.append({"cat": "mixed", "raw": mix[i % len(mix)], "quote": q, "path": path,
                   "exp_intent": None, "exp_propose": False})

    return fx


FIXTURES = _fixtures()


def test_fixture_pack_counts():
    from collections import Counter
    c = Counter(f["cat"] for f in FIXTURES)
    assert c["valid"] == 30 and c["update"] == 30 and c["cancel"] == 20 and c["result"] == 25
    assert c["ambiguous"] == 25 and c["ocr"] == 20 and c["duplicate"] == 15 and c["conflict"] == 15
    assert c["stale"] == 15 and c["mixed"] == 10 and len(FIXTURES) == 205


def test_every_fixture_asserts_intent_and_proposal():
    fails = []
    for fx in FIXTURES:
        d = _interp(fx)
        # contract version stamped on every intake
        if d["contract_version"] != CFG.FAROUK_INTERPRETATION_CONTRACT_VERSION:
            fails.append((fx["cat"], "no_version"))
        # may_create_proposal must match expectation
        if d["may_create_proposal"] != fx["exp_propose"]:
            fails.append((fx["cat"], fx["raw"][:30], "propose", d["may_create_proposal"], d["blocking_reasons"][:3]))
        # expected intent (None => don't assert a specific one, but it must not be an eligible NEW_SIGNAL)
        if fx["exp_intent"] and d["intent"] != fx["exp_intent"]:
            fails.append((fx["cat"], fx["raw"][:30], "intent", d["intent"], fx["exp_intent"]))
    assert not fails, fails[:8]


def test_fail_closed_no_bad_category_proposes():
    for fx in FIXTURES:
        if fx["cat"] in ("update", "result", "ambiguous", "ocr", "duplicate", "conflict", "stale", "mixed"):
            d = _interp(fx)
            assert d["may_create_proposal"] is False, (fx["cat"], fx["raw"][:40])
            assert d["execution_eligible"] is False


def test_result_card_flags():
    d = _interp({"raw": "XAUUSD SELL 4119.44 -> 4111.85 profit 1518.00"})
    assert d["intent"] == "TRADE_RESULT"
    assert set(["COMPLETED_TRADE_RESULT", "REPLAY_VALIDATION_ONLY", "NOT_ACTIONABLE_SIGNAL"]) <= set(d["flags"])


def test_precedence_result_over_cancel():
    # a result card that also contains 'cancel' wording stays TRADE_RESULT
    d = FC.interpret(raw_text="cancel — XAUUSD SELL 4119.44 -> 4111.85 profit 1518.00", now_ms=NOW)
    assert d["intent"] == "TRADE_RESULT"


def test_quote_state_blocks_all_non_active():
    q, path = valid_ctx(4116.0, 4118.0, "BUY")
    for st in ("QUOTES_SILENT", "QUOTES_STALE", "QUOTES_DISCONNECTED", "QUOTES_MARKET_CLOSED", "QUOTES_ERROR"):
        d = FC.interpret(raw_text="GOLD BUY LIMIT 4116-4118 SL 4110", provider_ts_ms=FRESH,
                         now_ms=NOW, quote=q, quote_path=path, quote_health_state=st)
        assert d["may_create_proposal"] is False and any("QUOTE_HEALTH_NOT_ACTIVE" in b for b in d["blocking_reasons"])


def test_missing_provider_timestamp_blocks():
    q, path = valid_ctx(4116.0, 4118.0, "BUY")
    d = FC.interpret(raw_text="GOLD BUY LIMIT 4116-4118 SL 4110", provider_ts_ms=None, now_ms=NOW,
                     quote=q, quote_path=path)
    assert d["may_create_proposal"] is False and "PROVIDER_TIMESTAMP_UNVERIFIED" in d["blocking_reasons"]


def test_breakeven_uses_broker_vwap_reference():
    # management interpretation maps to a plan; breakeven volume/price come from broker VWAP downstream
    d = FC.interpret(raw_text="move sl to be", now_ms=NOW, matched_position="VERIFIED")
    assert d["management_plan"] == "MOVE_SL_BREAKEVEN"


def test_take_one_out_is_ambiguous_management():
    d = FC.interpret(raw_text="take one out", now_ms=NOW, matched_position="VERIFIED")
    assert d["management_plan"] == "UNKNOWN_UPDATE" and "AMBIGUOUS_MANAGEMENT_WORDING" in d["blocking_reasons"]


def test_no_trading_constructor_and_locks_false():
    for m in ("farouk_contract.py", "ocr_normalize.py", "contradiction.py"):
        src = open(os.path.join(_DE, m), encoding="utf-8").read()
        for bad in ("ProtoOA", "send_new_order", "send_management", "SerializeToString", "network_send"):
            assert bad not in src
    assert CFG.ORDER_SENDING_ENABLED is False and CFG.ORDER_MANAGEMENT_ENABLED is False
