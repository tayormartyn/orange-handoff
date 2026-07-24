"""
log_history.py — review and selectively log signals from history_review.csv into
paper_log.csv, ONE AT A TIME, with duplicate-checking and outcomes.

Why this exists: the history-puller (module_a_telegram.py --history) catches and
classifies past signals into history_review.csv, but turning the good ones into
real logged paper trades — with outcomes, without duplicates — was a manual CSV
edit. This walks you through them carefully instead:

  * shows each "clean signal" (and, with --include-review, REVIEW rows) one at a time
  * auto-checks for likely duplicates already in paper_log.csv and WARNS you
  * asks NEW vs DUPLICATE vs SKIP, then the OUTCOME (win/loss/breakeven/missed/
    unclear/skip) — the same outcome vocabulary as outcome.py
  * a WIN is scored at its REAL R from the trade's own levels (entry→stated
    target), e.g. a "tp1-hit-then-scratched" small win logs at the R to TP1 — NOT
    +1R flat, and never an assumed partial size or guessed price. Full wins (all
    TP) keep their full R. If the stated info can't yield an R, it asks you or
    marks the row for manual entry rather than guessing.
  * only logs the ones YOU confirm, sized + routed through the NORMAL engine
    (conservative entry, slippage, routing tags all applied consistently)
  * makes a timestamped BACKUP of paper_log.csv before it starts
  * shows a running tally and never auto-logs anything without your per-trade say-so

PAPER MODE ONLY. It writes to paper_log.csv (your log) after a backup; it reads
history_review.csv; it connects to no broker, places no order, and never touches
the LIVE stub.

Run it:
    python log_history.py                       # walk the clean signals
    python log_history.py --include-review        # also walk REVIEW rows
    python log_history.py --history other.csv --log other_log.csv   # custom files
"""

import csv
import os
import re
import shutil
import sys
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation

import config
import module_router as router
import module_c_risk as risk
import module_d_logger as logger
import module_b_parser as parser
import outcome as outcome_mod
from models import Signal

try:
    from module_a_telegram import _console_safe
except Exception:                                  # pragma: no cover
    def _console_safe(t):
        return str(t)

HISTORY_FILE = getattr(config, "HISTORY_REVIEW_FILE", "history_review.csv")
LINE = "=" * 70
THIN = "-" * 70


# ----------------------------------------------------------------------------
# Small helpers
# ----------------------------------------------------------------------------
def _num(value):
    try:
        return Decimal(str(value).replace(",", "").replace("£", "").replace("$", "").strip())
    except (InvalidOperation, ValueError, AttributeError):
        return None


def _ask(prompt: str) -> str:
    try:
        return input(prompt).strip()
    except EOFError:
        return "quit"


def _parse_zone(entry_str: str):
    """'4030-4045' / '4030 - 4045' / '2315' -> (low, high) Decimals, or None."""
    nums = [d for d in (_num(x) for x in re.findall(r"\d[\d,]*\.?\d*", entry_str or "")) if d]
    if not nums:
        return None
    return (min(nums), max(nums))


def _hist_date_to_iso(date_str: str) -> str:
    """'2026-06-26 13:58' -> ISO '2026-06-26T13:58:00+00:00'; blank/garbage -> now."""
    date_str = (date_str or "").strip()
    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(date_str, fmt).replace(
                tzinfo=timezone.utc).isoformat(timespec="seconds")
        except ValueError:
            continue
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# ----------------------------------------------------------------------------
# Build a Signal from a reviewed history row
# ----------------------------------------------------------------------------
def build_signal(row: dict):
    """Return (Signal, None) or (None, reason) if the row can't be made into one."""
    asset = (row.get("Asset") or "").strip()
    direction = (row.get("Direction") or "").strip().upper()
    if not asset:
        return None, "no asset"
    if direction not in ("LONG", "SHORT"):
        return None, "no clear direction"
    zone = _parse_zone(row.get("Entry"))
    if zone is None:
        return None, "no entry price"
    low, high = zone
    stop = _num(row.get("Stop"))     # may be None (then it can't be sized)
    targets = [d for d in (_num(row.get(c)) for c in ("TP1", "TP2", "TP3")) if d]
    sig = Signal(
        ticker=asset.upper(),
        pair=asset.upper(),
        direction=direction,
        asset_class="",                          # let the router/risk classify it
        entry_low=low,
        entry_high=high,
        stop_loss=stop,
        targets=targets,
        raw_text=(row.get("RawMessage") or "").strip(),
        source=(row.get("Sender") or "").strip(),
        primary_entry=parser.conservative_entry(direction, low, high),
        order_type="",
    )
    return sig, None


# ----------------------------------------------------------------------------
# Duplicate detection against the existing log
# ----------------------------------------------------------------------------
def find_duplicates(sig: Signal, day: str, existing: list) -> list:
    """
    Existing log rows that look like THIS signal: same ticker + direction + same
    calendar day, and a logged entry near the zone. A warning aid — you decide.
    """
    out = []
    tol = abs(sig.primary_entry) * Decimal("0.003") + Decimal("1")  # ~0.3% + 1
    for r in existing:
        if (r.get("ticker", "").upper() == sig.ticker.upper()
                and r.get("direction", "").upper() == sig.direction.upper()
                and (r.get("timestamp", "") or "")[:10] == day):
            ee = _num(r.get("entry"))
            if ee is None or (sig.entry_low - tol) <= ee <= (sig.entry_high + tol):
                out.append(r)
    return out


# ----------------------------------------------------------------------------
# Outcome -> log-row fields (same vocabulary as outcome.py)
# ----------------------------------------------------------------------------
def apply_choice(row: dict, choice: str, sig: Signal, iso_ts: str,
                 win_rr=None, win_label: str = "", loss_rr=None, loss_label: str = ""):
    """
    Write the outcome the operator chose into the just-logged row.

    WIN: `win_rr` is the realised R from the STATED outcome (R to the stated
    target, R from stated pips, or 0R when the exit can't be reconstructed). None
    -> leave AWAITING a manual realised_rr (never +1R flat, never an assumed partial).
    LOSS: `loss_rr` is the realised R — a MANUAL loss with stated pips scores at its
    actual −R; the original stop is −1R; a manual loss of UNKNOWN magnitude
    (loss_rr is None) is still logged as a LOSS, awaiting a manual −R (never zero,
    never dropped, never silently −1R). A loss is never dropped.
    """
    row["timestamp"] = iso_ts                  # use the HISTORICAL date, not 'now'
    bits = ["back-logged from history"]
    if not sig.targets:
        bits.append("no TP in signal")
    note = "; ".join(bits)

    if choice == "win":
        if win_rr is not None:
            # Real R from the trade's own stated levels — NOT +1R flat.
            row["outcome"] = "WIN"
            row["realised_rr"] = str(win_rr)
            row["notes"] = note + f" [win — {win_label}: {win_rr}R, stated]"
        else:
            # Stated info doesn't allow an R calc -> leave awaiting MANUAL entry.
            row["outcome"] = ""
            row["notes"] = note + (f" — WIN ({win_label or 'partial'}) but realised_rr "
                                   "needs MANUAL entry (not guessed)")
    elif choice == "loss":
        row["outcome"] = "LOSS"
        if loss_rr is None:
            # A MANUAL loss whose magnitude can't be stated — still a LOSS, but the
            # −R is left for MANUAL entry (never zero, never a silent −1R).
            row["notes"] = note + (f" [manual loss — {loss_label or 'magnitude unknown'}: "
                                   "realised_rr needs MANUAL entry (negative, not guessed)]")
        elif loss_rr != Decimal("-1"):
            # A MANUAL loss scored at its ACTUAL stated size — not a flat −1R.
            row["realised_rr"] = str(loss_rr)
            row["notes"] = note + f" [manual loss — {loss_label}: {loss_rr}R, stated]"
        else:
            row["tps_hit"] = "SL"               # review -> -1R (original stop / full loss)
            row["notes"] = note + (f" [{loss_label}]" if loss_label else "")
    elif choice == "breakeven":
        row["outcome"] = "BE"                   # review -> 0R
        row["notes"] = note
    elif choice == "missed":
        row["outcome"] = "MISSED"
        row["realised_rr"] = "0"
        row["pnl"] = "0"
        row["notes"] = note
    elif choice == "unclear":
        row["outcome"] = ""                     # left awaiting, like the CONFIRM ones
        row["notes"] = note + " — outcome UNCLEAR / CONFIRM"


# ----------------------------------------------------------------------------
# Scoring a WIN at its real, STATED R (no +1R flat, no assumed partials)
# ----------------------------------------------------------------------------
def _target_from_evidence(text: str):
    """
    Which target the evidence STATES was reached: 'all' (all tp / all targets),
    the highest named TP number (int), or None if no target is named.
    """
    t = (text or "").lower()
    if re.search(r"\ball\s+(?:tp|tps|targets?)\b", t):
        return "all"
    nums = [int(n) for n in re.findall(r"\btp\s*([1-9])\b", t)]
    nums += [int(n) for n in re.findall(r"\btarget\s*([1-9])\b", t)]
    return max(nums) if nums else None


_PIPS_RE = re.compile(r"([+-]?\s*\d+(?:\.\d+)?)\s*pi(?:p|sp)s?\b", re.I)  # "pisp" = Farouk's typo for "pips"


def _stated_pips(text: str):
    """The largest pips magnitude stated in the text, or None."""
    vals = []
    for m in _PIPS_RE.finditer(text or ""):
        v = _num(m.group(1).replace(" ", ""))
        if v is not None:
            vals.append(abs(v))
    return max(vals) if vals else None


def _stop_is_valid(sig: Signal) -> bool:
    """False if the signal's stop is on the WRONG side of entry (a LONG stop at/
    above entry, a SHORT stop at/below entry). True when it can't tell."""
    lo, hi, sl = sig.entry_low, sig.entry_high, sig.stop_loss
    if lo is None or hi is None or sl is None:
        return True
    d = (sig.direction or "").upper()
    if d.startswith("L") or d == "BUY":
        return sl < min(lo, hi)
    if d.startswith("S") or d == "SELL":
        return sl > max(lo, hi)
    return True


_EXIT_PRICE_RE = re.compile(r"(?:reached|hit|to|at|@)\s+([0-9][0-9,]{2,}(?:\.\d+)?)", re.I)


def _r_from_exit_price(sig: Signal, risk: Decimal, evidence: str):
    """
    R from a STATED exit PRICE ("reached 63,900", "took profit at 2350"), measured
    from the nearer entry against the trade's risk. Returns (R, label) or None.
    Only accepts a price on the PROFIT side and within a sane band of entry.
    """
    if risk <= 0 or sig.entry_low is None:
        return None
    lo, hi = min(sig.entry_low, sig.entry_high), max(sig.entry_low, sig.entry_high)
    d = (sig.direction or "").upper()
    is_long = d.startswith("L") or d == "BUY"
    for m in _EXIT_PRICE_RE.finditer(evidence or ""):
        price = _num(m.group(1))
        if price is None or price <= 0:
            continue
        # must look like a price on this instrument's scale (within ~3x of entry)
        if not (hi / 3 <= price <= hi * 3):
            continue
        move = (price - hi) if is_long else (lo - price)
        if move <= 0:                      # not on the profit side -> ignore
            continue
        return (Decimal(str(move)) / risk).quantize(Decimal("0.01")), f"exit {price}"
    return None


def _resolve_win_rr(sig: Signal, ticket, row: dict):
    """
    Realised R for a WIN, from the STATED outcome ONLY. Returns (Decimal R, label)
    or (None, label) to mark the row for MANUAL entry. The rule (honest, both ways):

      * INVALID STOP (stop on the wrong side of entry) -> 0R: R is meaningless, so
        it stays a win but isn't credited a fabricated target R.
      * An EXPLICIT target HIT ("tp1 hit", "all tp hit") -> full R to that target.
      * Otherwise DON'T OVER-CREDIT a distant target that was only instructed: when
        stated pips are present, score to the SMALLER of (pips R, target R). A bare
        take/now instruction with no pips -> R to that target. Stated pips with no
        target -> pips R, but CAPPED at the furthest target's R (so a hyped "500
        pips" on a ~50-point gold move can never exceed what the targets allow).
      * A stated exit PRICE ("reached 63,900") -> R from that price.
      * Only when profit is confirmed with GENUINELY no quantity ("take tp",
        "closed in profit", "almost reached tp1") -> 0R.
    """
    import module_a_telegram as listener
    rr_targets = [Decimal(str(r)) for r in (getattr(ticket, "rr_targets", []) or [])]
    evidence = (row.get("OutcomeEvidence") or row.get("RawMessage") or "")
    risk = Decimal(str(getattr(ticket, "sl_dollar", 0) or 0))   # |entry-stop| in price

    def r_to(idx0):
        if 0 <= idx0 < len(rr_targets):
            return rr_targets[idx0].quantize(Decimal("0.01"))
        return None

    # An invalid stop makes every R meaningless -> confirmed win, but 0R.
    if risk <= 0 or not _stop_is_valid(sig):
        return Decimal("0.00"), "profit confirmed, invalid stop -> 0R"

    # "almost reached tp1" did NOT reach the target -> 0R, never credit the target.
    if listener._OUT_ALMOST_RE.search(evidence):
        return Decimal("0.00"), "profit confirmed (almost), R unknown -> 0R"

    explicit_hit = bool(listener._OUT_TARGET_HIT_CONFIRM_RE.search(evidence))
    pips = _stated_pips(evidence)
    furthest = r_to(len(rr_targets) - 1) if rr_targets else None

    # R to the named target named in the evidence (if its price is in the signal).
    tgt = _target_from_evidence(evidence)
    r_target, target_label = None, None
    if tgt == "all" and rr_targets:
        r_target, target_label = r_to(len(rr_targets) - 1), "all targets"
    elif isinstance(tgt, int):
        r = r_to(tgt - 1)
        if r is not None:
            r_target, target_label = r, f"TP{tgt}"

    # R from the stated pips, CAPPED at the furthest target (never over-credit).
    # Gold "pips" are $0.10 increments, so convert to a price-point move first.
    r_pips, pips_label = None, None
    if pips is not None and pips > 0:
        move = Decimal(str(listener._pip_points(getattr(sig, "ticker", ""), pips)))
        rp = (move / risk).quantize(Decimal("0.01"))
        if furthest is not None and rp > furthest:
            r_pips, pips_label = furthest, f"+{pips} pips (capped at furthest target)"
        else:
            r_pips, pips_label = rp, f"+{pips} pips"

    # 1. An explicit target HIT -> full R to that target (don't downgrade to pips).
    if explicit_hit and r_target is not None:
        return r_target, target_label
    # 2. Both a target and stated pips, NOT an explicit hit -> the SMALLER (don't
    #    over-credit a distant target that wasn't actually reached).
    if r_target is not None and r_pips is not None:
        return (r_pips, pips_label) if r_pips < r_target else (r_target, target_label)
    # 3. Only stated pips (no reconstructable target) -> the capped pips R.
    if r_pips is not None:
        return r_pips, pips_label
    # 4. Only a named target (a take/now instruction, no pips) -> R to that target.
    if r_target is not None:
        return r_target, target_label

    # 5. A stated exit PRICE reached -> R from that price.
    by_price = _r_from_exit_price(sig, risk, evidence)
    if by_price is not None:
        return by_price

    # 6. Profit confirmed but genuinely no stated quantity -> 0R (never assumed).
    return Decimal("0.00"), "profit confirmed, R unknown -> 0R"


def _resolve_loss_rr(ticket, row: dict):
    """
    Realised R for a LOSS. Returns (Decimal R, label), or (None, label) when it's
    a manual loss whose MAGNITUDE can't be stated (mark for manual entry — still a
    loss, never dropped):

      * a MANUAL/net loss with a STATED size ("cut for -40 pips") -> −pips vs risk;
      * a MANUAL/net loss with NO stated size ("close it for a small loss", "count
        it as a loss overall") -> (None) R unknown but negative — enter manually;
      * the original stop being hit -> −1R.
    """
    import module_a_telegram as listener
    evidence = (row.get("OutcomeEvidence") or row.get("RawMessage") or "")
    risk = Decimal(str(getattr(ticket, "sl_dollar", 0) or 0))
    asset = getattr(getattr(ticket, "signal", None), "ticker", "") or row.get("Asset", "")
    manual = re.search(
        r"(?<![\d.,])-\s*\d+|cut\b|closed?\s+(?:for|in)\b|stopped\s+for|manually\s+clos|"
        r"small\s+loss|loss\s+overall|count\s+it\s+as\s+a\s+loss|\d+\s+wins?\s*,?\s*\d+\s+loss",
        evidence, re.I)
    pips = _stated_pips(evidence)
    if manual and pips is not None and pips > 0 and risk > 0:
        # Gold "pips" are $0.10 increments -> convert to a price-point move first.
        move = Decimal(str(listener._pip_points(asset, pips)))
        return (-(move) / risk).quantize(Decimal("0.01")), f"-{pips} pips"
    if manual:
        return None, "manual loss, magnitude unknown -> enter R"
    return Decimal("-1"), "original stop / full loss"


# ----------------------------------------------------------------------------
# Display
# ----------------------------------------------------------------------------
def _show_signal(n: int, total: int, row: dict, sig: Signal):
    targets = "  ".join(str(t) for t in sig.targets) or "(none)"
    zone = str(sig.entry_low) if sig.entry_low == sig.entry_high \
        else f"{sig.entry_low} – {sig.entry_high}"
    print(THIN)
    print(f"  Signal {n} of {total}     [{row.get('Classification','?')}]"
          f"   confidence: {row.get('Confidence','') or '—'}")
    print(THIN)
    print(f"    Date        : {row.get('Date','')}")
    print(f"    Sender      : {_console_safe(row.get('Sender',''))}")
    print(f"    Asset       : {sig.ticker}    Direction: {sig.direction}")
    print(f"    Entry zone  : {zone}")
    print(f"    Primary entry (conservative): {sig.primary_entry}")
    print(f"    Stop loss   : {sig.stop_loss if sig.stop_loss is not None else '(none)'}")
    print(f"    Targets     : {targets}")
    print(f"    Raw message : {_console_safe(row.get('RawMessage',''))[:200]}")


# ----------------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------------
def _parse_args(argv):
    opts = {"history": HISTORY_FILE, "log": config.PAPER_LOG_FILE, "include_review": False}
    i = 0
    while i < len(argv):
        a = argv[i]
        if a in ("-h", "--help", "help"):
            opts["help"] = True
        elif a == "--include-review":
            opts["include_review"] = True
        elif a == "--history":
            i += 1
            opts["history"] = argv[i] if i < len(argv) else opts["history"]
        elif a == "--log":
            i += 1
            opts["log"] = argv[i] if i < len(argv) else opts["log"]
        else:
            print(f"  (Ignoring unrecognised option: {a})")
        i += 1
    return opts


def _usage():
    print("  Usage:")
    print("    python log_history.py                  # walk the clean signals")
    print("    python log_history.py --include-review   # also walk REVIEW rows")
    print("    python log_history.py --history F.csv --log L.csv   # custom files")


def main():
    argv = [a for a in sys.argv[1:] if a.strip()]
    opts = _parse_args(argv)
    if opts.get("help"):
        _usage()
        return

    hist_path, log_path = opts["history"], opts["log"]

    if not os.path.exists(hist_path):
        print(f"\n  No history file found ('{hist_path}').")
        print("  Create one first:  python module_a_telegram.py --history 500\n")
        return

    try:
        with open(hist_path, newline="", encoding="utf-8") as f:
            hist_rows = list(csv.DictReader(f))
    except (OSError, csv.Error) as e:
        print(f"\n  Couldn't read '{hist_path}': {e}\n")
        return

    wanted = {"clean signal"} | ({"REVIEW"} if opts["include_review"] else set())
    candidates = [r for r in hist_rows if (r.get("Classification") or "").strip() in wanted]

    print(LINE)
    print("   LOG HISTORY — review & selectively log past signals  (PAPER)")
    print(LINE)
    print(f"   From : {hist_path}")
    print(f"   Into : {log_path}")
    print(f"   Rows : {len(candidates)} to review "
          f"({'clean + REVIEW' if opts['include_review'] else 'clean signals only'})")
    print("   Nothing is logged without your per-trade confirmation. Duplicates and")
    print("   skips are never written. No broker, no orders, LIVE stub untouched.")
    print(LINE)

    if not candidates:
        print("\n  Nothing to review. (No matching rows — try --include-review.)\n")
        return

    # --- BACKUP first -------------------------------------------------------
    backup_path = None
    if os.path.exists(log_path):
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = f"{log_path}.backup_{stamp}.csv"
        try:
            shutil.copy2(log_path, backup_path)
            print(f"\n  Backup made: {os.path.abspath(backup_path)}\n")
        except OSError as e:
            print(f"\n  Couldn't back up '{log_path}': {e}\n  Stopping — fix that first.\n")
            return

    # Existing log rows (for duplicate checks); grows as we log.
    existing = []
    if os.path.exists(log_path):
        try:
            _fn, existing = outcome_mod.load(log_path)
        except (OSError, csv.Error):
            existing = []

    pot = Decimal(config.POT_SIZE)
    logged = skipped = duplicates = errors = 0

    for idx, row in enumerate(candidates, start=1):
        sig, reason = build_signal(row)
        if sig is None:
            print(THIN)
            print(f"  Signal {idx} of {len(candidates)}: can't build a trade ({reason}) — skipping.")
            print(f"    {_console_safe(row.get('RawMessage',''))[:120]}")
            skipped += 1
            continue

        _show_signal(idx, len(candidates), row, sig)

        # --- Duplicate warning ---------------------------------------------
        day = _hist_date_to_iso(row.get("Date"))[:10]
        dupes = find_duplicates(sig, day, existing)
        if dupes:
            print("\n  ** WARNING: this looks like it may ALREADY be logged "
                  f"({len(dupes)} match):")
            for d in dupes[:3]:
                print(f"       {d.get('timestamp','')[:16]}  {d.get('ticker','')} "
                      f"{d.get('direction','')}  entry {d.get('entry','')}  "
                      f"outcome {d.get('outcome','') or '(open)'}")

        # --- Q1: new / duplicate / skip ------------------------------------
        a1 = _ask("\n  NEW trade, DUPLICATE (skip), or SKIP for now?  [n/d/s, q=quit]: ").lower()
        if a1 in ("q", "quit"):
            print("\n  Stopping here. Progress so far is saved.")
            break
        if a1 in ("d", "dup", "duplicate"):
            print("  Marked DUPLICATE — not logged.")
            duplicates += 1
            continue
        if a1 not in ("n", "new"):
            print("  Skipped for now.")
            skipped += 1
            continue

        # --- Q2: outcome ----------------------------------------------------
        a2 = _ask("  Outcome?  win / loss / breakeven / missed / unclear / skip "
                  "[w/l/b/m/u/s]: ").lower()
        choice = {
            "w": "win", "win": "win",
            "l": "loss", "loss": "loss",
            "b": "breakeven", "be": "breakeven", "breakeven": "breakeven",
            "m": "missed", "miss": "missed", "missed": "missed",
            "u": "unclear", "unclear": "unclear",
        }.get(a2)
        if choice is None:
            print("  No valid outcome — skipped for now.")
            skipped += 1
            continue

        # --- Size + route through the NORMAL engine ------------------------
        try:
            decision = router.route(sig)
            ticket = risk.size_signal(sig, pot, require_targets=False)
        except risk.RiskError as e:
            print(f"  Engine couldn't size this — NOT logged:\n    {e}")
            errors += 1
            continue
        except Exception as e:                       # noqa: BLE001
            print(f"  Couldn't process this — NOT logged: {e}")
            errors += 1
            continue

        # --- A WIN is scored at its real, STATED R (never +1R flat); a LOSS at
        #     its actual stated size (manual) or -1R (original stop) ------------
        win_rr, win_label = (None, "")
        loss_rr, loss_label = (None, "")
        if choice == "win":
            win_rr, win_label = _resolve_win_rr(sig, ticket, row)
            if win_rr is not None:
                print(f"    Win scored at {win_rr}R ({win_label}) — from the trade's "
                      "own stated levels, not +1R flat.")
            else:
                print(f"    Win left AWAITING a manual realised_rr ({win_label}) — not guessed.")
        elif choice == "loss":
            loss_rr, loss_label = _resolve_loss_rr(ticket, row)
            if loss_rr is not None:
                print(f"    Loss scored at {loss_rr}R ({loss_label}).")
            else:
                print(f"    Loss left AWAITING a manual -R ({loss_label}) — not guessed.")

        # --- Log it, then write the chosen outcome onto the new row --------
        try:
            logger.log_ticket(ticket, path=log_path, routing=decision)
            fieldnames, rows = outcome_mod.load(log_path)
            apply_choice(rows[-1], choice, sig, _hist_date_to_iso(row.get("Date")),
                         win_rr=win_rr, win_label=win_label,
                         loss_rr=loss_rr, loss_label=loss_label)
            outcome_mod.save(log_path, fieldnames, rows)
            existing.append(rows[-1])                 # so later rows dedup against it
        except Exception as e:                        # noqa: BLE001
            print(f"  Couldn't write to the log — NOT logged: {e}")
            errors += 1
            continue

        logged += 1
        if choice == "win":
            result_desc = f"WIN {win_rr}R" if win_rr is not None else "WIN (manual R pending)"
        elif choice == "loss":
            result_desc = f"LOSS {loss_rr}R" if loss_rr is not None else "LOSS (manual R pending)"
        else:
            result_desc = choice.upper()
        print(f"  LOGGED: {sig.ticker} {sig.direction} {ticket.lots} lot(s)  "
              f"-> {result_desc}   (running: {logged} logged, "
              f"{duplicates} dup, {skipped} skipped)")

    # --- Final tally --------------------------------------------------------
    print("\n" + LINE)
    print(f"  DONE.  Logged {logged}   ·   Skipped {skipped}   ·   "
          f"Duplicates {duplicates}" + (f"   ·   Couldn't size {errors}" if errors else ""))
    if backup_path:
        print(f"  Backup of the pre-run log: {os.path.abspath(backup_path)}")
    if logged:
        print("  Review the result:  python review.py    (or  python status.py)")
    print("  Nothing was sent to a broker. PAPER mode; LIVE stub untouched.")
    print(LINE)


if __name__ == "__main__":
    main()
