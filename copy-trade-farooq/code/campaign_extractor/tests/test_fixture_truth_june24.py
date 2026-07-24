"""
Guard tests for the June 24 HELD-OUT blind-test fixture expected_truth.

Locked BEFORE any extractor run. These tests lock the FACTS and — critically — the
UNCERTAINTY (remaining_fraction NULL, campaign OPEN, one leg only). A later pass cannot
quietly "improve" an unresolved value into a guessed number without breaking these.
"""
import json
import os

FIXTURE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       "phase0", "fixtures", "fixture_2026-06-24.json")


def _load():
    with open(FIXTURE, encoding="utf-8") as f:
        fx = json.load(f)
    return fx, {int(m["message_id"]): m for m in fx["messages"]}


def _events(m):
    return m["expected_truth"]["events"]


def _types(m):
    return [e["event_type"] for e in _events(m)]


def test_all_17_manually_checked():
    _, by_id = _load()
    assert len(by_id) == 17
    assert all(m["expected_truth"]["manually_checked"] for m in by_id.values())


def test_open_leg_size_null_qualitative_msg327():
    _, by_id = _load()
    leg = next(e for e in _events(by_id[327]) if e["event_type"] == "OPEN_LEG")
    assert leg["fields"]["size"]["value"] is None
    assert leg["fields"]["size"]["size_quality"] == "QUALITATIVE_ONLY"
    assert leg["fields"]["entry_low"]["value"] == "4030"
    assert leg["fields"]["entry_high"]["value"] == "4045"
    assert leg["fields"]["stop"]["value"] == "4130"


# ---- R1/R2: the LOCKED UNCERTAINTY — every partial close has remaining_fraction NULL
def test_all_partial_closes_remaining_fraction_null():
    _, by_id = _load()
    pcs = [e for m in by_id.values() for e in _events(m) if e["event_type"] == "PARTIAL_CLOSE"]
    assert len(pcs) == 4                                  # msgs 336, 339, 342, 343
    for e in pcs:
        rf = e["fields"]["remaining_fraction"]
        assert rf["value"] is None, "remaining_fraction must stay NULL (locked uncertainty)"
        assert rf["provenance"] == "UNSUPPORTED"


def test_r1_taking_morphology_locked_as_null():
    _, by_id = _load()
    for mid in (336, 343):                                # 'taking 50%/90% off'
        e = next(x for x in _events(by_id[mid]) if x["event_type"] == "PARTIAL_CLOSE")
        assert e["fields"]["remaining_fraction"]["value"] is None
        assert "morphology" in e["note"].lower()


def test_r2_25pct_not_allowlisted_null_msg339():
    _, by_id = _load()
    e = next(x for x in _events(by_id[339]) if x["event_type"] == "PARTIAL_CLOSE")
    assert e["fields"]["remaining_fraction"]["value"] is None


# ---- the campaign-level locked uncertainty
def test_campaign_ends_open_no_full_close():
    fx, _ = _load()
    gold = fx["authored_campaigns"]["GOLD_SELL_2026-06-24"]
    assert gold["final_state"]["campaign_status"] == "OPEN"
    assert gold["final_state"]["remaining_fraction"] is None
    assert gold["final_state"]["full_close"] is False
    assert gold["closed_by"] is None
    # no message carries a full CLOSE event
    _, by_id = _load()
    assert not any("CLOSE" == t for m in by_id.values() for t in _types(m))


# ---- R3: exactly one leg; second/Whaleroom entry not invented
def test_r3_one_leg_only_second_is_needs_review():
    fx, by_id = _load()
    gold = fx["authored_campaigns"]["GOLD_SELL_2026-06-24"]
    assert gold["leg_count"] == 1 and list(gold["legs"]) == ["leg-1"]
    assert any("Whaleroom" in nr for nr in gold["needs_review"])
    # msg 330 itself creates no leg
    assert _events(by_id[330]) == []


# ---- R4: BTC is not a campaign and not a leg
def test_r4_btc_no_leg_no_campaign_msg341():
    fx, by_id = _load()
    assert by_id[341]["expected_truth"]["campaign"] is None
    assert _events(by_id[341]) == []
    assert fx["authored_campaigns"]["BTC"]["present"] is False


# ---- R5: .mov media reference -> no events
def test_r5_mov_media_reference_no_events_msg338():
    _, by_id = _load()
    assert _events(by_id[338]) == []
    assert "MEDIA_REFERENCE_ONLY" in by_id[338]["expected_truth"]["notes"]


# ---- conditional plan -> no leg, future numbers not extracted
def test_conditional_plan_no_leg_msg335():
    _, by_id = _load()
    assert _types(by_id[335]) == ["CONDITIONAL"]
    assert by_id[335]["expected_truth"]["events"][0]["leg_ref"] is None
    # the 4070-4080 future zone must NOT appear as an entry field anywhere
    assert all("4070" not in json.dumps(e.get("fields", {}))
               for e in _events(by_id[335]))


def test_empty_bodies_media_missing_no_events():
    _, by_id = _load()
    for mid in (329, 332, 337):
        assert _events(by_id[mid]) == []
        assert "MEDIA_MISSING" in by_id[mid]["expected_truth"]["notes"]


def test_partial_tp_is_non_terminal_and_pips_not_r():
    _, by_id = _load()
    for mid in (328, 334):
        tp = next(e for e in _events(by_id[mid]) if e["event_type"] == "PARTIAL_TP")
        assert "non-terminal" in tp["note"].lower()
        assert "not r" in tp["note"].lower()


def test_morphology_limitation_logged():
    fx, _ = _load()
    lims = fx["authored_campaigns"]["GOLD_SELL_2026-06-24"]["known_limitations"]
    assert any("morphology" in l.lower() for l in lims)


# ---- the master lock: the whole authored-truth payload is pinned to one hash
LOCKED_TRUTH_HASH = "a230ce7a704b2d301a00451f91c472a30a77f042dbabd9e47c1888ae3bcba4a2"


def test_authored_truth_hash_locked():
    import hashlib
    fx, _ = _load()
    payload = {"authored_campaigns": fx["authored_campaigns"],
               "expected_truth": {m["message_id"]: m["expected_truth"] for m in fx["messages"]}}
    h = hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
    assert h == LOCKED_TRUTH_HASH, (
        f"June 24 authored truth changed! got {h}. The held-out truth is frozen — "
        f"refine the extractor/prompt, never the truth.")
    assert fx.get("authored_truth_hash") == LOCKED_TRUTH_HASH
