"""Tests for the OCR proposal adapter (pure, synthetic OCR text) + TRADE_UPDATE class + safety."""
from __future__ import annotations
import inspect
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_CON = os.path.join(_ROOT, "campaign_extractor", "paper_loop", "console")
for p in (_ROOT, os.path.join(_ROOT, "campaign_extractor"),
          os.path.join(_ROOT, "campaign_extractor", "q4_align"),
          os.path.join(_ROOT, "campaign_extractor", "paper_loop"),
          os.path.join(_ROOT, "campaign_extractor", "vision_v1"), _CON):
    if p not in sys.path:
        sys.path.insert(0, p)
os.chdir(_ROOT)

import ocr_adapter as O
import server as C
import image_confirm
import farouk_cohort_monitor as M


def ocr(*texts):
    return {"lines": [{"text": t, "box": None, "conf": 0.9} for t in texts], "full_text": "\n".join(texts)}


def test_fresh_gold_signal_proposed_signal():
    p = O.propose(ocr("XAUUSD BUY", "Entry 3300 - 3305", "SL 3295", "TP1 3315  TP2 3325"))
    assert p["classification"]["value"] == "SIGNAL"
    f = p["fields"]
    assert f["instrument"]["value"] == "XAUUSD" and f["instrument"]["confidence"] == "HIGH"
    assert f["direction"]["value"] == "BUY"
    assert f["entry_low"]["value"] == "3300" and f["entry_high"]["value"] == "3305"
    assert f["stop_price"]["value"] == "3295" and "3315" in (f["target_prices"]["value"] or "")


def test_tp2_move_sl_is_trade_update():
    p = O.propose(ocr("TP2 reached", "Move SL to entry", "Still holding, next target 3400"))
    assert p["classification"]["value"] == "TRADE_UPDATE"


# Regression fixture — EXACT OCR of the 2026-07-02 snip Martyn had to classify by hand. The OCR glued
# the words ("...pipstakemoreprofit") so a spaced "take more profit" never substring-matched, and that
# phrase was absent from UPDATE_KWS. classify() now carries the phrase and matches space-insensitively.
LATEST_SNIP_OCR_20260702 = ("SeaScalper-Farouk", "WR", "20:22", "@whale140pipstakemoreprofit",
                            "XAUUSD-VIPsell1", "1335.00", "4124.95?4111.60")


def test_latest_glued_take_more_profit_is_trade_update():
    p = O.propose(ocr(*LATEST_SNIP_OCR_20260702))
    assert p["classification"]["value"] == "TRADE_UPDATE"
    assert p["classification"]["confidence"] == "HIGH"


def test_new_management_keywords_are_trade_update():
    for phrase in ("take more profit", "secure profit", "bank profit", "close worst entry",
                   "hold best entry", "hold runner", "take one out", "reduce position", "partial close",
                   "move stop to entry"):
        p = O.propose(ocr("XAUUSD", phrase))
        assert p["classification"]["value"] == "TRADE_UPDATE", phrase


def test_price_pair_alone_not_trade_update():
    # a bare entry->target price pair must NOT be read as a management update (no partial close)
    p = O.propose(ocr("XAUUSD", "4124.95 -> 4111.60"))
    assert p["classification"]["value"] != "TRADE_UPDATE"


# ---- completed result-card classification ----
def test_result_card_exact_fixture():
    p = O.propose(ocr("XAUUSD-VIP sell 2", "4119.44 -> 4111.85", "1 518.00"))
    assert p["classification"]["value"] == "TRADE_RESULT" and p["classification"]["confidence"] == "HIGH"
    assert p["intent"] == "COMPLETED_TRADE_RESULT"
    rc = p["result_card"]
    assert rc["instrument"] == "XAUUSD" and rc["direction"] == "SELL" and rc["provider_leg_candidate"] == "SELL_2"
    assert rc["entry_candidate"] == 4119.44 and rc["exit_candidate"] == 4111.85
    assert rc["reported_profit_candidate"] == 1518.00
    assert p["flags"] == ["HISTORICAL_RESULT_CARD", "NOT_ACTIONABLE_SIGNAL", "REPLAY_VALIDATION_ONLY"]


def test_spaced_money_normalizes():
    assert O.result_card("XAUUSD sell 2 4119.44 -> 4111.85 1 518.00")["profit"] == "1518.00"


def test_arrow_variants():
    for arrow in ("->", "→", "to"):
        p = O.propose(ocr("XAUUSD sell 2", f"4119.44 {arrow} 4111.85", "1518.00"))
        assert p["classification"]["value"] == "TRADE_RESULT", arrow


def test_price_pair_without_money_is_unknown():
    assert O.propose(ocr("XAUUSD sell", "4119.44 -> 4111.85"))["classification"]["value"] == "UNKNOWN"


def test_money_without_pair_is_unknown():
    assert O.propose(ocr("XAUUSD sell", "1518.00"))["classification"]["value"] == "UNKNOWN"


def test_instrument_direction_alone_not_signal():
    assert O.propose(ocr("XAUUSD sell"))["classification"]["value"] != "SIGNAL"


def test_result_card_precedence_over_weak_signal():
    # instrument + SELL would be a weak/absent signal; the completed card wins
    p = O.propose(ocr("XAUUSD-VIP sell 2", "4119.44 -> 4111.85", "1518.00"))
    assert p["classification"]["value"] == "TRADE_RESULT"


def test_result_card_creates_no_order_or_broker_action():
    # classification is advisory; ocr_adapter emits no order proposal / broker call (real code, not
    # the "does NOT create cohort/order" disclaimer text)
    src = inspect.getsource(O)
    for bad in ("ProtoOANewOrderReq", "send_new_order(", "build_proposal(", "/api/demo_approve",
                "new_order("):
        assert bad not in src


def test_pnl_card_is_trade_result():
    p = O.propose(ocr("XAUUSD", "Closed in profit", "P&L: +$1749.57"))
    assert p["classification"]["value"] == "TRADE_RESULT"


def test_uncertain_is_unknown():
    p = O.propose(ocr("gm traders", "coffee time, good luck today"))
    assert p["classification"]["value"] == "UNKNOWN"


def test_looking_for_entry_not_signal():
    # has instrument+direction+price+levels BUT 'looking for' -> must NOT be a fresh SIGNAL
    p = O.propose(ocr("XAUUSD BUY", "looking for a new entry 3300", "SL 3290 TP 3310"))
    assert p["classification"]["value"] != "SIGNAL"


def test_unclear_digits_not_accepted():
    p = O.propose(ocr("XAUUSD BUY", "Entry 33OO - 3305", "SL 3295", "TP 3315"))
    e = p["fields"]["entry_low"]
    assert e["value"] is None and e["confidence"] == "LOW" and e["reason"] == "AMBIGUOUS_DIGITS"
    assert e["candidate"] == "33OO"                 # candidate shown, never silently accepted


def test_provider_text_not_verified():
    p = O.propose(ocr("SeaScalper-Farouk", "XAUUSD BUY 3300 SL 3295 TP 3315"))
    pc = p["provider_candidate"]
    assert pc["candidate"] is not None and pc["verification_state"] == "PROVIDER_UNVERIFIED"


def test_confidence_tiers():
    p = O.propose(ocr("hello world with no trade content"))
    assert p["fields"]["instrument"]["confidence"] == "LOW"
    assert p["fields"]["instrument"]["value"] is None      # LOW -> blank


def test_analyse_creates_no_observation_route():
    src = inspect.getsource(C.do_analyse)
    for bad in ("PaperDB", "do_observe", "save_review", "build_review_record", ".record("):
        assert bad not in src


def test_manual_correction_overrides_ocr():
    # OCR may propose XAUUSD; the human submits BTCUSD -> the observe route uses the SUBMITTED value
    a = C._answers({"intake_class": "SIGNAL", "instrument": "BTCUSD", "direction": "SELL",
                    "entry_low": "60000"})
    assert a["instrument"] == "BTCUSD" and a["direction"] == "SELL" and a["entry_low"] == "60000"


def _bundle(ic):
    return {"intake_id": "u1", "review": {"review_id": "r", "intake_id": "u1", "intake_class": ic,
            "explicit_confirmation_state": "CONFIRMED",
            "provider": {"value": "seascalperfarouk", "verification_state": "PROVIDER_VERIFIED"},
            "provider_posted_at": {"value": None, "provenance": "UNVERIFIABLE"}, "fields": {}},
            "manifest": {"duplicate": False}, "paper_obs": None, "bridge_obs": None}


def test_trade_update_contributes_zero_to_cohort():
    r = M.assess([_bundle("TRADE_UPDATE")])
    assert r["complete"] == 0 and r["counts"]["trade_update_excluded"] == 1


def test_trade_update_gate_in_image_paper_run():
    import image_paper_run
    src = inspect.getsource(image_paper_run.run)
    assert "TRADE_UPDATE_EXCLUDED" in src           # gated before any signal processing


def test_execution_locks_and_no_order_code():
    from broker_readonly.source_scan import scan_no_order_code
    cfg = open(os.path.join(_ROOT, "config.py"), encoding="utf-8").read()
    assert "EXECUTION_ENABLED = False" in cfg
    assert scan_no_order_code([_CON]) == []
