"""Exact 'take more profit' OCR update handling + volume terminology tests. DRY-RUN; nothing sent."""
from __future__ import annotations
import glob
import os
import sys
import tempfile

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DE = os.path.join(_ROOT, "campaign_extractor", "demo_executor")
for p in (_ROOT, _DE):
    if p not in sys.path:
        sys.path.insert(0, p)

import config as CFG
import update_parser
import management_planner as MP
import volume_terms as VT
import update_plans as UP
from audit_db import AuditDB
from models import BrokerPosition, Quote, AccountSnapshot

RAW = "1540 pips take more profit. Sell one 41 24.95 to 411 1.60."
NOW = 1_800_000_000_000


def pos(volume_units=300, price=4124.95, label="order-sig-1", direction="SELL"):
    return BrokerPosition(88449001, label, "XAUUSD", direction, volume_units, price, 4140.0, None, NOW)


def quote(bid=4111.60, ask=4111.71):
    return Quote(bid, ask, NOW)


def acct():
    return AccountSnapshot(4257941, False, 10000.0, "GBP", "trade", "DEMO")


def _run(fn):
    tmp = tempfile.mkdtemp(prefix="ocr_")
    try:
        return fn(tmp)
    finally:
        import shutil
        shutil.rmtree(tmp, ignore_errors=True)


# 1 + 2 — parse + raw immutable + normalization as candidate only
def test_exact_ocr_parse_and_normalization():
    r = update_parser.parse_ocr_update(RAW)
    assert r["raw_text"] == RAW                          # raw unchanged
    assert r["normalized_candidate"] == "1540 pips — take more profit. Sell 1: 4124.95 to 4111.60."
    assert r["normalized_candidate"] != r["raw_text"]
    assert r["classification"] == "TRADE_UPDATE" and r["intent"] == "PARTIAL_CLOSE_CANDIDATE"
    assert r["provider_claimed_pips"] == 1540
    assert r["provider_entry_candidate"] == 4124.95 and r["provider_exit_candidate"] == 4111.60
    assert r["provider_price_movement"] == 13.35 and r["provider_leg_candidate"] == "SELL_1"
    assert r["provider_close_volume"] == "UNKNOWN"
    for fl in ("OCR_DIGIT_SPACING", "CLOSE_VOLUME_NOT_SPECIFIED", "PROVIDER_LEG_NOT_YET_MAPPED",
               "PROVIDER_PIPS_NOT_BROKER_VERIFIED"):
        assert fl in r["ambiguity_flags"]
    assert r["instruction_vs_recap"] == "INSTRUCTION_VS_RECAP_REQUIRES_CONFIRMATION"


# 3 — action without a linked position -> NO_MATCH
def test_action_without_position_no_match():
    def f(tmp):
        r = UP.build_ocr_update_plan(signal_id="sig-1", source_class="TRADE_UPDATE", confirmed=True,
            provider_verified=True, ocr_text=RAW, update_ts_ms=NOW, account=acct(), account_type="HEDGED",
            symbol_digits=2, pip_position=1, positions=[], quote=quote(), now_ms=NOW, units_per_lot=10000,
            lot_size_raw=10000, min_volume_units=100, step_volume_units=100, audit=AuditDB(os.path.join(tmp, "a.db")))
        assert not r["valid"] and "NO_MATCH" in r["card"]["reason"]
    _run(f)


# 4 — a price pair without action language must not propose a close
def test_price_pair_without_action_no_close():
    r = update_parser.parse_ocr_update("Sell one 4124.95 to 4111.60")
    assert r["intent"] == "AMBIGUOUS_UPDATE" and r["price_pair_only"] is True


# 5 — SELL_1 without explicit leg mapping stays ambiguous
def test_sell1_unmapped():
    r = update_parser.parse_ocr_update(RAW)
    assert r["provider_leg_candidate"] == "SELL_1" and "PROVIDER_LEG_NOT_YET_MAPPED" in r["ambiguity_flags"]


# 6 — provider pips separate from broker pips
def test_provider_pips_separate_from_broker():
    a = MP.ocr_take_more_proposal(pos(), update_parser.parse_ocr_update(RAW), min_volume_units=100,
                                  step_volume_units=100, units_per_lot=10000, lot_size_raw=10000,
                                  quote=quote(), pip_position=1)
    assert a.detail["provider_claimed_pips"] == 1540
    assert a.detail["broker_pip_calc_of_move"] == 133.5      # 13.35 / 0.1
    assert a.detail["provider_claimed_pips"] != a.detail["broker_pip_calc_of_move"]


# 7 — no provider volume -> operator policy warning
def test_no_provider_volume_operator_policy():
    a = MP.ocr_take_more_proposal(pos(), update_parser.parse_ocr_update(RAW), min_volume_units=100,
                                  step_volume_units=100, units_per_lot=10000, lot_size_raw=10000,
                                  quote=quote(), pip_position=1, operator_policy_fraction=0.5)
    assert a.detail["operator_policy_label"] == "OPERATOR_POLICY_NOT_PROVIDER_VOLUME"
    assert a.detail["operator_policy_fraction"] == 0.5 and a.detail["provider_close_volume"] == "UNKNOWN"


# 8 — 50% of 0.03 lots normalizes to a broker step
def test_fifty_pct_of_003_lots():
    a = MP.ocr_take_more_proposal(pos(volume_units=300), update_parser.parse_ocr_update(RAW),
                                  min_volume_units=100, step_volume_units=100, units_per_lot=10000,
                                  lot_size_raw=10000, quote=quote(), pip_position=1, operator_policy_fraction=0.5)
    close = a.detail["operator_policy_close"]
    assert close["raw_protocol_volume"] == 100 and close["underlying_xau_units"] == 1.0 and close["displayed_lots"] == 0.01
    assert a.detail["operator_policy_remaining"]["displayed_lots"] == 0.02


# 9 — raw protocol / underlying units / lots displayed separately
def test_volume_terms_separate():
    t = VT.symbol_terms(lot_size_raw_protocol=10000, min_volume_raw_protocol=100, step_volume_raw_protocol=100)
    assert t["one_lot"] == {"raw_protocol_volume": 10000, "underlying_xau_units": 100.0, "displayed_lots": 1.0}
    assert t["min"]["displayed_lots"] == 0.01 and t["step"]["underlying_xau_units"] == 1.0


# 12 — full dry-run ends dry-run only
def test_dry_run_only_with_matched_position():
    def f(tmp):
        adb = AuditDB(os.path.join(tmp, "a.db"))
        r = UP.build_ocr_update_plan(signal_id="sig-1", source_class="TRADE_UPDATE", confirmed=True,
            provider_verified=True, ocr_text=RAW, update_ts_ms=NOW, account=acct(), account_type="HEDGED",
            symbol_digits=2, pip_position=1, positions=[pos(label="order-sig-1")], quote=quote(), now_ms=NOW,
            units_per_lot=10000, lot_size_raw=10000, min_volume_units=100, step_volume_units=100, audit=adb)
        assert r["valid"] and r["status"] == "MANAGEMENT_PLAN_VALIDATED"
        UP.arm_plan(r["plan_id"], adb)
        res = UP.dry_run_approve(r["plan_id"], now_ms=NOW, audit=adb)
        assert res["result"] == "UPDATE_PLAN_DRY_RUN_APPROVED" and res["broker_action_sent"] is False
    _run(f)


def test_trade_result_cannot_modify_via_ocr():
    def f(tmp):
        r = UP.build_ocr_update_plan(signal_id="sig-1", source_class="TRADE_RESULT", confirmed=True,
            provider_verified=True, ocr_text=RAW, update_ts_ms=NOW, account=acct(), account_type="HEDGED",
            symbol_digits=2, pip_position=1, positions=[pos()], quote=quote(), now_ms=NOW, units_per_lot=10000,
            lot_size_raw=10000, min_volume_units=100, step_volume_units=100)
        assert not r["valid"] and r["card"]["reason"] == "TRADE_RESULT_CANNOT_MODIFY_POSITION"
    _run(f)


# 13/14/15 — no order/amend/close endpoint anywhere
def test_no_order_amend_close_req():
    # management_adapter.py / order_request_adapter.py hold the AUTHORISED, network-GATED (disabled)
    # builders — exempted from the raw-constructor scan, same as the other constructor-scan tests.
    exempt = {"management_adapter.py", "order_request_adapter.py"}
    for p in glob.glob(os.path.join(_DE, "*.py")):
        if os.path.basename(p) in exempt:
            continue
        src = open(p, encoding="utf-8").read()
        for bad in ("ProtoOAAmendPositionSLTPReq", "ProtoOAClosePositionReq", "ProtoOACancelOrderReq",
                    "ProtoOAAmendOrderReq", "sendorder"):
            assert bad not in src


# 16/17 — hashes + locks
def test_locks_false():
    cfg = open(os.path.join(_ROOT, "config.py"), encoding="utf-8").read()
    cc = open(os.path.join(_ROOT, "ctrader_config.py"), encoding="utf-8").read()
    assert "EXECUTION_ENABLED = False" in cfg and "CTRADER_EXECUTION_ENABLED = False" in cc
    assert CFG.ORDER_SENDING_ENABLED is False
