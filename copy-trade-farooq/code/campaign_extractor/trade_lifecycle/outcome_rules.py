"""
Outcome rules. BROKER_EXECUTION_EVIDENCE is authoritative for Martyn's demo result. Provider wording
and market-path touches never assert a broker fill or a realised result. R and realised P&L are only
produced when the underlying values are actually known — otherwise a blocker is recorded, never a
guess. Move-to-breakeven uses the actual broker VWAP once a demo position exists.
"""
from __future__ import annotations

BE_TOL = 0.10          # price tolerance for "at breakeven / at a level"


def _close(a, b):
    return a is not None and b is not None and abs(a - b) <= BE_TOL


def _r_multiple(signal, entry, exit_price, blockers):
    if entry is None or exit_price is None or signal.stop is None:
        blockers.append("R_UNAVAILABLE_MISSING_ENTRY_EXIT_OR_STOP")
        return None
    risk = abs(entry - signal.stop)
    if risk <= 0:
        blockers.append("R_UNAVAILABLE_ZERO_RISK")
        return None
    reward = (exit_price - entry) if (signal.direction or "BUY").upper() == "BUY" else (entry - exit_price)
    return round(reward / risk, 3)


def determine_outcome(*, signal, broker_events, provider_only=False):
    """Returns (state, outcome, realised_pnl, r_multiple, blockers)."""
    blockers = []
    be = list(broker_events or [])

    # rules 5/6/7: provider wording / price touch alone -> no broker execution asserted
    if not be:
        return ("NO_BROKER_EXECUTION",
                "PROVIDER_INSTRUCTION_ONLY" if provider_only else None,
                None, None, ["NO_BROKER_EXECUTION_EVIDENCE"])

    fill = next((e for e in be if e.kind == "ORDER_FILLED"), None)
    placed = any(e.kind == "ORDER_PLACED" for e in be)

    # rule 10: pending order that never filled -> not a win/loss
    if placed and fill is None:
        return ("MISSED_NOT_ENTERED", "MISSED_NOT_ENTERED", None, None, ["PENDING_ORDER_NEVER_FILLED"])
    if fill is None:
        return ("NO_BROKER_EXECUTION", None, None, None, ["NO_BROKER_FILL"])

    entry_vwap = fill.vwap_price                        # rule 9: breakeven is measured vs broker VWAP
    partials = [e for e in be if e.kind == "PARTIAL_CLOSE"]
    partial_confirmed = len(partials) > 0
    partial_vol_known = all(p.closed_volume_raw is not None for p in partials) if partials else True
    moved_to_be = any(_close(e.stop_price, entry_vwap) for e in be if e.kind == "SL_AMENDED")

    closes = [e for e in be if e.kind in ("POSITION_CLOSED", "STOP_HIT", "TARGET_HIT")]
    realised = None
    rp = [e.realised_pnl for e in be if e.realised_pnl is not None]
    if rp:
        realised = round(sum(rp), 2)

    if not closes:
        return (("RUNNER_OPEN" if partial_confirmed else "OPEN"), "OPEN_UNRESOLVED",
                realised, None, blockers + ["POSITION_STILL_OPEN"])

    final = closes[-1]
    hit_price = final.stop_price if final.stop_price is not None else final.vwap_price
    is_be = _close(hit_price, entry_vwap) or moved_to_be
    is_orig_stop = _close(hit_price, signal.stop)

    # rule 1: original stop hit before any confirmed profit -> loss
    if final.kind == "STOP_HIT" and is_orig_stop and not partial_confirmed:
        return ("ORIGINAL_STOP_HIT", "CLOSED_LOSS", realised,
                _r_multiple(signal, entry_vwap, hit_price, blockers), blockers)

    # rule 3: confirmed partial profit + runner stopped at breakeven -> managed profit
    if partial_confirmed and final.kind == "STOP_HIT" and is_be:
        if not partial_vol_known:                       # rule 4 dominates when volume unknown
            return ("CLOSED_MANAGED_PROFIT", "CLOSED_PROFIT_R_UNKNOWN", realised, None,
                    blockers + ["PARTIAL_CLOSE_VOLUME_UNKNOWN"])
        return ("CLOSED_MANAGED_PROFIT", "CLOSED_MANAGED_PROFIT", realised,
                _r_multiple(signal, entry_vwap, hit_price, blockers), blockers)

    # rule 2: stop moved to breakeven and hit, no confirmed partial -> breakeven
    if final.kind == "STOP_HIT" and is_be and not partial_confirmed:
        return ("BREAKEVEN_STOP_HIT", "CLOSED_BREAKEVEN", realised, 0.0, blockers)

    # rule 4: partial confirmed but exact closed volume unknown -> R unknown
    if partial_confirmed and not partial_vol_known:
        return ("FULL_CLOSE_CONFIRMED", "CLOSED_PROFIT_R_UNKNOWN", realised, None,
                blockers + ["PARTIAL_CLOSE_VOLUME_UNKNOWN"])

    # target / profitable close
    if final.kind == "TARGET_HIT" or (realised is not None and realised > 0):
        state = "TARGET_HIT" if final.kind == "TARGET_HIT" else "FULL_CLOSE_CONFIRMED"
        return (state, "CLOSED_WIN", realised, _r_multiple(signal, entry_vwap, hit_price, blockers), blockers)

    return ("FULL_CLOSE_CONFIRMED", "OPEN_UNRESOLVED", realised, None, blockers + ["UNCLASSIFIED_CLOSE"])
