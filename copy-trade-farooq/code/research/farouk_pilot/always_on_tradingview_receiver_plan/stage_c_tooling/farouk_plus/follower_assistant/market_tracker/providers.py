"""Provider-neutral market-data adapters (READ-ONLY, no execution surface possible).

  * ReplayCSVProvider    — frozen historical Pepperstone TradingView exports (MODE 1)
  * FileTailProvider     — incrementally appended/replaced candle CSV (MODE 2)
  * DukascopyBarProvider — LIVE_READ_ONLY boundary over the EXISTING proven
                           dukascopy_adapter.py (credential-free public HTTPS datafeed,
                           bid/ask ticks aggregated to 1m bars; DELAYED ~1h by publication).
                           Network fetch happens ONLY when explicitly invoked; tests use
                           the offline aggregation path.

None of these can place, amend, or cancel anything anywhere: they read files or perform
HTTP GETs of public historical data. No credentials exist in any path.
"""
from __future__ import annotations

import csv
import os
import sys
import time
from decimal import Decimal as D

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from market_events import MarketBar, MarketEventError, validate_bar  # noqa: E402


class MarketDataProvider:
    """Abstract boundary: completed 1m bars after a timestamp. The management engine only
    ever sees MarketBar objects — connecting a future live source touches NOTHING else."""
    name = "ABSTRACT"

    def fetch_completed_bars(self, after_ts: int) -> list[MarketBar]:
        raise NotImplementedError


class ReplayCSVProvider(MarketDataProvider):
    """MODE 1 — frozen historical bars; deterministic clock = the bar timestamps themselves."""
    name = "PEPPERSTONE_TV_EXPORT"

    def __init__(self, csv_path: str, clamp_end_ts: int | None = None):
        self.csv_path = csv_path
        self.clamp_end_ts = clamp_end_ts          # replay-to-a-point (no outcome leakage)
        self._bars = None

    def _load(self):
        if self._bars is not None:
            return
        out, seq = [], 0
        self.row_errors = []
        with open(self.csv_path, newline="", encoding="utf-8-sig") as fh:
            for r in csv.reader(fh):
                if not r or r[0] == "time":
                    continue
                seq += 1
                try:
                    out.append(validate_bar({
                        "provider": self.name, "event_ts": int(r[0]), "receive_ts": int(r[0]) + 60,
                        "open": r[1], "high": r[2], "low": r[3], "close": r[4],
                        "source_id": os.path.basename(self.csv_path), "sequence": seq}))
                except (MarketEventError, ValueError, IndexError) as e:
                    # one poison row must never stall ingestion (red-team finding 2)
                    self.row_errors.append(f"row {seq}: {e}")
        self._bars = sorted(out, key=lambda b: b.event_ts)

    def fetch_completed_bars(self, after_ts: int) -> list[MarketBar]:
        self._load()
        # clamp = knowledge point: a bar is known only once COMPLETE (event_ts + 60 <= clamp)
        # (red-team finding 13: the bar OPENING at the clamp holds 60s of future price)
        return [b for b in self._bars if b.event_ts > after_ts and
                (self.clamp_end_ts is None or b.event_ts + 60 <= self.clamp_end_ts)]


class FileTailProvider(MarketDataProvider):
    """MODE 2 — watches a CSV that grows (or is atomically replaced by a longer export).
    Only bars strictly OLDER than the newest bar in the file are treated as completed when
    the file is live-growing; a fully re-exported file is re-read idempotently (the
    BarStream dedups). Survives replacement + restart because state = only `after_ts`."""
    name = "PEPPERSTONE_TV_EXPORT_TAIL"

    def __init__(self, csv_path: str, assume_last_bar_incomplete: bool = True):
        self.csv_path = csv_path
        self.assume_last_bar_incomplete = assume_last_bar_incomplete

    def fetch_completed_bars(self, after_ts: int) -> list[MarketBar]:
        if not os.path.exists(self.csv_path):
            return []
        rows, seq = [], 0
        with open(self.csv_path, newline="", encoding="utf-8-sig") as fh:
            for r in csv.reader(fh):
                if not r or r[0] == "time":
                    continue
                seq += 1
                try:
                    rows.append((int(r[0]), r, seq))
                except ValueError:
                    continue                      # malformed timestamp row skipped
        if not rows:
            return []
        rows.sort(key=lambda x: x[0])
        if self.assume_last_bar_incomplete:
            rows = rows[:-1]                     # newest bar may still be forming
        now = int(time.time())
        out = []
        self.row_errors = []
        for t, r, s in rows:
            if t <= after_ts:
                continue
            try:
                out.append(validate_bar({"provider": self.name, "event_ts": t, "receive_ts": now,
                                         "open": r[1], "high": r[2], "low": r[3], "close": r[4],
                                         "source_id": os.path.basename(self.csv_path), "sequence": s}))
            except (MarketEventError, ValueError, IndexError) as e:
                self.row_errors.append(f"row {s}: {e}")   # poison row skipped, never stalls
        return out


class R2TvBarProvider(MarketDataProvider):
    """MODE 4 — LIVE TradingView completed-bar feed (READ-ONLY consumer).

    Producer chain (all pre-existing / write-only): TradingView alert
    ORANGE_XAUUSD_1M_BAR_FEED (minimal Pine indicator, one JSON per confirmed 1m bar)
    -> existing logging-only Worker (POST, secret path) -> R2 predictable key
    bars/{instrument}/1m/{YYYYMMDDHHMM}.json (bar-feed lane, deploy 4bcad626).

    This consumer computes expected keys from its cursor and fetches each via
    `wrangler r2 object get --remote` (account auth; no webhook secret involved; no list
    branch ever deployed). Missing keys inside the grace window are retried next cycle;
    beyond grace they are recorded as gaps (market closed / alert paused) and skipped.
    A long dark period (weekend) fast-forwards after MAX_CONSECUTIVE_GAPS to avoid
    grinding one wrangler call per dead minute.
    """
    name = "PEPPERSTONE_TV_BAR_FEED"

    def __init__(self, worker_dir: str, instrument: str = "XAUUSD",
                 grace_seconds: int = 300, max_fetch_per_cycle: int = 10,
                 max_consecutive_gaps: int = 5):
        self.worker_dir = worker_dir
        self.instrument = instrument
        self.grace = grace_seconds
        self.max_fetch = max_fetch_per_cycle
        self.max_gaps = max_consecutive_gaps
        self.row_errors = []

    def _key(self, ts: int) -> str:
        from datetime import datetime, timezone
        return f"bars/{self.instrument}/1m/{datetime.fromtimestamp(ts, timezone.utc):%Y%m%d%H%M}.json"

    def _get(self, key: str):
        import subprocess
        try:
            p = subprocess.run(["npx", "wrangler", "r2", "object", "get",
                                f"farouk-tv-webhook-evidence-v1/{key}", "--remote", "--pipe"],
                               capture_output=True, text=True, cwd=self.worker_dir,
                               timeout=120, shell=True)
            import json as _json
            for line in p.stdout.splitlines():
                if line.strip().startswith("{"):
                    return _json.loads(line)
        except Exception:                                        # noqa: BLE001
            return None
        return None

    def parse_rec(self, rec: dict, expected_ts: int, receive_ts: int):
        """Worker evidence record -> MarketBar (validated; deterministic; offline-testable)."""
        import json as _json
        inner = _json.loads(rec["raw_payload"])
        if inner.get("event_type") != "XAU_1M_BAR" or inner.get("instrument") != self.instrument:
            raise MarketEventError("record is not a bar event for this instrument")
        from datetime import datetime, timezone
        bo = int(datetime.fromisoformat(inner["bar_open_time"].replace("Z", "+00:00")).timestamp())
        if bo != expected_ts:
            raise MarketEventError(f"bar_open_time {bo} != expected key ts {expected_ts}")
        return validate_bar({
            "provider": self.name, "event_ts": bo, "receive_ts": receive_ts,
            "open": inner["open"], "high": inner["high"], "low": inner["low"],
            "close": inner["close"],
            "source_id": f"{inner.get('source', 'tv_bar')}/{inner.get('symbol', '')}",
            "sequence": bo // 60,
            "quality_flags": ("TV_ALERT_DELIVERY",)})

    def fetch_completed_bars(self, after_ts: int) -> list[MarketBar]:
        import time as _time
        now = int(_time.time())
        self.row_errors = []
        start = after_ts + 60 if after_ts > 0 else ((now - 180) // 60) * 60
        ts = start - (start % 60)
        out, fetched, consecutive_gaps = [], 0, 0
        self.cursor_hint = after_ts        # highest DEFINITIVELY resolved minute (fetched or gap)
        while ts <= now - 120 and fetched < self.max_fetch:
            rec = self._get(self._key(ts))
            if rec is None:
                if now - (ts + 60) <= self.grace:
                    break                                        # young bar: retry next cycle
                consecutive_gaps += 1
                self.row_errors.append(f"missing bar {ts} beyond grace -> gap")
                self.cursor_hint = max(self.cursor_hint, ts)     # gap resolved: never re-fetch
                if consecutive_gaps >= self.max_gaps:
                    jump = ((now - 180) // 60) * 60
                    self.row_errors.append(
                        f"{consecutive_gaps} consecutive gaps -> fast-forward {ts}->{jump} "
                        "(market closed / alert paused; coverage gap recorded)")
                    ts = jump
                    self.cursor_hint = max(self.cursor_hint, jump - 60)
                    consecutive_gaps = 0
                    continue
                ts += 60
                continue
            consecutive_gaps = 0
            try:
                out.append(self.parse_rec(rec, ts, now))
                fetched += 1
                self.cursor_hint = max(self.cursor_hint, ts)
            except MarketEventError as e:
                self.row_errors.append(f"bar {ts}: {e}")
                self.cursor_hint = max(self.cursor_hint, ts)
            ts += 60
        return out


class DukascopyBarProvider(MarketDataProvider):
    """MODE 3 — LIVE_READ_ONLY (delayed) boundary over the repo's proven adapter.

    Uses signal-terminal/dukascopy_adapter.py (public datafeed, NO credentials, stdlib
    HTTPS GET, bid/ask ticks). Publication is hourly -> latency up to ~1-2h. Feed is NOT
    Pepperstone: every consumer must treat levels within the $3 band as FEED_SENSITIVE
    (VR-21). Aggregation tick->1m is deterministic; bid/ask mid is the bar price basis,
    with bid/ask extremes preserved.
    """
    name = "DUKASCOPY_DATAFEED"

    def __init__(self, st_root: str):
        self.st_root = st_root

    @staticmethod
    def aggregate_ticks(ticks, hour_start_ts: int, receive_ts: int, source_id: str):
        """ticks: iterable of (ms_in_hour, bid_decimal, ask_decimal). Deterministic 1m bars
        from MID price; bars with zero ticks are ABSENT (no interpolation)."""
        buckets = {}
        for ms, bid, ask in ticks:
            mts = hour_start_ts + (int(ms) // 60000) * 60
            mid = (D(bid) + D(ask)) / 2
            b = buckets.setdefault(mts, {"o": mid, "h": mid, "l": mid, "c": mid,
                                         "bid": D(bid), "ask": D(ask), "first_ms": ms})
            b["h"] = max(b["h"], mid)
            b["l"] = min(b["l"], mid)
            b["c"] = mid
            b["bid"], b["ask"] = D(bid), D(ask)
        out = []
        for i, (mts, b) in enumerate(sorted(buckets.items())):
            out.append(validate_bar({
                "provider": DukascopyBarProvider.name, "event_ts": mts, "receive_ts": receive_ts,
                "open": b["o"], "high": b["h"], "low": b["l"], "close": b["c"],
                "bid": b["bid"], "ask": b["ask"], "source_id": source_id, "sequence": i + 1,
                "quality_flags": ("DELAYED_PUBLICATION", "NON_PEPPERSTONE_FEED")}))
        return out

    def fetch_completed_bars(self, after_ts: int) -> list[MarketBar]:
        if self.st_root not in sys.path:
            sys.path.insert(0, self.st_root)
        import dukascopy_adapter                                    # existing proven module
        from datetime import datetime, timezone
        out = []
        now = int(time.time())
        # fetch the (at most 3) most recent fully-published UTC hours after the cursor
        hour = (max(after_ts, now - 4 * 3600) // 3600) * 3600
        while hour + 3600 <= now - 3600 and len(out) < 3 * 60:
            dt = datetime.fromtimestamp(hour, timezone.utc)
            res = dukascopy_adapter.get_hour(dt)                    # adapter's proven entrypoint
            ticks = [(t.epoch_ms - hour * 1000, t.bid, t.ask)
                     for t in (getattr(res, "ticks", None) or [])]
            if ticks:
                out.extend(self.aggregate_ticks(
                    ticks, hour, now, f"dukascopy/{dt:%Y-%m-%d}/{dt:%H}h"))
            hour += 3600
        return [b for b in out if b.event_ts > after_ts]
