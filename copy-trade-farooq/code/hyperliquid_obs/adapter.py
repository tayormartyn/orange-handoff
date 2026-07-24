"""
H1 — offline observation orchestrator (mock + replay). No network, no signing, READ-ONLY.

This module turns raw public payloads (as returned by /info and the public WS) into
classified, append-only observations, driving the connection state machine end to end.
It defines NO order/transfer/signing method and connects to nothing — the live connector is
a separate module, used only after this offline path is proven and separately approved.

Payload parsing is tolerant of the documented public shapes:
  meta   : {"universe":[{"name","szDecimals","maxLeverage"}, ...]}
  l2Book : {"coin","time","levels":[[bids],[asks]]}
  trades : [{"coin","side","px","sz","time","hash","tid"}, ...]
"""
from __future__ import annotations

from . import config
from .instruments import resolve_perp, parse_universe
from .observations import BookSnapshot, TradeTick, ObsContext
from .observation_db import ObservationDB
from .states import WSConnectionStateMachine


def frame_to_book(data: dict, local_recv_ms) -> BookSnapshot:
    levels = data.get("levels") or [[], []]
    bids = levels[0] if len(levels) > 0 else []
    asks = levels[1] if len(levels) > 1 else []
    return BookSnapshot(coin=data.get("coin"), bids=list(bids), asks=list(asks),
                        exch_time_ms=data.get("time"), local_recv_ms=local_recv_ms)


def frame_to_trades(data, local_recv_ms) -> list:
    items = data if isinstance(data, list) else [data]
    out = []
    for d in items:
        if not isinstance(d, dict):
            continue
        out.append(TradeTick(coin=d.get("coin"), side=d.get("side"), px=d.get("px"),
                             sz=d.get("sz"), exch_time_ms=d.get("time"), local_recv_ms=local_recv_ms,
                             tid=d.get("tid"), txhash=d.get("hash")))
    return out


class OfflineReplayObserver:
    """Replays a recorded public session deterministically through the full pipeline.

    `meta` is the /info meta dict; `frames` is an ordered list of
    {"channel": "l2Book"|"trades", "data": ..., "local_recv_ms": int}.
    Identical input -> identical DB logical hash.
    """

    def __init__(self, meta: dict, frames: list, *, db: ObservationDB = None,
                 environment="testnet", clock=None, max_age_ms=None):
        self.meta = meta
        self.frames = list(frames)
        self.db = db or ObservationDB(":memory:")
        self.environment = environment
        self.sm = WSConnectionStateMachine(clock=clock)
        self.max_age_ms = max_age_ms if max_age_ms is not None else config.DEFAULT_MAX_AGE_MS
        self.perp = None
        self._prev_book = None
        self._seen_tids = set()
        self._last_trade_ms = None

    def _ctx(self):
        return ObsContext(connected=True, env_verified_testnet=True,
                          symbol_verified=self.perp is not None, max_age_ms=self.max_age_ms)

    def run(self):
        self.sm.transition("CONNECTING", "offline replay start")
        self.sm.transition("CONNECTED", "transport up (replay)")
        self.db.append_connection_event(environment=self.environment, endpoint=None,
                                        connection_state="CONNECTED", reason_code="replay")
        # identify BTC perp from the RETURNED metadata (never assumed)
        universe = parse_universe(self.meta)
        self.perp = resolve_perp(self.meta, config.TARGET_PERP_NAME)
        self.sm.transition("META_LOADED", "meta parsed")
        self.sm.transition("SYMBOL_VERIFIED", f"{self.perp.name} perp id={self.perp.asset_id}")
        self.db.append_instrument_observation(self.perp, environment=self.environment,
                                              universe_size=len(universe))
        self.sm.transition("SUBSCRIBED", "l2Book+trades subscribed (replay)")
        self.sm.transition("STREAMING", "frames flowing")

        results = {"book": [], "trade": []}
        for fr in self.frames:
            ch, data, lrm = fr.get("channel"), fr.get("data"), fr.get("local_recv_ms")
            if ch == "l2Book":
                snap = frame_to_book(data, lrm)
                status = self.db.append_book_observation(snap, environment=self.environment,
                                                         ctx=self._ctx(), prev=self._prev_book)
                results["book"].append(status)
                if status not in ("DUPLICATE", "OUT_OF_ORDER", "EMPTY_BOOK", "ONE_SIDED",
                                  "INVALID_VALUE", "INVALID_TIMESTAMP"):
                    self._prev_book = snap
            elif ch == "trades":
                for t in frame_to_trades(data, lrm):
                    status = self.db.append_trade_observation(
                        t, environment=self.environment, ctx=self._ctx(),
                        seen_tids=self._seen_tids, last_trade_time_ms=self._last_trade_ms)
                    results["trade"].append(status)
                    if status == "TRADE_ADMISSIBLE":
                        if t.tid is not None:
                            self._seen_tids.add(t.tid)
                        try:
                            self._last_trade_ms = int(t.exch_time_ms)
                        except (TypeError, ValueError):
                            pass
        return results

    def disconnect(self, reason="clean shutdown"):
        if self.sm.state in ("STREAMING", "STALLED", "SUBSCRIBED", "CONNECTED",
                             "META_LOADED", "SYMBOL_VERIFIED", "CONNECTING"):
            self.sm.transition("CLOSING", reason)
            self.sm.transition("CLOSED", reason)
            self.db.append_connection_event(environment=self.environment, endpoint=None,
                                            connection_state="CLOSED", reason_code=reason,
                                            reconnect_count=self.sm.reconnects)
        return self.sm.state

    def logical_hash(self):
        return self.db.logical_hash()
