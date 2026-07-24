"""
Explicit volume terminology. cTrader protocol volume is NOT the same as underlying asset units or
displayed lots. For XAUUSD (broker metadata: lotSize 10000, min/step 100, base asset XAU/oz):

  cTrader convention: protocol volume is in 1/100 of an underlying unit
    -> underlying_xau_units = raw_protocol_volume / 100
    -> displayed_lots       = raw_protocol_volume / lotSize_raw_protocol
  so 10000 raw protocol volume  =  100 underlying XAU units (oz)  =  1.00 lot.

We NEVER display "1 lot = 10000 Gold units" — 10000 is raw PROTOCOL volume, not underlying units.
The definitive proof of the 1/100 convention is an actual broker fill (future phase); this is the
cTrader-standard derivation from the read metadata.
"""
from __future__ import annotations

PROTOCOL_UNITS_PER_UNDERLYING = 100.0     # cTrader convention: volume in 1/100 of an underlying unit


def breakdown(raw_protocol_volume, *, lot_size_raw_protocol):
    return {
        "raw_protocol_volume": round(raw_protocol_volume, 4),
        "underlying_xau_units": round(raw_protocol_volume / PROTOCOL_UNITS_PER_UNDERLYING, 4),
        "displayed_lots": round(raw_protocol_volume / lot_size_raw_protocol, 4),
    }


def symbol_terms(*, lot_size_raw_protocol, min_volume_raw_protocol, step_volume_raw_protocol):
    def b(v):
        return breakdown(v, lot_size_raw_protocol=lot_size_raw_protocol)
    return {
        "lotSize_raw_protocol": lot_size_raw_protocol,
        "minVolume_raw_protocol": min_volume_raw_protocol,
        "stepVolume_raw_protocol": step_volume_raw_protocol,
        "one_lot": b(lot_size_raw_protocol),
        "min": b(min_volume_raw_protocol),
        "step": b(step_volume_raw_protocol),
        "conversion_statement": (f"{lot_size_raw_protocol} raw protocol volume "
                                 f"= {lot_size_raw_protocol / PROTOCOL_UNITS_PER_UNDERLYING:g} underlying XAU units "
                                 f"= {lot_size_raw_protocol / lot_size_raw_protocol:.2f} lot"),
        "definitive_proof": "cTrader-standard 1/100 convention from read metadata; confirmed by an actual fill (future)",
    }
