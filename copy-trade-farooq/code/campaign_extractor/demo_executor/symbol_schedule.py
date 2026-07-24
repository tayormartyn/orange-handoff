"""
XAUUSD market-state decision from BROKER-provided symbol schedule / holiday metadata. Authoritative:
distinguishes QUOTES_MARKET_CLOSED from QUOTES_STALE using the broker's schedule, NEVER from the local
calendar alone. If no broker schedule is available, returns UNKNOWN (do NOT assume closed). Advisory
only — no broker action. Regardless of the outcome, any non-active quote state still blocks eligibility.

Broker schedule shape (as captured from ProtoOASymbol trading hours), all seconds-of-week UTC:
    schedule = [{"start_seconds": <int>, "end_seconds": <int>}, ...]   # weekly open intervals
    holidays = [{"date": "YYYY-MM-DD", "name": "...", "is_open": false}]  # broker holiday calendar
"""
from __future__ import annotations
import calendar
import time

UNKNOWN = "SCHEDULE_UNKNOWN"
MARKET_OPEN = "MARKET_OPEN"
MARKET_CLOSED = "MARKET_CLOSED"


def _seconds_of_week(now_ms):
    t = time.gmtime(now_ms / 1000)
    # Telegram/cTrader week: seconds since Sunday 00:00 UTC (tm_wday: Mon=0..Sun=6 -> Sun=0..Sat=6)
    dow_sun0 = (t.tm_wday + 1) % 7
    return dow_sun0 * 86400 + t.tm_hour * 3600 + t.tm_min * 60 + t.tm_sec


def market_state(*, now_ms, schedule=None, holidays=None):
    """Return (state, reason). state in MARKET_OPEN / MARKET_CLOSED / SCHEDULE_UNKNOWN. Broker metadata
    is authoritative; with none available we return UNKNOWN and NEVER infer closure from the calendar."""
    # broker holiday override first (authoritative)
    if holidays:
        today = time.strftime("%Y-%m-%d", time.gmtime(now_ms / 1000))
        for h in holidays:
            if h.get("date") == today and h.get("is_open") is False:
                return MARKET_CLOSED, "BROKER_HOLIDAY:" + str(h.get("name") or today)
    if not schedule:
        return UNKNOWN, "NO_BROKER_SCHEDULE"              # do NOT assume closed from the calendar
    sow = _seconds_of_week(now_ms)
    for iv in schedule:
        s, e = iv.get("start_seconds"), iv.get("end_seconds")
        if s is None or e is None:
            continue
        if s <= sow < e or (e < s and (sow >= s or sow < e)):   # handle wrap past Saturday->Sunday
            return MARKET_OPEN, "WITHIN_BROKER_SESSION"
    return MARKET_CLOSED, "OUTSIDE_BROKER_SESSION"


def market_closed_flag(*, now_ms, schedule=None, holidays=None):
    """Convenience for quote_health.health(market_closed=...). Only True when the broker schedule
    AUTHORITATIVELY says closed; UNKNOWN -> False (report STALE, don't fabricate a closure)."""
    state, reason = market_state(now_ms=now_ms, schedule=schedule, holidays=holidays)
    return (state == MARKET_CLOSED), state, reason
