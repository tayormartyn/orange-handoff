"""
asset_classes.py — the per-asset-class registry accessor & classifier.

This is the small, shared brain that turns a ticker into an asset class and
hands back that class's spec from config.ASSET_CLASSES. Both the router
(module_router) and the risk calculator (module_c_risk) read it, so the rules
for "what IS this instrument" live in exactly one place — and adding a new asset
class is a config edit, not a code change (see config.ASSET_CLASSES).

It is pure metadata: it classifies and looks things up. It sizes nothing,
routes nothing, and touches no money.
"""

from decimal import Decimal, InvalidOperation

import config

# Re-export the fine asset-class names so callers don't hardcode strings.
GOLD = "GOLD"
SILVER = "SILVER"
FOREX = "FOREX"
CRYPTO = "CRYPTO"
OIL = "OIL"
COMMODITIES = "COMMODITIES"
STOCKS = "STOCKS"
UNKNOWN = "UNKNOWN"


# ----------------------------------------------------------------------------
# Small readers (tolerate a Signal object, a plain dict, or a bare ticker str)
# ----------------------------------------------------------------------------
def _get(obj, name, default=""):
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)


def _fields(ticker_or_obj):
    """
    Normalise the input into (ticker, pair, parser_hint), all upper/stripped.
    Accepts a Signal, a dict, or a bare ticker string (pair defaults to ticker).
    """
    if isinstance(ticker_or_obj, str):
        ticker = ticker_or_obj
        pair = ticker_or_obj
        hint = ""
    else:
        ticker = str(_get(ticker_or_obj, "ticker", "")).strip()
        pair = str(_get(ticker_or_obj, "pair", "")).strip() or ticker
        hint = str(_get(ticker_or_obj, "asset_class", "")).strip()
    return ticker.upper().strip(), pair.upper().strip(), hint.upper().strip()


def _letters(text: str) -> str:
    return "".join(ch for ch in str(text).upper() if ch.isalpha())


def quote_currency(ticker: str, pair: str = "") -> str:
    """
    Best-effort QUOTE currency/token of a pair (the part you're priced in).
    'EUR/USD' -> 'USD';  'USDCAD' -> 'CAD';  'BTC/USDT' -> 'USDT'.
    """
    for candidate in (pair, ticker):
        c = str(candidate or "").upper().strip()
        if not c:
            continue
        if "/" in c:
            tail = _letters(c.split("/")[-1])
            if tail:
                return tail
        letters = _letters(c)
        if len(letters) == 6:           # e.g. USDCAD -> CAD
            return letters[3:]
    return ""


def _base_token(ticker: str, pair: str = "") -> str:
    """Best-effort BASE token (what you're buying). 'BTC/USDT' -> 'BTC'."""
    for candidate in (ticker, pair):
        c = str(candidate or "").upper().strip()
        if "/" in c:
            head = _letters(c.split("/")[0])
            if head:
                return head
        letters = _letters(c)
        if len(letters) == 6:
            return letters[:3]
        if letters:
            return letters
    return ""


# ----------------------------------------------------------------------------
# Structural detectors (config-driven)
# ----------------------------------------------------------------------------
def _looks_like_forex(ticker: str, pair: str) -> bool:
    """Two ISO fiat codes back to back, e.g. USDCAD / GBP/JPY."""
    fx = set(getattr(config, "FX_CODES", set()))
    for candidate in (pair, ticker):
        letters = _letters(candidate)
        if len(letters) == 6 and letters[:3] in fx and letters[3:] in fx:
            return True
    return False


def _looks_like_crypto(ticker: str, pair: str, parser_hint: str, match: dict) -> bool:
    blob = f"{ticker} {pair}"
    if match.get("perp") and "PERP" in blob:
        return True
    if match.get("quote_codes"):
        quote = quote_currency(ticker, pair)
        if quote in set(getattr(config, "CRYPTO_QUOTE_CODES", set())):
            return True
    if match.get("parser_hint") and parser_hint == match.get("parser_hint"):
        return True
    if match.get("bases"):
        if _base_token(ticker, pair) in set(getattr(config, "CRYPTO_BASES", set())):
            return True
    return False


def _matches(name: str, spec: dict, ticker: str, pair: str, base: str,
             parser_hint: str) -> bool:
    """Does this asset class's recognition rule fire for the instrument?"""
    match = spec.get("match", {}) or {}

    # Prefix match (metals): XAU* / XAG*
    for prefix in match.get("prefixes", []):
        if base.startswith(prefix.upper()):
            return True

    # Exact ticker list (oil / commodities / stocks)
    tickers = {t.upper() for t in match.get("tickers", [])}
    if tickers and (base in tickers or ticker in tickers or _letters(pair) in tickers):
        return True

    # Structural detectors
    if match.get("forex_codes") and _looks_like_forex(ticker, pair):
        return True
    if (match.get("quote_codes") or match.get("perp")
            or match.get("parser_hint") or match.get("bases")):
        if _looks_like_crypto(ticker, pair, parser_hint, match):
            return True

    return False


# ----------------------------------------------------------------------------
# Public API
# ----------------------------------------------------------------------------
def classify(ticker_or_obj, pair: str = None, parser_hint: str = None) -> str:
    """
    Classify an instrument into a fine asset class using config.ASSET_CLASSES.
    Returns one of the class names, or UNKNOWN if nothing recognises it.

    Tried in config.ASSET_CLASS_ORDER so the most specific rules win and, in
    particular, the structural FOREX check runs BEFORE CRYPTO (so a fiat pair
    like USDCAD is never mistaken for crypto on a 'USDC' substring).
    """
    t, p, hint = _fields(ticker_or_obj)
    if pair is not None:
        p = str(pair).upper().strip()
    if parser_hint is not None:
        hint = str(parser_hint).upper().strip()
    base = _base_token(t, p) or t.replace("/", "")
    base_full = t.replace("/", "")

    order = getattr(config, "ASSET_CLASS_ORDER", list(config.ASSET_CLASSES.keys()))
    for name in order:
        spec = config.ASSET_CLASSES.get(name)
        if not spec:
            continue
        # Try both the parsed base (BTC) and the full base (BTCUSD) for ticker lists.
        if _matches(name, spec, t, p, base, hint) or _matches(
                name, spec, t, p, base_full, hint):
            return name
    return UNKNOWN


def spec(fine_class: str) -> dict:
    """The config spec for a fine class, or {} if not in the registry."""
    return config.ASSET_CLASSES.get(fine_class, {})


def is_known(fine_class: str) -> bool:
    return fine_class in config.ASSET_CLASSES


def is_calibrated(fine_class: str) -> bool:
    """True if the engine has trusted sizing logic for this class."""
    return bool(spec(fine_class).get("calibrated", False))


def ledger_class(fine_class: str) -> str:
    """The value to write to the log's `asset_class` column (back-compat)."""
    return spec(fine_class).get("ledger_class", fine_class)


def display_name(fine_class: str) -> str:
    return spec(fine_class).get("display_name", fine_class.lower())


def slippage(fine_class: str) -> Decimal:
    raw = spec(fine_class).get("slippage", getattr(config, "SLIPPAGE_DEFAULT", "0"))
    try:
        return Decimal(str(raw))
    except (InvalidOperation, ValueError):
        return Decimal("0")


def quote_to_account_rate(quote_ccy: str) -> Decimal:
    """
    Approximate {quote currency -> account currency} rate for FOREX pip value.
    USD is the engine's 1:1 proxy; unknown quotes fall back to the configured
    default (1.0) and are flagged CONFIRM-WITH-BROKER by the sizing code.
    """
    table = getattr(config, "FX_QUOTE_TO_ACCOUNT", {})
    default = getattr(config, "FX_QUOTE_TO_ACCOUNT_DEFAULT", "1.0")
    try:
        return Decimal(str(table.get((quote_ccy or "").upper(), default)))
    except (InvalidOperation, ValueError):
        return Decimal("1.0")


def is_usd_proxy_quote(quote_ccy: str) -> bool:
    """USD-quote pairs are the 'known' case under the engine's USD≈account proxy."""
    return (quote_ccy or "").upper() == "USD"


def slippage_summary_items():
    """[(display_name, slippage_str)] for the calibrated classes (for status.py)."""
    items = []
    order = getattr(config, "ASSET_CLASS_ORDER", list(config.ASSET_CLASSES.keys()))
    for name in order:
        s = config.ASSET_CLASSES.get(name, {})
        if s.get("calibrated"):
            items.append((s.get("display_name", name.lower()), str(s.get("slippage", "0"))))
    return items
