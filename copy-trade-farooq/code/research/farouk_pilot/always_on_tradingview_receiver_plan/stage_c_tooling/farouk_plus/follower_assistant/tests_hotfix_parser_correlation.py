"""Parser-morphology + campaign-correlation hotfix tests (RESEARCH-ONLY). Sandboxes the wire's
ledgers/cards to temp; never writes genuine ledgers. Covers the Phase-6/10 corpus + Phase-7 behaviour.
"""
from __future__ import annotations

import io
import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import interpreter                                                # noqa: E402
import live_wire as W                                             # noqa: E402

PASS = 0
FAIL = 0
H = "seascalperfarouk Posted in gold-trades\n\n"


def ok(name, cond):
    global PASS, FAIL
    if cond:
        PASS += 1
    else:
        FAIL += 1
        print(f"FAIL: {name}")


# ---- Phase 6 POSITIVE corpus (all must parse to ENTRY) ----------------------------------------
POSITIVES = {
    "exact_1532": (H + "`Whale` XAUUSD Sell Zone: 4059–4069\nStop Loss: 4090\nhigh Risk: Low lot size", "SHORT", "4090"),
    "buy_equiv": (H + "XAUUSD Buy Zone: 4059 – 4069\nSL: 4058", "LONG", "4058"),
    "mixed_case": (H + "xauusd SELL ZONE 4059-4069 stop: 4090", "SHORT", "4090"),
    "slash": (H + "Gold Sell Zone 4059/4069\nStop Loss: 4090", "SHORT", "4090"),
    "to_words": (H + "XAUUSD sell zone is 4059 to 4069\nSL 4090", "SHORT", "4090"),
    "em_dash": (H + "XAUUSD Sell Zone 4059 — 4069\nStop Loss: 4090", "SHORT", "4090"),
    "mention_prefix": (H + "@Whale XAUUSD Sell Zone: 4059–4069\nStop Loss: 4090", "SHORT", "4090"),
    "commentary_after": (H + "XAUUSD Sell Zone: 4059-4069\nStop Loss: 4090\nbe careful, low lot", "SHORT", "4090"),
}


def test_positive_corpus():
    for name, (txt, direction, sl) in POSITIVES.items():
        c = interpreter.classify(txt)
        ok(f"positive[{name}] -> ENTRY", c["kind"] == "ENTRY")
        if c["kind"] == "ENTRY":
            ok(f"positive[{name}] dir={direction}", c["direction"] == direction)
            ok(f"positive[{name}] zone 4059-4069", c["zone_low"] == "4059" and c["zone_high"] == "4069")
            ok(f"positive[{name}] sl={sl}", c["sl"] == sl)
    # qualitative risk preserved as text only, no sizing
    c = interpreter.classify(POSITIVES["exact_1532"][0])
    ok("risk commentary flagged", c["qualitative_risk_flag"] == "HIGH_RISK_SOURCE_WORDING")
    ok("no sizing derived", "lot/money/exposure" in c["no_sizing_note"])
    blob = json.dumps(c).lower()
    for tok in ("lot_size", "position_size", "account", "leverage", "risk_pct", "0.01"):
        ok(f"no sizing token '{tok}'", tok not in blob)


# ---- Phase 6 NEGATIVE corpus (must NOT be ENTRY) ----------------------------------------------
NEGATIVES = {
    "tp1_card": H + "XAUUSD-VIP sell 1  4062.47 4054.34  813.00",
    "closure_card": H + "XAUUSD-VIP sell 1  4062.47 4047.18  1529.00",
    "tp1_now": H + "tp 1 now",
    "sl_to_entry": H + "put sl to entry",
    "pips_commentary": H + "140-150 pips if you're still holding.",
    "chart_chat": H + "Trade Breakdown: the reason behind the sell...",
    "btc_signal": H + "`Whale` BTC Sell Limit: 65,900 – 67,300",
    "incomplete_zone": H + "XAUUSD Sell Zone: 4059\nStop Loss: 4090",
    "missing_direction": H + "XAUUSD Zone: 4059-4069\nStop Loss: 4090",
}


def test_negative_corpus():
    for name, txt in NEGATIVES.items():
        c = interpreter.classify(txt)
        ok(f"negative[{name}] not ENTRY", c["kind"] != "ENTRY")
    # result cards / commentary must not become MANAGEMENT state mutations either
    ok("tp1 card is OTHER (not a signal, not mgmt)", interpreter.classify(NEGATIVES["tp1_card"])["kind"] == "OTHER")
    ok("closure card is OTHER", interpreter.classify(NEGATIVES["closure_card"])["kind"] == "OTHER")


# ---- Phase 4/6 correlation fixtures (sandboxed process_message) --------------------------------
def _sandbox(tmp):
    W.FWD_LEDGER = os.path.join(tmp, "fwd.jsonl")
    W.FOLLOWER_LEDGER = os.path.join(tmp, "follower.jsonl")
    W.CARD_DIR = os.path.join(tmp, "cards")


def _msg(mid, posted, text):
    import hashlib
    return {"id": mid, "posted_at": posted, "raw_text": text,
            "raw_text_sha256": hashlib.sha256(text.encode()).hexdigest(),
            "event_type": "CREATED", "revision": 1}


def _fwd_records(tmp):
    p = os.path.join(tmp, "fwd.jsonl")
    return [json.loads(l) for l in open(p, encoding="utf-8")] if os.path.exists(p) else []


def test_full_authentic_sequence():
    tmp = tempfile.mkdtemp(prefix="hotfix_")
    _sandbox(tmp)
    con = {"version": "0.1.0"}
    # a prior STALE F002-like open campaign (07-14) that must NEVER be a fallback target
    setups = {"XAU-F002-20260714": {"record_type": "XAU_F_SETUP", "setup_id": "XAU-F002-20260714",
              "revision": 1, "message_ids": [45727], "timestamp_utc": "2026-07-14T13:26:21+00:00",
              "direction": "SHORT", "management_timing_8c": {"instruction_events": []}}}
    open_ids = ["XAU-F002-20260714"]
    # 15:32 ENTRY -> exactly one NEW campaign
    a = W.process_message(_msg(45755, "2026-07-15T14:32:18+00:00", POSITIVES["exact_1532"][0]), setups, open_ids, con)
    ok("15:32 emits a proposal (new campaign)", a.startswith("PROPOSAL_EMITTED"))
    new_ids = [s for s in setups if s != "XAU-F002-20260714"]
    ok("exactly one new campaign created", len(new_ids) == 1)
    newid = new_ids[0]
    ok("new campaign is F003 (not F001/F002)", newid.startswith("XAU-F003"))
    setup = setups[newid]
    ok("new campaign SHORT 4059-4069 sl 4090", setup["direction"] == "SHORT" and setup["entry_zone"] == "4059-4069" and setup["sl"].startswith("4090"))
    # 15:45 TP1 -> correlates to the NEW campaign, NOT F002
    b = W.process_message(_msg(45756, "2026-07-15T14:46:01+00:00", H + "tp 1 now"), setups, open_ids, con)
    ok("15:45 TP1 correlates to new campaign", newid in b and "XAU-F002" not in b)
    ok("F002 message_ids NOT extended", setups["XAU-F002-20260714"]["message_ids"] == [45727])
    # 15:52 SL-to-entry -> new campaign
    d = W.process_message(_msg(45759, "2026-07-15T14:52:03+00:00", H + "put sl to entry"), setups, open_ids, con)
    ok("15:52 BE correlates to new campaign", newid in d)
    evs = [e["instruction_type"] for e in setups[newid]["management_timing_8c"]["instruction_events"]]
    ok("new campaign has TP1 + SL_TO_ENTRY", "TP1_TAKE" in evs and "SL_TO_ENTRY" in evs)
    # 16:13 commentary -> no state mutation
    e = W.process_message(_msg(45760, "2026-07-15T15:13:34+00:00", H + "140-150 pips if you're still holding."), setups, open_ids, con)
    ok("16:13 commentary no action", e == "FAROUK_GOLD_COMMENTARY_NO_ACTION")


def test_orphan_stale_fallback_prohibited():
    tmp = tempfile.mkdtemp(prefix="hotfix_orphan_")
    _sandbox(tmp)
    con = {"version": "0.1.0"}
    # only a STALE 07-14 F002 open; a 07-15 management message must ORPHAN, never attach to F002
    setups = {"XAU-F002-20260714": {"record_type": "XAU_F_SETUP", "setup_id": "XAU-F002-20260714",
              "revision": 1, "message_ids": [45727], "timestamp_utc": "2026-07-14T13:26:21+00:00",
              "direction": "SHORT", "management_timing_8c": {"instruction_events": []}}}
    open_ids = ["XAU-F002-20260714"]
    a = W.process_message(_msg(45756, "2026-07-15T14:46:01+00:00", H + "tp 1 now"), setups, open_ids, con)
    ok("stale-only -> ORPHAN_MANAGEMENT_MESSAGE", a.startswith("ORPHAN_MANAGEMENT_MESSAGE"))
    ok("F002 NOT mutated by orphan", setups["XAU-F002-20260714"]["message_ids"] == [45727])
    rec = [r for r in _fwd_records(tmp) if r.get("record_type") == "XAU_F_ORPHAN_MANAGEMENT"]
    ok("orphan record appended (fail-closed)", len(rec) == 1 and "never defaults to F001/F002" in rec[0]["why"])
    # no open campaign at all -> also fail closed
    a2 = W.process_message(_msg(45999, "2026-07-15T14:46:01+00:00", H + "tp 1 now"), {}, [], con)
    ok("no open campaign -> fail closed", a2.startswith("FAIL_CLOSED_REVIEW"))


def test_proximate_ambiguous_fail_closed():
    tmp = tempfile.mkdtemp(prefix="hotfix_amb_")
    _sandbox(tmp)
    con = {"version": "0.1.0"}
    # two SAME-DAY open campaigns -> ambiguous -> fail closed
    setups = {"XAU-F003-20260715": {"record_type": "XAU_F_SETUP", "setup_id": "XAU-F003-20260715",
              "revision": 1, "message_ids": [1], "timestamp_utc": "2026-07-15T14:00:00+00:00",
              "direction": "SHORT", "management_timing_8c": {"instruction_events": []}},
              "XAU-F004-20260715": {"record_type": "XAU_F_SETUP", "setup_id": "XAU-F004-20260715",
              "revision": 1, "message_ids": [2], "timestamp_utc": "2026-07-15T14:10:00+00:00",
              "direction": "LONG", "management_timing_8c": {"instruction_events": []}}}
    open_ids = ["XAU-F003-20260715", "XAU-F004-20260715"]
    a = W.process_message(_msg(45756, "2026-07-15T14:46:01+00:00", H + "tp 1 now"), setups, open_ids, con)
    ok("two proximate open -> ambiguous fail closed", a.startswith("FAIL_CLOSED_REVIEW"))


def test_no_f001_f002_fallback_when_stale():
    ok("proximity window is a disclosed constant", isinstance(W.PROXIMITY_HOURS, int))
    ok("_within rejects >window", not W._within("2026-07-14T13:26:21+00:00", "2026-07-15T14:46:01+00:00", W.PROXIMITY_HOURS))
    ok("_within accepts <=window", W._within("2026-07-15T14:32:18+00:00", "2026-07-15T14:46:01+00:00", W.PROXIMITY_HOURS))


if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    for fn in [test_positive_corpus, test_negative_corpus, test_full_authentic_sequence,
               test_orphan_stale_fallback_prohibited, test_proximate_ambiguous_fail_closed,
               test_no_f001_f002_fallback_when_stale]:
        fn()
    print(f"\n{PASS} passed, {FAIL} failed")
    sys.exit(1 if FAIL else 0)
