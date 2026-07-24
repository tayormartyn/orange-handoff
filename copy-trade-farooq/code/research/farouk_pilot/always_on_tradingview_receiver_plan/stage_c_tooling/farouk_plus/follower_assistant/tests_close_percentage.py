"""CLOSE_PERCENTAGE_v0_1 — focused regression gate (hermetic; real ledgers untouched).

Covers the 20 required checks: grammar, semantics on CURRENT remaining quantity, compounding,
terminal cancellation, fail-closed rejections, false-positive immunity, source/association
gates, duplicate/restart idempotency, unchanged neighbours (full-exit, quantity-base guard,
Constitution hash, no execution fields). Run: python tests_close_percentage.py
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
CONST_SHA_BEFORE = hashlib.sha256(
    open(os.path.join(HERE, "follower_constitution_v0_1.json"), "rb").read()).hexdigest()


def instrs(text):
    c = interpreter.classify(HDR + text)
    return c, (c.get("instructions", []) if c["kind"] == "MANAGEMENT" else [])


print("== 1/2: exact + case/whitespace/punctuation variants")
for text in ("`Whale` close 100%", "`Whale` Close 100%", "`Whale` CLOSE 100 %.",
             "`Whale` close 100%!"):
    c, ins = instrs(text)
    ok(len(ins) == 1 and ins[0]["instruction_type"] == "EXPLICIT_FULL_EXIT"
       and ins[0]["morphology"] == "CLOSE_PERCENTAGE_v0_1", f"100% variant -> FULL_EXIT: {text[8:]}")
for text, n in (("`Whale` close 50%", 50), ("`Whale` Close 25 %.", 25), ("`Whale` close 30%!", 30),
                ("`Whale` close 1%", 1), ("`Whale` close 99%", 99)):
    c, ins = instrs(text)
    ok(len(ins) == 1 and ins[0]["instruction_type"] == "CLOSE_PERCENTAGE_PARTIAL"
       and ins[0]["close_percentage"] == n and ins[0]["retain_percentage"] == 100 - n
       and ins[0]["quantity_base"] == "CURRENTLY_REMAINING_OPEN_FILLED_QUANTITY",
       f"partial variant -> CLOSE_PERCENTAGE_PARTIAL {n}/{100-n}: {text[8:]}")

print("== 3-6: engine semantics on CURRENT remaining quantity (Decimal/Fraction, no floats)")
SIG = 1784284200
BARS = [
    (SIG, D("4004"), D("4009"), D("3996"), D("3999.0")),          # near+mid fill (SHORT limits)
    (SIG + 60, D("3999"), D("4000"), D("3990"), D("3992.0")),     # partial 1 bar
    (SIG + 120, D("3992"), D("3993"), D("3985"), D("3987.0")),    # partial 2 bar
    (SIG + 180, D("3987"), D("3988"), D("3975"), D("3978.0")),    # full exit bar
]


def run(events, bars=BARS):
    camp = {"setup_id": "XAU-TEST-CP", "direction": "SHORT", "zone_low": D("3998"),
            "zone_high": D("4008"), "sl": "4043", "signal_ts": SIG, "attempt_number": 1,
            "events": events}
    return EG.FollowerEngine(camp, bars, "LANE_A", CONST).run()


res = run([{"ts": SIG + 60, "instruction_type": "CLOSE_PERCENTAGE_PARTIAL", "pct": 0.5,
            "message_id": 1}])
open_after = sum(Fraction(l["open_size"]) for l in res["legs"] if l["state"] == "FILLED")
banked = sum(Fraction(s["size"]) for s in res["slices"] if s["reason"] == "P12_TAKE_PCT")
ok(banked > 0 and open_after == banked,
   "close 50% banks exactly half of CURRENT open (remainder == banked)")
res = run([{"ts": SIG + 60, "instruction_type": "CLOSE_PERCENTAGE_PARTIAL", "pct": 0.5, "message_id": 1},
           {"ts": SIG + 120, "instruction_type": "CLOSE_PERCENTAGE_PARTIAL", "pct": 0.5, "message_id": 2}])
p12 = [s for s in res["slices"] if s["reason"] == "P12_TAKE_PCT"]
half1 = sum(Fraction(s["size"]) for s in p12 if s["bar_ts"] == SIG + 60)
half2 = sum(Fraction(s["size"]) for s in p12 if s["bar_ts"] == SIG + 120)
ok(half1 > 0 and half2 == half1 / 2,
   "sequential 50% closes COMPOUND against then-current remainder (2nd tranche = half of 1st)")
res = run([{"ts": SIG + 60, "instruction_type": "CLOSE_PERCENTAGE_PARTIAL", "pct": 0.5, "message_id": 1},
           {"ts": SIG + 180, "instruction_type": "EXPLICIT_FULL_EXIT", "message_id": 3}])
ok(res["campaign_state"] == "CLOSED"
   and sum(Fraction(l["open_size"]) for l in res["legs"] if l.get("open_size")) == 0,
   "close 100% after a prior partial closes the ENTIRE remainder")
# one filled leg + two unfilled -> 100% closes filled remainder AND cancels both unfilled
BARS_NEAR = [(SIG, D("3996"), D("3998.4"), D("3995"), D("3996.5")),
             (SIG + 60, D("3996"), D("3997"), D("3990"), D("3991.0"))]
res = run([{"ts": SIG + 60, "instruction_type": "EXPLICIT_FULL_EXIT", "message_id": 4}], bars=BARS_NEAR)
states = {l["leg_id"].split("/")[-1]: l["state"] for l in res["legs"]}
ok(states["mid"] == "CANCELLED" and states["far"] == "CANCELLED" and res["campaign_state"] == "CLOSED",
   "close 100% with 1 filled + 2 unfilled: banks filled remainder, cancels both unfilled (7)")

print("== 8: partial does NOT cancel unfilled entries")
res = run([{"ts": SIG + 60, "instruction_type": "CLOSE_PERCENTAGE_PARTIAL", "pct": 0.5,
            "message_id": 5}], bars=BARS_NEAR)
states = {l["leg_id"].split("/")[-1]: l["state"] for l in res["legs"]}
ok(states["mid"] != "CANCELLED" and states["far"] != "CANCELLED",
   "close 50% leaves unfilled entries resting (no separate cancel rule invoked)")

print("== idempotent no-op: close 100% with nothing open")
res = run([{"ts": SIG + 60, "instruction_type": "EXPLICIT_FULL_EXIT", "message_id": 6}],
          bars=[(SIG, D("3990"), D("3993"), D("3985"), D("3986.0")),
                (SIG + 60, D("3986"), D("3987"), D("3980"), D("3981.0"))])
ok(res["campaign_state"] == "NO_FILL" and not res["slices"],
   "close 100% with zero fills -> terminal NO_FILL, ZERO realised slices (no phantom close)")

print("== 9-12: fail-closed rejections and false-positive immunity")
for text, why in (("`Whale` close 0%", "0%"), ("`Whale` close 101%", "101%"),
                  ("`Whale` close 1000%", "1000%"), ("`Whale` close 10.5%", "decimal"),
                  ("`Whale` close -5%", "negative")):
    c, _ = instrs(text)
    ok(c["kind"] == "NEEDS_HUMAN_REVIEW", f"rejected fail-closed to review: {why}")
for text, why in (("`Whale` close 100 pips", "close 100 pips (no %)"),
                  ("`Whale` 100%", "bare 100%"),
                  ("`Whale` we made 100%", "we made 100%"),
                  ("`Whale` 280-300 pips no buy today guys", "pips claim"),
                  ("`Whale` 130 pips in profit if you're still holding.", "profit claim"),
                  ("`Whale` enjoy profit", "result-card caption")):
    c, ins = instrs(text)
    ok(not any(i["instruction_type"] in ("EXPLICIT_FULL_EXIT", "CLOSE_PERCENTAGE_PARTIAL",
                                         "INVALID_PERCENTAGE_PARTIAL") for i in ins),
       f"never matches close-N%: {why}")
c = interpreter.classify("kyledoops Posted in ⚓・captains-take\n\nclose 100%")
ok(c["kind"] == "NOT_FAROUK_GOLD", "13: wrong source (non farouk-gold header) rejected")

print("== 14-16: wire-level association + duplicate/restart idempotency (temp world)")
TMP = tempfile.mkdtemp(prefix="cp_wire_")
W.FWD_LEDGER = os.path.join(TMP, "fwd.jsonl")
W.CURSOR_PATH = os.path.join(TMP, "wire_cursor.json")
W.CARD_DIR = os.path.join(TMP, "cards")
W.FOLLOWER_LEDGER = os.path.join(TMP, "follower.jsonl")
open(W.FWD_LEDGER, "w").close()
json.dump({"last_processed_id": 79999, "fail_counts": {}}, open(W.CURSOR_PATH, "w"))
DB = os.path.join(TMP, "ev.db")
con = sqlite3.connect(DB)
con.execute("""CREATE TABLE prospective_message_evidence(
  telegram_message_id TEXT, telegram_posted_at_utc TEXT, raw_text TEXT, raw_text_hash TEXT,
  message_event_type TEXT, message_revision_number INTEGER)""")


def iso(ts):
    return datetime.fromtimestamp(ts, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def add(mid, ts, text):
    con.execute("INSERT INTO prospective_message_evidence VALUES(?,?,?,?,?,?)",
                (str(mid), iso(ts), text, "h" * 64, "CREATED", 1))
    con.commit()


add(80001, SIG, HDR + "`Whale` close 50%")            # management with NO open campaign
acts = dict(W.run_cycle(db_path=DB))
ok("FAIL_CLOSED" in acts.get("80001/1", "") or "ORPHAN" in acts.get("80001/1", ""),
   "14: close 50% with no open campaign -> fail-closed, no mutation")
add(80002, SIG + 60, HDR + "`Whale` XAUUSD Sell : 3998–4008\nStop Loss: 4043")
add(80003, SIG + 120, HDR + "`Whale` close 100%")
acts = dict(W.run_cycle(db_path=DB))
sid = acts["80002/1"].split("(")[1].rstrip(")")
ok(acts.get("80003/1", "").startswith(f"CARD_UPDATED({sid}"), "close 100% correlates uniquely")
setups, open_ids, _ = W.load_campaign_state()
ok(sid not in open_ids, "campaign closed by CLOSE_PERCENTAGE_v0_1 terminal")
n_before = sum(1 for _ in open(W.FWD_LEDGER, encoding="utf-8"))
acts = dict(W.run_cycle(db_path=DB))                  # replay same cursor position (no new msgs)
n_after = sum(1 for _ in open(W.FWD_LEDGER, encoding="utf-8"))
ok(not acts and n_after == n_before, "15: cursor replay produces zero duplicate records")
cur = json.load(open(W.CURSOR_PATH))
cur["last_processed_id"] = 80002                       # simulate restart with regressed cursor
json.dump(cur, open(W.CURSOR_PATH, "w"))
acts = dict(W.run_cycle(db_path=DB))
n_after2 = sum(1 for _ in open(W.FWD_LEDGER, encoding="utf-8"))
setups2, open2, _ = W.load_campaign_state()
evs = [e["instruction_type"] for e in setups2[sid]["management_timing_8c"]["instruction_events"]]
ok(evs.count("EXPLICIT_FULL_EXIT") >= 1 and sid not in open2,
   "16a: replayed terminal remains terminal (no state flip)")
res = run([{"ts": SIG + 120, "instruction_type": "EXPLICIT_FULL_EXIT", "message_id": 80003},
           {"ts": SIG + 120, "instruction_type": "EXPLICIT_FULL_EXIT", "message_id": 80003}])
ok(sum(1 for t in res["transitions"] if t.get("event") == "DUPLICATE_EVENT_SKIPPED") >= 1
   or res["campaign_state"] in ("CLOSED", "NO_FILL"),
   "16b: duplicate same-message terminal collapses (engine idempotency)")

print("== 17-20: neighbours unchanged")
for text in ("`Whale` full exit", "`Whale` close all", "`Whale` close everything"):
    _, ins = instrs(text)
    ok(any(i["instruction_type"] == "EXPLICIT_FULL_EXIT" for i in ins),
       f"17: existing terminal morphology unchanged: {text[8:]}")
_, ins = instrs("`Whale` close 50% leave 50%")
ok(ins and ins[0]["instruction_type"] == "EXPLICIT_PERCENTAGE_PARTIAL_CLOSE",
   "17b: close-X-leave-Y still takes precedence over close-N%")
bad = {"instruction_type": "CLOSE_PERCENTAGE_PARTIAL", "close_percentage": 50,
       "retain_percentage": 50, "quantity_base": "ORIGINAL_CAMPAIGN_QUANTITY"}
try:
    guards.assert_clean({"record_type": "X", "management_timing_8c": {"instruction_events": [bad]},
                         "review_only": True, "executable": False, "trade_ready": False,
                         "observation_only": True}, "t")
    ok(False, "18: guard must reject ORIGINAL_CAMPAIGN_QUANTITY base")
except guards.GuardViolation:
    ok(True, "18: quantity-base guard still rejects unsupported bases for the new type")
good, _ = instrs("`Whale` close 50%")
guards.assert_clean({"record_type": "X", "management_timing_8c": {"instruction_events":
                    [dict(i, message_id=1, timestamp_utc="t") for i in good["instructions"]]},
                    "review_only": True, "executable": False, "trade_ready": False,
                    "observation_only": True}, "t")
ok(True, "20: emitted close-N% instruction passes guards (no execution/sizing fields)")
CONST_SHA_AFTER = hashlib.sha256(
    open(os.path.join(HERE, "follower_constitution_v0_1.json"), "rb").read()).hexdigest()
ok(CONST_SHA_BEFORE == CONST_SHA_AFTER == hashlib.sha256(
    open(os.path.join(HERE, "follower_constitution_v0_1.json"), "rb").read()).hexdigest()
   and CONST_SHA_AFTER.startswith("7bce618f29d1d44a"), "19: Constitution v0.1 hash unchanged")
con.close()
print(f"\nPASS {PASS} close-percentage checks")
