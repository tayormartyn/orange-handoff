"""
Link a confirmed TRADE_UPDATE / TRADE_RESULT to its parent SIGNAL. Priority: explicit approved link >
signal-id in order/position metadata > broker order/position id > heuristic (instrument AND direction
AND provider AND chronology). SYMBOL ALONE NEVER selects a parent. Anything ambiguous (more than one
candidate) stays AMBIGUOUS/UNLINKED and blocks automatic lifecycle advancement.
"""
from __future__ import annotations

from lc_models import (LinkResult, LINK_LINKED, LINK_UNLINKED, LINK_AMBIGUOUS)


def link_child(child, signals, broker_map=None):
    """signals: iterable[SignalRef]. broker_map: {broker_order_id|broker_position_id: signal_id}."""
    by_id = {s.signal_id: s for s in signals}
    broker_map = broker_map or {}

    # 1. explicit approved human link — if set, it is authoritative: it links ONLY to that parent and
    #    never heuristically falls through to a different signal.
    if child.explicit_parent_signal_id:
        if child.explicit_parent_signal_id in by_id:
            return LinkResult(LINK_LINKED, child.explicit_parent_signal_id, "EXPLICIT_APPROVED_LINK")
        return LinkResult(LINK_UNLINKED, None, None, "EXPLICIT_PARENT_NOT_IN_SET")

    # 2. signal id embedded in order/position metadata
    if child.signal_id_in_metadata and child.signal_id_in_metadata in by_id:
        return LinkResult(LINK_LINKED, child.signal_id_in_metadata, "SIGNAL_ID_IN_METADATA")

    # 3. broker order / position id
    for bid in (child.broker_order_id, child.broker_position_id):
        if bid and broker_map.get(bid) in by_id:
            return LinkResult(LINK_LINKED, broker_map[bid], "BROKER_ID")

    # 4. heuristic — requires instrument AND direction AND provider AND chronology (all present+equal).
    #    Instrument alone can never select (direction+provider must corroborate).
    cands = []
    for s in signals:
        if not child.instrument or not s.instrument:
            continue
        if s.instrument.upper() != child.instrument.upper():
            continue
        dir_ok = bool(child.direction and s.direction and child.direction == s.direction)
        prov_ok = bool(child.provider and s.provider and child.provider == s.provider)
        chron_ok = (s.ts_ms is None or child.ts_ms is None or s.ts_ms <= child.ts_ms)
        if dir_ok and prov_ok and chron_ok:
            cands.append(s.signal_id)

    if len(cands) == 1:
        return LinkResult(LINK_LINKED, cands[0], "HEURISTIC_INSTRUMENT_DIRECTION_PROVIDER_CHRONO")
    if len(cands) > 1:
        return LinkResult(LINK_AMBIGUOUS, None, None, "MULTIPLE_CANDIDATES", tuple(cands))
    # nothing corroborated beyond (at most) the symbol
    return LinkResult(LINK_UNLINKED, None, None, "SYMBOL_ALONE_OR_NO_MATCH")
