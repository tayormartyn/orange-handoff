"""
Deterministic validator + Farouk-filter tests.

All evidence here is SYNTHETIC and inline — it does NOT depend on the manually-authored
fixture expected_truth (which we are authoring together separately). Each test encodes a
frozen-regression scenario at the validator/sender level.

Reducer-level frozen tests (STOP_HIT survives permanently vs later winning re-entry;
earlier losses not erased by later gains; repeated screenshots -> one leg; event replay
== identical state hash) require the immutable event store + reducer, which are the NEXT
build step. They are listed at the bottom as TODO markers, not silently skipped.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from schema import CandidateEvent, EvidenceQuote, Status, Provenance, EventType
from sender_gate import derive_sender, is_farouk, role_for, Role, may_mutate_campaign_state
from validator import validate, ArchiveReader

V = {"extractor": "x-0.1", "model": "claude-opus-4-8", "prompt": "p-0.1"}


def _cand(**kw):
    base = dict(event_type=EventType.ENTRY.value, proposed_fields={}, source_message_keys=[],
                evidence=[], sender_handle="seascalperfarouk", confidence=0.9, versions=V)
    base.update(kw)
    return CandidateEvent(**base)


# ----------------------------------------------------------------- sender gate
def test_farouk_handle_recognised():
    h, voice = derive_sender("seascalperfarouk Posted in 🐚·sea-scalper-farouk\nBuy gold")
    assert h == "seascalperfarouk" and is_farouk(h) and role_for(h) is Role.CAMPAIGN_SOURCE


def test_columbus_is_analysis_only():
    h, voice = derive_sender(".ccolumbus Posted in 🧭·columbus-trades\nalready $2 up")
    assert h == ".ccolumbus" and not is_farouk(h)
    assert role_for(h) is Role.ANALYSIS_ONLY_CONTEXT
    assert may_mutate_campaign_state(".ccolumbus Posted in 🧭·columbus-trades\nalready $2 up") is False


def test_no_handle_fails_closed():
    h, voice = derive_sender("Posted in ⚓·captains-take\nsomething")
    assert h is None and voice == "AMBIGUOUS_NO_HANDLE"
    assert role_for(h) is Role.ANALYSIS_ONLY_CONTEXT


def test_non_farouk_candidate_rejected_by_validator():
    arc = ArchiveReader(mem_map={"m1": ".ccolumbus Posted in 🧭·columbus-trades\nGold buy 4000"})
    c = _cand(sender_handle=".ccolumbus", source_message_keys=["m1"],
              proposed_fields={"entry": "4000", "direction": "buy"},
              evidence=[EvidenceQuote("m1", "Gold buy 4000")])
    v = validate(c, arc)
    assert v.status == Status.REJECTED.value
    assert "non-Farouk" in v.reasons[0]


# --------------------------------------------------- deterministic conversions
def test_re_enter_quarter_size_is_0_25():
    txt = "seascalperfarouk Posted in 🐚·sea-scalper-farouk\nRe-enter quarter size here"
    arc = ArchiveReader(mem_map={"m1": txt})
    c = _cand(event_type=EventType.RE_ENTER.value, source_message_keys=["m1"],
              proposed_fields={"size": 0.25}, parent_ref="leg-1", leg_ref="leg-2",
              evidence=[EvidenceQuote("m1", "Re-enter quarter size here")])
    v = validate(c, arc)
    assert v.status == Status.ACCEPTED.value
    assert v.fields["size"].value == 0.25
    assert v.fields["size"].provenance == Provenance.DETERMINISTIC_CONVERSION.value


def test_half_size_is_0_50():
    txt = "seascalperfarouk Posted in 🐚\nadd half size"
    arc = ArchiveReader(mem_map={"m1": txt})
    c = _cand(event_type=EventType.ADD.value, source_message_keys=["m1"],
              proposed_fields={"size": 0.5}, evidence=[EvidenceQuote("m1", "add half size")])
    v = validate(c, arc)
    assert v.fields["size"].value == 0.50
    assert v.fields["size"].provenance == Provenance.DETERMINISTIC_CONVERSION.value


def test_leave_10_percent_remaining_0_10():
    txt = "seascalperfarouk Posted in 🐚\ntake profit, leave 10% running"
    arc = ArchiveReader(mem_map={"m1": txt})
    c = _cand(event_type=EventType.PARTIAL_CLOSE.value, source_message_keys=["m1"],
              proposed_fields={"remaining_fraction": 0.10},
              evidence=[EvidenceQuote("m1", "leave 10% running")])
    v = validate(c, arc)
    assert v.fields["remaining_fraction"].value == 0.10
    assert v.fields["remaining_fraction"].provenance == Provenance.DETERMINISTIC_CONVERSION.value


def test_take_90_off_remaining_0_10():
    txt = "seascalperfarouk Posted in 🐚\ntake 90% off the table"
    arc = ArchiveReader(mem_map={"m1": txt})
    c = _cand(event_type=EventType.PARTIAL_CLOSE.value, source_message_keys=["m1"],
              proposed_fields={"remaining_fraction": 0.10},
              evidence=[EvidenceQuote("m1", "take 90% off the table")])
    v = validate(c, arc)
    assert v.fields["remaining_fraction"].value == 0.10


# ------------------------------------------------------- qualitative stays NULL
def test_small_size_is_qualitative_null():
    txt = "seascalperfarouk Posted in 🐚\nGetting in small size on gold"
    arc = ArchiveReader(mem_map={"m1": txt})
    c = _cand(source_message_keys=["m1"], proposed_fields={"size": 0.1},  # LLM guessed 0.1
              evidence=[EvidenceQuote("m1", "Getting in small size on gold")])
    v = validate(c, arc)
    assert v.fields["size"].value is None
    assert v.fields["size"].rejected and "QUALITATIVE_ONLY" in v.fields["size"].reason


def test_low_lot_is_qualitative_null():
    txt = "seascalperfarouk Posted in 🐚\nlow lot entry"
    arc = ArchiveReader(mem_map={"m1": txt})
    c = _cand(source_message_keys=["m1"], proposed_fields={"lot": 0.05},
              evidence=[EvidenceQuote("m1", "low lot entry")])
    v = validate(c, arc)
    assert v.fields["lot"].value is None and v.fields["lot"].rejected


# ----------------------------------------------------- conditional -> no leg
def test_conditional_future_reentry_creates_no_leg():
    txt = "seascalperfarouk Posted in 🐚\nif stopped I'll give another trade"
    arc = ArchiveReader(mem_map={"m1": txt})
    c = _cand(event_type=EventType.CONDITIONAL.value, source_message_keys=["m1"],
              proposed_fields={}, evidence=[EvidenceQuote("m1", "if stopped I'll give another trade")])
    v = validate(c, arc)
    assert any("creates no leg" in r for r in v.reasons)


# --------------------------------------------------- image-only number -> NULL
def test_image_only_stop_is_media_missing_null():
    # text proves a STOP_HIT happened, but the stop PRICE is only in a screenshot we don't have
    txt = "seascalperfarouk Posted in 🐚\nstopped out on gold, see screenshot"
    arc = ArchiveReader(mem_map={"m1": txt})
    c = _cand(event_type=EventType.STOP_HIT.value, source_message_keys=["m1"], leg_ref="leg-1",
              proposed_fields={"stop": "4091.80"},  # price only in image
              evidence=[EvidenceQuote("m1", "stopped out on gold", is_image_field=False),
                        EvidenceQuote("m1", "screenshot", is_image_field=True, image_ref="img:missing")])
    v = validate(c, arc)
    # field-level: STOP_HIT event survives, but the price field is NULL/MEDIA_MISSING
    assert v.status == Status.ACCEPTED.value
    assert v.fields["stop"].value is None and v.fields["stop"].rejected
    assert "media missing" in v.fields["stop"].reason


def test_stop_hit_survives_with_unknown_price():
    # field-level rejection: a valid STOP_HIT survives even with no stop price at all
    txt = "seascalperfarouk Posted in 🐚\nthat one stopped us out"
    arc = ArchiveReader(mem_map={"m1": txt})
    c = _cand(event_type=EventType.STOP_HIT.value, source_message_keys=["m1"], leg_ref="leg-1",
              proposed_fields={"stop": "9999.99"},  # price not in text
              evidence=[EvidenceQuote("m1", "that one stopped us out")])
    v = validate(c, arc)
    assert v.status == Status.ACCEPTED.value           # event survives
    assert v.fields["stop"].value is None              # price rejected individually


# ----------------------------------------------------- hard rejections
def test_quote_not_present_rejects_event():
    arc = ArchiveReader(mem_map={"m1": "seascalperfarouk Posted in 🐚\nGold buy"})
    c = _cand(source_message_keys=["m1"], proposed_fields={"entry": "4000"},
              evidence=[EvidenceQuote("m1", "Gold sell at 4000")])  # not in text
    v = validate(c, arc)
    assert v.status == Status.REJECTED.value


def test_missing_source_message_rejects():
    arc = ArchiveReader(mem_map={})
    c = _cand(source_message_keys=["ghost"], evidence=[])
    v = validate(c, arc)
    assert v.status == Status.REJECTED.value and "not found" in v.reasons[0]


def test_cross_message_synthesis_requires_recorded_ids():
    arc = ArchiveReader(mem_map={"m1": "seascalperfarouk Posted in 🐚\nbuy gold",
                                 "m2": "seascalperfarouk Posted in 🐚\nstop 4000"})
    c = _cand(source_message_keys=["m1"],  # m2 cited in evidence but NOT recorded
              proposed_fields={}, evidence=[EvidenceQuote("m2", "stop 4000")])
    v = validate(c, arc)
    assert v.status == Status.REJECTED.value and "unrecorded" in v.reasons[0]


def test_ambiguous_leg_association_needs_review():
    txt = "seascalperfarouk Posted in 🐚\nclosed it out"
    arc = ArchiveReader(mem_map={"m1": txt})
    c = _cand(event_type=EventType.CLOSE.value, source_message_keys=["m1"], leg_ref="AMBIGUOUS",
              proposed_fields={}, evidence=[EvidenceQuote("m1", "closed it out")])
    v = validate(c, arc)
    assert v.status == Status.NEEDS_REVIEW.value


# ----------------------------------------------------- idempotency
def test_identical_candidate_identical_hashes():
    txt = "seascalperfarouk Posted in 🐚·sea-scalper-farouk\nRe-enter quarter size"
    arc = ArchiveReader(mem_map={"m1": txt})
    mk = lambda: _cand(event_type=EventType.RE_ENTER.value, source_message_keys=["m1"],
                       proposed_fields={"size": 0.25, "leg_association": "leg-1"},
                       evidence=[EvidenceQuote("m1", "Re-enter quarter size")])
    a, b = mk(), mk()
    assert a.canonical_hash() == b.canonical_hash()
    va, vb = validate(a, arc), validate(b, arc)
    assert va.accepted_hash() == vb.accepted_hash()


# ----------------------------------------------------------------- TODO (reducer step)
# These frozen regressions need the immutable event store + deterministic reducer:
#   - explicit STOP_HIT survives permanently despite later winning re-entry
#   - earlier losses cannot be erased by later gains
#   - repeated 4091.80 screenshots -> one leg, no extra wins
#   - "closed worst entry, holding best" -> closes one leg, preserves another
#   - screenshot profit unrealised unless explicit close wording exists
#   - event replay produces identical state hash
#   - impossible stop geometry flagged, never repaired
#   - provider/shadow/demo outcomes remain separate
