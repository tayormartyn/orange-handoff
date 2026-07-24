"""Canonical market-event contract v0.1 — deterministic, decimal-safe, append-only.

Schema id: market_event_v0_1. One record per COMPLETED bar observation.
UTC canonical; XAUUSD pip convention: 1 pip = $0.10 (pips = USD * 10).
No silent interpolation, ever: gaps/duplicates/out-of-order/revisions are DETECTED,
FLAGGED and LOGGED — never repaired invisibly.
"""
from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation

SCHEMA = "market_event_v0_1"
PIPS_PER_USD = Decimal("10")
D = Decimal


class MarketEventError(Exception):
    pass


@dataclass(frozen=True)
class MarketBar:
    instrument: str                   # "XAUUSD"
    provider: str                     # PEPPERSTONE_TV_EXPORT | DUKASCOPY_DATAFEED | SYNTHETIC_TEST
    timeframe: str                    # "1m"
    event_ts: int                     # bar OPEN epoch seconds UTC (canonical identity)
    receive_ts: int                   # when Orange observed it (provenance only, never logic)
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    bid: Decimal | None = None        # optional (tick-derived providers)
    ask: Decimal | None = None
    spread: Decimal | None = None
    source_id: str = ""               # file path / object key / fetch identity
    sequence: int = 0                 # per-source monotone counter
    completeness: str = "COMPLETE"    # COMPLETE | SUSPECT
    quality_flags: tuple = ()         # GAP_AFTER_PREVIOUS | OUT_OF_ORDER | REVISED_BAR | STALE ...
    revision: int = 1

    def logical_hash(self) -> str:
        basis = {"s": SCHEMA, "i": self.instrument, "p": self.provider, "tf": self.timeframe,
                 "t": self.event_ts, "o": str(self.open), "h": str(self.high),
                 "l": str(self.low), "c": str(self.close), "rev": self.revision}
        return hashlib.sha256(json.dumps(basis, sort_keys=True).encode()).hexdigest()

    def as_tuple(self):
        """(ts,o,h,l,c) — the exact shape the follower engine consumes."""
        return (self.event_ts, self.open, self.high, self.low, self.close)


def validate_bar(raw: dict) -> MarketBar:
    """Strict validation; raises MarketEventError (never guesses)."""
    try:
        o, h, l, c = (D(str(raw[k])) for k in ("open", "high", "low", "close"))
    except (KeyError, InvalidOperation) as e:
        raise MarketEventError(f"non-decimal OHLC: {e}")
    if not (l <= o <= h and l <= c <= h and h >= l):
        raise MarketEventError(f"OHLC inconsistent at ts {raw.get('event_ts')}")
    ts = int(raw["event_ts"])
    if ts <= 0 or ts % 60 != 0:
        raise MarketEventError(f"event_ts not a 1m boundary: {ts}")
    bid = D(str(raw["bid"])) if raw.get("bid") is not None else None
    ask = D(str(raw["ask"])) if raw.get("ask") is not None else None
    spread = (ask - bid) if (bid is not None and ask is not None) else None
    return MarketBar(
        instrument=raw.get("instrument", "XAUUSD"), provider=raw["provider"],
        timeframe=raw.get("timeframe", "1m"), event_ts=ts,
        receive_ts=int(raw.get("receive_ts", 0)),
        open=o, high=h, low=l, close=c, bid=bid, ask=ask, spread=spread,
        source_id=str(raw.get("source_id", "")), sequence=int(raw.get("sequence", 0)),
        completeness=raw.get("completeness", "COMPLETE"),
        quality_flags=tuple(raw.get("quality_flags", ())), revision=int(raw.get("revision", 1)))


class BarStream:
    """Deterministic ordered store of validated bars with duplicate / out-of-order /
    revision / gap handling and an append-only ingestion log."""

    def __init__(self, ingestion_log_path: str | None = None):
        self.bars: dict[int, MarketBar] = {}      # event_ts -> accepted bar (latest revision)
        self.hashes: set[str] = set()
        self.max_ts = 0
        self.log_path = ingestion_log_path
        self.anomalies: list[dict] = []

    def _log(self, kind, bar: MarketBar, note=""):
        rec = {"schema": SCHEMA, "kind": kind, "event_ts": bar.event_ts,
               "provider": bar.provider, "revision": bar.revision,
               "logical_hash": bar.logical_hash(), "note": note}
        if kind in ("ACCEPTED", "REVISED_BAR", "GAP", "OUT_OF_ORDER"):
            # full payload so the stream can be RESTORED after a restart (red-team CRITICAL 1)
            rec["bar"] = {"instrument": bar.instrument, "provider": bar.provider,
                          "timeframe": bar.timeframe, "event_ts": bar.event_ts,
                          "receive_ts": bar.receive_ts, "open": str(bar.open),
                          "high": str(bar.high), "low": str(bar.low), "close": str(bar.close),
                          "bid": str(bar.bid) if bar.bid is not None else None,
                          "ask": str(bar.ask) if bar.ask is not None else None,
                          "source_id": bar.source_id, "sequence": bar.sequence,
                          "revision": bar.revision}
        if kind not in ("ACCEPTED",):
            self.anomalies.append(rec)
        if self.log_path:
            with open(self.log_path, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(rec) + "\n")

    def restore(self) -> int:
        """Rebuild the stream from the append-only ingestion log (restart recovery).
        Returns bars restored. Safe to call on a fresh/absent log."""
        if not self.log_path or not os.path.exists(self.log_path):
            return 0
        n = 0
        path = self.log_path
        self.log_path = None                       # no re-logging while restoring
        try:
            with open(path, encoding="utf-8") as fh:
                for line in fh:
                    try:
                        rec = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    b = rec.get("bar")
                    if not b or rec.get("kind") not in ("ACCEPTED", "REVISED_BAR",
                                                        "GAP", "OUT_OF_ORDER"):
                        continue
                    try:
                        self.ingest(validate_bar(b))
                        n += 1
                    except MarketEventError:
                        continue                    # duplicates/conflicts on replay are fine
        finally:
            self.log_path = path
        return n

    def ingest(self, bar: MarketBar) -> str:
        """-> ACCEPTED | DUPLICATE | REVISED_BAR | OUT_OF_ORDER_ACCEPTED. Raises on conflict
        without a declared revision (silent mutation refused)."""
        lh = bar.logical_hash()
        if lh in self.hashes:
            self._log("DUPLICATE", bar, "identical bar already ingested")
            return "DUPLICATE"
        prev = self.bars.get(bar.event_ts)
        if prev is not None:
            if bar.revision > prev.revision:
                bar = _flag(bar, "REVISED_BAR")
                self.bars[bar.event_ts] = bar
                self.hashes.add(lh)
                self._log("REVISED_BAR", bar, f"replaced revision {prev.revision}")
                return "REVISED_BAR"
            raise MarketEventError(
                f"conflicting bar at ts {bar.event_ts} without a higher revision — refused")
        flags = []
        if self.max_ts and bar.event_ts < self.max_ts:
            flags.append("OUT_OF_ORDER")
        if self.max_ts and bar.event_ts > self.max_ts + 60:
            flags.append("GAP_AFTER_PREVIOUS")
        if flags:
            bar = _flag(bar, *flags)
        self.bars[bar.event_ts] = bar
        self.hashes.add(lh)
        self.max_ts = max(self.max_ts, bar.event_ts)
        if "OUT_OF_ORDER" in flags:
            self._log("OUT_OF_ORDER", bar)
            return "OUT_OF_ORDER_ACCEPTED"
        if "GAP_AFTER_PREVIOUS" in flags:
            self._log("GAP", bar, "missing bar(s) before this one — no interpolation performed")
        self._log("ACCEPTED", bar)
        return "ACCEPTED"

    def ordered(self) -> list[MarketBar]:
        return [self.bars[t] for t in sorted(self.bars)]

    def ordered_tuples(self):
        return [b.as_tuple() for b in self.ordered()]

    def stream_hash(self) -> str:
        return hashlib.sha256("".join(b.logical_hash() for b in self.ordered()).encode()).hexdigest()

    def gaps(self):
        ts = sorted(self.bars)
        return [(a, b) for a, b in zip(ts, ts[1:]) if b - a > 60]

    def staleness_seconds(self, now_ts: int) -> int:
        return now_ts - (self.max_ts + 60) if self.max_ts else -1


def _flag(bar: MarketBar, *flags) -> MarketBar:
    return MarketBar(**{**bar.__dict__, "quality_flags": tuple(bar.quality_flags) + flags})
