"""
test_multiasset.py — tests for the per-asset-class engine.

Covers the two bugs that were fixed and the future-class guard rails:

  * FOREX routing  — USDCAD (even when mis-tagged CRYPTO) classifies as FOREX,
                     and sizes to a sensible lot size (NOT the ~28,000 it produced
                     when it was sized with crypto maths).
  * GOLD sizing    — a gold signal still sizes EXACTLY as before (0.04 lot,
                     £123.20 at risk) — no regression.
  * CRYPTO sizing  — sizes by the percentage-of-capital-at-risk strategy
                     (multiplier 1, fractional units), flagged for fee/spread.
  * OIL + STOCKS   — recognised, but routed to REVIEW and REFUSED by sizing with
                     the "recognised but not yet calibrated" message.

PAPER mode only. Nothing here connects to a venue, places an order, or moves money.

Run directly (no pytest needed):

    python test_multiasset.py

It is also pytest-compatible:  pytest test_multiasset.py
"""

from decimal import Decimal

import config
import asset_classes
import module_router as router
import module_c_risk as risk
from models import Signal

POT = Decimal(config.POT_SIZE)            # 14000
RISK = Decimal(config.RISK_PCT)           # 0.01
BUDGET = POT * RISK                        # 140 — the 1% cash-at-risk budget


def _signal(ticker, pair, direction, e_low, e_high, sl, targets, asset_class="",
            source="", channel=""):
    """Build a Signal with a true (low, high) entry zone."""
    lo, hi = Decimal(str(e_low)), Decimal(str(e_high))
    return Signal(
        ticker=ticker,
        pair=pair,
        direction=direction,
        asset_class=asset_class,
        entry_low=min(lo, hi),
        entry_high=max(lo, hi),
        stop_loss=Decimal(str(sl)),
        targets=[Decimal(str(t)) for t in targets],
        raw_text=f"{ticker} {direction} test",
        source=source,
    )


# ----------------------------------------------------------------------------
# FOREX — the USDCAD bug, both halves of it
# ----------------------------------------------------------------------------
def test_usdcad_classifies_forex_even_when_mishinted_crypto():
    """The exact shape of last night's mis-tag: parser hint says CRYPTO."""
    sig = _signal("USDCAD", "USDCAD", "SHORT", "1.4600", "1.4600", "1.4650",
                  ["1.4520"], asset_class="CRYPTO", source="FAROUK")
    assert asset_classes.classify(sig) == "FOREX"
    # And siblings that contain the 'USDC' substring must NOT be crypto either.
    assert asset_classes.classify("USDCHF") == "FOREX"
    assert asset_classes.classify("EURUSD") == "FOREX"
    assert asset_classes.classify("GBPJPY") == "FOREX"


def test_usdcad_routes_forex_not_review():
    sig = _signal("USDCAD", "USDCAD", "SHORT", "1.4600", "1.4600", "1.4650",
                  ["1.4520"], asset_class="CRYPTO", source="FAROUK")
    decision = router.route(sig, channel="Farouk FX")
    assert decision.asset_class == "FOREX"
    assert not decision.needs_review, decision.review_reasons
    assert decision.venue == config.VENUE_MAP["FOREX"]


def test_usdcad_sizes_sensibly():
    """Used to size ~28,000 'lots' with crypto maths. Must now be a sane lot size."""
    sig = _signal("USDCAD", "USDCAD", "SHORT", "1.4600", "1.4600", "1.4650",
                  ["1.4520", "1.4450"])
    ticket = risk.size_signal(sig, POT, RISK)

    assert ticket.asset_class == "FOREX"
    assert ticket.sizing_method == "pip_value"
    assert ticket.size_unit == "lot(s)"
    # The headline fix: a sane, small lot size — emphatically NOT thousands.
    assert ticket.lots < Decimal("100"), f"insane lot size: {ticket.lots}"
    assert Decimal("0.01") <= ticket.lots <= Decimal("5")
    # Risk stays inside the 1% budget (round-DOWN guarantees at-or-under).
    assert ticket.cash_at_risk <= BUDGET
    assert ticket.cash_at_risk >= BUDGET / 2     # and isn't trivially tiny
    # Honesty: a non-USD (CAD) quote must be flagged CONFIRM WITH BROKER.
    assert any("CONFIRM WITH BROKER" in f for f in ticket.flags)
    assert ticket.quote_currency == "CAD"


# ----------------------------------------------------------------------------
# GOLD — must behave EXACTLY as before
# ----------------------------------------------------------------------------
def test_gold_sizing_unchanged():
    sig = _signal("XAUUSD", "XAUUSD", "LONG", "2292.00", "2304.50", "2274.00",
                  ["2325", "2350", "2385"], asset_class="METAL")
    ticket = risk.size_signal(sig, POT, RISK)

    assert ticket.asset_class == "METAL"             # ledger label unchanged
    assert ticket.contract_multiplier == Decimal("100")
    assert ticket.size_unit == "lot(s)"
    assert ticket.lots == Decimal("0.04")            # same lot as before the refactor
    assert ticket.cash_at_risk == Decimal("123.20")  # same £ at risk as before
    assert ticket.notional == Decimal("9219.20")     # same notional as before
    assert ticket.slippage == Decimal("0.30")        # gold slippage preserved
    assert ticket.sizing_method == "dollar_per_point"


def test_gold_routes_as_gold():
    sig = _signal("XAUUSD", "XAUUSD", "LONG", "2292.00", "2304.50", "2274.00",
                  ["2325"], asset_class="METAL", source="COLUMBUS")
    decision = router.route(sig, channel="Columbus CPS")
    assert decision.asset_class == "GOLD"
    assert not decision.needs_review


# ----------------------------------------------------------------------------
# CRYPTO — percentage-based sizing, flagged for fees/spread
# ----------------------------------------------------------------------------
def test_crypto_percent_sizing():
    sig = _signal("FET", "FET/USDT", "SHORT", "1.4334", "1.4721", "1.5284",
                  ["1.3912", "1.3323"], asset_class="CRYPTO")
    ticket = risk.size_signal(sig, POT, RISK)

    assert ticket.asset_class == "CRYPTO"
    assert ticket.sizing_method == "percent_risk"
    assert ticket.contract_multiplier == Decimal("1")   # no contract multiplier
    assert ticket.size_unit == "unit(s)"                # fractional coin units, not lots
    assert ticket.lots != ticket.lots.to_integral_value()  # genuinely fractional
    assert ticket.slippage == Decimal("0")              # no slippage modelled yet
    # Percentage-of-capital-at-risk: stop-out costs ~the 1% budget.
    assert ticket.cash_at_risk <= BUDGET
    assert ticket.cash_at_risk >= BUDGET - Decimal("0.01")
    # Flagged as needing fee/spread modelling.
    assert any("fee" in f.lower() or "spread" in f.lower() for f in ticket.flags)


# ----------------------------------------------------------------------------
# Future classes — recognised, but not yet calibrated -> REVIEW, never sized
# ----------------------------------------------------------------------------
NOT_CALIBRATED_MSG = "recognised but not yet calibrated for sizing"


def test_oil_routes_review_not_calibrated():
    sig = _signal("USOIL", "USOIL", "LONG", "78.50", "78.90", "77.40",
                  ["80.00", "82.00"], source="CHRIS")
    decision = router.route(sig, channel="Chris Energy")
    assert decision.asset_class == "OIL"
    assert decision.needs_review
    assert any(NOT_CALIBRATED_MSG in r for r in decision.review_reasons), decision.review_reasons


def test_stock_routes_review_not_calibrated():
    sig = _signal("AAPL", "AAPL", "LONG", "210.00", "212.00", "205.00",
                  ["220", "230"])
    decision = router.route(sig, channel="Random tip")
    assert decision.asset_class == "STOCKS"
    assert decision.needs_review
    assert any(NOT_CALIBRATED_MSG in r for r in decision.review_reasons), decision.review_reasons


def test_uncalibrated_classes_are_refused_by_sizing():
    """Defence in depth: even if one reaches sizing, it must be refused, not guessed."""
    for ticker, pair in (("USOIL", "USOIL"), ("AAPL", "AAPL")):
        sig = _signal(ticker, pair, "LONG", "100", "100", "95", ["110"])
        try:
            risk.size_signal(sig, POT, RISK)
        except risk.RiskError as e:
            assert "not yet calibrated" in str(e), str(e)
        else:
            raise AssertionError(f"{ticker}: sizing should have refused an uncalibrated class")


# ----------------------------------------------------------------------------
# Asset-specific friction — each class uses its OWN slippage, never gold's
# ----------------------------------------------------------------------------
def test_slippage_is_per_asset_class():
    # Each class has its own value; gold's $0.30 is NOT shared with the others.
    assert asset_classes.slippage("GOLD") == Decimal("0.30")
    assert asset_classes.slippage("SILVER") == Decimal("0.03")
    assert asset_classes.slippage("FOREX") != asset_classes.slippage("GOLD")  # forex tighter
    assert asset_classes.slippage("CRYPTO") != asset_classes.slippage("GOLD")


def test_gold_spread_not_applied_to_forex():
    # A sized FOREX ticket must carry FOREX's friction, never gold's $0.30.
    gold = risk.size_signal(_signal("XAUUSD", "XAUUSD", "LONG", "4006", "4016", "3970", ["4030"]), POT)
    forex = risk.size_signal(_signal("EURUSD", "EURUSD", "LONG", "1.0840", "1.0850", "1.0800", ["1.0950"]), POT)
    assert gold.slippage == Decimal("0.30")
    assert forex.slippage == asset_classes.slippage("FOREX")
    assert forex.slippage != gold.slippage


# ----------------------------------------------------------------------------
# Minimal runner (so it works without pytest installed)
# ----------------------------------------------------------------------------
def _run():
    tests = [v for k, v in sorted(globals().items())
             if k.startswith("test_") and callable(v)]
    passed = 0
    failed = 0
    print("=" * 64)
    print("  MULTI-ASSET ENGINE TESTS")
    print("=" * 64)
    for t in tests:
        try:
            t()
            print(f"  PASS  {t.__name__}")
            passed += 1
        except AssertionError as e:
            print(f"  FAIL  {t.__name__}: {e}")
            failed += 1
        except Exception as e:                       # noqa: BLE001 — report any error
            print(f"  ERROR {t.__name__}: {type(e).__name__}: {e}")
            failed += 1
    print("-" * 64)
    print(f"  {passed} passed, {failed} failed, {len(tests)} total")
    print("=" * 64)
    return failed == 0


if __name__ == "__main__":
    import sys
    sys.exit(0 if _run() else 1)
