"""
test_parser_zone.py — entry-RANGE parsing + the "don't over-correct" guard.

Proves:
  * Farouk's range-entry formats parse cleanly (both zone ends kept, plus a
    CONSERVATIVE primary entry — BUY->higher, SELL->lower, never the midpoint).
  * A complete signal (asset + direction + entry zone + STOP) becomes a clean
    signal; a range with NO stop, or management/commentary chatter, does NOT —
    it stays REVIEW / commentary (the range-fix must not over-trigger).
  * Sizing uses the conservative primary entry.

All deterministic — no API key needed (the local parser handles these). PAPER,
read-only.  Run:  python test_parser_zone.py
"""

from decimal import Decimal

import config
import module_b_parser as parser
import module_router as router
import module_c_risk as risk
import module_a_telegram as listener
from models import Signal


# ----------------------------------------------------------------------------
# 1) The real examples parse, with both ends + a conservative primary entry
# ----------------------------------------------------------------------------
def test_buy_range_with_now_at():
    sig = parser.parse_locally("Gold buy now @ 2312 - 2309")
    assert sig is not None
    assert sig.ticker == "XAUUSD" and sig.direction == "LONG"
    assert sig.entry_low == Decimal("2309") and sig.entry_high == Decimal("2312")
    assert sig.primary_entry == Decimal("2312")        # BUY -> higher (worse fill)
    assert sig.stop_loss is None                        # no SL in this one


def test_buy_range_with_stop_tight_spacing():
    sig = parser.parse_locally("XAUUSD buy 4323-4315 sl 4295")
    assert sig is not None
    assert sig.ticker == "XAUUSD" and sig.direction == "LONG"
    assert sig.entry_low == Decimal("4315") and sig.entry_high == Decimal("4323")
    assert sig.primary_entry == Decimal("4323")        # BUY -> higher
    assert sig.stop_loss == Decimal("4295")


def test_sell_range_with_odd_spacing_and_stop():
    sig = parser.parse_locally("Gold sell 4269- 4280 sl 4300")
    assert sig is not None
    assert sig.ticker == "XAUUSD" and sig.direction == "SHORT"
    assert sig.entry_low == Decimal("4269") and sig.entry_high == Decimal("4280")
    assert sig.primary_entry == Decimal("4269")        # SELL -> lower (worse fill)
    assert sig.stop_loss == Decimal("4300")


def test_spacing_variations_all_parse():
    for txt in ("XAUUSD buy 4323-4315 sl 4295",
                "XAUUSD buy 4323 - 4315 sl 4295",
                "XAUUSD buy 4323  -  4315 sl 4295",
                "XAUUSD buy 4315–4323 sl 4295"):   # en-dash
        sig = parser.parse_locally(txt)
        assert sig is not None, txt
        assert sig.entry_low == Decimal("4315") and sig.entry_high == Decimal("4323"), txt


def test_parse_signal_uses_local_without_api():
    # parse_signal() must return the deterministic result here (no API key needed).
    sig = parser.parse_signal("Gold sell 4269- 4280 sl 4300")
    assert sig.ticker == "XAUUSD" and sig.direction == "SHORT"
    assert sig.primary_entry == Decimal("4269")


# ----------------------------------------------------------------------------
# 2) Routing: complete signal -> ROUTE (clean); no-stop -> REVIEW
# ----------------------------------------------------------------------------
def test_complete_signals_route_clean():
    for txt in ("XAUUSD buy 4323-4315 sl 4295", "Gold sell 4269- 4280 sl 4300"):
        d = router.route(parser.parse_locally(txt))
        assert not d.needs_review, (txt, d.review_reasons)
        assert d.asset_class == "GOLD"


def test_range_without_stop_goes_to_review():
    d = router.route(parser.parse_locally("Gold buy now @ 2312 - 2309"))
    assert d.needs_review
    assert any("stop" in r.lower() for r in d.review_reasons)


# ----------------------------------------------------------------------------
# 3) History classification — clean only when complete; chatter stays put
# ----------------------------------------------------------------------------
def _classify(text):
    # parse_ctx ok=False -> deterministic only (no LLM), so the test is hermetic.
    cls, _fields, _conf = listener._classify_message(text, {"ok": False})
    return cls


def test_classify_complete_signals_clean():
    assert _classify("XAUUSD buy 4323-4315 sl 4295") == "clean signal"
    assert _classify("Gold sell 4269- 4280 sl 4300") == "clean signal"


def test_classify_range_without_stop_is_review_not_clean():
    assert _classify("Gold buy now @ 2312 - 2309") == "REVIEW"


def test_management_messages_stay_commentary():
    # These have no direction -> not even signal-shaped -> commentary.
    for msg in ("we have 100 pips so tp 2",
                "sl to entry",
                "Take profit guys, please",
                "Move stop loss to entry, we are 50 pips in profit",
                "100+ pips!!!!!"):
        assert _classify(msg) == "commentary", msg


def test_management_with_direction_is_not_promoted_to_clean():
    # Signal-shaped chatter (has 'buy'/'tp' + numbers) but no real entry+stop:
    # it must NOT become a clean signal. REVIEW (or commentary) is fine.
    for msg in ("we are 100-150 pips in profit on the buy, take tp2",
                "still holding the gold buy, tp1 done, move sl to be"):
        assert _classify(msg) != "clean signal", msg


# ----------------------------------------------------------------------------
# 3b) MANDATORY: classify() — both directions clean; management ALWAYS commentary
# ----------------------------------------------------------------------------
CLEAN_SIGNALS = [
    "GOLD buy @ 2315 sl 2305",
    "XAUUSD Sell 2345 SL:2360",
    "gold buy now 2312-2309 sl 2300",
    "Sell Limit gold 2345 sl 2360 tp1 2330",
]

# Danger cases: they DO contain gold/price/sl tokens but are running-trade
# updates — they must NOT be promoted to a new signal.
MANAGEMENT_MESSAGES = [
    "we got 100 pips on gold, move sl to 2312",
    "gold tp1 hit, move sl to entry",
    "running 50 pips in profit on gold",
    "close half the gold position, sl to breakeven",
]


def test_classify_clean_signals_both_directions():
    for txt in CLEAN_SIGNALS:
        assert parser.classify(txt) == "clean_signal", txt


def test_classify_management_always_commentary():
    for txt in MANAGEMENT_MESSAGES:
        assert parser.classify(txt) == "commentary", txt


def test_management_never_auto_clean():
    # A management phrase + a complete fresh signal must NOT become clean_signal.
    # (It's a re-entry, so it surfaces as REVIEW — see the re-entry tests below.)
    txt = "gold buy 2310 sl 2300, tp1 hit, move sl to entry"
    assert parser.is_management(txt) is True
    assert parser.classify(txt) != "clean_signal"


def test_reentry_management_plus_complete_signal_is_review():
    # Management language ("sl to entry", "hit") AND a complete fresh signal
    # (direction + entry zone + stop) -> REVIEW. Surfaced so a real re-entry is
    # not missed, but never auto-clean. Asset may be implied (single-asset channel).
    txt = "SL to entry was hit again. BUY Entry: 4339-4330 SL: 4318"
    assert parser.is_management(txt) is True
    assert parser.has_fresh_entry(txt) is True
    assert parser.classify(txt) == "REVIEW"


def test_reentry_with_asset_also_review():
    txt = "gold buy 2310 sl 2300, tp1 hit, move sl to entry"
    assert parser.classify(txt) == "REVIEW"


def test_pure_management_no_fresh_signal_stays_commentary():
    # Management only — no complete fresh entry -> commentary (unchanged).
    for txt in ("we got 100 pips on gold, move sl to 2312",   # no direction
                "gold tp1 hit, move sl to entry",             # no entry+stop
                "running 50 pips in profit on gold",
                "close half the gold position, sl to breakeven"):
        assert parser.has_fresh_entry(txt) is False, txt
        assert parser.classify(txt) == "commentary", txt


def test_classify_review_when_incomplete():
    # Mentions gold + numbers but no SL -> REVIEW (not clean, not commentary).
    assert parser.classify("GOLD buy @ 2315") == "REVIEW"
    # Mentions gold + numbers but no direction -> REVIEW.
    assert parser.classify("gold 2315 2320 2330") == "REVIEW"


def test_flexible_entry_markers_and_punctuation():
    # @ with/without space, "at", and bare-after-direction all read the entry.
    for txt in ("gold buy @2311 sl 2300",
                "gold buy @ 2311 sl 2300",
                "XAUUSD buy at 2311 sl 2300",
                "XAUUSD Sell 2311 SL-2320"):
        sig = parser.parse_locally(txt)
        assert sig is not None and sig.entry_low == Decimal("2311"), txt


def test_order_type_detected():
    assert parser.parse_locally("Sell Limit gold 2345 sl 2360").order_type == "limit"
    assert parser.parse_locally("gold buy now 2312 sl 2300").order_type == "market"


def test_tp_index_not_captured_as_target():
    sig = parser.parse_locally("Sell Limit gold 2345 sl 2360 tp1 2330")
    assert sig.targets == [Decimal("2330")]      # the '1' in 'tp1' is NOT a target


# ----------------------------------------------------------------------------
# 4) Sizing uses the conservative primary entry
# ----------------------------------------------------------------------------
def _signal(direction, low, high, primary, stop, targets):
    return Signal(ticker="XAUUSD", pair="XAUUSD", direction=direction, asset_class="METAL",
                  entry_low=Decimal(low), entry_high=Decimal(high),
                  stop_loss=Decimal(stop), targets=[Decimal(t) for t in targets],
                  raw_text="t", primary_entry=Decimal(primary))


def test_sizing_uses_conservative_primary_long():
    # LONG: conservative = HIGH end (4323). raw_entry (pre-slippage) must be that.
    sig = _signal("LONG", "4315", "4323", "4323", "4295", ["4360"])
    ticket = risk.size_signal(sig, Decimal(config.POT_SIZE))
    assert ticket.raw_entry == Decimal("4323")


def test_sizing_uses_conservative_primary_short():
    # SHORT: conservative = LOW end (4269).
    sig = _signal("SHORT", "4269", "4280", "4269", "4300", ["4230"])
    ticket = risk.size_signal(sig, Decimal(config.POT_SIZE))
    assert ticket.raw_entry == Decimal("4269")


def test_sizing_without_primary_entry_still_works():
    # No primary_entry recorded -> risk derives the conservative end (no regression).
    sig = Signal(ticker="XAUUSD", pair="XAUUSD", direction="LONG", asset_class="METAL",
                 entry_low=Decimal("4315"), entry_high=Decimal("4323"),
                 stop_loss=Decimal("4295"), targets=[Decimal("4360")], raw_text="t")
    ticket = risk.size_signal(sig, Decimal(config.POT_SIZE))
    assert ticket.raw_entry == Decimal("4323")


# ----------------------------------------------------------------------------
# Minimal runner (no pytest needed)
# ----------------------------------------------------------------------------
def _run():
    tests = [v for k, v in sorted(globals().items())
             if k.startswith("test_") and callable(v)]
    passed = failed = 0
    print("=" * 64)
    print("  ENTRY-RANGE PARSER TESTS")
    print("=" * 64)
    for t in tests:
        try:
            t()
            print(f"  PASS  {t.__name__}")
            passed += 1
        except AssertionError as e:
            print(f"  FAIL  {t.__name__}: {e}")
            failed += 1
        except Exception as e:                       # noqa: BLE001
            print(f"  ERROR {t.__name__}: {type(e).__name__}: {e}")
            failed += 1
    print("-" * 64)
    print(f"  {passed} passed, {failed} failed, {len(tests)} total")
    print("=" * 64)
    return failed == 0


if __name__ == "__main__":
    import sys
    sys.exit(0 if _run() else 1)
