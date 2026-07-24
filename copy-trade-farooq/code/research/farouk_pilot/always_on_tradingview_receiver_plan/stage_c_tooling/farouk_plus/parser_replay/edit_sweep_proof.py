"""Edit-sweep RED/GREEN + no-op proof (LIVE_EDIT fix, wire side).

RED   : the LIVE wire's new_messages cannot see an EDITED row whose message id is
        already behind the cursor (the edit-after-transition case).
GREEN : v2.2's new_edit_rows sees it via the rowseq cursor.
NO-OP : against the REAL evidence DB (read-only), v2.2 new_messages returns exactly the
        same rows as live (all rows are CREATED today) and new_edit_rows returns [].
"""
import os
import sqlite3
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
FA = os.path.join(os.path.dirname(HERE), "follower_assistant")
sys.path.insert(0, FA)
_cwd = os.getcwd()
os.chdir(FA)
import live_wire as LIVE          # noqa: E402
import live_wire_v2 as V2         # noqa: E402
os.chdir(_cwd)

ok = True


def ck(name, cond, detail=""):
    global ok
    print(("PASS " if cond else "FAIL ") + name + ("" if cond else f"  <- {detail}"))
    ok = ok and bool(cond)


# temp DB with the wire's expected columns: one CREATED (id 45938) + one EDITED revision
tmp = os.path.join(tempfile.mkdtemp(prefix="edit_sweep_"), "ev.db")
con = sqlite3.connect(tmp)
con.execute("CREATE TABLE prospective_message_evidence ("
            "rowseq INTEGER PRIMARY KEY AUTOINCREMENT, telegram_message_id TEXT, "
            "telegram_posted_at_utc TEXT, raw_text TEXT, raw_text_hash TEXT, "
            "message_event_type TEXT, message_revision_number INTEGER)")
con.execute("INSERT INTO prospective_message_evidence (telegram_message_id, "
            "telegram_posted_at_utc, raw_text, raw_text_hash, message_event_type, "
            "message_revision_number) VALUES ('45938','2026-07-20T16:10:00Z',"
            "'close worst hold best entry','h1','CREATED',1)")
con.execute("INSERT INTO prospective_message_evidence (telegram_message_id, "
            "telegram_posted_at_utc, raw_text, raw_text_hash, message_event_type, "
            "message_revision_number) VALUES ('45938','2026-07-20T16:10:00Z',"
            "'close worst entry hold best entry','h2','EDITED',2)")
con.commit(); con.close()

CURSOR = 45969  # the real wire cursor position — 45938 is far behind it

red = LIVE.new_messages(CURSOR, db_path=tmp)
ck("RED: live wire NEVER sees the edit (id behind cursor)", red == [], red)

green = V2.new_edit_rows(0, db_path=tmp)
ck("GREEN: v2.2 sweep sees exactly the EDITED row",
   len(green) == 1 and green[0]["id"] == 45938 and green[0]["event_type"] == "EDITED"
   and green[0]["revision"] == 2, green)

ck("GREEN: sweep never returns CREATED rows",
   all(r["event_type"] != "CREATED" for r in V2.new_edit_rows(0, db_path=tmp)))

ck("GREEN: rowseq cursor excludes consumed rows", V2.new_edit_rows(green[0]["rowseq"], db_path=tmp) == [])

# NO-OP proof on the REAL DB (read-only handles inside both functions)
REAL = LIVE.EVIDENCE_DB
a = LIVE.new_messages(0, db_path=REAL)
b = V2.new_messages(0, db_path=REAL)
ck(f"NO-OP: real-DB new_messages identical live vs v2.2 ({len(a)} rows)", a == b,
   (len(a), len(b)))
e = V2.new_edit_rows(0, db_path=REAL)
ck("real-DB sweep returns ONLY non-CREATED edit rows (live edits now exist, e.g. F008 46011)",
   all(r["event_type"] != "CREATED" for r in e))

print("\nEDIT_SWEEP_PROOF:", "PASS" if ok else "FAIL")
sys.exit(0 if ok else 1)
