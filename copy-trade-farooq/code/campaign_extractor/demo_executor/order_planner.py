"""
Pending-order planning (MVP: pending orders only, NO market orders). Chooses a valid pending entry
inside the confirmed zone, derives LIMIT/STOP, and validates side / distance / freshness / market.
"""
from __future__ import annotations

import config as CFG
from models import OrderPlan


def _now_ms(now_ms):
    return now_ms


def plan_order(*, direction, entry_low, entry_high, stop, quote, symbol, manual_entry=None,
               now_ms=0, signal_confirmed_at_ms=None):
    d = str(direction).upper()
    bid, ask = quote.bid, quote.ask
    zlo, zhi = min(entry_low, entry_high), max(entry_low, entry_high)
    base = OrderPlan(False, "", None, None, zlo, zhi, bid, ask)

    # freshness / market gates first
    if not symbol.enabled:
        base.reason = "SYMBOL_DISABLED"; return base
    if not symbol.market_open:
        base.reason = "MARKET_CLOSED"; return base
    if (now_ms - quote.ts_ms) > CFG.QUOTE_STALE_MS:
        base.reason = "STALE_QUOTE"; return base
    if signal_confirmed_at_ms is not None and (now_ms - signal_confirmed_at_ms) > CFG.SIGNAL_STALE_SECONDS * 1000:
        base.reason = "STALE_SIGNAL"; return base
    if d not in ("BUY", "SELL"):
        base.reason = "UNKNOWN_DIRECTION"; return base
    if stop is None:
        base.reason = "MISSING_STOP"; return base

    ref = ask if d == "BUY" else bid                     # BUY fills at ask, SELL at bid

    # choose entry
    if manual_entry is not None:
        if not (zlo <= float(manual_entry) <= zhi):
            base.reason = "MANUAL_ENTRY_OUTSIDE_ZONE"; return base
        entry = float(manual_entry); sel = "manual override inside zone"
    elif ref < zlo:
        entry, sel = zlo, "price below zone -> nearest zone boundary (low)"
    elif ref > zhi:
        entry, sel = zhi, "price above zone -> nearest zone boundary (high)"
    else:
        # inside zone -> nearest boundary that yields a valid pending order (entry != ref)
        cand = sorted([zlo, zhi], key=lambda b: abs(b - ref))
        entry = next((b for b in cand if b != ref), None)
        if entry is None:
            base.reason = "NO_VALID_PENDING_PRICE"; return base
        sel = "price inside zone -> nearest boundary giving a valid pending order"

    # order type from entry vs current price
    if d == "BUY":
        otype = "BUY_LIMIT" if entry < ask else ("BUY_STOP" if entry > ask else None)
    else:
        otype = "SELL_LIMIT" if entry > bid else ("SELL_STOP" if entry < bid else None)
    if otype is None:
        base.reason = "NO_VALID_PENDING_PRICE"; return base

    # stop on the correct side
    if d == "BUY" and float(stop) >= entry:
        base.reason = "STOP_WRONG_SIDE"; return base
    if d == "SELL" and float(stop) <= entry:
        base.reason = "STOP_WRONG_SIDE"; return base

    # entry inside zone (guard against boundary rounding)
    if not (zlo <= entry <= zhi):
        base.reason = "ENTRY_OUTSIDE_ZONE"; return base

    # minimum pending-order distance from current price
    dist_points = abs(entry - ref) / symbol.point
    if dist_points < symbol.min_stop_distance_points:
        base.reason = "MIN_DISTANCE_VIOLATION"; return base

    return OrderPlan(True, "OK", otype, round(entry, symbol.digits), zlo, zhi, bid, ask, sel)
