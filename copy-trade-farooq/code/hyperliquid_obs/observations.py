"""
H1 — observation models for L2 order-book snapshots and trade ticks.

Every observation carries BOTH an exchange timestamp (from the venue payload) and a
local-receipt timestamp (injected, never wall-clock-read inside the classifier — so replay
is deterministic). Each observation gets exactly ONE deterministic primary status; coexisting
boolean flags (duplicate / stale / out_of_order) are recorded separately.

An admissible observation is market CONTEXT ONLY. It is never proof of a fill, an entry, an
exit, liquidity you could take, or anyone's position. This package only watches.

Hyperliquid public WS payloads:
  l2Book : {"coin","time": ms, "levels": [ [bid...], [ask...] ]}, level = {"px","sz","n"}
  trades : [ {"coin","side":"B"/"A","px","sz","time": ms,"hash","tid"}, ... ]
"""
from __future__ import annotations
from dataclasses import dataclass, field

BOOK_STATUSES = (
    "COMPLETE_ADMISSIBLE", "EMPTY_BOOK", "ONE_SIDED", "CROSSED_BOOK", "INVALID_VALUE",
    "INVALID_TIMESTAMP", "DUPLICATE", "STALE", "OUT_OF_ORDER",
    "SYMBOL_UNVERIFIED", "ENVIRONMENT_UNVERIFIED", "NOT_CONNECTED",
)
TRADE_STATUSES = (
    "TRADE_ADMISSIBLE", "INVALID_VALUE", "INVALID_TIMESTAMP", "DUPLICATE", "OUT_OF_ORDER",
    "SYMBOL_UNVERIFIED", "ENVIRONMENT_UNVERIFIED", "NOT_CONNECTED",
)
BOOK_QUARANTINE = ("EMPTY_BOOK", "ONE_SIDED", "CROSSED_BOOK", "INVALID_VALUE",
                   "INVALID_TIMESTAMP", "STALE", "OUT_OF_ORDER")


@dataclass
class ObsContext:
    connected: bool = False
    env_verified_testnet: bool = False
    symbol_verified: bool = False
    max_age_ms: int = 5000


@dataclass
class BookSnapshot:
    coin: str
    bids: list                 # list of (px, sz) or {"px","sz","n"}
    asks: list
    exch_time_ms: object = None
    local_recv_ms: object = None


@dataclass
class TradeTick:
    coin: str
    side: object
    px: object
    sz: object
    exch_time_ms: object = None
    local_recv_ms: object = None
    tid: object = None
    txhash: object = None


def _fnum(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def _ipx(level):
    """Extract px from a level given as dict {"px":..} or a [px, sz, ..] sequence."""
    if isinstance(level, dict):
        return _fnum(level.get("px"))
    if isinstance(level, (list, tuple)) and level:
        return _fnum(level[0])
    return None


def _int_ms(x):
    try:
        return int(x)
    except (TypeError, ValueError):
        return None


def classify_book(snap: BookSnapshot, prev: BookSnapshot, ctx: ObsContext):
    """Return (status, flags, derived). Deterministic precedence."""
    flags = {"duplicate": False, "stale": False, "out_of_order": False}
    derived = {"best_bid": None, "best_ask": None, "spread": None, "mid": None,
               "n_bids": 0, "n_asks": 0}

    if not ctx.connected:
        return "NOT_CONNECTED", flags, derived
    if not ctx.env_verified_testnet:
        return "ENVIRONMENT_UNVERIFIED", flags, derived
    if not ctx.symbol_verified:
        return "SYMBOL_UNVERIFIED", flags, derived

    bids = list(snap.bids or [])
    asks = list(snap.asks or [])
    derived["n_bids"], derived["n_asks"] = len(bids), len(asks)

    if not bids and not asks:
        return "EMPTY_BOOK", flags, derived
    if not bids or not asks:
        # record whichever side exists, but it is non-admissible context
        if bids:
            derived["best_bid"] = _ipx(bids[0])
        if asks:
            derived["best_ask"] = _ipx(asks[0])
        return "ONE_SIDED", flags, derived

    best_bid, best_ask = _ipx(bids[0]), _ipx(asks[0])
    derived["best_bid"], derived["best_ask"] = best_bid, best_ask
    if best_bid is None or best_ask is None or best_bid <= 0 or best_ask <= 0:
        return "INVALID_VALUE", flags, derived
    if best_ask < best_bid:
        return "CROSSED_BOOK", flags, derived

    derived["spread"] = best_ask - best_bid
    derived["mid"] = (best_ask + best_bid) / 2.0

    et, lt = _int_ms(snap.exch_time_ms), _int_ms(snap.local_recv_ms)
    if et is None or lt is None:
        return "INVALID_TIMESTAMP", flags, derived

    if prev is not None:
        pet = _int_ms(prev.exch_time_ms)
        if pet is not None and et < pet:
            flags["out_of_order"] = True
            return "OUT_OF_ORDER", flags, derived
        if (et == pet and _ipx((prev.bids or [None])[0]) == best_bid
                and _ipx((prev.asks or [None])[0]) == best_ask):
            flags["duplicate"] = True
            return "DUPLICATE", flags, derived

    if (lt - et) > ctx.max_age_ms:
        flags["stale"] = True
        return "STALE", flags, derived

    return "COMPLETE_ADMISSIBLE", flags, derived


def classify_trade(t: TradeTick, ctx: ObsContext, seen_tids=None, last_trade_time_ms=None):
    """Return (status, flags). Dedup by tid; out-of-order by exchange time."""
    flags = {"duplicate": False, "out_of_order": False}
    if not ctx.connected:
        return "NOT_CONNECTED", flags
    if not ctx.env_verified_testnet:
        return "ENVIRONMENT_UNVERIFIED", flags
    if not ctx.symbol_verified:
        return "SYMBOL_UNVERIFIED", flags

    px, sz = _fnum(t.px), _fnum(t.sz)
    if px is None or px <= 0 or sz is None or sz <= 0:
        return "INVALID_VALUE", flags
    et = _int_ms(t.exch_time_ms)
    if et is None:
        return "INVALID_TIMESTAMP", flags

    if seen_tids is not None and t.tid is not None and t.tid in seen_tids:
        flags["duplicate"] = True
        return "DUPLICATE", flags
    if last_trade_time_ms is not None and et < last_trade_time_ms:
        flags["out_of_order"] = True
        return "OUT_OF_ORDER", flags

    return "TRADE_ADMISSIBLE", flags
