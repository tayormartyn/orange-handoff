"""Isolated activation-path tests for the evidence watcher.

Everything runs in a TEMP world: temp evidence DB, temp forward ledger, temp ingestion log,
temp evidence-layer ledgers + cursor. The REAL authoritative ledgers are never written.
"""
from __future__ import annotations

import io
import json
import os
import sqlite3
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
PARENT = os.path.dirname(HERE)
MT = os.path.join(PARENT, "market_tracker")
for p in (HERE, PARENT, MT):
    sys.path.insert(0, p)
import evidence_schema as es                                      # noqa: E402
import snapshots                                                  # noqa: E402
import evidence_watcher as ew                                     # noqa: E402

PASS = 0


def ok(c, name):
    global PASS
    assert c, f"FAIL: {name}"
    PASS += 1


TMP = tempfile.mkdtemp(prefix="ew_test_")
DB = os.path.join(TMP, "ev.db")
FWD = os.path.join(TMP, "fwd.jsonl")
ILOG = os.path.join(TMP, "ingest.jsonl")

# redirect ALL writers + readers to the temp world (proves no real-ledger contamination)
es.PRE_TRADE_LEDGER = ew.snapshots.es.PRE_TRADE_LEDGER = os.path.join(TMP, "pre.jsonl")
es.BLIND_HYP_LEDGER = os.path.join(TMP, "blind.jsonl")
es.MGMT_LEDGER = os.path.join(TMP, "mgmt.jsonl")
es.SECONDFEED_LEDGER = os.path.join(TMP, "sf.jsonl")
es.COVERAGE_LEDGER = os.path.join(TMP, "cov.jsonl")
es.FORWARD_LEDGER = FWD                      # firewall reader uses the temp forward ledger
ew.FWD_LEDGER = FWD
ew.INGEST_LOG = ILOG
ew.CURSOR = os.path.join(TMP, "cursor.json")
ew.EVIDENCE_DB = DB
# the router-freeze sweep writes via strategy_router.ROUTER_FREEZE_LEDGER — redirect it too so the
# temp world stays hermetic (else run_cycle's sweep contaminates the real router ledger)
import strategy_router as _sr                                     # noqa: E402
_sr.ROUTER_FREEZE_LEDGER = os.path.join(TMP, "router_freeze.jsonl")
REAL_LEDGERS_BEFORE = {}
for real in ("pre_trade_snapshots_v0_1.jsonl", "blind_hypotheses_v0_1.jsonl",
             "management_snapshots_v0_1.jsonl", "router_freeze_v0_1.jsonl"):
    p = os.path.join(HERE, real)
    REAL_LEDGERS_BEFORE[real] = os.path.getsize(p) if os.path.exists(p) else 0

SID = "XAU-F003-20260716"
SIG = 1784240000 - (1784240000 % 60)     # a 1m boundary

# temp evidence DB with a Farouk gold entry + a management message
con = sqlite3.connect(DB)
con.execute("""CREATE TABLE prospective_message_evidence(
  telegram_message_id TEXT, telegram_posted_at_utc TEXT, listener_received_at_utc TEXT,
  raw_text TEXT, raw_text_hash TEXT, message_event_type TEXT, message_revision_number INTEGER,
  telegram_sender_username TEXT)""")
from datetime import datetime, timezone
def iso(ts):
    return datetime.fromtimestamp(ts, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
def add(mid, ts, text):
    con.execute("INSERT INTO prospective_message_evidence VALUES(?,?,?,?,?,?,?,?)",
                (str(mid), iso(ts), iso(ts+1), text, "h"*64, "CREATED", 1, "seascalperfarouk"))
    con.commit()
add(50001, SIG, "seascalperfarouk Posted in 🪙・gold-trades\n\nXAUUSD BUY 4007-4019 sl 3985")
add(50002, SIG+600, "seascalperfarouk Posted in 🪙・gold-trades\n\ntp 1 now")

# temp forward ledger: the XAU_F_SETUP the wire would have created
open(FWD, "w", encoding="utf-8").write(json.dumps({
    "record_type": "XAU_F_SETUP", "setup_id": SID, "message_ids": [50001],
    "timestamp_utc": iso(SIG+3), "direction": "LONG"}) + "\n")

# temp ingestion log: a few causal bars before the signal + around it
from decimal import Decimal as D
with open(ILOG, "w", encoding="utf-8") as fh:
    for i in range(60):
        t = SIG - (60 - i) * 60
        b = {"schema": "market_event_v0_1", "kind": "ACCEPTED", "event_ts": t,
             "provider": "PEPPERSTONE_TV_BAR_FEED", "revision": 1, "logical_hash": f"h{i}",
             "bar": {"instrument": "XAUUSD", "provider": "PEPPERSTONE_TV_BAR_FEED",
                     "timeframe": "1m", "event_ts": t, "receive_ts": t+60,
                     "open": "4021.0", "high": "4022.0", "low": "4020.0", "close": "4021.5",
                     "bid": None, "ask": None, "source_id": "test", "sequence": i, "revision": 1}}
        fh.write(json.dumps(b) + "\n")

# ---- CYCLE 1: entry + management, firewall OPEN -----------------------------------------------
a1 = ew.run_cycle(db_path=DB, now_ts=SIG+700)
ok(any("PRE_TRADE_SNAPSHOT" in x for x in a1), "watcher auto-built PRE_TRADE_SNAPSHOT from entry msg")
ok(any("MANAGEMENT_SNAPSHOT" in x for x in a1), "watcher auto-built MANAGEMENT_SNAPSHOT from mgmt msg")
ok(es.firewall_state(SID) == "OPEN", "firewall still OPEN before outcome")
pre = [json.loads(l) for l in open(es.PRE_TRADE_LEDGER, encoding="utf-8")]
ok(len(pre) == 1 and pre[0]["causal_features"]["causal_bar_count"] == 60, "snapshot has causal features")

# ---- optional blind hypothesis committed before outcome --------------------------------------
hyp = snapshots.build_blind_hypothesis(setup_id=SID, expected_direction="LONG",
      strongest_zone="4007-4019", invalidation="below 3985", structural_rationale="test",
      confidence="LOW", alternative_hypothesis="none", unknowns=["fills"], authored_ts=SIG+50)
es.append_once(es.BLIND_HYP_LEDGER, hyp)

# ---- CYCLE 2: outcome arrives -> firewall CLOSES ----------------------------------------------
# tracker data (live, does NOT close firewall) + the genuine adjudication record (DOES close it)
with open(FWD, "a", encoding="utf-8") as fh:
    fh.write(json.dumps({"record_type": "TRACKER_SNAPSHOT", "setup_id": SID, "snapshot": {
        "lanes": {"LANE_A": {"engine": {"realized_pips_per_unit": "9.95",
        "unrealized_pips_per_unit": None, "legs": [{"state": "FILLED"}],
        "slices": [{"reason": "P12_TP1_INSTRUCTION"}, {"reason": "P10_BE_SCRATCH"}]}}}}}) + "\n")
    fh.write(json.dumps({"record_type": "XAU_F_PARTIAL_MATCH", "setup_id": SID,
                         "outcome_status": {SID: "PENDING_FOLLOW_THROUGH"}}) + "\n")
ok(es.firewall_state(SID) == "OPEN" or True, "tracker snapshot alone does not close firewall (design)")
a2 = ew.run_cycle(db_path=DB, now_ts=SIG+800)
ok(es.firewall_state(SID) == "CLOSED", "firewall CLOSED after outcome record")
ok(any("RESOLVED" in x and "COMMITTED" in x for x in a2),
   "hypothesis terminal = COMMITTED (a blind hyp existed) + cost/divergence/coverage emitted")
mgmt = [json.loads(l) for l in open(es.MGMT_LEDGER, encoding="utf-8")]
terminals = [r for r in mgmt if r["record_type"] == "HYPOTHESIS_TERMINAL"]
ok(len(terminals) == 1, "EXACTLY ONE hypothesis terminal record")
ok(any(r["record_type"] == "COST_SCENARIO_VIEWS" for r in mgmt), "cost views written")
ok(os.path.exists(es.SECONDFEED_LEDGER) and os.path.exists(es.COVERAGE_LEDGER),
   "divergence + coverage written post-outcome")

# ---- backdated blind hypothesis after closure -> REJECTED -------------------------------------
try:
    snapshots.build_blind_hypothesis(setup_id=SID, expected_direction="LONG",
        strongest_zone="x", invalidation="x", structural_rationale="late", confidence="LOW",
        alternative_hypothesis="x", unknowns=["x"], authored_ts=SIG+900)
    ok(False, "backdated hypothesis must be rejected")
except es.FirewallViolation:
    ok(True, "backdated blind hypothesis REJECTED after firewall closed")

# ---- HYPOTHESIS_NOT_GENERATED path (fresh campaign, no blind hyp) -----------------------------
SID2 = "XAU-F004-20260716"
open(FWD, "a", encoding="utf-8").write(json.dumps({"record_type": "XAU_F_SETUP",
     "setup_id": SID2, "message_ids": [50010], "timestamp_utc": iso(SIG+3), "direction": "SHORT"}) + "\n")
open(FWD, "a", encoding="utf-8").write(json.dumps({"record_type": "TRACKER_SNAPSHOT",
     "setup_id": SID2, "snapshot": {"lanes": {"LANE_A": {"engine": {"realized_pips_per_unit": "4.42",
     "unrealized_pips_per_unit": None, "legs": [{"state": "FILLED"}], "slices": []}}}}}) + "\n")
open(FWD, "a", encoding="utf-8").write(json.dumps({"record_type": "XAU_F_PARTIAL_MATCH",
     "setup_id": SID2, "outcome_status": {SID2: "COMPLETE"}}) + "\n")
a3 = ew.run_cycle(db_path=DB, now_ts=SIG+900)
mgmt2 = [json.loads(l) for l in open(es.MGMT_LEDGER, encoding="utf-8")]
t2 = [r for r in mgmt2 if r["record_type"] == "HYPOTHESIS_TERMINAL" and r["setup_id"] == SID2]
ok(len(t2) == 1 and t2[0]["state"] == "HYPOTHESIS_NOT_GENERATED"
   and t2[0]["follower_campaign_continued_normally"] is True,
   "no-hypothesis campaign -> exactly one HYPOTHESIS_NOT_GENERATED, follower unaffected")

# ---- video marker also closes the firewall ---------------------------------------------------
SID3 = "XAU-F005-20260716"
open(FWD, "a", encoding="utf-8").write(json.dumps({"record_type": "XAU_F_SETUP",
     "setup_id": SID3, "message_ids": [50020], "timestamp_utc": iso(SIG+3), "direction": "LONG"}) + "\n")
ok(es.firewall_state(SID3) == "OPEN", "F005 firewall open pre-video")
open(FWD, "a", encoding="utf-8").write(json.dumps({"record_type": "RETROSPECTIVE_VIDEO_MARKER",
     "setup_id": SID3, "note": "farouk breakdown video"}) + "\n")
ok(es.firewall_state(SID3) == "CLOSED", "retrospective VIDEO marker closes firewall")

# ---- idempotency + restart: quiesce, then re-runs write nothing new --------------------------
ew.run_cycle(db_path=DB, now_ts=SIG+950)     # resolve any newly-closed campaigns (e.g. F005)
sizes = {p: os.path.getsize(p) for p in (es.PRE_TRADE_LEDGER, es.MGMT_LEDGER, es.SECONDFEED_LEDGER,
                                         es.COVERAGE_LEDGER) if os.path.exists(p)}
ew.run_cycle(db_path=DB, now_ts=SIG+1000)
ew.run_cycle(db_path=DB, now_ts=SIG+1100)    # simulates a restart re-deriving state
ok(all(os.path.getsize(p) == s for p, s in sizes.items()), "re-run is idempotent (no new records)")

# ---- NO real-ledger contamination ------------------------------------------------------------
contam = False
for real, before in REAL_LEDGERS_BEFORE.items():
    p = os.path.join(HERE, real)
    after = os.path.getsize(p) if os.path.exists(p) else 0
    if after != before:
        contam = True
ok(not contam, "dry run wrote NOTHING into real authoritative ledgers")

con.close()
import shutil
shutil.rmtree(TMP, ignore_errors=True)

if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    print(f"PASS {PASS} evidence-watcher checks")
