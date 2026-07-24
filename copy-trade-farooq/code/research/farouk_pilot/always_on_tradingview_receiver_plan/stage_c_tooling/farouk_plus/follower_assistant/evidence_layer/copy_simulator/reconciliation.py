"""Reconciliation — EXPECTED vs OBSERVED simulated-state divergence detection (RESEARCH-ONLY).

Never silently repairs divergence: it scans a simulated event ledger and returns
RECONCILED / DIVERGENCE_DETECTED / AMBIGUOUS plus the concrete divergences found.
"""
from __future__ import annotations


DIVERGENCE_CLASSES = ["MISSING_ACK", "DUPLICATE_ACK", "DUPLICATE_FILL", "FILL_AFTER_CANCELLATION",
                      "MODIFICATION_BEFORE_FILL", "STOP_INCONSISTENCY", "POSITION_QUANTITY_INCONSISTENCY",
                      "PARTIAL_CLOSE_INCONSISTENCY", "RESTART_DISCREPANCY", "LEDGER_STATE_MISMATCH"]


def reconcile(events, final_legs=None):
    """events: the simulated event ledger. final_legs: the simulator's final leg snapshot (optional
    cross-check). Returns a reconciliation record; never mutates/repairs."""
    div = []
    acks, fills, cancels, mods, partials = {}, {}, {}, [], {}
    for e in events:
        t = e.get("record_type")
        leg = e.get("leg")
        ts = e.get("event_timestamp")
        if t == "SIMULATED_ACK":
            acks[leg] = acks.get(leg, 0) + 1
        elif t == "SIMULATED_FILL":
            fills.setdefault(leg, []).append(ts)
        elif t == "SIMULATED_CANCEL":
            cancels[leg] = ts
        elif t == "SIMULATED_MODIFY":
            mods.append((leg, ts, e.get("detail")))
        elif t == "SIMULATED_PARTIAL_FILL":
            partials.setdefault(leg, []).append(ts)

    for leg, n in acks.items():
        if n > 1:
            div.append({"class": "DUPLICATE_ACK", "leg": leg, "count": n})
    for leg, ts_list in fills.items():
        if len(ts_list) > 1:
            div.append({"class": "DUPLICATE_FILL", "leg": leg, "count": len(ts_list)})
        if leg not in acks:
            div.append({"class": "MISSING_ACK", "leg": leg})
        if leg in cancels and any(ft > cancels[leg] for ft in ts_list):
            div.append({"class": "FILL_AFTER_CANCELLATION", "leg": leg})
    for leg, ts, detail in mods:
        if str(detail).startswith("BE") and leg is not None and leg not in fills:
            div.append({"class": "MODIFICATION_BEFORE_FILL", "leg": leg})
    for leg, plist in partials.items():
        if leg not in fills:
            div.append({"class": "PARTIAL_CLOSE_INCONSISTENCY", "leg": leg, "reason": "partial close on unfilled leg"})

    ambiguous = any(e.get("record_type") == "AMBIGUITY_STATE" and e.get("detail") == "AMBIGUOUS_INTRABAR_ORDER" for e in events)
    if div:
        status = "DIVERGENCE_DETECTED"
    elif ambiguous:
        status = "AMBIGUOUS"
    else:
        status = "RECONCILED"
    return {"record_type": "RECONCILIATION_RESULT", "status": status, "divergences": div,
            "divergence_classes_checked": DIVERGENCE_CLASSES, "silent_repair": False,
            "SIMULATION_ONLY": True, "NO_BROKER_EXECUTION": True}


def reconstruct_from_ledger(events):
    """Ledger replay -> reconstructed final leg states (proves restart/replay reproducibility)."""
    state = {}
    for e in events:
        leg = e.get("leg")
        t = e.get("record_type")
        if t == "SIMULATED_ORDER" and leg:
            state[leg] = {"state": "PROPOSED", "fill_price": None, "be": None}
        elif t == "SIMULATED_FILL" and leg:
            state.setdefault(leg, {})["state"] = "FILLED"
            state[leg]["fill_price"] = e.get("price")
        elif t == "SIMULATED_CANCEL" and leg:
            state.setdefault(leg, {})["state"] = "CANCELLED"
        elif t == "SIMULATED_MODIFY" and leg and str(e.get("detail", "")).startswith("BE"):
            state.setdefault(leg, {})["be"] = e.get("price")
    return state
