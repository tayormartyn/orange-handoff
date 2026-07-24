"""
Guard tests for the June 17 THIRD held-out fixture — the FIRST CLOSED campaign.

Locked BEFORE any extractor run. Headline locked property: campaign = CLOSED via a
breakeven stop-at-entry after TPs (msg 266). Also locks the TP_LEVELS single-leg
association, the 258 NEEDS_REVIEW fills, and the realized_r NULL.
"""
import json
import os

FIXTURE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       "phase0", "fixtures", "fixture_2026-06-17.json")


def _load():
    with open(FIXTURE, encoding="utf-8") as f:
        fx = json.load(f)
    return fx, {int(m["message_id"]): m for m in fx["messages"]}


def _events(m):
    return m["expected_truth"]["events"]


def _types(m):
    return [e["event_type"] for e in _events(m)]


def test_all_14_manually_checked():
    _, by_id = _load()
    assert len(by_id) == 14
    assert all(m["expected_truth"]["manually_checked"] for m in by_id.values())


# ---- HEADLINE: the first CLOSED campaign
def test_campaign_closed_via_breakeven_stop_after_tps():
    fx, by_id = _load()
    gold = fx["authored_campaigns"]["GOLD_BUY_2026-06-17"]
    assert gold["final_state"]["campaign_status"] == "CLOSED"
    assert gold["final_state"]["closed_at_msg"] == 266
    assert gold["closed_by"] == 266
    assert "breakeven" in gold["final_state"]["closed_via"].lower()
    # msg 266 is the STOP_HIT that closes it, realized_r NULL, breakeven note
    stop = next(e for e in _events(by_id[266]) if e["event_type"] == "STOP_HIT")
    assert stop["fields"]["realized_r"]["value"] is None
    assert "breakeven" in stop["note"].lower()
    assert stop["leg_ref"] == "leg-1"


def test_open_leg_size_null_msg256():
    _, by_id = _load()
    leg = next(e for e in _events(by_id[256]) if e["event_type"] == "OPEN_LEG")
    assert leg["fields"]["direction"]["value"] == "BUY"
    assert leg["fields"]["entry_low"]["value"] == "4315"
    assert leg["fields"]["entry_high"]["value"] == "4323"
    assert leg["fields"]["stop"]["value"] == "4295"
    assert leg["fields"]["size"]["value"] is None


def test_ruling_tp_levels_single_leg_association_msg257():
    _, by_id = _load()
    tpl = next(e for e in _events(by_id[257]) if e["event_type"] == "TP_LEVELS")
    assert tpl["leg_ref"] == "leg-1"                       # SAFE single-leg association
    assert tpl["association_status"] == "CONFIRMED"
    assert tpl["fields"]["tp1"]["value"] == "4328"
    assert tpl["fields"]["tp2"]["value"] == "4332"
    assert tpl["fields"]["tp3"]["value"] == "4345"


def test_ruling_highest_lowest_needs_review_msg258():
    _, by_id = _load()
    assert _events(by_id[258])
    assert all(e["association_status"] == "NEEDS_REVIEW" for e in _events(by_id[258]))
    assert set(_types(by_id[258])) == {"PARTIAL_TP", "HOLD_REMAINDER"}


def test_partial_tps_non_terminal_msgs_262_264():
    _, by_id = _load()
    for mid in (262, 264):
        assert "PARTIAL_TP" in _types(by_id[mid])
    # 262 records pips as magnitude, explicitly not R
    pj = next(e for e in _events(by_id[262]) if e["event_type"] == "PARTIAL_TP")
    assert pj["fields"]["pips"]["value"] == "100" and "not r" in pj["note"].lower()


def test_empty_and_media_no_events():
    _, by_id = _load()
    assert _events(by_id[261]) == []                       # empty body
    assert _events(by_id[268]) == []                       # .mov breakdown
    assert "MEDIA_REFERENCE_ONLY" in by_id[268]["expected_truth"]["notes"]


def test_describing_member_is_commentary_msg260():
    _, by_id = _load()
    assert _events(by_id[260]) == []                       # "he follow the rules..." = context


def test_closed_state_needs_leg_association_limitation_logged():
    fx, _ = _load()
    lims = fx["authored_campaigns"]["GOLD_BUY_2026-06-17"]["known_limitations"]
    assert any("leg association" in l.lower() and "closed" in l.lower() for l in lims)


# ---- master truth-hash lock
LOCKED_TRUTH_HASH = "c8b1c3ebfb46441e113570f798e951ffce35829c4e4b50a052f9c2b8eba20339"


def test_authored_truth_hash_locked():
    import hashlib
    fx, _ = _load()
    payload = {"authored_campaigns": fx["authored_campaigns"],
               "expected_truth": {m["message_id"]: m["expected_truth"] for m in fx["messages"]}}
    h = hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
    assert h == LOCKED_TRUTH_HASH, f"June 17 authored truth changed! got {h}"
    assert fx.get("authored_truth_hash") == LOCKED_TRUTH_HASH
