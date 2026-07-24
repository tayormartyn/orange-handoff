"""Step 6: inventory of June captured screenshots joined to ledger setups (read-only)."""
import sqlite3, json, sys, io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
ROOT = r"C:\Users\Marty\signal-terminal"
BASE = ROOT + r"\research\farouk_pilot\always_on_tradingview_receiver_plan\stage_c_tooling"
MEDIA = ROOT + r"\campaign_extractor\prospective\data\prospective_media_v1.db"

d3 = json.load(open(BASE + r"\SPRINT_DAY3_JUNE_XAU_LEDGER_v1.json", encoding="utf-8"))
msg2setup = {}
for s in d3["setups"]:
    for m in s["message_ids"]:
        msg2setup[int(m)] = s["setup_id"]

con = sqlite3.connect(f"file:{MEDIA}?mode=ro", uri=True)
con.row_factory = sqlite3.Row
q = """SELECT message_id, content_sha256, storage_relative_path, byte_count, telegram_posted_at_utc
       FROM media_records
       WHERE capture_status='MEDIA_CAPTURED' AND CAST(message_id AS INTEGER) BETWEEN 44000 AND 45292
       ORDER BY CAST(message_id AS INTEGER)"""
rows = list(con.execute(q))
con.close()
linked = 0
for r in rows:
    mid = int(r["message_id"])
    sid = msg2setup.get(mid, "-")
    if sid != "-":
        linked += 1
    print(f"[{mid}] {sid:22s} {r['byte_count']:>7}B {r['storage_relative_path']} {r['telegram_posted_at_utc'][:16]}")
print(f"\ntotal June captured: {len(rows)}  linked to setups: {linked}")
