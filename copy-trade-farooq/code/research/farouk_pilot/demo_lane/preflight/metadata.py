"""Read-only XAUUSD symbol-metadata normalisation. Pure parsing of a broker-reported
symbol record into the fields Martyn needs to ratify sizing. No order code, no writes.

The adapter (mock in dry-run, a view-only client in a later burn-in) supplies the raw
record; this module only NAMES and NORMALISES the fields and computes the stop-distance
unit — it never places, modifies, or closes anything.
"""


class MetadataIncomplete(Exception):
    pass

# fields we require to be present to report a complete preflight (all read-only)
REQUIRED_FIELDS = (
    "symbolId", "symbolName", "enabled", "tradingStatus",
    "digits", "pipPosition", "lotSize", "minVolume", "maxVolume", "stepVolume",
)


def normalise(raw):
    """Return a normalised, human-labelled metadata dict. Raises MetadataIncomplete if a
    required read-only field is missing (fail closed — never fabricate a default)."""
    missing = [k for k in REQUIRED_FIELDS if raw.get(k) is None]
    if missing:
        raise MetadataIncomplete(f"symbol metadata missing required field(s): {missing}")

    digits = raw["digits"]
    tick = raw.get("tickSize")
    if tick is None:
        # cTrader reports price precision via `digits`; tick = 10**-digits when not explicit
        tick = 10 ** (-digits)

    # minimum stop distance may arrive in price units or in points; carry the unit explicitly
    min_stop = raw.get("minStopDistance")
    min_stop_unit = raw.get("minStopDistanceUnit")
    if min_stop is not None and min_stop_unit is None:
        # if the broker gives distance in points, price-unit conversion is points * tick.
        # We do NOT guess — report the raw value AND flag the unit as UNSPECIFIED so Martyn
        # sees it must be confirmed, rather than silently treating points as price.
        min_stop_unit = "UNSPECIFIED_CONFIRM_BEFORE_USE"

    return {
        "symbol": {
            "symbolId": raw["symbolId"],
            "name": raw["symbolName"],
            "enabled": bool(raw["enabled"]),
            "trading_status": raw["tradingStatus"],
        },
        "precision": {
            "digits": digits,
            "pip_position": raw["pipPosition"],
            "tick_size": tick,
        },
        "volume": {
            "lot_size": raw["lotSize"],
            "min_volume": raw["minVolume"],
            "max_volume": raw["maxVolume"],
            "step_volume": raw["stepVolume"],
            "unit_note": "protocol volume is in broker units; lot_size = units per 1.00 lot",
        },
        "stop_distance": {
            "min_stop_distance": min_stop,
            "min_stop_distance_unit": min_stop_unit,
        },
        "session": normalise_session(raw.get("session")),
    }


def normalise_session(session):
    """Normalise trading-session info where available. Returns a status even when the
    broker omits the schedule (reported as UNAVAILABLE, never assumed open)."""
    if not session:
        return {"available": False, "status": "UNAVAILABLE", "windows": []}
    return {
        "available": True,
        "status": session.get("status", "UNKNOWN"),
        "windows": session.get("windows", []),
    }
