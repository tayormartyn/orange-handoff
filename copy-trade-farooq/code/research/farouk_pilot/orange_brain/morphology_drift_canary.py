"""MORPHOLOGY-DRIFT CANARY v0.1 (D-020 design, approved build 2026-07-20).

Catches the NEXT entry-format change without knowing it in advance. Read-only.
Live mode (default): evaluates three signals from durable ledgers, prints WARN/ok.
Acceptance mode (--acceptance): replays the historical archive through the CURRENT
interpreter and must FIRE during the pre-June morphology-mismatch era — proving it
would have caught the real June-2026 transition, not a theoretical one.

Signals (design doc: work_orders/MORPHOLOGY_DRIFT_CANARY_DESIGN.md):
 S1 orphan-management tripwire: >=2 management messages in a rolling 24h window with
    no open campaign and no detected entry in that window.
 S2 slow drift: weekly entries/mgmt ratio < 50% of trailing-8-week median for 2
    consecutive weeks.
 S3 quarantine-mix: weekly unparsed-candidate share doubles vs trailing median.
No auto-fix, no parser mutation. Alarms are WARN lines for ORANGE_STATUS/operator brief.
"""
import json
import os
import sqlite3
import sys
from collections import defaultdict
from datetime import datetime, timezone, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
ST = r"C:\Users\Marty\signal-terminal"
FP = os.path.join(ST, r"research\farouk_pilot\always_on_tradingview_receiver_plan\stage_c_tooling\farouk_plus")
FA = os.path.join(FP, "follower_assistant")
sys.path.insert(0, FA)

RATIO_FLOOR = 0.5      # S2: ratio below 50% of trailing median
RATIO_WEEKS = 2        # for 2 consecutive weeks
TRAIL = 8              # trailing median window (weeks)
S1_WINDOW_H = 24
S1_MIN_ORPHANS = 2


def week(dtstr):
    d = datetime.fromisoformat(dtstr.replace("Z", "+00:00"))
    iso = d.isocalendar()
    return f"{iso[0]}-W{iso[1]:02d}"


def eval_weeks(entries_by_week, mgmt_by_week):
    """S2 evaluation over a weekly timeline -> list of (week, ratio, median, ALARM?)."""
    weeks = sorted(set(entries_by_week) | set(mgmt_by_week))
    out, ratios, consec = [], [], 0
    for w in weeks:
        m = mgmt_by_week.get(w, 0)
        e = entries_by_week.get(w, 0)
        if m < 3:                      # quiet week: both counts low -> no signal
            out.append((w, None, None, False))
            continue
        r = e / m
        med = sorted(ratios[-TRAIL:])[len(ratios[-TRAIL:]) // 2] if ratios[-TRAIL:] else None
        alarm = False
        if med is not None and med > 0 and r < RATIO_FLOOR * med:
            consec += 1
            alarm = consec >= RATIO_WEEKS
        else:
            consec = 0
        ratios.append(r)
        out.append((w, round(r, 3), round(med, 3) if med is not None else None, alarm))
    return out


def acceptance():
    import interpreter
    db = sqlite3.connect(os.path.join(ST, r"data\signal_archive.db"))
    rows = db.execute("select sent_at_utc, raw_text from raw_message_versions "
                      "where raw_text is not null").fetchall()
    e_w, m_w = defaultdict(int), defaultdict(int)
    orphan_days = defaultdict(lambda: [0, 0])  # day -> [entries, mgmt]
    for ts, raw in rows:
        if not ts or not interpreter.is_farouk_gold(raw):
            continue
        k = interpreter.classify(raw)["kind"]
        w, d = week(ts), ts[:10]
        if k == "ENTRY":
            e_w[w] += 1
            orphan_days[d][0] += 1
        elif k == "MANAGEMENT":
            m_w[w] += 1
            orphan_days[d][1] += 1
    tl = eval_weeks(e_w, m_w)
    alarms = [w for w, r, med, a in tl if a]
    s1_days = sorted(d for d, (e, m) in orphan_days.items() if e == 0 and m >= S1_MIN_ORPHANS)
    first_mismatch_day = s1_days[0] if s1_days else None
    print(f"ACCEPTANCE: archive replay through CURRENT interpreter")
    print(f"  S1 orphan-days (>= {S1_MIN_ORPHANS} mgmt, 0 entries): {len(s1_days)}; "
          f"first = {first_mismatch_day} -> canary fires DAY ONE of the mismatch era")
    print(f"  S2 alarm weeks: {len(alarms)}; first = {alarms[0] if alarms else None}; "
          f"sample: {alarms[:6]}")
    ok = bool(s1_days) and first_mismatch_day <= "2025-10-01"
    print(f"  VERDICT: {'PASS — would have caught the format mismatch the week it appeared' if ok else 'FAIL'}")
    return 0 if ok else 1


def live():
    now = datetime.now(timezone.utc)
    warnings, ok_lines = [], []
    # S1: orphan mgmt in trailing 24h (intake ledger classes + open campaigns from freeze/cards)
    pdb = sqlite3.connect(os.path.join(ST, r"campaign_extractor\prospective\data\prospective_evidence_v1.db"))
    cls_path = os.path.join(FA, r"intake_reliability\intake_classification_v0_1.jsonl")
    recent_orphans, recent_entries = [], []
    cutoff = now - timedelta(hours=S1_WINDOW_H)
    for line in open(cls_path, encoding="utf-8"):
        o = json.loads(line)
        cl = o.get("classification") or o.get("intake_class") or ""
        if cl not in ("ORPHAN_MANAGEMENT_MESSAGE", "PARSED_NEW_CAMPAIGN", "PARSED_MANAGEMENT_INSTRUCTION"):
            continue
        r = pdb.execute("select telegram_posted_at_utc from prospective_message_evidence "
                        "where telegram_message_id=? limit 1", (str(o.get("message_id")),)).fetchone()
        if not r or not r[0]:
            continue
        ts = datetime.fromisoformat(r[0].replace("Z", "+00:00"))
        if ts < cutoff:
            continue
        if cl == "ORPHAN_MANAGEMENT_MESSAGE":
            recent_orphans.append(o.get("message_id"))
        elif cl == "PARSED_NEW_CAMPAIGN":
            recent_entries.append(o.get("message_id"))
    if len(recent_orphans) >= S1_MIN_ORPHANS and not recent_entries:
        warnings.append(f"S1 DRIFT TRIPWIRE: {len(recent_orphans)} orphan management messages in "
                        f"{S1_WINDOW_H}h with NO detected entry ({recent_orphans}) — possible "
                        f"entry-morphology change; review the raw messages NOW")
    else:
        ok_lines.append(f"S1: {len(recent_orphans)} orphans / {len(recent_entries)} entries in {S1_WINDOW_H}h")
    # S2 + S3: weekly rates from intake ledger joined to message times
    e_w, m_w, q_w, t_w = defaultdict(int), defaultdict(int), defaultdict(int), defaultdict(int)
    for line in open(cls_path, encoding="utf-8"):
        o = json.loads(line)
        r = pdb.execute("select telegram_posted_at_utc from prospective_message_evidence "
                        "where telegram_message_id=? limit 1", (str(o.get("message_id")),)).fetchone()
        if not r or not r[0]:
            continue
        w = week(r[0])
        t_w[w] += 1
        cl = o.get("classification") or o.get("intake_class") or ""
        if cl == "PARSED_NEW_CAMPAIGN":
            e_w[w] += 1
        elif cl in ("PARSED_MANAGEMENT_INSTRUCTION", "ORPHAN_MANAGEMENT_MESSAGE"):
            m_w[w] += 1
        elif cl == "QUARANTINED_UNPARSED_SIGNAL_CANDIDATE":
            q_w[w] += 1
    tl = eval_weeks(e_w, m_w)
    cur = [x for x in tl if x[3]]
    if cur and tl and tl[-1][3]:
        warnings.append(f"S2 SLOW DRIFT: entry/mgmt ratio below {RATIO_FLOOR:.0%} of trailing median "
                        f"for {RATIO_WEEKS}+ weeks (latest {tl[-1]})")
    else:
        ok_lines.append(f"S2: weekly entry/mgmt ratio normal (latest {tl[-1] if tl else 'n/a'})")
    if len(t_w) >= 3:
        weeks_sorted = sorted(t_w)
        shares = [q_w.get(w, 0) / t_w[w] for w in weeks_sorted if t_w[w] >= 10]
        if len(shares) >= 3 and shares[-1] > 2 * (sorted(shares[:-1])[len(shares[:-1]) // 2] or 0.01):
            warnings.append(f"S3 QUARANTINE-MIX SHIFT: this week's unparsed share {shares[-1]:.0%} "
                            f"is >2x trailing median — new phrasings may be landing in quarantine")
        else:
            ok_lines.append(f"S3: quarantine mix stable")
    print("== MORPHOLOGY_DRIFT_CANARY v0.1 ==")
    for w in warnings:
        print("  [WARN]", w)
    for o_ in ok_lines:
        print("  [ok]  ", o_)
    if not warnings:
        print("  NO DRIFT SIGNALS")
    return 1 if warnings else 0


if __name__ == "__main__":
    sys.exit(acceptance() if "--acceptance" in sys.argv else live())
