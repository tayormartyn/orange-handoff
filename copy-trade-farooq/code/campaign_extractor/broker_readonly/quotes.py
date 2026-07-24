"""
Brick 3 — quote status model + admissible-quote definition.

Each quote receives exactly ONE deterministic primary status; coexisting boolean flags
are recorded separately. A COMPLETE_ADMISSIBLE quote is still market CONTEXT ONLY — it is
never proof of a fill, entry, exit, liquidity, a subscriber entry, or a provider entry.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime

PRIMARY_STATUSES = (
    "COMPLETE_ADMISSIBLE", "BID_ONLY", "ASK_ONLY", "DUPLICATE", "STALE", "OUT_OF_ORDER",
    "INVALID_CROSSED_MARKET", "INVALID_VALUE", "SYMBOL_UNVERIFIED", "ENVIRONMENT_UNVERIFIED",
    "BROKER_NOT_CONNECTED", "AUTH_NOT_AVAILABLE",
)


@dataclass
class QuoteContext:
    connected: bool = False
    auth_ready: bool = False
    env_verified_demo: bool = False     # demo env AND demo account both verified
    symbol_verified: bool = False
    max_age_ms: int = 5000


@dataclass
class RawQuote:
    symbol: str
    bid: object
    ask: object
    broker_ts: object = None            # ISO-8601 UTC string
    local_ts: object = None             # ISO-8601 UTC string
    seq: object = None


def _num_pos(x) -> bool:
    try:
        return float(x) > 0
    except (TypeError, ValueError):
        return False


def _parse(ts):
    try:
        return datetime.fromisoformat(str(ts))
    except (TypeError, ValueError):
        return None


def classify(q: RawQuote, prev: RawQuote, ctx: QuoteContext):
    """Return (primary_status, flags_dict). Deterministic precedence."""
    flags = {"duplicate": False, "stale": False, "out_of_order": False}

    # 1. connection / auth / environment / symbol gates (in order)
    if not ctx.connected:
        return "BROKER_NOT_CONNECTED", flags
    if not ctx.auth_ready:
        return "AUTH_NOT_AVAILABLE", flags
    if not ctx.env_verified_demo:
        return "ENVIRONMENT_UNVERIFIED", flags
    if not ctx.symbol_verified:
        return "SYMBOL_UNVERIFIED", flags

    bid_present = q.bid is not None
    ask_present = q.ask is not None

    # 2. value validity (present but non-numeric / non-positive -> invalid)
    if (bid_present and not _num_pos(q.bid)) or (ask_present and not _num_pos(q.ask)):
        return "INVALID_VALUE", flags
    if not bid_present and not ask_present:
        return "INVALID_VALUE", flags

    # 3. one-sided
    if bid_present and not ask_present:
        return "BID_ONLY", flags
    if ask_present and not bid_present:
        return "ASK_ONLY", flags

    # both present & positive
    # 4. crossed market
    if float(q.ask) < float(q.bid):
        return "INVALID_CROSSED_MARKET", flags

    # 5. timestamp validity (malformed -> invalid)
    bt, lt = _parse(q.broker_ts), _parse(q.local_ts)
    if bt is None or lt is None:
        return "INVALID_VALUE", flags

    # 6. chronology / duplicate (relative to previous admissible-candidate quote)
    if prev is not None:
        pbt = _parse(prev.broker_ts)
        if pbt is not None and bt < pbt:
            flags["out_of_order"] = True
            return "OUT_OF_ORDER", flags
        if (q.bid == prev.bid and q.ask == prev.ask and q.broker_ts == prev.broker_ts):
            flags["duplicate"] = True
            return "DUPLICATE", flags

    # 7. staleness (age = local receipt - broker timestamp)
    age_ms = (lt - bt).total_seconds() * 1000.0
    if age_ms > ctx.max_age_ms:
        flags["stale"] = True
        return "STALE", flags

    # 8. all admissibility conditions met
    return "COMPLETE_ADMISSIBLE", flags
