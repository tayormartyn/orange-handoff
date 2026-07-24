"""
recovered_rescore.py — re-score gold with LLM-recovered stops, then report the
honest cleaned aggregate on the now-larger known-R set.

NO scoring logic is changed: recovered stops are fed into the EXISTING signed-off
scorer (archive._score_r). The signed-off archive DB is never mutated — recovered
stops come from the separate parser_revisions.db and are applied in-memory only.

Reports: stops recovered, newly-known-R count, new clean known-R count, mean AND
median (with the same robust checks as gold_clean_report — outlier-driven? stable
across months? median≈mean?), versus the pre-recovery ~+0.26-0.28R.
"""

import sqlite3
import statistics
import sys

import archive
import backfill_audit as BA
import gold_clean_report as G

REVISIONS_DB = "data/parser_revisions.db"


def _accepted_recoveries():
    c = sqlite3.connect(f"file:{REVISIONS_DB}?mode=ro", uri=True)
    c.row_factory = sqlite3.Row
    rows = c.execute("SELECT signal_id, recovered_stop, confidence FROM stop_recoveries "
                     "WHERE validation='accepted'").fetchall()
    c.close()
    return {r["signal_id"]: r["recovered_stop"] for r in rows}


def _evidence_and_cat(conn, signal_id):
    p = conn.execute("SELECT outcome_category, primary_evidence_message_key "
                     "FROM outcome_projections WHERE signal_id=?", (signal_id,)).fetchone()
    if not p:
        return None, ""
    ev = ""
    if p["primary_evidence_message_key"]:
        r = conn.execute("SELECT raw_text FROM raw_message_versions WHERE message_key=? "
                         "ORDER BY version_number DESC LIMIT 1",
                         (p["primary_evidence_message_key"],)).fetchone()
        ev = (r["raw_text"] if r else "") or ""
    return p["outcome_category"], ev


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    recoveries = _accepted_recoveries()
    conn = BA._ro_conn()
    gold = BA.load_gold(conn)

    # Apply recovered stops in-memory and re-score via the EXISTING scorer.
    newly_known = 0
    rescored = 0
    for s in gold:
        if s["signal_id"] not in recoveries:
            continue
        rescored += 1
        s["stop"] = recoveries[s["signal_id"]]            # in-memory only
        cat, ev = _evidence_and_cat(conn, s["signal_id"])
        sig = {"asset": "XAUUSD", "direction": s["direction"],
               "entry_low": s["entry_low"], "entry_high": s["entry_high"],
               "stop": s["stop"], "tp1": s["tp1"], "tp2": s["tp2"], "tp3": s["tp3"],
               "provider": ""}
        try:
            r, known, _label = archive._score_r(sig, cat, ev)
        except Exception:  # noqa: BLE001
            r, known = None, False
        was_known = bool(s["r_is_known"])
        s["calculated_r"] = str(r) if r is not None else None
        s["r_is_known"] = 1 if known else 0
        if known and not was_known:
            newly_known += 1
    conn.close()

    # Re-classify with recovered stops; clean = not broken (G's narrow definition).
    clean, broken = [], []
    for s in gold:
        is_b, reasons = G.classify(s)
        (broken if is_b else clean).append(s)
    clean_known = [s for s in clean if s["r_is_known"] and BA._f(s["calculated_r"]) is not None]

    agg_all = G._agg(gold)
    agg_clean = G._agg(clean)

    print("=" * 92)
    print("  GOLD — RE-SCORED WITH LLM-RECOVERED STOPS (read-only, advisory, scorer UNCHANGED)")
    print("=" * 92)
    print(f"  stops recovered + validated : {len(recoveries)}  (applied to {rescored} archive signals)")
    print(f"  newly KNOWN-R (were unknown) : {newly_known}")
    print(f"  CLEAN: {len(clean)}/{len(gold)}    BROKEN: {len(broken)}/{len(gold)}")
    print("  " + "-" * 88)
    print("  AGGREGATE R (gold known-R; mean = outlier-sensitive, median = robust)")
    print(f"    WITH broken (raw)    : n={agg_all['n']:3d}  mean={agg_all['mean']}  median={agg_all['median']}")
    print(f"    cleaned (post-recovery): n={agg_clean['n']:3d}  mean={agg_clean['mean']}  median={agg_clean['median']}")
    print(f"    (pre-recovery cleaned was: n=66  mean=0.2788  median=0.26)")
    print("  " + "-" * 88)
    # outcome distribution on clean set
    from collections import Counter
    cat = Counter(s["outcome_category"] or "?" for s in clean)
    binr = Counter(s["binary_rollup"] or "?" for s in clean)
    print("  OUTCOME DISTRIBUTION — CLEAN set (post-recovery):")
    for k, v in cat.most_common():
        print(f"    {k:30} {v}")
    print(f"    roll-up: " + "  ".join(f"{k}={v}" for k, v in binr.most_common()))

    # robust checks (reuse gold_clean_report's reports)
    G.contributors_report(clean_known)
    months = G.by_month_report(clean_known)

    # PASS-style read-out
    mean = agg_clean["mean"] or 0
    median = agg_clean["median"] or 0
    pos = [BA._f(s["calculated_r"]) for s in clean_known if BA._f(s["calculated_r"]) > 0]
    top_share = (max(pos) / sum(pos)) if pos else 1.0
    pos_months = sum(1 for m in months.values() if m["mean"] > 0)
    print("\n  " + "-" * 88)
    print("  EDGE HOLDS? (against the robust criteria)")
    print(f"    cleaned mean ~+0.26-0.28R region : {mean}R  -> {'YES' if 0.18 <= mean <= 0.40 else 'CHECK'}")
    print(f"    median ≈ mean (not outlier-driven): mean {mean} vs median {median}  "
          f"-> {'YES' if abs(mean-median) <= 0.15 else 'CHECK'}")
    print(f"    no single outlier driving it     : top winner {top_share*100:.0f}% of +R  "
          f"-> {'YES' if top_share < 0.25 else 'CHECK'}")
    print(f"    positive across months           : {pos_months}/{len(months)}  "
          f"-> {'YES' if pos_months >= 2 else 'CHECK'}")
    print(f"    bigger sample                    : n={agg_clean['n']} clean known-R "
          f"(was 66) -> +{agg_clean['n']-66}")
    print("=" * 92)
    print("  Scorer unchanged; signed-off 28 + LIVE stub untouched; archive DB not mutated.")
    print("=" * 92)


if __name__ == "__main__":
    main()
