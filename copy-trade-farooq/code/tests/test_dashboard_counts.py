"""Dashboard consistency tests — one effective source of truth; unrelated replay excluded; refresh is
read-only; original vs effective statuses separate. No broker action; locks false."""
from __future__ import annotations
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_TL = os.path.join(_ROOT, "campaign_extractor", "trade_lifecycle")
_CON = os.path.join(_ROOT, "campaign_extractor", "paper_loop", "console")
for p in (_ROOT, _TL, _CON):
    if p not in sys.path:
        sys.path.insert(0, p)

import lifecycle_console as LC

BTC = {"intake-712866e400e54a29", "intake-ca7086828455a4d6"}


def test_top_strip_and_lifecycle_unlinked_counts_agree():
    import server as S
    ec = LC.effective_counts()
    q = S.do_queue()
    assert q["unlinked_updates_results"] == len(ec["unlinked_updates_results"])
    assert q["parent_link_coverage"] == ec["parent_link_coverage"]        # same source of truth


def test_unrelated_btc_absent_from_gold_blockers():
    tls = LC.build_timelines()
    for sid, t in tls.items():
        for b in t["blockers"]:
            assert not any(x in b for x in BTC), (sid, b)


def test_coverage_denominator_excludes_unrelated_replay():
    ec = LC.effective_counts()
    denom = int(ec["parent_link_coverage"].split("/")[1])
    assert denom == len(ec["gold_children"])                             # excludes unrelated
    assert set(ec["unrelated_replay_children"]) == BTC
    assert not (set(ec["gold_children"]) & BTC)                          # BTC not in Gold children


def test_refresh_is_read_only_no_duplicate_events():
    log = os.path.join(_ROOT, "data", "manual_image_intake_v1", "repair_events.jsonl")
    before = sum(1 for _ in open(log, encoding="utf-8")) if os.path.exists(log) else 0
    LC.effective_counts(); LC.inspect(); LC.build_timelines()            # simulate a refresh
    after = sum(1 for _ in open(log, encoding="utf-8")) if os.path.exists(log) else 0
    assert before == after                                              # refresh writes nothing


def test_refresh_buttons_and_endpoints_present():
    html = open(os.path.join(_CON, "index.html"), encoding="utf-8").read()
    assert "REFRESH LIFECYCLES" in html and "REFRESH REPAIR QUEUE" in html and "REFRESH ALL DASHBOARD COUNTS" in html
    assert "refreshTimelines()" in html and "refreshRepair()" in html and "refreshAllCounts()" in html
    assert "REFRESHING" in html and "UPDATED " in html and "REFRESH FAILED" in html
    srv = open(os.path.join(_CON, "server.py"), encoding="utf-8").read()
    assert "/api/timelines" in srv and "/api/repair_queue" in srv


def test_original_and_effective_status_separate():
    html = open(os.path.join(_CON, "index.html"), encoding="utf-8").read()
    assert "ORIGINAL IMPORT STATUS" in html and "EFFECTIVE REVIEW STATUS" in html


def test_classification_card_surfaced_in_ui_and_endpoints():
    html = open(os.path.join(_CON, "index.html"), encoding="utf-8").read()
    assert "CLASSIFICATION CORRECTIONS" in html
    assert "CONFIRM CLASSIFICATION CORRECTION" in html and "REJECT CLASSIFICATION CORRECTION" in html
    assert "confirmClassification(" in html and "rejectClassification(" in html
    srv = open(os.path.join(_CON, "server.py"), encoding="utf-8").read()
    assert "confirm_classification" in srv and "reject_classification" in srv


def test_pending_review_reconciled_with_history():
    import server as S
    hist = S.do_history(limit=500).get("recent", [])
    expected = sum(1 for r in hist if r.get("effective_status") == "IMPORTED_PENDING_REVIEW")
    assert S.do_queue()["pending_review"] == expected            # headline == history


def test_price_in_zone_candidate_matching():
    # state-independent: a SELL result child whose entry sits in the parent's zone is a HIGH candidate;
    # a child outside the zone is excluded.
    import history_repair as HR
    parents = [{"signal_id": "P1", "instrument": "XAUUSD", "direction": "SELL", "provider": "farouk",
                "ts_ms": 1, "entry_low": 4116.0, "entry_high": 4126.0},
               {"signal_id": "P2", "instrument": "XAUUSD", "direction": "SELL", "provider": "farouk",
                "ts_ms": 1, "entry_low": 4124.0, "entry_high": 4129.0}]
    child = {"instrument": "XAUUSD", "direction": "SELL", "provider": "farouk", "ts_ms": 9,
             "entry_candidate": 4119.44}
    cands = {c["parent_signal_id"]: c for c in HR.link_candidates(child, parents)}
    assert "P1" in cands and cands["P1"]["price_in_zone"] is True and cands["P1"]["confidence"] == "HIGH"
    assert "P2" not in cands                                     # 4119.44 outside 4124-4129 -> excluded


def test_history_effective_status_applies_reclass():
    import server as S
    row = [r for r in S.do_history(limit=500)["recent"] if r["intake_id"] == "intake-16aa46ce6d497d8a"][0]
    assert row["manifest_status"] == "IMPORTED_PENDING_REVIEW"
    assert row["original_confirmed_review_class"] == "SIGNAL"
    assert row["effective_class"] == "TRADE_RESULT"
    assert row["effective_status"] == "TRADE_RESULT_EXCLUDED"
    assert row["provenance"] == "REPLAY_VALIDATION_ONLY"


def test_counts_after_reclass_and_link():
    ec = LC.effective_counts()
    assert ec["signal_count"] == 3                               # parent signals 4 -> 3 (16aa46 reclassed)
    assert ec["parent_link_coverage"] == "5/5"                   # denominator 5 (incl 16aa46), all linked
    assert ec["unlinked_updates_results"] == []                  # 16aa46 now confirmed-linked to 30b8d4
    import history_repair as HR
    assert HR.confirmed_links().get("intake-16aa46ce6d497d8a") == "intake-30b8d4bfb0996dcc"


def test_no_broker_action_and_locks_false():
    for f in ("lifecycle_console.py", "effective_view.py", "history_repair.py"):
        src = open(os.path.join(_TL, f), encoding="utf-8").read()
        for bad in ("ProtoOANewOrderReq", "send_new_order(", "ProtoOAClosePositionReq"):
            assert bad not in src
    cfg = open(os.path.join(_ROOT, "config.py"), encoding="utf-8").read()
    cc = open(os.path.join(_ROOT, "ctrader_config.py"), encoding="utf-8").read()
    de = open(os.path.join(_ROOT, "campaign_extractor", "demo_executor", "config.py"), encoding="utf-8").read()
    assert "EXECUTION_ENABLED = False" in cfg and "CTRADER_EXECUTION_ENABLED = False" in cc
    assert "ORDER_SENDING_ENABLED = False" in de
