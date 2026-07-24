"""Price policy: decimal-string only, Decimal parse, reject NaN/Inf/exponent/negative/excess precision,
tick-size, round-trip tolerance. Prices preserved exactly in the audit."""
from __future__ import annotations
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _fixtures import valid_proposal, NOW
from campaign_extractor.alpha_intake import price_policy as PP, qst_adapter as A


def _rej(raw):
    try:
        PP.parse_and_check(raw, field="p")
        return None
    except PP.PricePolicyError as e:
        return e.code


def test_valid_decimal_string_parses_and_preserves():
    rec = PP.parse_and_check("4116.25", field="zoneLow")
    assert rec["original_string"] == "4116.25" and rec["parsed_decimal"] == "4116.25"
    assert rec["downstream_float"] == 4116.25


def test_reject_nan_inf_exponent_negative():
    assert _rej("NaN") == "PRICE_UNSUPPORTED_NOTATION"
    assert _rej("Infinity") == "PRICE_UNSUPPORTED_NOTATION"
    assert _rej("1e3") == "PRICE_UNSUPPORTED_NOTATION"
    assert _rej("-4116.00") == "PRICE_MALFORMED"           # leading '-' not allowed by the regex
    assert _rej("0") == "PRICE_NOT_POSITIVE"


def test_reject_non_string():
    try:
        PP.parse_price(4116.0, field="p"); assert False
    except PP.PricePolicyError as e:
        assert e.code == "PRICE_NOT_STRING"


def test_excess_precision_rejected():
    assert _rej("4116.123") == "PRICE_EXCESS_PRECISION"     # > 2 dp default
    # a configurable policy can allow more precision
    cfg = dict(PP.DEFAULT_PRICE_CONFIG, max_decimal_places=3, tick_size="0.001")
    rec = PP.parse_and_check("4116.123", field="p", config=cfg)
    assert rec["parsed_decimal"] == "4116.123"


def test_tick_size_enforced():
    # 4116.255 fails 2dp precision first; test tick with an allowed-precision config
    cfg = dict(PP.DEFAULT_PRICE_CONFIG, max_decimal_places=3, tick_size="0.01")
    try:
        PP.parse_and_check("4116.255", field="p", config=cfg); assert False
    except PP.PricePolicyError as e:
        assert e.code == "PRICE_NOT_ON_TICK"
    assert PP.parse_and_check("4116.25", field="p", config=cfg)["downstream_float"] == 4116.25


def test_price_violation_rejects_proposal():
    r = A.evaluate(valid_proposal(invalidationPrice="41 10.0"), now_ms=NOW)
    assert r["ack"]["accepted"] is False and r["ack"]["reasonCode"] == "PRICE_POLICY_VIOLATION"


def test_audit_preserves_original_and_decimal():
    r = A.evaluate(valid_proposal(), now_ms=NOW)
    pa = {x["field"]: x for x in r["audit"]["price_audit"]}
    assert pa["zoneLow"]["original_string"] == "4116.00" and pa["zoneLow"]["parsed_decimal"] == "4116.00"
    assert pa["invalidationPrice"]["downstream_float"] == 4110.0
