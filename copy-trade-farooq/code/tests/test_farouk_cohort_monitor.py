"""Read-only tests for farouk_cohort_monitor.assess() — cohort inclusion rules + safety."""
from __future__ import annotations
import hashlib
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)
os.chdir(_ROOT)

import farouk_cohort_monitor as M


def bundle(intake_id="i1", intake_class="SIGNAL", provider="seascalperfarouk", verified=True,
           confirmed=True, duplicate=False, has_obs=True, coverage=None, reviewer="martyn",
           instrument="XAUUSD", posted=None):
    rv = {"review_id": "review-img-" + intake_id, "intake_id": intake_id, "intake_class": intake_class,
          "explicit_confirmation_state": "CONFIRMED" if confirmed else "NOT_CONFIRMED",
          "provider": {"value": provider,
                       "verification_state": "PROVIDER_VERIFIED" if verified else "PROVIDER_UNVERIFIED"},
          "provider_posted_at": {"value": posted, "provenance": "UNVERIFIABLE" if posted is None else "DISCORD_MESSAGE_ID_OR_LINK"},
          "review_created_at_utc": "2026-07-02T08:00:00Z", "reviewer_ref": reviewer,
          "fields": {"instrument": {"value": instrument}, "direction": {"value": "BUY"}}}
    m = {"intake_id": intake_id, "screenshot_imported_at": "2026-07-02T07:59:00Z", "duplicate": duplicate}
    po = ({"observation_id": "paperobs-" + intake_id, "status": "PAPER_READY",
           "reason_code": coverage, "decision_timestamp": "2026-07-02T08:00:01Z",
           "persisted_utc": "2026-07-02T08:00:02Z"} if has_obs else None)
    br = ({"paper_observation_id": "paperobs-" + intake_id, "intake_id": intake_id,
           "human_confirmed_actionable_result": {"reason": coverage},
           "capture_latency_s": None, "import_latency_s": 1.0, "actionable_latency_s": 2.0}
          if has_obs else None)
    return {"intake_id": intake_id, "review": rv, "manifest": m, "paper_obs": po, "bridge_obs": br}


def test_trade_result_contributes_zero():
    r = M.assess([bundle(intake_class="TRADE_RESULT")])
    assert r["complete"] == 0 and r["counts"]["trade_result_excluded"] == 1


def test_unknown_contributes_zero():
    r = M.assess([bundle(intake_class="UNKNOWN")])
    assert r["complete"] == 0 and r["counts"]["blocked"] == 1


def test_duplicate_contributes_once_at_most():
    r = M.assess([bundle("i1", duplicate=False), bundle("i1dup", duplicate=True)])
    assert r["complete"] == 1 and r["counts"]["duplicates_excluded"] == 1


def test_pipeline_validation_contributes_zero():
    # a pipeline-validation record is provider-unverified -> excluded, shown as PROVIDER_UNVERIFIED
    r = M.assess([bundle(verified=False)])
    assert r["complete"] == 0 and r["counts"]["provider_unverified"] == 1


def test_non_farouk_contributes_zero():
    r = M.assess([bundle(provider="navigatorjosh")])
    assert r["complete"] == 0 and r["counts"]["non_farouk_excluded"] == 1


def test_unconfirmed_contributes_zero():
    r = M.assess([bundle(confirmed=False)])
    assert r["complete"] == 0 and r["counts"]["awaiting_confirmation"] == 1


def test_five_eligible_complete():
    r = M.assess([bundle(f"g{i}") for i in range(5)])
    assert r["complete"] == 5 and r["headline"] == "COHORT ONE: 5 / 5 COMPLETE"
    assert [m["cohort_position"] for m in r["cohort_members"]] == [1, 2, 3, 4, 5]


def test_caps_at_five():
    r = M.assess([bundle(f"g{i}") for i in range(7)])
    assert r["complete"] == 5 and r["headline"] == "COHORT ONE: 5 / 5 COMPLETE"


def test_coverage_split():
    r = M.assess([bundle("a", coverage=None), bundle("b", coverage="NO_COVERAGE")])
    assert r["complete"] == 2 and r["counts"]["recorded_successfully"] == 1 and r["counts"]["no_coverage"] == 1


def test_missing_timestamps_not_invented():
    r = M.assess([bundle("x", confirmed=False, has_obs=False, posted=None)])
    mrec = r["members"][0]
    assert mrec["provider_posted_time"] is None and mrec["q4a_decision_time"] is None
    assert mrec["paper_recorded_time"] is None      # not fabricated


def test_synthetic_excluded():
    r = M.assess([bundle("test-1", reviewer="testbot")])
    assert r["complete"] == 0 and r["members"][0]["cohort_status"] == "EXCLUDED_SYNTHETIC"


def test_monitor_modifies_no_evidence_db():
    def sha(p):
        return hashlib.sha256(open(p, "rb").read()).hexdigest() if os.path.exists(p) else None
    # NOTE: ctrader_quotes_v1.db is deliberately NOT watched — it is live-appended by the running
    # quote recorder and the cohort monitor never reads or writes it. These are the evidence DBs
    # the monitor could conceivably touch; it must leave them byte-identical.
    watched = ["data/signal_archive.db", "data/shadow.db",
               "campaign_extractor/mpk/data/mpk_campaigns_v1.db"]
    # include the paper/bridge stores if they exist (genuine console usage may have created them);
    # the monitor is read-only and must leave every evidence store byte-identical.
    for extra in ("data/paper_observations_v1.db", "data/image_bridge_observations_v1.db"):
        if os.path.exists(extra):
            watched.append(extra)
    before = {p: sha(p) for p in watched}
    M.main()                                        # full live run (writes only to data/reports)
    after = {p: sha(p) for p in watched}
    assert before == after                          # monitor modifies NO evidence DB


def test_execution_locks_and_no_order_code():
    cfg = open(os.path.join(_ROOT, "config.py"), encoding="utf-8").read()
    cc = open(os.path.join(_ROOT, "ctrader_config.py"), encoding="utf-8").read()
    assert "EXECUTION_ENABLED = False" in cfg and "CTRADER_EXECUTION_ENABLED = False" in cc
    src = open(os.path.join(_ROOT, "farouk_cohort_monitor.py"), encoding="utf-8").read()
    for bad in ("new_order", "place_order", "amend", "cancel_order", "close_position", "execute_trade"):
        assert bad not in src
