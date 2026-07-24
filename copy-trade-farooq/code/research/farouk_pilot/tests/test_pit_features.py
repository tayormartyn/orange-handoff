"""Point-in-time integrity: timestamp parsing, strictly-causal session high/low, and the core
invariant — appending/mutating FUTURE candles must not change any earlier feature or decision."""
from __future__ import annotations
import copy
import os
import sys

_PILOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _PILOT)
import pit_features as PIT


def _candles():
    # 1-min XAUUSD candles (decimal-string prices). ts in ms.
    base = PIT.parse_iso_utc_ms("2026-07-04T13:00:00Z")
    rows = [
        (0, "4120.0", "4118.0", "4119.0"),
        (60000, "4123.0", "4119.5", "4122.0"),
        (120000, "4125.0", "4121.0", "4124.0"),   # session high 4125 forms here (T = base+120s)
        (180000, "4124.0", "4116.0", "4117.0"),   # session low 4116 forms here (AFTER T)
        (240000, "4130.0", "4126.0", "4129.0"),
    ]
    return [{"ts_ms": base + off, "high": h, "low": l, "close": c} for off, h, l, c in rows]


def test_timestamp_parsing():
    assert PIT.parse_iso_utc_ms("2026-07-04T13:00:00Z") == 1783170000000
    assert PIT.parse_iso_utc_ms("2026-07-04T13:00:00.250Z") == 1783170000250
    for bad in ("2026-07-04T13:00:00", "2026-07-04 13:00:00Z", "not-a-time"):
        try:
            PIT.parse_iso_utc_ms(bad); assert False, bad
        except ValueError:
            pass


def test_session_high_low_as_of_T():
    c = _candles()
    ss = c[0]["ts_ms"]
    T = c[2]["ts_ms"]                                    # as of the 3rd candle
    shl = PIT.session_high_low(c, as_of_ms=T, session_start_ms=ss)
    assert shl["session_high"] == "4125.0"              # includes candle @ T
    assert shl["session_low"] == "4118.0"              # the 4116 low is AFTER T -> excluded
    assert shl["candles_used"] == 3


def test_future_candle_mutation_invariance():
    c = _candles()
    ss = c[0]["ts_ms"]
    T = c[2]["ts_ms"]
    before = PIT.features_as_of(c, as_of_ms=T, session_start_ms=ss)

    mutated = copy.deepcopy(c)
    mutated[3]["low"] = "4000.0"                         # mutate a FUTURE candle's low (after T)
    mutated[4]["high"] = "9999.0"                        # mutate a FUTURE candle's high
    mutated.append({"ts_ms": c[-1]["ts_ms"] + 60000, "high": "8888.0", "low": "1.0", "close": "5000.0"})
    after = PIT.features_as_of(mutated, as_of_ms=T, session_start_ms=ss)

    assert before == after                              # earlier PIT features are unchanged
    assert PIT.session_high_low(c, as_of_ms=T, session_start_ms=ss) == \
        PIT.session_high_low(mutated, as_of_ms=T, session_start_ms=ss)
    assert before["uses_only_past_or_present"] is True


def test_excursion_is_causal():
    c = _candles()
    ss = c[0]["ts_ms"]
    T = c[2]["ts_ms"]
    ex = PIT.excursion(c, entry_decimal_string="4122.0", direction="BUY", from_ms=ss, to_ms=T)
    # within [ss, T] high=4125, low=4118 -> MFE=3.0, MAE=4.0
    assert ex["mfe"] == "3.0" and ex["mae"] == "4.0"
    # a future candle does not change the windowed excursion up to T
    mutated = copy.deepcopy(c); mutated[4]["high"] = "9999.0"
    assert PIT.excursion(mutated, entry_decimal_string="4122.0", direction="BUY", from_ms=ss, to_ms=T) == ex


def test_previous_day_levels_causal():
    c = _candles()
    ss = c[0]["ts_ms"]
    T = c[2]["ts_ms"]
    lv = PIT.previous_day_levels(c, as_of_ms=T, prev_day_start_ms=ss, prev_day_end_ms=c[1]["ts_ms"])
    assert lv["prev_high"] == "4123.0" and lv["prev_close"] == "4122.0"   # only candles 0-1, none after T
