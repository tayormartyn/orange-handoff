import sqlite3, json, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

BASE = r"C:\Users\Marty\signal-terminal\campaign_extractor\prospective\data"
EV = BASE + r"\prospective_evidence_v1.db"
MEDIA = BASE + r"\prospective_media_v1.db"

mcon = sqlite3.connect(f"file:{MEDIA}?mode=ro", uri=True)
mcon.row_factory = sqlite3.Row
print("=== MEDIA DB TABLES ===")
for r in mcon.execute("SELECT name, sql FROM sqlite_master WHERE type='table'"):
    print(r["sql"])
    print()

con = sqlite3.connect(f"file:{EV}?mode=ro", uri=True)
con.row_factory = sqlite3.Row

# ranges of interest per Day 0 (with generous buffers to catch follow-ups)
RANGES = [
    ("SETUP1 2026-06-30", 45320, 45400),
    ("SETUP2 2026-07-07", 45490, 45520),
    ("SETUP2 follow-up + SETUP3 2026-07-08", 45540, 45580),
    ("SETUP4 2026-07-10", 45615, 45650),
]

for label, lo, hi in RANGES:
    print(f"\n{'='*90}\n### {label} (msg {lo}-{hi})\n{'='*90}")
    q = """SELECT telegram_message_id, telegram_posted_at_utc, telegram_channel_id,
                  telegram_sender_username, telegram_sender_display, message_revision_number,
                  media_reference_or_hash, raw_text
           FROM prospective_message_evidence
           WHERE CAST(telegram_message_id AS INTEGER) BETWEEN ? AND ?
           ORDER BY CAST(telegram_message_id AS INTEGER), message_revision_number"""
    for r in con.execute(q, (lo, hi)):
        txt = (r["raw_text"] or "").replace("\n", " | ")
        media = r["media_reference_or_hash"] or "-"
        print(f"[{r['telegram_message_id']}] rev{r['message_revision_number']} {r['telegram_posted_at_utc']} "
              f"ch={r['telegram_channel_id']} @{r['telegram_sender_username']} media={media[:60]}")
        print(f"    TEXT: {txt[:600]}")
print(f"\n{'='*90}\n### MEDIA RECORDS (XAU-adjacent msgs)\n{'='*90}")
mq = """SELECT message_id, message_revision_number, media_type, byte_count, content_sha256,
               storage_relative_path, capture_status, telegram_posted_at_utc
        FROM media_records
        WHERE capture_status='MEDIA_CAPTURED'
        ORDER BY CAST(message_id AS INTEGER)"""
for r in mcon.execute(mq):
    print(f"[{r['message_id']}] rev{r['message_revision_number']} {r['media_type']} {r['byte_count']}B "
          f"sha256={r['content_sha256']} path={r['storage_relative_path']} at={r['telegram_posted_at_utc']}")

con.close()
mcon.close()
