"""
Match a confirmed update to its parent signal's ACTUAL broker position/order. Never uses symbol
alone. Refuses ambiguous matches. Determines account type. Provides worst/best-leg ordering for
multi-leg (HEDGED) accounts; a single VWAP / NETTED position makes CLOSE_WORST_LEG ambiguous.
"""
from __future__ import annotations

import config as CFG
from models import MatchResult

TIME_WINDOW_MS = 6 * 3600 * 1000        # a same-thread management window


def detect_account_type(raw):
    r = str(raw).upper()
    if "HEDG" in r:
        return "HEDGED"
    if "NET" in r:
        return "NETTED"
    if "SPREAD" in r:
        return "SPREAD_BETTING"
    return "UNKNOWN"


def _matches(obj, *, signal_id, symbol, direction):
    keys = []
    label_hit = signal_id and signal_id in (getattr(obj, "label", "") or "")
    if label_hit:
        keys.append("label_signal_id")
    if (getattr(obj, "symbol", "") or "").upper() == str(symbol).upper():
        keys.append("symbol")
    if (getattr(obj, "direction", "") or "").upper() == str(direction).upper():
        keys.append("direction")
    return keys


def match_position(*, signal_id, account_id, symbol, direction, positions, orders=None, now_ms=0):
    """Returns MatchResult. Requires MORE than symbol: the parent signal id must be present in the
    position label (primary), or symbol+direction+time as a weaker fallback that stays AMBIGUOUS if
    more than one candidate qualifies. Symbol-alone never selects a position."""
    cands = []
    for pos in (positions or []):
        keys = _matches(pos, signal_id=signal_id, symbol=symbol, direction=direction)
        if "symbol" not in keys:
            continue                                    # different instrument
        # symbol alone is NOT enough: need label OR (direction + time)
        time_ok = pos.open_time_ms is None or abs(now_ms - pos.open_time_ms) <= TIME_WINDOW_MS
        strong = "label_signal_id" in keys
        weak = ("direction" in keys) and time_ok
        if strong or weak:
            cands.append((pos, keys, strong))
    if not cands:
        return MatchResult("NO_MATCH", None, [], "NO_POSITION_FOR_SIGNAL")
    strong_cands = [c for c in cands if c[2]]
    if len(strong_cands) == 1:
        c = strong_cands[0]
        return MatchResult("CONFIRMED", c[0], [x[0] for x in cands], "MATCHED_BY_SIGNAL_LABEL", c[1])
    if len(strong_cands) > 1:
        # multiple positions carry the same signal label -> identifiable legs (HEDGED multi-leg)
        return MatchResult("MULTI_LEG", None, [x[0] for x in strong_cands],
                           "MULTIPLE_IDENTIFIABLE_LEGS", ["label_signal_id"])
    # no strong match; only weak symbol+direction+time candidates
    if len(cands) == 1:
        return MatchResult("AMBIGUOUS", None, [cands[0][0]],
                           "WEAK_MATCH_NO_SIGNAL_LABEL", cands[0][1])
    return MatchResult("AMBIGUOUS", None, [x[0] for x in cands], "MULTIPLE_WEAK_CANDIDATES")


def order_legs_worst_first(legs, direction):
    """SELL: lower entry = worse. BUY: higher entry = worse. Returns legs ordered worst->best."""
    d = str(direction).upper()
    if d == "SELL":
        return sorted(legs, key=lambda p: p.price)          # lowest entry worst
    return sorted(legs, key=lambda p: -p.price)             # BUY: highest entry worst


def close_worst_leg_selection(legs, direction, account_type):
    """CLOSE_WORST_LEG only makes sense with multiple identifiable legs; a single VWAP/NETTED position
    is AMBIGUOUS and must NOT be reinterpreted as a percentage close."""
    if account_type == "NETTED" or len(legs) <= 1:
        return {"status": "AMBIGUOUS", "reason": "SINGLE_VWAP_OR_NETTED_ACCOUNT",
                "candidates": [p.position_id for p in legs]}
    ordered = order_legs_worst_first(legs, direction)
    return {"status": "IDENTIFIED", "worst": ordered[0].position_id, "best": ordered[-1].position_id,
            "ordered_worst_first": [p.position_id for p in ordered],
            "candidates": [{"position_id": p.position_id, "entry": p.price} for p in ordered]}
