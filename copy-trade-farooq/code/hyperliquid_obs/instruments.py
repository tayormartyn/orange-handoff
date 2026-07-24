"""
H1 — instrument metadata parsing + BTC-perp identification.

The BTC perp is NEVER assumed. It is resolved from the RETURNED `meta` universe by exact
name match, and only accepted when exactly one match exists with well-formed metadata.
Absent / ambiguous / malformed metadata -> InstrumentError (an unverified instrument
mapping is a hard-fail; nothing downstream may observe an unverified symbol).

Hyperliquid `meta` (public /info, type="meta") shape:
  {"universe": [ {"name":"BTC","szDecimals":int,"maxLeverage":int, ...}, ... ]}
For perps the ASSET ID is the index of the entry within `universe`.
"""
from __future__ import annotations
from dataclasses import dataclass


class InstrumentError(Exception):
    pass


@dataclass(frozen=True)
class PerpInstrument:
    name: str
    asset_id: int          # index within meta.universe (the perp asset id)
    sz_decimals: int
    max_leverage: object
    verified: bool = True


def parse_universe(meta: dict) -> list:
    """Return the list of universe entries, or raise on a malformed envelope."""
    if not isinstance(meta, dict) or "universe" not in meta:
        raise InstrumentError("meta response has no 'universe' field — cannot verify any instrument")
    universe = meta["universe"]
    if not isinstance(universe, list) or not universe:
        raise InstrumentError("meta 'universe' is empty or not a list")
    return universe


def resolve_perp(meta: dict, name: str) -> PerpInstrument:
    """Identify the named perp from the RETURNED metadata. Exactly-one-match or fail."""
    universe = parse_universe(meta)
    matches = []
    for idx, entry in enumerate(universe):
        if isinstance(entry, dict) and entry.get("name") == name:
            matches.append((idx, entry))
    if len(matches) == 0:
        raise InstrumentError(f"no perp named {name!r} found in returned universe — not assumed")
    if len(matches) > 1:
        raise InstrumentError(
            f"ambiguous: {len(matches)} perps named {name!r} in returned universe — not assumed")
    idx, entry = matches[0]
    if "szDecimals" not in entry:
        raise InstrumentError(f"perp {name!r} metadata missing szDecimals — mapping unverified")
    try:
        sz = int(entry["szDecimals"])
    except (TypeError, ValueError):
        raise InstrumentError(f"perp {name!r} szDecimals not an integer — mapping unverified")
    return PerpInstrument(name=name, asset_id=idx, sz_decimals=sz,
                          max_leverage=entry.get("maxLeverage"), verified=True)
