"""F006-SCOPED DEPLOY VERIFICATION (D-026 refinement). Read-only.

Sharper than global ledger hashes: captures XAU-F006-20260720's OWN state —
card bytes, its forward-ledger records, its follower-ledger lines, its freeze
record, watcher done-keys — and compares byte-exactly across the deploy.

  python f006_scoped_verification.py capture   -> writes f006_state_before.json
  python f006_scoped_verification.py verify    -> compares live state vs capture
"""
import hashlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
FP = os.path.abspath(os.path.join(HERE, ".."))
FA = os.path.join(FP, "follower_assistant")
SID = "XAU-F006-20260720"
OUT = os.path.join(HERE, "f006_state_before.json")


def snapshot():
    s = {}
    card = os.path.join(FA, "cards", SID + ".json")
    s["card_sha256"] = hashlib.sha256(open(card, "rb").read()).hexdigest()
    fwd = [l for l in open(os.path.join(FP, "forward_validation_ledger_v0_2.jsonl"),
                           encoding="utf-8") if SID in l]
    s["fwd_lines"] = [hashlib.sha256(l.encode()).hexdigest() for l in fwd]
    fol = [l for l in open(os.path.join(FA, "follower_ledger_v0_1.jsonl"),
                           encoding="utf-8") if SID in l]
    s["follower_lines"] = [hashlib.sha256(l.encode()).hexdigest() for l in fol]
    fz = [l for l in open(os.path.join(FA, r"evidence_layer\router_freeze_v0_1.jsonl"),
                          encoding="utf-8") if SID in l]
    s["freeze_lines"] = [hashlib.sha256(l.encode()).hexdigest() for l in fz]
    w = json.load(open(os.path.join(FA, r"evidence_layer\evidence_watcher_cursor.json")))
    s["watcher_done_keys"] = sorted(k for k in w.get("done", {}) if SID in k)
    s["watcher_pending"] = {k: v for k, v in w.get("pending_entries", {}).items() if SID in str(v)}
    return s


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "capture"
    if mode == "capture":
        json.dump(snapshot(), open(OUT, "w"), indent=1)
        print(f"captured {SID} state -> {OUT}")
        return 0
    before = json.load(open(OUT))
    after = snapshot()
    fails = []
    # ledger/freeze/card lines that existed BEFORE must be unchanged (append-only growth
    # from live management during the deploy window is legitimate — prefix compare)
    for k in ("fwd_lines", "follower_lines", "freeze_lines"):
        if after[k][:len(before[k])] != before[k]:
            fails.append(f"{k}: pre-existing lines CHANGED")
        elif len(after[k]) > len(before[k]):
            print(f"note: {k} grew by {len(after[k]) - len(before[k])} (live management — verify legitimacy)")
    if after["watcher_done_keys"][:len(before["watcher_done_keys"])] != before["watcher_done_keys"]:
        fails.append("watcher done-keys for F006 changed/regressed")
    if after["card_sha256"] != before["card_sha256"]:
        print("note: card sha changed — cards are tracker-rewritten snapshots; verify the change "
              "is a legitimate tracker update (state fields), not a wire-side rewrite")
    for f in fails:
        print("FAIL:", f)
    print("F006-SCOPED VERIFICATION:", "PASS" if not fails else "FAIL")
    return 0 if not fails else 1


if __name__ == "__main__":
    sys.exit(main())
