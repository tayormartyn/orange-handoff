"""
Reducer-level frozen-regression tests.

All events are SYNTHETIC Farouk messages, validated through the real deterministic
validator, appended to the immutable EventStore, then reduced. No dependency on the
manually-authored fixture expected_truth (parked for the joint session).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from schema import CandidateEvent, EvidenceQuote, EventType, Status
from validator import validate, ArchiveReader
from event_store import EventStore
from reducer import reduce

V = {"extractor": "x-0.1", "model": "claude-opus-4-8", "prompt": "p-0.1"}


def _F(t):
    return "seascalperfarouk Posted in 🐚·sea-scalper-farouk\n" + t


def _ev(arc, et, key, text, quote, fields=None, leg_ref=None, parent_ref=None,
        track="SHADOW", expect=Status.ACCEPTED):
    arc[key] = _F(text)
    c = CandidateEvent(event_type=et, proposed_fields=fields or {}, source_message_keys=[key],
                       evidence=[EvidenceQuote(key, quote)], sender_handle="seascalperfarouk",
                       confidence=0.9, versions=V, track=track, leg_ref=leg_ref, parent_ref=parent_ref)
    v = validate(c, ArchiveReader(mem_map=arc))
    assert v.status == expect.value, (et, v.status, v.reasons)
    return v


def _store(events):
    s = EventStore()
    for e in events:
        s.append(e)
    return s


# 1 --------------------------------------------------------------------------
def test_stop_hit_survives_permanently_vs_later_winning_reentry():
    arc = {}
    evs = [
        _ev(arc, EventType.ENTRY.value, "m1", "Buy gold 4000 stop 3990", "Buy gold 4000 stop 3990",
            fields={"direction": "buy", "entry": "4000", "stop": "3990"}, leg_ref="leg-1"),
        _ev(arc, EventType.STOP_HIT.value, "m2", "stopped out", "stopped out", leg_ref="leg-1"),
        _ev(arc, EventType.RE_ENTER.value, "m3", "re-entering quarter size", "re-entering quarter size",
            fields={"size": 0.25}, leg_ref="leg-2", parent_ref="leg-1"),
        _ev(arc, EventType.TP_HIT.value, "m4", "tp1 hit", "tp1 hit", leg_ref="leg-2"),
    ]
    st = reduce(_store(evs).events())
    legs = st.legs("SHADOW")
    assert legs["leg-1"].status == "STOPPED"          # survives the later win
    assert legs["leg-2"].status == "TP"
    assert legs["leg-2"].parent_leg_id == "leg-1"     # separate child leg
    assert st.count("SHADOW", "STOPPED") == 1 and st.count("SHADOW", "TP") == 1


# 2 --------------------------------------------------------------------------
def test_losses_not_erased_or_netted_by_later_gains():
    arc = {}
    e_entry = _ev(arc, EventType.ENTRY.value, "m1", "Buy gold 4000 stop 3990", "Buy gold 4000 stop 3990",
                  fields={"direction": "buy", "entry": "4000", "stop": "3990"}, leg_ref="leg-1")
    e_stop = _ev(arc, EventType.STOP_HIT.value, "m2", "stopped out", "stopped out", leg_ref="leg-1")
    e_re = _ev(arc, EventType.RE_ENTER.value, "m3", "re-entering", "re-entering", leg_ref="leg-2", parent_ref="leg-1")
    e_tp = _ev(arc, EventType.TP_HIT.value, "m4", "tp1 hit", "tp1 hit", leg_ref="leg-2")

    before = reduce([e_entry, e_stop]).legs("SHADOW")["leg-1"]
    after = reduce([e_entry, e_stop, e_re, e_tp]).legs("SHADOW")["leg-1"]
    # the stopped leg is preserved byte-for-byte; the later win neither removes nor flips it
    assert after.status == "STOPPED"
    assert after.closed_by_hash == before.closed_by_hash == e_stop.accepted_hash()
    assert reduce([e_entry, e_stop, e_re, e_tp]).count("SHADOW", "STOPPED") == 1


# 3 --------------------------------------------------------------------------
def test_repeated_screenshots_one_leg_no_extra_wins():
    arc = {}
    evs = [_ev(arc, EventType.ENTRY.value, "m1", "Buy gold 4000 stop 3990", "Buy gold 4000 stop 3990",
               fields={"direction": "buy", "entry": "4000", "stop": "3990"}, leg_ref="leg-1")]
    for i in range(3):
        evs.append(_ev(arc, EventType.COMMENTARY.value, f"s{i}",
                       "screenshot 4091.80 in profit", "screenshot 4091.80 in profit"))
    st = reduce(_store(evs).events())
    assert len(st.legs("SHADOW")) == 1
    assert st.legs("SHADOW")["leg-1"].status == "OPEN"
    assert st.count("SHADOW", "TP") == 0 and st.count("SHADOW", "CLOSED") == 0


# 4 --------------------------------------------------------------------------
def test_closed_worst_held_best_no_invented_percentage():
    arc = {}
    evs = [
        _ev(arc, EventType.ENTRY.value, "m1", "Buy gold 4000 stop 3990", "Buy gold 4000 stop 3990",
            fields={"direction": "buy", "entry": "4000", "stop": "3990"}, leg_ref="leg-1"),
        _ev(arc, EventType.ENTRY.value, "m2", "Buy gold 3980 stop 3970", "Buy gold 3980 stop 3970",
            fields={"direction": "buy", "entry": "3980", "stop": "3970"}, leg_ref="leg-2"),
        _ev(arc, EventType.CLOSE.value, "m3", "closed worst entry, holding best",
            "closed worst entry, holding best", leg_ref="leg-1"),
    ]
    st = reduce(_store(evs).events())
    assert st.legs("SHADOW")["leg-1"].status == "CLOSED"
    assert st.legs("SHADOW")["leg-2"].status == "OPEN"
    assert st.legs("SHADOW")["leg-2"].remaining_fraction == 1.0   # nothing invented


# 5 --------------------------------------------------------------------------
def test_screenshot_profit_unrealised_until_explicit_close():
    arc = {}
    e_entry = _ev(arc, EventType.ENTRY.value, "m1", "Buy gold 4000 stop 3990", "Buy gold 4000 stop 3990",
                  fields={"direction": "buy", "entry": "4000", "stop": "3990"}, leg_ref="leg-1")
    e_shot = _ev(arc, EventType.COMMENTARY.value, "m2", "up nicely, screenshot attached", "screenshot attached")
    e_close = _ev(arc, EventType.CLOSE.value, "m3", "closing it here now", "closing it here now", leg_ref="leg-1")

    assert reduce([e_entry, e_shot]).legs("SHADOW")["leg-1"].status == "OPEN"     # unrealised
    assert reduce([e_entry, e_shot, e_close]).legs("SHADOW")["leg-1"].status == "CLOSED"


# 6 --------------------------------------------------------------------------
def test_event_replay_identical_state_hash():
    arc = {}
    evs = [
        _ev(arc, EventType.ENTRY.value, "m1", "Buy gold 4000 stop 3990", "Buy gold 4000 stop 3990",
            fields={"direction": "buy", "entry": "4000", "stop": "3990"}, leg_ref="leg-1"),
        _ev(arc, EventType.STOP_HIT.value, "m2", "stopped out", "stopped out", leg_ref="leg-1"),
        _ev(arc, EventType.RE_ENTER.value, "m3", "re-entering", "re-entering", leg_ref="leg-2", parent_ref="leg-1"),
        _ev(arc, EventType.TP_HIT.value, "m4", "tp1 hit", "tp1 hit", leg_ref="leg-2"),
    ]
    stream = _store(evs).events()
    assert reduce(stream).state_hash() == reduce(stream).state_hash()
    # a fresh identical stream reduces to the same hash (idempotent / deterministic)
    assert reduce(_store(evs).events()).state_hash() == reduce(stream).state_hash()


# 7 --------------------------------------------------------------------------
def test_impossible_stop_geometry_flagged_never_repaired():
    arc = {}
    # long with stop ABOVE entry -> impossible
    e = _ev(arc, EventType.ENTRY.value, "m1", "Buy gold 4000 stop 4100", "Buy gold 4000 stop 4100",
            fields={"direction": "buy", "entry": "4000", "stop": "4100"}, leg_ref="leg-1")
    st = reduce([e])
    leg = st.legs("SHADOW")["leg-1"]
    assert "IMPOSSIBLE_STOP_GEOMETRY" in leg.flags
    assert leg.entry == "4000" and leg.stop == "4100"    # untouched, never repaired
    assert any(a["issue"] == "impossible stop geometry" for a in st.anomalies)


# 9 --------------------------------------------------------------------------
def test_partial_tp_is_non_terminal_leg_stays_open():
    arc = {}
    e_entry = _ev(arc, EventType.ENTRY.value, "m1", "Sell gold 4090 stop 4120", "Sell gold 4090 stop 4120",
                  fields={"direction": "sell", "entry": "4090", "stop": "4120"}, leg_ref="leg-1")
    e_tp1 = _ev(arc, EventType.PARTIAL_TP.value, "m2", "tp 1 again", "tp 1 again", leg_ref="leg-1")
    # after a partial TP the leg is NOT terminal — it stays open (PARTIAL)
    st = reduce([e_entry, e_tp1])
    leg = st.legs("SHADOW")["leg-1"]
    assert leg.status == "PARTIAL" and leg.partial_tp_count == 1
    assert leg.status not in ("TP", "CLOSED", "STOPPED")
    # ...and a later STOP_HIT can still apply (proving the leg was never closed by tp1)
    e_stop = _ev(arc, EventType.STOP_HIT.value, "m3", "stopped out", "stopped out", leg_ref="leg-1")
    st2 = reduce([e_entry, e_tp1, e_stop])
    assert st2.legs("SHADOW")["leg-1"].status == "STOPPED"


# 8 --------------------------------------------------------------------------
def test_provider_shadow_demo_outcomes_remain_separate():
    arc = {}
    evs = [
        _ev(arc, EventType.ENTRY.value, "p1", "Buy gold 4000 stop 3990", "Buy gold 4000 stop 3990",
            fields={"direction": "buy", "entry": "4000", "stop": "3990"}, leg_ref="leg-1", track="PROVIDER"),
        _ev(arc, EventType.STOP_HIT.value, "p2", "stopped out", "stopped out", leg_ref="leg-1", track="PROVIDER"),
        _ev(arc, EventType.ENTRY.value, "s1", "Buy gold 4000 stop 3990", "Buy gold 4000 stop 3990",
            fields={"direction": "buy", "entry": "4000", "stop": "3990"}, leg_ref="leg-1", track="SHADOW"),
        _ev(arc, EventType.TP_HIT.value, "s2", "tp1 hit", "tp1 hit", leg_ref="leg-1", track="SHADOW"),
    ]
    st = reduce(_store(evs).events())
    assert st.legs("PROVIDER")["leg-1"].status == "STOPPED"
    assert st.legs("SHADOW")["leg-1"].status == "TP"      # same leg id, independent track
    assert st.count("PROVIDER", "TP") == 0 and st.count("SHADOW", "STOPPED") == 0
