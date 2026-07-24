"""
module_router.py — the Signal Router (Module Router).

================================  METADATA ONLY  ===============================
The router takes a PARSED signal and does two jobs:

  1. CLASSIFIES it   — what asset class is it (GOLD / SILVER / CRYPTO / FOREX /
                       UNKNOWN), which trader called it, and which venue it WOULD
                       one day be routed to.
  2. DIRECTS it      — clean signals get a routing tag; anything UNKNOWN or
                       malformed is sent to a REVIEW bucket for human eyes,
                       rather than the router guessing.

It does NOT execute anything. It does not connect to a venue, place an order, or
move money. The "venue" it assigns is a PLACEHOLDER label (see config.VENUE_MAP)
for a step that does not exist yet. This is PAPER mode; there is no live path.
===============================================================================

Run it on its own to watch it classify the real example signals:

    python module_router.py
"""

from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from typing import List, Optional

import config
import asset_classes
import signal_quality
from models import Signal


# ----------------------------------------------------------------------------
# Configurable bits (read from config.py, with safe fallbacks)
# ----------------------------------------------------------------------------
KNOWN_TRADERS = getattr(config, "KNOWN_TRADERS", ["FAROUK", "COLUMBUS", "CHRIS"])
VENUE_MAP = getattr(config, "VENUE_MAP", {
    "GOLD": "venue_A", "SILVER": "venue_A", "FOREX": "venue_A", "CRYPTO": "venue_B",
})
VENUE_REVIEW = getattr(config, "VENUE_REVIEW", "REVIEW")

# Asset-class names. The recognition rules themselves now live in
# config.ASSET_CLASSES and are applied by asset_classes.classify() — so adding a
# new class is a config edit, not a change here.
ASSET_GOLD = asset_classes.GOLD
ASSET_SILVER = asset_classes.SILVER
ASSET_CRYPTO = asset_classes.CRYPTO
ASSET_FOREX = asset_classes.FOREX
ASSET_UNKNOWN = asset_classes.UNKNOWN

# Routing decision buckets.
BUCKET_ROUTE = "ROUTE"
BUCKET_REVIEW = "REVIEW"

UNKNOWN_TRADER = "UNKNOWN"


# ----------------------------------------------------------------------------
# The enriched result
# ----------------------------------------------------------------------------
@dataclass
class RoutingDecision:
    """
    A parsed signal enriched with routing tags. The original Signal is kept
    untouched in `.signal`; the tags below are the router's metadata.
    """
    signal: Signal
    asset_class: str                 # GOLD / SILVER / CRYPTO / FOREX / UNKNOWN
    trader: str                      # a KNOWN_TRADERS tag, or UNKNOWN
    raw_source: str                  # the original source text, kept verbatim
    channel: str                     # which channel it came from, if known
    venue: str                       # PLACEHOLDER venue label, or VENUE_REVIEW
    bucket: str                      # ROUTE or REVIEW
    confidence: str = "NORMAL"       # HIGH / NORMAL / LOW — from the trader's own risk flags
    confidence_cues: List[str] = field(default_factory=list)  # which cues were found
    review_reasons: List[str] = field(default_factory=list)  # why it needs review
    notes: List[str] = field(default_factory=list)           # non-blocking notes

    @property
    def needs_review(self) -> bool:
        return self.bucket == BUCKET_REVIEW

    def as_dict(self) -> dict:
        """Plain dict of the routing tags (handy for logging/inspection later)."""
        return {
            "ticker": _get(self.signal, "ticker"),
            "direction": _get(self.signal, "direction"),
            "asset_class": self.asset_class,
            "trader": self.trader,
            "raw_source": self.raw_source,
            "channel": self.channel,
            "venue": self.venue,
            "bucket": self.bucket,
            "confidence": self.confidence,
            "confidence_cues": list(self.confidence_cues),
            "review_reasons": list(self.review_reasons),
            "notes": list(self.notes),
        }


# ----------------------------------------------------------------------------
# Small readers (tolerate a Signal object OR a plain dict)
# ----------------------------------------------------------------------------
def _get(sig, name, default=""):
    if isinstance(sig, dict):
        return sig.get(name, default)
    return getattr(sig, name, default)


def _num(value) -> Optional[Decimal]:
    """Best-effort Decimal, or None if it isn't a readable number."""
    if value is None or value == "":
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


# ----------------------------------------------------------------------------
# Classification
# ----------------------------------------------------------------------------
def classify_asset(signal) -> str:
    """
    Finer asset class than the parser's CRYPTO/METAL split, decided by the
    shared, config-driven classifier: GOLD, SILVER, FOREX, CRYPTO, plus the
    recognised-but-not-yet-calibrated OIL / COMMODITIES / STOCKS, or UNKNOWN.

    Crucially, the structural FOREX check runs BEFORE the CRYPTO check, and
    crypto's stablecoin quote is matched as a real quote TOKEN (not a loose
    substring) — so a fiat pair like USDCAD is classified FOREX, never CRYPTO,
    even if the parser mis-hinted it (the bug that mis-tagged last night's test).
    """
    return asset_classes.classify(signal)


def classify_trader(signal) -> str:
    """Tag the trader from the `source` field against KNOWN_TRADERS, else UNKNOWN."""
    src = str(_get(signal, "source", "")).upper().strip()
    if not src:
        return UNKNOWN_TRADER
    for name in KNOWN_TRADERS:
        if name.upper() in src:          # substring: "FAROUK-GOLD" -> FAROUK
            return name.upper()
    return UNKNOWN_TRADER


def _malformed_problems(signal) -> List[str]:
    """
    Blocking problems that make a signal un-routable (-> REVIEW). These are the
    'can't even tell what this trade is' basics, NOT completeness niceties.
    """
    problems = []
    if not str(_get(signal, "ticker", "")).strip():
        problems.append("no ticker")
    if str(_get(signal, "direction", "")).upper().strip() not in ("LONG", "SHORT"):
        problems.append("direction isn't LONG or SHORT")

    lo = _num(_get(signal, "entry_low", None))
    hi = _num(_get(signal, "entry_high", None))
    if lo is None and hi is None:
        problems.append("no entry price")
    elif (lo is not None and lo <= 0) or (hi is not None and hi <= 0):
        problems.append("entry price isn't a positive number")

    sl = _num(_get(signal, "stop_loss", None))
    if sl is None:
        problems.append("no stop-loss")
    elif sl <= 0:
        problems.append("stop-loss isn't a positive number")

    return problems


# ----------------------------------------------------------------------------
# The router
# ----------------------------------------------------------------------------
def route(signal, channel: str = None) -> RoutingDecision:
    """
    Classify a parsed signal and decide where it goes. Returns a RoutingDecision
    (the signal enriched with routing tags). Routes nothing, executes nothing.

    A signal goes to the REVIEW bucket — for human eyes — when its asset class is
    UNKNOWN, when it's malformed, or when its (known) asset class has no venue
    mapping. Otherwise it's tagged ROUTE with its placeholder venue.
    """
    asset = classify_asset(signal)
    trader = classify_trader(signal)
    raw_source = str(_get(signal, "source", "")).strip()
    if channel is None:
        channel = str(_get(signal, "channel", "")).strip()

    review_reasons = _malformed_problems(signal)
    notes = []

    # A missing target list isn't fatal for routing (the exit ladder can apply
    # later), so it's a note, not a reason to bounce to review.
    if not (_get(signal, "targets", []) or []):
        notes.append("no take-profit targets listed")

    if asset == ASSET_UNKNOWN:
        review_reasons.append("asset class not recognised (not a configured asset class)")
    elif not asset_classes.is_calibrated(asset):
        # Recognised, but the engine has no trusted sizing for it yet. Do NOT
        # size it with guessed maths — hand it to a human. Flipping "calibrated"
        # to True in config.ASSET_CLASSES (with sizing/params) is all it takes
        # to start sizing the class properly later.
        review_reasons.append(
            f"Asset class {asset} recognised but not yet calibrated for sizing "
            "— human review needed."
        )

    # --- Signal-quality confidence tag (the trader's OWN risk flags) ---------
    # Information only by default: it's recorded so review.py can compare HIGH vs
    # LOW later. It does NOT change sizing and does NOT block — UNLESS the opt-in
    # config.SKIP_LOW_CONFIDENCE is on, in which case a LOW tag sends the signal
    # to human REVIEW instead of auto-processing.
    quality = signal_quality.classify(_get(signal, "raw_text", ""))
    confidence = quality.level
    confidence_cues = quality.cues
    notes.append(f"confidence: {quality.summary()}")
    if confidence == signal_quality.LOW and getattr(config, "SKIP_LOW_CONFIDENCE", False):
        review_reasons.append(
            "LOW-confidence signal and SKIP_LOW_CONFIDENCE is ON — sent to REVIEW "
            "instead of auto-processing."
        )

    # Decide the bucket and the venue.
    if review_reasons:
        bucket = BUCKET_REVIEW
        venue = VENUE_REVIEW
    else:
        venue = VENUE_MAP.get(asset, VENUE_REVIEW)
        if venue == VENUE_REVIEW:
            bucket = BUCKET_REVIEW
            review_reasons.append(f"no venue mapping for asset class {asset}")
        else:
            bucket = BUCKET_ROUTE

    return RoutingDecision(
        signal=signal,
        asset_class=asset,
        trader=trader,
        raw_source=raw_source,
        channel=channel,
        venue=venue,
        bucket=bucket,
        confidence=confidence,
        confidence_cues=confidence_cues,
        review_reasons=review_reasons,
        notes=notes,
    )


# ----------------------------------------------------------------------------
# Pretty printing
# ----------------------------------------------------------------------------
def format_decision(decision: RoutingDecision) -> str:
    s = decision.signal
    ticker = _get(s, "pair") or _get(s, "ticker") or "(no ticker)"
    direction = _get(s, "direction") or "?"

    source_txt = decision.raw_source or "(none)"
    trader_txt = decision.trader
    if decision.trader != UNKNOWN_TRADER and decision.raw_source:
        trader_txt = f"{decision.trader}   (from \"{decision.raw_source}\")"
    elif decision.trader == UNKNOWN_TRADER:
        trader_txt = f"UNKNOWN   (source: {source_txt})"

    flag = "   <-- NEEDS REVIEW" if decision.needs_review else ""
    venue_txt = "(held for review)" if decision.needs_review else decision.venue

    lines = [
        f"  {ticker}  {direction}",
        f"      asset class   : {decision.asset_class}",
        f"      trader        : {trader_txt}",
        f"      channel       : {decision.channel or '(unknown)'}",
        f"      confidence    : {decision.confidence}"
        + (f"   (cues: {', '.join(decision.confidence_cues)})"
           if decision.confidence_cues else "   (no risk/quality cues)"),
        f"      venue (later) : {venue_txt}",
        f"      decision      : {decision.bucket}{flag}",
    ]
    for reason in decision.review_reasons:
        lines.append(f"        - review: {reason}")
    for note in decision.notes:
        lines.append(f"        - note  : {note}")
    return "\n".join(lines)


# ----------------------------------------------------------------------------
# Self-test: classify the real example signals + a couple of coverage cases.
# ----------------------------------------------------------------------------
def _build(ticker, pair, direction, asset_class, e1, e2, sl, targets,
           raw, source="", channel=""):
    e1d, e2d = Decimal(str(e1)), Decimal(str(e2))
    sig = Signal(
        ticker=ticker,
        pair=pair,
        direction=direction,
        asset_class=asset_class,
        entry_low=min(e1d, e2d),
        entry_high=max(e1d, e2d),
        stop_loss=Decimal(str(sl)),
        targets=[Decimal(str(t)) for t in targets],
        raw_text=raw,
        source=source,
    )
    return sig, channel


def _run_self_test():
    # --- Your real signals --------------------------------------------------
    real = [
        _build("FET", "FET/USDT", "SHORT", "CRYPTO",
               "1.4334", "1.4721", "1.5284",
               ["1.3912", "1.3323", "1.2612", "1.1578"],
               "FET/USDT SHORT zone 1.4334-1.4721 SL 1.5284 ...",
               channel="Whale Room"),
        _build("SOL", "SOL/USDT", "LONG", "CRYPTO",
               "131.20", "134.65", "127.15",
               ["138.80", "143.50", "149.00", "156.00"],
               "SOL/USDT LONG zone 131.20-134.65 SL 127.15 ...",
               channel="Whale Room"),
        _build("PEPE", "PEPE/USDT", "SHORT", "CRYPTO",
               "0.00001221", "0.00001258", "0.00001306",
               ["0.0000118", "0.00001135", "0.0000106", "0.0000097"],
               "PEPE/USDT SHORT zone 0.00001221-0.00001258 SL 0.00001306 ...",
               channel="Whale Room"),
        _build("XAUUSD", "XAUUSD", "LONG", "METAL",
               "2292.00", "2304.50", "2274.00",
               ["2325", "2350", "2385"],
               "XAUUSD LONG zone 2292.00-2304.50 SL 2274.00 ...",
               source="COLUMBUS", channel="Columbus CPS"),
        _build("XAGUSD", "XAGUSD", "SHORT", "METAL",
               "29.850", "30.200", "30.650",
               ["29.20", "28.50", "27.30"],
               "XAGUSD SHORT zone 29.850-30.200 SL 30.650 ...",
               source="COLUMBUS", channel="Columbus CPS"),
        # The Farouk gold ones (real, from the imported batches).
        _build("XAUUSD", "XAUUSD", "SHORT", "METAL",
               "4635", "4635", "4670", [],
               "FAROUK SHORT 4635 SL 4670 (gold)",
               source="FAROUK-GOLD", channel="Farouk Gold"),
        _build("XAUUSD", "XAUUSD", "LONG", "METAL",
               "5022", "5022", "5007", ["5040", "5060"],
               "FAROUK LONG 5022 SL 5007 (limit channel)",
               source="FAROUK-LIMIT", channel="Farouk Limits"),
    ]

    # --- Extra coverage: FOREX (incl. the mis-tagged USDCAD), recognised-but-
    #     -not-calibrated (OIL / STOCKS -> REVIEW), and a malformed paste -------
    coverage = [
        _build("GBPJPY", "GBPJPY", "SHORT", "",
               "198.50", "198.90", "199.80",
               ["197.50", "196.40", "195.00"],
               "GBPJPY SHORT 198.50-198.90 SL 199.80",
               source="CHRIS", channel="Chris FX"),
        # The exact shape of last night's mis-tag: a forex pair the parser
        # wrongly hinted CRYPTO. It must now classify FOREX, not CRYPTO.
        _build("USDCAD", "USDCAD", "SHORT", "CRYPTO",
               "1.4600", "1.4600", "1.4650",
               ["1.4520"],
               "USDCAD SHORT 1.4600 SL 1.4650 (mis-tagged CRYPTO by the parser)",
               source="FAROUK", channel="Farouk FX"),
        _build("USOIL", "USOIL", "LONG", "",
               "78.50", "78.90", "77.40",
               ["80.00", "82.00"],
               "USOIL LONG 78.50-78.90 SL 77.40 (oil — recognised, not calibrated)",
               source="CHRIS", channel="Chris Energy"),
        _build("AAPL", "AAPL", "LONG", "",
               "210.00", "212.00", "205.00",
               ["220", "230"],
               "AAPL LONG 210-212 SL 205 (a stock — recognised, not calibrated)",
               source="", channel="Random tip"),
        _build("XAUUSD", "XAUUSD", "LONG", "METAL",
               "0", "0", "0", [],
               "XAUUSD LONG (broken paste — no usable entry/stop)",
               source="FAROUK", channel="Farouk Gold"),
    ]

    print("=" * 64)
    print("   SIGNAL ROUTER — CLASSIFY & ROUTE  (PAPER, metadata only)")
    print("=" * 64)
    print("   Tags each signal (asset / trader / venue) and decides ROUTE vs")
    print("   REVIEW. It connects to nothing and places no orders.")
    print("=" * 64)

    print("\n  YOUR REAL SIGNALS")
    print("  " + "-" * 60)
    for sig, channel in real:
        print(format_decision(route(sig, channel=channel)))
        print()

    print("  EXTRA COVERAGE (forex / not-yet-calibrated / malformed)")
    print("  " + "-" * 60)
    for sig, channel in coverage:
        print(format_decision(route(sig, channel=channel)))
        print()

    # Tiny summary so the routing outcome is obvious at a glance.
    everything = real + coverage
    decisions = [route(sig, channel=ch) for sig, ch in everything]
    routed = [d for d in decisions if not d.needs_review]
    review = [d for d in decisions if d.needs_review]
    print("  " + "-" * 60)
    print(f"  Summary: {len(routed)} routed, {len(review)} sent to REVIEW "
          f"(of {len(decisions)} signals).")
    by_asset = {}
    for d in decisions:
        by_asset[d.asset_class] = by_asset.get(d.asset_class, 0) + 1
    bits = ", ".join(f"{k}: {v}" for k, v in sorted(by_asset.items()))
    print(f"  By asset class: {bits}")
    print("=" * 64)


if __name__ == "__main__":
    _run_self_test()
