"""
Deterministic leg-resolver (refinement 3) unit tests — synthetic, isolated.

Covers: single-open-leg association, terminal-closes-leg, multi-leg -> NEEDS_REVIEW,
ranking carve-out -> NEEDS_REVIEW, price-match association, ambiguous price -> NEEDS_REVIEW,
zero open legs -> NEEDS_REVIEW. The watch-item (wrong leg) is guarded by asserting the
EXACT leg id chosen, and by asserting refusal where two legs match.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from schema import ValidatedEvent, ValidatedField, Status, Provenance, EventType
from validator import ArchiveReader
from leg_resolver import resolve


def VE(event_type, mkey, status=Status.NEEDS_REVIEW.value, fields=None, leg_ref=None):
    fobj = {n: ValidatedField(n, v, Provenance.LITERAL_TEXT.value) for n, v in (fields or {}).items()}
    return ValidatedEvent(event_type=event_type, status=status, fields=fobj,
                          source_message_keys=[mkey], sender_handle="seascalperfarouk",
                          versions={}, reasons=[], candidate_hash="h", track="PROVIDER",
                          leg_ref=leg_ref, parent_ref=None)


def _arc(d):
    return ArchiveReader(mem_map=d)


def test_single_open_leg_associates():
    arc = _arc({"m1": "buy gold 4000 stop 3990", "m2": "stopped out"})
    evs = [VE(EventType.ENTRY.value, "m1", status=Status.ACCEPTED.value,
              fields={"entry_low": "4000", "stop": "3990"}),
           VE(EventType.STOP_HIT.value, "m2")]
    rep = resolve(evs, arc)
    assert evs[0].leg_ref == "leg-1"
    assert evs[1].leg_ref == "leg-1" and evs[1].status == Status.ACCEPTED.value
    assert rep[-1]["outcome"] == "RESOLVED" and rep[-1]["method"] == "single_open_leg"


def test_terminal_closes_leg_then_zero_open_stays_review():
    # after the single leg is stopped, a later event has ZERO open legs -> NEEDS_REVIEW
    arc = _arc({"m1": "buy gold 4000 stop 3990", "m2": "stopped out", "m3": "take more off"})
    evs = [VE(EventType.ENTRY.value, "m1", status=Status.ACCEPTED.value, fields={"entry_low": "4000"}),
           VE(EventType.STOP_HIT.value, "m2"),
           VE(EventType.PARTIAL_CLOSE.value, "m3")]
    resolve(evs, arc)
    assert evs[1].status == Status.ACCEPTED.value      # stop resolved & closed the leg
    assert evs[2].status == Status.NEEDS_REVIEW.value  # nothing open now -> stays


def test_multi_open_legs_no_price_stays_review():
    arc = _arc({"m1": "buy gold 4000", "m2": "re-enter", "m3": "stopped out"})
    evs = [VE(EventType.ENTRY.value, "m1", status=Status.ACCEPTED.value, fields={"entry_low": "4000"}),
           VE(EventType.RE_ENTER.value, "m2", status=Status.ACCEPTED.value),
           VE(EventType.STOP_HIT.value, "m3")]
    resolve(evs, arc)
    assert evs[2].status == Status.NEEDS_REVIEW.value  # 2 open legs, no disambiguator


def test_ranking_language_stays_review_even_with_one_leg():
    # only ONE open leg, but "highest entry" is sub-fill ranking -> must NOT associate
    arc = _arc({"m1": "buy gold 4000", "m2": "take tp on highest entry hold lowest entry"})
    evs = [VE(EventType.ENTRY.value, "m1", status=Status.ACCEPTED.value, fields={"entry_low": "4000"}),
           VE(EventType.PARTIAL_TP.value, "m2")]
    rep = resolve(evs, arc)
    assert evs[1].status == Status.NEEDS_REVIEW.value
    assert "ranking" in rep[-1]["reason"]


def test_worst_best_stays_review():
    arc = _arc({"m1": "buy 4000", "m2": "re-enter", "m3": "closed the worst entry holding the best"})
    evs = [VE(EventType.ENTRY.value, "m1", status=Status.ACCEPTED.value),
           VE(EventType.RE_ENTER.value, "m2", status=Status.ACCEPTED.value),
           VE(EventType.PARTIAL_CLOSE.value, "m3")]
    resolve(evs, arc)
    assert evs[2].status == Status.NEEDS_REVIEW.value


def test_price_match_associates_exactly_one_leg():
    arc = _arc({"m1": "buy 4000 stop 3990", "m2": "buy 4080 stop 4070", "m3": "close the 4080 trade"})
    evs = [VE(EventType.ENTRY.value, "m1", status=Status.ACCEPTED.value,
              fields={"entry_low": "4000", "stop": "3990"}),
           VE(EventType.RE_ENTER.value, "m2", status=Status.ACCEPTED.value,
              fields={"entry_low": "4080", "stop": "4070"}),
           VE(EventType.CLOSE.value, "m3")]
    rep = resolve(evs, arc)
    assert evs[2].leg_ref == "leg-2" and evs[2].status == Status.ACCEPTED.value
    assert rep[-1]["method"] == "price_match"


def test_price_match_ambiguous_refuses():
    # both legs share the level 4000 -> two legs match -> must refuse
    arc = _arc({"m1": "buy 4000", "m2": "buy 4000", "m3": "close at 4000"})
    evs = [VE(EventType.ENTRY.value, "m1", status=Status.ACCEPTED.value, fields={"entry_low": "4000"}),
           VE(EventType.RE_ENTER.value, "m2", status=Status.ACCEPTED.value, fields={"entry_low": "4000"}),
           VE(EventType.CLOSE.value, "m3")]
    resolve(evs, arc)
    assert evs[2].status == Status.NEEDS_REVIEW.value  # 4000 matches both -> ambiguous


def test_event_before_any_entry_stays_review():
    arc = _arc({"m1": "take profit"})
    evs = [VE(EventType.PARTIAL_TP.value, "m1")]
    resolve(evs, arc)
    assert evs[0].status == Status.NEEDS_REVIEW.value


def test_llm_proposed_legref_is_ignored():
    # extractor put a bogus free-text leg_ref and the validator accepted it; the resolver
    # must IGNORE it and re-derive. With ranking language -> forced back to NEEDS_REVIEW.
    arc = _arc({"m1": "buy 4000", "m2": "re-enter", "m3": "closed the worst entry"})
    evs = [VE(EventType.ENTRY.value, "m1", status=Status.ACCEPTED.value),
           VE(EventType.RE_ENTER.value, "m2", status=Status.ACCEPTED.value),
           VE(EventType.CLOSE.value, "m3", status=Status.ACCEPTED.value, leg_ref="worst entry")]
    resolve(evs, arc)
    assert evs[2].status == Status.NEEDS_REVIEW.value      # bogus leg_ref not trusted
    assert evs[2].leg_ref is None


def test_price_match_skipped_when_same_message_opens_a_leg():
    # the stop+re-entry in one message: the 4080 belongs to the NEW leg's declaration,
    # so it must NOT be borrowed to disambiguate the stop -> stays NEEDS_REVIEW.
    arc = _arc({"m1": "buy 4000 stop 3990", "m2": "re-enter",
                "m3": "sl hit, re-enter SELL 4080 SL 4070"})
    evs = [VE(EventType.ENTRY.value, "m1", status=Status.ACCEPTED.value,
              fields={"entry_low": "4000", "stop": "3990"}),
           VE(EventType.RE_ENTER.value, "m2", status=Status.ACCEPTED.value),
           VE(EventType.STOP_HIT.value, "m3"),
           VE(EventType.RE_ENTER.value, "m3", status=Status.ACCEPTED.value,
              fields={"entry_low": "4080", "stop": "4070"})]
    resolve(evs, arc)
    assert evs[2].status == Status.NEEDS_REVIEW.value      # price_match suppressed
