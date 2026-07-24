"""LIVE_EDIT_EVENTS_NOT_CAPTURED fix (D-028 named defect; demo-lane prerequisite).

Capture Telegram MESSAGE EDITS as append-only EDITED revisions in the prospective
evidence DB. Kept OUT of module_a_telegram.py so the listener file's diff is a minimal
wiring block; all logic + tests live here.

Contract (mirrors Gate-1 CREATED capture):
- CHANNEL ALLOWLIST fail-closed: off-allowlist edits raise PermissionError, no row.
- Append-only: a new row with message_event_type=EDITED, message_revision_number =
  prior max + 1, supersedes_evidence_id -> prior row's evidence_id. Originals are never
  touched (DB has BEFORE UPDATE/DELETE refusal triggers).
- Edit of a message we never captured (pre-listener history): recorded as EDITED with
  revision 1 and supersedes NULL — still a non-CREATED row, so the wire's fail-closed
  edit branch triggers identically. EDITED + supersedes NULL is the orphan signature.
- RAW-TEXT CONTAINMENT: this module never prints/logs message content; callers print
  only counts/hashes/ids (same rule as the CREATED handler).
- NO interpretation here. Downstream, live_wire.process_message already routes any
  non-CREATED/revision>1 row to EDIT_REVISION_RECORDED and appends an
  XAU_F_CAMPAIGN_PAUSE alarm for every campaign whose message_ids contain the edited
  id (edit-after-transition alarm: never silently applied, never silently ignored).
- Quote-context rows are NOT written for edits: quote context belongs to the original
  capture moment; an edit is the same market message re-worded, not a new quote event.
"""
from datetime import datetime, timezone


def prior_revision(recorder, channel_id, message_id):
    """Latest (evidence_id, revision_number) for this channel/message, or (None, 0)."""
    row = recorder.db.con.execute(
        "SELECT evidence_id, message_revision_number FROM prospective_message_evidence "
        "WHERE telegram_channel_id=? AND telegram_message_id=? "
        "ORDER BY rowseq DESC LIMIT 1",
        (str(channel_id), str(message_id))).fetchone()
    if row is None:
        return None, 0
    return row[0], int(row[1] or 1)


def record_prospective_edit(recorder, event, allowed_chat_ids=None):
    """Persist one EDITED Telegram message as a new append-only revision row.

    Returns the appended record dict (from ProspectiveDB._append). Raises
    PermissionError off-allowlist. Never mutates prior rows."""
    if allowed_chat_ids is not None and event.chat_id not in allowed_chat_ids:
        raise PermissionError(f"channel {event.chat_id} not on allowlist")
    msg = event.message
    raw = event.raw_text
    media_ref = None
    if getattr(msg, "media", None) is not None:
        media_ref = f"media:{type(msg.media).__name__}:{getattr(msg, 'id', None)}"
    now = datetime.now(timezone.utc).isoformat()
    posted = msg.date.astimezone(timezone.utc).isoformat() if getattr(msg, "date", None) else None
    edited = (msg.edited_date.astimezone(timezone.utc).isoformat()
              if getattr(msg, "edited_date", None) else now)
    sender_id = getattr(msg, "sender_id", None) or getattr(event, "sender_id", None)

    prev_eid, prev_rev = prior_revision(recorder, event.chat_id, getattr(msg, "id", None))
    return recorder.db.append_message_evidence(
        telegram_channel_id=str(event.chat_id),
        telegram_message_id=str(getattr(msg, "id", None)),
        telegram_posted_at_utc=posted,
        listener_received_at_utc=now,
        listener_observed_at_utc=now,
        raw_text=raw,
        media_reference_or_hash=media_ref,
        message_event_type="EDITED",
        message_revision_number=(prev_rev + 1) if prev_eid else 1,
        supersedes_evidence_id=prev_eid,
        telegram_edited_at_utc=edited,
        telegram_sender_id=str(sender_id) if sender_id is not None else None,
    )
