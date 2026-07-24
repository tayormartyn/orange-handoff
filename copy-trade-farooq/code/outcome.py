"""
outcome.py — record how a trade finished, without ever editing the CSV by hand.

Run it with:

    python outcome.py

It shows the trades you've logged that don't have a result yet, lets you pick
one by number, asks in plain English how it finished (hit a target, stopped out,
closed at breakeven, or was MISSED because the entry never filled), and writes
that into paper_log.csv for you. Then `python review.py` will pick it up
automatically.

You can also back-log a signal you saw but never entered: choose [a] from the
main menu and type in the ticker. It's stored as MISSED so the review tool can
show your fill rate (how often entries actually got hit) without it ever
counting as a win or a loss.

PAPER MODE ONLY. This tool only reads and updates your paper log. It never
connects to a broker, never places an order, and never touches the LIVE stub.
"""

import csv
import os
from datetime import datetime, timezone

import config

# A trade counts as "already recorded" if any of these are filled in.
RECORDED_FIELDS = ("tps_hit", "outcome", "realised_rr")


# ----------------------------------------------------------------------------
# Reading / writing the log
# ----------------------------------------------------------------------------
def load(path: str):
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return reader.fieldnames, list(reader)


def save(path: str, fieldnames, rows):
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def is_recorded(row: dict) -> bool:
    return any((row.get(k) or "").strip() for k in RECORDED_FIELDS)


def unrecorded(rows: list) -> list:
    """List of (index_in_rows, row) for trades with no result yet."""
    return [(i, r) for i, r in enumerate(rows) if not is_recorded(r)]


def apply_outcome(row: dict, kind: str, target=None, notes: str = "") -> dict:
    """
    Write a result into a row. `kind` is "target", "sl", "be", or "missed".

    For a target hit we record tps_hit (how far it ran, used by the CPS
    scale-out) plus a human-readable WIN. review.py works out the R and P&L.

    For "missed" (the entry never filled, so no trade was taken) we record
    outcome=MISSED with realised_rr and pnl set to 0 — it's not a win or a loss,
    just a signal that got away. review.py reports these separately as fill rate.
    """
    if kind == "target":
        row["tps_hit"] = str(target)
        row["outcome"] = "WIN"
    elif kind == "sl":
        row["tps_hit"] = "SL"
        row["outcome"] = "LOSS"
    elif kind == "be":
        row["tps_hit"] = ""
        row["outcome"] = "BE"
    elif kind == "missed":
        row["tps_hit"] = ""
        row["outcome"] = "MISSED"
        row["realised_rr"] = "0"
        row["pnl"] = "0"
    else:
        raise ValueError(f"unknown outcome kind: {kind}")
    if notes:
        row["notes"] = notes
    return row


# ----------------------------------------------------------------------------
# Small display helpers
# ----------------------------------------------------------------------------
def _date(row: dict) -> str:
    ts = (row.get("timestamp") or "").strip()
    return ts[:10] if ts else "?"


def _label(row: dict) -> str:
    return f"{row.get('ticker','?')} {row.get('direction','')}".strip()


def _targets_hint(row: dict) -> str:
    bits = []
    for col in ("tp1", "tp2", "tp3"):
        v = (row.get(col) or "").strip()
        if v:
            bits.append(f"{col.upper()} {v}")
    return "   ".join(bits)


def _ask(prompt: str) -> str:
    return input(prompt).strip()


# ----------------------------------------------------------------------------
# The interactive flow
# ----------------------------------------------------------------------------
def _print_list(todo: list):
    print("\n  Trades waiting for a result:\n")
    for n, (_, row) in enumerate(todo, start=1):
        entry = (row.get("entry") or "").strip()
        print(f"    {n:>2})  {_label(row):<14}  entry {entry:<10}  {_date(row)}")
    print()


def _ask_how_finished(row: dict):
    """Return (kind, target) or None if the user cancels this trade."""
    while True:
        print(f"\n  How did this trade finish?   ({_label(row)})")
        print("    [t] Hit a target")
        print("    [s] Stopped out (hit the stop-loss)")
        print("    [b] Closed at breakeven")
        print("    [m] Missed — entry never filled (no trade taken)")
        print("    [c] Cancel — leave it for now")
        choice = _ask("  Type t / s / b / m / c: ").lower()

        if choice in ("t", "target", "1", "win"):
            hint = _targets_hint(row)
            if hint:
                print(f"\n  Targets on this trade:   {hint}")
            num = _ask("  Which target did it reach? (1, 2, 3...): ")
            if num.isdigit() and int(num) >= 1:
                return ("target", int(num))
            print("  Please type a whole number like 1, 2 or 3.")
            continue
        if choice in ("s", "sl", "stop", "stopped", "loss"):
            return ("sl", None)
        if choice in ("b", "be", "breakeven", "break-even"):
            return ("be", None)
        if choice in ("m", "miss", "missed"):
            return ("missed", None)
        if choice in ("c", "cancel", "q", ""):
            return None
        print("  Sorry, I didn't catch that — please type t, s, b, m or c.")


def _describe(kind: str, target) -> str:
    if kind == "target":
        return f"reached TP{target} (WIN)"
    if kind == "sl":
        return "stopped out (LOSS)"
    if kind == "missed":
        return "MISSED — entry never filled (no trade taken)"
    return "closed at breakeven (BE)"


# ----------------------------------------------------------------------------
# Back-logging a missed signal
# ----------------------------------------------------------------------------
def _timestamp_for(when: str) -> str:
    """ISO timestamp for a back-logged miss. Blank/garbage -> now (UTC)."""
    when = (when or "").strip()
    if when:
        try:
            d = datetime.strptime(when, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            return d.isoformat(timespec="seconds")
        except ValueError:
            print("  (Couldn't read that date — using today instead.)")
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _new_missed_row(fieldnames) -> dict:
    """A complete blank row (every column present) already marked MISSED."""
    row = {name: "" for name in fieldnames}
    row["outcome"] = "MISSED"
    row["realised_rr"] = "0"
    row["pnl"] = "0"
    return row


def add_missed_signal(fieldnames, rows) -> bool:
    """
    Back-log a signal you saw but never entered (the entry never filled). Asks
    for just enough to identify it — no sizing, no P&L — and appends it as MISSED.
    Returns True if a row was added.
    """
    print("\n  Back-log a MISSED signal (one you saw but never entered).")
    ticker = _ask("  Ticker (e.g. XAUUSD): ").upper()
    if not ticker:
        print("  No ticker typed — nothing added.")
        return False
    direction = _ask("  Direction? LONG / SHORT (optional — Enter to skip): ").upper()
    entry = _ask("  Entry it would have needed (optional — Enter to skip): ")
    when = _ask("  Date you saw it? YYYY-MM-DD (optional — Enter for today): ")
    notes = _ask("  Any notes? (optional — Enter to skip): ")

    row = _new_missed_row(fieldnames)
    row["timestamp"] = _timestamp_for(when)
    row["ticker"] = ticker
    row["direction"] = direction
    row["entry"] = entry
    row["notes"] = notes
    rows.append(row)
    return True


def main():
    path = config.PAPER_LOG_FILE

    if not os.path.exists(path):
        print(f"\n  There's no log yet ('{path}').")
        print("  Log some signals with  python run.py  first, then come back.\n")
        return

    try:
        fieldnames, rows = load(path)
    except PermissionError:
        print(f"\n  Couldn't open '{path}' — is it open in Excel?")
        print("  Close it and run this again.\n")
        return

    print("=" * 56)
    print("   RECORD A TRADE RESULT   (paper log)")
    print("=" * 56)

    while True:
        todo = unrecorded(rows)
        if todo:
            _print_list(todo)
        else:
            print("\n  No trades are waiting for a result.")

        print("  Options:  a number = record that trade's result")
        print("            [a]      = back-log a signal you MISSED (never entered)")
        print("            [Enter]  = finish")
        pick = _ask("  Your choice: ")

        if pick == "" or pick.lower() in ("q", "quit", "done"):
            print("\n  Done. Run  python review.py  to see your updated numbers.\n")
            break

        if pick.lower() in ("a", "add", "miss", "missed"):
            if add_missed_signal(fieldnames, rows):
                try:
                    save(path, fieldnames, rows)
                except PermissionError:
                    print(f"\n  Couldn't save — is '{path}' open in Excel? "
                          "Close it and try again.\n")
                    rows.pop()   # undo the just-added row so the file stays in sync
                    continue
                print("  Saved a missed signal.")
            continue

        if not pick.isdigit() or not (1 <= int(pick) <= len(todo)):
            if todo:
                print(f"  Please type a number between 1 and {len(todo)}, "
                      "'a' to back-log a miss, or Enter to finish.")
            else:
                print("  Type 'a' to back-log a missed signal, or Enter to finish.")
            continue

        idx, row = todo[int(pick) - 1]

        result = _ask_how_finished(row)
        if result is None:
            print("  Left as-is.")
            continue
        kind, target = result

        notes = _ask("  Any notes? (optional — press Enter to skip): ")

        apply_outcome(rows[idx], kind, target=target, notes=notes)

        try:
            save(path, fieldnames, rows)
        except PermissionError:
            print(f"\n  Couldn't save — is '{path}' open in Excel? "
                  "Close it and try that trade again.\n")
            # Undo the in-memory change so the list stays accurate.
            for k in ("tps_hit", "outcome", "notes", "realised_rr", "pnl"):
                rows[idx][k] = ""
            continue

        print(f"  Saved: {_label(row)} -> {_describe(kind, target)}.")


if __name__ == "__main__":
    main()
