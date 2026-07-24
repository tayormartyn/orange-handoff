"""
Gate 1 wiring proof — the PREVIEW NewMessage handler writes prospective evidence.

Proven OFFLINE with a simulated event (no Telegram connection, no network): the wired
handler persists raw message evidence + a BROKER_NOT_CONNECTED quote-context row to the
prospective DB ONLY, with quote fields NULL. No trading pipeline, no broker.
"""
import os
import sys
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))      # campaign_extractor
PARENT = os.path.dirname(ROOT)                                          # signal-terminal
sys.path.insert(0, ROOT)
sys.path.insert(0, PARENT)

import module_a_telegram as mat
from prospective.prospective_db import ProspectiveDB, TABLES
from prospective.recorder import ProspectiveRecorder


class _FakeMsg:
    def __init__(self, mid, media=None):
        self.id = mid
        self.date = datetime(2026, 7, 1, 10, 0, tzinfo=timezone.utc)
        self.media = media


class _FakeEvent:
    def __init__(self, raw_text, mid=555, chat_id=-1001234567890, media=None):
        self.raw_text = raw_text
        self.chat_id = chat_id
        self.message = _FakeMsg(mid, media=media)


def _rec():
    return ProspectiveRecorder(ProspectiveDB(":memory:"))


def test_wired_handler_records_text_message():
    rec = _rec()
    mat._record_prospective(rec, _FakeEvent("seascalperfarouk Posted in shell\nXAUUSD SELL 4078"))
    db = rec.db
    assert db.count("prospective_message_evidence") == 1
    row = db.con.execute("SELECT raw_text, raw_text_hash, message_event_type "
                         "FROM prospective_message_evidence").fetchone()
    assert "XAUUSD SELL 4078" in row[0] and row[1] and row[2] == "CREATED"


def test_wired_handler_writes_broker_not_connected_quote_context():
    rec = _rec()
    mat._record_prospective(rec, _FakeEvent("hello"))
    qc = rec.db.con.execute("SELECT bid, ask, broker_timestamp_utc, context_status "
                            "FROM prospective_quote_context").fetchone()
    assert qc[0] is None and qc[1] is None and qc[2] is None and qc[3] == "BROKER_NOT_CONNECTED"


def test_wired_handler_media_only_stores_null_text_with_media_ref():
    rec = _rec()
    mat._record_prospective(rec, _FakeEvent(None, media=object()))     # media-only, no caption
    row = rec.db.con.execute("SELECT raw_text, media_reference_or_hash "
                             "FROM prospective_message_evidence").fetchone()
    assert row[0] is None and row[1] and row[1].startswith("media:")


def test_wired_handler_writes_only_evidence_and_quote_context():
    # capture-only wiring: no candidate extraction / campaign links created live
    rec = _rec()
    mat._record_prospective(rec, _FakeEvent("XAUUSD SELL 4078"))
    counts = {t: rec.db.count(t) for t in TABLES}
    assert counts["prospective_message_evidence"] == 1
    assert counts["prospective_quote_context"] == 1
    assert counts["prospective_candidate_events"] == 0
    assert counts["prospective_campaign_links"] == 0


def test_trading_pipeline_handoff_remains_disabled():
    src = open(os.path.join(PARENT, "module_a_telegram.py"), encoding="utf-8").read()
    # the module_b handoff line must still be commented out (no live enable)
    assert "# parsed = module_b_parser" in src
    # and the recorder is wired (the approved change)
    assert "_record_prospective(recorder, event, allowed_ids)" in src


# ---- channel allowlist (fail closed)
def test_off_allowlist_channel_rejected_creates_no_row():
    rec = _rec()
    ev = _FakeEvent("XAUUSD SELL 4078", chat_id=-100999999999)      # NOT the configured channel
    try:
        mat._record_prospective(rec, ev, {-1001902136163})          # allowlist = real channel
        assert False, "off-allowlist channel should be refused"
    except PermissionError:
        pass
    assert rec.db.count("prospective_message_evidence") == 0         # fail closed -> no evidence


def test_on_allowlist_channel_records():
    rec = _rec()
    ev = _FakeEvent("XAUUSD SELL 4078", chat_id=-1001902136163)
    mat._record_prospective(rec, ev, {-1001902136163})
    assert rec.db.count("prospective_message_evidence") == 1


# ---- raw-text containment: handler must not print message content
def test_handler_does_not_print_raw_text():
    src = open(os.path.join(PARENT, "module_a_telegram.py"), encoding="utf-8").read()
    assert "print(message_text)" not in src                         # old raw-content print removed
    assert "content -> evidence DB only" in src                     # safe-metadata print present


# ---- NewMessage / CREATED only; no edit or deletion handling wired
def test_only_new_message_created_no_edit_or_deletion_handler():
    src = open(os.path.join(PARENT, "module_a_telegram.py"), encoding="utf-8").read()
    assert "events.NewMessage" in src
    assert "MessageEdited" not in src and "MessageDeleted" not in src
    rec = _rec()
    mat._record_prospective(rec, _FakeEvent("hi", chat_id=-1001902136163), {-1001902136163})
    et = rec.db.con.execute("SELECT message_event_type FROM prospective_message_evidence").fetchone()[0]
    assert et == "CREATED"
