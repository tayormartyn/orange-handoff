"""Exact volume conversion (correction 3 + F1). NO rounding either way.
The nominal must convert EXACTLY to a valid protocol volume, else HALT."""


class SizingHalt(Exception):
    pass


def to_protocol_volume(nominal_lots, symbol_meta):
    """symbol_meta: {lotSize, minVolume, maxVolume, stepVolume} in protocol units.
    Returns the exact protocol volume or raises SizingHalt. F1 conditions ALL required:
      >= minVolume, <= maxVolume, (volume % stepVolume) == 0, AND == the exact ratified nominal.
    'Exact ratified nominal' means nominal_lots * lotSize is an integer protocol volume with
    no remainder — a nominal that does not land exactly on a protocol unit HALTS (no rounding)."""
    lot = symbol_meta["lotSize"]
    raw = nominal_lots * lot
    volume = round(raw)
    if abs(raw - volume) > 1e-9:
        raise SizingHalt(f"nominal {nominal_lots} lots -> {raw} is not an exact protocol volume (no rounding)")
    mn, mx, step = symbol_meta["minVolume"], symbol_meta["maxVolume"], symbol_meta["stepVolume"]
    if not (volume >= mn):
        raise SizingHalt(f"volume {volume} < minVolume {mn}")
    if not (volume <= mx):
        raise SizingHalt(f"volume {volume} > maxVolume {mx}")
    if volume % step != 0:
        raise SizingHalt(f"volume {volume} not a multiple of stepVolume {step}")
    return volume


def aggregate_ok(volumes, max_aggregate):
    return sum(volumes) <= max_aggregate
