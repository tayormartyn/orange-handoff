"""Full-exit morphology v0.1 + exact-sequence isolated replay (watcher race + correlation).

Everything runs in a TEMP world (temp evidence DB, forward/follower ledgers, cards, cursors,
evidence-layer ledgers, router freeze ledger with SYNTHETIC_INTEGRATION_TEST class). The real
authoritative ledgers are never written. Run directly: python tests_full_exit_replay.py
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
EL = os.path.join(HERE, "evidence_layer")
MT = os.path.join(HERE, "market_tracker")
for p in (HERE, EL, MT):
    sys.path.insert(0, p)
import interpreter                                                # noqa: E402
import live_wire as W                                             # noqa: E402
import engine as EG                                               # noqa: E402
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


# ---------------- Part A: bounded full-exit morphology ------------------------------------------
HDR = "seascalperfarouk Posted in 🪙・gold-trades\n\n"
for phrase in ("full exit", "Fully exit", "exit fully", "exited fully", "close all",
               "close everything"):
    c = interpreter.classify(HDR + "`Whale` " + phrase)
    ok(c["kind"] == "MANAGEMENT" and any(i["instruction_type"] == "EXPLICIT_FULL_EXIT"
                                          for i in c["instructions"]),
       f"A: '{phrase}' -> EXPLICIT_FULL_EXIT management")
c = interpreter.classify(HDR + "`Whale` full close")
ok(any(i["instruction_type"] == "FINAL_CLOSE" for i in c["instructions"]),
   "A: 'full close' keeps its existing FINAL_CLOSE terminal path")
for text, why in (("`Whale` 280-300 pips no buy today guys", "pips claim"),
                  ("`Whale` enjoy profit", "profit commentary"),
                  ("`Whale` 100+ pisp", "pips typo claim"),
                  ("`Whale`", "bare result-card caption"),
                  ("`Whale` 200 pips in profit. Taking 75% off and looking for 3980–3970 as the final take profit target.", "partial take")):
    c = interpreter.classify(HDR + text)
    ins = c.get("instructions", []) if c["kind"] == "MANAGEMENT" else []
    ok(not any(i["instruction_type"] == "EXPLICIT_FULL_EXIT" for i in ins),
       f"A: {why} does NOT create a full exit")
c = interpreter.classify(HDR + "`Whale` full exit")
fe = [i for i in c["instructions"] if i["instruction_type"] == "EXPLICIT_FULL_EXIT"][0]
ok(fe["raw_instruction"] == "full exit"
   and fe["size_basis"] == "ALL_CURRENTLY_REMAINING_OPEN_FILLED_SIZE",
   "A: source wording + size basis preserved on the instruction")

# ---------------- Part B: engine terminal semantics ---------------------------------------------
CONST = json.load(open(W.CONST_PATH, encoding="utf-8"))
SIG = 1784240000 - (1784240000 % 60)
bars = [
    (SIG, D("4020"), D("4026"), D("4019"), D("4025.5")),          # closes inside zone -> near fills
    (SIG + 60, D("4025.5"), D("4027"), D("4024"), D("4026.0")),
    (SIG + 120, D("4026"), D("4026.5"), D("4018"), D("4019.0")),  # full-exit bar
]
camp = {"setup_id": "XAU-TEST-FE", "direction": "SHORT", "zone_low": D("4025"),
        "zone_high": D("4035"), "sl": "4075", "signal_ts": SIG, "attempt_number": 1,
        "events": [{"ts": SIG + 120, "instruction_type": "EXPLICIT_FULL_EXIT",
                    "message_id": 91002}]}
eng = EG.FollowerEngine(camp, bars, "LANE_A", CONST)
res = eng.run()
ok(res["campaign_state"] == "CLOSED", "B: EXPLICIT_FULL_EXIT closes the campaign")
ok(any(s["reason"] == "P13_FINAL_CLOSE" for s in res["slices"]),
   "B: remaining filled quantity banked at close (P13)")
ok(any(t.get("rule") == "P14" or "P14" in str(t.get("rule")) for t in res["transitions"]
       if "CANCEL" in str(t.get("event", "")) + str(t.get("detail", ""))) or
   any(l["state"] == "CANCELLED" for l in res["legs"]),
   "B: unfilled resting entries cancelled per constitution terminal rule (P14)")
ok(sum(1 for l in res["legs"] if l["state"] == "FILLED") >= 1, "B: at least one leg had filled")

# ---------------- Part C+D: exact-sequence isolated replay --------------------------------------
TMP = tempfile.mkdtemp(prefix="fe_replay_")
DB = os.path.join(TMP, "ev.db")
FWD = os.path.join(TMP, "fwd.jsonl")
ILOG = os.path.join(TMP, "ingest.jsonl")

W.FWD_LEDGER = FWD
W.CURSOR_PATH = os.path.join(TMP, "wire_cursor.json")
W.CARD_DIR = os.path.join(TMP, "cards")
W.FOLLOWER_LEDGER = os.path.join(TMP, "follower.jsonl")
es.PRE_TRADE_LEDGER = ew.snapshots.es.PRE_TRADE_LEDGER = os.path.join(TMP, "pre.jsonl")
es.BLIND_HYP_LEDGER = os.path.join(TMP, "blind.jsonl")
es.MGMT_LEDGER = os.path.join(TMP, "mgmt.jsonl")
es.SECONDFEED_LEDGER = os.path.join(TMP, "sf.jsonl")
es.COVERAGE_LEDGER = os.path.join(TMP, "cov.jsonl")
es.FORWARD_LEDGER = FWD
ew.FWD_LEDGER = FWD
ew.INGEST_LOG = ILOG
ew.CURSOR = os.path.join(TMP, "watcher_cursor.json")
ew.EVIDENCE_DB = DB
ew.ENTRY_REFUSAL_LEDGER = os.path.join(TMP, "entry_refusals.jsonl")
_sr.ROUTER_FREEZE_LEDGER = os.path.join(TMP, "router_freeze.jsonl")
_sr.RECORD_CLASS_OVERRIDE = "SYNTHETIC_INTEGRATION_TEST"          # isolation seam (documented)
ew._ranking_pack = lambda sid, c, m, cur: f"RANK_STUB({sid})"     # side lane, not under test


def iso(ts):
    return datetime.fromtimestamp(ts, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


con = sqlite3.connect(DB)
con.execute("""CREATE TABLE prospective_message_evidence(
  rowseq INTEGER PRIMARY KEY AUTOINCREMENT,
  telegram_message_id TEXT, telegram_posted_at_utc TEXT, listener_received_at_utc TEXT,
  raw_text TEXT, raw_text_hash TEXT, message_event_type TEXT, message_revision_number INTEGER,
  telegram_sender_username TEXT, telegram_edited_at_utc TEXT)""")


def add(mid, ts, text):
    con.execute("INSERT INTO prospective_message_evidence "
                "(telegram_message_id, telegram_posted_at_utc, listener_received_at_utc, raw_text, "
                "raw_text_hash, message_event_type, message_revision_number, telegram_sender_username) "
                "VALUES(?,?,?,?,?,?,?,?)",
                (str(mid), iso(ts), iso(ts + 1), text, format(mid, "x") * 8, "CREATED", 1,
                 "seascalperfarouk"))
    con.commit()


T0 = SIG
with open(ILOG, "w", encoding="utf-8") as fh:                     # causal bars only (ts < events)
    for i in range(40):
        t = T0 - (40 - i) * 60
        fh.write(json.dumps({"schema": "market_event_v0_1", "kind": "ACCEPTED", "event_ts": t,
                             "provider": "PEPPERSTONE_TV_BAR_FEED", "revision": 1,
                             "logical_hash": f"rp{i}",
                             "bar": {"instrument": "XAUUSD", "provider": "PEPPERSTONE_TV_BAR_FEED",
                                     "timeframe": "1m", "event_ts": t, "receive_ts": t + 60,
                                     "open": "4030.0", "high": "4031.0", "low": "4029.0",
                                     "close": "4030.5", "bid": None, "ask": None,
                                     "source_id": "rp", "sequence": i, "revision": 1}}) + "\n")

# seed CLOSED historical F001/F002 (fallback bait — must never be selected)
with open(FWD, "w", encoding="utf-8") as fh:
    for old_sid, old_mid in (("XAU-F001-20260714", 45713), ("XAU-F002-20260714", 45716)):
        fh.write(json.dumps({
            "record_type": "XAU_F_SETUP", "setup_id": old_sid, "revision": 1,
            "message_ids": [old_mid], "timestamp_utc": iso(T0 - 2 * 86400),
            "direction": "SHORT", "entry_zone": "4084-4094",
            "sl": "4144 (posted follower stop)", "frozen_evidence_sha256": "0" * 64,
            "detector_v0_2": {"review_label": "X"}, "detector_v0_3": {"review_label": "X"},
            "detector_v0_2_label": "X", "detector_score": 0,
            "scoring_features_used": {"attempt_number": 1},
            "management_timing_8c": {"instruction_events": [
                {"instruction_type": "FINAL_CLOSE", "message_id": old_mid + 1,
                 "timestamp_utc": iso(T0 - 2 * 86400 + 3600)}]},
            "pre_mark_comparison": {},
            "review_only": True, "executable": False, "trade_ready": False,
            "observation_only": True}) + "\n")

json.dump({"last_processed_id": 69999, "fail_counts": {}},
          open(W.CURSOR_PATH, "w", encoding="utf-8"))

ENTRY_F003 = HDR + "`Whale` XAUUSD Sell : 4025–4035\nStop Loss: 4075\n\nLOW LOT"
ENTRY_F004 = HDR + "`Whale` XAUUSD Sell Zone: 4003–4014\nStop Loss: 4027"

print("== D: exact-sequence replay (real 2026-07-16 ordering pattern)")
# A/B. F003' entry arrives; the WATCHER sees it BEFORE the wire has written the setup
add(70001, T0, ENTRY_F003)
a = ew.run_cycle(db_path=DB, now_ts=T0 + 5)
ok(any("ENTRY_DEFERRED_WAITING_FOR_SETUP(70001)" in x for x in a),
   "D: watcher saw entry first -> deferred (the race, now safe)")
# C. wire writes the setup later (its own poll)
acts = dict(W.run_cycle(db_path=DB))
ok(acts.get("70001/1", "").startswith("PROPOSAL_EMITTED(XAU-F003"),
   "D: wire created the campaign exactly once")
SID3 = acts["70001/1"].split("(")[1].rstrip(")")
# D. watcher retries and completes exactly one PRE lifecycle
a = ew.run_cycle(db_path=DB, now_ts=T0 + 50)
ok(any(f"ENTRY_PRE_LIFECYCLE_COMPLETED(70001 -> {SID3})" in x for x in a),
   "D: watcher retry completed ONE PRE lifecycle for F003'")
pre = [json.loads(l) for l in open(es.PRE_TRADE_LEDGER, encoding="utf-8")]
ok(len(pre) == 1 and pre[0]["setup_id"] == SID3, "D: exactly one PRE snapshot so far")

# E. F003' receives "full exit" -> unique correlation -> terminal
add(70002, T0 + 1800, HDR + "`Whale` full exit")
acts = dict(W.run_cycle(db_path=DB))
ok(acts.get("70002/1", "").startswith(f"CARD_UPDATED({SID3}"),
   "D: full exit correlated uniquely to F003'")
setups, open_ids, paused = W.load_campaign_state()
ok(SID3 not in open_ids, "D: F003' CLOSED by EXPLICIT_FULL_EXIT (before F004 entry)")

# F. F004' entry arrives
add(70003, T0 + 7200, ENTRY_F004)
acts = dict(W.run_cycle(db_path=DB))
ok(acts.get("70003/1", "").startswith("PROPOSAL_EMITTED(XAU-F004"),
   "D: F004' campaign created exactly once")
SID4 = acts["70003/1"].split("(")[1].rstrip(")")
a = ew.run_cycle(db_path=DB, now_ts=T0 + 7300)
ok(any(f"ENTRY_PRE_LIFECYCLE_COMPLETED(70003 -> {SID4})" in x for x in a),
   "D: F004' PRE lifecycle completed exactly once")

# G. F004' management: TP1 / close worst + SL to entry / SL to entry again / take 50%
mgmt = [(70004, T0 + 7600, "`Whale` 50 pips in profit take TP1 now."),
        (70005, T0 + 7800, "`Whale` close worst hold best sl to entry"),
        (70006, T0 + 7900, "`Whale` move sl to entry again"),
        (70007, T0 + 8400, "`Whale` take 50% off")]
for mid, ts, text in mgmt:
    add(mid, ts, HDR + text)
acts = dict(W.run_cycle(db_path=DB))
for mid, _, _ in mgmt:
    ok(acts.get(f"{mid}/1", "").startswith(f"CARD_UPDATED({SID4}"),
       f"D: mgmt {mid} correlated uniquely to F004' (no pause, no orphan)")

# invariants
fwd = [json.loads(l) for l in open(FWD, encoding="utf-8")]
sets = {}
for r in fwd:
    if r.get("record_type") == "XAU_F_SETUP":
        sets.setdefault(r["setup_id"], []).append(r)
ok(len(sets[SID3]) >= 1 and len({r["revision"] for r in sets[SID3]}) == len(sets[SID3]),
   "D: no duplicate F003' campaign (revisions strictly distinct)")
ok(len([r for r in sets[SID4] if r["revision"] == 1]) == 1, "D: no duplicate F004' campaign")
pre = [json.loads(l) for l in open(es.PRE_TRADE_LEDGER, encoding="utf-8")]
ok(len(pre) == 2, "D: both entries -> exactly one PRE lifecycle each")
ok(not any(p["setup_id"] in ("XAU-F001-20260714", "XAU-F002-20260714") for p in pre),
   "D: no F001/F002 fallback in evidence layer")
ok(not any(r.get("setup_id") in ("XAU-F001-20260714", "XAU-F002-20260714")
           for r in fwd if r.get("record_type") in ("XAU_F_CAMPAIGN_PAUSE",)
           ) and all("F001" not in str(acts.get(f"{mid}/1")) and "F002" not in str(acts.get(f"{mid}/1"))
                     for mid, _, _ in mgmt),
   "D: no F001/F002 fallback in wire correlation")
frz = [json.loads(l) for l in open(_sr.ROUTER_FREEZE_LEDGER, encoding="utf-8")] \
    if os.path.exists(_sr.ROUTER_FREEZE_LEDGER) else []
ok(len(frz) == len({r["setup_id"] for r in frz}), "D: no duplicate freezes")
for r in frz:
    ok(r["record_class"] == "SYNTHETIC_INTEGRATION_TEST" and r["eligible_for_training"] is False,
       f"D: freeze {r['setup_id']} isolated synthetic + training-ineligible")
    ca = r["causality"]
    ok(ca["latest_source_bar_close_time"] <= ca["decision_timestamp"],
       f"D: freeze {r['setup_id']} causal cutoff (no future bars)")
ok(all(p.startswith(TMP) for p in (FWD, W.FOLLOWER_LEDGER, W.CARD_DIR, es.PRE_TRADE_LEDGER,
                                   _sr.ROUTER_FREEZE_LEDGER, ew.ENTRY_REFUSAL_LEDGER)),
   "D: hermetic — every writer redirected into the temp world")
_sr.RECORD_CLASS_OVERRIDE = None
con.close()
print(f"\nPASS {PASS} full-exit + exact-sequence replay checks")
