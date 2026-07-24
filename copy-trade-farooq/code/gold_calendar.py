"""
gold_calendar.py — SHADOW MODE Phase 1a, the gold (XAU/USD spot) session calendar.

Tells you, for any UTC instant, whether spot gold is EXPECTED to be trading. Its
job is to let the rest of the foundation distinguish:

    MARKET_CLOSED  (no ticks EXPECTED — weekend / daily settlement break)
        vs
    DATA_MISSING   (ticks were expected but the feed has none)

Design choices that matter:
  * Spot XAU/USD runs ~23h/day, Sunday evening to Friday evening, with a one-hour
    daily settlement break, all anchored to 17:00 New York time.
  * DST is computed from the US federal rule (2nd Sunday of March -> 1st Sunday of
    November) — NO external tz database (Windows here has no IANA tzdata, and a
    price foundation should not depend on one). EST = UTC-5, EDT = UTC-4.
  * US HOLIDAYS are treated as ADVISORY, not as hard closures. Spot metals trade
    THIN (often with an early close) on most US holidays rather than shutting —
    e.g. Dukascopy returns a full hour of XAU ticks on US Memorial Day. So the
    calendar flags a holiday as context; the ACTUAL DATA PRESENCE is what the
    runner uses to call CLOSED vs MISSING. We never fabricate a closure the data
    contradicts.

PAPER mode, pure/deterministic, no I/O, no network.
"""

from datetime import date, datetime, timedelta, timezone

# Session status values
OPEN = "OPEN"
WEEKEND_CLOSED = "WEEKEND_CLOSED"
DAILY_BREAK = "DAILY_BREAK"


class SessionStatus:
    def __init__(self, status, is_open, reason, holiday=None, thin_liquidity=False):
        self.status = status                  # OPEN / WEEKEND_CLOSED / DAILY_BREAK
        self.is_open = is_open                # True only when ticks are EXPECTED
        self.reason = reason
        self.holiday = holiday                # name str, or None
        self.thin_liquidity = thin_liquidity  # advisory: open but expect thin/early-close

    def __repr__(self):
        h = f" holiday={self.holiday}" if self.holiday else ""
        return f"<{self.status} is_open={self.is_open}{h}: {self.reason}>"


# ----------------------------------------------------------------------------
# US Eastern offset (no tzdata) — federal DST rule, valid for all years >= 2007
# ----------------------------------------------------------------------------
def _nth_weekday(year, month, weekday, n):
    """Date of the n-th `weekday` (Mon=0..Sun=6) of (year, month)."""
    d = date(year, month, 1)
    offset = (weekday - d.weekday()) % 7
    return d + timedelta(days=offset + 7 * (n - 1))


def _is_edt(dt_utc):
    """True if US Eastern is on Daylight time (EDT, UTC-4) at this UTC instant.

    DST: 02:00 LOCAL on the 2nd Sunday of March .. 02:00 LOCAL on the 1st Sunday
    of November. We compare in UTC using the transition instants (the spring jump
    is at 07:00 UTC; the autumn fall-back is at 06:00 UTC because the clock is
    still on EDT at the moment of transition).
    """
    y = dt_utc.year
    dst_start = datetime(y, 3, _nth_weekday(y, 3, 6, 2).day, 7, tzinfo=timezone.utc)
    dst_end = datetime(y, 11, _nth_weekday(y, 11, 6, 1).day, 6, tzinfo=timezone.utc)
    return dst_start <= dt_utc < dst_end


def eastern_local(dt_utc):
    """Convert a tz-aware UTC datetime to naive US Eastern wall-clock time."""
    dt_utc = dt_utc.astimezone(timezone.utc)
    offset = -4 if _is_edt(dt_utc) else -5
    return (dt_utc + timedelta(hours=offset)).replace(tzinfo=None)


# ----------------------------------------------------------------------------
# US holidays relevant to spot-metals trading (ADVISORY ONLY)
# ----------------------------------------------------------------------------
def _us_holiday(d):
    """Return a holiday name if `d` (a date) is a US market holiday metals traders
    watch, else None. Used for CONTEXT only — most of these trade thin, not closed.

    Likely-CLOSED (full): New Year's Day, Good Friday, Christmas Day.
    Thin / early-close:   Memorial Day, Juneteenth, Independence Day, Labor Day,
                          Thanksgiving.
    """
    y = d.year
    # Fixed-date
    if (d.month, d.day) == (1, 1):
        return "New Year's Day"
    if (d.month, d.day) == (6, 19):
        return "Juneteenth"
    if (d.month, d.day) == (7, 4):
        return "Independence Day"
    if (d.month, d.day) == (12, 25):
        return "Christmas Day"
    # Floating
    if d == _last_monday(y, 5):
        return "Memorial Day"          # last Monday of May
    if d == _nth_weekday(y, 9, 0, 1):
        return "Labor Day"             # first Monday of September
    if d == _nth_weekday(y, 11, 3, 4):
        return "Thanksgiving"          # fourth Thursday of November
    if d == _good_friday(y):
        return "Good Friday"
    return None


_FULL_CLOSE_HOLIDAYS = {"New Year's Day", "Christmas Day", "Good Friday"}


def _last_monday(year, month):
    # last Monday of a month
    d = date(year, month, 28)
    while d.month == month:
        nxt = d + timedelta(days=1)
        if nxt.month != month:
            break
        d = nxt
    # walk back to Monday
    while d.weekday() != 0:
        d -= timedelta(days=1)
    return d


def _good_friday(year):
    """Good Friday = 2 days before Easter Sunday (anonymous Gregorian algorithm)."""
    a = year % 19
    b = year // 100
    c = year % 100
    dd = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - dd - g + 15) % 30
    i = c // 4
    k = c % 4
    L = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * L) // 451
    month = (h + L - 7 * m + 114) // 31
    day = ((h + L - 7 * m + 114) % 31) + 1
    easter = date(year, month, day)
    return easter - timedelta(days=2)


# ----------------------------------------------------------------------------
# The session decision
# ----------------------------------------------------------------------------
def session_status(when):
    """Classify the gold session at a tz-aware UTC `when`.

    Weekend window: Friday 17:00 ET -> Sunday 18:00 ET is closed.
    Daily break:    Mon-Thu 17:00-18:00 ET (one hour) is closed.
    Holidays:       advisory only (thin/early-close), EXCEPT the full-close set
                    which is reported is_open=False so a missing hour is explained.
    """
    if when.tzinfo is None:
        raise ValueError("`when` must be timezone-aware (UTC)")
    et = eastern_local(when)
    wd = et.weekday()            # Mon=0 .. Sun=6
    holiday = _us_holiday(et.date())

    # --- Weekend ---
    if wd == 5:                                  # Saturday
        return SessionStatus(WEEKEND_CLOSED, False, "Saturday — gold market closed",
                             holiday=holiday)
    if wd == 4 and et.hour >= 17:                # Friday after 17:00 ET
        return SessionStatus(WEEKEND_CLOSED, False,
                             "after Friday 17:00 ET weekly close", holiday=holiday)
    if wd == 6 and et.hour < 18:                 # Sunday before 18:00 ET
        return SessionStatus(WEEKEND_CLOSED, False,
                             "before Sunday 18:00 ET weekly open", holiday=holiday)

    # --- Daily settlement break (Mon-Thu 17:00-18:00 ET) ---
    if wd in (0, 1, 2, 3) and et.hour == 17:
        return SessionStatus(DAILY_BREAK, False,
                             "17:00-18:00 ET daily settlement break", holiday=holiday)

    # --- Full-close holidays (explain a missing hour as closed, not missing) ---
    if holiday in _FULL_CLOSE_HOLIDAYS:
        return SessionStatus(WEEKEND_CLOSED, False,
                             f"{holiday} — gold market closed", holiday=holiday)

    # --- Open (thin advisory on non-full-close holidays) ---
    if holiday:
        return SessionStatus(OPEN, True,
                             f"open (thin — {holiday}, expect reduced liquidity/early close)",
                             holiday=holiday, thin_liquidity=True)
    return SessionStatus(OPEN, True, "normal trading session")


# ----------------------------------------------------------------------------
# CLI:  python gold_calendar.py YYYY-MM-DDTHH:MM
# ----------------------------------------------------------------------------
if __name__ == "__main__":
    import sys
    when = datetime.fromisoformat(sys.argv[1]).replace(tzinfo=timezone.utc)
    et = eastern_local(when)
    print(f"UTC {when.isoformat()}  ==  ET {et.isoformat()} ({'EDT' if _is_edt(when) else 'EST'})")
    print(session_status(when))
