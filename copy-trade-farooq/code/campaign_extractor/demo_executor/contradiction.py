"""
Contradiction / internal-consistency detection for a parsed Farouk intake. Any contradiction blocks
execution (fail closed). Reason codes are explicit — never a vague 'invalid'.
"""
from __future__ import annotations

# reason codes
CONTRADICTORY_DIRECTION = "CONTRADICTORY_DIRECTION"
INVALID_STOP_SIDE = "INVALID_STOP_SIDE"
MALFORMED_ENTRY_ZONE = "MALFORMED_ENTRY_ZONE"
MULTIPLE_INSTRUMENTS = "MULTIPLE_INSTRUMENTS"
MULTIPLE_DIRECTIONS = "MULTIPLE_DIRECTIONS"
CONFLICTING_STOP_LOSS = "CONFLICTING_STOP_LOSS"
CONFLICTING_ORDER_TYPE = "CONFLICTING_ORDER_TYPE"
MIXED_INTENT_REQUIRES_REVIEW = "MIXED_INTENT_REQUIRES_REVIEW"
UNMATCHED_TRADE_UPDATE = "UNMATCHED_TRADE_UPDATE"
MATERIAL_OCR_CORRECTION_UNCONFIRMED = "MATERIAL_OCR_CORRECTION_UNCONFIRMED"


def detect(*, direction, entry_low, entry_high, stop, order_type=None, instruments=None,
           directions=None, stops=None, order_types=None, has_result_card=False,
           has_new_signal_wording=False, has_cancellation=False, has_new_entry=False,
           is_trade_update=False, matched_position=None, material_ocr_unconfirmed=False):
    """Returns a sorted list of contradiction reason codes (empty => consistent)."""
    b = set()
    instruments = [i for i in (instruments or []) if i]
    directions = [d for d in (directions or []) if d]
    stops = [s for s in (stops or []) if s is not None]
    order_types = [o for o in (order_types or []) if o]

    if len({i.upper() for i in instruments}) > 1:
        b.add(MULTIPLE_INSTRUMENTS)
    if len({d.upper() for d in directions}) > 1:
        b.add(MULTIPLE_DIRECTIONS); b.add(CONTRADICTORY_DIRECTION)
    if len({round(s, 5) for s in stops}) > 1:
        b.add(CONFLICTING_STOP_LOSS)
    if len({o.upper() for o in order_types}) > 1:
        b.add(CONFLICTING_ORDER_TYPE)

    # malformed / reversed zone
    if entry_low is not None and entry_high is not None:
        if entry_low > entry_high:
            b.add(MALFORMED_ENTRY_ZONE)

    # stop side vs direction (evaluated against the near zone bound)
    if direction and stop is not None and (entry_low is not None or entry_high is not None):
        lo = entry_low if entry_low is not None else entry_high
        hi = entry_high if entry_high is not None else entry_low
        d = direction.upper()
        if d == "BUY" and stop >= lo:          # a BUY stop-loss must sit BELOW the entry
            b.add(INVALID_STOP_SIDE)
        if d == "SELL" and stop <= hi:         # a SELL stop-loss must sit ABOVE the entry
            b.add(INVALID_STOP_SIDE)

    # mixed intents
    if has_result_card and has_new_signal_wording:
        b.add(MIXED_INTENT_REQUIRES_REVIEW)
    if has_cancellation and has_new_entry:
        b.add(MIXED_INTENT_REQUIRES_REVIEW)

    # a trade update with no uniquely matched broker position/order
    if is_trade_update and matched_position not in ("VERIFIED",):
        b.add(UNMATCHED_TRADE_UPDATE)

    if material_ocr_unconfirmed:
        b.add(MATERIAL_OCR_CORRECTION_UNCONFIRMED)

    return sorted(b)
