"""Tests for LIVE_EDIT_EVENTS_NOT_CAPTURED fix. Offline; temp DB in scratch; monkeypatches
live_wire ledger writes so NO real ledger/DB is touched. Run:
  python tests_listener_edit_capture.py
"""
import os
import sys
import tempfile
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.abspath(__file__))
CE = os.path.join(ROOT, "campaign_extractor")
for p in (ROOT, CE):
    if p not in sys.path:
        sys.path.insert(0, p)

from prospective.prospective_db import ProspectiveDB
from prospective.recorder import ProspectiveRecorder
import listener_edit_capture as LEC

checks = []


def ck(name, cond, detail=""):
    checks.append((name, bool(cond), detail))


class FakeMsg:
    def __init__(self, mid, text, edited=None):
        self.id = mid
        self.date = datetime(2026, 7, 21, 9, 0, tzinfo=timezone.utc)
        self.edited_date = edited
        self.media = None
        self.sender_id = 111


class FakeEvent:
    def __init__(self, chat_id, msg, text):
        self.chat_id = chat_id
        self.message = msg
        self.raw_text = text
        self.sender_id = 111


tmp = tempfile.mkdtemp(prefix="edit_capture_test_")
db = ProspectiveDB(os.path.join(tmp, "test_evidence.db"))
rec = ProspectiveRecorder(db)
ALLOW = {-100123}

# 1) CREATED then EDITED -> append-only revision chain
orig = FakeEvent(-100123, FakeMsg(500, "XAUUSD BUY 4010-4000 SL 3992"), "XAUUSD BUY 4010-4000 SL 3992")
rec.record_message({"channel_id": "-100123", "message_id": 500,
                    "raw_text": orig.raw_text, "media_reference": None,
                    "posted_at_utc": "2026-07-21T09:00:00+00:00",
                    "received_at_utc": "2026-07-21T09:00:01+00:00",
                    "listener_observed_at_utc": "2026-07-21T09:00:01+00:00",
                    "message_event_type": "CREATED"})
e1 = FakeEvent(-100123, FakeMsg(500, "", edited=datetime(2026, 7, 21, 9, 5, tzinfo=timezone.utc)),
               "XAUUSD BUY 4012-4000 SL 3990")
row = LEC.record_prospective_edit(rec, e1, ALLOW)
ck("edit row EDITED", row["message_event_type"] == "EDITED", row)
ck("edit revision 2", row["message_revision_number"] == 2, row)
ck("supersedes prior evidence_id", bool(row["supersedes_evidence_id"]), row)
ck("edited_at carried", row["telegram_edited_at_utc"].startswith("2026-07-21T09:05"), row)
ck("raw text stored exactly", row["raw_text"] == "XAUUSD BUY 4012-4000 SL 3990")
prior = db.con.execute("SELECT raw_text FROM prospective_message_evidence "
                       "WHERE telegram_message_id='500' AND message_event_type='CREATED'").fetchone()
ck("original row untouched", prior[0] == "XAUUSD BUY 4010-4000 SL 3992", prior)

# 2) second edit -> revision 3, chains to revision 2's evidence_id
e2 = FakeEvent(-100123, FakeMsg(500, ""), "XAUUSD BUY 4012-4002 SL 3990")
row2 = LEC.record_prospective_edit(rec, e2, ALLOW)
ck("second edit revision 3", row2["message_revision_number"] == 3, row2)
ck("chains to rev2", row2["supersedes_evidence_id"] == row["evidence_id"],
   (row2["supersedes_evidence_id"], row["evidence_id"]))

# 3) edit of a never-captured message -> EDITED orphan, revision 1, supersedes NULL
e3 = FakeEvent(-100123, FakeMsg(9999, ""), "some pre-history message, now edited")
row3 = LEC.record_prospective_edit(rec, e3, ALLOW)
ck("orphan edit EDITED", row3["message_event_type"] == "EDITED")
ck("orphan revision 1", row3["message_revision_number"] == 1, row3)
ck("orphan supersedes NULL", row3["supersedes_evidence_id"] is None, row3)

# 4) allowlist fail-closed
try:
    LEC.record_prospective_edit(rec, FakeEvent(-999888, FakeMsg(42, ""), "x"), ALLOW)
    ck("off-allowlist rejected", False, "no exception raised")
except PermissionError:
    ck("off-allowlist rejected", True)
n_before = db.count("prospective_message_evidence")
ck("no row for rejected edit", n_before == 4, n_before)  # 1 CREATED + 3 EDITED

# 5) DB append-only triggers still refuse mutation of the chain
try:
    db.con.execute("UPDATE prospective_message_evidence SET raw_text='tamper' WHERE rowseq=1")
    ck("UPDATE refused by trigger", False, "update succeeded!")
except Exception:
    ck("UPDATE refused by trigger", True)

# 6) WIRE SIDE: an EDITED row for a campaign-driving message must alarm (pause), never apply
WD = os.path.join(ROOT, r"research\farouk_pilot\always_on_tradingview_receiver_plan"
                        r"\stage_c_tooling\farouk_plus\follower_assistant")
sys.path.insert(0, WD)
_cwd = os.getcwd()
os.chdir(WD)  # live_wire resolves its files relative to itself; imports only here
import live_wire  # noqa: E402
os.chdir(_cwd)

captured = []
live_wire.append_forward = lambda rec_: captured.append(rec_) or True   # NO real ledger writes
live_wire.append_follower = lambda *a, **k: True

edited_msg = {"id": 45938, "event_type": "EDITED", "revision": 2,
              "raw_text": "close worst entry hold best entry",
              "raw_text_sha256": "x", "posted_at": "2026-07-21T09:05:00Z"}
setups = {"XAU-F006-20260720": {"message_ids": [45930, 45937, 45938],
                                "direction": "LONG"}}
out = live_wire.process_message(edited_msg, setups, [], {})
ck("wire: edit routed to revision branch", out.startswith("EDIT_REVISION_RECORDED"), out)
ck("wire: pause alarm appended for touched campaign",
   any(r["record_type"] == "XAU_F_CAMPAIGN_PAUSE" and r["setup_id"] == "XAU-F006-20260720"
       and "EDITED" in r["why"] for r in captured), captured)
ck("wire: edit NEVER interpreted as instruction",
   not any(r.get("record_type") == "XAU_F_SETUP" for r in captured))

# 7) wire: edited row touching NO campaign -> recorded, no pause, no interpretation
captured.clear()
lone = {"id": 45700, "event_type": "EDITED", "revision": 2, "raw_text": "hello edited",
        "raw_text_sha256": "y", "posted_at": "2026-07-21T09:06:00Z"}
out2 = live_wire.process_message(lone, setups, [], {})
ck("wire: non-campaign edit no pause", captured == [], captured)
ck("wire: non-campaign edit still explicit", out2.startswith("EDIT_REVISION_RECORDED"), out2)

fails = [(n, d) for n, ok_, d in checks if not ok_]
for n, ok_, d in checks:
    print(("PASS " if ok_ else "FAIL ") + n + ("" if ok_ else f"  <- {d}"))
print(f"\n{len(checks) - len(fails)}/{len(checks)} pass")
sys.exit(0 if not fails else 1)
