"""
price_cache.py — SHADOW MODE Phase 1a, the immutable hashed price-window cache.

Caches Dukascopy instrument-hours on disk so the foundation is REPRODUCIBLE and
auditable. Two guarantees the brief requires:

  1. IMMUTABLE + HASHED. Every cached hour stores the SHA-256 of the exact raw
     compressed body it came from. If a re-download produces a DIFFERENT hash for
     an hour we already have, that is surfaced loudly as a "hash-changed" anomaly
     — we never silently overwrite history.

  2. REPRODUCIBLE NORMALISATION. The cache also stores the normalised ticks. A
     repeat run reproduces byte-identical normalised ticks because (a) the raw
     bytes are pinned by hash and (b) normalisation is pure/deterministic. A
     verify step re-decodes the cached raw bytes and checks the ticks still match.

Layout (under data/price_cache/):
    XAUUSD/2026/05/25/14h.bi5      the exact raw compressed body (or empty file)
    XAUUSD/2026/05/25/14h.json     metadata: status, sha256, tick count, anomalies
    XAUUSD/2026/05/25/14h.ticks    normalised ticks, one per line (deterministic)

PAPER mode, read-only to everything except its OWN cache directory. Touches no
trade log, no DB, no LIVE stub.
"""

import hashlib
import json
import os
from datetime import datetime, timezone
from decimal import Decimal

import dukascopy_adapter as adapter

CACHE_DIR = os.path.join("data", "price_cache")
EMPTY_SHA = hashlib.sha256(b"").hexdigest()   # the hash of an empty (closed) hour

# Process-level in-memory cache of already-loaded hours. The disk cache makes a
# repeat run cheap; THIS makes a single run cheap, so the replay engine can call
# get_hour() thousands of times without re-reading + re-decoding the same .ticks
# files. Disk remains the source of truth; this only avoids redundant rebuilds.
_MEM = {}


def clear_mem_cache():
    _MEM.clear()


# ----------------------------------------------------------------------------
# Paths
# ----------------------------------------------------------------------------
def _hour_dir(hour_start, instrument):
    h = hour_start.astimezone(timezone.utc)
    # Month is stored ZERO-INDEXED to mirror the Dukascopy path exactly, so the
    # cache layout is a faithful local copy of the upstream tree.
    return os.path.join(CACHE_DIR, instrument,
                        f"{h.year:04d}", f"{h.month - 1:02d}", f"{h.day:02d}")


def _paths(hour_start, instrument):
    d = _hour_dir(hour_start, instrument)
    h = hour_start.astimezone(timezone.utc).hour
    base = os.path.join(d, f"{h:02d}h")
    return base + ".bi5", base + ".json", base + ".ticks"


def _sha256(data):
    return hashlib.sha256(data).hexdigest()


# ----------------------------------------------------------------------------
# Deterministic tick serialisation (the reproducibility contract)
# ----------------------------------------------------------------------------
# We serialise the RAW integer points + raw volume bits, not the derived Decimal,
# so a round-trip is exact and never depends on Decimal/float formatting choices.
def _tick_line(t):
    return f"{t.epoch_ms}\t{t.ask_raw}\t{t.bid_raw}\t{t.ask_vol!r}\t{t.bid_vol!r}"


def _ticks_blob(ticks):
    return "\n".join(_tick_line(t) for t in ticks)


def _load_ticks_blob(blob, hour_start, instrument):
    """Rebuild Tick objects from a stored .ticks blob (exact inverse of _ticks_blob)."""
    out = []
    if not blob:
        return out
    for line in blob.split("\n"):
        if not line:
            continue
        epoch_ms, ask_raw, bid_raw, ask_vol, bid_vol = line.split("\t")
        epoch_ms = int(epoch_ms)
        ask_raw = int(ask_raw)
        bid_raw = int(bid_raw)
        out.append(adapter.Tick(
            epoch_ms=epoch_ms,
            dt=datetime.fromtimestamp(epoch_ms / 1000, tz=timezone.utc),
            bid=Decimal(bid_raw) / adapter.POINT_SCALE,
            ask=Decimal(ask_raw) / adapter.POINT_SCALE,
            bid_raw=bid_raw,
            ask_raw=ask_raw,
            bid_vol=float(bid_vol),
            ask_vol=float(ask_vol),
        ))
    return out


# ----------------------------------------------------------------------------
# Write (atomic, never overwrites a differing hash)
# ----------------------------------------------------------------------------
def _atomic_write_bytes(path, data):
    tmp = path + ".tmp"
    with open(tmp, "wb") as f:
        f.write(data)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def _atomic_write_text(path, text):
    _atomic_write_bytes(path, text.encode("utf-8"))


def _store(hour_start, instrument, result):
    """Persist a HourResult to the cache. Returns the metadata dict written."""
    os.makedirs(_hour_dir(hour_start, instrument), exist_ok=True)
    bi5_path, json_path, ticks_path = _paths(hour_start, instrument)
    raw = result.raw_bytes if result.raw_bytes is not None else b""
    sha = _sha256(raw)
    meta = {
        "instrument": instrument,
        "hour_start_utc": hour_start.astimezone(timezone.utc).isoformat(),
        "url": adapter.hour_url(hour_start, instrument),
        "status": result.status,
        "http_status": result.http_status,
        "sha256_raw": sha,
        "tick_count": len(result.ticks),
        "anomalies": result.anomalies,
        "cached_at_utc": datetime.now(timezone.utc).isoformat(),
        "adapter_record_fmt": adapter.RECORD_FMT,
        "point_scale": str(adapter.POINT_SCALE),
    }
    _atomic_write_bytes(bi5_path, raw)
    _atomic_write_text(ticks_path, _ticks_blob(result.ticks))
    _atomic_write_text(json_path, json.dumps(meta, indent=2, sort_keys=True))
    return meta


# ----------------------------------------------------------------------------
# Read
# ----------------------------------------------------------------------------
def _cached_meta(hour_start, instrument):
    _, json_path, _ = _paths(hour_start, instrument)
    if not os.path.exists(json_path):
        return None
    with open(json_path, "r", encoding="utf-8") as f:
        return json.load(f)


def _read_cached(hour_start, instrument):
    """Reconstruct a HourResult from the cache (no network). None if not cached."""
    meta = _cached_meta(hour_start, instrument)
    if meta is None:
        return None
    bi5_path, _, ticks_path = _paths(hour_start, instrument)
    with open(bi5_path, "rb") as f:
        raw = f.read()
    with open(ticks_path, "r", encoding="utf-8") as f:
        blob = f.read()
    ticks = _load_ticks_blob(blob, hour_start, instrument)
    return adapter.HourResult(
        instrument, hour_start, meta["status"], ticks=ticks, raw_bytes=raw,
        anomalies=meta.get("anomalies", []), http_status=meta.get("http_status"))


# ----------------------------------------------------------------------------
# Public API
# ----------------------------------------------------------------------------
class HashChangedError(Exception):
    """Raised when a fresh download of an already-cached hour has a different
    SHA-256 than the immutable copy on disk. History is never silently rewritten."""


def get_hour(when, instrument=adapter.INSTRUMENT, refresh=False, timeout=adapter.DEFAULT_TIMEOUT,
             opener=None):
    """Return a HourResult for the hour containing `when`, using the cache.

    * Cache HIT  -> served from disk, no network.
    * Cache MISS -> fetched via the adapter, then stored immutably.
    * refresh=True -> re-fetch even on a hit AND verify the hash is unchanged;
      a changed hash raises HashChangedError (loud, never a silent overwrite).

    ERROR results (network failures) are returned but NOT cached — we never pin a
    failure as if it were the truth of an hour.
    """
    hour_start = adapter._floor_hour(when)
    mem_key = (hour_start.isoformat(), instrument)
    if not refresh and mem_key in _MEM:
        return _MEM[mem_key]
    cached = None if refresh else _read_cached(hour_start, instrument)
    if cached is not None:
        _MEM[mem_key] = cached
        return cached

    fresh = adapter.get_hour(hour_start, instrument, timeout=timeout, opener=opener)

    # Immutability check FIRST, on the raw bytes, independent of decode success:
    # an upstream change must be caught even if the changed bytes no longer decode.
    if refresh:
        prior = _cached_meta(hour_start, instrument)
        if prior is not None and fresh.raw_bytes is not None:
            new_sha = _sha256(fresh.raw_bytes)
            if new_sha != prior["sha256_raw"]:
                raise HashChangedError(
                    f"{instrument} {hour_start.isoformat()}: cached sha "
                    f"{prior['sha256_raw'][:12]}... != fresh {new_sha[:12]}... "
                    f"(immutable hour changed upstream — investigate, do NOT overwrite)")

    if fresh.status == "ERROR":
        return fresh  # do not cache transient failures
    _store(hour_start, instrument, fresh)
    _MEM[mem_key] = fresh
    return fresh


def verify_cached(hour_start, instrument=adapter.INSTRUMENT):
    """Re-derive everything from the cached raw bytes and confirm it still matches
    the stored metadata + normalised ticks. Returns (ok, list_of_problems).

    This is the reproducibility proof: cached raw bytes -> re-decode -> identical
    normalised tick blob and identical hash as recorded.
    """
    problems = []
    meta = _cached_meta(hour_start, instrument)
    if meta is None:
        return False, ["not cached"]
    bi5_path, _, ticks_path = _paths(hour_start, instrument)
    with open(bi5_path, "rb") as f:
        raw = f.read()
    if _sha256(raw) != meta["sha256_raw"]:
        problems.append("raw .bi5 sha256 != metadata sha256 (raw file corrupted)")
    try:
        reticks = adapter.decode_ticks(raw, hour_start, instrument)
    except ValueError as e:
        return False, [f"re-decode failed: {e}"]
    if len(reticks) != meta["tick_count"]:
        problems.append(f"tick count {len(reticks)} != metadata {meta['tick_count']}")
    with open(ticks_path, "r", encoding="utf-8") as f:
        stored_blob = f.read()
    if _ticks_blob(reticks) != stored_blob:
        problems.append("re-decoded ticks != stored .ticks blob (non-reproducible!)")
    return (len(problems) == 0), problems


# ----------------------------------------------------------------------------
# CLI:  python price_cache.py YYYY-MM-DDTHH  [--verify]
# ----------------------------------------------------------------------------
if __name__ == "__main__":
    import sys
    when = datetime.fromisoformat(sys.argv[1]).replace(tzinfo=timezone.utc)
    r = get_hour(when)
    print(r)
    ok, probs = verify_cached(adapter._floor_hour(when))
    print("verify:", "OK" if ok else f"FAIL {probs}")
