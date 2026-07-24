"""EXPLICIT_PERCENTAGE_PARTIAL_CLOSE engine mapping v0.1 + COMPOUND_PRECEDENCE_v0_1 — the
30-point focused gate (hermetic; real ledgers untouched; F005/Constitution immutability proven
in-suite). Run: python tests_explicit_partial_close.py
"""
from __future__ import annotations

import hashlib
import io
import json
import os
import sqlite3
import sys
import tempfile
from datetime import datetime, timezone
from decimal import Decimal as D
from fractions import Fraction

HERE = os.path.dirname(os.path.abspath(__file__))
MT = os.path.join(HERE, "market_tracker")
for p in (HERE, MT):
    sys.path.insert(0, p)
import interpreter                                                # noqa: E402
import guards                                                     # noqa: E402
import engine as EG                                               # noqa: E402
import run_fixtures                                               # noqa: E402
import live_wire as W                                             # noqa: E402

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
PASS = 0


def ok(c, name):
    global PASS
    assert c, f"FAIL: {name}"
    PASS += 1
    print(f"  ok {PASS}: {name}")


HDR = "seascalperfarouk Posted in 🪙・gold-trades\n\n"
CONST = json.load(open(os.path.join(HERE, "follower_constitution_v0_1.json"), encoding="utf-8"))
FP = os.path.dirname(HERE)
EL = os.path.join(HERE, "evidence_layer")
IMMUTABLE = {
    "f005_pre": hashlib.sha256(open(os.path.join(EL, "pre_trade_snapshots_v0_1.jsonl"), "rb")
                               .read().splitlines()[5]).hexdigest(),
    "f005_hyp": hashlib.sha256(open(os.path.join(EL, "blind_hypotheses_v0_1.jsonl"), "rb")
                               .read().splitlines()[1]).hexdigest(),
    "f005_freeze": json.loads(open(os.path.join(EL, "router_freeze_v0_1.jsonl"), encoding="utf-8")
                              .read().splitlines()[1])["logical_hash"],
    "const": hashlib.sha256(open(os.path.join(HERE, "follower_constitution_v0_1.json"), "rb")
                            .read()).hexdigest(),
    "fwd": hashlib.sha256(open(os.path.join(FP, "forward_validation_ledger_v0_2.jsonl"), "rb")
                          .read()).hexdigest(),
}


def instrs(text):
    c = interpreter.classify(HDR + text)
    return c, (c.get("instructions", []) if c["kind"] == "MANAGEMENT" else [])


SIG = 1784284200
BARS = [
    (SIG, D("4004"), D("4009"), D("3996"), D("3999.0")),          # near+mid fill (SHORT)
    (SIG + 60, D("3999"), D("4000"), D("3990"), D("3992.0")),
    (SIG + 120, D("3992"), D("3993"), D("3985"), D("3987.0")),
]


def run(events, bars=BARS):
    camp = {"setup_id": "XAU-TEST-EPPC", "direction": "SHORT", "zone_low": D("3998"),
            "zone_high": D("4008"), "sl": "4043", "signal_ts": SIG, "attempt_number": 1,
            "events": events}
    return EG.FollowerEngine(camp, bars, "LANE_A", CONST).run()


def eppc(cp, rp, ts=SIG + 60, mid=1, base="CURRENTLY_REMAINING_OPEN_FILLED_QUANTITY", pct=None):
    return {"ts": ts, "instruction_type": "EXPLICIT_PERCENTAGE_PARTIAL_CLOSE",
            "close_percentage": cp, "retain_percentage": rp, "quantity_base": base,
            "pct": pct if pct is not None else (cp / 100.0 if isinstance(cp, int) else None),
            "message_id": mid}


def open_frac(res):
    return sum(Fraction(l["open_size"]) for l in res["legs"] if l["state"] == "FILLED")


def banked_frac(res):
    return sum(Fraction(s["size"]) for s in res["slices"] if s["reason"] == "P12_TAKE_PCT")


print("== 1/2/26: close-X-leave-Y engine application on CURRENT remaining, exact fractions")
BASE_OPEN = open_frac(run([]))                                     # exposure with no management
res = run([eppc(50, 50)])
ok(res["campaign_state"] != "PAUSED_NEEDS_HUMAN_REVIEW", "1: EPPC no longer P20-pauses")
ok(BASE_OPEN > 0 and banked_frac(res) == BASE_OPEN / 2 and open_frac(res) == BASE_OPEN / 2,
   f"1: close 50% leave 50% from {BASE_OPEN} open -> banked exactly half, remaining exactly half")
res = run([eppc(30, 70)])
ok(banked_frac(res) == BASE_OPEN * Fraction(30, 100)
   and open_frac(res) == BASE_OPEN * Fraction(70, 100),
   "2: close 30% leave 70% -> banked exactly 30% of current open, remaining exactly 70%")

print("== 3/25: compounding + one-reduction-per-message")
res = run([eppc(50, 50, ts=SIG + 60, mid=1), eppc(50, 50, ts=SIG + 120, mid=2)])
tr = [s for s in res["slices"] if s["reason"] == "P12_TAKE_PCT"]
h1 = sum(Fraction(s["size"]) for s in tr if s["bar_ts"] == SIG + 60)
h2 = sum(Fraction(s["size"]) for s in tr if s["bar_ts"] == SIG + 120)
ok(h2 == h1 / 2, "3: second compound partial applies to the THEN-current remainder")
_, ins = instrs("`Whale` take 50% off and close 25%")
red = [i for i in ins if i["instruction_type"] in
       ("TAKE_PCT_OFF", "CLOSE_PERCENTAGE_PARTIAL", "EXPLICIT_PERCENTAGE_PARTIAL_CLOSE")]
ok(len(red) == 1, "25: two percentage phrasings in one message -> exactly ONE reduction emitted")
_, ins = instrs("`Whale` close 90% leave 10% for 4020")
red = [i for i in ins if "PARTIAL" in i["instruction_type"] or i["instruction_type"] == "TAKE_PCT_OFF"]
ok(len(red) == 1 and red[0]["instruction_type"] == "EXPLICIT_PERCENTAGE_PARTIAL_CLOSE"
   and red[0]["pct"] == 0.9, "25b: authentic 45561 wording -> single EPPC (close-N% suppressed)")

print("== 4/5/6/24: quantity-base rules (original vs remaining)")
res = run([eppc(50, 50, base="ORIGINAL_CAMPAIGN_QUANTITY")])
ok(res["campaign_state"] == "PAUSED_NEEDS_HUMAN_REVIEW" and banked_frac(res) == 0,
   "4/24: ORIGINAL base -> engine fails closed, zero exposure change")
res = run([eppc(50, 50, base="CURRENTLY_REMAINING_OPEN_FILLED_QUANTITY")])
ok(banked_frac(res) == BASE_OPEN / 2, "5: CURRENT_REMAINING base applies")
res = run([eppc(50, 50, base=None)])
ok(res["campaign_state"] == "PAUSED_NEEDS_HUMAN_REVIEW",
   "6: missing quantity base -> engine fails closed (explicit base REQUIRED)")
bad = {"instruction_type": "EXPLICIT_PERCENTAGE_PARTIAL_CLOSE", "close_percentage": 50,
       "retain_percentage": 50}
try:
    guards.assert_clean({"record_type": "X", "management_timing_8c": {"instruction_events": [bad]},
                         "review_only": True, "executable": False, "trade_ready": False,
                         "observation_only": True}, "t")
    ok(False, "6b")
except guards.GuardViolation:
    ok(True, "6b: guard blocks a base-less EPPC record at the wire layer too")

print("== 7/9/10/11: invalid percentages fail closed (interpreter + engine)")
for text, why in (("`Whale` close 60% leave 60%", "60+60"), ("`Whale` close 0% leave 100%", "0%"),
                  ("`Whale` close 110 leave -10", "110/-10"),
                  ("`Whale` close 50.5% leave 49.5%", "decimals")):
    c, _ = instrs(text)
    ok(c["kind"] == "NEEDS_HUMAN_REVIEW", f"7/9/10/11: {why} -> quarantine, no instruction")
res = run([eppc(60, 60)])
ok(res["campaign_state"] == "PAUSED_NEEDS_HUMAN_REVIEW" and banked_frac(res) == 0,
   "7b: crafted non-reconciling event -> engine pause, no exposure change")
res = run([eppc(50, 50, pct=0.8)])
ok(res["campaign_state"] == "PAUSED_NEEDS_HUMAN_REVIEW",
   "7c: pct field contradicting close_percentage -> fail closed (no silent choice)")

print("== 8: over-close impossible")
res = run([eppc(99, 1)])
ok(banked_frac(res) <= BASE_OPEN and open_frac(res) >= 0,
   "8: close amount bounded by open exposure, no negative exposure")

print("== 16/27: no filled leg + runner preservation")
NOFILL = [(SIG, D("3990"), D("3993"), D("3985"), D("3986.0")),
          (SIG + 60, D("3986"), D("3987"), D("3980"), D("3981.0"))]
res = run([eppc(50, 50)], bars=NOFILL)
ok(res["campaign_state"] != "PAUSED_NEEDS_HUMAN_REVIEW" and banked_frac(res) == 0,
   "16: EPPC with no open filled leg -> not-applicable log, no pause, no exposure change")
res = run([eppc(50, 50)],
          bars=[(SIG, D("3996"), D("3998.4"), D("3995"), D("3996.5")),
                (SIG + 60, D("3996"), D("3997"), D("3990"), D("3991.0"))])
states = {l["leg_id"].split("/")[-1]: l["state"] for l in res["legs"]}
ok(states["mid"] != "CANCELLED" and states["far"] != "CANCELLED"
   and open_frac(res) > 0, "27: partial preserves runner AND leaves unfilled entries resting")

print("== 21/22/23: compound precedence")
_, ins = instrs("`Whale` close 50% and cancel the limit orders")
tps = [i["instruction_type"] for i in ins]
ok("CLOSE_PERCENTAGE_PARTIAL" in tps and "CANCEL_LIMITS" in tps,
   "21: close % + cancel limits co-emitted")
_, ins = instrs("`Whale` close 50% and move sl to entry")
tps = [i["instruction_type"] for i in ins]
ok("CLOSE_PERCENTAGE_PARTIAL" in tps and "SL_TO_ENTRY" in tps, "22: close % + SL-to-entry co-emitted")
_, ins = instrs("`Whale` close 50% leave 50% ... actually full exit")
tps = [i["instruction_type"] for i in ins]
ok("EXPLICIT_FULL_EXIT" in tps, "23a: terminal co-emitted with reduction")
res = run([{"ts": SIG + 60, "instruction_type": "EXPLICIT_PERCENTAGE_PARTIAL_CLOSE",
            "close_percentage": 50, "retain_percentage": 50, "pct": 0.5,
            "quantity_base": "CURRENTLY_REMAINING_OPEN_FILLED_QUANTITY", "message_id": 9},
           {"ts": SIG + 60, "instruction_type": "EXPLICIT_FULL_EXIT", "message_id": 9}])
ok(res["campaign_state"] == "CLOSED" and open_frac(res) == 0
   and not [s for s in res["slices"] if s["reason"] == "P12_TAKE_PCT"],
   "23b: terminal precedence — full exit applies FIRST, no separate partial reduction")

print("== 12/13/14 + replay regression: idempotency (wire temp world)")
TMP = tempfile.mkdtemp(prefix="eppc_wire_")
W.FWD_LEDGER = os.path.join(TMP, "fwd.jsonl")
W.CURSOR_PATH = os.path.join(TMP, "wire_cursor.json")
W.CARD_DIR = os.path.join(TMP, "cards")
W.FOLLOWER_LEDGER = os.path.join(TMP, "follower.jsonl")
open(W.FWD_LEDGER, "w").close()
json.dump({"last_processed_id": 89999, "fail_counts": {}}, open(W.CURSOR_PATH, "w"))
DB = os.path.join(TMP, "ev.db")
con = sqlite3.connect(DB)
con.execute("""CREATE TABLE prospective_message_evidence(
  telegram_message_id TEXT, telegram_posted_at_utc TEXT, raw_text TEXT, raw_text_hash TEXT,
  message_event_type TEXT, message_revision_number INTEGER)""")


def iso(ts):
    return datetime.fromtimestamp(ts, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def add(mid, ts, text, evt="CREATED", rev=1):
    con.execute("INSERT INTO prospective_message_evidence VALUES(?,?,?,?,?,?)",
                (str(mid), iso(ts), text, "h" * 64, evt, rev))
    con.commit()


add(90000, SIG - 600, HDR + "`Whale` close 40% leave 60%")     # 17: before ANY campaign exists
add(90001, SIG, HDR + "`Whale` XAUUSD Sell : 3998–4008\nStop Loss: 4043")
add(90002, SIG + 120, HDR + "`Whale` close 50% leave 50%")
acts = dict(W.run_cycle(db_path=DB))
ok("FAIL_CLOSED" in acts.get("90000/1", ""), "17: EPPC before campaign creation -> fail-closed review")
sid = acts["90001/1"].split("(")[1].rstrip(")")
ok(acts.get("90002/1", "").startswith(f"CARD_UPDATED({sid}"), "EPPC correlates and records")
card = json.load(open(os.path.join(W.CARD_DIR, sid + ".json"), encoding="utf-8"))
ev = card["management_state"]["instruction_events"]
ok(any(e["instruction_type"] == "EXPLICIT_PERCENTAGE_PARTIAL_CLOSE" and e["message_id"] == 90002
       for e in ev), "28: proposal card carries the EPPC event (evidence/card consistency)")
n1 = sum(1 for _ in open(W.FWD_LEDGER, encoding="utf-8"))
acts = dict(W.run_cycle(db_path=DB))
n2 = sum(1 for _ in open(W.FWD_LEDGER, encoding="utf-8"))
ok(not acts and n1 == n2, "12: duplicate delivery (same cursor) -> zero new records")
setups, open_ids, _ = W.load_campaign_state()
rev_before = setups[sid]["revision"]
cur = json.load(open(W.CURSOR_PATH))
cur["last_processed_id"] = 90001
json.dump(cur, open(W.CURSOR_PATH, "w"))
W.run_cycle(db_path=DB)
setups2, _, _ = W.load_campaign_state()
evs = [e for e in setups2[sid]["management_timing_8c"]["instruction_events"]
       if e["instruction_type"] == "EXPLICIT_PERCENTAGE_PARTIAL_CLOSE"]
camp = run_fixtures.campaign_from_setup(setups2[sid])
eng_res = EG.FollowerEngine(camp, BARS, "LANE_A", CONST).run()
tranches = [s for s in eng_res["slices"] if s["reason"] == "P12_TAKE_PCT"]
ok(len(tranches) <= len({(s["bar_ts"], s["leg_id"]) for s in tranches}) + 0 and
   sum(1 for t in eng_res["transitions"] if t.get("event") == "DUPLICATE_EVENT_SKIPPED") >= (1 if len(evs) > 1 else 0),
   "14/replay: cursor replay -> engine collapses any duplicated event; at most ONE exposure transition")
add(90002, SIG + 180, HDR + "`Whale` close 50% leave 50% (edited)", evt="EDITED", rev=2)
n_pre_edit = sum(1 for _ in open(W.FWD_LEDGER, encoding="utf-8"))
s_pre, _, _ = W.load_campaign_state()
rev_pre_edit = s_pre[sid]["revision"]
acts = dict(W.run_cycle(db_path=DB))
n_post_edit = sum(1 for _ in open(W.FWD_LEDGER, encoding="utf-8"))
s_post, _, _ = W.load_campaign_state()
ok(n_post_edit == n_pre_edit and s_post[sid]["revision"] == rev_pre_edit
   and "CARD_UPDATED" not in str(acts.get("90002/2", "")),
   "13: edited duplicate of a consumed message -> NO second reduction, no new records "
   "(cursor excludes replays; edits of unconsumed ids take the explicit pause path)")

print("== 15/18: ambiguity + post-terminal")
add(90010, SIG + 300, HDR + "`Whale` XAUUSD Sell Zone: 3998–4008\nStop Loss: 4043")
add(90011, SIG + 360, HDR + "`Whale` close 50% leave 50%")
acts = dict(W.run_cycle(db_path=DB))
ok("FAIL_CLOSED" in acts.get("90011/1", "") or "PAUSE" in str(acts.get("90011/1", "")).upper()
   or "ambiguous" in str(acts.get("90011/1", "")),
   "15: two active campaigns -> ambiguous association fails closed")
add(90020, SIG + 420, HDR + "`Whale` close 100%")
add(90021, SIG + 480, HDR + "`Whale` close 20% leave 80%")
acts = dict(W.run_cycle(db_path=DB))
ok("FAIL_CLOSED" in str(acts.get("90021/1", "")) or "ORPHAN" in str(acts.get("90021/1", "")),
   "18: EPPC after terminal closure -> fail-closed/orphan, no mutation")

print("== 19/20: image-only + retrospective text cannot drive the engine")
c = interpreter.classify(None)
ok(c["kind"] == "NOT_FAROUK_GOLD", "19: image-only (no text) -> structurally NOT parseable")
c = interpreter.classify("terrilyn Posted in ⚓・captains-take\n\nclose 90% leave 10%")
ok(c["kind"] == "NOT_FAROUK_GOLD", "20: non-authorised source with EPPC wording -> rejected")

print("== 29/30: immutability")
now = {
    "f005_pre": hashlib.sha256(open(os.path.join(EL, "pre_trade_snapshots_v0_1.jsonl"), "rb")
                               .read().splitlines()[5]).hexdigest(),
    "f005_hyp": hashlib.sha256(open(os.path.join(EL, "blind_hypotheses_v0_1.jsonl"), "rb")
                               .read().splitlines()[1]).hexdigest(),
    "f005_freeze": json.loads(open(os.path.join(EL, "router_freeze_v0_1.jsonl"), encoding="utf-8")
                              .read().splitlines()[1])["logical_hash"],
    "const": hashlib.sha256(open(os.path.join(HERE, "follower_constitution_v0_1.json"), "rb")
                            .read()).hexdigest(),
    "fwd": hashlib.sha256(open(os.path.join(FP, "forward_validation_ledger_v0_2.jsonl"), "rb")
                          .read()).hexdigest(),
}
ok(now == IMMUTABLE, "29/30: F005 PRE/hypothesis/freeze + Constitution + real forward ledger "
   "byte-identical through the whole suite")
con.close()
print(f"\nPASS {PASS} explicit-partial-close checks")
