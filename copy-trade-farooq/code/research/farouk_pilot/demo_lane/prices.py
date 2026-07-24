"""Price representability + stop-distance validation (addendum item 3). Reject rather than
silently normalize — the executor never lets the broker adjust a price."""


class PriceHalt(Exception):
    pass


def representable(price, tick_size):
    """A price must land exactly on a tick; a non-representable price is rejected (never rounded)."""
    q = round(price / tick_size)
    if abs(price - q * tick_size) > 1e-9:
        raise PriceHalt(f"price {price} not representable at tick {tick_size}")
    return price


def stop_distance_ok(entry, stop, side, min_stop_distance):
    """Stop must be at least min_stop_distance from entry on the protective side."""
    dist = abs(entry - stop)
    if dist < min_stop_distance - 1e-9:
        raise PriceHalt(f"stop distance {dist:.5f} < minimum {min_stop_distance}")
    # protective side: SELL stop above entry, BUY stop below
    if side == "SELL" and stop <= entry:
        raise PriceHalt("SELL stop must be above entry")
    if side == "BUY" and stop >= entry:
        raise PriceHalt("BUY stop must be below entry")
    return True
