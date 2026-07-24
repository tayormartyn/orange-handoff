"""
chart.py — a visual view of your PAPER trades.

Run it with:

    python chart.py                 # pick a trade from a numbered list (like outcome.py)
    python chart.py last            # chart the most recent trade, no prompt
    python chart.py 3               # chart trade #3 from the list
    python chart.py 1,3,5           # chart a few trades at once
    python chart.py last --out C:/somewhere   # choose where the image is saved

It reads the trades already in paper_log.csv and draws each one on a simple price
chart: the ENTRY line, the STOP-LOSS line, and the TAKE-PROFIT target lines,
clearly labelled, with the trade's direction (LONG/SHORT). A light "illustrative
path" is drawn from entry toward however the trade actually finished (win / stop /
breakeven) — purely to make the picture readable.

IMPORTANT — what this is NOT:
  * There is NO live market data here. It does not fetch prices from anywhere.
  * It only ever PLOTS the trade's own logged levels (entry / stop / targets).
  * Every chart is stamped "PAPER TRADE — illustration only, not live."

PAPER MODE ONLY. This tool is READ-ONLY to paper_log.csv: it opens the file to
read it and never writes to it. It connects to no broker, places no order, and
never touches the LIVE stub. Real broker charts with live price data are a
future, post-proof step (see the README).
"""

import csv
import os
import sys
from datetime import datetime

import config


# ----------------------------------------------------------------------------
# Friendly dependency / file guards (same plain-English style as the rest)
# ----------------------------------------------------------------------------
def _friendly_stop(message: str):
    print("\n  Can't draw the chart yet:")
    print(f"  {message}\n")


def _load_matplotlib():
    """
    Import matplotlib with a non-interactive backend (so it just writes an image
    file and needs no display), or print a friendly install hint. Returns the
    pyplot module, or None.
    """
    try:
        import matplotlib
        matplotlib.use("Agg")          # headless: render straight to a PNG, no window
        import matplotlib.pyplot as plt
        return plt
    except ImportError:
        _friendly_stop(
            "the 'matplotlib' charting library isn't installed.\n"
            "  Fix: open PowerShell and run:  pip install matplotlib"
        )
        return None


# ----------------------------------------------------------------------------
# Reading the log (READ-ONLY)
# ----------------------------------------------------------------------------
def load(path: str):
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return reader.fieldnames, list(reader)


def _f(value):
    """Parse a price cell into a float, or None if it's blank/unreadable."""
    s = (value or "").strip()
    if not s:
        return None
    try:
        return float(s)
    except ValueError:
        return None


def _date(row: dict) -> str:
    ts = (row.get("timestamp") or "").strip()
    return ts[:10] if ts else "?"


def _label(row: dict) -> str:
    return f"{row.get('ticker','?')} {row.get('direction','')}".strip()


def _outcome_text(row: dict) -> str:
    """A short, human-readable result tag for the list/title."""
    outcome = (row.get("outcome") or "").strip().upper()
    tps = (row.get("tps_hit") or "").strip().upper()
    if outcome in ("WIN",) or (tps.isdigit() and int(tps) >= 1):
        reached = tps if tps.isdigit() else "?"
        return f"WIN (reached TP{reached})" if reached != "?" else "WIN"
    if outcome in ("LOSS", "SL") or tps == "SL":
        return "LOSS (stopped out)"
    if outcome in ("BE",):
        return "breakeven"
    if outcome in ("MISSED",):
        return "MISSED (never filled)"
    return "open / no result yet"


# ----------------------------------------------------------------------------
# Turning a row into chartable levels
# ----------------------------------------------------------------------------
def _parse_rr_ladder(row: dict) -> dict:
    """
    Pull the R:R per target out of the stored 'rr_ladder' string, e.g.
    "T1=0.13:1 | T2=0.24:1 | T3=0.52:1"  ->  {1: "0.13", 2: "0.24", 3: "0.52"}.
    """
    out = {}
    for chunk in (row.get("rr_ladder") or "").split("|"):
        chunk = chunk.strip()
        if not chunk or "=" not in chunk:
            continue
        label, value = chunk.split("=", 1)
        label = label.strip().upper().lstrip("T")
        value = value.strip().rstrip(":1").rstrip(":").strip()
        if label.isdigit():
            out[int(label)] = value
    return out


def trade_levels(row: dict) -> dict:
    """
    Gather everything we need to draw one trade. Returns a dict with:
        ticker, direction, date, source, outcome_text
        entry (float|None), stop (float|None)
        targets: list of (label, price, rr_text)
    """
    rr = _parse_rr_ladder(row)
    targets = []
    for i, col in enumerate(("tp1", "tp2", "tp3"), start=1):
        price = _f(row.get(col))
        if price is not None:
            targets.append((f"TP{i}", price, rr.get(i, "")))
    return {
        "ticker": row.get("ticker", "?") or "?",
        "direction": (row.get("direction") or "").upper().strip(),
        "date": _date(row),
        "source": (row.get("source") or row.get("trader") or "").strip(),
        "outcome_text": _outcome_text(row),
        "entry": _f(row.get("entry")),
        "stop": _f(row.get("sl_price")),
        "targets": targets,
    }


def _resolve_end(levels: dict, row: dict):
    """
    Where should the illustrative price line END, and how to mark it?
    Returns (end_price|None, marker, colour, caption). end_price None = the entry
    never filled (a MISSED signal), so no path is drawn.
    """
    entry = levels["entry"]
    stop = levels["stop"]
    targets = levels["targets"]
    is_long = levels["direction"] != "SHORT"
    profit_sign = 1 if is_long else -1
    # A sensible "1R" distance for trades that logged no explicit target.
    risk = abs(entry - stop) if (entry is not None and stop is not None) else \
        (abs(entry) * 0.01 if entry is not None else 0.0)

    outcome = (row.get("outcome") or "").strip().upper()
    tps = (row.get("tps_hit") or "").strip().upper()

    if outcome == "MISSED":
        return None, None, None, "entry never filled (MISSED)"
    if outcome in ("LOSS", "SL") or tps == "SL":
        end = stop if stop is not None else (entry - profit_sign * risk)
        return end, "X", "#d62728", "stopped out"
    if outcome == "BE":
        return entry, "s", "#7f7f7f", "closed at breakeven"
    if outcome == "WIN" or (tps.isdigit() and int(tps) >= 1):
        if targets:
            idx = int(tps) if tps.isdigit() else len(targets)
            idx = max(1, min(idx, len(targets)))
            end = targets[idx - 1][1]
        else:
            end = entry + profit_sign * risk      # ~1R move, illustrative
        return end, ("^" if is_long else "v"), "#2ca02c", "result: win"
    # No result recorded yet.
    end = targets[0][1] if targets else (entry + profit_sign * risk)
    return end, "o", "#7f7f7f", "open (illustrative target)"


# ----------------------------------------------------------------------------
# Drawing
# ----------------------------------------------------------------------------
def draw_trade(row: dict, plt, out_path: str) -> str:
    """Draw one trade to a PNG at out_path. Returns the path, or "" if not drawable."""
    import numpy as np

    levels = trade_levels(row)
    entry = levels["entry"]
    if entry is None:
        print(f"  Skipped {_label(row)} ({_date(row)}): no entry price logged to chart.")
        return ""

    stop = levels["stop"]
    targets = levels["targets"]
    is_long = levels["direction"] != "SHORT"

    fig, ax = plt.subplots(figsize=(10, 6))
    x0, x1 = 0.0, 10.0

    # All the prices we're showing, so we can set a tidy y-range with margin.
    prices = [entry] + [t[1] for t in targets] + ([stop] if stop is not None else [])
    end, marker, end_colour, caption = _resolve_end(levels, row)
    if end is not None:
        prices.append(end)
    lo, hi = min(prices), max(prices)
    pad = (hi - lo) * 0.18 or abs(entry) * 0.01 or 1.0
    ax.set_ylim(lo - pad, hi + pad)
    ax.set_xlim(x0, x1 + 3.6)          # extra room on the right for level labels

    # --- Risk zone (entry<->stop) and reward zone (entry<->furthest target) ---
    if stop is not None:
        ax.axhspan(min(entry, stop), max(entry, stop), color="#d62728", alpha=0.06)
    if targets:
        furthest = max((t[1] for t in targets), key=lambda p: abs(p - entry))
        ax.axhspan(min(entry, furthest), max(entry, furthest), color="#2ca02c", alpha=0.06)

    # --- Illustrative price path (NOT real market data) ----------------------
    if end is not None:
        xs = np.linspace(x0, x1, 7)
        base = np.linspace(entry, end, 7)
        amp = 0.18 * abs(end - entry) if end != entry else abs(entry) * 0.004
        wiggle = amp * np.array([0.0, 0.5, -0.35, 0.55, -0.25, 0.3, 0.0])
        path = base + wiggle
        path[0], path[-1] = entry, end
        ax.plot(xs, path, color="#ff7f0e", lw=1.6, alpha=0.75, zorder=2,
                label="Illustrative path (not real data)")
        # End marker (its colour/shape shows win/stop/breakeven). The outcome is
        # also spelled out in the title, so we keep a short caption ABOVE the
        # marker — never to its right, where the level labels live.
        ax.plot(x1, end, marker=marker, color=end_colour, markersize=11, zorder=4)
        ax.annotate(caption, xy=(x1, end), xytext=(x1, end + pad * 0.45),
                    color=end_colour, fontsize=9, ha="center", fontweight="bold")
    ax.plot(x0, entry, marker="o", color="#1f77b4", markersize=8, zorder=4)

    # --- The level lines, labelled at the right edge -------------------------
    def level(price, colour, ls, lw, text):
        ax.axhline(price, color=colour, ls=ls, lw=lw, zorder=3)
        ax.text(x1 + 0.5, price, text, color=colour, va="center",
                fontsize=9, fontweight="bold")

    level(entry, "#1f77b4", "-", 2.2, f"ENTRY  {entry:g}")
    if stop is not None:
        level(stop, "#d62728", "--", 1.8, f"STOP  {stop:g}")
    for label, price, rr in targets:
        rr_txt = f"  ({rr}R)" if rr else ""
        level(price, "#2ca02c", "--", 1.5, f"{label}  {price:g}{rr_txt}")
    if not targets:
        ax.text(x1 + 0.5, hi + pad * 0.4, "(no take-profit targets logged)",
                color="#7f7f7f", va="center", fontsize=8, style="italic")

    # --- Direction badge -----------------------------------------------------
    arrow = "LONG ▲" if is_long else "SHORT ▼"
    badge_colour = "#2ca02c" if is_long else "#d62728"
    ax.text(0.02, 0.96, arrow, transform=ax.transAxes, fontsize=14,
            fontweight="bold", color="white", va="top", ha="left",
            bbox=dict(boxstyle="round,pad=0.4", facecolor=badge_colour, edgecolor="none"))

    # --- Titles, banner, footer ----------------------------------------------
    src = f"  ·  {levels['source']}" if levels["source"] else ""
    ax.set_title(f"{levels['ticker']}  {levels['direction']}     {levels['date']}{src}\n"
                 f"{levels['outcome_text']}", fontsize=12, fontweight="bold")
    fig.suptitle("PAPER TRADE — illustration only, not live",
                 fontsize=13, fontweight="bold", color="#b22222", y=0.99)
    ax.set_ylabel(f"Price  ({levels['ticker']})")
    ax.set_xlabel("Illustrative time →   (not real timestamps — no market data)")
    ax.set_xticks([])
    ax.grid(axis="y", ls=":", alpha=0.4)
    if end is not None:            # only when an illustrative path was drawn
        ax.legend(loc="lower right", fontsize=8, framealpha=0.9)
    fig.text(0.5, 0.005,
             "Read-only view of paper_log.csv  ·  no live data  ·  no broker  ·  no execution",
             ha="center", fontsize=8, color="#666666")
    fig.tight_layout(rect=(0, 0.02, 1, 0.96))

    fig.savefig(out_path, dpi=120)
    plt.close(fig)
    return out_path


# ----------------------------------------------------------------------------
# Selecting which trade(s) to chart
# ----------------------------------------------------------------------------
def _listing(rows: list):
    """
    Rows paired with a display number, NEWEST FIRST. Returns a list of
    (display_no, original_index, row). Display numbers are what the user types.
    """
    indexed = list(enumerate(rows))
    indexed.sort(key=lambda pair: (pair[1].get("timestamp") or ""), reverse=True)
    return [(n, orig_i, row) for n, (orig_i, row) in enumerate(indexed, start=1)]


def _print_list(listing):
    print("\n  Your paper trades (newest first):\n")
    for display_no, _orig_i, row in listing:
        entry = (row.get("entry") or "").strip() or "—"
        print(f"    {display_no:>2})  {_label(row):<14}  entry {entry:<10}  "
              f"{_date(row):<11}  {_outcome_text(row)}")
    print()


def _safe_name(text: str) -> str:
    return "".join(c if c.isalnum() else "-" for c in text).strip("-") or "trade"


def _out_path_for(out_dir: str, display_no: int, row: dict) -> str:
    name = f"chart_{display_no:02d}_{_safe_name(row.get('ticker','trade'))}_{_date(row)}.png"
    return os.path.join(out_dir, name)


def _parse_picks(text: str, listing) -> list:
    """Turn '1,3,5' or 'last' / 'latest' into a list of (display_no, orig_i, row)."""
    text = (text or "").strip().lower()
    if text in ("last", "latest", "recent", "l"):
        return [listing[0]] if listing else []
    chosen = []
    by_no = {display_no: item for item in listing for display_no in (item[0],)}
    for part in text.replace(" ", "").split(","):
        if part.isdigit() and int(part) in by_no:
            chosen.append(by_no[int(part)])
        elif part:
            print(f"  (Ignoring '{part}' — not a trade number on the list.)")
    return chosen


# ----------------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------------
def _print_usage():
    print("  Usage:")
    print("    python chart.py                # pick a trade from a numbered list")
    print("    python chart.py last           # chart the most recent trade")
    print("    python chart.py 3              # chart trade #3")
    print("    python chart.py 1,3,5          # chart several trades")
    print("    python chart.py last --out DIR  # save the image(s) into DIR")


def main():
    args = [a for a in sys.argv[1:] if a.strip()]
    if args and args[0] in ("-h", "--help", "help"):
        _print_usage()
        return

    # Optional --out DIR for where images are saved (default: ./charts).
    out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "charts")
    if "--out" in args:
        i = args.index("--out")
        if i + 1 < len(args):
            out_dir = args[i + 1]
            del args[i:i + 2]
        else:
            _friendly_stop("--out needs a folder after it, e.g.  --out C:/charts")
            return

    path = config.PAPER_LOG_FILE
    if not os.path.exists(path):
        print(f"\n  There's no log yet ('{path}').")
        print("  Log some signals with  python run.py  first, then come back.\n")
        return

    plt = _load_matplotlib()
    if plt is None:
        return

    try:
        _fieldnames, rows = load(path)
    except PermissionError:
        _friendly_stop(f"couldn't open '{path}' — is it open in Excel? Close it and retry.")
        return

    if not rows:
        print(f"\n  '{path}' has no trades in it yet.\n")
        return

    listing = _listing(rows)

    print("=" * 64)
    print("   CHART A PAPER TRADE   —   illustration only, not live")
    print("=" * 64)
    print("   Reads paper_log.csv (read-only) and draws the trade's own levels:")
    print("   entry, stop-loss and targets. No live data, no broker, no execution.")
    print("=" * 64)

    # Decide what to chart: from args, or interactively.
    rest = [a for a in args if a]
    if rest:
        picks = _parse_picks(",".join(rest), listing)
    else:
        _print_list(listing)
        print("  Type a number, several (e.g. 1,3,5), 'last' for the most recent,")
        raw = input("  or just Enter to finish: ").strip()
        if not raw:
            print("\n  Nothing selected. Done.\n")
            return
        picks = _parse_picks(raw, listing)

    if not picks:
        print("\n  No matching trades to chart.\n")
        return

    os.makedirs(out_dir, exist_ok=True)
    made = []
    for display_no, _orig_i, row in picks:
        out_path = _out_path_for(out_dir, display_no, row)
        result = draw_trade(row, plt, out_path)
        if result:
            made.append(result)
            print(f"  Charted {_label(row)} ({_date(row)})  ->  {result}")

    if made:
        print(f"\n  Done. {len(made)} chart(s) saved in:\n    {os.path.abspath(out_dir)}")
        print("  Each is stamped 'PAPER TRADE — illustration only, not live'.\n")
    else:
        print("\n  Nothing was drawn.\n")


if __name__ == "__main__":
    main()
