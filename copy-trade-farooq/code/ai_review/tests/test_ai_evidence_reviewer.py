"""
Tests for the AI Evidence Reviewer lane (schemas + fail-closed validator + stub reviewer).

Runnable standalone:  python test_ai_evidence_reviewer.py   (also pytest-compatible)
No AI API calls; no secrets; observation-only.
"""
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_PKG = os.path.dirname(_HERE)
for p in (_PKG, _HERE):
    if p not in sys.path:
        sys.path.insert(0, p)

import schema                    # noqa: E402
import stub_reviewer as SR       # noqa: E402

FIXTURE = os.path.join(_PKG, "fixtures", "fp_live_trade_obs_003_xauusd.json")


def _pack():
    return json.load(open(FIXTURE, encoding="utf-8"))


def _valid_output():
    return {
        "pack_id": "X", "extracted_instrument": "XAUUSD", "direction": "SHORT",
        "entry_zone": "4102-4115", "sl": "4152", "tp_levels": ["4077.00", "4055.00"],
        "result_claim": "100 pips; 200 pips", "evidence_used": [45625],
        "confidence": 0.7, "contradictions": [], "missing_evidence": [],
        "ohlc_required": True, "verdict": "EXTRACTED",
    }


# ===================================================================== fixture + stub end-to-end
def test_fixture_pack_validates():
    schema.validate_evidence_pack(_pack())


def test_stub_reviewer_extracts_xau_pack():
    out = SR.review(_pack(), provider="stub")
    assert out["verdict"] in schema.VERDICTS
    assert out["extracted_instrument"] == "XAUUSD"
    assert out["direction"] == "SHORT"                      # SELL call
    assert out["sl"] == "4152"
    assert out["entry_zone"] and "4102" in out["entry_zone"]
    assert out["ohlc_required"] is True                     # result claims need independent OHLC
    assert "100" in (out["result_claim"] or "")
    # review-only stamp is hard-wired by the validator
    assert out["review_only"] is True and out["executable"] is False
    assert out["trade_ready"] is False and out["observation_only"] is True


def test_unknown_provider_rejected():
    try:
        SR.review(_pack(), provider="fable-live")
        assert False, "unknown provider should raise"
    except ValueError:
        pass


# ===================================================================== forbidden execution fields
def test_each_forbidden_field_is_rejected():
    bad_fields = ["order", "order_type", "lot_size", "risk", "account_id", "broker",
                  "cTrader", "permit", "lease", "execute", "trade_now"]
    for f in bad_fields:
        out = _valid_output()
        out[f] = "x"
        try:
            schema.validate_reviewer_output(out)
            assert False, f"forbidden field '{f}' was not rejected"
        except schema.ReviewerOutputRejected:
            pass


def test_forbidden_field_nested_is_rejected():
    out = _valid_output()
    out["extras"] = {"deep": [{"broker_hint": "pepperstone"}]}
    try:
        schema.validate_reviewer_output(out)
        assert False, "nested forbidden field not rejected"
    except schema.ReviewerOutputRejected:
        pass


def test_provider_cannot_self_declare_executable():
    # even if a provider tries to send review_only=False / trade_ready=True, the validator stamp wins
    out = _valid_output()
    out["review_only"] = False
    out["trade_ready"] = True
    clean = schema.validate_reviewer_output(out)
    assert clean["review_only"] is True and clean["trade_ready"] is False
    assert clean["executable"] is False


# ===================================================================== schema strictness
def test_invalid_verdict_rejected():
    out = _valid_output(); out["verdict"] = "TRADE_READY"
    try:
        schema.validate_reviewer_output(out); assert False
    except schema.ReviewerOutputRejected:
        pass


def test_missing_required_field_rejected():
    out = _valid_output(); del out["contradictions"]
    try:
        schema.validate_reviewer_output(out); assert False
    except schema.ReviewerOutputRejected:
        pass


def test_confidence_bounds():
    out = _valid_output(); out["confidence"] = 1.7
    try:
        schema.validate_reviewer_output(out); assert False
    except schema.ReviewerOutputRejected:
        pass


def test_contradictory_pack_flagged():
    pack = _pack()
    pack["messages"].append({"message_id": 1, "timestamp_utc": "2026-07-10T14:00:00+00:00",
                             "raw_text": "actually BUY long here"})
    out = SR.review(pack)
    assert out["verdict"] == "CONTRADICTORY"
    assert out["contradictions"]


# ===================================================================== lane has no execution imports
def test_ai_review_has_no_forbidden_imports():
    import re, glob
    imp = re.compile(r"^\s*(?:from|import)\s+([\w\.]+)")
    forbidden = re.compile(r"(broker|ctrader|qst|execution|order|permit|lease|module_b|demo_executor)", re.I)
    offenders = []
    for f in glob.glob(os.path.join(_PKG, "*.py")):
        for ln in open(f, encoding="utf-8"):
            m = imp.match(ln)
            if m and forbidden.search(m.group(1)):
                offenders.append((os.path.basename(f), ln.strip()[:80]))
    assert offenders == [], offenders


def _run_all():
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    passed, failed = 0, []
    for t in tests:
        try:
            t(); passed += 1; print(f"PASS  {t.__name__}")
        except Exception as e:  # noqa: BLE001
            failed.append((t.__name__, repr(e))); print(f"FAIL  {t.__name__}: {e!r}")
    print(f"\n{passed}/{len(tests)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(_run_all())
