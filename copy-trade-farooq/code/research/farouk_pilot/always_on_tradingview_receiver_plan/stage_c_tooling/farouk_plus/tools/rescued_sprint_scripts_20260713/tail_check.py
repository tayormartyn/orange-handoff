import sqlite3
EV = r"C:\Users\Marty\signal-terminal\campaign_extractor\prospective\data\prospective_evidence_v1.db"
OUT = r"C:\Users\Marty\AppData\Local\Temp\claude\C--Users-Marty\5fc06f59-5409-4db3-ac12-a901363ccb04\scratchpad\tail_check.txt"
con = sqlite3.connect(f"file:{EV}?mode=ro", uri=True)
con.row_factory = sqlite3.Row
out = open(OUT, "w", encoding="utf-8")
r = con.execute("SELECT MIN(CAST(telegram_message_id AS INTEGER)) lo, MAX(CAST(telegram_message_id AS INTEGER)) hi, COUNT(*) n, MIN(telegram_posted_at_utc) t0, MAX(telegram_posted_at_utc) t1 FROM prospective_message_evidence").fetchone()
out.write(f"window: msgs {r['lo']}..{r['hi']} n={r['n']} {r['t0']} .. {r['t1']}\n\n")
q = """SELECT telegram_message_id id, telegram_posted_at_utc t, media_reference_or_hash m, raw_text txt
       FROM prospective_message_evidence
       WHERE CAST(telegram_message_id AS INTEGER) > 45642
       ORDER BY CAST(telegram_message_id AS INTEGER)"""
for row in con.execute(q):
    txt = (row["txt"] or "").replace("\n", " | ")
    out.write(f"[{row['id']}] {row['t']} media={row['m'] or '-'}\n    {txt[:400]}\n")
out.close()
con.close()
print("done")
