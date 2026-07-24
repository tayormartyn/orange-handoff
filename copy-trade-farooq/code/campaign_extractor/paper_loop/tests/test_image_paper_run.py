"""Targeted tests for the minimal image->paper observation route (image_confirm + image_paper_run).
Fully isolated: synthetic intake/review/DBs in temp dirs — NEVER the real intake or real DBs."""
from __future__ import annotations
import glob
import json
import os
import shutil
import sys
import tempfile

_HERE = os.path.dirname(os.path.abspath(__file__))
_PL = os.path.dirname(_HERE)
_CE = os.path.dirname(_PL)
_ROOT = os.path.dirname(_CE)
_Q4 = os.path.join(_CE, "q4_align")
_VIS = os.path.join(_CE, "vision_v1")
for p in (_ROOT, _CE, _Q4, _PL, _VIS):
    if p not in sys.path:
        sys.path.insert(0, p)

import image_intake
import image_confirm
import image_paper_run as R
from paper_db import PaperDB
from image_bridge_db import ImageBridgeDB
from ingest import make_png, sha256_file


def _isolate(tmp):
    """Point the confirm/intake modules at temp dirs; return (fixtures, intake_root)."""
    intake_root = os.path.join(tmp, "intake")
    fixtures = os.path.join(tmp, "fixtures")
    for d in ("manifests", "review", "inbox", "processed", "rejected"):
        os.makedirs(os.path.join(intake_root, d), exist_ok=True)
    image_intake.INTAKE_ROOT = intake_root
    image_confirm.REVIEW_DIR = os.path.join(intake_root, "review")
    image_confirm.FIXTURES = fixtures
    return fixtures, intake_root


def _make_intake(fixtures, intake_root, tamper_hash=False):
    """Create a synthetic immutable image + manifest; return intake_id, manifest."""
    img = os.path.join(fixtures, "_src.png")
    os.makedirs(fixtures, exist_ok=True)
    with open(img, "wb") as f:
        f.write(make_png(80, 30))
    sha = sha256_file(img)
    claimed = ("deadbeef" * 8) if tamper_hash else sha   # tamper: file named by claimed hash, real content
    mid = "media-" + sha[:16]
    mdir = os.path.join(fixtures, mid)
    os.makedirs(mdir, exist_ok=True)
    shutil.copy2(img, os.path.join(mdir, f"original_{claimed}.png"))
    manifest = {"intake_id": "intake-" + sha[:16], "original_filename": "shot.png",
                "imported_media_id": mid,
                "original_image_sha256": claimed,
                "provider_candidate": "UNKNOWN", "platform": "DISCORD",
                "screenshot_imported_at": "2026-07-02T05:31:08Z",
                "screenshot_captured_at": None, "intake_status": "IMPORTED_PENDING_REVIEW"}
    with open(os.path.join(intake_root, "manifests", f"{manifest['intake_id']}.json"), "w") as f:
        json.dump(manifest, f)
    return manifest["intake_id"], manifest


def _answers(confirmed=True, provider="UNKNOWN", posted_at=None, provenance=None, evidence=None,
             intake_class="SIGNAL", visible_result_fields=None):
    return {"intake_class": intake_class, "instrument": "XAUUSD", "direction": "BUY",
            "entry_low": "4000.00", "entry_high": "4000.00", "stop_price": None, "target_prices": None,
            "provider": provider, "provider_posted_at": posted_at, "provider_posted_timezone": None,
            "provider_posted_provenance": provenance, "source_evidence_references": evidence or [],
            "reviewer_ref": "martyn", "semantic_class": "SIGNAL_ANNOUNCEMENT",
            "visible_result_fields": visible_result_fields, "explicit_confirmation": confirmed}


def _confirm(intake_id, manifest, **kw):
    rec = image_confirm.build_review_record(intake_id, manifest, _answers(**kw))
    saved, _p, _new = image_confirm.save_review(rec)
    return saved


def _dbs(tmp):
    return PaperDB(os.path.join(tmp, "paper.db")), ImageBridgeDB(os.path.join(tmp, "ib.db"))


def _run(fn):
    tmp = tempfile.mkdtemp(prefix="imgpr_")
    try:
        return fn(tmp)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_01_unconfirmed_blocked():
    def f(tmp):
        fx, ir = _isolate(tmp); iid, m = _make_intake(fx, ir)
        rev = _confirm(iid, m, confirmed=False)
        pdb, ib = _dbs(tmp)
        r = R.run(iid, rev["review_id"], quotes=[], paper_db=pdb, bridge_db=ib, move_file=False,
                  alert_dir=tmp)
        assert r["status"] == "REJECTED" and r["reason"] == "REVIEW_NOT_CONFIRMED"
        assert pdb.count() == 0 and ib.count() == 0                 # no obs, no bridge row
        assert not glob.glob(os.path.join(tmp, "image_paper_alert_*.json"))   # no confirmed alert
    _run(f)


def test_02_confirmed_proceeds():
    def f(tmp):
        fx, ir = _isolate(tmp); iid, m = _make_intake(fx, ir)
        rev = _confirm(iid, m)
        pdb, ib = _dbs(tmp)
        r = R.run(iid, rev["review_id"], quotes=[], paper_db=pdb, bridge_db=ib, move_file=False, alert_dir=tmp)
        assert r["status"] == "PIPELINE_VALIDATION_ONLY" and pdb.count() == 1 and ib.count() == 1
    _run(f)


def test_03_hash_mismatch_rejected():
    def f(tmp):
        fx, ir = _isolate(tmp); iid, m = _make_intake(fx, ir, tamper_hash=True)
        rev = _confirm(iid, m)
        pdb, ib = _dbs(tmp)
        r = R.run(iid, rev["review_id"], quotes=[], paper_db=pdb, bridge_db=ib, move_file=False, alert_dir=tmp)
        assert r["status"] == "REJECTED" and "HASH_MISMATCH" in r["reason"] and pdb.count() == 0
    _run(f)


def test_04_duplicate_review_no_dup_record():
    def f(tmp):
        fx, ir = _isolate(tmp); iid, m = _make_intake(fx, ir)
        r1 = _confirm(iid, m); r2 = _confirm(iid, m)                # same answers -> same review_id
        assert r1["review_id"] == r2["review_id"]
        assert len(glob.glob(os.path.join(ir, "review", "review-img-*.json"))) == 1
    _run(f)


def test_05_duplicate_orchestration_no_dup_observation():
    def f(tmp):
        fx, ir = _isolate(tmp); iid, m = _make_intake(fx, ir)
        rev = _confirm(iid, m)
        pdb, ib = _dbs(tmp)
        R.run(iid, rev["review_id"], quotes=[], paper_db=pdb, bridge_db=ib, move_file=False, alert_dir=tmp)
        r2 = R.run(iid, rev["review_id"], quotes=[], paper_db=pdb, bridge_db=ib, move_file=False, alert_dir=tmp)
        assert r2["status"] == "ALREADY_OBSERVED" and pdb.count() == 1 and ib.count() == 1
    _run(f)


def test_06_unknown_provider_unverified():
    def f(tmp):
        fx, ir = _isolate(tmp); iid, m = _make_intake(fx, ir)
        rev = _confirm(iid, m, provider="UNKNOWN")
        assert rev["provider"]["verification_state"] == "PROVIDER_UNVERIFIED"
        pdb, ib = _dbs(tmp)
        r = R.run(iid, rev["review_id"], quotes=[], paper_db=pdb, bridge_db=ib, move_file=False, alert_dir=tmp)
        assert r["provider_verification"] == "PROVIDER_UNVERIFIED"
    _run(f)


def test_07_absent_post_time_unverifiable():
    def f(tmp):
        fx, ir = _isolate(tmp); iid, m = _make_intake(fx, ir)
        rev = _confirm(iid, m, posted_at=None, provenance=None)
        assert rev["provider_posted_at"]["provenance"] == "UNVERIFIABLE"
        pdb, ib = _dbs(tmp)
        r = R.run(iid, rev["review_id"], quotes=[], paper_db=pdb, bridge_db=ib, move_file=False, alert_dir=tmp)
        assert r["post_provenance"] == "UNVERIFIABLE"
        assert r["anchors"]["PROVIDER_POST_TIME_RESULT"]["reason"] == "POST_TIME_UNVERIFIABLE"
    _run(f)


def test_08_absent_coverage_no_coverage():
    def f(tmp):
        fx, ir = _isolate(tmp); iid, m = _make_intake(fx, ir)
        rev = _confirm(iid, m)
        pdb, ib = _dbs(tmp)
        r = R.run(iid, rev["review_id"], quotes=[], paper_db=pdb, bridge_db=ib, move_file=False, alert_dir=tmp)
        assert r["coverage"] == "NO_COVERAGE"
    _run(f)


def test_09_excluded_from_aggregates():
    def f(tmp):
        fx, ir = _isolate(tmp); iid, m = _make_intake(fx, ir)
        rev = _confirm(iid, m)
        pdb, ib = _dbs(tmp)
        R.run(iid, rev["review_id"], quotes=[], paper_db=pdb, bridge_db=ib, move_file=False, alert_dir=tmp)
        # recorded under provider UNKNOWN (isolated) + status PIPELINE_VALIDATION_ONLY
        assert pdb.by_provider("FAROUK") == [] and len(pdb.by_provider("UNKNOWN")) == 1
        row = pdb.conn.execute("SELECT status FROM paper_observations").fetchone()
        assert row[0] == "PIPELINE_VALIDATION_ONLY"
    _run(f)


def test_10_alert_labels():
    def f(tmp):
        fx, ir = _isolate(tmp); iid, m = _make_intake(fx, ir)
        rev = _confirm(iid, m)
        pdb, ib = _dbs(tmp)
        r = R.run(iid, rev["review_id"], quotes=[], paper_db=pdb, bridge_db=ib, move_file=False, alert_dir=tmp)
        a = r["alert"]
        assert set(["PAPER_ONLY", "NOT_A_FILL", "NOT_AN_OUTCOME", "MANUAL_IMAGE",
                    "PIPELINE_VALIDATION_ONLY"]).issubset(set(a["labels"]))
        for token in ("MANUAL IMAGE", "PIPELINE VALIDATION ONLY", "PAPER ONLY", "NO COVERAGE",
                      "NOT A FILL", "NOT AN OUTCOME"):
            assert token in a["banner"]
    _run(f)


def test_11_execution_locks_false():
    cfg = open(os.path.join(_ROOT, "config.py"), encoding="utf-8").read()
    cc = open(os.path.join(_ROOT, "ctrader_config.py"), encoding="utf-8").read()
    assert "EXECUTION_ENABLED = False" in cfg and "CTRADER_EXECUTION_ENABLED = False" in cc


def test_12_no_order_route():
    from broker_readonly.source_scan import scan_no_order_code
    assert scan_no_order_code([_PL]) == []


# ---- the human-review safety gate that test_42 intends ----
def test_safety_unconfirmed_creates_nothing():
    def f(tmp):
        fx, ir = _isolate(tmp); iid, m = _make_intake(fx, ir)
        rev = _confirm(iid, m, confirmed=False)
        pdb, ib = _dbs(tmp)
        r = R.run(iid, rev["review_id"], quotes=[], paper_db=pdb, bridge_db=ib, move_file=False, alert_dir=tmp)
        assert r["status"] == "REJECTED"                            # no UnifiedSignal-driven observation
        assert pdb.count() == 0 and ib.count() == 0
        assert not glob.glob(os.path.join(tmp, "image_paper_alert_*.json"))
    _run(f)


def test_safety_confirmed_is_eligible():
    def f(tmp):
        fx, ir = _isolate(tmp); iid, m = _make_intake(fx, ir)
        rev = _confirm(iid, m)
        pdb, ib = _dbs(tmp)
        r = R.run(iid, rev["review_id"], quotes=[], paper_db=pdb, bridge_db=ib, move_file=False, alert_dir=tmp)
        assert r["status"] == "PIPELINE_VALIDATION_ONLY" and pdb.count() == 1
    _run(f)


# ================= SEMANTIC-CLASS GATE (SIGNAL / TRADE_RESULT / UNKNOWN) =================
def _tr_review(iid, m, ic="TRADE_RESULT"):
    rec = image_confirm.build_review_record(iid, m, _answers(intake_class=ic,
          visible_result_fields={"instrument": "BTCUSD", "entry": "59897.94", "exit": "60481.13",
                                 "pnl": "1749.57"}))
    saved, _p, _new = image_confirm.save_review(rec)
    return saved


def test_gate_trade_result_no_unified_signal():
    def f(tmp):
        fx, ir = _isolate(tmp); iid, m = _make_intake(fx, ir)
        rev = _tr_review(iid, m)
        assert rev["intake_class"] == "TRADE_RESULT" and rev["pipeline_excluded"] is True
        pdb, ib = _dbs(tmp)
        r = R.run(iid, rev["review_id"], quotes=[], paper_db=pdb, bridge_db=ib, move_file=False, alert_dir=tmp)
        assert r["status"] == "TRADE_RESULT_EXCLUDED" and "anchors" not in r   # no UnifiedSignal built
    _run(f)


def test_gate_trade_result_no_paper_observation():
    def f(tmp):
        fx, ir = _isolate(tmp); iid, m = _make_intake(fx, ir)
        rev = _tr_review(iid, m)
        pdb, ib = _dbs(tmp)
        R.run(iid, rev["review_id"], quotes=[], paper_db=pdb, bridge_db=ib, move_file=False, alert_dir=tmp)
        assert pdb.count() == 0 and ib.count() == 0
        assert not glob.glob(os.path.join(tmp, "image_paper_alert_*.json"))     # no confirmed alert
    _run(f)


def test_gate_trade_result_no_quote_anchoring():
    def f(tmp):
        fx, ir = _isolate(tmp); iid, m = _make_intake(fx, ir)
        rev = _tr_review(iid, m)
        pdb, ib = _dbs(tmp)
        r = R.run(iid, rev["review_id"], quotes=[], paper_db=pdb, bridge_db=ib, move_file=False, alert_dir=tmp)
        assert "anchors" not in r and r["reason"] == "KNOWN_RESULT_OR_CLOSED_TRADE_IMAGE"
    _run(f)


def test_gate_trade_result_excluded_from_aggregates():
    def f(tmp):
        fx, ir = _isolate(tmp); iid, m = _make_intake(fx, ir)
        rev = _tr_review(iid, m)
        pdb, ib = _dbs(tmp)
        R.run(iid, rev["review_id"], quotes=[], paper_db=pdb, bridge_db=ib, move_file=False, alert_dir=tmp)
        # not present in ANY provider ledger (no observation row at all)
        assert pdb.by_provider("FAROUK") == [] and pdb.by_provider("UNKNOWN") == [] and pdb.count() == 0
        assert rev["exclusion_reason"] == "KNOWN_RESULT_OR_CLOSED_TRADE_IMAGE"
    _run(f)


def test_gate_unknown_blocked():
    def f(tmp):
        fx, ir = _isolate(tmp); iid, m = _make_intake(fx, ir)
        rec = image_confirm.build_review_record(iid, m, _answers(intake_class="UNKNOWN", confirmed=False))
        saved, _p, _n = image_confirm.save_review(rec)
        pdb, ib = _dbs(tmp)
        r = R.run(iid, saved["review_id"], quotes=[], paper_db=pdb, bridge_db=ib, move_file=False, alert_dir=tmp)
        assert r["status"] == "BLOCKED" and pdb.count() == 0 and ib.count() == 0
    _run(f)


def test_gate_only_confirmed_signal_proceeds():
    def f(tmp):
        fx, ir = _isolate(tmp); iid, m = _make_intake(fx, ir)
        # SIGNAL + confirmed -> proceeds; SIGNAL + unconfirmed -> rejected (no obs)
        pdb, ib = _dbs(tmp)
        c = _confirm(iid, m)
        assert R.run(iid, c["review_id"], quotes=[], paper_db=pdb, bridge_db=ib, move_file=False,
                     alert_dir=tmp)["status"] == "PIPELINE_VALIDATION_ONLY"
        u = image_confirm.build_review_record(iid, m, _answers(confirmed=False))
        image_confirm.save_review(u)
        assert R.run(iid, u["review_id"], quotes=[], paper_db=pdb, bridge_db=ib, move_file=False,
                     alert_dir=tmp)["status"] == "REJECTED"
    _run(f)


def test_gate_ctrlc_before_confirm_creates_nothing():
    def f(tmp):
        fx, ir = _isolate(tmp); iid, m = _make_intake(fx, ir)
        # a review record is only WRITTEN by save_review (called after CONFIRM). Building alone (an
        # aborted/Ctrl+C flow before the phrase) writes no file and creates no observation.
        rec = image_confirm.build_review_record(iid, m, _answers(confirmed=False))
        assert not os.path.exists(os.path.join(ir, "review", f"{rec['review_id']}.json"))
        pdb, ib = _dbs(tmp)
        r = R.run(iid, rec["review_id"], quotes=[], paper_db=pdb, bridge_db=ib, move_file=False, alert_dir=tmp)
        assert r["status"] == "REJECTED" and r["reason"] == "REVIEW_NOT_FOUND" and pdb.count() == 0
    _run(f)
