"""MORPHOLOGY_EXTENSION_v2 re-proof (D-020 + Addition 2). Read-only.

1. F001-F006 BYTE-IDENTITY: classify()+type_instructions() of every real campaign
   message must be byte-identical v1 vs v2.
2. FULL DIFF over all archive+prospective rows: transition matrix; HALT on any
   ENTRY->non-ENTRY; MANAGEMENT->ENTRY listed for review.
3. 240-SIGNAL RECONCILIATION: every old-extractor Farouk XAU signal that does NOT
   classify as ENTRY under v2 is individually named with reason.
"""
import json
import os
import sqlite3
import sys
from collections import Counter

FA = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "follower_assistant"))
sys.path.insert(0, FA)
import interpreter as V1        # noqa: E402
import interpreter_v2 as V2     # noqa: E402

ST = r"C:\Users\Marty\signal-terminal"
CAMPAIGN_MSGS = [45711, 45714, 45715, 45717, 45718, 45719, 45720, 45723, 45724,   # F001
                 45727, 45728, 45729, 45731, 45742,                               # F002
                 45791, 45792, 45800, 45805,                                      # F003
                 45807, 45808, 45810, 45813, 45816,                               # F004
                 45878, 45879, 45880, 45881, 45885,                               # F005
                 45935]                                                           # F006 (rev msgs may grow)


def canon(mod, raw):
    c = mod.classify(raw)
    t = mod.type_instructions(raw) if raw else []
    return json.dumps({"c": c, "t": t}, sort_keys=True, ensure_ascii=False)


def main():
    pdb = sqlite3.connect(os.path.join(ST, r"campaign_extractor\prospective\data\prospective_evidence_v1.db"))
    fails = []
    checked = 0
    for mid in CAMPAIGN_MSGS:
        row = pdb.execute("select raw_text from prospective_message_evidence where telegram_message_id=? "
                          "order by message_revision_number desc limit 1", (str(mid),)).fetchone()
        if not row or row[0] is None:
            continue
        checked += 1
        if canon(V1, row[0]) != canon(V2, row[0]):
            fails.append(mid)
    print(f"1) F001-F006 byte-identity: {checked} messages checked, {len(fails)} diffs "
          f"{'FAIL ' + str(fails) if fails else '-> PASS'}")

    def disp(mod, raw):
        if raw is None or not str(raw).strip():
            return "EMPTY"
        return mod.classify(raw)["kind"]

    adb = sqlite3.connect(os.path.join(ST, r"data\signal_archive.db"))
    rows = adb.execute("select row_id, raw_text from raw_message_versions").fetchall()
    rows += [("p" + str(r[0]), r[1]) for r in pdb.execute(
        "select evidence_id, raw_text from prospective_message_evidence").fetchall()]
    trans = Counter()
    entry_degrade = []
    mgmt_to_entry = []
    for rid, raw in rows:
        a, b = disp(V1, raw), disp(V2, raw)
        trans[(a, b)] += 1
        if a == "ENTRY" and b != "ENTRY":
            entry_degrade.append((rid, b, (raw or "")[:90]))
        if a == "MANAGEMENT" and b == "ENTRY":
            mgmt_to_entry.append((rid, (raw or "").splitlines()[2] if len((raw or "").splitlines()) > 2 else (raw or "")[:90]))
    print(f"\n2) full diff over {len(rows)} rows; transitions (changed only):")
    for (a, b), n in sorted(trans.items(), key=lambda x: -x[1]):
        if a != b:
            print(f"   {a:>18} -> {b:<18} {n}")
    print(f"   ENTRY->non-ENTRY (HALT if any): {len(entry_degrade)}")
    for e in entry_degrade:
        print("   HALT:", e)
    print(f"   MANAGEMENT->ENTRY (review): {len(mgmt_to_entry)}")
    for m in mgmt_to_entry[:15]:
        print("     M->E:", m)

    sigs = adb.execute("""select s.signal_id, m.sent_at_utc, m.raw_text from signals s
                          join raw_message_versions m on m.message_key = s.source_message_key
                          where s.provider='seascalperfarouk' and s.asset='XAUUSD'""").fetchall()
    not_entry = []
    got = 0
    for sid, ts, raw in sigs:
        c = V2.classify(raw)
        if c["kind"] == "ENTRY":
            got += 1
        else:
            body = " ".join((raw or "").splitlines()[2:4])[:80]
            not_entry.append((sid, (ts or "")[:10], c["kind"], c.get("why", ""), body))
    print(f"\n3) 240-signal reconciliation: {got}/{len(sigs)} classify as ENTRY under v2")
    print(f"   individually named non-ENTRY ({len(not_entry)}):")
    for r in not_entry:
        print("   ", r)
    with open(os.path.join(os.path.dirname(__file__), "v2_reproof_results.json"), "w", encoding="utf-8") as f:
        json.dump({"byte_identity_fails": fails, "transitions": {f"{a}->{b}": n for (a, b), n in trans.items()},
                   "entry_degrade": entry_degrade, "mgmt_to_entry": mgmt_to_entry,
                   "signals_entry": got, "signals_total": len(sigs),
                   "signals_not_entry": not_entry}, f, indent=1, ensure_ascii=False)
    return 1 if (fails or entry_degrade) else 0


if __name__ == "__main__":
    sys.exit(main())
