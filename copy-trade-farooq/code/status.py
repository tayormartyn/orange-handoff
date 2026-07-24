"""
status.py — the operation status dashboard (PAPER MODE, READ-ONLY).

One command:

    python status.py

shows the whole state of your operation at a glance: mode and risk settings,
today's circuit-breaker headroom, your overall edge (win rate / expectancy after
slippage / net R and £), a per-trader breakdown, how many trades still need an
outcome, and a loud, unmissable execution-status line.

It READS paper_log.csv and config.py and prints. It changes nothing, logs
nothing, places nothing, and never touches the LIVE stub. It reuses review.py and
limits.py so every number matches those tools exactly (one source of truth).
"""

import csv
import os
from datetime import datetime
from decimal import Decimal

import config
import review
import limits
import module_c_risk as risk

LINE = "=" * 64
THIN = "-" * 64


# ----------------------------------------------------------------------------
# Small formatting helpers
# ----------------------------------------------------------------------------
def _money(amount) -> str:
    return f"{config.CURRENCY}{Decimal(amount).quantize(Decimal('0.01')):,}"

def _money_signed(amount) -> str:
    return f"{config.CURRENCY}{Decimal(amount).quantize(Decimal('0.01')):+,}"

def _trust_flag(n: int) -> str:
    return "" if n >= review.TRUST_MIN else "  [<30]"

def _slippage_summary() -> str:
    table = getattr(config, "SLIPPAGE", {})
    names = {"XAU": "gold", "XAG": "silver", "CRYPTO": "crypto"}
    parts = [f"{names[k]} ${table[k]}/side" for k in ("XAU", "XAG", "CRYPTO") if k in table]
    return ", ".join(parts) if parts else "none configured"


def _count_awaiting(path: str) -> int:
    """Rows logged but not yet resolved (blank outcome -> 'open'); the CONFIRM ones."""
    if not os.path.exists(path):
        return 0
    n = 0
    try:
        with open(path, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                if review.realised_r(row)[2] == "open":
                    n += 1
    except (OSError, csv.Error):
        return 0
    return n


# ----------------------------------------------------------------------------
# Sections
# ----------------------------------------------------------------------------
def _header_lines() -> list:
    today = datetime.now().strftime("%Y-%m-%d")
    risk_pct, phase, profile, _cap = risk.resolve_risk_profile()
    out = [
        LINE,
        f"   SIGNAL TERMINAL — STATUS DASHBOARD            {today}",
        LINE,
        f"  Mode            : {config.MODE}        (read-only dashboard — changes nothing)",
        f"  Pot             : {_money(config.POT_SIZE)}",
        f"  Risk per trade  : {risk_pct * 100:.2f}%   (profile {profile}"
        + (f", phase {phase}" if profile == "CPS" else "") + ")",
        f"  Slippage model  : {_slippage_summary()}",
        f"  Quality filter  : tagging ON  "
        f"(SKIP_LOW_CONFIDENCE = {getattr(config, 'SKIP_LOW_CONFIDENCE', False)}"
        + (" — LOW signals routed to REVIEW)"
           if getattr(config, "SKIP_LOW_CONFIDENCE", False)
           else " — LOW signals tagged but still processed)"),
        "",
        f"  EXECUTION       : EXECUTION_ENABLED = {getattr(config, 'EXECUTION_ENABLED', False)}",
        "                    *** LIVE TRADING DISABLED — paper only ***",
    ]
    return out


def _breaker_lines(path: str) -> list:
    out = [THIN, "  CIRCUIT BREAKER (loss limits)"]
    try:
        st = limits.status(path)
    except review.ReviewError:
        out.append("    (no log yet — nothing to limit, full room available)")
        return out

    today = datetime.now().date()
    day_pnl = st["daily"].get(today, Decimal("0"))
    week_pnl = st["weekly"].get(limits._week_key(today), Decimal("0"))
    daily_cap = st["daily_cap"]
    weekly_cap = st["weekly_cap"]
    daily_room = daily_cap + day_pnl      # day_pnl is negative when losing
    weekly_room = weekly_cap + week_pnl
    dpct = Decimal(config.DAILY_LOSS_LIMIT) * 100
    wpct = Decimal(config.WEEKLY_LOSS_LIMIT) * 100

    out.append(f"    Today : {_money_signed(day_pnl)} realised   ->  "
               f"{_money(daily_room)} room before the {dpct:.0f}% daily stop")
    out.append(f"    Week  : {_money_signed(week_pnl)} realised   ->  "
               f"{_money(weekly_room)} room before the {wpct:.0f}% weekly stop")

    breaker = limits.circuit_breaker(path)
    if breaker.blocked:
        out.append(f"    Status: BLOCKED — {breaker.block_reason}")
    else:
        out.append("    Status: CLEAR — new trades allowed")
        for w in breaker.warnings:
            out.append(f"            ** {w}")
    return out


def _segment(trades: list) -> tuple:
    """(n, winners, losers, flats, total_r, net_cash) for a list of filled trades."""
    n = len(trades)
    winners = sum(1 for t in trades if t["r"] > 0)
    losers = sum(1 for t in trades if t["r"] < 0)
    flats = sum(1 for t in trades if t["r"] == 0)
    total_r = sum((t["r"] for t in trades), Decimal("0"))
    net_cash = sum((t["pnl"] for t in trades), Decimal("0"))
    return n, winners, losers, flats, total_r, net_cash


def _overall_lines(closed: list, missed: list, awaiting: int) -> list:
    out = [THIN, "  OVERALL  (win rate & expectancy = FILLED trades only)"]
    n, w, l, flat, total_r, net_cash = _segment(closed)
    total_rows = n + len(missed) + awaiting
    out.append(f"    Trades logged : {total_rows} total  "
               f"({n} filled / {len(missed)} missed / {awaiting} awaiting outcome)")
    if n == 0:
        out.append("    No filled trades yet — win rate / expectancy need at least one.")
        return out
    expectancy = total_r / Decimal(n)
    out.append(f"    Win rate      : {review._pct(w, n)}  ({w}W / {l}L / {flat} flat)")
    out.append(f"    Expectancy    : {expectancy:+.2f} R/trade  (after modelled slippage)")
    out.append(f"    Net           : {total_r:+.2f} R   ({_money_signed(net_cash)})"
               f"{_trust_flag(n)}")
    return out


def _by_source_lines(closed: list, missed: list) -> list:
    out = [THIN, "  BY TRADER / SOURCE  (sample / fill / win / expectancy)"]
    groups = {}
    for t in closed:
        groups.setdefault(t.get("source") or "(none)", {"f": [], "m": []})["f"].append(t)
    for m in missed:
        groups.setdefault(m.get("source") or "(none)", {"f": [], "m": []})["m"].append(m)

    if not groups:
        out.append("    (no resolved trades yet)")
        return out

    # Biggest sample first.
    order = sorted(groups, key=lambda k: (-(len(groups[k]["f"]) + len(groups[k]["m"])), str(k)))
    for src in order:
        g = groups[src]
        n_f, n_m = len(g["f"]), len(g["m"])
        n = n_f + n_m
        winners = sum(1 for t in g["f"] if t["r"] > 0)
        total_r = sum((t["r"] for t in g["f"]), Decimal("0"))
        exp = (total_r / Decimal(n_f)) if n_f else Decimal("0")
        out.append(
            f"    {src:<14} {n:>3} sig   "
            f"{review._pct(n_f, n):>4} fill   "
            f"{review._pct(winners, n_f):>4} win   "
            f"{exp:+.2f} R/trade{_trust_flag(n_f)}"
        )
    return out


def _by_confidence_lines(closed: list) -> list:
    """Win rate & expectancy by the trader's own confidence flag (HIGH/NORMAL/LOW)."""
    out = [THIN, "  BY CONFIDENCE  (trader's risk flags — sample / win / expectancy)"]
    if not closed:
        out.append("    (no resolved trades yet)")
        return out
    groups = {}
    for t in closed:
        groups.setdefault(t.get("confidence") or "NORMAL", []).append(t)
    order = [lvl for lvl in ("HIGH", "NORMAL", "LOW") if groups.get(lvl)]
    order += [k for k in groups if k not in ("HIGH", "NORMAL", "LOW")]
    for lvl in order:
        g = groups[lvl]
        n = len(g)
        winners = sum(1 for t in g if t["r"] > 0)
        total_r = sum((t["r"] for t in g), Decimal("0"))
        exp = total_r / Decimal(n) if n else Decimal("0")
        out.append(
            f"    {lvl:<8} {n:>3} trades   "
            f"{review._pct(winners, n):>4} win   "
            f"{exp:+.2f} R/trade{_trust_flag(n)}"
        )
    return out


def _awaiting_lines(awaiting: int) -> list:
    out = [THIN, "  AWAITING OUTCOME"]
    if awaiting == 0:
        out.append("    None — every logged trade has a result.")
    else:
        out.append(f"    {awaiting} trade(s) logged but not yet resolved "
                   "(the 'unclear / CONFIRM' ones).")
        out.append("    Record results with:  python outcome.py")
    return out


def _trust_lines() -> list:
    return [
        THIN,
        "  TRUST",
        f"    A sample under {review.TRUST_MIN} trades is a hint, not a verdict. Anything",
        "    marked [<30] needs more data before you lean on it.",
    ]


# ----------------------------------------------------------------------------
# Build + run
# ----------------------------------------------------------------------------
def build_dashboard(path: str = None) -> str:
    path = path or config.PAPER_LOG_FILE
    out = []
    out.extend(_header_lines())
    out.extend(_breaker_lines(path))

    try:
        closed, missed, skipped_bad = review.load_closed_trades(path)
    except review.ReviewError:
        closed, missed, skipped_bad = [], [], []

    awaiting = _count_awaiting(path)

    out.extend(_overall_lines(closed, missed, awaiting))
    out.extend(_by_source_lines(closed, missed))
    out.extend(_by_confidence_lines(closed))
    out.extend(_awaiting_lines(awaiting))

    if skipped_bad:
        out.append(THIN)
        out.append(f"  NOTE: {len(skipped_bad)} row(s) couldn't be read and were skipped "
                   "(see python review.py).")

    out.extend(_trust_lines())
    out.append(LINE)
    return "\n".join(out)


def main():
    print(build_dashboard())


if __name__ == "__main__":
    main()
