"""
Brick 5A — raw message preservation (full spec). Offline only; listener unwired.

Covers all 14 required tests: recoverable raw_text; SHA-256 integrity over exact UTF-8;
unicode/emoji round-trip; NULL vs empty distinct; media-only NULL; raw_text survives parser
failure / exception (no rollback); ordinary prose not rejected by the secret scanner while a
secret-named FIELD still is; tampering breaks integrity; edits are append-only revisions;
original + edited independently recoverable; append-only protections active; listener unwired.
"""
import hashlib
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PARENT = os.path.dirname(ROOT)
sys.path.insert(0, ROOT)

import sqlite3
from prospective.prospective_db import ProspectiveDB
from prospective.recorder import ProspectiveRecorder
from validator import ArchiveReader
from broker_readonly.secrets import SecretLeak

F = "seascalperfarouk Posted in 🐚·sea-scalper-farouk\n"


def _db():
    return ProspectiveDB(":memory:")


def _msg(mid, text, **kw):
    m = dict(channel_id="gold-trades", message_id=mid, message_key=f"telegram:p:{mid}",
             raw_text=(F + text) if text is not None else None,
             posted_at_utc="2026-07-01T10:00:00+00:00",
             received_at_utc="2026-07-01T10:00:00.200+00:00", candidates=[])
    m.update(kw)
    return m


def _run(messages):
    db = _db()
    rec = ProspectiveRecorder(db)
    rec.run_batch(messages, ArchiveReader(mem_map={m["message_key"]: m["raw_text"] or ""
                                                   for m in messages}))
    return db


def _evrow(db, where=""):
    return db.con.execute(
        f"SELECT raw_text, raw_text_hash, message_event_type, message_revision_number, "
        f"supersedes_evidence_id, evidence_id FROM prospective_message_evidence {where} "
        f"ORDER BY rowseq").fetchall()


# 1
def test_normal_raw_text_stored_and_recoverable():
    msg = _msg("n1", "XAUUSD SELL 4078-4092 SL4120")
    db = _run([msg])
    assert _evrow(db)[0][0] == msg["raw_text"]


# 2
def test_raw_text_hash_verifies_exact_utf8():
    db = _run([_msg("h1", "leave 10% open")])
    text, h = _evrow(db)[0][0], _evrow(db)[0][1]
    assert hashlib.sha256(text.encode("utf-8")).hexdigest() == h


# 3
def test_unicode_emoji_punctuation_roundtrip():
    weird = "Gold 🪙→ SELL «4078–4092» … SL‑4120 ✅ naïve café"
    db = _run([_msg("u1", weird)])
    stored, h = _evrow(db)[0][0], _evrow(db)[0][1]
    assert stored == F + weird                                   # exact round-trip
    assert hashlib.sha256(stored.encode("utf-8")).hexdigest() == h


# 4
def test_null_and_empty_text_distinguishable():
    db = _db()
    db.append_message_evidence(telegram_channel_id="c", telegram_message_id="null1",
                               telegram_posted_at_utc=None, listener_received_at_utc=None,
                               raw_text=None)                     # media-only -> NULL
    db.append_message_evidence(telegram_channel_id="c", telegram_message_id="empty1",
                               telegram_posted_at_utc=None, listener_received_at_utc=None,
                               raw_text="")                       # explicit empty string
    rows = db.con.execute("SELECT raw_text, raw_text_hash FROM prospective_message_evidence "
                          "ORDER BY rowseq").fetchall()
    assert rows[0][0] is None and rows[0][1] is None             # NULL -> hash NULL
    assert rows[1][0] == "" and rows[1][1] == hashlib.sha256(b"").hexdigest()  # "" -> empty hash
    assert rows[0][0] is not rows[1][0]                          # distinct states


# 5
def test_media_only_message_stores_null_safely():
    db = _run([_msg("m1", None, media_reference="img:hash:xyz")])   # no caption
    row = _evrow(db)[0]
    assert row[0] is None and row[1] is None
    media = db.con.execute("SELECT media_reference_or_hash FROM prospective_message_evidence").fetchone()[0]
    assert media == "img:hash:xyz"


# 6
def test_parser_failure_persists_raw_text_and_hash():
    bad = _msg("pf", "perishable content here",
               candidates=[{"event_type": None, "evidence_quote": None,
                            "proposed_fields": {"entry": object()}}])
    db = _run([bad])
    row = _evrow(db)[0]
    assert row[0] == bad["raw_text"] and row[1] == hashlib.sha256(row[0].encode("utf-8")).hexdigest()


# 7
def test_parser_exception_does_not_roll_back_raw_evidence():
    bad = _msg("pe", "must survive the exception",
               candidates=[{"event_type": "ENTRY", "evidence_quote": None,
                            "proposed_fields": {"x": object()}}])
    db = _run([bad])
    assert db.count("prospective_message_evidence") == 1
    assert "must survive the exception" in _evrow(db)[0][0]


# 8
def test_ordinary_prose_not_rejected_by_secret_scanner():
    db = _run([_msg("c1", "talking about an access token and password in passing")])
    assert "access token" in _evrow(db)[0][0]                    # stored, not censored


# 9
def test_secret_named_field_still_rejected():
    db = _db()
    for bad in ({"telegram_message_id": "x", "access_token": "S"},
                {"telegram_message_id": "x", "client_secret": "S"},
                {"telegram_message_id": "x", "refresh_token": "S"}):
        try:
            db._append("prospective_message_evidence", bad); assert False
        except SecretLeak:
            pass


# 10
def test_changed_character_breaks_integrity():
    db = _run([_msg("t1", "XAUUSD SELL 4078")])
    text, h = _evrow(db)[0][0], _evrow(db)[0][1]
    tampered = text.replace("4078", "4079")
    assert hashlib.sha256(tampered.encode("utf-8")).hexdigest() != h


# 11
def test_edit_is_new_append_only_revision():
    db = _db()
    orig = db.append_message_evidence(telegram_channel_id="gt", telegram_message_id="999",
                                      telegram_posted_at_utc="2026-07-01T10:00:00+00:00",
                                      listener_received_at_utc="2026-07-01T10:00:00+00:00",
                                      raw_text="XAUUSD SELL 4078", message_event_type="CREATED",
                                      message_revision_number=1)
    db.append_message_evidence(telegram_channel_id="gt", telegram_message_id="999",
                               telegram_posted_at_utc="2026-07-01T10:00:00+00:00",
                               listener_received_at_utc="2026-07-01T10:05:00+00:00",
                               raw_text="XAUUSD SELL 4080 (edited)", message_event_type="EDITED",
                               message_revision_number=2, supersedes_evidence_id=orig["evidence_id"],
                               telegram_edited_at_utc="2026-07-01T10:05:00+00:00")
    rows = _evrow(db, "WHERE telegram_message_id='999'")
    assert len(rows) == 2                                        # two rows, original not overwritten
    assert rows[0][2] == "CREATED" and rows[1][2] == "EDITED"
    assert rows[0][3] == 1 and rows[1][3] == 2
    assert rows[1][4] == rows[0][5]                              # EDITED supersedes CREATED


# 12
def test_original_and_edited_independently_recoverable():
    db = _db()
    o = db.append_message_evidence(telegram_channel_id="gt", telegram_message_id="42",
                                   telegram_posted_at_utc="t", listener_received_at_utc="t",
                                   raw_text="ORIGINAL text", message_event_type="CREATED")
    db.append_message_evidence(telegram_channel_id="gt", telegram_message_id="42",
                               telegram_posted_at_utc="t", listener_received_at_utc="t2",
                               raw_text="EDITED text", message_event_type="EDITED",
                               message_revision_number=2, supersedes_evidence_id=o["evidence_id"])
    texts = [r[0] for r in _evrow(db, "WHERE telegram_message_id='42'")]
    assert "ORIGINAL text" in texts and "EDITED text" in texts   # both recoverable


# 13
def test_append_only_protections_active():
    db = _run([_msg("ao", "XAUUSD SELL 4000")])
    for sql in ("UPDATE prospective_message_evidence SET raw_text='tampered'",
                "DELETE FROM prospective_message_evidence"):
        try:
            db.con.execute(sql); db.con.commit(); assert False
        except sqlite3.Error as e:
            assert "append-only" in str(e).lower()


# 14 — updated for Gate 1 (approved): the recorder IS now wired, but the TRADING pipeline
# (module_b handoff) must remain disabled. This is an approved state change, not a loosened check.
def test_listener_wired_to_recorder_but_trading_disabled():
    src = open(os.path.join(PARENT, "module_a_telegram.py"), encoding="utf-8").read()
    assert "_record_prospective(recorder, event, allowed_ids)" in src   # Gate 1 recorder wired (allowlisted)
    assert "# parsed = module_b_parser" in src                  # trading handoff still disabled
    assert "place_order" not in src and "execute_trade" not in src   # no order code
