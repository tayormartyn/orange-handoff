"""OQ-8 quarantine review tool (D-037 item D). Operator workflow + durable resolutions.

Usage:
  python quarantine_review.py --list            # write review queue md + print ids/counts
  python quarantine_review.py --resolve 45916 CORRECTLY_QUARANTINED --note "pure commentary"
  python quarantine_review.py --resolve 45922 ACTIONABLE_MISSED --note "leg-selective variant X"
  python quarantine_review.py --status          # counts only

Durable format: quarantine_resolutions_v0_1.jsonl (append-only, one JSON per line):
  {message_id, verdict, note, raw_text_hash, resolved_at_utc, resolver}
- verdict enum: CORRECTLY_QUARANTINED | ACTIONABLE_MISSED | COMMENTARY | DUPLICATE | DEFER
- ACTIONABLE_MISSED REQUIRES a note naming the morphology/coverage gap (it feeds the
  parser work queue; a nameless miss is not a resolution).
- raw_text_hash binds the resolution to the exact quarantined content: if the same
  message id is ever re-quarantined with different text, it re-enters the queue.
- DEFER keeps the message in the pending queue (recorded, not subtracted).
- Resolutions never mutate the quarantine ledger, campaigns, or any evidence store.

RAW-TEXT CONTAINMENT: message content goes ONLY into the local review-queue file for the
operator (quarantine_review_queue.md, gitignored dir); terminal output is ids/counts.
brain_refresh subtracts resolved (non-DEFER) ids from the actionable pending count.
"""
import argparse
import json
import os
import sys
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
ST = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
FA = os.path.join(ST, r"research\farouk_pilot\always_on_tradingview_receiver_plan"
                      r"\stage_c_tooling\farouk_plus\follower_assistant")
QUAR = os.path.join(FA, r"intake_reliability\intake_quarantine_v0_1.jsonl")
FWD = os.path.join(os.path.dirname(FA), "forward_validation_ledger_v0_2.jsonl")
RESOLUTIONS = os.path.join(HERE, "quarantine_resolutions_v0_1.jsonl")
QUEUE_MD = os.path.join(HERE, "quarantine_review_queue.md")
MODERN_ERA_FLOOR = 45784      # same rule as brain_refresh actionable computation

VERDICTS = ("CORRECTLY_QUARANTINED", "ACTIONABLE_MISSED", "COMMENTARY", "DUPLICATE", "DEFER")


def load_resolutions(path=RESOLUTIONS):
    out = {}
    if os.path.exists(path):
        for l in open(path, encoding="utf-8"):
            if l.strip():
                r = json.loads(l)
                out[int(r["message_id"])] = r      # last resolution wins (append-only file)
    return out


def pending_actionable(quar_path=QUAR, fwd_path=FWD, res_path=RESOLUTIONS):
    fwd_ids = set()
    for l in open(fwd_path, encoding="utf-8"):
        if not l.strip():
            continue
        o = json.loads(l)
        for m in (o.get("message_ids") or []):
            fwd_ids.add(int(m))
        if o.get("message_id"):
            fwd_ids.add(int(o["message_id"]))
    res = load_resolutions(res_path)
    rows = {}
    for l in open(quar_path, encoding="utf-8"):
        if not l.strip():
            continue
        o = json.loads(l)
        mid = int(o.get("message_id"))
        if o.get("resolution_status") != "PENDING_OPERATOR_REVIEW":
            continue
        if mid < MODERN_ERA_FLOOR or mid in fwd_ids:
            continue
        r = res.get(mid)
        if r and r["verdict"] != "DEFER" and r.get("raw_text_hash") == o.get("raw_text_hash"):
            continue                               # durably resolved for THIS content
        rows[mid] = o                              # latest quarantine row per id
    return [rows[m] for m in sorted(rows)], res


def cmd_list():
    rows, res = pending_actionable()
    lines = ["# QUARANTINE REVIEW QUEUE (generated — resolve with quarantine_review.py)",
             f"Generated {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')} · "
             f"{len(rows)} pending actionable · {len(res)} resolutions on file",
             "", "Verdicts: CORRECTLY_QUARANTINED | ACTIONABLE_MISSED (note required) | "
                 "COMMENTARY | DUPLICATE | DEFER", ""]
    for o in rows:
        lines += [f"## msg {o['message_id']}  ({o.get('source_timestamp', '?')})",
                  f"- reason: {o.get('failed_parser_reason', '?')} · probable: {o.get('probable', '?')}",
                  f"- hash: {o.get('raw_text_hash', '?')[:16]}",
                  "```", str(o.get("raw_text_bounded", "")).strip(), "```", ""]
    with open(QUEUE_MD, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"pending actionable: {len(rows)} -> ids {[o['message_id'] for o in rows]}")
    print(f"queue written for review: {QUEUE_MD}")


def cmd_resolve(mid, verdict, note):
    if verdict not in VERDICTS:
        sys.exit(f"verdict must be one of {VERDICTS}")
    if verdict == "ACTIONABLE_MISSED" and not note:
        sys.exit("ACTIONABLE_MISSED requires --note naming the coverage gap")
    rows, _ = pending_actionable()
    match = [o for o in rows if int(o["message_id"]) == int(mid)]
    if not match:
        sys.exit(f"msg {mid} is not in the pending actionable queue (already resolved, "
                 "not actionable, or unknown) — nothing recorded")
    rec = {"message_id": int(mid), "verdict": verdict, "note": note or "",
           "raw_text_hash": match[0].get("raw_text_hash"),
           "resolved_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
           "resolver": "MARTYN"}
    with open(RESOLUTIONS, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec) + "\n")
    left = len(pending_actionable()[0])
    print(f"resolved msg {mid} as {verdict}; pending actionable now {left}")


def cmd_status():
    rows, res = pending_actionable()
    by = {}
    for r in res.values():
        by[r["verdict"]] = by.get(r["verdict"], 0) + 1
    print(f"pending actionable: {len(rows)} | resolutions on file: {len(res)} {by}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--resolve", nargs=2, metavar=("MSG_ID", "VERDICT"))
    ap.add_argument("--note", default="")
    ap.add_argument("--status", action="store_true")
    a = ap.parse_args()
    if a.list:
        cmd_list()
    elif a.resolve:
        cmd_resolve(a.resolve[0], a.resolve[1], a.note)
    else:
        cmd_status()
