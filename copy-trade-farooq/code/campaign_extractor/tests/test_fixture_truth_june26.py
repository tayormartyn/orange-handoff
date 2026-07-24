"""
Guard tests for the June 26 fixture expected_truth.

This is the FIXED human-authored ground truth (Martyn, joint session). These tests lock
the four rulings and the structural decisions so that the LLM candidate extractor — built
last — can be checked AGAINST this truth and can NEVER silently alter it. If someone edits
the fixture truth, these tests break.
"""
import json
import os

FIXTURE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       "phase0", "fixtures", "fixture_2026-06-26.json")


def _load():
    with open(FIXTURE, encoding="utf-8") as f:
        fx = json.load(f)
    return fx, {int(m["message_id"]): m for m in fx["messages"]}


def _events(m):
    return m["expected_truth"]["events"]


def _types(m):
    return [e["event_type"] for e in _events(m)]


def test_all_messages_manually_checked():
    _, by_id = _load()
    assert by_id and all(m["expected_truth"]["manually_checked"] for m in by_id.values())


def test_ruling1_msg352_size_null_qualitative():
    _, by_id = _load()
    open_leg = next(e for e in _events(by_id[352]) if e["event_type"] == "OPEN_LEG")
    size = open_leg["fields"]["size"]
    assert size["value"] is None
    assert size["size_quality"] == "QUALITATIVE_ONLY"
    assert size["provenance"] == "UNSUPPORTED"
    # entry/stop ARE literal
    assert open_leg["fields"]["stop"]["value"] == "4120"
    assert open_leg["fields"]["entry_low"]["value"] == "4078"


def test_ruling2_msg360_stop_realized_r_null_and_reentry():
    _, by_id = _load()
    types = _types(by_id[360])
    assert "STOP_HIT" in types and "RE_ENTER" in types        # two events, one message
    stop = next(e for e in _events(by_id[360]) if e["event_type"] == "STOP_HIT")
    assert stop["fields"]["realized_r"]["value"] is None       # no loss magnitude asserted
    assert "breakeven" in stop["note"].lower()
    reenter = next(e for e in _events(by_id[360]) if e["event_type"] == "RE_ENTER")
    assert reenter["leg_ref"] == "leg-3"
    assert reenter["fields"]["size"]["value"] is None          # 'low lot' -> NULL


def test_ruling3_msg357_partial_tp_non_terminal():
    _, by_id = _load()
    assert _types(by_id[357]) == ["PARTIAL_TP"]
    assert "non-terminal" in _events(by_id[357])[0]["note"].lower()


def test_ruling4_msg361_366_association_needs_review():
    _, by_id = _load()
    for mid in (361, 366):
        assert _events(by_id[mid]), f"msg {mid} should have events"
        assert all(e["association_status"] == "NEEDS_REVIEW" for e in _events(by_id[mid]))


def test_reentry_quarter_size_conversion_msg355():
    _, by_id = _load()
    re = next(e for e in _events(by_id[355]) if e["event_type"] == "RE_ENTER")
    assert re["fields"]["size"]["value"] == 0.25
    assert re["fields"]["size"]["provenance"] == "DETERMINISTIC_CONVERSION"


def test_conditional_plans_create_no_leg_msgs_362_368():
    _, by_id = _load()
    for mid in (362, 368):
        assert any(e["event_type"] == "CONDITIONAL" for e in _events(by_id[mid]))
    # conditional events never carry a leg
    for mid in (362, 368):
        for e in _events(by_id[mid]):
            if e["event_type"] == "CONDITIONAL":
                assert e["leg_ref"] is None


def test_empty_messages_are_media_missing_no_events():
    _, by_id = _load()
    for mid in (359, 363, 371, 377):
        assert _events(by_id[mid]) == []
        assert "MEDIA_MISSING" in by_id[mid]["expected_truth"]["notes"]


def test_btc_is_separate_campaign_excluded_from_gold():
    fx, by_id = _load()
    assert by_id[376]["expected_truth"]["campaign"] == "BTC_BUY_2026-06-26"
    assert by_id[379]["expected_truth"]["campaign"] == "BTC_BUY_2026-06-26"
    # no gold message references BTC, and the BTC open leg is asset BTCUSD
    open_leg = next(e for e in _events(by_id[376]) if e["event_type"] == "OPEN_LEG")
    assert open_leg["fields"]["asset"]["value"] == "BTCUSD"
    assert fx["authored_campaigns"]["BTC_BUY_2026-06-26"]["excluded_from_gold"] is True


def test_campaign_close_is_msg374():
    _, by_id = _load()
    assert "CLOSE" in _types(by_id[374])


def test_pip_magnitudes_are_commentary_not_r():
    _, by_id = _load()
    # 367 (100+ pips), 372 (150 pips) carry no events
    assert _events(by_id[367]) == [] and _events(by_id[372]) == []
    # 365 records pips as literal MAGNITUDE, explicitly not R, on a non-terminal partial TP
    pj = next(e for e in _events(by_id[365]) if e["event_type"] == "PARTIAL_TP")
    assert pj["fields"]["pips"]["value"] == "90"
    assert "not r" in pj["note"].lower()
