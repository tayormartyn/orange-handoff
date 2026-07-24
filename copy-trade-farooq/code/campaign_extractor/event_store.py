"""
Immutable, append-only campaign event store.

Only ACCEPTED ValidatedEvents enter the reducible stream and may affect campaign state.
NEEDS_REVIEW and REJECTED events are recorded in a separate audit log — visible for
provenance, but never replayed into state.

Append-only by construction: there is no update or delete API. Each accepted event gets
a monotonic sequence number; replay order == append order, which makes the reducer
deterministic. Optional persistence writes to a SEPARATE sqlite file
(campaign_extractor/data/campaign_events.db) and never touches signal_archive.db or any
shadow/paper/baseline state.
"""
from __future__ import annotations
import json
import os
import sqlite3
from typing import Optional

from schema import ValidatedEvent, ValidatedField, Status


class EventStore:
    def __init__(self, db_path: Optional[str] = None):
        self._accepted = []          # ordered list of (seq, ValidatedEvent)
        self._audit = []             # NEEDS_REVIEW / REJECTED, recorded only
        self._seq = 0
        self._con = None
        if db_path is not None:
            os.makedirs(os.path.dirname(db_path), exist_ok=True)
            self._con = sqlite3.connect(db_path)
            self._con.execute(
                "CREATE TABLE IF NOT EXISTS campaign_events ("
                "seq INTEGER PRIMARY KEY, accepted_hash TEXT NOT NULL, "
                "event_type TEXT, status TEXT, track TEXT, payload TEXT NOT NULL)"
            )
            self._con.commit()

    # ----------------------------------------------------------------- append
    def append(self, ev: ValidatedEvent) -> Optional[int]:
        """Append one validated event. Returns its seq if it joined the reducible
        stream (ACCEPTED), else None (recorded in the audit log)."""
        if ev.status != Status.ACCEPTED.value:
            self._audit.append(ev)
            return None
        self._seq += 1
        self._accepted.append((self._seq, ev))
        if self._con is not None:
            self._con.execute(
                "INSERT INTO campaign_events (seq, accepted_hash, event_type, status, track, payload) "
                "VALUES (?,?,?,?,?,?)",
                (self._seq, ev.accepted_hash(), ev.event_type, ev.status, ev.track,
                 json.dumps(_serialize(ev), ensure_ascii=False, sort_keys=True)),
            )
            self._con.commit()
        return self._seq

    # ----------------------------------------------------------------- read
    def events(self):
        """Accepted events in immutable append order — the reducer's input."""
        return [ev for _seq, ev in self._accepted]

    def audit(self):
        return list(self._audit)

    def close(self):
        if self._con is not None:
            self._con.close()
            self._con = None

    def log_hash(self):
        """Hash of the ordered accepted-event stream (tamper / replay check)."""
        import hashlib
        h = hashlib.sha256()
        for seq, ev in self._accepted:
            h.update(f"{seq}:{ev.accepted_hash()}\n".encode("utf-8"))
        return h.hexdigest()


def _serialize(ev: ValidatedEvent) -> dict:
    return {
        "event_type": ev.event_type, "status": ev.status, "track": ev.track,
        "leg_ref": ev.leg_ref, "parent_ref": ev.parent_ref,
        "source_message_keys": ev.source_message_keys, "sender_handle": ev.sender_handle,
        "versions": ev.versions, "accepted_hash": ev.accepted_hash(),
        "fields": {n: {"value": f.value, "provenance": f.provenance, "rejected": f.rejected}
                   for n, f in ev.fields.items()},
    }
