"""Minimal stdlib xlsx reader: dump sheets, headers, and rows (redacting sizing/account columns)."""
import zipfile, re, sys, io
from xml.etree import ElementTree as ET

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
REDACT = re.compile(r"lot|size|risk|account|balance|ticket|leverage|margin|volume|deposit|equity|p&l \$|pnl \$|\$", re.I)

def load(path, max_rows=40):
    z = zipfile.ZipFile(path)
    shared = []
    if "xl/sharedStrings.xml" in z.namelist():
        root = ET.fromstring(z.read("xl/sharedStrings.xml"))
        for si in root.findall("m:si", NS):
            shared.append("".join(t.text or "" for t in si.iter("{http://schemas.openxmlformats.org/spreadsheetml/2006/main}t")))
    wb = ET.fromstring(z.read("xl/workbook.xml"))
    sheets = [(s.get("name"), i + 1) for i, s in enumerate(wb.find("m:sheets", NS))]
    print(f"=== {path.split(chr(92))[-1]} — sheets: {[s[0] for s in sheets]}")
    for name, idx in sheets:
        p = f"xl/worksheets/sheet{idx}.xml"
        if p not in z.namelist():
            continue
        root = ET.fromstring(z.read(p))
        rows = root.find("m:sheetData", NS)
        print(f"\n--- sheet '{name}' ---")
        redact_cols = set()
        for ri, row in enumerate(rows.findall("m:row", NS)):
            if ri >= max_rows:
                print(f"  ... ({len(rows)} rows total)")
                break
            cells = []
            for c in row.findall("m:c", NS):
                ref = c.get("r", "")
                col = re.match(r"[A-Z]+", ref).group(0) if ref else "?"
                v = c.find("m:v", NS)
                val = v.text if v is not None else ""
                if c.get("t") == "s" and val:
                    val = shared[int(val)]
                if ri == 0 and REDACT.search(str(val)):
                    redact_cols.add(col)
                    val = f"[REDACTED_HEADER:{col}]"
                elif col in redact_cols:
                    val = "[R]"
                cells.append(str(val)[:28])
            print("  " + " | ".join(cells))
    z.close()

for f in sys.argv[1:]:
    load(f)
    print()
