"""Forward cycle 001: read-only scan of the live evidence store for new messages after 45642."""
import sqlite3, sys, io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
EV = r"C:\Users\Marty\signal-terminal\campaign_extractor\prospective\data\prospective_evidence_v1.db"
con = sqlite3.connect(f"file:{EV}?mode=ro", uri=True)
con.row_factory = sqlite3.Row

r = con.execute("SELECT MAX(CAST(telegram_message_id AS INTEGER)) hi, MAX(telegram_posted_at_utc) t, COUNT(*) n "
                "FROM prospective_message_evidence").fetchone()
print(f"store: max_msg={r['hi']} latest={r['t']} total_rows={r['n']}")

q = """SELECT telegram_message_id id, telegram_posted_at_utc t, media_reference_or_hash m, raw_text x
       FROM prospective_message_evidence
       WHERE CAST(telegram_message_id AS INTEGER) > 45642
       ORDER BY CAST(telegram_message_id AS INTEGER), message_revision_number"""
rows = list(con.execute(q))
print(f"new messages after 45642: {len(rows)}\n")
for row in rows:
    txt = (row["x"] or "").replace("\n", " | ")
    print(f"[{row['id']}] {row['t']} media={row['m'] or '-'}")
    print(f"    {txt[:400]}")
con.close()
