"""CANDIDATE nominal-quantity -> protocol-volume conversions, for Martyn to ratify.

BINDING BEHAVIOUR:
  * Reports every candidate with its EXACT human-readable nominal and EXACT protocol volume.
  * Does NOT select, rank, recommend, or ratify any candidate.
  * Does NOT round in either direction — a nominal that does not land exactly on a protocol
    unit (or violates min/max/step) is reported as HALT with the reason, never coerced.

Reuses demo_lane.sizing.to_protocol_volume as the single conversion authority so the
preflight figures are identical to what the (separately-authorised) executor would compute.
"""
from .. import sizing


def _human(nominal_lots, lot_size, protocol_volume):
    return (f"{nominal_lots:g} lot(s) = {protocol_volume} protocol units "
            f"(lot_size {lot_size} units per 1.00 lot)")


def candidate_table(nominal_lots_list, symbol_meta):
    """symbol_meta needs lotSize/minVolume/maxVolume/stepVolume (protocol units).
    Returns a list of candidate rows. Each row is either:
      {status: 'EXACT', nominal_lots, human_readable, protocol_volume}
      {status: 'HALT',  nominal_lots, human_readable, protocol_volume: None, halt_reason}
    NO row is marked selected/recommended. Order is input order (not a ranking)."""
    meta = {
        "lotSize": symbol_meta["lotSize"],
        "minVolume": symbol_meta["minVolume"],
        "maxVolume": symbol_meta["maxVolume"],
        "stepVolume": symbol_meta["stepVolume"],
    }
    rows = []
    for nominal in nominal_lots_list:
        try:
            vol = sizing.to_protocol_volume(nominal, meta)
            rows.append({
                "status": "EXACT",
                "nominal_lots": nominal,
                "protocol_volume": vol,
                "human_readable": _human(nominal, meta["lotSize"], vol),
                "selected": False,          # nothing is auto-selected — Martyn ratifies
                "recommended": False,
            })
        except sizing.SizingHalt as e:
            rows.append({
                "status": "HALT",
                "nominal_lots": nominal,
                "protocol_volume": None,
                "human_readable": f"{nominal:g} lot(s) -> NO exact protocol volume",
                "halt_reason": str(e),
                "selected": False,
                "recommended": False,
            })
    return {
        "note": ("CANDIDATES ONLY — no quantity is selected, rounded, or ratified. Ratify a "
                 "specific figure knowingly by choosing one exact (nominal, protocol_volume) pair."),
        "rows": rows,
    }
