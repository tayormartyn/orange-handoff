"""
limits.py — daily / weekly loss-limit tracker (CPS).

Reads the paper log, adds up realised P&L per day and per week, and prints a
clear STOP warning whenever a loss limit has been hit:

    Daily 2% loss limit reached  -> stop trading for the day
    Weekly 10% loss limit reached -> stop trading for the week

In PAPER mode this only WARNS — it never blocks logging. It's the discipline
rail you'll lean on once trades are live.

  * run.py calls today_warnings() at the top of each loop, so you see a STOP
    warning the moment today's (or this week's) paper losses cross the line.
  * Run it on its own for a full retrospective audit of every breached day/week:

        python limits.py

Limits are measured against the pot in config.POT_SIZE (a fixed reference
balance — simple and predictable for paper review).
"""

from dataclasses import dataclass, field
from datetime import datetime, date
from decimal import Decimal

import config
import review   # reuse the realised-R / P&L logic so there's one source of truth

# Warn (but still allow) when realised losses come within this fraction of the
# pot of a limit — e.g. 0.5% of pot of room left before the 2%/10% caps.
WARN_BUFFER_PCT = Decimal("0.005")


def _balance_ref() -> Decimal:
    return Decimal(config.POT_SIZE)


def _daily_limit_cash() -> Decimal:
    return _balance_ref() * Decimal(config.DAILY_LOSS_LIMIT)


def _weekly_limit_cash() -> Decimal:
    return _balance_ref() * Decimal(config.WEEKLY_LOSS_LIMIT)


def _day_key(ts: str):
    """Date part of an ISO timestamp -> a date object (or None if unreadable)."""
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts).date()
    except ValueError:
        try:
            return date.fromisoformat(ts[:10])
        except ValueError:
            return None


def _week_key(d: date):
    """(ISO year, ISO week) for grouping a date into its week."""
    iso = d.isocalendar()
    return (iso[0], iso[1])


def _sum_pnl_by(closed, keyfunc):
    """Map key -> summed realised P&L (Decimal)."""
    totals = {}
    for t in closed:
        d = _day_key(t.get("timestamp", ""))
        if d is None:
            continue
        k = keyfunc(d)
        totals[k] = totals.get(k, Decimal("0")) + t["pnl"]
    return totals


def status(path: str = None):
    """
    Return a dict describing every breached day and week across the whole log,
    plus the limit amounts used. P&L is realised P&L from closed trades.
    """
    closed, _missed, _ = review.load_closed_trades(path)

    daily = _sum_pnl_by(closed, lambda d: d)
    weekly = _sum_pnl_by(closed, _week_key)

    daily_cap = _daily_limit_cash()
    weekly_cap = _weekly_limit_cash()

    breached_days = sorted(
        (d, pnl) for d, pnl in daily.items() if pnl <= -daily_cap
    )
    breached_weeks = sorted(
        (w, pnl) for w, pnl in weekly.items() if pnl <= -weekly_cap
    )
    return {
        "daily": daily,
        "weekly": weekly,
        "daily_cap": daily_cap,
        "weekly_cap": weekly_cap,
        "breached_days": breached_days,
        "breached_weeks": breached_weeks,
        "n_closed": len(closed),
    }


def today_warnings(path: str = None, today: date = None) -> list:
    """
    Warning lines (possibly empty) for the CURRENT day and week — what run.py
    shows at the top of each loop. Pass `today` to test; defaults to now().
    """
    today = today or datetime.now().date()
    try:
        st = status(path)
    except review.ReviewError:
        return []   # no log yet — nothing to warn about

    cur = config.CURRENCY
    warns = []

    day_pnl = st["daily"].get(today, Decimal("0"))
    if day_pnl <= -st["daily_cap"]:
        warns.append(
            f"** STOP — Daily {Decimal(config.DAILY_LOSS_LIMIT) * 100:.0f}% loss limit "
            f"reached (today {cur}{day_pnl:,.2f}, limit {cur}-{st['daily_cap']:,.2f}). "
            "Stop trading for the day."
        )

    wk = _week_key(today)
    week_pnl = st["weekly"].get(wk, Decimal("0"))
    if week_pnl <= -st["weekly_cap"]:
        warns.append(
            f"** STOP — Weekly {Decimal(config.WEEKLY_LOSS_LIMIT) * 100:.0f}% loss limit "
            f"reached (this week {cur}{week_pnl:,.2f}, limit {cur}-{st['weekly_cap']:,.2f}). "
            "Stop trading for the week."
        )
    return warns


def print_today_banner(path: str = None):
    """Print today's STOP warnings (if any) — used by run.py."""
    for w in today_warnings(path):
        print("  " + w)


# ----------------------------------------------------------------------------
# Circuit breaker — the hard guardrail wired into pipeline.py
# ----------------------------------------------------------------------------
@dataclass
class CircuitDecision:
    """
    The verdict the pipeline acts on. `blocked` True means refuse the new trade
    (a limit is already breached). `warnings` are 'close to a limit' notices that
    still allow the trade. `lines` are human-readable status for the stage banner.
    """
    blocked: bool = False
    block_reason: str = ""
    warnings: list = field(default_factory=list)
    lines: list = field(default_factory=list)


def circuit_breaker(path: str = None, today: date = None) -> CircuitDecision:
    """
    Decide whether a NEW trade may proceed, from the realised losses already in
    the log (today for the daily limit, this ISO week for the weekly limit).

    Daily limit = DAILY_LOSS_LIMIT (2%) of the pot; weekly = WEEKLY_LOSS_LIMIT
    (10%). Reads the actual paper_log.csv so it reflects real logged outcomes.

    PAPER MODE: the only thing this 'blocks' is the pipeline proceeding to size
    and log a new paper trade. It never touches a live order — there is none.
    """
    cur = config.CURRENCY
    today = today or datetime.now().date()
    dec = CircuitDecision()

    try:
        st = status(path)
    except review.ReviewError:
        # No log yet -> no realised losses -> nothing to limit.
        dec.lines.append("No logged results yet — nothing to limit. Clear to proceed.")
        return dec

    pot = _balance_ref()
    buffer = pot * WARN_BUFFER_PCT
    daily_cap = st["daily_cap"]
    weekly_cap = st["weekly_cap"]
    day_pnl = st["daily"].get(today, Decimal("0"))
    week_pnl = st["weekly"].get(_week_key(today), Decimal("0"))

    daily_pct = Decimal(config.DAILY_LOSS_LIMIT) * 100
    weekly_pct = Decimal(config.WEEKLY_LOSS_LIMIT) * 100

    dec.lines.append(
        f"Today : {cur}{day_pnl:,.2f} realised   "
        f"(limit {cur}-{daily_cap:,.2f} = {daily_pct:.0f}% of pot)"
    )
    dec.lines.append(
        f"Week  : {cur}{week_pnl:,.2f} realised   "
        f"(limit {cur}-{weekly_cap:,.2f} = {weekly_pct:.0f}% of pot)"
    )

    daily_breached = day_pnl <= -daily_cap
    weekly_breached = week_pnl <= -weekly_cap

    if daily_breached:
        dec.blocked = True
        dec.block_reason = (
            f"CIRCUIT BREAKER: daily {daily_pct:.0f}% loss limit reached "
            f"({cur}{day_pnl:,.2f} today) — no new trades today. "
            "The machine is protecting your capital."
        )
    elif weekly_breached:
        dec.blocked = True
        dec.block_reason = (
            f"CIRCUIT BREAKER: weekly {weekly_pct:.0f}% loss limit reached "
            f"({cur}{week_pnl:,.2f} this week) — no new trades this week. "
            "The machine is protecting your capital."
        )

    # 'Close to a limit' warnings — only when not already blocked on that limit.
    if not daily_breached and day_pnl <= -(daily_cap - buffer):
        room = daily_cap + day_pnl   # day_pnl is negative -> remaining loss room
        dec.warnings.append(
            f"WARNING: close to the daily {daily_pct:.0f}% limit — only "
            f"{cur}{room:,.2f} of loss room left today before new trades are blocked."
        )
    if not weekly_breached and week_pnl <= -(weekly_cap - buffer):
        room = weekly_cap + week_pnl
        dec.warnings.append(
            f"WARNING: close to the weekly {weekly_pct:.0f}% limit — only "
            f"{cur}{room:,.2f} of loss room left this week before new trades are blocked."
        )

    return dec


def main():
    try:
        st = status()
    except review.ReviewError as e:
        print("\n  " + str(e) + "\n")
        return

    cur = config.CURRENCY
    print("=" * 60)
    print("   LOSS-LIMIT AUDIT  (realised P&L from closed paper trades)")
    print("=" * 60)
    print(f"   Reference balance : {cur}{_balance_ref():,.2f}")
    print(f"   Daily limit       : {cur}{st['daily_cap']:,.2f}  "
          f"({Decimal(config.DAILY_LOSS_LIMIT) * 100:.0f}%)")
    print(f"   Weekly limit      : {cur}{st['weekly_cap']:,.2f}  "
          f"({Decimal(config.WEEKLY_LOSS_LIMIT) * 100:.0f}%)")
    print(f"   Closed trades     : {st['n_closed']}")
    print("-" * 60)

    if not st["breached_days"] and not st["breached_weeks"]:
        print("  No day or week breached its loss limit. Discipline intact.")
    else:
        if st["breached_days"]:
            print("  Days that hit the 2% daily loss limit:")
            for d, pnl in st["breached_days"]:
                print(f"    {d.isoformat()}  {cur}{pnl:,.2f}   -> stop for the day")
        if st["breached_weeks"]:
            print("  Weeks that hit the 10% weekly loss limit:")
            for (yr, wk), pnl in st["breached_weeks"]:
                print(f"    {yr}-W{wk:02d}  {cur}{pnl:,.2f}   -> stop for the week")
    print("=" * 60)


if __name__ == "__main__":
    main()
