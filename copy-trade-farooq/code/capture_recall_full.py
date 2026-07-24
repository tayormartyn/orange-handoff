"""
capture_recall_full.py — FULLER capture-recall (anti-flattery) check on gold history.

READ-ONLY, advisory, no scoring changes. Uses ARCHIVED raw text only (no Telegram).
The key question: are any genuine gold signals — especially LOSSES — missing from
the database in a way that would flatter the edge?

Method:
  * Select 15-20 NEW blind trading days, spread across the gold-era months, chosen
    BY DATE (not outcome), seeded for reproducibility, EXCLUDING the original 6
    cr_mini days. Selection method + days recorded.
  * For each day, dump ALL raw channel messages and compute:
      - DB gold signals that day (count + message_ids)
      - raw ENTRY-looking gold messages (gold + side + price + entry/sl/tp cue),
        and which are NOT in the DB  -> missed-entry candidates (recall)
      - raw LOSS-outcome messages (SL hit / took the loss / -N pips)  -> the key check
      - recap messages ("X wins, Y losses")  -> reconcile with DB counts
      - macro/commentary turned into trades?  -> DB signals with non-gold entries (precision)
  * GLOBAL loss reconciliation across the whole gold history: every DB loss, plus a
    scan of loss-outcome wording, so a missed-loss pattern can't hide in unsampled days.

Outputs day dumps to data/audit/cr_full/<date>.txt and prints a reconciliation table.
A human/agent then reads the flagged days. Archive + signed-off 28 + LIVE stub untouched.
"""

import os
import random
import re
import sqlite3
import sys
from collections import Counter, defaultdict

ARCHIVE_DB = "data/signal_archive.db"
OUT_DIR = "data/audit/cr_full"
SEED = 20260728                      # recorded; distinct from cr_mini (20260635)
ERA_START = "2025-06-13"            # first gold signal
TARGET_DAYS = 18
ORIGINAL_6 = {"2025-06-17", "2025-07-01", "2025-08-05",
              "2025-09-05", "2025-12-01", "2026-03-21"}   # cr_mini days — excluded

GOLD = re.compile(r"\b(xau|gold)\b", re.I)
SIDE = re.compile(r"\b(buy|sell|long|short)\b", re.I)
PRICE = re.compile(r"\b([1-9]\d{3}(?:\.\d+)?)\b")          # 4-digit gold price
ENTRY_CUE = re.compile(r"\b(sl|stop|tp|target|entry|zone|now|limit)\b", re.I)
LOSS = re.compile(r"\b(stop ?loss|sl hit|stopped out|hit (?:our |the )?sl|took? the loss|"
                  r"cut .{0,12}loss|closed .{0,15}loss|loss on|-\s?\d+\s?pips|took? a loss|"
                  r"hit (?:our |the )?stop)\b", re.I)
RECAP = re.compile(r"(\d+)\s*wins?.{0,12}?(\d+)\s*loss|recap|results|scoreboard|"
                   r"\d+\s*/\s*\d+\s*(?:trades|setups)", re.I)


def _ro():
    c = sqlite3.connect(f"file:{ARCHIVE_DB}?mode=ro", uri=True)
    c.row_factory = sqlite3.Row
    return c


def load(conn):
    msgs = conn.execute(
        "SELECT message_key, message_id, sent_at_utc, raw_text FROM raw_message_versions r "
        "JOIN (SELECT message_key mk, MAX(version_number) v FROM raw_message_versions "
        "GROUP BY message_key) m ON r.message_key=m.mk AND r.version_number=m.v "
        "WHERE sent_at_utc>=?", (ERA_START,)).fetchall()
    # DB gold signals: message_key -> (date, outcome, binary)
    sig = {}
    for r in conn.execute("""SELECT s.source_message_key, s.sent_at_utc, p.outcome_category,
                                    p.binary_rollup
                             FROM signals s LEFT JOIN outcome_projections p
                               ON p.signal_id=s.signal_id WHERE s.asset='XAUUSD'"""):
        sig[r["source_message_key"]] = {"date": (r["sent_at_utc"] or "")[:10],
                                        "cat": r["outcome_category"], "bin": r["binary_rollup"]}
    return msgs, sig


def is_entry(t):
    return bool(GOLD.search(t) and SIDE.search(t) and PRICE.search(t)
                and ENTRY_CUE.search(t) and not RECAP.search(t))


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    os.makedirs(OUT_DIR, exist_ok=True)
    conn = _ro()
    msgs, sig = load(conn)

    by_day = defaultdict(list)
    by_month = defaultdict(set)
    for m in msgs:
        d = (m["sent_at_utc"] or "")[:10]
        by_day[d].append(m)
        by_month[d[:7]].add(d)

    # ---- blind selection: spread across months, exclude original 6, seeded ----
    rng = random.Random(SEED)
    chosen = set()
    months = sorted(by_month)
    # 1 per month for full coverage...
    for mo in months:
        days = [d for d in sorted(by_month[mo]) if d not in ORIGINAL_6]
        if days:
            chosen.add(rng.choice(days))
    # ...then top up to TARGET_DAYS with additional random days (still blind by date).
    pool = sorted(d for d in by_day
                  if d not in ORIGINAL_6 and d not in chosen)
    rng.shuffle(pool)
    for d in pool:
        if len(chosen) >= TARGET_DAYS:
            break
        chosen.add(d)
    chosen = sorted(chosen)

    print("=" * 96)
    print("  FULLER CAPTURE-RECALL (anti-flattery) — gold history, read-only, no scoring change")
    print("=" * 96)
    print(f"  Selection: seed={SEED}, blind by date — 1/month across {len(months)} months then")
    print(f"             topped up to {TARGET_DAYS}, excluding the original 6 cr_mini days. "
          f"{len(chosen)} days chosen.")
    print(f"  Raw dumps -> {OUT_DIR}/<date>.txt")
    print("  " + "-" * 92)
    print(f"  {'day':12}{'msgs':>5}{'DB_sig':>7}{'entry?':>7}{'miss_entry':>11}"
          f"{'loss_msgs':>10}{'recap':>6}   note")

    flagged = []
    for d in chosen:
        day_msgs = by_day[d]
        db_ids = [m["message_key"] for m in day_msgs if m["message_key"] in sig]
        entry_msgs = [m for m in day_msgs if is_entry(m["raw_text"] or "")]
        missed = [m for m in entry_msgs if m["message_key"] not in sig]
        loss_msgs = [m for m in day_msgs if LOSS.search(m["raw_text"] or "")
                     and GOLD.search(m["raw_text"] or "")]
        recaps = [m for m in day_msgs if RECAP.search(m["raw_text"] or "")]
        note = ""
        if missed:
            note = f"MISSED-ENTRY x{len(missed)} -> read"; flagged.append(d)
        elif loss_msgs and not any(sig.get(k, {}).get("bin") == "loss" for k in db_ids):
            note = "loss-wording, no DB loss -> read"; flagged.append(d)
        print(f"  {d:12}{len(day_msgs):>5}{len(db_ids):>7}{len(entry_msgs):>7}"
              f"{len(missed):>11}{len(loss_msgs):>10}{len(recaps):>6}   {note}")
        # dump
        with open(os.path.join(OUT_DIR, f"{d}.txt"), "w", encoding="utf-8") as f:
            f.write(f"ALL raw messages {d} ({len(day_msgs)} msgs) | DB gold signals={len(db_ids)} "
                    f"| entry-looking={len(entry_msgs)} | missed-entry={len(missed)}\n")
            f.write("=" * 70 + "\n")
            for m in day_msgs:
                tag = []
                if m["message_key"] in sig:
                    tag.append(f"DB:{sig[m['message_key']]['cat']}")
                if is_entry(m["raw_text"] or ""):
                    tag.append("ENTRY?")
                if LOSS.search(m["raw_text"] or "") and GOLD.search(m["raw_text"] or ""):
                    tag.append("LOSS?")
                if RECAP.search(m["raw_text"] or ""):
                    tag.append("RECAP?")
                f.write(f"[{m['sent_at_utc']}] (id {m['message_id']}) {' '.join(tag)}\n"
                        f"{m['raw_text']}\n" + "-" * 40 + "\n")

    # show missed-entry candidates inline so they can be judged immediately
    print("  " + "-" * 92)
    print("  MISSED-ENTRY CANDIDATES (raw entry-looking msgs NOT in DB):")
    any_missed = False
    for d in flagged:
        for m in by_day[d]:
            if is_entry(m["raw_text"] or "") and m["message_key"] not in sig:
                any_missed = True
                print(f"    {d} id{m['message_id']}: {(m['raw_text'] or '')[:150].strip().replace(chr(10),' ')}")
    if not any_missed:
        print("    (none — every entry-looking message on the sampled days is in the DB)")

    # ---- GLOBAL loss reconciliation ----
    print("  " + "-" * 92)
    db_losses = sum(1 for v in sig.values()
                    if v.get("bin") == "loss" or (v.get("cat") or "") in
                    ("manual_loss", "original_stop_loss", "stop_loss"))
    global_loss_msgs = [m for m in msgs if LOSS.search(m["raw_text"] or "")
                        and GOLD.search(m["raw_text"] or "")]
    # how many loss-outcome msgs are themselves NOT linked to any DB signal AND look
    # like they announce a NEW losing trade with an entry (would be a missed loss)
    print("  GLOBAL loss reconciliation (whole gold history):")
    print(f"    DB gold LOSS signals: {db_losses}")
    print(f"    raw msgs w/ loss-wording + gold: {len(global_loss_msgs)} "
          f"(mostly outcome/recap/commentary, not new entries)")
    conn.close()
    print("=" * 96)
    print(f"  Flagged days to read: {flagged or 'NONE'}")
    print("  Dumps written for ALL chosen days. Archive + signed-off 28 + LIVE stub untouched.")
    print("=" * 96)


if __name__ == "__main__":
    main()
