import sqlite3, json

DB = r"C:\Users\Marty\signal-terminal\campaign_extractor\prospective\data\prospective_evidence_v1.db"
con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
con.row_factory = sqlite3.Row
cur = con.cursor()

print("=== TABLES ===")
for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"):
    print(r["name"])

print("\n=== SCHEMAS ===")
for r in cur.execute("SELECT name, sql FROM sqlite_master WHERE type='table' ORDER BY name"):
    print(r["sql"])
    print()

con.close()
