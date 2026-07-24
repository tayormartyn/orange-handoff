"""
gold_clean_report.py — READ-ONLY honest cleaning + measurement of the 296 gold signals.

Right-sized, NOT a heavyweight audit. It removes only GENUINELY BROKEN parse rows
(garbled level/R data) and reports the honest cleaned aggregate. It does NOT remove
legitimate-but-unusual signals (managed exits, no explicit TP, re-entries) — those
are kept and merely spot-checked.

BROKEN-PARSE (narrow, defensible — the data feeding R is garbage):
  * implausible R: |R| > 5
  * non-gold / absurd entry: entry outside a plausible gold band ($800–$8000)
  * malformed level: a stop/TP < 50% or > 200% of the entry (e.g. a "60" target)
  * stop on the WRONG side of entry
  * missing / zero ENTRY or STOP (core levels needed to define risk/R)
  * absurd TP distance: a TP implying a > 30% move from entry
  * extreme risk: |entry-stop| < $2 or > $200 (produces garbage R)
NOT broken (kept): no TP only, managed_profit, re-entry, recap/cross-asset evidence.

ADVISORY ONLY. No scoring logic changed. Reads the archive read-only; the signed-off
28 baseline and the LIVE stub are untouched. Gold denominator (296) is reported
separately from the 406 all-asset total.

Usage:  python gold_clean_report.py
"""

import statistics
import sys

import backfill_audit as BA   # reuse read-only helpers + load_gold

GOLD_BAND = (800.0, 8000.0)   # plausible XAU/USD over 2023–2026
LEVEL_LOW, LEVEL_HIGH = 0.5, 2.0
ABSURD_MOVE = 0.30
RISK_MIN, RISK_MAX = 2.0, 200.0
R_IMPLAUSIBLE = 5.0


def classify(s):
    """Return (is_broken, reasons[]) for one gold signal. Narrow parse-error test."""
    lo, hi = BA._f(s["entry_low"]), BA._f(s["entry_high"])
    stop = BA._f(s["stop"])
    tps = [BA._f(s["tp1"]), BA._f(s["tp2"]), BA._f(s["tp3"])]
    entry_mid = (lo + hi) / 2 if (lo is not None and hi is not None) else lo
    rval = BA._f(s["calculated_r"]) if s["r_is_known"] else None
    direction = (s["direction"] or "").upper()
    reasons = []

    if rval is not None and abs(rval) > R_IMPLAUSIBLE:
        reasons.append(f"implausible R={rval:g}")
    if entry_mid in (None, 0):
        reasons.append("missing/zero entry")
    elif not (GOLD_BAND[0] <= entry_mid <= GOLD_BAND[1]):
        reasons.append(f"non-gold entry={entry_mid:g}")
    if stop in (None, 0):
        reasons.append("missing/zero stop")
    if entry_mid and entry_mid != 0:
        for nm, v in [("stop", stop), ("tp1", tps[0]), ("tp2", tps[1]), ("tp3", tps[2])]:
            if v is not None and v != 0 and (v < LEVEL_LOW * entry_mid or v > LEVEL_HIGH * entry_mid):
                reasons.append(f"malformed {nm}={v:g}")
        for i, t in enumerate(tps, 1):
            if t is not None and abs(t - entry_mid) / entry_mid > ABSURD_MOVE:
                reasons.append(f"absurd tp{i} dist ({t:g})")
        if stop:
            if direction in ("LONG", "BUY") and stop >= entry_mid:
                reasons.append("stop wrong side (long stop>=entry)")
            if direction in ("SHORT", "SELL") and stop <= entry_mid:
                reasons.append("stop wrong side (short stop<=entry)")
            risk = abs(entry_mid - stop)
            if risk < RISK_MIN:
                reasons.append(f"tiny risk ${risk:g}")
            elif risk > RISK_MAX:
                reasons.append(f"huge risk ${risk:g}")
    return (len(reasons) > 0), reasons


def _agg(rows):
    rs = [float(r["calculated_r"]) for r in rows
          if r["r_is_known"] and BA._f(r["calculated_r"]) is not None]
    if not rs:
        return {"n": 0, "mean": None, "median": None}
    return {"n": len(rs), "mean": round(statistics.mean(rs), 4),
            "median": round(statistics.median(rs), 4)}


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    conn = BA._ro_conn()
    gold = BA.load_gold(conn)

    clean, broken = [], []
    for s in gold:
        is_b, reasons = classify(s)
        s["_reasons"] = reasons
        (broken if is_b else clean).append(s)

    all_agg = _agg(gold)
    clean_agg = _agg(clean)
    broken_agg = _agg(broken)
    # context aggregates
    signed = [s for s in gold if s["source"] == "signed_off"]
    newgold = [s for s in gold if s["source"] == "backfill"]
    newgold_clean = [s for s in clean if s["source"] == "backfill"]

    print("=" * 92)
    print("  GOLD — HONEST CLEANED MEASUREMENT (read-only, advisory, NO scoring changed)")
    print("=" * 92)
    print(f"  GOLD denominator: {len(gold)}  (signed_off=27 + backfill=269)  "
          f"[separate from the 406 all-asset total]")
    print(f"  CLEAN: {len(clean)} / {len(gold)}    BROKEN-PARSE: {len(broken)} / {len(gold)}")
    print(f"    of backfill (269): clean={len(newgold_clean)}  broken={len(newgold)-len(newgold_clean)}")
    print(f"    of signed_off (27): clean={sum(1 for s in clean if s['source']=='signed_off')}  "
          f"broken={sum(1 for s in broken if s['source']=='signed_off')}")
    print("  " + "-" * 88)
    print("  AGGREGATE R  (gold known-R only; mean = outlier-sensitive, median = robust)")
    print(f"    WITH broken (raw)   : n={all_agg['n']:3d}  mean={all_agg['mean']:<9}  median={all_agg['median']}")
    print(f"    WITHOUT broken (clean): n={clean_agg['n']:3d}  mean={clean_agg['mean']:<9}  median={clean_agg['median']}")
    print(f"    broken-only         : n={broken_agg['n']:3d}  mean={broken_agg['mean']:<9}  median={broken_agg['median']}")
    print("  " + "-" * 88)
    print("  FOR CONTEXT:")
    print(f"    signed-off 27 baseline known-R avg : ~+0.33R  ({_agg(signed)['mean']} mean / "
          f"{_agg(signed)['median']} median here)")
    print(f"    new-gold (backfill) clean          : mean={_agg(newgold_clean)['mean']} "
          f"median={_agg(newgold_clean)['median']} (n={_agg(newgold_clean)['n']})")
    print("  " + "-" * 88)
    # outcome distribution on the CLEAN set
    from collections import Counter
    cat = Counter(s["outcome_category"] or "?" for s in clean)
    binr = Counter(s["binary_rollup"] or "?" for s in clean)
    print("  OUTCOME DISTRIBUTION — CLEAN set:")
    for k, v in cat.most_common():
        print(f"    {k:30} {v}")
    print(f"    roll-up: " + "  ".join(f"{k}={v}" for k, v in binr.most_common()))
    print("  " + "-" * 88)
    # broken list
    broken_known = [s for s in broken if s["r_is_known"] and BA._f(s["calculated_r"]) is not None]
    print(f"  BROKEN-PARSE ROWS ({len(broken)}; only {len(broken_known)} have a known R — the rest")
    print(f"  are incomplete/unscored so they never touched the aggregate). id/date, garbled, R:")
    def absr(s):
        return abs(BA._f(s["calculated_r"])) if (s["r_is_known"] and BA._f(s["calculated_r"]) is not None) else 0
    for s in sorted(broken, key=absr, reverse=True):
        rid = s["signal_id"][:8]
        rstr = s["calculated_r"] if s["r_is_known"] else "(unknown)"
        print(f"    {rid} {str(s['sent_at_utc'])[:16]} {s['direction']:5} entry={s['entry_low']}-{s['entry_high']:<8} "
              f"sl={str(s['stop']):>7} tp={s['tp1']}/{s['tp2']}/{s['tp3']:<6} R={str(rstr):>9} | "
              f"{'; '.join(s['_reasons'])}")
    print("=" * 92)
    print(f"  HONEST CLEANED GOLD NUMBER: mean {clean_agg['mean']}R / median {clean_agg['median']}R "
          f"over n={clean_agg['n']} known-R clean signals (of {len(clean)} clean / {len(gold)} gold).")
    print("  No scoring changed; signed-off 28 + LIVE stub untouched.")
    print("=" * 92)

    # ---- ROBUST SUMMARY: contributors, by-month, trades remaining ----
    clean_known = [s for s in clean if s["r_is_known"] and BA._f(s["calculated_r"]) is not None]
    contributors_report(clean_known)
    months = by_month_report(clean_known)

    # ---- mini capture-recall (anti-flattery) ----
    cr = mini_capture_recall(conn)

    # ---- light spot-check: higher-risk CLEAN rows with evidence ----
    spot_check(conn, clean)

    # ---- PASS / FAIL against ALL criteria ----
    pass_criteria(clean_agg, all_agg, clean_known, months, cr)
    conn.close()


def contributors_report(clean_known):
    rows = sorted(clean_known, key=lambda s: BA._f(s["calculated_r"]), reverse=True)
    total = sum(BA._f(s["calculated_r"]) for s in rows)
    pos_total = sum(BA._f(s["calculated_r"]) for s in rows if BA._f(s["calculated_r"]) > 0)
    print("\n  " + "-" * 88)
    print(f"  CONTRIBUTORS (clean known-R; total R sum = {total:.2f} over n={len(rows)}):")
    top = rows[:5]
    print(f"    TOP 5 (largest +R) — combined {sum(BA._f(s['calculated_r']) for s in top):.2f}R "
          f"= {100*sum(BA._f(s['calculated_r']) for s in top)/pos_total:.0f}% of all positive R:")
    for s in top:
        print(f"      {str(s['sent_at_utc'])[:16]} {s['direction']:5} R={s['calculated_r']:>6} "
              f"{s['outcome_category']}  ({s['source']})")
    print("    WORST 5 (largest -R):")
    for s in rows[-5:][::-1]:
        print(f"      {str(s['sent_at_utc'])[:16]} {s['direction']:5} R={s['calculated_r']:>6} "
              f"{s['outcome_category']}  ({s['source']})")


def by_month_report(clean_known):
    from collections import defaultdict
    import statistics as st
    by = defaultdict(list)
    for s in clean_known:
        by[str(s["sent_at_utc"])[:7]].append(BA._f(s["calculated_r"]))
    print("\n  " + "-" * 88)
    print("  RESULT BY MONTH (clean known-R) — is it positive across months, or one spell?")
    months = {}
    for m in sorted(by):
        rs = by[m]
        months[m] = {"n": len(rs), "mean": round(st.mean(rs), 3), "sum": round(sum(rs), 2)}
        print(f"    {m}: n={len(rs):2d}  mean={st.mean(rs):+.3f}R  sum={sum(rs):+.2f}R")
    pos_months = sum(1 for m in months.values() if m["mean"] > 0)
    print(f"    -> positive in {pos_months} of {len(months)} months")
    return months


def mini_capture_recall(conn, n_days=6):
    """Blind random days across different months; dump raw + an AUTOMATED gold-call vs
    DB heuristic to surface potential missed/false signals. Files -> data/audit/cr_mini/."""
    import os
    import random
    import re
    from collections import defaultdict
    msgs = conn.execute("""
        SELECT r.message_id, r.sent_at_utc, r.raw_text FROM raw_message_versions r
        JOIN (SELECT message_key, MAX(version_number) v FROM raw_message_versions GROUP BY message_key) m
          ON r.message_key=m.message_key AND r.version_number=m.v
        WHERE r.sent_at_utc >= '2025-06-13'""").fetchall()
    by_day = defaultdict(list)
    by_month = defaultdict(set)
    for m in msgs:
        day = (m["sent_at_utc"] or "")[:10]
        by_day[day].append(m)
        by_month[day[:7]].add(day)
    # one blind random day per distinct month (up to n_days), seeded
    rng = random.Random(BA.MASTER_SEED + 7)
    chosen = []
    for mo in sorted(by_month):
        days = sorted(by_month[mo])
        chosen.append(rng.choice(days))
    chosen = sorted(rng.sample(chosen, min(n_days, len(chosen))))

    gold_by_day = defaultdict(int)
    for r in conn.execute("SELECT sent_at_utc FROM signals WHERE asset='XAUUSD'").fetchall():
        gold_by_day[(r["sent_at_utc"] or "")[:10]] += 1

    # heuristic: a raw message that looks like a gold CALL (xau/gold + side + price>=800)
    call_re = re.compile(r"(xau|gold)", re.I)
    side_re = re.compile(r"\b(buy|sell|long|short)\b", re.I)
    price_re = re.compile(r"\b([1-9]\d{3}(?:\.\d+)?)\b")
    recap_re = BA._RECAP_RE

    cr_dir = os.path.join(BA.AUDIT_DIR, "cr_mini")
    os.makedirs(cr_dir, exist_ok=True)
    summary = []
    for day in chosen:
        day_msgs = by_day[day]
        looks_calls = 0
        recaps = 0
        for m in day_msgs:
            t = m["raw_text"] or ""
            if call_re.search(t) and side_re.search(t) and price_re.search(t):
                looks_calls += 1
            if recap_re.search(t):
                recaps += 1
        db_sig = gold_by_day.get(day, 0)
        summary.append({"day": day, "messages": len(day_msgs), "looks_like_gold_calls": looks_calls,
                        "db_gold_signals": db_sig, "recaps": recaps})
        with open(os.path.join(cr_dir, f"{day}.txt"), "w", encoding="utf-8") as f:
            f.write(f"ALL raw messages for {day}  ({len(day_msgs)} msgs)  "
                    f"db_gold_signals={db_sig}  gold-call-looking={looks_calls}  recaps={recaps}\n")
            f.write("=" * 70 + "\n")
            for m in day_msgs:
                f.write(f"[{m['sent_at_utc']}] (id {m['message_id']})\n{m['raw_text']}\n" + "-"*40 + "\n")

    print("\n  " + "-" * 88)
    print(f"  MINI CAPTURE-RECALL (anti-flattery) — {len(chosen)} BLIND days across months "
          f"(seed {BA.MASTER_SEED + 7}); raw dumps -> {cr_dir}/")
    print("    day         msgs  gold-call-looking  db_gold_signals  recaps   note")
    discrepancies = 0
    for r in summary:
        note = ""
        if r["looks_like_gold_calls"] > r["db_gold_signals"]:
            note = "potential MISSED call(s)"; discrepancies += 1
        elif r["db_gold_signals"] > r["looks_like_gold_calls"] and r["db_gold_signals"] > 0:
            note = "DB>raw-heuristic (recap-derived? re-entry?)"
        print(f"    {r['day']}  {r['messages']:5d}  {r['looks_like_gold_calls']:16d}  "
              f"{r['db_gold_signals']:14d}  {r['recaps']:6d}   {note}")
    print(f"    (heuristic only — dumps are for HAND comparison; {discrepancies} day(s) flagged to eyeball)")
    return {"days": summary, "discrepancies": discrepancies}


def pass_criteria(clean_agg, all_agg, clean_known, months, cr):
    pos_months = sum(1 for m in months.values() if m["mean"] > 0)
    total_months = len(months)
    mean = clean_agg["mean"] or 0
    median = clean_agg["median"] or 0
    # largest single contributor share of positive R (no single absurd outlier)
    pos = [BA._f(s["calculated_r"]) for s in clean_known if BA._f(s["calculated_r"]) > 0]
    pos_total = sum(pos) if pos else 0
    top_share = (max(pos) / pos_total) if pos_total else 1.0

    checks = []
    checks.append(("cleaned mean >= ~+0.2R", mean >= 0.2, f"mean={mean}R"))
    checks.append(("no single absurd outlier driving it", top_share < 0.25 and (all_agg["mean"] or 0) - mean > 0,
                   f"top winner = {top_share*100:.0f}% of positive R; raw mean {all_agg['mean']} -> cleaned {mean}"))
    checks.append(("positive across >1 month", pos_months >= 2,
                   f"positive in {pos_months}/{total_months} months"))
    checks.append(("median not wildly inconsistent with mean", abs(mean - median) <= 0.2,
                   f"mean={mean} vs median={median}"))
    checks.append(("no systematically missed losses (capture sample)", cr["discrepancies"] == 0,
                   f"{cr['discrepancies']} capture day(s) flagged for missed calls — eyeball dumps"))
    checks.append(("enough trades remaining after cleaning", clean_agg["n"] >= 30,
                   f"n={clean_agg['n']} clean known-R"))

    print("\n" + "=" * 92)
    print("  PASS / FAIL  (zero-risk demo decision — judged on ALL criteria, not just the mean)")
    print("=" * 92)
    for name, ok, detail in checks:
        print(f"    [{'PASS' if ok else 'CHECK'}] {name}")
        print(f"           {detail}")
    overall = all(ok for _, ok, _ in checks)
    hard = all(ok for (name, ok, _) in checks if "missed losses" not in name)  # capture is human-confirmed
    print("  " + "-" * 88)
    verdict = ("PASS" if overall else
               ("PASS (pending human capture-recall eyeball)" if hard else "FAIL"))
    print(f"  VERDICT: {verdict}")
    print("    A modest, stable, broadly-distributed mean = PASS; a high mean driven by a few")
    print("    inflated winners = FAIL. The capture-recall dumps need a human eyeball to confirm")
    print("    no losses were systematically missed before calling it a final PASS.")
    print("=" * 92)


def spot_check(conn, clean):
    def rv(s):
        return BA._f(s["calculated_r"]) if (s["r_is_known"] and BA._f(s["calculated_r"]) is not None) else None
    losses = [s for s in clean if (s["binary_rollup"] == "loss")
              or (rv(s) is not None and rv(s) < 0)]
    winners = sorted([s for s in clean if rv(s) is not None and rv(s) > 0],
                     key=lambda s: rv(s), reverse=True)
    # re-entries: detect via the frozen audit flag set (time cluster / wording)
    gold_epochs = [BA._epoch(s["sent_at_utc"]) for s in clean]
    reentries = []
    for s in clean:
        flags, _ = BA.flag_signal(s, conn, gold_epochs)
        if any(f.startswith("REENTRY") for f in flags):
            reentries.append(s)

    print("\n" + "=" * 92)
    print("  LIGHT SPOT-CHECK (sanity only, not exhaustive) — clean rows + evidence")
    print("=" * 92)
    def dump(title, rows):
        print(f"\n  -- {title} ({len(rows)} shown) --")
        for s in rows:
            ev = BA._text_for(conn, s["primary_evidence_message_key"])[:130].replace("\n", " ")
            rstr = s["calculated_r"] if s["r_is_known"] else "(unknown)"
            print(f"    {str(s['sent_at_utc'])[:16]} {s['direction']:5} {s['entry_low']}-{s['entry_high']} "
                  f"sl={s['stop']} tp={s['tp1']}/{s['tp2']}/{s['tp3']} | {s['outcome_category']} "
                  f"R={rstr}")
            print(f"        evidence: {ev}")
    dump("LOSSES", losses[:6])
    dump("BIG WINNERS (top R)", winners[:6])
    dump("RE-ENTRIES", reentries[:6])
    print("=" * 92)


if __name__ == "__main__":
    main()
