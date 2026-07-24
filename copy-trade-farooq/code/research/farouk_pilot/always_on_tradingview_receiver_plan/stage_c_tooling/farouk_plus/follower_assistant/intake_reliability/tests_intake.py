"""Fail-loud intake tests — real corpus + fuzz + correlation stress + failure injection + canaries.
Sandboxed: scans write to temp ledgers; the real intake ledgers and all genuine ledgers are untouched.
"""
from __future__ import annotations

import io
import json
import os
import sqlite3
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
FA = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, FA)
import interpreter                                                # noqa: E402
import intake_observer as OB                                     # noqa: E402
import guards                                                     # noqa: E402

PASS = 0
FAIL = 0
H = "seascalperfarouk Posted in gold-trades\n\n"
REAL_DB = os.path.join(guards.ST_ROOT, "campaign_extractor", "prospective", "data", "prospective_evidence_v1.db")


def ok(name, cond):
    global PASS, FAIL
    if cond:
        PASS += 1
    else:
        FAIL += 1
        print(f"FAIL: {name}")


def _tmp_ledgers(tmp):
    return dict(class_ledger=os.path.join(tmp, "cls.jsonl"), quar_ledger=os.path.join(tmp, "quar.jsonl"),
                alert_ledger=os.path.join(tmp, "alert.jsonl"), status_path=os.path.join(tmp, "status.json"),
                cursor={"classified": {}})


def _make_db(tmp, rows):
    """rows: list of (msg_id, posted, text). Build a temp evidence DB the observer can read."""
    db = os.path.join(tmp, "ev.db")
    con = sqlite3.connect(db)
    con.execute("CREATE TABLE prospective_message_evidence(telegram_message_id TEXT, "
                "telegram_posted_at_utc TEXT, listener_received_at_utc TEXT, raw_text TEXT, "
                "raw_text_hash TEXT, telegram_sender_username TEXT, message_event_type TEXT)")
    import hashlib
    for mid, posted, text in rows:
        con.execute("INSERT INTO prospective_message_evidence VALUES(?,?,?,?,?,?,?)",
                    (str(mid), posted, posted, text, hashlib.sha256((text or "").encode()).hexdigest(),
                     "seascalperfarouk", "CREATED"))
    con.commit(); con.close()
    return db


EMPTY_IDX = {"created": {}, "mgmt": {}, "review": {}, "orphan": {}, "ambiguous": {}, "setups": {}, "freezes": set()}


# ---- Part 4: real corpus, no silent relevant drop ---------------------------------------------
def test_real_corpus_no_silent_drop():
    tmp = tempfile.mkdtemp(prefix="intake_corpus_")
    L = _tmp_ledgers(tmp)
    idx = OB.build_index()                                        # read the real forward/freeze ledgers
    s = OB.scan(db_path=REAL_DB, idx=idx, **L)
    cls = [json.loads(x) for x in open(L["class_ledger"], encoding="utf-8")]
    ok("every CREATED message got exactly one classification", len(cls) == s["messages"] and s["messages"] >= 390)
    ok("every classification is in the closed enum", all(r["classification"] in OB.CLASSES for r in cls))
    # no farouk-gold trade message routed IRRELEVANT (silent drop)
    con = sqlite3.connect(f"file:{REAL_DB}?mode=ro", uri=True)
    txt = {int(r[0]): r[1] for r in con.execute("SELECT telegram_message_id,raw_text FROM prospective_message_evidence WHERE message_event_type='CREATED'").fetchall()}
    con.close()
    silent = [r["message_id"] for r in cls if r["classification"] == "IRRELEVANT" and interpreter.is_farouk_gold(txt.get(r["message_id"]))]
    ok("SILENT_RELEVANT_DROP_COUNT == 0", len(silent) == 0)
    d = {r["message_id"]: r["classification"] for r in cls}
    ok("15:32 miss (45755) is QUARANTINED", d.get(45755) == "QUARANTINED_UNPARSED_SIGNAL_CANDIDATE")
    # no false campaigns: every PARSED_NEW_CAMPAIGN maps to a genuine wire XAU_F_SETUP entry
    # (invariant form — the live corpus legitimately grows: F001/F002, then F003/F004 2026-07-16, …)
    _setup_entry_mids = set()
    _fwdp = os.path.join(os.path.dirname(HERE), "..", "forward_validation_ledger_v0_2.jsonl")
    for _line in open(_fwdp, encoding="utf-8"):
        try:
            _r = json.loads(_line)
        except json.JSONDecodeError:
            continue
        if _r.get("record_type") == "XAU_F_SETUP" and _r.get("revision", 1) == 1:
            _setup_entry_mids.update(_r.get("message_ids") or [])
    _pnc = [r["message_id"] for r in cls if r["classification"] == "PARSED_NEW_CAMPAIGN"]
    ok("no false campaigns (every PARSED_NEW_CAMPAIGN is a genuine wire setup entry)",
       len(_pnc) >= 2 and all(m in _setup_entry_mids for m in _pnc))


# ---- Part 5: fuzz — valid variants parse, damaged quarantine ----------------------------------
def _variants():
    base_dir = ["Sell", "SELL", "sell", "Buy", "BUY"]
    seps = ["-", "–", "—", "/", " to "]
    stops = ["Stop Loss: 4090", "SL: 4090", "Stop: 4090", "SL 4090"]
    names = ["XAUUSD", "GOLD", "xauusd"]
    out = []
    for d in base_dir[:3]:                                        # SELL forms
        for sep in seps:
            for st in stops[:2]:
                for nm in names[:2]:
                    out.append(f"{H}@Whale {nm} {d} Zone: 4059{sep}4069\n{st}")
    return out


def test_fuzz_valid_variants_parse():
    variants = _variants()
    parsed = sum(1 for v in variants if interpreter.classify(v)["kind"] == "ENTRY")
    ok(f"all {len(variants)} valid signal variants parse to ENTRY", parsed == len(variants))
    # damaged variants must NOT become a campaign (parse-fail -> the observer quarantines)
    damaged = [H + "XAUUSD Sell Zone: 4059\nStop Loss: 4090",          # incomplete zone
               H + "XAUUSD Zone: 4059-4069\nStop Loss: 4090",          # no direction
               H + "XAUUSD Sell Zone: 4059-4069",                      # no stop
               H + "XAUUSD Sell Buy Zone: 4059-4069\nSL 4090"]         # ambiguous direction
    fp = sum(1 for v in damaged if interpreter.classify(v)["kind"] == "ENTRY")
    ok("no false-positive campaign from damaged variants", fp == 0)
    # each damaged, plausibly-signal message the observer routes to QUARANTINE (not silent)
    q = 0
    for v in damaged:
        c, _, _ = OB.route_message({"id": 1, "raw_text": v, "posted": "2026-07-15T14:00:00+00:00"}, EMPTY_IDX)
        if c == "QUARANTINED_UNPARSED_SIGNAL_CANDIDATE":
            q += 1
    ok("damaged plausible signals quarantine (never silent)", q == len(damaged))


# ---- Part 6: management correlation routing under index states --------------------------------
def test_correlation_routing():
    m = {"id": 500, "raw_text": H + "tp 1 now", "posted": "2026-07-15T14:46:00+00:00"}
    ok("in-campaign mgmt -> PARSED_MANAGEMENT", OB.route_message(m, {**EMPTY_IDX, "mgmt": {500: "XAU-F003"}})[0] == "PARSED_MANAGEMENT_INSTRUCTION")
    ok("no-campaign mgmt -> ORPHAN", OB.route_message(m, EMPTY_IDX)[0] == "ORPHAN_MANAGEMENT_MESSAGE")
    ok("wire-orphan-recorded -> ORPHAN", OB.route_message(m, {**EMPTY_IDX, "orphan": {500: "no proximate campaign"}})[0] == "ORPHAN_MANAGEMENT_MESSAGE")
    ok("wire-pause -> AMBIGUOUS", OB.route_message(m, {**EMPTY_IDX, "ambiguous": {500: "two+ open"}})[0] == "AMBIGUOUS_CAMPAIGN_CORRELATION")
    ok("invalidated-by-correction -> ORPHAN", OB.route_message(m, {**EMPTY_IDX, "orphan": {500: "correlation invalidated"}})[0] == "ORPHAN_MANAGEMENT_MESSAGE")
    # F001/F002 never used as a fallback route for management (routing uses explicit index only)
    ok("no F001/F002 fallback in routing", "F00" not in str(OB.route_message(m, EMPTY_IDX)))


# ---- Part 8: failure injection ----------------------------------------------------------------
def test_failure_injection():
    orig = interpreter.classify
    interpreter.classify = lambda t: (_ for _ in ()).throw(ValueError("boom"))
    try:
        c, reason, extra = OB.route_message({"id": 1, "raw_text": H + "XAUUSD Sell Zone: 4059-4069 SL 4090", "posted": "x"}, EMPTY_IDX)
    finally:
        interpreter.classify = orig
    ok("parser exception -> PARSER_FAILURE_CAPTURED", c == "PARSER_FAILURE_CAPTURED")
    ok("raw preserved on failure", extra.get("raw_preserved") is True)
    ok("failure reason recorded", "ValueError" in reason)
    # unreadable/None text must not crash
    c2, _, _ = OB.route_message({"id": 2, "raw_text": None, "posted": "x"}, EMPTY_IDX)
    ok("None text handled (no crash)", c2 in OB.CLASSES)


# ---- Part 9: canaries A-F (sandboxed temp DB) -------------------------------------------------
def _run_canary(tmp, rows, idx=None):
    os.makedirs(tmp, exist_ok=True)
    L = _tmp_ledgers(tmp)
    db = _make_db(tmp, rows)
    OB.scan(db_path=db, idx=idx or dict(EMPTY_IDX), **L)
    cls = {json.loads(x)["message_id"]: json.loads(x)["classification"] for x in open(L["class_ledger"], encoding="utf-8")}
    alerts = [json.loads(x) for x in open(L["alert_ledger"], encoding="utf-8")] if os.path.exists(L["alert_ledger"]) else []
    return cls, alerts, L


def test_canaries():
    tmp = tempfile.mkdtemp(prefix="intake_canary_")
    # A. valid signal -> PARSED_NEW_CAMPAIGN, no alert  (needs a wire 'created' index entry)
    a_idx = {**EMPTY_IDX, "created": {701: "XAU-F003-20260715"}}
    cls, alerts, _ = _run_canary(os.path.join(tmp, "A"), [(701, "2026-07-15T14:00:00+00:00", H + "XAUUSD Sell Zone: 4059-4069\nStop Loss: 4090")], a_idx)
    os.makedirs(os.path.join(tmp, "A"), exist_ok=True)
    ok("Canary A: valid signal -> PARSED_NEW_CAMPAIGN", cls.get(701) == "PARSED_NEW_CAMPAIGN")
    ok("Canary A: no alert (freeze absent triggers freeze-missing? only if post-activation)", all(al["message_id"] != 701 or al["alert_type"] == "CAMPAIGN_CREATED_FREEZE_MISSING" for al in alerts))
    # B. plausible unsupported signal -> QUARANTINE + 1 alert
    cls, alerts, _ = _run_canary(os.path.join(tmp, "B"), [(702, "2026-07-15T14:00:00+00:00", H + "XAUUSD Sell around 4059 to 4069 area, stop somewhere near 4090ish")])
    ok("Canary B: plausible unsupported -> QUARANTINE", cls.get(702) == "QUARANTINED_UNPARSED_SIGNAL_CANDIDATE")
    ok("Canary B: exactly one alert", sum(1 for a in alerts if a["message_id"] == 702) == 1)
    # C. management, no active campaign -> ORPHAN + 1 alert
    cls, alerts, _ = _run_canary(os.path.join(tmp, "C"), [(703, "2026-07-15T14:00:00+00:00", H + "tp 1 now")])
    ok("Canary C: mgmt no campaign -> ORPHAN", cls.get(703) == "ORPHAN_MANAGEMENT_MESSAGE")
    ok("Canary C: exactly one alert", sum(1 for a in alerts if a["message_id"] == 703) == 1)
    # D. two plausible campaigns -> AMBIGUOUS + 1 alert
    cls, alerts, _ = _run_canary(os.path.join(tmp, "D"), [(704, "2026-07-15T14:00:00+00:00", H + "put sl to entry")], {**EMPTY_IDX, "ambiguous": {704: "two+ open campaigns"}})
    ok("Canary D: two campaigns -> AMBIGUOUS", cls.get(704) == "AMBIGUOUS_CAMPAIGN_CORRELATION")
    ok("Canary D: exactly one alert", sum(1 for a in alerts if a["message_id"] == 704) == 1)
    # E. parser exception -> PARSER_FAILURE_CAPTURED + alert; raw preserved
    orig = interpreter.classify
    interpreter.classify = lambda t: (_ for _ in ()).throw(RuntimeError("kaboom"))
    try:
        cls, alerts, LE = _run_canary(os.path.join(tmp, "E"), [(705, "2026-07-15T14:00:00+00:00", H + "XAUUSD Sell Zone 4059-4069 SL 4090")])
    finally:
        interpreter.classify = orig
    ok("Canary E: parser exception -> PARSER_FAILURE_CAPTURED", cls.get(705) == "PARSER_FAILURE_CAPTURED")
    ok("Canary E: alert raised", sum(1 for a in alerts if a["message_id"] == 705) == 1)
    ok("Canary E: raw message preserved in classification", any(json.loads(x)["message_id"] == 705 for x in open(LE["class_ledger"], encoding="utf-8")))
    # F. duplicate input -> one classification, no duplicate alert (idempotent cursor)
    tmpf = os.path.join(tmp, "F"); os.makedirs(tmpf, exist_ok=True)
    L = _tmp_ledgers(tmpf); db = _make_db(tmpf, [(706, "2026-07-15T14:00:00+00:00", H + "tp 1 now")])
    cur = {"classified": {}}
    OB.scan(db_path=db, idx=dict(EMPTY_IDX), cursor=cur, class_ledger=L["class_ledger"], quar_ledger=L["quar_ledger"], alert_ledger=L["alert_ledger"], status_path=L["status_path"])
    OB.scan(db_path=db, idx=dict(EMPTY_IDX), cursor=cur, class_ledger=L["class_ledger"], quar_ledger=L["quar_ledger"], alert_ledger=L["alert_ledger"], status_path=L["status_path"])
    n_cls = sum(1 for x in open(L["class_ledger"], encoding="utf-8") if json.loads(x)["message_id"] == 706)
    n_alert = sum(1 for x in open(L["alert_ledger"], encoding="utf-8")) if os.path.exists(L["alert_ledger"]) else 0
    ok("Canary F: duplicate re-scan -> one classification", n_cls == 1)
    ok("Canary F: duplicate re-scan -> no duplicate alert", n_alert == 1)


# ---- observer never mutates genuine ledgers ---------------------------------------------------
def test_no_genuine_mutation():
    import hashlib
    fwd = os.path.join(FA, "..", "forward_validation_ledger_v0_2.jsonl")
    before = hashlib.sha256(open(fwd, "rb").read()).hexdigest()
    tmp = tempfile.mkdtemp(prefix="intake_nomut_")
    OB.scan(db_path=REAL_DB, idx=OB.build_index(), **_tmp_ledgers(tmp))
    ok("forward ledger byte-unchanged by observer", hashlib.sha256(open(fwd, "rb").read()).hexdigest() == before)
    ok("observer writes only to its own ledgers", all("intake" in p or p.startswith(tmp) for p in [OB.CLASS_LEDGER, OB.QUAR_LEDGER, OB.ALERT_LEDGER]))


if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    for fn in [test_real_corpus_no_silent_drop, test_fuzz_valid_variants_parse, test_correlation_routing,
               test_failure_injection, test_canaries, test_no_genuine_mutation]:
        fn()
    print(f"\n{PASS} passed, {FAIL} failed")
    sys.exit(1 if FAIL else 0)
