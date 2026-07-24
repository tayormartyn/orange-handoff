"""Deterministic tests for the Stage-1 live proposal wire (isolated temp world:
temp evidence DB, temp forward/follower ledgers, temp cursor/cards — the real
project files are never written by these tests)."""
from __future__ import annotations

import io
import json
import os
import shutil
import sqlite3
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import guards                                                    # noqa: E402
import interpreter                                               # noqa: E402
import live_wire                                                 # noqa: E402

PASS = 0


def ok(cond, name):
    global PASS
    assert cond, f"FAIL: {name}"
    PASS += 1


TMP = tempfile.mkdtemp(prefix="live_wire_test_")
DB = os.path.join(TMP, "evidence.db")
live_wire.FWD_LEDGER = os.path.join(TMP, "forward.jsonl")
live_wire.FOLLOWER_LEDGER = os.path.join(TMP, "follower.jsonl")
live_wire.CURSOR_PATH = os.path.join(TMP, "cursor.json")
live_wire.CARD_DIR = os.path.join(TMP, "cards")
live_wire.INITIAL_CURSOR = 0

con = sqlite3.connect(DB)
con.execute("""CREATE TABLE prospective_message_evidence (
    rowseq INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_message_id TEXT, telegram_posted_at_utc TEXT, raw_text TEXT, raw_text_hash TEXT,
    message_event_type TEXT, message_revision_number INTEGER, telegram_edited_at_utc TEXT)""")
con.commit()


def add(mid, text, posted="2026-07-15T09:00:00+00:00", evt="CREATED", rev=1, edited=None):
    con.execute("INSERT INTO prospective_message_evidence "
                "(telegram_message_id, telegram_posted_at_utc, raw_text, raw_text_hash, "
                "message_event_type, message_revision_number, telegram_edited_at_utc) "
                "VALUES (?,?,?,?,?,?,?)",
                (str(mid), posted, text, "h" * 64, evt, rev, edited))
    con.commit()


def cycle():
    return live_wire.run_cycle(db_path=DB)


F = "seascalperfarouk Posted in 🪙・gold-trades\n\n`Whale` "

# ---------- interpreter parity with the ratified fixtures --------------------------------------
e1 = interpreter.classify(F + "XAUUSD BUY 4019-4007 sl 3985")
ok(e1["kind"] == "ENTRY" and e1["direction"] == "LONG" and e1["zone_low"] == "4007"
   and e1["zone_high"] == "4019" and e1["sl"] == "3985", "F001 entry text parses identically")
e2 = interpreter.classify(F + "XAUUSD SELL\nEntry: 4084-4094.\n\nsl 4144\nlow lot\n\ndont risk profit")
ok(e2["kind"] == "ENTRY" and e2["direction"] == "SHORT" and e2["sl"] == "4144",
   "F002 entry text parses identically")
m1 = interpreter.type_instructions("close worst hold best and tp 1")
ok({i["instruction_type"] for i in m1} == {"CLOSE_WORST", "HOLD_BEST", "TP1_TAKE"},
   "45714 typing matches fixture")
m2 = interpreter.type_instructions("put now sl to entry on lowest entry")
ok(m2[0]["instruction_type"] == "SL_TO_ENTRY" and m2[0]["scope"] == "lowest entry leg",
   "45717 scoped BE typing")
m3 = interpreter.type_instructions("130 pips take Some off")
ok(m3[0]["instruction_type"] == "TAKE_PCT_OFF" and m3[0]["pct"] is None, "45720 take-some pct NULL")
m4 = interpreter.type_instructions("140 pips take 50% off")
ok(m4[0]["pct"] == 0.5, "45731 allowlisted 50%")
ok(interpreter.type_instructions("90 pips on Lowes entry lets make profit before cpi") == [],
   "45715 stays commentary (no phantom instruction)")
ok(any(i["instruction_type"] == "FINAL_CLOSE"
       for i in interpreter.type_instructions("trade closed in700 pips enjoy profit")),
   "45723 close detected")

# ---------- 1. genuine Farouk gold setup -> exactly one proposal -------------------------------
add(101, F + "XAUUSD BUY 4019-4007 sl 3985", posted="2026-07-15T08:38:06+00:00")
acts = cycle()
ok(any("PROPOSAL_EMITTED" in a for _, a in acts), "entry post emits proposal")
sid = "XAU-F001-20260715"
ok(os.path.exists(os.path.join(live_wire.CARD_DIR, sid + ".md")), "card written within cycle")
fl = [json.loads(l) for l in open(live_wire.FOLLOWER_LEDGER, encoding="utf-8")]
ok(len([r for r in fl if r["record_type"] == "FOLLOWER_PROPOSAL"]) == 1, "one follower-ledger record")
card = json.load(open(os.path.join(live_wire.CARD_DIR, sid + ".json"), encoding="utf-8"))
ok(card["banner"].startswith("NO BROKER ACTION"), "banner present")
ok("NOT_ADJUDICATED" in card["fill_state"]["LANE_A"], "no OHLC used at proposal time")
ok(card["detector_v0_2_label"] == "SHADOW_CANDIDATE_MEDIUM", "auto v0.2 label (attempt+pre-1530)")
ok(all(v in ("NOT_MATCHED", "EXPIRED") for v in card["pre_mark_comparisons"].values()),
   "pre-mark comparison computed, none matched for 4007-4019 LONG")

# ---------- 2. duplicate: re-run cycle -> nothing new -------------------------------------------
n_fwd = len(open(live_wire.FWD_LEDGER, encoding="utf-8").readlines())
acts2 = cycle()
ok(acts2 == [] and len(open(live_wire.FWD_LEDGER, encoding="utf-8").readlines()) == n_fwd,
   "re-run emits nothing (cursor + idempotent hashes)")

# ---------- 4. management updates the SAME campaign card ---------------------------------------
add(102, F + "close worst hold best and tp 1", posted="2026-07-15T09:10:00+00:00")
acts3 = cycle()
ok(any("CARD_UPDATED" in a and "rev 2" in a for _, a in acts3), "management -> revision 2 update")
card2 = json.load(open(os.path.join(live_wire.CARD_DIR, sid + ".json"), encoding="utf-8"))
ok(len(card2["management_state"]["instruction_events"]) == 3 and card2["revision"] == 2,
   "instructions attached to existing campaign (no new campaign)")

# ---------- 3. edit-to-existing-campaign stays a revision record (case c; matrix at file end) ----
add(101, F + "XAUUSD BUY 4019-4007 sl 3980 EDITED", posted="2026-07-15T08:38:06+00:00",
    evt="EDITED", rev=2, edited="2026-07-15T09:05:00+00:00")
acts4 = cycle()
ok(any("EDIT_REVISION_RECORDED" in a for _, a in acts4)
   and not any("PROPOSAL_EMITTED_FROM_EDIT" in a for _, a in acts4),
   "case (c): edit to an EXISTING campaign -> EDIT_REVISION_RECORDED, no new campaign")

# ---------- 5/6/7. non-XAU, other provider, indicator-alert text: all inert ---------------------
add(104, "kyledoops Posted in ⚓・captains-take\n\nBTC looks great buy 62000-61000 sl 60000")
add(105, ".ccolumbus Posted in 🪙・metals\n\nGold long Entry 4007 SL 3997 XAUUSD BUY 4007-4017 sl 3997")
add(106, "CHoCH up (bullish)")
acts5 = cycle()
kinds = [a for _, a in acts5]
ok(all(a == "IGNORED_NOT_FAROUK_GOLD" for a in kinds) and len(kinds) == 3,
   "non-XAU, Columbus gold, and indicator-alert text all structurally excluded")
fl2 = [json.loads(l) for l in open(live_wire.FOLLOWER_LEDGER, encoding="utf-8")]
ok(len([r for r in fl2 if r["record_type"] == "FOLLOWER_PROPOSAL"]) == 1,
   "still exactly one proposal campaign")

# ---------- 8. missing stop fails closed ---------------------------------------------------------
add(107, F + "XAUUSD SELL 4090-4100 no stop stated yet")
acts6 = cycle()
ok(any("FAIL_CLOSED_REVIEW" in a for _, a in acts6), "missing stop -> NEEDS_HUMAN_REVIEW, no proposal")
fwd = [json.loads(l) for l in open(live_wire.FWD_LEDGER, encoding="utf-8")]
ok(any(r["record_type"] == "XAU_F_INTERPRETATION_REVIEW" for r in fwd), "review record appended")
ok(not os.path.exists(os.path.join(live_wire.CARD_DIR, "XAU-F002-20260715.json")),
   "no card for failed-closed entry")

# ---------- 9. poison message cannot escape the cycle (listener isolation) ----------------------
add(108, F + "XAUUSD BUY 3990-3980 sl 3970")
real_classify = interpreter.classify
interpreter.classify = lambda t: (_ for _ in ()).throw(RuntimeError("boom"))
try:
    a1 = cycle(); a2 = cycle(); a3 = cycle()
finally:
    interpreter.classify = real_classify
ok(a1 == [] and a2 == [] and any(a == "FAILED_NEEDS_HUMAN_REVIEW" for _, a in a3),
   "3 failures -> recorded + skipped; no exception escaped any cycle")
ok("telethon" not in sys.modules and "module_a_telegram" not in sys.modules,
   "live wire imports no Telegram/listener code (structural isolation)")

# ---------- 10/11. prohibited fields + invariants ------------------------------------------------
try:
    guards.assert_clean(dict(card, position_size=1), "probe")
    ok(False, "prohibited key must fail")
except guards.GuardViolation:
    ok(True, "prohibited execution field rejected on live cards")
inv = guards.verify_project_invariants()
ok(inv["scorers"] == "UNCHANGED" and inv["pre_marks"] == "FROZEN"
   and inv["gates"] == "PAPER/PREVIEW/False/False", "scorer/gate/pre-mark immutability holds")

# ---------- 12. LIVE_EDIT_COMPLETION matrix cases (a) + (a-BLOCKED) — D-106 (run last: create/block) --
def _props():
    return [json.loads(l) for l in open(live_wire.FOLLOWER_LEDGER, encoding="utf-8")
            if json.loads(l)["record_type"] == "FOLLOWER_PROPOSAL"]

# CASE (a): completing edit, NO existing campaign, NO outcome evidence yet -> creates campaign +
# T=0 at the EDIT-COMPLETION time (the F008-would-have-worked case).
n_a0 = len(_props())
add(200, F + "XAUUSD SELL 4161-4171 SL 4187", posted="2026-07-22T14:03:48+00:00",
    evt="EDITED", rev=2, edited="2026-07-22T14:04:00+00:00")
acts_a = cycle()
ok(any("PROPOSAL_EMITTED_FROM_EDIT" in a for _, a in acts_a) and len(_props()) == n_a0 + 1,
   "case (a): completing edit, no campaign, pre-outcome -> ONE new campaign (PROPOSAL_EMITTED_FROM_EDIT)")
_edit_setup = [json.loads(l) for l in open(live_wire.FWD_LEDGER, encoding="utf-8")
               if "SELL" in l and (json.loads(l).get("timestamp_utc", "") or "").startswith("2026-07-22T14:")]
ok(any((r.get("timestamp_utc") or "").startswith("2026-07-22T14:04:00") for r in _edit_setup),
   "case (a): T=0 stamped at EDIT-COMPLETION (14:04:00), NOT the original post (14:03:48)")

# CASE (a-BLOCKED): backdating guard. Outcome recorded at 15:06, then a SLOW completing edit
# received 15:10 (after the outcome) -> NO campaign; stays quarantined.
with open(live_wire.FWD_LEDGER, "a", encoding="utf-8") as fh:
    fh.write(json.dumps({"record_type": "XAU_F_ORPHAN_MANAGEMENT", "message_id": 301,
                         "timestamp_utc": "2026-07-22T15:06:00+00:00", "why": "TP1 hit (orphan)"}) + "\n")
n_ab0 = len(_props())
add(300, F + "XAUUSD SELL 4200-4210 SL 4225", posted="2026-07-22T15:03:00+00:00",
    evt="EDITED", rev=2, edited="2026-07-22T15:10:00+00:00")
acts_ab = cycle()
ok(any("RETROSPECTIVE_EDIT_COMPLETION_BLOCKED" in a for _, a in acts_ab) and len(_props()) == n_ab0,
   "case (a-BLOCKED): slow completing edit after outcome -> BLOCKED, NO campaign (backdating guard)")

# ---------- 13. GATE INHERITANCE on the edit path (D-106 review Q1): the completing-edit branch
# classifies via the SAME interpreter.classify() as CREATED, and classify SHORT-CIRCUITS to
# NOT_FAROUK_GOLD (author + instrument-scope header gate) BEFORE any pricing check. So an edit that
# "completes" into a valid priced signal but is from a NON-FAROUK author, or is CRYPTO, must NOT
# create a gold campaign. The gate is inherited via `ce["kind"] == "ENTRY"` being false. ----------
n_g0 = len(_props())
# non-Farouk author, body is a perfectly-formed gold entry -> excluded by the author/channel header
add(500, "kyledoops Posted in ⚓・captains-take\n\nXAUUSD SELL 4161-4171 SL 4187",
    posted="2026-07-22T17:00:00+00:00", evt="EDITED", rev=2, edited="2026-07-22T17:00:20+00:00")
# Farouk but CRYPTO channel + crypto instrument (K-047 hard isolation) -> excluded, no gold campaign
add(501, "seascalperfarouk Posted in 🪙・crypto-trades\n\nBTCUSD BUY 62000-61000 SL 60000",
    posted="2026-07-22T17:01:00+00:00", evt="EDITED", rev=2, edited="2026-07-22T17:01:20+00:00")
acts_g = cycle()
gacts = [a for _, a in acts_g]
ok(not any("PROPOSAL_EMITTED_FROM_EDIT" in a for a in gacts) and len(_props()) == n_g0,
   "gate inheritance: non-Farouk edit + crypto edit create NO gold campaign on the edit path")
ok(len(gacts) == 2 and all(a == "EDIT_REVISION_RECORDED(no campaign affected)" for a in gacts),
   "gate inheritance: both short-circuit at NOT_FAROUK_GOLD (author+instrument), not at pricing")

# ---------- 14. MULTIPLE-EDIT SEQUENCING (D-106 review Q2): edit1 completes a signal -> creates a
# campaign (case a); a LATER edit2 to the SAME message must hit case (c) EDIT_REVISION_RECORDED
# against the now-existing campaign — never a SECOND campaign, never a re-freeze. Farouk edits >1x.
n_m0 = len(_props())
add(400, F + "XAUUSD SELL 4055-4065 SL 4080", posted="2026-07-22T16:00:00+00:00",
    evt="EDITED", rev=2, edited="2026-07-22T16:00:30+00:00")
acts_m1 = cycle()
ok(any("PROPOSAL_EMITTED_FROM_EDIT" in a for _, a in acts_m1) and len(_props()) == n_m0 + 1,
   "multi-edit: edit1 completes the signal -> ONE campaign created (case a)")
# edit2 to the SAME message id 400 (now revision 3), AFTER the campaign exists
add(400, F + "XAUUSD SELL 4055-4065 SL 4075 EDITED AGAIN", posted="2026-07-22T16:00:00+00:00",
    evt="EDITED", rev=3, edited="2026-07-22T16:05:00+00:00")
acts_m2 = cycle()
ok(any("EDIT_REVISION_RECORDED" in a for _, a in acts_m2)
   and not any("PROPOSAL_EMITTED_FROM_EDIT" in a for _, a in acts_m2)
   and len(_props()) == n_m0 + 1,
   "multi-edit: edit2 to same message -> case (c) EDIT_REVISION_RECORDED; no 2nd campaign, no re-freeze")

con.close()
shutil.rmtree(TMP, ignore_errors=True)

if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    print(f"PASS {PASS} live-wire checks")
