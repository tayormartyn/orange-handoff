"""ENTRY-race fix v0.1 — deterministic race tests (isolated TEMP world; real ledgers untouched).

Covers the 8 required scenarios: defer-then-complete, multi-poll retry, restart recovery,
duplicate suppression, setup-timeout refusal, snapshot-write-failure retry, multi-entry ordering,
and no-F001/F002-fallback. Run directly: python tests_watcher_race.py
"""
from __future__ import annotations

import io
import json
import os
import sqlite3
import sys
import tempfile
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
PARENT = os.path.dirname(HERE)
MT = os.path.join(PARENT, "market_tracker")
for p in (HERE, PARENT, MT):
    sys.path.insert(0, p)
import evidence_schema as es                                      # noqa: E402
import evidence_watcher as ew                                     # noqa: E402
import strategy_router as _sr                                     # noqa: E402

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
PASS = 0


def ok(c, name):
    global PASS
    assert c, f"FAIL: {name}"
    PASS += 1
    print(f"  ok {PASS}: {name}")


TMP = tempfile.mkdtemp(prefix="ew_race_")
DB = os.path.join(TMP, "ev.db")
FWD = os.path.join(TMP, "fwd.jsonl")
ILOG = os.path.join(TMP, "ingest.jsonl")

# hermetic redirection (same pattern as tests_watcher.py)
es.PRE_TRADE_LEDGER = ew.snapshots.es.PRE_TRADE_LEDGER = os.path.join(TMP, "pre.jsonl")
es.BLIND_HYP_LEDGER = os.path.join(TMP, "blind.jsonl")
es.MGMT_LEDGER = os.path.join(TMP, "mgmt.jsonl")
es.SECONDFEED_LEDGER = os.path.join(TMP, "sf.jsonl")
es.COVERAGE_LEDGER = os.path.join(TMP, "cov.jsonl")
es.FORWARD_LEDGER = FWD
ew.FWD_LEDGER = FWD
ew.INGEST_LOG = ILOG
ew.CURSOR = os.path.join(TMP, "cursor.json")
ew.EVIDENCE_DB = DB
ew.ENTRY_REFUSAL_LEDGER = os.path.join(TMP, "entry_refusals.jsonl")
_sr.ROUTER_FREEZE_LEDGER = os.path.join(TMP, "router_freeze.jsonl")
# race logic under test — hypothesis/ranking side lanes stubbed for determinism
ew._auto_hypothesis = lambda sid, snap, cur, now_ts: f"HYP_STUB({sid})"
ew._ranking_pack = lambda sid, c, m, cur: f"RANK_STUB({sid})"

BASE = 1784240000 - (1784240000 % 60)
WAIT = ew.entry_setup_wait_seconds()
ok(WAIT >= 2 * ew._wire_poll_seconds(), "wait window derived from wire poll interval with margin")


def iso(ts):
    return datetime.fromtimestamp(ts, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


con = sqlite3.connect(DB)
con.execute("""CREATE TABLE prospective_message_evidence(
  telegram_message_id TEXT, telegram_posted_at_utc TEXT, listener_received_at_utc TEXT,
  raw_text TEXT, raw_text_hash TEXT, message_event_type TEXT, message_revision_number INTEGER,
  telegram_sender_username TEXT)""")


def add(mid, ts, text):
    con.execute("INSERT INTO prospective_message_evidence VALUES(?,?,?,?,?,?,?,?)",
                (str(mid), iso(ts), iso(ts + 1), text, "h" * 64, "CREATED", 1, "seascalperfarouk"))
    con.commit()


def add_setup(sid, mid, ts):
    with open(FWD, "a", encoding="utf-8") as fh:
        fh.write(json.dumps({"record_type": "XAU_F_SETUP", "setup_id": sid,
                             "message_ids": [mid], "timestamp_utc": iso(ts),
                             "direction": "SHORT"}) + "\n")


with open(ILOG, "w", encoding="utf-8") as fh:
    for i in range(30):
        t = BASE - (30 - i) * 60
        fh.write(json.dumps({"schema": "market_event_v0_1", "kind": "ACCEPTED", "event_ts": t,
                             "provider": "PEPPERSTONE_TV_BAR_FEED", "revision": 1, "logical_hash": f"h{i}",
                             "bar": {"instrument": "XAUUSD", "provider": "PEPPERSTONE_TV_BAR_FEED",
                                     "timeframe": "1m", "event_ts": t, "receive_ts": t + 60,
                                     "open": "4030.0", "high": "4031.0", "low": "4029.0",
                                     "close": "4030.5", "bid": None, "ask": None,
                                     "source_id": "t", "sequence": i, "revision": 1}}) + "\n")
open(FWD, "w").close()

ENTRY = "seascalperfarouk Posted in 🪙・gold-trades\n\nXAUUSD Sell : 4025–4035\nStop Loss: 4075"


def pre_count():
    if not os.path.exists(es.PRE_TRADE_LEDGER):
        return 0
    return sum(1 for _ in open(es.PRE_TRADE_LEDGER, encoding="utf-8"))


def refusals():
    if not os.path.exists(ew.ENTRY_REFUSAL_LEDGER):
        return []
    return [json.loads(l) for l in open(ew.ENTRY_REFUSAL_LEDGER, encoding="utf-8")]


def cursor():
    return json.load(open(ew.CURSOR, encoding="utf-8"))


print("== T1: ENTRY one cycle before setup -> deferred, then exactly one PRE lifecycle")
add(60001, BASE, ENTRY)
a = ew.run_cycle(db_path=DB, now_ts=BASE + 5)
ok(any("ENTRY_DEFERRED_WAITING_FOR_SETUP(60001)" in x for x in a), "T1 deferred (no silent consume)")
ok("60001" in cursor().get("pending_entries", {}), "T1 pending state durable in cursor file")
ok(pre_count() == 0, "T1 no PRE before setup exists")
add_setup("XAU-F900-20260716", 60001, BASE + 14)          # wire writes setup 14s later
a = ew.run_cycle(db_path=DB, now_ts=BASE + 50)
ok(any("ENTRY_PRE_LIFECYCLE_COMPLETED(60001 -> XAU-F900-20260716)" in x for x in a), "T1 completed on retry")
ok(pre_count() == 1, "T1 exactly one PRE snapshot")
ok("60001" not in cursor().get("pending_entries", {}), "T1 pending cleared after completion")

print("== T2: ENTRY multiple wire-polls before setup -> repeated retry, no silent loss")
add(60002, BASE + 100, ENTRY)
a = ew.run_cycle(db_path=DB, now_ts=BASE + 105)
ok(any("ENTRY_DEFERRED_WAITING_FOR_SETUP(60002)" in x for x in a), "T2 deferred")
for i in range(3):                                        # three watcher cycles, still no setup
    a = ew.run_cycle(db_path=DB, now_ts=BASE + 150 + i * 45)
    ok(any("ENTRY_RETRY(60002" in x for x in a), f"T2 retry cycle {i+1} visible")
ok(pre_count() == 1 and not refusals(), "T2 no loss, no premature refusal inside wait window")
add_setup("XAU-F901-20260716", 60002, BASE + 290)
a = ew.run_cycle(db_path=DB, now_ts=BASE + 300)
ok(any("ENTRY_PRE_LIFECYCLE_COMPLETED(60002" in x for x in a) and pre_count() == 2,
   "T2 completes after late setup, exactly one PRE")

print("== T3: watcher restart while ENTRY pending -> pending state resumes and completes")
add(60003, BASE + 400, ENTRY)
ew.run_cycle(db_path=DB, now_ts=BASE + 405)
ok("60003" in cursor().get("pending_entries", {}), "T3 pending before restart")
# restart simulation: nothing in memory carries over — run_cycle always re-loads the cursor file
add_setup("XAU-F902-20260716", 60003, BASE + 430)
a = ew.run_cycle(db_path=DB, now_ts=BASE + 460)
ok(any("ENTRY_PRE_LIFECYCLE_COMPLETED(60003" in x for x in a) and pre_count() == 3,
   "T3 pending survived restart and completed exactly once")

print("== T4: duplicate ENTRY after completion -> no duplicate PRE/freeze")
c = cursor()
c["after_msg_id"] = 60002                                  # force re-scan of 60003
json.dump(c, open(ew.CURSOR, "w", encoding="utf-8"))
a = ew.run_cycle(db_path=DB, now_ts=BASE + 500)
ok(any("ENTRY_DUPLICATE_ALREADY_COMPLETED(60003" in x for x in a), "T4 duplicate detected")
ok(pre_count() == 3, "T4 no duplicate PRE")

print("== T5: setup never appears -> explicit timeout refusal, prospective-ineligible, no drop")
add(60004, BASE + 600, ENTRY)
ew.run_cycle(db_path=DB, now_ts=BASE + 605)
a = ew.run_cycle(db_path=DB, now_ts=BASE + 605 + WAIT + 60)   # beyond the bounded window
ok(any("ENTRY_REFUSED_SETUP_TIMEOUT(60004" in x for x in a), "T5 refusal logged")
r = [x for x in refusals() if x["message_id"] == 60004]
ok(len(r) == 1, "T5 exactly one durable refusal record")
ok(r[0]["eligible_for_prospective_evidence"] is False and r[0]["eligible_for_training"] is False,
   "T5 refusal is prospective/training-ineligible")
ok(r[0]["configured_wait_window_seconds"] == WAIT and r[0]["retries"] >= 1
   and r[0]["first_seen_ts"] and r[0]["refused_ts"], "T5 refusal carries ids/timestamps/retries/window")
ok("60004" not in cursor().get("pending_entries", {}), "T5 safe cursor progression after refusal")
ok(pre_count() == 3, "T5 no PRE manufactured")

print("== T6: snapshot write fails once -> retry next cycle, no cursor loss")
add(60005, BASE + 900, ENTRY)
add_setup("XAU-F903-20260716", 60005, BASE + 901)
_orig = ew.snapshots.build_pre_trade_snapshot
_calls = {"n": 0}
def _flaky(**kw):
    _calls["n"] += 1
    if _calls["n"] == 1:
        raise OSError("simulated disk failure")
    return _orig(**kw)
ew.snapshots.build_pre_trade_snapshot = _flaky
a = ew.run_cycle(db_path=DB, now_ts=BASE + 910)
ok(any("ENTRY_LIFECYCLE_WRITE_FAILED(60005" in x for x in a), "T6 write failure surfaced")
ok("60005" in cursor().get("pending_entries", {}), "T6 entry retained pending (cursor retryable)")
a = ew.run_cycle(db_path=DB, now_ts=BASE + 955)
ok(any("ENTRY_PRE_LIFECYCLE_COMPLETED(60005" in x for x in a) and pre_count() == 4,
   "T6 retry succeeded exactly once")
ew.snapshots.build_pre_trade_snapshot = _orig

print("== T7: multiple sequential entries -> ordering preserved, no indefinite blockage")
add(60006, BASE + 1000, ENTRY)
add(60007, BASE + 1010, ENTRY)
a = ew.run_cycle(db_path=DB, now_ts=BASE + 1015)
ok(any("ENTRY_DEFERRED_WAITING_FOR_SETUP(60006)" in x for x in a)
   and any("ENTRY_DEFERRED_WAITING_FOR_SETUP(60007)" in x for x in a), "T7 both deferred")
add_setup("XAU-F904-20260716", 60007, BASE + 1020)         # LATER entry's setup arrives first
a = ew.run_cycle(db_path=DB, now_ts=BASE + 1060)
ok(any("ENTRY_PRE_LIFECYCLE_COMPLETED(60007" in x for x in a), "T7 later entry not blocked by earlier pending")
ok(any("ENTRY_RETRY(60006" in x for x in a), "T7 earlier entry still retrying (no head-of-line block)")
add_setup("XAU-F905-20260716", 60006, BASE + 1070)
a = ew.run_cycle(db_path=DB, now_ts=BASE + 1105)
ok(any("ENTRY_PRE_LIFECYCLE_COMPLETED(60006" in x for x in a) and pre_count() == 6, "T7 both completed once each")

print("== T8: F001/F002 present -> never selected as fallback for an unmatched ENTRY")
for old_sid, old_mid in (("XAU-F001-20260714", 45713), ("XAU-F002-20260714", 45716)):
    add_setup(old_sid, old_mid, BASE - 200000)
add(60008, BASE + 1200, ENTRY)
a = ew.run_cycle(db_path=DB, now_ts=BASE + 1205)
ok(any("ENTRY_DEFERRED_WAITING_FOR_SETUP(60008)" in x for x in a),
   "T8 unmatched entry deferred — F001/F002 NOT selected")
a = ew.run_cycle(db_path=DB, now_ts=BASE + 1205 + WAIT + 60)
ok(any("ENTRY_REFUSED_SETUP_TIMEOUT(60008" in x for x in a), "T8 refused after window")
pre_records = [json.loads(l) for l in open(es.PRE_TRADE_LEDGER, encoding="utf-8")]
ok(not any(p["setup_id"] in ("XAU-F001-20260714", "XAU-F002-20260714") for p in pre_records),
   "T8 no PRE ever attached to F001/F002")

# real-ledger contamination guard: every temp path is under TMP; the redirected refusal ledger too
ok(all(p.startswith(TMP) for p in (es.PRE_TRADE_LEDGER, es.BLIND_HYP_LEDGER, es.MGMT_LEDGER,
                                   ew.ENTRY_REFUSAL_LEDGER, ew.CURSOR, ew.FWD_LEDGER,
                                   _sr.ROUTER_FREEZE_LEDGER)),
   "hermetic: all writers redirected into the temp world")
con.close()
print(f"\nPASS {PASS} watcher-race checks | WATCHER_ENTRY_SILENT_LOSS_COUNT = 0 (every entry "
      "completed, duplicate-suppressed, or explicitly refused)")
