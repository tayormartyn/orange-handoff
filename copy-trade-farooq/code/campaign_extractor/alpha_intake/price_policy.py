"""
Price policy for the Alpha->QST intake boundary. Prices cross the JSON boundary ONLY as validated
decimal STRINGS (never floats). We parse with Python Decimal, enforce a configurable XAUUSD tick-size
policy, preserve the exact original string + parsed Decimal for the audit record, and convert to the
existing downstream float representation ONLY at the final pure-QST call — with a round-trip tolerance
check. This does NOT migrate any downstream price types; it is a boundary policy only.
"""
from __future__ import annotations
import re
from decimal import Decimal, InvalidOperation

# plain non-negative decimal string: no sign, no exponent, no NaN/Inf, digits[.digits]
_DECIMAL_STRING_RE = re.compile(r"^\d+(\.\d+)?$")


class PricePolicyError(ValueError):
    def __init__(self, code, field=None, detail=None):
        self.code = code
        self.field = field
        self.detail = detail
        super().__init__(f"{code}" + (f" ({field})" if field else "") + (f": {detail}" if detail else ""))


# configurable XAUUSD tick-size policy (NOT a repo-wide decimal migration)
DEFAULT_PRICE_CONFIG = {
    "tick_size": "0.01",            # XAUUSD minimum price increment
    "max_decimal_places": 2,        # excessive precision beyond this is rejected
    "float_roundtrip_tolerance": "0.000001",
    "min_price_exclusive": "0",     # prices must be > 0
    "max_price": "1000000",
}


def parse_price(raw, *, field="price", config=None):
    """Validate + parse a boundary price string to Decimal. Rejects non-strings, NaN/Inf, exponent
    notation, negatives, and excessive precision. Returns (Decimal, original_string)."""
    cfg = config or DEFAULT_PRICE_CONFIG
    if not isinstance(raw, str):
        raise PricePolicyError("PRICE_NOT_STRING", field, type(raw).__name__)
    s = raw.strip()
    if s == "" or s != raw:
        raise PricePolicyError("PRICE_MALFORMED", field, "whitespace or empty")
    low = s.lower()
    if "e" in low or "nan" in low or "inf" in low:
        raise PricePolicyError("PRICE_UNSUPPORTED_NOTATION", field, s)     # exponent / NaN / infinity
    if not _DECIMAL_STRING_RE.match(s):
        raise PricePolicyError("PRICE_MALFORMED", field, s)                # also blocks leading '-'
    try:
        d = Decimal(s)
    except InvalidOperation:
        raise PricePolicyError("PRICE_UNPARSEABLE", field, s)
    if d.is_nan() or d.is_infinite():
        raise PricePolicyError("PRICE_UNSUPPORTED_NOTATION", field, s)
    if d <= Decimal(cfg["min_price_exclusive"]):
        raise PricePolicyError("PRICE_NOT_POSITIVE", field, s)
    if d > Decimal(cfg["max_price"]):
        raise PricePolicyError("PRICE_OUT_OF_RANGE", field, s)
    places = max(0, -d.as_tuple().exponent)
    if places > int(cfg["max_decimal_places"]):
        raise PricePolicyError("PRICE_EXCESS_PRECISION", field, f"{places}>{cfg['max_decimal_places']}")
    return d, s


def validate_tick(d, *, field="price", config=None):
    """Reject a price that is not an exact multiple of the configured tick size."""
    cfg = config or DEFAULT_PRICE_CONFIG
    tick = Decimal(cfg["tick_size"])
    if tick <= 0:
        raise PricePolicyError("TICK_CONFIG_INVALID", field, str(tick))
    q = (d / tick)
    if q != q.to_integral_value():
        raise PricePolicyError("PRICE_NOT_ON_TICK", field, f"{d} not a multiple of {tick}")
    return True


def to_downstream_float(d, *, field="price", config=None):
    """Final conversion to the EXISTING downstream float representation, gated by a round-trip
    tolerance check. Reject the conversion if precision loss exceeds the configured tolerance."""
    cfg = config or DEFAULT_PRICE_CONFIG
    tol = Decimal(cfg["float_roundtrip_tolerance"])
    f = float(d)
    back = Decimal(str(f))
    if abs(back - d) > tol:
        raise PricePolicyError("PRICE_ROUNDTRIP_EXCEEDED", field, f"|{back}-{d}|>{tol}")
    return f


def parse_and_check(raw, *, field="price", config=None):
    """Full boundary parse for one price: parse + tick-validate. Returns an audit dict with the exact
    original string, parsed Decimal (as str), and the downstream float (round-trip checked)."""
    d, s = parse_price(raw, field=field, config=config)
    validate_tick(d, field=field, config=config)
    f = to_downstream_float(d, field=field, config=config)
    return {"field": field, "original_string": s, "parsed_decimal": str(d), "downstream_float": f}
