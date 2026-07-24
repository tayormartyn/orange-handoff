"""RESTART-SAFETY PROOF (D-026 option b, operator-approved with two required cases).

Sandbox-only. Proves, with the v2 files ACTIVE and every cycle a COLD-START
subprocess (true restart path: fresh import -> load_cursor -> load_campaign_state
ledger rebuild -> new_messages):

 CASE 1: restart with a campaign in runner-equivalent state (OPEN, multi-revision,
         partials taken, runner held) — beyond the entry-era precedent.
 CASE 2: management arriving (a) just before shutdown, (b) during the down window,
         (c) immediately after startup — each picked up EXACTLY ONCE, correlated
         to the open campaign, no loss, no duplicate.

Nothing live is read or written: private sandbox tree + private evidence DB.
"""
import hashlib
import json
import os
import shutil
import sqlite3
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
FP = os.path.abspath(os.path.join(HERE, ".."))
ST = r"C:\Users\Marty\signal-terminal"
SAND = r"C:\Users\Marty\rs_sb"          # short path (MAX_PATH); removed at end
SFA = os.path.join(SAND, "f")

H = "seascalperfarouk Posted in 🪙・gold-trades\n\n"


def msg_row(mid, text, ts):
    return (str(-1001902136163), str(mid), ts, ts, text, None, "RESTART_PROOF_SANDBOX",
            "CREATED", 1, ts, None, None, None, 0, None,
            hashlib.sha256(text.encode()).hexdigest())


def build_sandbox():
    if os.path.exists(SAND):
        shutil.rmtree(SAND)
    os.makedirs(os.path.join(SAND, "campaign_extractor", "prospective", "data"))
    shutil.copytree(os.path.join(FP, "follower_assistant"), SFA,
                    ignore=shutil.ignore_patterns("__pycache__", "logs", "cards"))
    os.makedirs(os.path.join(SFA, "cards"))
    # v2 ACTIVE (this is what the deploy will run)
    shutil.copy2(os.path.join(SFA, "interpreter_v2.py"), os.path.join(SFA, "interpreter.py"))
    shutil.copy2(os.path.join(SFA, "live_wire_v2.py"), os.path.join(SFA, "live_wire.py"))
    # start with EMPTY ledgers/cursor so the sandbox campaign is the only state
    open(os.path.join(SFA, "..", "forward_validation_ledger_v0_2.jsonl"), "w").close()
    for f in ("forward_validation_ledger_v0_2.jsonl",):
        pass
    open(os.path.join(SFA, "follower_ledger_v0_1.jsonl"), "w").close()
    cur = os.path.join(SFA, "live_wire_cursor.json")
    json.dump({"last_processed_id": 90000, "fail_counts": {}}, open(cur, "w"))
    # sandbox needs the parent ledger file path used by append_forward — create empty at ../
    shutil.copy2(os.path.join(FP, "pre_mark_candidates_v0_1.jsonl"),
                 os.path.join(SAND, "pre_mark_candidates_v0_1.jsonl"))
    for extra in ("knowledge", "tools"):
        src = os.path.join(FP, extra)
        if os.path.isdir(src):
            shutil.copytree(src, os.path.join(SAND, extra))
    for f in ("detector_v0_2_replay_results.json", "detector_v0_3_replay_results.json"):
        p = os.path.join(FP, f)
        if os.path.exists(p):
            shutil.copy2(p, os.path.join(SAND, f))
    shutil.copy2(os.path.join(ST, "config.py"), os.path.join(SAND, "config.py"))
    shutil.copy2(os.path.join(ST, "ctrader_config.py"), os.path.join(SAND, "ctrader_config.py"))
    # NOTE: sandbox dir layout puts follower_assistant at SAND/f, so the wire's relative
    # paths (HERE/..) resolve inside SAND. The evidence DB path is passed explicitly.
    db = sqlite3.connect(os.path.join(SAND, "evidence.db"))
    src = sqlite3.connect(os.path.join(ST, r"campaign_extractor\prospective\data\prospective_evidence_v1.db"))
    src_schema = src.execute("select sql from sqlite_master where name='prospective_message_evidence'").fetchone()[0]
    db.execute(src_schema)
    db.commit()
    return db


def insert(db, mid, text, ts):
    text = H + text
    h = hashlib.sha256(text.encode()).hexdigest()
    vals = {"evidence_id": f"RS-{mid}-1", "telegram_channel_id": str(-1001902136163),
            "telegram_message_id": str(mid), "telegram_posted_at_utc": ts,
            "listener_received_at_utc": ts, "raw_text": text, "raw_text_hash": h,
            "message_event_type": "CREATED", "message_revision_number": 1,
            "extractor_version": "RESTART_PROOF_SANDBOX", "evidence_hash": h,
            "listener_observed_at_utc": ts, "telegram_is_forwarded": 0}
    # fill any remaining NOT NULL columns with benign defaults
    for cid, name, ctype, notnull, dflt, pk in db.execute(
            "PRAGMA table_info(prospective_message_evidence)"):
        if notnull and dflt is None and not pk and name not in vals:
            vals[name] = 0 if "INT" in (ctype or "").upper() else ""
    cols = ",".join(vals)
    db.execute(f"insert into prospective_message_evidence ({cols}) values "
               f"({','.join('?' * len(vals))})", tuple(vals.values()))
    db.commit()


RUNNER = os.path.join(SFA, "_cycle_runner.py")
RUNNER_SRC = '''import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import live_wire
out = live_wire.run_cycle(db_path=sys.argv[1])
print(json.dumps(out if out is not None else {"note": "cycle done"}))
'''


def cold_cycle(dbp):
    """One COLD-START wire cycle in a fresh subprocess (true restart semantics)."""
    r = subprocess.run([sys.executable, RUNNER, dbp], capture_output=True, text=True,
                       timeout=300, cwd=SFA)
    if r.returncode != 0:
        print("CYCLE STDERR:", r.stderr[-500:])
        raise RuntimeError("cycle failed")
    return r.stdout


def ledger():
    p = os.path.join(SAND, "forward_validation_ledger_v0_2.jsonl")
    return [json.loads(l) for l in open(p, encoding="utf-8")] if os.path.exists(p) else []


def counts_by_msg():
    c = {}
    for r in ledger():
        ids = r.get("message_ids") or ([r["message_id"]] if r.get("message_id") else [])
        for m in ids:
            c[m] = c.get(m, 0) + 1
    return c


def main():
    db = build_sandbox()
    open(RUNNER, "w").write(RUNNER_SRC)
    dbp = os.path.join(SAND, "evidence.db")
    ok = []

    def ck(name, cond, detail=""):
        ok.append(cond)
        print(("PASS " if cond else "FAIL ") + name + ("" if cond else f"  <- {detail}"))

    # ---- build the runner-equivalent campaign across COLD cycles ----
    insert(db, 90001, "`Whale` XAUUSD BUY 4010-4000 SL 3992", "2026-07-21T08:00:00+00:00")
    cold_cycle(dbp)
    insert(db, 90002, "`Whale` tp 1 now", "2026-07-21T08:30:00+00:00")
    insert(db, 90003, "`Whale` take 50% off, sl to entry, let it run", "2026-07-21T09:00:00+00:00")
    cold_cycle(dbp)
    led = ledger()
    setups = [r for r in led if r.get("record_type") == "XAU_F_SETUP"]
    sid = setups[0]["setup_id"] if setups else None
    ck("CASE1 setup created + managed to runner-equivalent (3 revisions, OPEN)",
       sid is not None and len(setups) == 3 and setups[-1]["revision"] == 3,
       f"revisions={[s.get('revision') for s in setups]}")

    # ---- CASE 2a: message just BEFORE shutdown ----
    insert(db, 90004, "`Whale` tp 2 hit take some off", "2026-07-21T09:30:00+00:00")
    cold_cycle(dbp)                      # processes 90004, then "shutdown"
    n_after_a = counts_by_msg().get(90004, 0)
    cold_cycle(dbp)                      # RESTART with nothing new
    ck("CASE2a before-shutdown: processed exactly once, NOT reprocessed on restart",
       n_after_a == 1 and counts_by_msg().get(90004, 0) == 1,
       f"before={n_after_a} after={counts_by_msg().get(90004, 0)}")

    # ---- CASE 2b: message lands DURING the down window ----
    insert(db, 90005, "`Whale` put sl to entry on the runner", "2026-07-21T10:00:00+00:00")
    # (process is down: no cycle running when it landed)
    cold_cycle(dbp)                      # RESTART picks it up
    cold_cycle(dbp)                      # extra restart: must not duplicate
    c5 = counts_by_msg().get(90005, 0)
    latest = [r for r in ledger() if 90005 in (r.get("message_ids") or [])]
    ck("CASE2b during-down: picked up exactly once on restart, correlated to campaign",
       c5 == 1 and latest and latest[0].get("setup_id") == sid, f"count={c5}")

    # ---- CASE 2c: message immediately AFTER startup ----
    insert(db, 90006, "`Whale` close 50% leave 50%", "2026-07-21T10:30:00+00:00")
    cold_cycle(dbp)
    cold_cycle(dbp)
    c6 = counts_by_msg().get(90006, 0)
    ck("CASE2c after-startup: exactly once, no duplicate across further restarts", c6 == 1,
       f"count={c6}")

    # ---- terminal after restarts: full exit closes the runner correctly ----
    insert(db, 90007, "`Whale` full exit", "2026-07-21T11:00:00+00:00")
    cold_cycle(dbp)
    last = [r for r in ledger() if r.get("record_type") == "XAU_F_SETUP"][-1]
    ck("terminal after multiple restarts: EXPLICIT_FULL_EXIT lands as next revision on same campaign",
       90007 in (last.get("message_ids") or []) and last["setup_id"] == sid, last.get("revision"))

    # ---- cursor sanity + no orphans/reviews for correlated msgs ----
    cur = json.load(open(os.path.join(SFA, "live_wire_cursor.json")))
    ck("cursor monotonic at head", cur["last_processed_id"] == 90007, cur)
    reviews = [r for r in ledger() if r.get("record_type") == "XAU_F_INTERPRETATION_REVIEW"]
    ck("zero interpretation-review/orphan records for correlated management", len(reviews) == 0,
       [r.get("message_id") for r in reviews])

    print(f"\nRESTART-SAFETY PROOF: {sum(ok)}/{len(ok)} PASS")
    shutil.rmtree(SAND, ignore_errors=True)
    return 0 if all(ok) else 1


if __name__ == "__main__":
    sys.exit(main())
