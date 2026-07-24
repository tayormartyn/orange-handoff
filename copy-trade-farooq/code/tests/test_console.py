"""Focused tests for the Manual Signal Intake Console (server.do_upload / do_observe).
Fully isolated: temp intake/fixtures/DBs; NO real intake, NO real PaperDB, NO live connection."""
from __future__ import annotations
import base64
import os
import shutil
import sys
import tempfile
import time

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_CON = os.path.join(_ROOT, "campaign_extractor", "paper_loop", "console")
_PL = os.path.join(_ROOT, "campaign_extractor", "paper_loop")
_VIS = os.path.join(_ROOT, "campaign_extractor", "vision_v1")
_Q4 = os.path.join(_ROOT, "campaign_extractor", "q4_align")
for p in (_ROOT, os.path.join(_ROOT, "campaign_extractor"), _Q4, _PL, _VIS, _CON):
    if p not in sys.path:
        sys.path.insert(0, p)

import server as C
import image_intake
import image_confirm
from paper_db import PaperDB
from image_bridge_db import ImageBridgeDB
from stores import CandidateDB
from ingest import make_png, sha256_file


def _run(fn):
    tmp = tempfile.mkdtemp(prefix="con_")
    try:
        return fn(tmp)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def _isolate(tmp):
    intake_root = os.path.join(tmp, "intake")
    fixtures = os.path.join(tmp, "fixtures")
    for d in ("manifests", "review", "inbox", "processed", "rejected"):
        os.makedirs(os.path.join(intake_root, d), exist_ok=True)
    os.makedirs(fixtures, exist_ok=True)
    image_intake.INTAKE_ROOT = intake_root
    image_confirm.REVIEW_DIR = os.path.join(intake_root, "review")
    image_confirm.FIXTURES = fixtures
    return fixtures, intake_root


def _make_intake(fixtures, intake_root, imported_at="2026-07-02T05:00:00Z"):
    import json
    img = os.path.join(fixtures, "_s.png")
    with open(img, "wb") as f:
        f.write(make_png(80, 30))
    sha = sha256_file(img)
    mid = "media-" + sha[:16]
    os.makedirs(os.path.join(fixtures, mid), exist_ok=True)
    shutil.copy2(img, os.path.join(fixtures, mid, f"original_{sha}.png"))
    m = {"intake_id": "intake-" + sha[:16], "original_filename": "s.png", "imported_media_id": mid,
         "original_image_sha256": sha, "platform": "DISCORD", "screenshot_imported_at": imported_at,
         "screenshot_captured_at": None, "intake_status": "IMPORTED_PENDING_REVIEW", "duplicate": False}
    with open(os.path.join(intake_root, "manifests", f"{m['intake_id']}.json"), "w") as f:
        json.dump(m, f)
    return m["intake_id"]


def _b64png():
    return "data:image/png;base64," + base64.b64encode(make_png(60, 24)).decode()


def _dbs(tmp):
    return PaperDB(os.path.join(tmp, "p.db")), ImageBridgeDB(os.path.join(tmp, "ib.db"))


def _q(seq, wall, bid, ask):
    return {"session": "S", "seq": seq, "symbol_id": 41, "raw_bid": int(bid * 100000),
            "raw_ask": int(ask * 100000), "broker_ts": wall, "wall_ms": wall, "mono_ns": wall * 1_000_000,
            "bid": bid, "ask": ask, "spread": round(ask - bid, 2), "flags": "OK",
            "bid_prov_seq": seq, "ask_prov_seq": seq}


def _covering(base_ms):
    return [_q(i + 1, base_ms - 2000 + i * 500, 4000.05, 4000.15) for i in range(0, 30)]


# ---- upload: immutable intake + dedup ----
def test_upload_creates_one_immutable_intake():
    def f(tmp):
        fx, ir = _isolate(tmp)
        cdb = CandidateDB(os.path.join(tmp, "cand.db"))
        orig = image_intake.vision_ingest.ingest_image
        image_intake.vision_ingest.ingest_image = lambda s, c, **k: orig(s, c, dest_root=fx, **k)
        try:
            r = C.do_upload("shot.png", _b64png(), candidate_db=cdb, root=ir)
            assert r["intake_status"] == "IMPORTED_PENDING_REVIEW" and r["duplicate"] is False
            assert cdb.get_image_by_sha(r["sha256"]) is not None       # immutably imported
        finally:
            image_intake.vision_ingest.ingest_image = orig
    _run(f)


def test_duplicate_upload_no_duplicate():
    def f(tmp):
        fx, ir = _isolate(tmp)
        cdb = CandidateDB(os.path.join(tmp, "cand.db"))
        orig = image_intake.vision_ingest.ingest_image
        image_intake.vision_ingest.ingest_image = lambda s, c, **k: orig(s, c, dest_root=fx, **k)
        try:
            img = _b64png()
            r1 = C.do_upload("a.png", img, candidate_db=cdb, root=ir)
            r2 = C.do_upload("a.png", img, candidate_db=cdb, root=ir)
            assert r1["media_id"] == r2["media_id"] and r2["duplicate"] is True
        finally:
            image_intake.vision_ingest.ingest_image = orig
    _run(f)


# ---- observe: gates ----
def _observe(tmp, ir, intake_id, *, quotes=None, **over):
    p = {"intake_id": intake_id, "reviewer_ref": "console", "instrument": over.get("instrument", "XAUUSD"),
         "direction": over.get("direction", "BUY"), "entry_low": over.get("entry_low", "4000.00"),
         "entry_high": over.get("entry_high", "4000.20"), "provider": "UNKNOWN",
         "intake_class": over.get("intake_class", "SIGNAL"), "confirm": over.get("confirm", True),
         "visible_result_fields": over.get("visible_result_fields")}
    pdb, ib = _dbs(tmp)
    res = C.do_observe(p, root=ir, paper_db=pdb, bridge_db=ib, alert_dir=tmp, quotes=quotes,
                       move_file=False, _no_status=True)        # isolate: never write real status events
    return res, pdb, ib


def test_unconfirmed_signal_blocked():
    def f(tmp):
        fx, ir = _isolate(tmp); iid = _make_intake(fx, ir)
        res, pdb, ib = _observe(tmp, ir, iid, confirm=False, quotes=[])
        assert res["final_status"] == "BLOCKED" and pdb.count() == 0
    _run(f)


def test_trade_result_excluded():
    def f(tmp):
        fx, ir = _isolate(tmp); iid = _make_intake(fx, ir)
        res, pdb, ib = _observe(tmp, ir, iid, intake_class="TRADE_RESULT",
                                visible_result_fields={"instrument": "BTCUSD", "pnl": "1749"}, quotes=[])
        assert res["final_status"] == "TRADE_RESULT_EXCLUDED" and pdb.count() == 0 and ib.count() == 0
    _run(f)


def test_unknown_blocked():
    def f(tmp):
        fx, ir = _isolate(tmp); iid = _make_intake(fx, ir)
        res, pdb, ib = _observe(tmp, ir, iid, intake_class="UNKNOWN", quotes=[])
        assert res["final_status"] == "BLOCKED" and pdb.count() == 0
    _run(f)


def test_confirmed_gold_one_observation_and_idempotent():
    def f(tmp):
        fx, ir = _isolate(tmp); iid = _make_intake(fx, ir)
        res, pdb, ib = _observe(tmp, ir, iid, instrument="XAUUSD", quotes=[])
        assert res["final_status"] == "NO_COVERAGE" and pdb.count() == 1
        # idempotent re-run through the console -> DUPLICATE, still one observation
        p = {"intake_id": iid, "intake_class": "SIGNAL", "instrument": "XAUUSD", "direction": "BUY",
             "entry_low": "4000.00", "entry_high": "4000.20", "provider": "UNKNOWN", "confirm": True,
             "reviewer_ref": "console"}
        res2 = C.do_observe(p, root=ir, paper_db=pdb, bridge_db=ib, alert_dir=tmp, quotes=[],
                            move_file=False, _no_status=True)
        assert res2["final_status"] == "DUPLICATE" and pdb.count() == 1
    _run(f)


def test_confirmed_bitcoin_one_observation():
    def f(tmp):
        fx, ir = _isolate(tmp); iid = _make_intake(fx, ir)
        res, pdb, ib = _observe(tmp, ir, iid, instrument="BTCUSD", quotes=[])
        assert res["final_status"] in ("NO_COVERAGE", "RECORDED") and pdb.count() == 1
    _run(f)


def test_absent_coverage_no_coverage():
    def f(tmp):
        fx, ir = _isolate(tmp); iid = _make_intake(fx, ir)
        res, pdb, ib = _observe(tmp, ir, iid, quotes=[])
        assert res["coverage"] == "NO_COVERAGE" and res["final_status"] == "NO_COVERAGE"
    _run(f)


def test_coverage_uses_q4a():
    def f(tmp):
        fx, ir = _isolate(tmp)
        base = (int(time.time())) * 1000
        iid = _make_intake(fx, ir)
        res, pdb, ib = _observe(tmp, ir, iid, instrument="XAUUSD", quotes=_covering(base))
        # Q4A consumed the covering quotes -> not NO_COVERAGE, and an observation was recorded
        assert res["coverage"] != "NO_COVERAGE" and res["final_status"] == "RECORDED" and pdb.count() == 1
    _run(f)


# ---- safety invariants ----
def test_execution_locks_and_scans():
    from broker_readonly.source_scan import scan_no_order_code
    cfg = open(os.path.join(_ROOT, "config.py"), encoding="utf-8").read()
    cc = open(os.path.join(_ROOT, "ctrader_config.py"), encoding="utf-8").read()
    assert "EXECUTION_ENABLED = False" in cfg and "CTRADER_EXECUTION_ENABLED = False" in cc
    assert scan_no_order_code([_CON]) == [] and scan_no_order_code([_PL]) == []


def test_console_does_not_reimplement_services():
    src = open(os.path.join(_CON, "server.py"), encoding="utf-8").read()
    # must CALL the tested services, not duplicate their logic
    assert "image_intake" in src and "image_confirm" in src and "image_paper_run" in src
    for banned in ("def align(", "def decide(", "class PaperDB", "def build_image_unified_signal"):
        assert banned not in src
