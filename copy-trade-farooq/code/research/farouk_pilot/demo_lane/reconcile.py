"""Reconciliation policy (correction 8) + F2 close-only closure. Never opens/increases/reverses;
never exceeds owned quantity; never touches unknown."""


class HaltNoTouch(Exception):
    pass


def reconcile(adapter, owned_position_ids):
    """Known Orange-owned mismatch -> caller cancels/flattens owned + alarm + halt.
    Unknown broker order/position -> alarm + halt + NO TOUCH."""
    broker_positions = set(adapter.list_positions().keys())
    owned = set(owned_position_ids)
    unknown = broker_positions - owned
    if unknown:
        raise HaltNoTouch(f"unknown broker position(s) {sorted(unknown)} — NO TOUCH, halt")
    return {"owned_present": sorted(broker_positions & owned)}


def risk_reducing_close(adapter, position_id, volume, owned_position_ids):
    """F2: close permitted SOLELY to reduce/close a positively-identified Orange-owned position."""
    if position_id not in owned_position_ids:
        raise HaltNoTouch(f"{position_id} not Orange-owned — no touch")
    pos = adapter.list_positions().get(position_id)
    if pos is None:
        raise HaltNoTouch(f"{position_id} not present")
    if volume > pos["volume"]:
        raise ValueError("excessive close quantity rejected")   # never exceed owned
    return adapter.close_position(position_id, volume, owner_check="ORANGE")
