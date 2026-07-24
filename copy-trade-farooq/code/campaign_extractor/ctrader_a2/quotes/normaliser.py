"""
Deterministic XAUUSD spot normaliser.

cTrader spot bid/ask are OPTIONAL uint64s scaled by 100000. Rules:
- preserve every raw value; convert by /100000; round to the symbol's digits;
- NEVER invent a missing side (None stays None; nothing becomes 0);
- retain the latest-known bid and ask, recording WHICH event supplied each (provenance);
- compute spread ONLY when both sides are known AND fresh;
- flag negative / stale / malformed; never silently discard an incomplete event.
"""
from __future__ import annotations

SCALE = 100000


class SpotNormaliser:
    def __init__(self, digits, scale=SCALE, stale_after_ns=None):
        self.digits = digits
        self.scale = scale
        self.stale_after_ns = stale_after_ns          # None -> no staleness gating
        self._bid = None
        self._bid_prov = None                          # (session, seq)
        self._bid_ns = None
        self._ask = None
        self._ask_prov = None
        self._ask_ns = None

    def _conv(self, raw):
        return round(raw / self.scale, self.digits)

    def ingest(self, raw_bid, raw_ask, session, seq, monotonic_ns):
        """Ingest one spot event's raw sides; update the tracker; return a normalised record dict."""
        flags = []
        norm_bid = None
        norm_ask = None

        # ---- bid ----
        if raw_bid is not None:
            if raw_bid < 0:
                flags.append("MALFORMED_BID")          # negative raw -> do NOT adopt
            else:
                norm_bid = self._conv(raw_bid)
                self._bid, self._bid_prov, self._bid_ns = norm_bid, (session, seq), monotonic_ns
        # ---- ask ----
        if raw_ask is not None:
            if raw_ask < 0:
                flags.append("MALFORMED_ASK")
            else:
                norm_ask = self._conv(raw_ask)
                self._ask, self._ask_prov, self._ask_ns = norm_ask, (session, seq), monotonic_ns

        # ---- side presence (never discard incomplete) ----
        has_bid = raw_bid is not None
        has_ask = raw_ask is not None
        if has_bid and not has_ask:
            flags.append("BID_ONLY")
        elif has_ask and not has_bid:
            flags.append("ASK_ONLY")
        elif not has_bid and not has_ask:
            flags.append("INCOMPLETE_NO_SIDES")

        # ---- spread only when both known AND fresh ----
        spread = None
        both_known = self._bid is not None and self._ask is not None
        stale = False
        if both_known and self.stale_after_ns is not None:
            if (monotonic_ns - self._bid_ns) > self.stale_after_ns:
                stale = True
            if (monotonic_ns - self._ask_ns) > self.stale_after_ns:
                stale = True
        if both_known and not stale:
            spread = round(self._ask - self._bid, self.digits)
            if spread < 0:
                flags.append("NEGATIVE_SPREAD")        # flagged, never silently accepted
        elif both_known and stale:
            flags.append("STALE")
        if not flags:
            flags.append("OK")

        return {
            "raw_bid": raw_bid, "raw_ask": raw_ask,
            "norm_bid": norm_bid, "norm_ask": norm_ask,
            "latest_bid": self._bid, "latest_ask": self._ask,
            "bid_provenance_session": self._bid_prov[0] if self._bid_prov else None,
            "bid_provenance_seq": self._bid_prov[1] if self._bid_prov else None,
            "ask_provenance_session": self._ask_prov[0] if self._ask_prov else None,
            "ask_provenance_seq": self._ask_prov[1] if self._ask_prov else None,
            "spread": spread,
            "flags": ",".join(flags),
        }
