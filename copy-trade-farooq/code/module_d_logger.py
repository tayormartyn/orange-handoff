"""
module_d_logger.py — the PAPER logger.

Appends one row per confirmed, sized signal to paper_log.csv. That's all it does.

There is NO broker connection here. No order is placed. The place where live
execution *would* one day go is stubbed out, clearly marked, and guarded so it
cannot run unless MODE is deliberately changed to "LIVE" (which the README tells
you not to do yet).
"""

import csv
import os
from datetime import datetime, timezone
from decimal import Decimal

import config
from models import Ticket

# Analysis-grade columns (matches the CPS journal's structure). Capturing entry,
# SL, lots, dollar-risk and the ladder is exactly what lets you compute REAL
# expectancy later — a pips-only "92% win rate" log can't.
#
# Filled automatically at log time:
#   timestamp..rr_ladder, cash_at_risk, notional, asset_verified
# Filled automatically by the router (when logged via pipeline.py):
#   trader, channel, venue, route_class
# Filled by YOU later (when a trade closes):
#   outcome, tps_hit, notes
# Computed for you by review.py from tps_hit + dollar_risk:
#   realised_rr, pnl, balance, pct_return
FIELDNAMES = [
    "timestamp",
    "ticker",
    "asset_class",
    "direction",
    "source",
    "session",
    "level_tf",
    "trader",        # router: normalised trader tag (e.g. FAROUK)
    "channel",       # router: which channel it came from, if known
    "venue",         # router: intended venue PLACEHOLDER (no execution)
    "route_class",   # router: finer asset class (GOLD/SILVER/CRYPTO/FOREX)
    "confidence",    # router: signal-quality tag from the trader's risk flags (HIGH/NORMAL/LOW)
    "entry",
    "sl_price",
    "tp1",
    "tp2",
    "tp3",
    "lots",
    "sl_dollar",
    "slippage",      # per-side price slippage modelled into the entry (honest fills)
    "phase",
    "risk_pct",
    "dollar_risk",
    "rr_ladder",
    "cash_at_risk",
    "notional",
    "asset_verified",
    "outcome",       # legacy single-exit code: 1/2/3/4, SL, BE  (optional)
    "tps_hit",       # CPS scale-out: how far it ran -> 0/1/2/3 (or SL). Fill this in.
    "realised_rr",   # computed by review.py (you can override by typing a number)
    "pnl",           # computed by review.py
    "balance",       # computed by review.py
    "pct_return",    # computed by review.py
    "notes",         # free text (e.g. "SL/TPs estimated from a typo'd signal")
]


def _s(value) -> str:
    """Decimal/None -> clean string ('' for None)."""
    return "" if value is None else str(value)


def _route(routing, attr) -> str:
    """Read a routing tag from a RoutingDecision OR a dict, '' if absent."""
    if routing is None:
        return ""
    if isinstance(routing, dict):
        return _s(routing.get(attr, ""))
    return _s(getattr(routing, attr, ""))


def _ensure_columns(path: str):
    """
    If an existing log predates the routing columns, rewrite it once with the
    full header, back-filling the new columns as blank. This keeps appended rows
    lined up with the header so review.py / outcome.py keep reading by name.
    Purely additive — no existing data is changed.
    """
    if not os.path.exists(path):
        return
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        header = reader.fieldnames
        if not header or not (set(FIELDNAMES) - set(header)):
            return  # nothing missing — already current
        rows = list(reader)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({k: (row.get(k) or "") for k in FIELDNAMES})


def log_ticket(ticket: Ticket, path: str = None, routing=None) -> str:
    """
    Append the ticket to the paper log CSV, creating the file (with a header)
    on first use. Returns the path written to.

    `routing` is an optional RoutingDecision (or dict) from module_router — when
    given, its tags (trader, channel, venue, finer asset class) are recorded too.
    """
    path = path or config.PAPER_LOG_FILE
    file_is_new = not os.path.exists(path)
    _ensure_columns(path)  # migrate an older log to the routing-aware header

    s = ticket.signal
    row = {
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "ticker": s.ticker,
        "asset_class": ticket.asset_class,
        "direction": s.direction,
        "source": s.source,
        "session": s.session,
        "level_tf": s.level_tf,
        "trader": _route(routing, "trader"),
        "channel": _route(routing, "channel"),
        "venue": _route(routing, "venue"),
        "route_class": _route(routing, "asset_class"),
        "confidence": _route(routing, "confidence"),
        "entry": _s(ticket.sizing_entry),
        "sl_price": _s(ticket.stop_loss),
        "tp1": _s(ticket.tp1),
        "tp2": _s(ticket.tp2),
        "tp3": _s(ticket.tp3),
        "lots": _s(ticket.lots),
        "sl_dollar": _s(ticket.sl_dollar),
        "slippage": _s(ticket.slippage),
        "phase": _s(ticket.phase),
        "risk_pct": _s(ticket.risk_pct),
        "dollar_risk": _s(ticket.dollar_risk),
        "rr_ladder": " | ".join(
            f"T{i}={rr.quantize(Decimal('0.01'))}:1"
            for i, rr in enumerate(ticket.rr_targets, start=1)
        ),
        "cash_at_risk": _s(ticket.cash_at_risk),
        "notional": _s(ticket.notional),
        "asset_verified": "yes" if ticket.asset_verified else "CONFIRM-WITH-BROKER",
        "outcome": "",       # you fill in later
        "tps_hit": "",       # you fill in later (CPS scale-out: 0/1/2/3 or SL)
        "realised_rr": "",   # review.py computes this
        "pnl": "",           # review.py computes this
        "balance": "",       # review.py computes this
        "pct_return": "",    # review.py computes this
        "notes": "",         # free text
    }

    with open(path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        if file_is_new:
            writer.writeheader()
        writer.writerow(row)

    # ========================================================================
    # LIVE EXECUTION STUB — DISABLED IN THIS BUILD.
    #
    # This is the ONLY place a real order would ever be sent. It is deliberately
    # not implemented. Do not implement it until paper data has been reviewed
    # and you have decided the signal feed has a real edge.
    # ========================================================================
    if config.MODE == "LIVE":
        raise RuntimeError(
            "LIVE mode is disabled in this build. No live execution code exists. "
            "Set MODE back to 'PAPER' in config.py."
        )
        # When (and only when) live trading is built, broker order placement
        # would go here — sized exactly as the ticket above describes.

    return path
