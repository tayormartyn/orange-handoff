"""Isolated tests for the automatic blind-hypothesis generator + backfill quarantine.

Fully temp-world: no real ledger is written. Proves the required lifecycle and failure modes.
"""
from __future__ import annotations

import io
import json
import os
import sqlite3
import sys
import tempfile
from datetime import datetime, timezone
from decimal import Decimal as D

HERE = os.path.dirname(os.path.abspath(__file__))
PARENT = os.path.dirname(HERE)
MT = os.path.join(PARENT, "market_tracker")
for p in (HERE, PARENT, MT):
    sys.path.insert(0, p)
import evidence_schema as es                                      # noqa: E402
import snapshots                                                  # noqa: E402
import hypothesis_generator as hg                                 # noqa: E402
import backfill_quarantine as bq                                  # noqa: E402
import evidence_watcher as ew                                     # noqa: E402

PASS = 0


def ok(c, name):
    global PASS
    assert c, f"FAIL: {name}"
    PASS += 1


def iso(ts):
    return datetime.fromtimestamp(ts, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ---- generator: causal-only, deterministic ----------------------------------------------------
SIG = 1784240000 - (1784240000 % 60)
snap = snapshots  # alias
# build a snapshot in a temp firewall world
TMP = tempfile.mkdtemp(prefix="auto_hyp_")
es.PRE_TRADE_LEDGER = os.path.join(TMP, "pre.jsonl")
es.BLIND_HYP_LEDGER = os.path.join(TMP, "blind.jsonl")
es.MGMT_LEDGER = os.path.join(TMP, "mgmt.jsonl")
es.SECONDFEED_LEDGER = os.path.join(TMP, "sf.jsonl")
es.COVERAGE_LEDGER = os.path.join(TMP, "cov.jsonl")
FWD = os.path.join(TMP, "fwd.jsonl")
es.FORWARD_LEDGER = ew.FWD_LEDGER = FWD
# redirect the router-freeze sweep ledger into the temp world too (run_cycle now calls it)
import strategy_router as _sr                                     # noqa: E402
_sr.ROUTER_FREEZE_LEDGER = os.path.join(TMP, "router_freeze.jsonl")

# causal bars (rising -> bullish HTF) before signal
bars = [(SIG - (60 - i) * 60, D("4000") + i, D("4001") + i, D("3999") + i, D("4000.5") + i)
        for i in range(60)]
open(FWD, "w", encoding="utf-8").write(json.dumps({"record_type": "XAU_F_SETUP",
     "setup_id": "XAU-F003-20260716", "message_ids": [60001], "timestamp_utc": iso(SIG + 3),
     "direction": "LONG"}) + "\n")
s = snapshots.build_pre_trade_snapshot(
    setup_id="XAU-F003-20260716", direction="LONG", zone_low="4050", zone_high="4060", sl="4030",
    source_ts=SIG, receipt_ts=SIG + 1, proposal_ts=SIG + 3, market_ts=SIG + 3,
    current_price="4058.0", incomplete_bar_status="FORMING", bars=bars)

h = hg.generate(s, now_ts=SIG + 4)
ok(h["expected_direction"] in ("LONG", "SHORT", "UNKNOWN"), "generator returns a direction")
ok(h["snapshot_hash"] == s["logical_hash"] and h["methodology_version"] == "methodology_v0_1",
   "hypothesis references snapshot hash + frozen methodology version")
ok(h["generated_at_utc"] == SIG + 4 and "confidence" in h, "hypothesis carries generation ts + confidence")
# determinism
ok(hg.generate(s, now_ts=SIG + 4) == h, "generator is deterministic")
# no outcome/future/video access: injecting outcome fields does not change the result
s_contaminated = dict(s)
try:
    s_contaminated["outcome_status"] = "VERIFIED_WIN"
    hg.generate(s_contaminated, now_ts=SIG + 4)
    ok(False, "snapshot with outcome key must be rejected as malformed")
except hg.HypothesisMalformed:
    ok(True, "generator refuses a snapshot carrying outcome/future/video keys")

# ---- failure modes ----------------------------------------------------------------------------
try:
    hg.generate(s, now_ts=SIG + 4, deadline_s=0.0, _slow=0.02)
    ok(False, "timeout must raise")
except hg.HypothesisTimeout:
    ok(True, "generator timeout raises HypothesisTimeout")
try:
    hg.generate({"logical_hash": "x"}, now_ts=SIG + 4)
    ok(False, "missing causal_features must raise")
except hg.HypothesisMalformed:
    ok(True, "malformed snapshot (no causal_features) raises")
# missing features: too few causal bars + UNKNOWN bias
thin = snapshots.build_pre_trade_snapshot(
    setup_id="XAU-F007-20260716", direction="LONG", zone_low="4050", zone_high="4060", sl="4030",
    source_ts=SIG, receipt_ts=SIG + 1, proposal_ts=SIG + 3, market_ts=SIG + 3,
    current_price="4058.0", incomplete_bar_status="FORMING", bars=bars[:5])
try:
    hg.generate(thin, now_ts=SIG + 4)
    ok(False, "insufficient features must raise")
except hg.MissingFeatures:
    ok(True, "missing/insufficient features raises MissingFeatures")

# ---- watcher integration: temp DB, auto-hypothesis committed ----------------------------------
DB = os.path.join(TMP, "ev.db")
ew.EVIDENCE_DB = DB
ew.CURSOR = os.path.join(TMP, "cursor.json")
ew.INGEST_LOG = os.path.join(TMP, "ingest.jsonl")
ew.INITIAL_AFTER_MSG_ID = 60000
con = sqlite3.connect(DB)
con.execute("""CREATE TABLE prospective_message_evidence(
  telegram_message_id TEXT, telegram_posted_at_utc TEXT, listener_received_at_utc TEXT,
  raw_text TEXT, raw_text_hash TEXT, message_event_type TEXT, message_revision_number INTEGER,
  telegram_sender_username TEXT)""")
con.execute("INSERT INTO prospective_message_evidence VALUES(?,?,?,?,?,?,?,?)",
            ("60001", iso(SIG), iso(SIG + 1),
             "seascalperfarouk Posted in 🪙・gold-trades\n\nXAUUSD BUY 4050-4060 sl 4030",
             "h" * 64, "CREATED", 1, "seascalperfarouk"))
con.commit()
with open(ew.INGEST_LOG, "w", encoding="utf-8") as fh:
    for i, b in enumerate(bars):
        fh.write(json.dumps({"schema": "market_event_v0_1", "kind": "ACCEPTED", "event_ts": b[0],
                 "provider": "PEPPERSTONE_TV_BAR_FEED", "revision": 1, "logical_hash": f"h{i}",
                 "bar": {"instrument": "XAUUSD", "provider": "PEPPERSTONE_TV_BAR_FEED",
                         "timeframe": "1m", "event_ts": b[0], "receive_ts": b[0] + 60,
                         "open": str(b[1]), "high": str(b[2]), "low": str(b[3]), "close": str(b[4]),
                         "bid": None, "ask": None, "source_id": "t", "sequence": i, "revision": 1}}) + "\n")

a1 = ew.run_cycle(db_path=DB, now_ts=SIG + 700)
ok(any("PRE_TRADE_SNAPSHOT" in x for x in a1), "watcher wrote pre-trade snapshot for F003")
ok(any("BLIND_HYPOTHESIS_AUTO" in x for x in a1), "watcher AUTO-committed a blind hypothesis")
blind = [json.loads(l) for l in open(es.BLIND_HYP_LEDGER, encoding="utf-8")]
ok(len(blind) == 1 and blind[0]["generator"] == "AUTO"
   and blind[0]["snapshot_hash"] != "UNKNOWN", "exactly one AUTO blind hypothesis w/ snapshot hash")
ok(es.firewall_state("XAU-F003-20260716") == "OPEN", "firewall still OPEN; follower independent")

# follower unaffected: no follower ledger/proposal file was touched by the watcher
ok(not os.path.exists(os.path.join(HERE, "..", "follower_ledger_v0_1.jsonl.EVIDENCE_TOUCH")),
   "watcher wrote nothing into follower state (separate process)")

# ---- outcome closes firewall -> terminal = COMMITTED, no later hypothesis ----------------------
with open(FWD, "a", encoding="utf-8") as fh:
    fh.write(json.dumps({"record_type": "XAU_F_PARTIAL_MATCH", "setup_id": "XAU-F003-20260716",
                         "outcome_status": {"XAU-F003-20260716": "COMPLETE"}}) + "\n")
a2 = ew.run_cycle(db_path=DB, now_ts=SIG + 800)
mgmt = [json.loads(l) for l in open(es.MGMT_LEDGER, encoding="utf-8")]
terms = [r for r in mgmt if r["record_type"] == "HYPOTHESIS_TERMINAL"
         and r["setup_id"] == "XAU-F003-20260716"]
ok(len(terms) == 1 and terms[0]["state"] == "BLIND_HYPOTHESIS_COMMITTED",
   "exactly one terminal = COMMITTED (auto hyp existed)")
try:
    snapshots.build_blind_hypothesis(setup_id="XAU-F003-20260716", expected_direction="LONG",
        strongest_zone="x", invalidation="x", structural_rationale="late", confidence="LOW",
        alternative_hypothesis="x", unknowns=["x"], authored_ts=SIG + 900)
    ok(False, "no later hypothesis possible")
except es.FirewallViolation:
    ok(True, "no later hypothesis possible after firewall closed")

# ---- idempotency / no duplicate hypothesis / restart -----------------------------------------
sizes = {p: os.path.getsize(p) for p in (es.BLIND_HYP_LEDGER, es.MGMT_LEDGER)}
ew.run_cycle(db_path=DB, now_ts=SIG + 900)
ew.run_cycle(db_path=DB, now_ts=SIG + 1000)
ok(all(os.path.getsize(p) == s2 for p, s2 in sizes.items()),
   "re-run: no duplicate hypothesis / terminal (idempotent, restart-safe)")

# ---- firewall closing DURING generation -> NOT_GENERATED terminal -----------------------------
# fresh campaign whose outcome is already present when the watcher first sees the entry
open(FWD, "a", encoding="utf-8").write(json.dumps({"record_type": "XAU_F_SETUP",
     "setup_id": "XAU-F008-20260716", "message_ids": [60008], "timestamp_utc": iso(SIG + 3),
     "direction": "LONG"}) + "\n")
open(FWD, "a", encoding="utf-8").write(json.dumps({"record_type": "XAU_F_PARTIAL_MATCH",
     "setup_id": "XAU-F008-20260716", "outcome_status": {"XAU-F008-20260716": "DONE"}}) + "\n")
con.execute("INSERT INTO prospective_message_evidence VALUES(?,?,?,?,?,?,?,?)",
            ("60008", iso(SIG), iso(SIG + 1),
             "seascalperfarouk Posted in 🪙・gold-trades\n\nXAUUSD BUY 4050-4060 sl 4030",
             "h" * 64, "CREATED", 1, "seascalperfarouk"))
con.commit()
a3 = ew.run_cycle(db_path=DB, now_ts=SIG + 1100)
t8 = [r for r in [json.loads(l) for l in open(es.MGMT_LEDGER, encoding="utf-8")]
      if r["record_type"] == "HYPOTHESIS_TERMINAL" and r["setup_id"] == "XAU-F008-20260716"]
# entry with firewall already CLOSED -> no pre-trade snapshot, resolution emits NOT_GENERATED
ok(len(t8) == 1 and t8[0]["state"] == "HYPOTHESIS_NOT_GENERATED",
   "firewall-closed-first campaign -> exactly one NOT_GENERATED terminal")

# ---- backfill quarantine ----------------------------------------------------------------------
ok(bq.is_analytical("XAU-F003-20260716") and bq.is_analytical("XAU-F015-20260801"),
   "campaign #3 and #15 are analytical")
ok(not bq.is_analytical("XAU-F001-20260714") and not bq.is_analytical("XAU-F002-20260714"),
   "F001/F002 excluded from analytics")
ok(not bq.is_analytical("XAU-F???-20260714") and not bq.is_analytical(""),
   "placeholder + empty ids excluded")
ids = ["XAU-F001-20260714", "XAU-F002-20260714", "XAU-F???-20260714",
       "XAU-F003-20260716", "XAU-F004-20260716"]
ok(bq.analytical_only(ids) == ["XAU-F003-20260716", "XAU-F004-20260716"],
   "analytical_only keeps campaign #3 onward only")
ok(bq.classification("XAU-F001-20260714") == "NON_ANALYTICAL_BACKFILL"
   and bq.classification("XAU-F003-20260716") == "ANALYTICAL_CAMPAIGN", "classification correct")
man = bq.write_manifest()
ok("expectancy" in man["excluded_from"] and "profitability_reports" in man["excluded_from"],
   "quarantine manifest lists excluded analytics")

# ---- guard / invariants ----------------------------------------------------------------------
import guards
inv = guards.verify_project_invariants()
ok(inv["constitution"] == "FROZEN_RATIFIED" and inv["scorers"] == "UNCHANGED", "invariants unchanged")

con.close()
import shutil
shutil.rmtree(TMP, ignore_errors=True)

if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    print(f"PASS {PASS} auto-hypothesis + quarantine checks")
