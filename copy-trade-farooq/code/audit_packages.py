"""
audit_packages.py — READ-ONLY audit packages for independent review of the gold archive.

Builds three packages under data/audit/ (changes NO scoring, writes nothing to the
archive, never touches the signed-off baseline rows or the LIVE stub):

  8. HIGH-RISK CONTEXT  — every parse-error suspect / cross-asset / recap-flagged
     gold signal WITH the surrounding raw channel messages (a context window), so a
     reviewer can see exactly what the parser saw.   -> data/audit/highrisk_context.txt

  9. ORDINARY-WIN SAMPLE — a stratified random sample (target 150) of ORDINARY gold
     wins (winning, sane R, NOT parse-error-suspect), spread across month and
     direction, with the RANDOM SEED recorded for reproducibility.
                                                     -> data/audit/ordinary_wins_sample.csv

 10. CAPTURE-RECALL PACKS — a BLIND random set of trading days (chosen by DATE, not
     by outcome). For each day, ALL raw channel messages are dumped so signals can be
     hand-counted against the database to find MISSED signals (recall check).
                                                     -> data/audit/capture_recall/<date>.txt

Reads the frozen audit CSV (data/audit/gold_audit_full.csv) for the flags so the
packages are consistent with the frozen flagging. Seed comes from backfill_audit.
"""

import csv
import os
import random
from collections import defaultdict
from datetime import datetime, timezone

import backfill_audit as BA

ARCHIVE_DB = BA.ARCHIVE_DB
AUDIT_DIR = BA.AUDIT_DIR
SEED = BA.MASTER_SEED
AUDIT_CSV = os.path.join(AUDIT_DIR, "gold_audit_full.csv")

CONTEXT_WINDOW = 6          # messages before/after the signal in channel time order
WIN_SAMPLE_TARGET = 150
CAPTURE_RECALL_DAYS = 25    # blind random trading days to dump in full

# context is built for these "needs-eyes-on-raw" flag families
CONTEXT_FLAG_KEYS = BA.PARSE_FLAG_KEYS + ("CROSS_ASSET_EVIDENCE", "RECAP_EVIDENCE",
                                          "STOP_WRONG_SIDE")


def _load_all_messages(conn):
    """Latest version of every message, ordered by (sent_at, message_id)."""
    rows = conn.execute("""
        SELECT r.message_key, r.message_id, r.sent_at_utc, r.raw_text
        FROM raw_message_versions r
        JOIN (SELECT message_key, MAX(version_number) v FROM raw_message_versions
              GROUP BY message_key) m
          ON r.message_key=m.message_key AND r.version_number=m.v
    """).fetchall()
    def k(r):
        try:
            mid = int(r["message_id"])
        except (TypeError, ValueError):
            mid = 0
        return (r["sent_at_utc"] or "", mid)
    return sorted((dict(r) for r in rows), key=k)


def _load_audit_rows():
    with open(AUDIT_CSV, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _signal_key_map(conn):
    """signal_id -> source_message_key (to locate a signal in the message stream)."""
    rows = conn.execute("SELECT signal_id, source_message_key FROM signals "
                        "WHERE asset='XAUUSD'").fetchall()
    return {r["signal_id"]: r["source_message_key"] for r in rows}


# ----------------------------------------------------------------------------
# Package 8 — high-risk context windows
# ----------------------------------------------------------------------------
def build_context(conn, audit_rows, messages, key_map):
    idx_by_key = {m["message_key"]: i for i, m in enumerate(messages)}
    targets = [r for r in audit_rows
               if any(k in r["why"] for k in CONTEXT_FLAG_KEYS)]
    out = os.path.join(AUDIT_DIR, "highrisk_context.txt")
    with open(out, "w", encoding="utf-8") as f:
        f.write("HIGH-RISK CONTEXT PACKAGE — parse-error / cross-asset / recap / wrong-side\n")
        f.write(f"window = +/-{CONTEXT_WINDOW} channel messages.  {len(targets)} signals.\n")
        f.write("READ-ONLY. No scoring changed.\n")
        f.write("=" * 88 + "\n")
        for r in targets:
            f.write(f"\n### {r['date']} {r['direction']} entry={r['entry']} stop={r['stop']} "
                    f"tps={r['tps']} | {r['source']} | {r['outcome']} R={r['R']}\n")
            f.write(f"    FLAGS: {r['why']}\n")
            key = key_map.get(r["signal_id"])
            i = idx_by_key.get(key)
            if i is None:
                f.write("    (source message not located in stream)\n")
                continue
            lo = max(0, i - CONTEXT_WINDOW)
            hi = min(len(messages), i + CONTEXT_WINDOW + 1)
            for j in range(lo, hi):
                m = messages[j]
                mark = " >>>" if j == i else "    "
                txt = (m["raw_text"] or "").replace("\n", " ")[:200]
                f.write(f"{mark} [{m['sent_at_utc']}] {txt}\n")
            f.write("-" * 88 + "\n")
    return out, len(targets)


# ----------------------------------------------------------------------------
# Package 9 — stratified ordinary-win sample
# ----------------------------------------------------------------------------
def build_win_sample(audit_rows):
    # ordinary win = winning, known positive R, NOT a parse-error suspect
    pool = []
    for r in audit_rows:
        if r["binary"] != "win":
            continue
        if r["r_is_known"] != "True":
            continue
        try:
            rv = float(r["R"])
        except (ValueError, TypeError):
            continue
        if rv <= 0:
            continue
        if any(k in r["why"] for k in BA.PARSE_FLAG_KEYS):
            continue   # exclude parse-error suspects -> "ordinary"
        pool.append(r)

    rng = random.Random(SEED)
    # stratify by (YYYY-MM, direction)
    strata = defaultdict(list)
    for r in pool:
        ym = (r["date"] or "")[:7]
        strata[(ym, r["direction"])].append(r)
    for s in strata.values():
        rng.shuffle(s)

    chosen = []
    if len(pool) <= WIN_SAMPLE_TARGET:
        chosen = list(pool)   # take all; pool smaller than target
    else:
        # proportional allocation, then top-up
        total = len(pool)
        alloc = {k: max(1, round(WIN_SAMPLE_TARGET * len(v) / total)) for k, v in strata.items()}
        for k, v in strata.items():
            chosen.extend(v[:alloc[k]])
        rng.shuffle(chosen)
        chosen = chosen[:WIN_SAMPLE_TARGET]

    out = os.path.join(AUDIT_DIR, "ordinary_wins_sample.csv")
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["seed", "stratum_year_month", "signal_id", "date", "source",
                    "direction", "entry", "stop", "tps", "outcome", "R", "evidence"])
        for r in sorted(chosen, key=lambda x: x["date"]):
            w.writerow([SEED, (r["date"] or "")[:7], r["signal_id"], r["date"], r["source"],
                        r["direction"], r["entry"], r["stop"], r["tps"], r["outcome"],
                        r["R"], r["evidence"]])
    return out, len(pool), len(chosen)


# ----------------------------------------------------------------------------
# Package 10 — capture-recall day packs (BLIND by date)
# ----------------------------------------------------------------------------
def build_capture_recall(conn, messages):
    # candidate days = days with >=1 message in the back-filled GOLD era
    # (2025-06-13 onward, where the parser found gold signals) — chosen blind by date.
    era_start = "2025-06-13"
    by_day = defaultdict(list)
    for m in messages:
        day = (m["sent_at_utc"] or "")[:10]
        if day >= era_start:
            by_day[day].append(m)
    days = sorted(by_day.keys())
    rng = random.Random(SEED + 1)   # distinct stream from the win sample
    n = min(CAPTURE_RECALL_DAYS, len(days))
    chosen_days = sorted(rng.sample(days, n))

    cr_dir = os.path.join(AUDIT_DIR, "capture_recall")
    os.makedirs(cr_dir, exist_ok=True)
    # how many DB gold signals fall on each chosen day (for the hand-count comparison)
    gold_by_day = defaultdict(int)
    for r in conn.execute("SELECT sent_at_utc FROM signals WHERE asset='XAUUSD'").fetchall():
        gold_by_day[(r["sent_at_utc"] or "")[:10]] += 1

    index = os.path.join(cr_dir, "_index.txt")
    with open(index, "w", encoding="utf-8") as ix:
        ix.write("CAPTURE-RECALL PACKS — BLIND random trading days (chosen by date, not outcome)\n")
        ix.write(f"seed={SEED + 1}  days={n}  era_start={era_start}\n")
        ix.write("Hand-count the SIGNALS in each day's dump and compare to db_gold_signals "
                 "to find MISSED signals (recall).\n")
        ix.write("=" * 70 + "\n")
        for day in chosen_days:
            msgs = by_day[day]
            fname = os.path.join(cr_dir, f"{day}.txt")
            with open(fname, "w", encoding="utf-8") as f:
                f.write(f"ALL raw channel messages for {day}  ({len(msgs)} messages)\n")
                f.write(f"DB gold signals recorded on this day: {gold_by_day.get(day,0)}\n")
                f.write("=" * 70 + "\n")
                for m in msgs:
                    f.write(f"[{m['sent_at_utc']}] (id {m['message_id']})\n{m['raw_text']}\n")
                    f.write("-" * 40 + "\n")
            ix.write(f"  {day}: {len(msgs):4d} messages | db_gold_signals={gold_by_day.get(day,0)}\n")
    return cr_dir, chosen_days, len(days)


def main():
    import sys
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    os.makedirs(AUDIT_DIR, exist_ok=True)
    conn = BA._ro_conn()
    audit_rows = _load_audit_rows()
    messages = _load_all_messages(conn)
    key_map = _signal_key_map(conn)

    ctx_path, n_ctx = build_context(conn, audit_rows, messages, key_map)
    win_path, pool_n, sample_n = build_win_sample(audit_rows)
    cr_dir, cr_days, cand_days = build_capture_recall(conn, messages)
    conn.close()

    print("=" * 84)
    print("  AUDIT PACKAGES (read-only, advisory — no scoring changed)")
    print("=" * 84)
    print(f"  8. HIGH-RISK CONTEXT : {n_ctx} signals + raw windows  -> {ctx_path}")
    print(f"  9. ORDINARY-WIN SAMPLE: pool={pool_n} ordinary wins; sampled {sample_n} "
          f"(target {WIN_SAMPLE_TARGET}, seed {SEED})")
    if pool_n < WIN_SAMPLE_TARGET:
        print(f"       NOTE: only {pool_n} ordinary wins exist (< {WIN_SAMPLE_TARGET}); took ALL.")
    print(f"       -> {win_path}")
    print(f" 10. CAPTURE-RECALL    : {len(cr_days)} blind days (of {cand_days} candidate days, "
          f"seed {SEED + 1})  -> {cr_dir}/")
    print(f"       days: {', '.join(cr_days)}")
    print("=" * 84)


if __name__ == "__main__":
    main()
