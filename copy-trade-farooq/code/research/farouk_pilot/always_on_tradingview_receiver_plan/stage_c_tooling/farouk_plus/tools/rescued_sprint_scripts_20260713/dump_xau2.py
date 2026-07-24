import sqlite3

BASE = r"C:\Users\Marty\signal-terminal\campaign_extractor\prospective\data"
EV = BASE + r"\prospective_evidence_v1.db"
MEDIA = BASE + r"\prospective_media_v1.db"
OUT = r"C:\Users\Marty\AppData\Local\Temp\claude\C--Users-Marty\5fc06f59-5409-4db3-ac12-a901363ccb04\scratchpad\xau_dump2.txt"

con = sqlite3.connect(f"file:{EV}?mode=ro", uri=True)
con.row_factory = sqlite3.Row
mcon = sqlite3.connect(f"file:{MEDIA}?mode=ro", uri=True)
mcon.row_factory = sqlite3.Row

out = open(OUT, "w", encoding="utf-8")

RANGES = [
    ("SETUP1 2026-06-30", 45331, 45353),
    ("SETUP2 2026-07-07", 45490, 45530),
    ("SETUP2-followup + SETUP3 2026-07-08", 45540, 45585),
    ("SETUP4 2026-07-10", 45615, 45650),
]

KEY = ("gold-trades", "XAU", "xau", "gold", "Gold", "GOLD", "pips", "stopped", "sl ", "SL", "tp", "TP")

for label, lo, hi in RANGES:
    out.write(f"\n{'='*90}\n### {label} (msg {lo}-{hi})\n{'='*90}\n")
    q = """SELECT telegram_message_id, telegram_posted_at_utc, telegram_channel_id,
                  message_revision_number, media_reference_or_hash, raw_text
           FROM prospective_message_evidence
           WHERE CAST(telegram_message_id AS INTEGER) BETWEEN ? AND ?
           ORDER BY CAST(telegram_message_id AS INTEGER), message_revision_number"""
    for r in con.execute(q, (lo, hi)):
        txt = (r["raw_text"] or "").replace("\n", " | ")
        if not any(k in txt for k in KEY) and "MessageMediaPhoto" not in (r["media_reference_or_hash"] or ""):
            continue
        media = r["media_reference_or_hash"] or "-"
        out.write(f"[{r['telegram_message_id']}] rev{r['message_revision_number']} {r['telegram_posted_at_utc']} "
                  f"ch={r['telegram_channel_id']} media={media}\n")
        out.write(f"    TEXT: {txt[:700]}\n")

out.write(f"\n{'='*90}\n### MEDIA RECORDS (all MEDIA_CAPTURED)\n{'='*90}\n")
mq = """SELECT message_id, message_revision_number, media_type, byte_count, content_sha256,
               storage_relative_path, capture_status, telegram_posted_at_utc
        FROM media_records
        WHERE capture_status='MEDIA_CAPTURED'
        ORDER BY CAST(message_id AS INTEGER), message_revision_number"""
for r in mcon.execute(mq):
    out.write(f"[{r['message_id']}] rev{r['message_revision_number']} {r['media_type']} {r['byte_count']}B "
              f"sha256={r['content_sha256']} path={r['storage_relative_path']} posted={r['telegram_posted_at_utc']}\n")

out.close()
con.close()
mcon.close()
print("written")
