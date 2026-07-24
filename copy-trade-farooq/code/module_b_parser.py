"""
module_b_parser.py — the Parser.

Takes a raw pasted signal message and returns a structured Signal, using an LLM
(Claude) to pull out the numbers. The original message is ALWAYS kept verbatim
in raw_text.

Because a misread stop-loss becomes a real-money mistake later, the parser also
provides an "amber-confirm" step: it shows the operator exactly what it read and
asks for a y/n before the signal is allowed to proceed.
"""

import os
import re
from decimal import Decimal, InvalidOperation

import config
from models import Signal


class ParserError(Exception):
    """Raised when a signal can't be read. Message is operator-facing."""


# The tool we force Claude to call. Numbers come back as STRINGS so we don't
# lose precision on tiny prices like PEPE before turning them into Decimals.
_EXTRACT_TOOL = {
    "name": "record_signal",
    "description": "Record the structured trading signal extracted from the raw message.",
    "input_schema": {
        "type": "object",
        "properties": {
            "ticker": {
                "type": "string",
                "description": "Base ticker, uppercase. e.g. FET, SOL, PEPE, XAUUSD, XAGUSD",
            },
            "pair": {
                "type": "string",
                "description": "Full pair e.g. FET/USDT. For metals use the ticker itself e.g. XAUUSD.",
            },
            "direction": {"type": "string", "enum": ["LONG", "SHORT"]},
            "asset_class": {"type": "string", "enum": ["CRYPTO", "METAL"]},
            "entry_a": {
                "type": "string",
                "description": "One edge of the entry ZONE, exactly as written. Entries are "
                               "often a RANGE like '4323-4315' or '2312 - 2309' (any spacing, "
                               "any order) — put one end here and the other in entry_b.",
            },
            "entry_b": {
                "type": "string",
                "description": "Other edge of the entry zone, exactly as written. "
                               "If only one entry price is given, repeat it here.",
            },
            "stop_loss": {"type": "string", "description": "Stop-loss price, exactly as written."},
            "targets": {
                "type": "array",
                "items": {"type": "string"},
                "description": "All take-profit targets in order, exactly as written.",
            },
        },
        "required": ["ticker", "pair", "direction", "asset_class",
                     "entry_a", "entry_b", "stop_loss", "targets"],
    },
}

_SYSTEM = (
    "You read crypto and metals trading signals and extract their fields precisely. "
    "Copy numbers EXACTLY as written — do not round, reformat, or 'fix' them. "
    "Entries are OFTEN a ZONE/RANGE written as two prices with a hyphen, e.g. "
    "'buy 4323-4315 sl 4295' or 'sell 4269- 4280' or 'now @ 2312 - 2309' — capture "
    "BOTH ends (entry_a and entry_b). 'Gold' means XAUUSD, 'Silver' means XAGUSD. "
    "Metals: XAU*/XAG* are METAL; anything quoted in USDT/USDC is CRYPTO. "
    "Always call the record_signal tool."
)


def _client():
    try:
        import anthropic
    except ImportError:
        raise ParserError(
            "The 'anthropic' library isn't installed.\n"
            "  Fix: open a terminal and run:  pip install anthropic"
        )
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise ParserError(
            "No API key found.\n"
            "  Fix: set ANTHROPIC_API_KEY (see the README for how)."
        )
    return anthropic.Anthropic()


def _to_decimal(raw: str, field_name: str) -> Decimal:
    """Turn a price string from the LLM into an exact Decimal."""
    cleaned = str(raw).replace(",", "").replace("£", "").replace("$", "").strip()
    try:
        return Decimal(cleaned)
    except (InvalidOperation, ValueError):
        raise ParserError(
            f"Couldn't read the {field_name} value '{raw}' as a number. "
            "Please check the original message."
        )


# ============================================================================
# Deterministic ("local") parsing — handles Farouk's real formatting drift
# WITHOUT the LLM, with flexible, case-insensitive regex. It copes with:
#   ASSET      XAUUSD / GOLD / Gold / gold -> XAUUSD ;  SILVER/Silver -> XAGUSD
#   DIRECTION  buy / sell (+ market vs limit: "buy limit", "sell limit", "buy now")
#   ENTRY      "@ 2311", "@2311", "at 2311", "2311", and ranges "2312-2309",
#              "@ 2312 - 2309", any spacing. Range -> keep both ends; primary =
#              the CONSERVATIVE end (BUY->higher, SELL->lower), never the midpoint.
#   SL / TP    lax punctuation: "SL:", "SL-", "SL", "sl", "tp1", "tp1:", "tp1-" …
#
# It only returns a Signal when it confidently reads asset + direction + entry.
# Whether that becomes a clean signal is decided by classify() below — where a
# MANAGEMENT/update message ALWAYS wins (it is never promoted to a new signal),
# and a signal needs a stop too.
# ============================================================================
_PRICE = r"\d[\d,]*(?:\.\d+)?"
_DIR_RE = re.compile(r"\b(buy|long|sell|short)\b", re.I)
# A range: two prices around a hyphen/en-dash, ANY spacing. The lookahead stops
# "100-150 pips" (pip counts, not prices) from being read as an entry zone.
_RANGE_RE = re.compile(r"(" + _PRICE + r")\s*[-–—]\s*(" + _PRICE + r")(?!\s*pip)", re.I)
# SL: keyword then OPTIONAL colon/dash/equals/at and any spacing, then the price.
_STOP_RE = re.compile(r"\b(?:sl|stop[\s-]?loss|stop)\b\s*[:=@\-]?\s*(" + _PRICE + r")", re.I)
# TP markers (tp / tp1 / target / take profit) with the same lax punctuation.
_TARGET_STRIP_RE = re.compile(
    r"\b(?:tp\s*\d?|target\s*\d?|take[\s-]?profit)\b\s*[:=@\-]?\s*" + _PRICE
    + r"(?:[\s,]+" + _PRICE + r")*", re.I)
_TARGET_KW_RE = re.compile(r"\b(?:tp\s*\d?|target\s*\d?|take[\s-]?profit|targets?)\b", re.I)
# Words that are NOT the entry price — stripped before we look for the number, so
# "Sell Limit gold 2345" (price after the asset) and bare "@2311" both work.
_NOISE_RE = re.compile(
    r"\b(?:xauusd|xagusd|xau|xag|gold|silver|buy|sell|long|short|limit|market|"
    r"now|at|entry|enter|zone|order)\b", re.I)


def _num(raw):
    """Decimal from a price token, or None (never raises)."""
    try:
        return Decimal(str(raw).replace(",", "").replace("£", "").replace("$", "").strip())
    except (InvalidOperation, ValueError, AttributeError):
        return None


def _detect_direction(text: str) -> str:
    m = _DIR_RE.search(text or "")
    if not m:
        return ""
    return "LONG" if m.group(1).lower() in ("buy", "long") else "SHORT"


def _detect_order_type(text: str, direction: str) -> str:
    """'limit' if it's a limit order, else 'market' (only meaningful with a direction)."""
    if not direction:
        return ""
    return "limit" if re.search(r"\blimit\b", text or "", re.I) else "market"


def _detect_instrument(text: str):
    """Return (ticker, pair, asset_class) or ('', '', '') if not confident."""
    t = (text or "").upper()
    fx = set(getattr(config, "FX_CODES", set()))
    # Metals — symbol or plain name.
    if re.search(r"\bXAUUSD\b", t) or re.search(r"\bGOLD\b", t) or re.search(r"\bXAU\b", t):
        return "XAUUSD", "XAUUSD", "METAL"
    if re.search(r"\bXAGUSD\b", t) or re.search(r"\bSILVER\b", t) or re.search(r"\bXAG\b", t):
        return "XAGUSD", "XAGUSD", "METAL"
    # Crypto quoted in a stablecoin (with or without a slash).
    m = re.search(r"\b([A-Z]{2,6})\s*/\s*(USDT|USDC|USD)\b", t)
    if m:
        return m.group(1), f"{m.group(1)}/{m.group(2)}", "CRYPTO"
    m = re.search(r"\b([A-Z]{2,6})(USDT|USDC)\b", t)
    if m:
        return m.group(1), f"{m.group(1)}{m.group(2)}", "CRYPTO"
    # Forex: two ISO fiat codes back to back (e.g. EURUSD, GBPJPY).
    for m in re.finditer(r"\b([A-Z]{6})\b", t):
        tok = m.group(1)
        if tok[:3] in fx and tok[3:] in fx:
            return tok, tok, ""
    # A bare XXXUSD pair (e.g. BTCUSD) — let the router classify it.
    m = re.search(r"\b([A-Z]{3,5}USD)\b", t)
    if m:
        return m.group(1), m.group(1), ""
    return "", "", ""


def _extract_stop(text: str):
    m = _STOP_RE.search(text or "")
    return _num(m.group(1)) if m else None


def _extract_targets(text: str):
    m = _TARGET_KW_RE.search(text or "")
    if not m:
        return []
    tail = _STOP_RE.sub(" ", text[m.start():])   # drop any SL number in the tail
    # Remove the TP/target KEYWORD tokens (incl. their index digit) so "tp1" does
    # NOT contribute a bogus "1" target — only the actual prices remain.
    tail = re.sub(r"\b(?:tp|target)\s*\d?\b|\btake[\s-]?profit\b", " ", tail, flags=re.I)
    out = []
    for tok in re.findall(_PRICE, tail):
        d = _num(tok)
        if d is not None and d > 0:
            out.append(d)
    return out


def _extract_zone(text: str):
    """
    Find the entry zone. Returns (low, high) Decimals, or None.

    We remove the SL and TP numbers first, then strip the non-price "noise" words
    (asset names, buy/sell, limit/market, now/at/entry/@ …). Whatever price tokens
    remain are the entry: a hyphen range -> both ends; otherwise the first single
    price. This reads "@2311", "at 2311", "Sell 2345", "Sell Limit gold 2345" and
    "@ 2312 - 2309" alike, with any spacing/punctuation.
    """
    work = _STOP_RE.sub(" ", text or "")     # take the SL number out of the running
    work = _TARGET_STRIP_RE.sub(" ", work)   # and the TP numbers
    work = _NOISE_RE.sub(" ", work)          # and the words that aren't the entry
    work = work.replace("@", " ")

    m = _RANGE_RE.search(work)
    if m:
        a, b = _num(m.group(1)), _num(m.group(2))
        if a is not None and b is not None and a > 0 and b > 0:
            return (min(a, b), max(a, b))
    m2 = re.search(_PRICE, work)
    if m2:
        p = _num(m2.group(0))
        if p is not None and p > 0:
            return (p, p)
    return None


def conservative_entry(direction: str, entry_low: Decimal, entry_high: Decimal) -> Decimal:
    """
    The WORSE fill of the zone — what we honestly assume we'd get filled at:
      BUY/LONG  -> the HIGHER price (you pay more)
      SELL/SHORT-> the LOWER price (you receive less)
    Never the midpoint, so sizing/expectancy is never flattered.
    """
    return entry_high if (direction or "").upper() == "LONG" else entry_low


def parse_locally(raw_text: str):
    """
    Deterministically parse a common one-line signal. Returns a Signal (with both
    zone ends AND a conservative primary_entry) or None if it can't confidently
    read direction + instrument + entry zone. Never calls the API; never raises.
    """
    text = (raw_text or "").strip()
    if not text:
        return None
    direction = _detect_direction(text)
    ticker, pair, asset_class = _detect_instrument(text)
    if not direction or not ticker:
        return None
    zone = _extract_zone(text)
    if zone is None:
        return None
    entry_low, entry_high = zone
    stop = _extract_stop(text)        # may be None — classify() then REVIEWs it
    targets = _extract_targets(text)
    return Signal(
        ticker=ticker,
        pair=pair,
        direction=direction,
        asset_class=asset_class,
        entry_low=entry_low,
        entry_high=entry_high,
        stop_loss=stop,
        targets=targets,
        raw_text=text,
        primary_entry=conservative_entry(direction, entry_low, entry_high),
        order_type=_detect_order_type(text, direction),
    )


# ============================================================================
# Management-message detection + classification
# ============================================================================
# Classification labels (these are what callers/tests check).
CLEAN_SIGNAL = "clean_signal"
COMMENTARY = "commentary"
REVIEW = "REVIEW"

# Phrases that mean this is a RUNNING-TRADE UPDATE / commentary, NOT a new entry.
# If ANY of these appear, the message is commentary — even if it also mentions an
# asset, a price and an SL. Management ALWAYS wins (a trade update is never
# promoted to a fresh signal). Each pattern is deliberately specific so it does
# NOT fire on a genuine entry (e.g. "tp hit" needs "hit"; "move sl" needs "move").
_MGMT_PATTERNS = [
    r"\btp\s*\d*\s*hit\b",                  # "tp hit", "tp1 hit", "tp 1 hit"
    r"\b\d+\s*pips?\b",                     # "100 pips", "50 pip"
    r"\bin\s+profit\b",                     # "in profit", "running in profit"
    r"\brunning\b",                         # "running 50 pips", "still running"
    r"\bmove\s+(?:the\s+)?(?:sl|stop[\s-]?loss|stop)\b",   # "move sl", "move stop loss"
    r"\b(?:sl|stop[\s-]?loss|stop)\s+to\s+(?:entry|break[\s-]?even|be)\b",  # "sl to entry/breakeven"
    r"\bmove\s+to\s+break[\s-]?even\b",
    r"\bbreak[\s-]?even\b",                 # "breakeven" / "break even"
    r"\bclose\s+(?:half|part|partial|the\s+\w+)\b",        # "close half", "close the position"
    r"\btake\s+partial",                    # "take partial(s)"
    r"\bpartial",                           # "partials banked"
    r"\bsecure\s+(?:profit|partial)",       # "secure profit"
    r"\b(?:we|i)\s+(?:have|got|are|'re)\b.{0,30}\bpips?\b",  # "we got X pips"
]
_MGMT_RE = re.compile("|".join(_MGMT_PATTERNS), re.I)


def is_management(text: str) -> bool:
    """True if the message is a running-trade update / commentary (not a new entry)."""
    return bool(_MGMT_RE.search(text or ""))


def _mentions_asset(text: str) -> bool:
    return bool(_detect_instrument(text)[0])


def has_fresh_entry(text: str) -> bool:
    """
    True if the message carries a COMPLETE fresh entry — a direction, an entry
    zone, AND a stop. The asset may be implied/omitted (re-entry posts in a
    single-asset channel often just say "BUY Entry … SL …"), so the asset is NOT
    required here. This is what distinguishes a RE-ENTRY (management language plus
    a real new entry) from pure management chatter.
    """
    return bool(_detect_direction(text)) and _extract_zone(text) is not None \
        and _extract_stop(text) is not None


def classify(text: str) -> str:
    """
    Classify a raw message as a fresh signal, an update, or something to eyeball:

      "commentary"   — PURE management/update chatter, or anything that isn't a
                       signal at all.
      "clean_signal" — asset + direction + entry + STOP, and NO management phrase.
      "REVIEW"       — needs a human look. Two cases:
                         * a RE-ENTRY: management language PLUS a complete fresh
                           signal (direction + entry + stop) — surfaced so a real
                           re-entry isn't missed, but never auto-logged; OR
                         * mentions an asset + numbers but is incomplete (missing
                           the stop or the direction).

    Management still takes priority over CLEAN: a message with a management phrase
    is never auto-promoted to a clean signal — at most it becomes REVIEW.
    """
    text = (text or "").strip()
    if not text:
        return COMMENTARY
    if is_management(text):
        # Pure management -> commentary; a re-entry (management + a complete fresh
        # signal) -> REVIEW so it's surfaced for the human, but never auto-clean.
        return REVIEW if has_fresh_entry(text) else COMMENTARY
    sig = parse_locally(text)               # needs asset + direction + entry
    if sig is not None:
        return CLEAN_SIGNAL if sig.stop_loss is not None else REVIEW
    if _mentions_asset(text) and re.search(r"\d", text):
        return REVIEW
    return COMMENTARY


def parse_signal(raw_text: str) -> Signal:
    """
    Parse a raw pasted message into a Signal. raw_text is preserved verbatim.
    The entry zone is sorted to a true (low, high) on ingest.

    Tries the deterministic local parser FIRST (reliable, free, handles entry
    ranges) and only falls back to the LLM for messages it can't confidently read.
    """
    raw_text = (raw_text or "").strip()
    if not raw_text:
        raise ParserError("Nothing was pasted — there's no signal to read.")

    local = parse_locally(raw_text)
    if local is not None:
        return local
    return parse_with_llm(raw_text)


def parse_with_llm(raw_text: str) -> Signal:
    """The LLM extraction path (used when the deterministic parser isn't sure)."""
    raw_text = (raw_text or "").strip()
    if not raw_text:
        raise ParserError("Nothing was pasted — there's no signal to read.")

    client = _client()

    try:
        resp = client.messages.create(
            model=config.PARSER_MODEL,
            max_tokens=1024,
            system=_SYSTEM,
            tools=[_EXTRACT_TOOL],
            tool_choice={"type": "tool", "name": "record_signal"},
            messages=[{"role": "user", "content": raw_text}],
        )
    except Exception as e:
        raise ParserError(
            f"Couldn't reach the parsing service: {e}\n"
            "  Check your internet connection and that ANTHROPIC_API_KEY is valid."
        )

    tool_block = next((b for b in resp.content if getattr(b, "type", None) == "tool_use"), None)
    if tool_block is None:
        raise ParserError("The parser didn't return structured fields. Try pasting the signal again.")

    data = tool_block.input

    entry_a = _to_decimal(data["entry_a"], "entry")
    entry_b = _to_decimal(data["entry_b"], "entry")
    targets = [_to_decimal(t, "target") for t in data.get("targets", [])]

    entry_low = min(entry_a, entry_b)        # sorted to true (low, high) on ingest
    entry_high = max(entry_a, entry_b)
    direction = str(data["direction"]).upper().strip()

    return Signal(
        ticker=str(data["ticker"]).upper().strip(),
        pair=str(data["pair"]).strip(),
        direction=direction,
        asset_class=str(data["asset_class"]).upper().strip(),
        entry_low=entry_low,
        entry_high=entry_high,
        stop_loss=_to_decimal(data["stop_loss"], "stop-loss"),
        targets=targets,
        raw_text=raw_text,                   # ALWAYS kept verbatim
        primary_entry=conservative_entry(direction, entry_low, entry_high),
    )


def format_for_confirmation(signal: Signal) -> str:
    """A clear, plain readout of what the parser read, for the operator to check."""
    targets = "  ".join(str(t) for t in signal.targets) or "(none)"
    primary = signal.primary_entry
    if primary is None:
        primary = conservative_entry(signal.direction, signal.entry_low, signal.entry_high)
    primary_line = (f"    Primary entry: {primary}   (conservative end — the worse fill, "
                    "used for sizing)\n") if signal.entry_low != signal.entry_high else ""
    return (
        "\n  I read this signal as:\n"
        f"    Ticker      : {signal.ticker}\n"
        f"    Pair        : {signal.pair}\n"
        f"    Direction   : {signal.direction}\n"
        f"    Asset class : {signal.asset_class}\n"
        f"    Entry zone  : {signal.entry_low}  to  {signal.entry_high}\n"
        + primary_line
        + f"    Stop loss   : {signal.stop_loss}\n"
        f"    Targets     : {targets}\n"
    )


def confirm_parsed(signal: Signal) -> bool:
    """
    The amber-confirm step. Show the parsed numbers and require a y/n.
    Returns True only if the operator types 'y'.
    """
    print(format_for_confirmation(signal))
    print("  ** Check the STOP-LOSS especially — a wrong stop is a real-money mistake later.")
    answer = input("  Are these numbers correct? (y/n): ").strip().lower()
    return answer in ("y", "yes")
