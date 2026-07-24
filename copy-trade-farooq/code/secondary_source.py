"""
secondary_source.py — SHADOW MODE Phase 1a, pluggable secondary price cross-check.

The brief wants an OANDA 5s-candle SECONDARY cross-check on sampled timestamps, to
catch a systematic problem in the primary (Dukascopy) feed — wrong scale, wrong
instrument, a timezone shift, a decimal error. This is a CONFIDENCE check, never a
price source for shadow fills.

It is deliberately PLUGGABLE and OPTIONAL:
  * Any source implementing SecondarySource can be dropped in.
  * If no source is configured/reachable/authenticated, the cross-check reports
    `available=False` and the coverage report records "secondary: unavailable".
    Per the agreed design this does NOT fail the GO/NO-GO — we simply cannot
    corroborate, and we say so honestly rather than pretending we did.

OANDA v20 needs an API token. In THIS environment the OANDA host is reachable but
no token is configured, so OandaS5Source reports unavailable with that exact
reason. Set OANDA_API_TOKEN (and optionally OANDA_ENV=practice|live) to enable it.

PAPER mode, read-only.
"""

import json
import os
import urllib.error
import urllib.request
from datetime import timezone
from decimal import Decimal

# How far apart the two sources may be before we call it a real divergence.
# Gold spreads are sub-$1; a healthy cross-source mid difference is a few tens of
# cents. $2 is a generous "something is structurally wrong" threshold (a scale or
# tz error would show up as tens or thousands of dollars, not cents).
DIVERGENCE_THRESHOLD = Decimal("2.0")


class SecondarySource:
    """Interface for a secondary price source used only for cross-checking."""

    name = "secondary"

    def is_available(self):
        """(available: bool, reason: str)."""
        raise NotImplementedError

    def mid_at(self, when):
        """Return (mid: Decimal, meta: dict) for the candle/quote covering `when`,
        or None if there is no data there. Raises on a transport error."""
        raise NotImplementedError


class OandaS5Source(SecondarySource):
    """OANDA v20 5-second (S5) candles for XAU_USD. Read-only."""

    name = "oanda-s5"

    def __init__(self, instrument="XAU_USD", token=None, env=None):
        self.instrument = instrument
        self.token = token or os.environ.get("OANDA_API_TOKEN")
        self.env = (env or os.environ.get("OANDA_ENV") or "practice").lower()
        self.host = ("https://api-fxtrade.oanda.com" if self.env == "live"
                     else "https://api-fxpractice.oanda.com")

    def is_available(self):
        if not self.token:
            return False, ("no OANDA_API_TOKEN configured (host reachable but "
                           "unauthenticated) — secondary cross-check unavailable")
        return True, f"OANDA {self.env} configured"

    def mid_at(self, when):
        when = when.astimezone(timezone.utc)
        # One S5 candle starting at/just before `when`: ask for a tiny window.
        frm = when.replace(microsecond=0)
        params = (f"?price=M&granularity=S5&count=1"
                  f"&from={frm.strftime('%Y-%m-%dT%H:%M:%SZ')}")
        url = f"{self.host}/v3/instruments/{self.instrument}/candles{params}"
        req = urllib.request.Request(url, headers={
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        })
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read())
        candles = data.get("candles") or []
        if not candles:
            return None
        c = candles[0]
        mid = c.get("mid") or {}
        o, h, l, cl = (Decimal(mid["o"]), Decimal(mid["h"]),
                       Decimal(mid["l"]), Decimal(mid["c"]))
        candle_mid = (h + l) / 2
        return candle_mid, {"time": c.get("time"), "ohlc_mid": [str(o), str(h),
                            str(l), str(cl)], "complete": c.get("complete")}


class NullSource(SecondarySource):
    """An explicitly-unavailable source — used when none is configured, so callers
    always have a real object and the report can state WHY corroboration is absent."""

    name = "none"

    def __init__(self, reason="no secondary source configured"):
        self.reason = reason

    def is_available(self):
        return False, self.reason

    def mid_at(self, when):
        return None


def default_source():
    """The secondary source for the runner. OANDA if a token is present, else a
    NullSource that explains the absence. Never raises."""
    oanda = OandaS5Source()
    ok, _ = oanda.is_available()
    if ok:
        return oanda
    return oanda  # OandaS5Source already reports its own unavailable reason


def cross_check(primary_mid, when, source):
    """Compare a primary mid (Decimal) against the secondary source at `when`.

    Returns a dict that is safe to log/serialise. Never raises: a transport error
    is captured as status="error" so one flaky cross-check cannot derail a run.
    """
    available, reason = source.is_available()
    if not available:
        return {"source": source.name, "status": "unavailable", "reason": reason,
                "primary_mid": str(primary_mid) if primary_mid is not None else None}
    if primary_mid is None:
        return {"source": source.name, "status": "no_primary",
                "reason": "no primary mid to compare"}
    try:
        got = source.mid_at(when)
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError) as e:
        return {"source": source.name, "status": "error", "reason": f"{type(e).__name__}: {e}"}
    if got is None:
        return {"source": source.name, "status": "no_secondary",
                "reason": "secondary had no candle at this time"}
    sec_mid, meta = got
    diff = abs(Decimal(primary_mid) - sec_mid)
    return {
        "source": source.name,
        "status": "diverges" if diff > DIVERGENCE_THRESHOLD else "agrees",
        "primary_mid": str(primary_mid),
        "secondary_mid": str(sec_mid),
        "abs_diff": str(diff),
        "threshold": str(DIVERGENCE_THRESHOLD),
        "secondary_meta": meta,
    }


if __name__ == "__main__":
    src = default_source()
    print("source:", src.name, "->", src.is_available())
