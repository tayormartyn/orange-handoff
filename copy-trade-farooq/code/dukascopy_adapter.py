"""
dukascopy_adapter.py — SHADOW MODE Phase 1a, the gold tick-data adapter.

Fetches Dukascopy historical XAU/USD tick data for a single UTC hour, decodes
it, and normalises it into exact, validated ticks. This is the PRICE FOUNDATION
for shadow mode — it ONLY retrieves and validates price data. It computes NO
shadow result, NO R, NO ledger, NO expectancy. PAPER mode, read-only.

------------------------------------------------------------------------------
RETRIEVAL ROUTE (proven reachable from this environment — see README Phase 1a)
------------------------------------------------------------------------------
  HTTPS GET  https://datafeed.dukascopy.com/datafeed/{INSTR}/{YYYY}/{MM0}/{DD}/{HH}h_ticks.bi5
    * {MM0} is the ZERO-INDEXED month: January = 00 ... December = 11.
    * The body is an LZMA-compressed (.bi5) stream of fixed 20-byte records.
    * Each record is BIG-ENDIAN  >IIIff :
          uint32  milliseconds since the start of the hour
          uint32  ask, in integer points
          uint32  bid, in integer points
          float32 ask volume (millions)
          float32 bid volume (millions)
    * XAU/USD points are scaled by 1000 (3 decimal places): price = points / 1000.

  Empirically observed responses (used to tell CLOSED from MISSING):
    * 200 + non-empty body   -> ticks present.
    * 200 + ZERO-length body -> an empty hour (market closed, or a genuine gap;
                                the calendar decides which). NOT an error.
    * 404                     -> the hour is not published -> DATA_MISSING.

No API key, no auth, stdlib only (urllib + lzma). No third-party packages.
"""

import lzma
import socket
import struct
import time
import urllib.error
import urllib.request
from collections import namedtuple
from datetime import datetime, timedelta, timezone
from decimal import Decimal

# ----------------------------------------------------------------------------
# Constants — the instrument contract for THIS adapter (gold only, on purpose)
# ----------------------------------------------------------------------------
INSTRUMENT = "XAUUSD"
BASE_URL = "https://datafeed.dukascopy.com/datafeed"
RECORD_FMT = ">IIIff"          # big-endian: ms, ask_pts, bid_pts, askVol, bidVol
RECORD_SIZE = 20               # struct.calcsize(RECORD_FMT)
POINT_SCALE = Decimal(1000)    # XAU/USD: 3 decimal places -> divide points by 1000
USER_AGENT = "signal-terminal-shadow/1a (read-only historical fetch)"
DEFAULT_TIMEOUT = 30
FETCH_RETRIES = 3              # transient network failures are retried (no silent give-up)
RETRY_BACKOFF_SEC = 1.5

# Plausibility band for $/oz gold — used ONLY to validate scaling/instrument, not
# to filter ticks. Deliberately wide: it must catch a 10x/1000x scaling mistake
# or a wrong instrument, without second-guessing a real market move.
PLAUSIBLE_PRICE_MIN = Decimal("400")
PLAUSIBLE_PRICE_MAX = Decimal("12000")
# A single tick spread this large almost certainly means corrupt/garbage data
# rather than a real (if wide) gold spread. Used for anomaly flagging only.
IMPOSSIBLE_SPREAD = Decimal("50")


# ----------------------------------------------------------------------------
# Data types
# ----------------------------------------------------------------------------
# One normalised tick. Prices are exact Decimals (points/1000); raw point ints
# are kept so the normalisation is fully reproducible/auditable.
Tick = namedtuple("Tick", "epoch_ms dt bid ask bid_raw ask_raw bid_vol ask_vol")


class HourResult:
    """The outcome of fetching+decoding ONE instrument-hour.

    status:
        "TICKS"        200 + records decoded (ticks populated).
        "EMPTY"        200 + zero-length body (closed hour or genuine gap).
        "MISSING"      404 (the hour is not published).
        "ERROR"        network/decoding failure (message populated).
    """

    def __init__(self, instrument, hour_start, status, ticks=None,
                 raw_bytes=None, anomalies=None, message=None, http_status=None):
        self.instrument = instrument
        self.hour_start = hour_start            # tz-aware UTC datetime, on the hour
        self.status = status
        self.ticks = ticks or []
        self.raw_bytes = raw_bytes              # the exact compressed body (for hashing)
        self.anomalies = anomalies or []
        self.message = message
        self.http_status = http_status

    @property
    def ok(self):
        return self.status == "TICKS"

    def __repr__(self):
        return (f"<HourResult {self.instrument} {self.hour_start.isoformat()} "
                f"{self.status} ticks={len(self.ticks)} anomalies={len(self.anomalies)}>")


# ----------------------------------------------------------------------------
# URL building
# ----------------------------------------------------------------------------
def hour_url(hour_start, instrument=INSTRUMENT):
    """Build the .bi5 URL for the UTC hour containing `hour_start`.

    Dukascopy months are ZERO-INDEXED in the path (Jan=00). This is the single
    most common mistake when pulling this feed, so it lives in exactly one place.
    """
    if hour_start.tzinfo is None:
        raise ValueError("hour_start must be timezone-aware (UTC)")
    h = hour_start.astimezone(timezone.utc)
    return (f"{BASE_URL}/{instrument}/{h.year:04d}/{h.month - 1:02d}/"
            f"{h.day:02d}/{h.hour:02d}h_ticks.bi5")


def _floor_hour(dt):
    """Truncate a tz-aware UTC datetime to the start of its hour."""
    dt = dt.astimezone(timezone.utc)
    return dt.replace(minute=0, second=0, microsecond=0)


# ----------------------------------------------------------------------------
# Fetch
# ----------------------------------------------------------------------------
def fetch_raw(hour_start, instrument=INSTRUMENT, timeout=DEFAULT_TIMEOUT, opener=None):
    """Fetch the raw compressed body for one hour.

    Returns (http_status, body_bytes). body_bytes is b"" for an empty hour.
    Raises FileNotFoundError on 404 (caller maps that to MISSING) and
    ConnectionError on any other network failure.

    `opener` lets tests inject a fake transport; default is urllib.
    """
    url = hour_url(hour_start, instrument)
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    _open = opener or (lambda r, t: urllib.request.urlopen(r, timeout=t))
    last_err = None
    for attempt in range(1, FETCH_RETRIES + 1):
        try:
            with _open(req, timeout) as resp:
                return resp.status, resp.read()
        except urllib.error.HTTPError as e:
            # 404 is a definitive answer (not published) — do NOT retry it.
            if e.code == 404:
                raise FileNotFoundError(f"404 not published: {url}") from e
            raise ConnectionError(f"HTTP {e.code} {e.reason}: {url}") from e
        except (urllib.error.URLError, TimeoutError, socket.timeout, OSError) as e:
            # Transient: time out, reset connection, DNS blip. Retry a few times
            # before giving up — never silently return a wrong/empty result.
            last_err = e
            if attempt < FETCH_RETRIES:
                time.sleep(RETRY_BACKOFF_SEC * attempt)
                continue
    raise ConnectionError(f"network error for {url} after {FETCH_RETRIES} tries: {last_err}")


# ----------------------------------------------------------------------------
# Decode + normalise
# ----------------------------------------------------------------------------
def decode_ticks(body, hour_start, instrument=INSTRUMENT):
    """Decompress + parse one hour's body into a sorted list of normalised Ticks.

    Raises ValueError on a truncated/garbled stream. An empty body returns [].
    Ticks are sorted by epoch_ms (the feed is usually already ordered; we make it
    a guarantee). Out-of-order / duplicate detection is reported separately by
    detect_anomalies(), NOT silently repaired here.
    """
    if not body:
        return []
    try:
        raw = lzma.decompress(body)
    except lzma.LZMAError as e:
        raise ValueError(f"LZMA decode failed: {e}") from e
    if len(raw) % RECORD_SIZE != 0:
        raise ValueError(
            f"truncated stream: {len(raw)} bytes is not a multiple of {RECORD_SIZE}")

    hour_start = _floor_hour(hour_start)
    hour_epoch_ms = int(hour_start.timestamp() * 1000)
    ticks = []
    for ms, ask_pts, bid_pts, ask_vol, bid_vol in struct.iter_unpack(RECORD_FMT, raw):
        epoch_ms = hour_epoch_ms + ms
        ticks.append(Tick(
            epoch_ms=epoch_ms,
            dt=datetime.fromtimestamp(epoch_ms / 1000, tz=timezone.utc),
            bid=Decimal(bid_pts) / POINT_SCALE,
            ask=Decimal(ask_pts) / POINT_SCALE,
            bid_raw=bid_pts,
            ask_raw=ask_pts,
            bid_vol=float(bid_vol),
            ask_vol=float(ask_vol),
        ))
    ticks.sort(key=lambda t: t.epoch_ms)
    return ticks


# ----------------------------------------------------------------------------
# Validation + anomaly detection (REPORT, never silently repair)
# ----------------------------------------------------------------------------
def validate_instrument(ticks):
    """Confirm the decoded ticks really are XAU/USD in $/oz, UTC, right scaling.

    Returns a list of anomaly strings (empty == clean). Checks:
      * prices land in a plausible $/oz band (catches 10x/1000x scaling errors,
        or a completely wrong instrument);
      * ask >= bid on the median tick (catches a bid<->ask field swap);
      * the median spread is sane (a swapped/garbled feed shows a huge spread).
    Per-tick anomalies (ask<bid, zero/neg, dupes, order, jumps) are in detect_anomalies.
    """
    out = []
    if not ticks:
        return out
    mids = sorted((t.bid + t.ask) / 2 for t in ticks)
    median_mid = mids[len(mids) // 2]
    if not (PLAUSIBLE_PRICE_MIN <= median_mid <= PLAUSIBLE_PRICE_MAX):
        out.append(
            f"SCALING/INSTRUMENT: median mid {median_mid} outside plausible "
            f"$/oz band [{PLAUSIBLE_PRICE_MIN},{PLAUSIBLE_PRICE_MAX}] "
            f"— wrong scale or not XAU/USD?")
    spreads = sorted(t.ask - t.bid for t in ticks)
    median_spread = spreads[len(spreads) // 2]
    if median_spread < 0:
        out.append(f"FIELD-SWAP: median spread {median_spread} < 0 — bid/ask swapped?")
    elif median_spread > IMPOSSIBLE_SPREAD:
        out.append(f"FIELD-SWAP/CORRUPT: median spread {median_spread} implausibly wide")
    return out


def detect_anomalies(ticks, hour_start):
    """Per-tick + structural anomaly checks. Returns a list of anomaly strings.

    NOTHING here mutates the ticks; we surface problems so a human/quality grade
    can react. Checks: ask<bid, zero/negative prices, impossible spread,
    duplicate timestamps, out-of-order, large jumps, and out-of-hour stamps
    (which would mean the hour file is mis-timed -> a UTC/date-match failure).
    """
    out = []
    if not ticks:
        return out
    hour_start = _floor_hour(hour_start)
    lo = int(hour_start.timestamp() * 1000)
    hi = lo + 3_600_000
    prev = None
    dupes = 0
    ooo = 0
    out_of_hour = 0
    for t in ticks:
        if t.ask < t.bid:
            out.append(f"ASK<BID at {t.dt.isoformat()}: ask={t.ask} bid={t.bid}")
        if t.bid <= 0 or t.ask <= 0:
            out.append(f"ZERO/NEG price at {t.dt.isoformat()}: bid={t.bid} ask={t.ask}")
        if (t.ask - t.bid) > IMPOSSIBLE_SPREAD:
            out.append(f"IMPOSSIBLE SPREAD at {t.dt.isoformat()}: {t.ask - t.bid}")
        if not (lo <= t.epoch_ms < hi):
            out_of_hour += 1
        if prev is not None:
            if t.epoch_ms == prev.epoch_ms:
                dupes += 1
            elif t.epoch_ms < prev.epoch_ms:
                ooo += 1
            # Jump check: gold rarely moves > $20 between consecutive ticks.
            jump = abs((t.bid + t.ask) / 2 - (prev.bid + prev.ask) / 2)
            if jump > Decimal("20"):
                out.append(f"PRICE JUMP at {t.dt.isoformat()}: {jump} between ticks")
        prev = t
    if dupes:
        out.append(f"DUPLICATE timestamps: {dupes}")
    if ooo:
        out.append(f"OUT-OF-ORDER ticks (pre-sort): {ooo}")
    if out_of_hour:
        out.append(f"OUT-OF-HOUR stamps: {out_of_hour} tick(s) fall outside "
                   f"{hour_start.isoformat()} +1h — UTC/date-match failure?")
    return out


# ----------------------------------------------------------------------------
# Top-level: fetch one hour, fully normalised + validated
# ----------------------------------------------------------------------------
def get_hour(when, instrument=INSTRUMENT, timeout=DEFAULT_TIMEOUT, opener=None):
    """Fetch, decode, normalise and validate the instrument-hour containing `when`.

    `when` is a tz-aware UTC datetime. Returns a HourResult. Never raises for the
    normal CLOSED/MISSING cases — those are statuses, not exceptions — so callers
    can cleanly distinguish "market closed" from "data missing" from "real error".
    """
    if when.tzinfo is None:
        raise ValueError("`when` must be timezone-aware (UTC)")
    hour_start = _floor_hour(when)
    try:
        http_status, body = fetch_raw(hour_start, instrument, timeout, opener)
    except FileNotFoundError as e:
        return HourResult(instrument, hour_start, "MISSING", message=str(e), http_status=404)
    except ConnectionError as e:
        return HourResult(instrument, hour_start, "ERROR", message=str(e))

    if not body:
        return HourResult(instrument, hour_start, "EMPTY", raw_bytes=b"",
                          http_status=http_status)
    try:
        ticks = decode_ticks(body, hour_start, instrument)
    except ValueError as e:
        return HourResult(instrument, hour_start, "ERROR", raw_bytes=body,
                          message=f"decode error: {e}", http_status=http_status)

    anomalies = validate_instrument(ticks) + detect_anomalies(ticks, hour_start)
    return HourResult(instrument, hour_start, "TICKS", ticks=ticks, raw_bytes=body,
                      anomalies=anomalies, http_status=http_status)


# ----------------------------------------------------------------------------
# Manual smoke test:  python dukascopy_adapter.py [YYYY-MM-DDTHH]
# ----------------------------------------------------------------------------
if __name__ == "__main__":
    import sys
    when = (datetime.fromisoformat(sys.argv[1]).replace(tzinfo=timezone.utc)
            if len(sys.argv) > 1 else datetime(2026, 6, 25, 14, tzinfo=timezone.utc))
    res = get_hour(when)
    print(res)
    print("url:", hour_url(_floor_hour(when)))
    if res.ticks:
        print("first:", res.ticks[0].dt.isoformat(), res.ticks[0].bid, res.ticks[0].ask)
        print("last :", res.ticks[-1].dt.isoformat(), res.ticks[-1].bid, res.ticks[-1].ask)
    if res.anomalies:
        print("anomalies:", res.anomalies)
