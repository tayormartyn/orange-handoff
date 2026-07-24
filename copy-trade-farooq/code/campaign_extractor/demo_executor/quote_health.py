"""
Deterministic read-only quote-health state. A connected socket is NEVER proof that quotes are active:
QUOTES_ACTIVE requires a recently received VALID XAUUSD spot event. Pure/testable — the live session
fields (pid, session, subscription phase, events this session, reconnect count, last error) are
injected; freshness is computed from the latest stored valid quote.
"""
from __future__ import annotations

# lifecycle states
CONNECTING = "QUOTES_CONNECTING"
AUTHENTICATED = "QUOTES_AUTHENTICATED"
SUBSCRIBING = "QUOTES_SUBSCRIBING"
ACTIVE = "QUOTES_ACTIVE"
SILENT = "QUOTES_SILENT"
STALE = "QUOTES_STALE"
DISCONNECTED = "QUOTES_DISCONNECTED"
MARKET_CLOSED = "QUOTES_MARKET_CLOSED"
ERROR = "QUOTES_ERROR"

ACTIVE_WINDOW_S = 30            # a valid spot within 30s => ACTIVE
SILENT_WINDOW_S = 120          # connected+subscribed but no spot 30-120s => SILENT
STALE_WINDOW_S = 300           # >5 min => STALE


def valid_quote(bid, ask):
    return (bid is not None and ask is not None and bid > 0 and ask > 0 and bid <= ask)


def health(*, latest_bid, latest_ask, latest_event_ms, now_ms, phase="subscribed", connected=True,
           subscribed=True, events_this_session=0, reconnect_count=0, last_error=None,
           market_closed=False, session_id=None, pid=None, coverage_start_ms=None, coverage_end_ms=None):
    """phase in connecting/authenticated/subscribing/subscribed. Returns the state + display dict."""
    age = None if latest_event_ms is None else round((now_ms - latest_event_ms) / 1000.0, 1)
    spread = (round(latest_ask - latest_bid, 3) if valid_quote(latest_bid, latest_ask) else None)

    if last_error:
        state = ERROR
    elif not connected:
        state = DISCONNECTED
    elif market_closed:
        state = MARKET_CLOSED
    elif phase == "connecting":
        state = CONNECTING
    elif phase == "authenticated":
        state = AUTHENTICATED
    elif phase == "subscribing" or not subscribed:
        state = SUBSCRIBING
    elif not valid_quote(latest_bid, latest_ask) or latest_event_ms is None:
        state = SILENT                                 # subscribed but no valid spot yet
    elif age is not None and age <= ACTIVE_WINDOW_S and events_this_session > 0:
        state = ACTIVE                                 # ONLY here: a recent valid spot event
    elif age is not None and age <= STALE_WINDOW_S:
        state = SILENT
    else:
        state = STALE

    return {
        "state": state, "supervisor_pid": pid, "session_id": session_id,
        "subscription_state": phase, "connected": connected, "subscribed": subscribed,
        "last_event_timestamp_ms": latest_event_ms, "quote_age_seconds": age,
        "bid": latest_bid, "ask": latest_ask, "spread": spread,
        "events_this_session": events_this_session, "reconnect_count": reconnect_count,
        "last_safe_error": last_error,
        "coverage_start_ms": coverage_start_ms, "coverage_end_ms": coverage_end_ms,
    }
