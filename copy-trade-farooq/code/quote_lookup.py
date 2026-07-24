"""
quote_lookup.py — SHADOW MODE Phase 1a, the timestamped quote lookup.

For ANY UTC timestamp, return:
  * the tick immediately BEFORE and the tick immediately AFTER it
    (bid, ask, and gap-ms for each),
  * the market-open status (from the gold session calendar),
  * a SEPARATE timestamp grade (how well we know WHEN) and price grade
    (how well-quoted that instant was).

Hard rules from the brief, enforced here:
  * NO interpolation. We expose the two real bracketing ticks; we never invent a
    single price between them.
  * NO stale-price forward-fill. We never carry a price across an empty/closed
    hour as if it were live.
  * "exact executable" is IMPOSSIBLE when the timestamp grade is T-C (posted-only)
    or T-U — you cannot claim an executable price for a time you only know coarsely.

TIMESTAMP grade (provenance of `when` — supplied by the caller, since this module
cannot know how the timestamp was obtained):
  T-A  receipt timestamp, millisecond precision
  T-B  receipt timestamp, second precision
  T-C  posted-only (the message's own posted time, not when we received/acted)
  T-U  unknown

PRICE grade (derived from the tick gap bracketing `when`):
  P-A  bracketing ticks span <= 1s
  P-B  bracketing ticks span <= 5s
  P-C  bracketing ticks span  > 5s   (also: a 5s-candle secondary source)
  P-D  only minute-resolution / midpoint data available
  P-U  no usable price (no ticks)

PAPER mode, read-only. Computes NO R, NO fill, NO ledger, NO expectancy.
"""

import bisect
from datetime import datetime, timedelta, timezone

import gold_calendar as calendar
import price_cache

# Timestamp grades
T_A, T_B, T_C, T_U = "T-A", "T-B", "T-C", "T-U"
_T_LABELS = {
    T_A: "receipt timestamp, millisecond precision",
    T_B: "receipt timestamp, second precision",
    T_C: "posted-only (message's own time, not receipt)",
    T_U: "unknown provenance",
}
# Only these provenances can ever support an "exact executable" claim.
_T_EXECUTABLE_OK = {T_A, T_B}

# Price grades
P_A, P_B, P_C, P_D, P_U = "P-A", "P-B", "P-C", "P-D", "P-U"
_P_LABELS = {
    P_A: "bracketing ticks <=1s apart",
    P_B: "bracketing ticks <=5s apart",
    P_C: "bracketing ticks >5s apart (or 5s-candle source)",
    P_D: "minute-resolution / midpoint only",
    P_U: "no usable price",
}

# Market status
OPEN_WITH_TICKS = "OPEN_WITH_TICKS"
MARKET_CLOSED = "MARKET_CLOSED"
DATA_MISSING = "DATA_MISSING"
ERROR = "ERROR"


class QuoteResult:
    def __init__(self, when, timestamp_grade):
        self.when = when
        self.timestamp_grade = timestamp_grade
        self.timestamp_grade_label = _T_LABELS.get(timestamp_grade, "?")
        self.session = None             # SessionStatus
        self.market_status = None       # OPEN_WITH_TICKS / MARKET_CLOSED / DATA_MISSING / ERROR
        self.before = None              # adapter.Tick or None
        self.after = None               # adapter.Tick or None
        self.before_gap_ms = None       # when - before  (>= 0)
        self.after_gap_ms = None        # after - when   (> 0)
        self.quote_gap_ms = None        # after - before (the gap `when` falls in)
        self.price_grade = P_U
        self.price_grade_label = _P_LABELS[P_U]
        self.exact_executable = False
        self.notes = []
        self.anomalies = []
        self.message = None

    def as_dict(self):
        def t(tk):
            if tk is None:
                return None
            return {"dt": tk.dt.isoformat(), "bid": str(tk.bid), "ask": str(tk.ask),
                    "spread": str(tk.ask - tk.bid)}
        return {
            "when_utc": self.when.isoformat(),
            "timestamp_grade": self.timestamp_grade,
            "timestamp_grade_label": self.timestamp_grade_label,
            "market_status": self.market_status,
            "session": repr(self.session) if self.session else None,
            "before_tick": t(self.before),
            "after_tick": t(self.after),
            "before_gap_ms": self.before_gap_ms,
            "after_gap_ms": self.after_gap_ms,
            "quote_gap_ms": self.quote_gap_ms,
            "price_grade": self.price_grade,
            "price_grade_label": self.price_grade_label,
            "exact_executable": self.exact_executable,
            "notes": self.notes,
            "anomalies": self.anomalies,
            "message": self.message,
        }

    def __repr__(self):
        return (f"<Quote {self.when.isoformat()} {self.market_status} "
                f"{self.timestamp_grade}/{self.price_grade} "
                f"exec={self.exact_executable}>")


def _epoch_ms(dt):
    return int(dt.astimezone(timezone.utc).timestamp() * 1000)


def _grade_price(quote_gap_ms):
    if quote_gap_ms is None:
        return P_U
    if quote_gap_ms <= 1000:
        return P_A
    if quote_gap_ms <= 5000:
        return P_B
    return P_C


def lookup(when, timestamp_grade=T_C, instrument=price_cache.adapter.INSTRUMENT,
           cache_get=None):
    """Return a QuoteResult for `when` (tz-aware UTC).

    `timestamp_grade` is the provenance of `when` (default T-C: the archive's
    timestamps are posted-only). `cache_get` lets tests inject a price source;
    default is the immutable hashed cache.
    """
    if when.tzinfo is None:
        raise ValueError("`when` must be timezone-aware (UTC)")
    if timestamp_grade not in _T_LABELS:
        raise ValueError(f"unknown timestamp grade {timestamp_grade!r}")
    get_hour = cache_get or (lambda w: price_cache.get_hour(w, instrument=instrument))

    res = QuoteResult(when, timestamp_grade)
    res.session = calendar.session_status(when)

    hour = get_hour(when)
    res.anomalies = list(hour.anomalies)

    # --- network/decoding error: surface it, decide nothing ---
    if hour.status == "ERROR":
        res.market_status = ERROR
        res.message = hour.message
        res.notes.append("fetch/decoding error — no quote derived")
        return res

    # --- no ticks in the hour: closed (expected) vs missing (problem) ---
    if hour.status in ("EMPTY", "MISSING") or not hour.ticks:
        if not res.session.is_open:
            res.market_status = MARKET_CLOSED
            res.notes.append(f"market closed: {res.session.reason}")
        else:
            res.market_status = DATA_MISSING
            res.notes.append(
                f"session OPEN but feed returned {hour.status} for this hour "
                f"({res.session.reason}) — DATA MISSING, not interpolated")
        res.price_grade, res.price_grade_label = P_U, _P_LABELS[P_U]
        return res

    # --- we have ticks: find the bracketing pair ---
    res.market_status = OPEN_WITH_TICKS
    when_ms = _epoch_ms(when)
    ticks = hour.ticks
    keys = [t.epoch_ms for t in ticks]
    # before = last tick with epoch_ms <= when_ms ; after = first with epoch_ms > when_ms
    i = bisect.bisect_right(keys, when_ms)
    before = ticks[i - 1] if i > 0 else None
    after = ticks[i] if i < len(ticks) else None

    # Boundary fallback: timestamp sits before the hour's first tick or after its
    # last tick -> reach into the adjacent hour for the MISSING side only. This is
    # NOT forward-fill: we return a real neighbouring tick with its true gap, and
    # we never bridge across an empty/closed hour (handled above).
    hour_start = when.astimezone(timezone.utc).replace(minute=0, second=0, microsecond=0)
    if before is None:
        prev = get_hour(hour_start - timedelta(milliseconds=1))   # lands in prev hour
        if prev.ticks:
            before = prev.ticks[-1]
            res.notes.append("before-tick taken from previous hour (boundary)")
    if after is None:
        nxt = get_hour(hour_start + timedelta(hours=1))            # next hour
        if nxt.ticks:
            after = nxt.ticks[0]
            res.notes.append("after-tick taken from next hour (boundary)")

    res.before, res.after = before, after
    if before is not None:
        res.before_gap_ms = when_ms - before.epoch_ms
    if after is not None:
        res.after_gap_ms = after.epoch_ms - when_ms
    if before is not None and after is not None:
        res.quote_gap_ms = after.epoch_ms - before.epoch_ms

    # Price grade from the bracketing gap. If only one side exists, we cannot
    # bracket the instant -> P-U (we refuse to forward-fill the single side).
    if before is None or after is None:
        res.price_grade = P_U
        res.notes.append("only one side bracketed — cannot grade an instant without "
                         "both sides; NOT forward-filling")
    else:
        res.price_grade = _grade_price(res.quote_gap_ms)
    res.price_grade_label = _P_LABELS[res.price_grade]

    # exact-executable: requires receipt-grade time AND a tightly bracketed instant.
    # Posted-only (T-C) / unknown (T-U) can NEVER be exact-executable, by rule.
    res.exact_executable = (
        timestamp_grade in _T_EXECUTABLE_OK
        and res.price_grade == P_A
        and res.market_status == OPEN_WITH_TICKS
    )
    if timestamp_grade not in _T_EXECUTABLE_OK and res.price_grade == P_A:
        res.notes.append(
            f"price tightly bracketed (P-A) BUT timestamp is {timestamp_grade} "
            f"({res.timestamp_grade_label}) — NOT exact-executable (minute-level "
            f"timing uncertainty dominates)")
    return res


# ----------------------------------------------------------------------------
# CLI:  python quote_lookup.py YYYY-MM-DDTHH:MM[:SS]  [T-A|T-B|T-C|T-U]
# ----------------------------------------------------------------------------
if __name__ == "__main__":
    import sys
    when = datetime.fromisoformat(sys.argv[1]).replace(tzinfo=timezone.utc)
    grade = sys.argv[2] if len(sys.argv) > 2 else T_C
    r = lookup(when, timestamp_grade=grade)
    print(r)
    import json
    print(json.dumps(r.as_dict(), indent=2))
