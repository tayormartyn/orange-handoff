"""
Entry-zone and market-path validation for a pending LIMIT/STOP entry. Uses a FRESH broker quote and
the correct bid/ask for the intended order relationship — never the vague 'price outside the zone'.
Fails CLOSED when required quote-path evidence is missing. Never reinterprets a missed LIMIT as a STOP
(or vice versa) and never converts a missed pending entry into a market order.
"""
from __future__ import annotations

import config as CFG

# reason codes
QUOTE_STALE = "QUOTE_STALE"
WOULD_CROSS = "PENDING_ORDER_WOULD_CROSS_MARKET"
ENTRY_PASSED = "ENTRY_ALREADY_PASSED"
ZONE_TOUCHED = "ZONE_ALREADY_TOUCHED"
ZONE_TRAVERSED = "ZONE_ALREADY_TRAVERSED"
QUOTE_PATH_UNVERIFIED = "QUOTE_PATH_UNVERIFIED"
SPREAD_EXCEEDED = "SPREAD_LIMIT_EXCEEDED"


def _order_type(direction, entry, ask, bid):
    """Determine LIMIT vs STOP from where entry sits relative to the market (deterministic)."""
    d = direction.upper()
    if d == "BUY":
        return "BUY_LIMIT" if entry < ask else "BUY_STOP"
    return "SELL_LIMIT" if entry > bid else "SELL_STOP"


def evaluate(*, direction, order_type, entry_low, entry_high, quote, now_ms, provider_ts_ms,
             quote_path=None, require_quote_path=True, max_spread=None, quote_stale_ms=None):
    """Returns {ok, blockers[], evidence}. quote has .bid/.ask/.ts_ms. quote_path is a list of
    {'bid','ask','ts_ms'} since the provider timestamp."""
    blockers = []
    max_spread = CFG.MAX_SPREAD_PRICE if max_spread is None else max_spread
    stale_ms = CFG.QUOTE_STALE_MS if quote_stale_ms is None else quote_stale_ms
    lo, hi = min(entry_low, entry_high), max(entry_low, entry_high)
    d = direction.upper()
    ev = {"order_type": order_type, "entry_zone": [lo, hi], "bid": quote.bid, "ask": quote.ask}

    # fresh quote + spread
    if now_ms - quote.ts_ms > stale_ms:
        blockers.append(QUOTE_STALE)
    spread = quote.ask - quote.bid
    ev["spread"] = round(spread, 3)
    if spread > max_spread:
        blockers.append(SPREAD_EXCEEDED)

    # marketable / already-passed, evaluated with the correct side per order type
    ot = (order_type or _order_type(d, (lo + hi) / 2, quote.ask, quote.bid)).upper()
    ev["evaluated_order_type"] = ot
    if ot == "BUY_LIMIT":       # buy below market; fills when ask <= entry(hi)
        if quote.ask <= hi:
            blockers.append(WOULD_CROSS)
        if quote.ask < lo:
            blockers.append(ENTRY_PASSED)
    elif ot == "SELL_LIMIT":    # sell above market; fills when bid >= entry(lo)
        if quote.bid >= lo:
            blockers.append(WOULD_CROSS)
        if quote.bid > hi:
            blockers.append(ENTRY_PASSED)
    elif ot == "BUY_STOP":      # buy above market; fills when ask >= entry(lo)
        if quote.ask >= lo:
            blockers.append(WOULD_CROSS)
    elif ot == "SELL_STOP":     # sell below market; fills when bid <= entry(hi)
        if quote.bid <= hi:
            blockers.append(WOULD_CROSS)

    # quote-path since provider timestamp: was the zone touched / traversed?
    path = [q for q in (quote_path or []) if q.get("ts_ms") is None or provider_ts_ms is None
            or q["ts_ms"] >= provider_ts_ms]
    if require_quote_path and not path:
        blockers.append(QUOTE_PATH_UNVERIFIED)           # fail CLOSED — no evidence
    else:
        touched = any(min(q["bid"], q["ask"]) <= hi and max(q["bid"], q["ask"]) >= lo for q in path)
        below = any(max(q["bid"], q["ask"]) < lo for q in path)
        above = any(min(q["bid"], q["ask"]) > hi for q in path)
        if touched:
            blockers.append(ZONE_TOUCHED)
        if below and above:
            blockers.append(ZONE_TRAVERSED)
        ev["path_points"] = len(path)

    ev["blockers"] = sorted(set(blockers))
    return {"ok": not blockers, "blockers": ev["blockers"], "evidence": ev}
