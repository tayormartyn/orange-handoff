"""
review.py — the expectancy / edge review.

Run it with:

    python review.py

It reads paper_log.csv, looks at the trades you've marked as closed (the ones
where you've filled in the "outcome" column), and prints a plain-English report:
win rate, expectancy (average R per trade — the headline number), total R, and a
breakdown of which target your winners actually reached.

Nothing here connects to an exchange or moves money. It only reads your log.

------------------------------------------------------------------------------
HOW TO FILL IN THE "outcome" COLUMN
------------------------------------------------------------------------------
For each trade, once it's finished, type ONE of these into the outcome cell:

    1     it reached target 1 (and you closed there)
    2     it reached target 2
    3     it reached target 3
    4     it reached target 4   (or higher target number, if the signal had more)
    SL    it stopped out (hit the stop-loss) — a full loss
    BE    you closed at breakeven — no win, no loss

Leave it BLANK if the trade is still open. Blank rows are ignored.
------------------------------------------------------------------------------
"""

import csv
import os
from decimal import Decimal, InvalidOperation

import config
import signal_quality
from module_c_risk import resolve_asset_config

# Below this many closed trades, a number isn't statistically trustworthy.
# We never hide it — we print it WITH a clear flag, so you can judge for yourself.
TRUST_MIN = 30

# A ticker/trader needs at least this many closed trades before we bother listing
# it on its own. Below this it's just noise, so we summarise it as "other".
SHOW_MIN = 5

# What counts as a loss in R. Risk is 1% of the pot per trade by design,
# so a full stop-out is, by definition, exactly -1R.
SL_R = Decimal("-1")
BE_R = Decimal("0")
# A missed signal isn't a trade — no entry, no money on the line. It carries 0R
# and is counted separately (fill rate), never as a win, loss, or flat trade.
MISSED_R = Decimal("0")
_THIRD = Decimal(1) / Decimal(3)


class ReviewError(Exception):
    """Operator-facing problem reading the log."""


def _is_missed(outcome_raw: str) -> bool:
    """True if the outcome cell says the entry never filled (no trade taken)."""
    o = (outcome_raw or "").strip().upper()
    return o in ("MISSED", "MISS", "M", "NF", "NO-FILL", "NOFILL", "NO FILL")


def _parse_ladder(rr_ladder: str) -> dict:
    """
    Turn the stored rr_ladder string into {target_number: R}.

    Stored format looks like:  "T1=0.44:1 | T2=1.06:1 | T3=1.81:1"
    """
    ladder = {}
    if not rr_ladder:
        return ladder
    for chunk in rr_ladder.split("|"):
        chunk = chunk.strip()
        if not chunk or "=" not in chunk:
            continue
        label, value = chunk.split("=", 1)
        label = label.strip().upper().lstrip("T")
        value = value.strip().rstrip(":1").rstrip(":").strip()
        try:
            ladder[int(label)] = Decimal(value)
        except (ValueError, InvalidOperation):
            continue
    return ladder


def _classify(outcome_raw: str):
    """
    Normalise an outcome cell into a category.

    Returns one of:
        ("open", None)              -> blank cell, still running, ignore
        ("target", n)               -> hit target n (winner)
        ("sl", None)                -> stopped out (loser)
        ("be", None)                -> breakeven
        ("bad", original_string)    -> couldn't understand it
    """
    o = (outcome_raw or "").strip().upper()
    if o == "":
        return ("open", None)
    if o in ("SL", "STOP", "STOPPED"):
        return ("sl", None)
    if o in ("BE", "B/E", "BREAKEVEN", "BREAK-EVEN"):
        return ("be", None)
    # Allow "1", "T1", "TARGET 1"
    cleaned = o.replace("TARGET", "").replace("T", "").strip()
    if cleaned.isdigit():
        return ("target", int(cleaned))
    return ("bad", outcome_raw)


def _cps_scaleout_r(tps_raw: str, ladder: dict):
    """
    Realised R for a CPS trade scaled out in thirds, given how far it ran.

      tps_hit = 0 / SL -> stopped before any TP   = -1R (full loss)
      tps_hit = 1      -> TP1 hit, remainder stopped = 1/3*rr1 + 2/3*(-1)
      tps_hit = 2      -> TP2 hit, runner to breakeven = 1/3*rr1 + 1/3*rr2 + 1/3*0
      tps_hit = 3+     -> full ladder              = 1/3*(rr1 + rr2 + rr3)

    (After TP2 the stop moves to breakeven on the runner — that's why a
    TP2-then-reverse trade banks rr1+rr2 over three thirds and nothing worse.)
    Returns Decimal R, or None if tps_hit can't be read.
    """
    raw = (tps_raw or "").strip().upper()
    if raw in ("SL", "STOP", "STOPPED", "0", "NONE"):
        n = 0
    elif raw.isdigit():
        n = int(raw)
    else:
        return None
    rr1 = ladder.get(1, Decimal("2"))
    rr2 = ladder.get(2, Decimal("3"))
    rr3 = ladder.get(3, Decimal("5"))
    # Three equal thirds. Sum the portion R's first, THEN divide by 3 once — this
    # keeps a TP1-only trade exactly 0R (the 1/3 winner cancels the 2/3 stopped),
    # instead of leaving a tiny rounding residue that miscounts it as a loss.
    if n <= 0:
        portions = [Decimal("-1"), Decimal("-1"), Decimal("-1")]
    elif n == 1:
        portions = [rr1, Decimal("-1"), Decimal("-1")]   # 1/3 at TP1, 2/3 stopped
    elif n == 2:
        portions = [rr1, rr2, Decimal("0")]              # runner to breakeven
    else:
        portions = [rr1, rr2, rr3]                       # full ladder
    return sum(portions, Decimal("0")) / Decimal(3)


def realised_r(row: dict):
    """
    Best-available realised R for one logged row. Precedence:
      1) explicit 'realised_rr' the operator typed (override),
      2) CPS scale-out 'tps_hit' (0/1/2/3 or SL),
      3) legacy 'outcome' code (1/2/3/4, SL, BE).

    Returns (r: Decimal|None, reached: int|None, status: str)
      status: "ok" (filled trade, usable) | "missed" (entry never filled) |
              "open" (skip) | "bad" (unreadable)
    """
    ladder = _parse_ladder(row.get("rr_ladder", ""))

    # A missed signal is checked FIRST — before the realised_rr override — because
    # we write realised_rr=0 on a miss, which would otherwise read as a 0R trade.
    if _is_missed(row.get("outcome", "")):
        return MISSED_R, None, "missed"

    override = (row.get("realised_rr") or "").strip()
    if override:
        try:
            return Decimal(override), None, "ok"
        except InvalidOperation:
            pass  # ignore a junk override, fall through to the real signals

    tps = (row.get("tps_hit") or "").strip()
    if tps:
        r = _cps_scaleout_r(tps, ladder)
        if r is None:
            return None, None, "bad"
        reached = int(tps) if tps.isdigit() and int(tps) >= 1 else None
        return r, reached, "ok"

    kind, detail = _classify(row.get("outcome", ""))
    if kind == "open":
        return None, None, "open"
    if kind == "sl":
        return SL_R, None, "ok"
    if kind == "be":
        return BE_R, None, "ok"
    if kind == "target":
        if detail in ladder:
            return ladder[detail], detail, "ok"
        return None, None, "bad"
    return None, None, "bad"


def _confidence_of(row: dict) -> str:
    """
    The signal-quality tag recorded for this row (HIGH/NORMAL/LOW). Rows logged
    before the quality filter existed have no tag — they count as NORMAL, which is
    exactly the default the filter would have given a signal with no cues.
    """
    c = (row.get("confidence") or "").strip().upper()
    return c if signal_quality.is_valid_level(c) else signal_quality.NORMAL


def trade_dollar_risk(row: dict) -> Decimal:
    """How much cash 1R is worth for this row — prefer the logged dollar_risk."""
    for col in ("dollar_risk", "cash_at_risk"):
        v = (row.get(col) or "").strip()
        if v:
            try:
                return Decimal(v)
            except InvalidOperation:
                pass
    return Decimal(config.POT_SIZE) * Decimal(config.RISK_PCT)


def load_closed_trades(path: str = None):
    """
    Read the log and return (closed, missed, skipped_bad).

    `closed` are FILLED trades (a real entry was taken) — each carries its
    realised R, cash P&L, and a running balance (computed in time order). Win
    rate and expectancy are built from these only.

    `missed` are signals whose entry never filled (no trade taken). They carry
    no R and no P&L; they're reported separately as fill rate, and never counted
    as a win, loss, or flat trade.
    """
    path = path or config.PAPER_LOG_FILE
    if not os.path.exists(path):
        raise ReviewError(
            f"Couldn't find '{path}'.\n"
            "  Have you logged any signals yet? Run  python run.py  first."
        )

    closed = []
    missed = []
    skipped_bad = []

    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None or "outcome" not in reader.fieldnames:
            raise ReviewError(
                f"'{path}' doesn't look like a Signal Terminal log "
                "(no 'outcome' column). Nothing to review."
            )
        for line_no, row in enumerate(reader, start=2):
            ticker = (row.get("ticker") or "?").strip()
            r, reached, status = realised_r(row)

            if status == "open":
                continue
            if status == "missed":
                missed.append({
                    "timestamp": (row.get("timestamp") or "").strip(),
                    "ticker": ticker,
                    "source": (row.get("source") or "").strip(),
                    "r": MISSED_R,
                    "pnl": Decimal("0"),
                })
                continue
            if status == "bad":
                skipped_bad.append(
                    f"line {line_no} ({ticker}): couldn't read the result — use "
                    "tps_hit 0/1/2/3 (or SL), or outcome 1/2/3/4/SL/BE. Skipped."
                )
                continue

            asset_class = (row.get("asset_class") or "").strip().upper()
            if not asset_class:
                asset_class = resolve_asset_config(ticker)["asset_class"]

            dollar_risk = trade_dollar_risk(row)
            closed.append({
                "timestamp": (row.get("timestamp") or "").strip(),
                "ticker": ticker,
                "asset_class": asset_class,
                "source": (row.get("source") or "").strip(),
                "session": (row.get("session") or "").strip(),
                "level_tf": (row.get("level_tf") or "").strip(),
                "confidence": _confidence_of(row),   # HIGH / NORMAL / LOW
                "reached": reached,        # highest target reached (1/2/3), else None
                "r": r,
                "dollar_risk": dollar_risk,
                "pnl": r * dollar_risk,
            })

    # Running balance over the closed trades, in chronological (file) order.
    balance = Decimal(config.POT_SIZE)
    for t in closed:
        before = balance
        balance += t["pnl"]
        t["balance"] = balance
        t["pct_return"] = (t["pnl"] / before) if before else Decimal("0")

    return closed, missed, skipped_bad


def _pct(part: int, whole: int) -> str:
    if whole == 0:
        return "0%"
    return f"{(Decimal(part) / Decimal(whole) * 100):.0f}%"


def _segment_lines(label: str, trades: list, indent: str = "  ") -> list:
    """
    The core numbers for any group of trades (the whole sample, an asset class,
    a ticker, a trader, a session, a timeframe): sample size, win rate, realised
    expectancy (average R), total R, and net cash. A loud trust flag is printed
    whenever the sample is below TRUST_MIN.
    """
    n = len(trades)
    winners = [t for t in trades if t["r"] > 0]
    losers = [t for t in trades if t["r"] < 0]
    flats = [t for t in trades if t["r"] == 0]

    total_r = sum((t["r"] for t in trades), Decimal("0"))
    expectancy = total_r / Decimal(n) if n else Decimal("0")
    net_cash = sum((t["pnl"] for t in trades), Decimal("0"))

    flag = "" if n >= TRUST_MIN else f"   <-- only {n}, NOT enough to trust yet"

    return [
        f"{indent}{label}",
        f"{indent}    trades       : {n}{flag}",
        f"{indent}    win rate     : {_pct(len(winners), n)}  "
        f"({len(winners)}W / {len(losers)}L / {len(flats)} flat)",
        f"{indent}    expectancy   : {expectancy:+.2f} R/trade   "
        f"(avg realised R, after modelled slippage)",
        f"{indent}    total / net  : {total_r:+.2f} R   "
        f"({config.CURRENCY}{net_cash:+,.2f})",
    ]


def _slippage_note_lines(indent: str = "  ") -> list:
    """
    A clear note that the R / expectancy figures are modelled with realistic
    (slippage-worsened) fills, listing the per-side estimates from config.
    """
    table = getattr(config, "SLIPPAGE", {})
    names = {"XAU": "gold (XAU)", "XAG": "silver (XAG)", "CRYPTO": "crypto"}
    parts = [f"{names[k]} ${table[k]}/side" for k in ("XAU", "XAG", "CRYPTO") if k in table]
    detail = ", ".join(parts) if parts else "see config.py"
    return [
        f"{indent}SLIPPAGE — fills are modelled realistically, not perfectly.",
        f"{indent}" + "-" * 48,
        f"{indent}    Modelled per side: {detail}",
        f"{indent}    (estimates — tune them in config.py).",
        f"{indent}    Win rate, R and expectancy below already include this for trades",
        f"{indent}    the terminal sized: slippage worsens the entry, so the edge here",
        f"{indent}    is NOT overstated. Real fills cost something — this counts it.",
    ]


def _fill_rate_lines(closed: list, missed: list, indent: str = "  ") -> list:
    """
    Fill rate — how often a signal's entry actually got hit and a trade was
    taken (filled) versus got away (missed). Also shows the "including misses"
    expectancy: average R across EVERY signal seen, counting each miss as a 0R
    no-trade. That number is the real-world drag from entries you couldn't get.
    """
    n_filled = len(closed)
    n_missed = len(missed)
    n_signals = n_filled + n_missed

    total_r = sum((t["r"] for t in closed), Decimal("0"))
    exp_filled = total_r / Decimal(n_filled) if n_filled else Decimal("0")
    exp_incl = total_r / Decimal(n_signals) if n_signals else Decimal("0")

    lines = [
        f"{indent}FILL RATE — did the entry actually get hit?",
        f"{indent}" + "-" * 48,
        f"{indent}    signals seen : {n_signals}   "
        f"({n_filled} filled / {n_missed} missed)",
        f"{indent}    fill rate    : {_pct(n_filled, n_signals)}  "
        "(how often the entry filled and a trade was taken)",
    ]
    if n_missed:
        lines += [
            f"{indent}    expectancy (filled only)   : {exp_filled:+.2f} R/trade   "
            "(the edge when you DO get in)",
            f"{indent}    expectancy (incl. misses)  : {exp_incl:+.2f} R/signal   "
            "(every miss counted as a 0R no-trade)",
        ]
    return lines


def _fill_rate_by_source_lines(closed: list, missed: list, indent: str = "  ") -> list:
    """
    Fill rate split by who called the signal — so you can see whether one feed
    actually gets you filled while another mostly gets away. Same maths as the
    pooled block, computed per source: fill rate, expectancy when filled, and
    expectancy across every signal (each miss counted as a 0R no-trade).
    """
    groups = {}
    for t in closed:
        groups.setdefault(t.get("source") or "(no source)", {"f": [], "m": []})["f"].append(t)
    for m in missed:
        groups.setdefault(m.get("source") or "(no source)", {"f": [], "m": []})["m"].append(m)

    lines = [
        f"{indent}FILL RATE BY SOURCE — who actually gets you filled?",
        f"{indent}" + "-" * 48,
    ]
    # Biggest sample first.
    order = sorted(groups, key=lambda k: (-(len(groups[k]["f"]) + len(groups[k]["m"])), str(k)))
    for src in order:
        g = groups[src]
        n_f, n_m = len(g["f"]), len(g["m"])
        n = n_f + n_m
        total_r = sum((t["r"] for t in g["f"]), Decimal("0"))
        exp_f = total_r / Decimal(n_f) if n_f else Decimal("0")
        exp_all = total_r / Decimal(n) if n else Decimal("0")
        lines.append(f"{indent}  {src}")
        lines.append(f"{indent}      signals    : {n}  ({n_f} filled / {n_m} missed)   "
                     f"fill rate {_pct(n_f, n)}")
        lines.append(f"{indent}      expectancy : {exp_f:+.2f} R/trade (filled only)   "
                     f"{exp_all:+.2f} R/signal (incl. misses)")
    return lines


def _target_breakdown_lines(trades: list, indent: str = "  ") -> list:
    """How far trades ran — which target they actually reached (TP1/TP2/TP3)."""
    reached_trades = [t for t in trades if t.get("reached")]
    lines = [f"{indent}How far trades ran (highest target reached):"]
    if not reached_trades:
        lines.append(f"{indent}    (none reached a target yet)")
        return lines
    counts = {}
    for t in reached_trades:
        counts[t["reached"]] = counts.get(t["reached"], 0) + 1
    total = len(reached_trades)
    for tgt in sorted(counts):
        c = counts[tgt]
        lines.append(f"{indent}    TP{tgt}  : {c:>3}   ({_pct(c, total)} of trades that reached a TP)")
    return lines


def _group_by(trades: list, key: str) -> dict:
    groups = {}
    for t in trades:
        groups.setdefault(t[key], []).append(t)
    return groups


def _grouped_section(out: list, title: str, groups: dict, summarise_small: bool):
    """
    Render one segmented section. Groups with >= SHOW_MIN trades get their own
    block; smaller ones are summarised (so tiny, noisy groups don't mislead).
    """
    out.append("")
    out.append(f"  {title}")
    out.append("  " + "-" * 48)

    # Biggest samples first — they're the ones worth reading.
    keys = sorted(groups, key=lambda k: (-len(groups[k]), str(k)))
    shown = 0
    small = []
    for k in keys:
        label = k if str(k).strip() else "(blank)"
        if summarise_small and len(groups[k]) < SHOW_MIN:
            small.append((label, len(groups[k])))
            continue
        out.extend(_segment_lines(str(label), groups[k], indent="  "))
        out.append("")
        shown += 1

    if shown == 0:
        out.append(f"    (nothing with at least {SHOW_MIN} closed trades yet)")
        out.append("")
    if small:
        bits = ", ".join(f"{lab} ({cnt})" for lab, cnt in small)
        out.append(f"    Too few to show on their own (under {SHOW_MIN} trades): {bits}")
        out.append("")


def build_report(path: str = None) -> str:
    closed, missed, skipped_bad = load_closed_trades(path)

    out = []
    out.append("=" * 60)
    out.append("   SIGNAL TERMINAL — EXPECTANCY REVIEW  (paper trades)")
    out.append("=" * 60)

    n = len(closed)
    n_missed = len(missed)

    if skipped_bad:
        out.append("")
        out.append(f"  Note: {len(skipped_bad)} row(s) couldn't be read and were skipped:")
        for msg in skipped_bad:
            out.append(f"    - {msg}")

    # --- SLIPPAGE: state up front that the numbers model real fills ---------
    out.append("")
    out.extend(_slippage_note_lines(indent="  "))

    # --- FILL RATE: filled vs missed, shown before anything else ------------
    if n or n_missed:
        out.append("")
        out.extend(_fill_rate_lines(closed, missed, indent="  "))

        # Split it by source when there's more than one feed to compare, or any
        # miss to attribute — otherwise the pooled line above already says it all.
        sources = {(t.get("source") or "") for t in closed} | \
                  {(m.get("source") or "") for m in missed}
        sources.discard("")
        if len(sources) > 1 or (sources and n_missed):
            out.append("")
            out.extend(_fill_rate_by_source_lines(closed, missed, indent="  "))

    if n == 0:
        out.append("")
        if n_missed:
            out.append("  No FILLED trades yet — only missed signals so far.")
            out.append("  Win rate and expectancy need at least one trade you actually took.")
        else:
            out.append("  No closed trades yet.")
            out.append("")
            out.append("  Fill in the 'outcome' column in paper_log.csv for trades that")
            out.append("  have finished, then run this again. Use:")
            out.append("     1/2/3/4 = hit that target,   SL = stopped out,   BE = breakeven,")
            out.append("     MISSED  = the entry never filled (no trade taken).")
        out.append("=" * 60)
        return "\n".join(out)

    # --- POOLED: the overall headline across every FILLED trade -------------
    # Win rate and expectancy below count FILLED trades only — misses are in the
    # fill-rate block above, never as a win, loss, or flat trade.
    out.append("")
    out.append("  POOLED — all FILLED trades together  (misses excluded here)")
    out.append("  " + "-" * 48)
    out.extend(_segment_lines("ALL FILLED TRADES", closed, indent="  "))
    out.append("")
    out.extend(_target_breakdown_lines(closed, indent="  "))

    # --- BY ASSET CLASS: crypto vs metal behave very differently ------------
    # Always show every class present (there are only ever a couple).
    _grouped_section(out, "BY ASSET CLASS", _group_by(closed, "asset_class"),
                     summarise_small=False)

    # --- BY TICKER: gold alone, silver alone, each coin ---------------------
    _grouped_section(out, "BY TICKER", _group_by(closed, "ticker"),
                     summarise_small=True)

    # --- BY TRADER / SOURCE: only if you've recorded any ---------------------
    with_source = [t for t in closed if t["source"]]
    if with_source:
        _grouped_section(out, "BY TRADER / SOURCE", _group_by(with_source, "source"),
                         summarise_small=True)
        no_src = n - len(with_source)
        if no_src:
            out.append(f"    ({no_src} trade(s) had no source recorded.)")
            out.append("")

    # --- BY CONFIDENCE: does the trader's own risk flagging predict edge? ----
    _confidence_section(out, closed)

    # --- BY SESSION (CPS context): Asia / New York / London ------------------
    _context_section(out, "BY SESSION", closed, "session",
                     "no session recorded yet — add it when logging")

    # --- BY LEVEL TIMEFRAME (CPS context): 4H / Daily / Weekly / Monthly -----
    _context_section(out, "BY LEVEL TIMEFRAME", closed, "level_tf",
                     "no level timeframe recorded yet — add it when logging")

    # --- How to read it -----------------------------------------------------
    out.append("  " + "-" * 48)
    out.append("  How to read it:")
    out.append("    * Fill rate is filled vs missed: how often the entry actually got")
    out.append("      hit. A MISSED signal isn't a win or a loss — no trade was taken.")
    out.append("      Win rate and expectancy below count FILLED trades only (the real")
    out.append("      edge when you get in); 'expectancy incl. misses' counts each miss")
    out.append("      as a 0R no-trade, showing the drag from entries you couldn't get.")
    out.append("    * Expectancy is the number that matters — average REALISED R per")
    out.append("      trade. Positive = made money on paper; negative = lost.")
    out.append("    * These figures are AFTER modelled slippage (realistic fills), so")
    out.append("      they don't flatter the edge. Per-side estimates are in config.py.")
    out.append("    * R is computed from how far each trade ran (tps_hit) under the CPS")
    out.append("      scale-out: 1/3 at TP1 (1:2), 1/3 at TP2 (1:3), 1/3 runner to TP3")
    out.append("      (1:5), stop to breakeven after TP2. A full stop-out is -1R.")
    out.append(f"    * Any segment under {TRUST_MIN} trades is flagged — treat its number")
    out.append("      as a hint, not a verdict, until the sample grows.")
    out.append("=" * 60)
    return "\n".join(out)


def _confidence_section(out: list, closed: list):
    """
    Performance split by the signal-quality tag (HIGH / NORMAL / LOW), in that
    fixed order, so you can see directly whether the trader's HIGH-confidence
    calls actually win more / have better expectancy than their LOW ones.
    """
    out.append("")
    out.append("  BY CONFIDENCE  (the trader's own risk flags — do HIGH calls outperform LOW?)")
    out.append("  " + "-" * 48)
    groups = _group_by(closed, "confidence")
    order = [signal_quality.HIGH, signal_quality.NORMAL, signal_quality.LOW]
    present = [lvl for lvl in order if groups.get(lvl)]
    if not present:
        out.append("    (no confidence tags on the closed trades yet)")
        out.append("")
        return
    for lvl in present:
        out.extend(_segment_lines(lvl, groups[lvl], indent="  "))
        out.append("")
    # Plain-English read of HIGH vs LOW, when both are present.
    if groups.get(signal_quality.HIGH) and groups.get(signal_quality.LOW):
        def _exp(ts):
            return sum((t["r"] for t in ts), Decimal("0")) / Decimal(len(ts))
        hi, lo = _exp(groups[signal_quality.HIGH]), _exp(groups[signal_quality.LOW])
        verdict = ("HIGH is beating LOW" if hi > lo else
                   "LOW is beating HIGH (!)" if lo > hi else "they're level")
        out.append(f"    Read: HIGH {hi:+.2f} vs LOW {lo:+.2f} R/trade — {verdict}.")
        out.append("    (Keep gathering trades before trusting it — see the trust note below.)")
        out.append("")


def _context_section(out: list, title: str, closed: list, key: str, empty_msg: str):
    """A grouped section for an optional context field — skipped politely if blank."""
    if any(t[key] for t in closed):
        _grouped_section(out, title, _group_by(closed, key), summarise_small=True)
    else:
        out.append("")
        out.append(f"  {title}")
        out.append("  " + "-" * 48)
        out.append(f"    ({empty_msg})")
        out.append("")


def main():
    try:
        print(build_report())
    except ReviewError as e:
        print("\n  " + str(e) + "\n")


if __name__ == "__main__":
    main()
