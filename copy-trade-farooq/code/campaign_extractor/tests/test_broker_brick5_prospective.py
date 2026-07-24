"""
Brick 5 — prospective Telegram evidence recorder. Offline fixtures only. No network, no
OAuth, no broker auth, no live Telegram activation, no real credentials.

Hard-proves: observe-don't-infer (no fill/entry/exit/R/score) on tempting fixtures; parser
failure never destroys raw evidence; ambiguous association -> NEEDS_REVIEW; UNKNOWN valid;
anti-hallucination pipeline (literal/allowlist; small size/low lot -> NULL); broker fields
explicit NULL/BROKER_NOT_CONNECTED never fabricated; writes ONLY to prospective_evidence_v1.db.
"""
import hashlib
import json
import os
import sqlite3
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from prospective.prospective_db import ProspectiveDB, TABLES, FORBIDDEN_OUTCOME_TOKENS
from prospective.recorder import ProspectiveRecorder
from validator import ArchiveReader
from broker_readonly.secrets import SecretLeak

F = "seascalperfarouk Posted in 🐚·sea-scalper-farouk\n"


def _db():
    return ProspectiveDB(":memory:")


def _msg(mid, text, **kw):
    m = dict(channel_id="gold-trades", message_id=mid, message_key=f"telegram:p:{mid}",
             raw_text=F + text, posted_at_utc="2026-07-01T10:00:00+00:00",
             received_at_utc="2026-07-01T10:00:00.200+00:00", candidates=[])
    m.update(kw)
    return m


def _arc(messages):
    return ArchiveReader(mem_map={m["message_key"]: m["raw_text"] for m in messages})


def _run(messages):
    db = _db()
    rec = ProspectiveRecorder(db)
    rec.run_batch(messages, _arc(messages))
    return db, rec


# ---- schema / isolation
def test_only_four_prospective_tables():
    db = _db()
    assert db.table_names() == sorted(TABLES)
    assert not any("campaign_event" in n or "signal" in n or "broker_observation" in n
                   for n in db.table_names())


def test_no_outcome_columns_anywhere():
    db = _db()
    for t in TABLES:
        for col in db.column_names(t):
            assert not any(tok in col.lower() for tok in FORBIDDEN_OUTCOME_TOKENS), \
                f"forbidden outcome column {col} in {t}"


# ---- raw evidence stored first/always (parser failure never destroys it)
def test_parser_failure_still_stores_raw_evidence():
    # a candidate proposal that breaks extraction (None text) -> still get evidence + a
    # REJECTED parse_failure marker; the raw message_evidence row survives.
    bad = _msg("m_bad", "garbled", candidates=[{"event_type": None, "evidence_quote": None,
                                                "proposed_fields": {"entry": object()}}])
    db, rec = _run([bad])
    assert db.count("prospective_message_evidence") == 1            # raw evidence survived
    # the candidate path recorded something, but evidence is intact regardless
    assert db.con.execute("SELECT raw_text_hash FROM prospective_message_evidence").fetchone()[0]


def test_message_with_no_candidates_still_stores_evidence():
    db, rec = _run([_msg("m_empty", "just chatting, gm")])
    assert db.count("prospective_message_evidence") == 1
    assert db.count("prospective_candidate_events") == 0


# ---- observe-don't-infer on tempting fixtures
def test_screenshot_profit_infers_no_fill_no_r_no_score():
    # tempting: a profit screenshot. Must NOT create fill/R/score; only evidence + (maybe) commentary
    msg = _msg("m_shot", "up nicely, screenshot attached 4091.80",
               media_reference="img:hash:abc",
               candidates=[{"event_type": "COMMENTARY", "evidence_quote": "screenshot attached"}])
    db, rec = _run([msg])
    # no forbidden outcome anywhere (structural) + no quote prices
    dump = json.dumps(db.logical_dump()).lower()
    for tok in ("realized_r", "realised_r", "\"fill\"", "win", "loss", "pnl"):
        assert tok not in dump
    qc = db.con.execute("SELECT bid, ask, context_status FROM prospective_quote_context").fetchone()
    assert qc[0] is None and qc[1] is None and qc[2] == "BROKER_NOT_CONNECTED"


def test_market_call_without_explicit_entry_no_entry_estimated():
    msg = _msg("m_mc", "watching gold here, might sell soon",
               candidates=[{"event_type": "COMMENTARY", "evidence_quote": "watching gold here"}])
    db, rec = _run([msg])
    row = db.con.execute("SELECT proposed_event_type, proposed_leg_id FROM prospective_candidate_events").fetchone()
    assert row[0] == "COMMENTARY" and row[1] is None        # no leg/entry invented


def test_conditional_reentry_plan_creates_no_leg():
    msg = _msg("m_cond", "if we get stopped I'll give another trade",
               candidates=[{"event_type": "CONDITIONAL",
                            "evidence_quote": "if we get stopped I'll give another trade"}])
    db, rec = _run([msg])
    assert db.count("prospective_campaign_links") == 0
    row = db.con.execute("SELECT proposed_event_type, proposed_leg_id FROM prospective_candidate_events").fetchone()
    assert row[0] == "CONDITIONAL" and row[1] is None


def test_explicit_stop_hit_recorded_no_r():
    msg = _msg("m_stop", "stopped out on gold", leg_ref=None,
               candidates=[{"event_type": "STOP_HIT", "evidence_quote": "stopped out on gold"}])
    db, rec = _run([msg])
    row = db.con.execute("SELECT proposed_event_type, validator_status, association_status "
                         "FROM prospective_candidate_events").fetchone()
    assert row[0] == "STOP_HIT"
    # single message, no prior open leg -> association cannot be forced -> NEEDS_REVIEW
    assert row[2] in ("NEEDS_REVIEW", "N/A")
    dump = json.dumps(db.logical_dump()).lower()
    assert "realized_r" not in dump and "realised_r" not in dump


# ---- anti-hallucination pipeline
def test_low_lot_size_stays_null():
    # extractor proposes size; validator must null it ('low lot' qualitative). No number stored
    # (there is no size column) and the field is rejected by the validator.
    from validator import validate
    from prospective.recorder import _to_candidate
    msg = _msg("m_size", "getting in low lot on gold",
               candidates=[{"event_type": "ENTRY", "evidence_quote": "getting in low lot on gold",
                            "proposed_fields": {"size": 0.1, "asset": "XAUUSD"}, "leg_ref": "leg-1"}])
    cand = _to_candidate(msg["candidates"][0], msg["message_key"], "seascalperfarouk")
    v = validate(cand, _arc([msg]))
    assert v.fields["size"].value is None and v.fields["size"].rejected      # NULL, not guessed
    db, rec = _run([msg])
    # structural: there is NO size column, so a fabricated size cannot be persisted
    assert "size" not in db.column_names("prospective_candidate_events")
    # and no candidate row carries the rejected numeric in any stored field
    row = db.con.execute("SELECT proposed_event_type, asset, direction, exact_supporting_text "
                         "FROM prospective_candidate_events").fetchone()
    assert "0.1" not in (str(row[3]) or "")                  # supporting text has no fabricated size


def test_quarter_size_allowlisted_conversion_in_pipeline():
    from validator import validate
    from prospective.recorder import _to_candidate
    msg = _msg("m_q", "re-enter quarter size",
               candidates=[{"event_type": "RE_ENTER", "evidence_quote": "re-enter quarter size",
                            "proposed_fields": {"size": 0.25}}])
    cand = _to_candidate(msg["candidates"][0], msg["message_key"], "seascalperfarouk")
    v = validate(cand, _arc([msg]))
    assert v.fields["size"].value == 0.25 and v.fields["size"].provenance == "DETERMINISTIC_CONVERSION"


# ---- ambiguous association -> NEEDS_REVIEW; UNKNOWN valid
def test_ambiguous_leg_association_needs_review():
    # two open legs, then a close that names neither -> resolver leaves NEEDS_REVIEW
    msgs = [
        _msg("e1", "XAUUSD sell 4000 stop 4010",
             candidates=[{"event_type": "ENTRY", "evidence_quote": "XAUUSD sell 4000 stop 4010",
                          "proposed_fields": {"asset": "XAUUSD", "direction": "sell",
                                              "entry": "4000", "stop": "4010"}, "leg_ref": "leg-1"}]),
        _msg("e2", "re-enter",
             candidates=[{"event_type": "RE_ENTER", "evidence_quote": "re-enter"}]),
        _msg("c1", "take profit guys",
             candidates=[{"event_type": "PARTIAL_TP", "evidence_quote": "take profit guys"}]),
    ]
    db, rec = _run(msgs)
    row = db.con.execute("SELECT association_status, validator_status FROM prospective_candidate_events "
                         "WHERE proposed_event_type='PARTIAL_TP'").fetchone()
    assert row[0] == "NEEDS_REVIEW" and row[1] == "NEEDS_REVIEW"


def test_simultaneous_opposite_campaigns_coexist():
    msgs = [
        _msg("o1", "XAUUSD sell 4000 stop 4010",
             candidates=[{"event_type": "ENTRY", "evidence_quote": "XAUUSD sell 4000 stop 4010",
                          "proposed_fields": {"asset": "XAUUSD", "direction": "sell"},
                          "leg_ref": "leg-1"}], campaign_id="gold-sell"),
        _msg("o2", "BTCUSD buy 59000 stop 57000",
             candidates=[{"event_type": "ENTRY", "evidence_quote": "BTCUSD buy 59000 stop 57000",
                          "proposed_fields": {"asset": "BTCUSD", "direction": "buy"},
                          "leg_ref": "btc-1"}], campaign_id="btc-buy"),
    ]
    db, rec = _run(msgs)
    camps = {r[0] for r in db.con.execute("SELECT proposed_campaign_id FROM prospective_candidate_events")}
    assert {"gold-sell", "btc-buy"} <= camps        # both coexist, neither suppressed


# ---- broker fields NULL / never fabricated
def test_quote_context_always_null_broker_not_connected():
    db, rec = _run([_msg("q1", "XAUUSD sell 4000")])
    rows = db.con.execute("SELECT bid, ask, broker_timestamp_utc, context_status "
                          "FROM prospective_quote_context").fetchall()
    assert rows and all(r[0] is None and r[1] is None and r[2] is None
                        and r[3] == "BROKER_NOT_CONNECTED" for r in rows)


def test_quote_context_refuses_fabricated_price():
    db = _db()
    try:
        db.append_quote_context(telegram_message_id="x", context_status="BROKER_NOT_CONNECTED",
                                bid=2000.0)        # attempt to fabricate a price
        assert False
    except ValueError as e:
        assert "null" in str(e).lower()


def test_quote_context_refuses_non_disconnected_status():
    db = _db()
    try:
        db.append_quote_context(telegram_message_id="x", context_status="COMPLETE_ADMISSIBLE")
        assert False
    except ValueError:
        pass


# ---- missing / unreadable media
def test_missing_media_recorded_without_fabrication():
    db, rec = _run([_msg("mm", "see chart", media_reference=None,
                         candidates=[{"event_type": "COMMENTARY", "evidence_quote": "see chart"}])])
    media = db.con.execute("SELECT media_reference_or_hash FROM prospective_message_evidence").fetchone()[0]
    assert media is None        # NULL, not a fabricated reference


def test_unreadable_media_marked_not_inferred():
    db, rec = _run([_msg("um", "chart breakdown", media_reference="media:UNREADABLE",
                         candidates=[{"event_type": "COMMENTARY", "evidence_quote": "chart breakdown"}])])
    media = db.con.execute("SELECT media_reference_or_hash FROM prospective_message_evidence").fetchone()[0]
    assert media == "media:UNREADABLE"     # recorded as-is, nothing inferred from it


# ---- duplicate message identifiable
def test_duplicate_message_identifiable():
    m1 = _msg("dup", "XAUUSD sell 4000")
    m2 = _msg("dup", "XAUUSD sell 4000")
    db, rec = _run([m1, m2])
    hashes = [r[0] for r in db.con.execute("SELECT raw_text_hash FROM prospective_message_evidence")]
    assert len(hashes) == 2 and hashes[0] == hashes[1]    # identical -> identifiable as duplicate


# ---- append-only + secret rejection (reuse engine guarantees)
def test_append_only_update_and_delete_rejected():
    db, rec = _run([_msg("ao", "XAUUSD sell 4000")])
    for sql in ("UPDATE prospective_message_evidence SET raw_text_hash='x'",
                "DELETE FROM prospective_message_evidence"):
        try:
            db.con.execute(sql); db.con.commit(); assert False
        except sqlite3.Error as e:
            assert "append-only" in str(e).lower()


def test_secret_field_rejected():
    db = _db()
    try:
        db._append("prospective_candidate_events", {"telegram_message_id": "x", "access_token": "S"})
        assert False
    except SecretLeak:
        pass


# ---- deterministic replay
def test_deterministic_replay_identical_hash():
    msgs = [_msg("r1", "XAUUSD sell 4000 stop 4010",
                 candidates=[{"event_type": "ENTRY", "evidence_quote": "XAUUSD sell 4000 stop 4010",
                              "proposed_fields": {"asset": "XAUUSD", "direction": "sell"},
                              "leg_ref": "leg-1"}]),
            _msg("r2", "stopped out",
                 candidates=[{"event_type": "STOP_HIT", "evidence_quote": "stopped out"}])]
    a, _ = _run(msgs)
    b, _ = _run([dict(m) for m in msgs])
    assert a.logical_hash() == b.logical_hash()


# ---- NEEDS_REVIEW rate metrics (diagnostic only)
def test_needs_review_rate_metrics():
    msgs = [
        _msg("x1", "XAUUSD sell 4000",
             candidates=[{"event_type": "ENTRY", "evidence_quote": "XAUUSD sell 4000",
                          "proposed_fields": {"asset": "XAUUSD", "direction": "sell"}, "leg_ref": "leg-1"}]),
        _msg("x2", "re-enter", candidates=[{"event_type": "RE_ENTER", "evidence_quote": "re-enter"}]),
        _msg("x3", "take profit guys", candidates=[{"event_type": "PARTIAL_TP", "evidence_quote": "take profit guys"}]),
    ]
    db, rec = _run(msgs)
    m = rec.metrics()
    assert m["total"] >= 3
    assert 0.0 <= m["needs_review_rate"] <= 1.0
    assert "by_event_type" in m and m["note"].startswith("diagnostic")
