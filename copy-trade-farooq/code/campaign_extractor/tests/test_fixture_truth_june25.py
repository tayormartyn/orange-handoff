"""
Guard tests for the June 25 SECOND held-out blind-test fixture.

Locked BEFORE any extractor run. Locks facts AND uncertainty: 349 remaining NULL,
351 remaining 0.10 (allowlisted), campaign OPEN, TP4/TP5 logged as schema limitation.
"""
import json
import os

FIXTURE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       "phase0", "fixtures", "fixture_2026-06-25.json")


def _load():
    with open(FIXTURE, encoding="utf-8") as f:
        fx = json.load(f)
    return fx, {int(m["message_id"]): m for m in fx["messages"]}


def _events(m):
    return m["expected_truth"]["events"]


def _types(m):
    return [e["event_type"] for e in _events(m)]


def test_all_8_manually_checked():
    _, by_id = _load()
    assert len(by_id) == 8
    assert all(m["expected_truth"]["manually_checked"] for m in by_id.values())


def test_open_leg_tp1_3_literal_size_null_msg344():
    _, by_id = _load()
    leg = next(e for e in _events(by_id[344]) if e["event_type"] == "OPEN_LEG")
    f = leg["fields"]
    assert f["direction"]["value"] == "BUY"
    assert f["entry_low"]["value"] == "4006" and f["entry_high"]["value"] == "4016"
    assert f["stop"]["value"] == "3970"
    assert f["tp1"]["value"] == "4022" and f["tp2"]["value"] == "4027" and f["tp3"]["value"] == "4040"
    assert f["size"]["value"] is None                       # not stated -> NULL
    # TP4/TP5 must NOT appear as invented fields
    assert "tp4" not in f and "tp5" not in f


def test_tp_ladder_schema_limitation_logged():
    fx, _ = _load()
    lims = fx["authored_campaigns"]["GOLD_BUY_2026-06-25"]["known_limitations"]
    sl = next((l for l in lims if "SCHEMA COVERAGE" in l), "")
    assert "TP4=4065" in sl and "TP5='open'" in sl       # documented, not dropped


# ---- the LOCKED UNCERTAINTY
def test_msg349_hold25_remaining_null():
    _, by_id = _load()
    e = next(x for x in _events(by_id[349]) if x["event_type"] == "HOLD_REMAINDER")
    assert e["fields"]["remaining_fraction"]["value"] is None
    assert e["fields"]["remaining_fraction"]["provenance"] == "UNSUPPORTED"


def test_msg351_leave10_remaining_0_10_deterministic():
    _, by_id = _load()
    e = next(x for x in _events(by_id[351]) if x["event_type"] == "PARTIAL_CLOSE")
    assert e["fields"]["remaining_fraction"]["value"] == 0.10
    assert e["fields"]["remaining_fraction"]["provenance"] == "DETERMINISTIC_CONVERSION"


def test_campaign_ends_open():
    fx, by_id = _load()
    gold = fx["authored_campaigns"]["GOLD_BUY_2026-06-25"]
    assert gold["final_state"]["campaign_status"] == "OPEN"
    assert gold["final_state"]["remaining_fraction"] == 0.10
    assert gold["final_state"]["full_close"] is False
    assert gold["closed_by"] is None
    assert not any("CLOSE" == t for m in by_id.values() for t in _types(m))   # no full CLOSE


def test_msg345_partial_tp_plus_move_stop():
    _, by_id = _load()
    assert set(_types(by_id[345])) == {"PARTIAL_TP", "MOVE_STOP"}


def test_one_leg_only():
    fx, _ = _load()
    gold = fx["authored_campaigns"]["GOLD_BUY_2026-06-25"]
    assert gold["leg_count"] == 1 and list(gold["legs"]) == ["leg-1"]


def test_empty_and_media_no_events():
    _, by_id = _load()
    assert _events(by_id[346]) == []                        # empty body
    assert _events(by_id[350]) == []                        # .mov media reference
    assert "MEDIA_REFERENCE_ONLY" in by_id[350]["expected_truth"]["notes"]


def test_pip_magnitude_and_member_directed_are_commentary():
    _, by_id = _load()
    assert _events(by_id[347]) == []                        # "300 pips"
    assert _events(by_id[348]) == []                        # "show profit in bragging-rights"


# ---- master truth-hash lock
LOCKED_TRUTH_HASH = "22041d7aeb06bd373c21e23cab42eaf8d422b4913625da518bd3dd6d4c649bce"


def test_authored_truth_hash_locked():
    import hashlib
    fx, _ = _load()
    payload = {"authored_campaigns": fx["authored_campaigns"],
               "expected_truth": {m["message_id"]: m["expected_truth"] for m in fx["messages"]}}
    h = hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
    assert h == LOCKED_TRUTH_HASH, f"June 25 authored truth changed! got {h}"
    assert fx.get("authored_truth_hash") == LOCKED_TRUTH_HASH
