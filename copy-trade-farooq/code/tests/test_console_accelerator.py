"""Signal Review Accelerator tests: effective status, parent linking, queue, safety."""
from __future__ import annotations
import json
import os
import shutil
import sys
import tempfile

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_CON = os.path.join(_ROOT, "campaign_extractor", "paper_loop", "console")
for p in (_ROOT, os.path.join(_ROOT, "campaign_extractor"),
          os.path.join(_ROOT, "campaign_extractor", "q4_align"),
          os.path.join(_ROOT, "campaign_extractor", "paper_loop"),
          os.path.join(_ROOT, "campaign_extractor", "vision_v1"), _CON):
    if p not in sys.path:
        sys.path.insert(0, p)
os.chdir(_ROOT)

import server as C
import console_ext as EXT
import ocr_adapter as O
import image_intake
import image_confirm
from paper_db import PaperDB
from image_bridge_db import ImageBridgeDB
from ingest import make_png, sha256_file


def _run(fn):
    tmp = tempfile.mkdtemp(prefix="acc_")
    try:
        return fn(tmp)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def _isolate(tmp):
    ir = os.path.join(tmp, "intake"); fx = os.path.join(tmp, "fixtures")
    for d in ("manifests", "review", "inbox", "processed", "rejected"):
        os.makedirs(os.path.join(ir, d), exist_ok=True)
    os.makedirs(fx, exist_ok=True)
    image_intake.INTAKE_ROOT = ir
    image_confirm.REVIEW_DIR = os.path.join(ir, "review")
    image_confirm.FIXTURES = fx
    return fx, ir


def _make_intake(fx, ir):
    img = os.path.join(fx, "_s.png"); open(img, "wb").write(make_png(80, 30))
    sha = sha256_file(img); mid = "media-" + sha[:16]
    os.makedirs(os.path.join(fx, mid), exist_ok=True)
    shutil.copy2(img, os.path.join(fx, mid, f"original_{sha}.png"))
    m = {"intake_id": "intake-" + sha[:16], "original_filename": "s.png", "imported_media_id": mid,
         "original_image_sha256": sha, "screenshot_imported_at": "2026-07-02T05:00:00Z",
         "intake_status": "IMPORTED_PENDING_REVIEW", "duplicate": False}
    mp = os.path.join(ir, "manifests", f"{m['intake_id']}.json")
    json.dump(m, open(mp, "w"))
    return m["intake_id"], mp


# ---- prefill confidence tiers (drive the frontend HIGH/MEDIUM/LOW) ----
def test_high_confidence_prefill():
    p = O.propose({"lines": [{"text": "XAUUSD BUY"}], "full_text": "XAUUSD BUY Entry 3300 SL 3295 TP 3315"})
    assert p["fields"]["instrument"]["confidence"] == "HIGH" and p["fields"]["instrument"]["value"] == "XAUUSD"


def test_low_ambiguous_unresolved():
    p = O.propose({"lines": [], "full_text": "XAUUSD BUY Entry 33OO SL 3295 TP 3315"})
    e = p["fields"]["entry_low"]
    assert e["value"] is None and e["confidence"] == "LOW" and e["reason"] == "AMBIGUOUS_DIGITS"


# ---- effective status (history) without touching the manifest ----
def test_effective_status_latest_wins_manifest_unchanged():
    def f(tmp):
        fx, ir = _isolate(tmp); iid, mp = _make_intake(fx, ir)
        before = open(mp).read()
        EXT.record_effective_status(iid, "SIGNAL_RECORDED", root=os.path.join(ir, "review"))
        EXT.record_effective_status(iid, "NO_COVERAGE", root=os.path.join(ir, "review"))
        assert EXT.latest_effective_status(iid, root=os.path.join(ir, "review")) == "NO_COVERAGE"
        assert open(mp).read() == before                      # manifest byte-identical
    _run(f)


def test_effective_from_final_map():
    assert EXT.effective_from_final("RECORDED") == "SIGNAL_RECORDED"
    assert EXT.effective_from_final("TRADE_UPDATE_EXCLUDED") == "TRADE_UPDATE_EXCLUDED"
    assert EXT.effective_from_final("BLOCKED") == "UNKNOWN_BLOCKED"


def test_do_observe_persists_status_before_clear():
    def f(tmp):
        fx, ir = _isolate(tmp); iid, _ = _make_intake(fx, ir)
        pdb, ib = PaperDB(os.path.join(tmp, "p.db")), ImageBridgeDB(os.path.join(tmp, "ib.db"))
        rev_root = os.path.join(ir, "review")
        r = C.do_observe({"intake_id": iid, "intake_class": "SIGNAL", "instrument": "XAUUSD",
                          "direction": "BUY", "entry_low": "4000.00", "entry_high": "4000.20",
                          "provider": "UNKNOWN", "confirm": True},
                         root=ir, paper_db=pdb, bridge_db=ib, alert_dir=tmp, quotes=[], move_file=False,
                         status_root=rev_root)
        assert r["effective_status"] == "NO_COVERAGE"          # persisted result returned to the UI
        assert EXT.latest_effective_status(iid, root=rev_root) == "NO_COVERAGE"   # event written
    _run(f)


def test_failed_confirmation_keeps_form():
    # the frontend clears ONLY on a non-error response; error path returns early keeping the form
    html = open(os.path.join(_CON, "index.html"), encoding="utf-8").read()
    assert "if(j.error)" in html and "return; }" in html
    assert html.index("if(j.error)") < html.index("clearForm();")   # error guard precedes clear


# ---- parent linking ----
REC = [{"observation_id": "o1", "provider": "seascalperfarouk", "instrument": "XAUUSD",
        "direction": "BUY", "time": "2026-07-02T08:00:00Z"}]


def test_confident_parent_suggested():
    s = O and EXT.suggest_parent({"provider": "seascalperfarouk", "instrument": "XAUUSD",
                                  "direction": "BUY", "post_time": "2026-07-02T09:00:00Z"}, REC)
    assert s["suggested"] == "o1" and s["confidence"] == "HIGH"


def test_ambiguous_parent_unlinked():
    rec = REC + [{"observation_id": "o2", "provider": "seascalperfarouk", "instrument": "XAUUSD",
                  "direction": "BUY", "time": "2026-07-02T08:00:00Z"}]
    s = EXT.suggest_parent({"provider": "seascalperfarouk", "instrument": "XAUUSD",
                            "direction": "BUY", "post_time": "2026-07-02T09:00:00Z"}, rec)
    assert s["suggested"] is None and s["reason"] == "AMBIGUOUS_MULTIPLE_MATCHES"


def test_manual_link_one_parent():
    def f(tmp):
        r = EXT.record_link("o1", "child-1", "UPDATE", root=tmp)
        assert r["linked"] and len(EXT.links_for_child("child-1", root=tmp)) == 1
        assert "child-1" in EXT.linked_children(root=tmp)
    _run(f)


def test_link_requires_human_approval():
    assert C.do_link({"parent_observation_id": "o", "intake_id": "i", "approve": False})["linked"] is False


def test_link_creates_no_observation_or_cohort():
    def f(tmp):
        EXT.record_link("o1", "c1", "UPDATE", root=tmp)
        files = os.listdir(tmp)
        assert files == ["parent_link_events.jsonl"]          # only the append-only link log
        assert not any(x.endswith(".db") for x in files)      # no paper/observation DB created
    _run(f)


# ---- queue ----
def test_queue_summary_reuses_records():
    q = EXT.queue_summary(statuses={"i1": "UNKNOWN_BLOCKED"},
                          bundles=[{"intake_id": "u1", "review": {"intake_class": "TRADE_UPDATE"}}],
                          links=set(), cohort={"complete": 0, "target": 5})
    assert q["unknown_blocked"] == 1 and q["unlinked_updates_results"] == 1
    assert q["cohort_headline"] == "COHORT ONE: 0 / 5" and q["ready_for_next_screenshot"] is True


# ---- safety ----
def test_provider_not_verified_by_ocr():
    p = O.propose({"lines": [], "full_text": "SeaScalper-Farouk XAUUSD BUY 3300 SL 3295 TP 3315"})
    assert p["provider_candidate"]["verification_state"] == "PROVIDER_UNVERIFIED"


def test_execution_locks_and_scans():
    from broker_readonly.source_scan import scan_no_order_code
    cfg = open(os.path.join(_ROOT, "config.py"), encoding="utf-8").read()
    cc = open(os.path.join(_ROOT, "ctrader_config.py"), encoding="utf-8").read()
    assert "EXECUTION_ENABLED = False" in cfg and "CTRADER_EXECUTION_ENABLED = False" in cc
    assert scan_no_order_code([_CON]) == []
