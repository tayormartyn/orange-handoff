"""OQ-10 FULL RETROSPECTIVE PASS (D-043 approval; D-045-round requirements a+b inherited).

READ-ONLY over stored media. Output rows: record_class SOURCE_REPORTED_OUTCOME,
eligible_for_prospective_evidence=false, eligible_for_training=false.
Per-row: side, volume_label, symbol, result_usd, entry, second_price (NEVER labelled
'exit'), card_state OPEN/CLOSED/UNDETERMINED (conservative), arithmetic reconciliation
(|dP| x 100 x volume vs displayed result) doubling as the dropped-leading-digit check.
Accuracy report + random operator-verification sample emitted alongside.
"""
import json
import os
import random
import re
import sqlite3
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
ST = r"C:\Users\Marty\signal-terminal"
MEDIA_DB = os.path.join(ST, r"campaign_extractor\prospective\data\prospective_media_v1.db")
MEDIA_DIR = os.path.join(ST, r"campaign_extractor\prospective\data\prospective_media_v1")
EVID_DB = os.path.join(ST, r"campaign_extractor\prospective\data\prospective_evidence_v1.db")
OUT_ROWS = os.path.join(HERE, "source_reported_outcome_v0_1.jsonl")
OUT_REPORT = os.path.join(HERE, "OCR_FULL_PASS_REPORT.md")
RAW_OCR = os.path.join(HERE, "_raw_ocr_lines.txt")

SIDE_RE = re.compile(r"^(buy|sell)\s+([0-9]+(?:\.[0-9]+)?)$", re.I)
PRICE_PAIR_RE = re.compile(r"^([0-9]{3,5}\.[0-9]{2})\s+([0-9]{3,5}\.[0-9]{2})$")
RESULT_RE = re.compile(r"^-?[0-9]{1,6}(?:\.[0-9]{2})?$")
SYMBOL_RE = re.compile(r"XAU|GOLD", re.I)


def ocr_all(paths):
    if not os.path.exists(RAW_OCR):
        lst = os.path.join(HERE, "_paths.txt")
        open(lst, "w", encoding="utf-8").write("\n".join(paths))
        with open(RAW_OCR, "w", encoding="utf-8") as out:
            subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
                            "-File", os.path.join(HERE, "win_ocr_batch.ps1"),
                            "-PathList", lst], stdout=out, text=True, timeout=3600)
    per_file, cur = {}, None
    for ln in open(RAW_OCR, encoding="utf-8", errors="replace"):
        ln = ln.rstrip("\n")
        if ln.startswith("=== FILE "):
            cur = ln[9:].strip(); per_file[cur] = []
        elif ln.startswith("LINE: ") and cur:
            per_file[cur].append(ln[6:])
        elif ln.startswith("!! ERROR"):
            parts = ln.split()
            per_file[parts[2]] = ["__OCR_ERROR__"]
    return per_file


def parse_cards(lines):
    """Group OCR lines into card rows: side/vol -> symbol -> result -> 'entry second'."""
    rows, i = [], 0
    while i < len(lines):
        m = SIDE_RE.match(lines[i].strip())
        if not m:
            i += 1; continue
        row = {"side": m.group(1).lower(), "volume_label": float(m.group(2))}
        j, found_prices = i + 1, False
        while j < len(lines) and j <= i + 5:
            s = lines[j].strip()
            pm = PRICE_PAIR_RE.match(s)
            if pm:
                row["entry"], row["second_price"] = float(pm.group(1)), float(pm.group(2))
                found_prices = True
                break
            if SYMBOL_RE.search(s):
                row["symbol"] = s
            elif RESULT_RE.match(s.replace(" ", "")):
                row["result_usd"] = float(s.replace(" ", ""))
            j += 1
        if found_prices:
            rows.append(row); i = j + 1
        else:
            i += 1
    return rows


def reconcile(row):
    if "result_usd" not in row:
        return "NO_RESULT_FIELD"
    # instrument multiplier: XAU $100/point/lot; BTC-scale prices (>10000) $1/point/lot.
    # BTC rows are K-047 crypto-scoped upstream regardless — never enter XAU analysis.
    mult = 1 if row["entry"] > 10000 else 100
    expect = abs(row["entry"] - row["second_price"]) * mult * row["volume_label"]
    got = abs(row["result_usd"])
    if expect == 0:
        return "ZERO_MOVE"
    if abs(expect - got) <= max(1.5, 0.01 * expect):
        return "PASS"
    # dropped-leading-digit probe: does adding a leading digit fix it?
    for d in "123456789":
        if abs(expect - abs(float(d + str(int(got * 100)).zfill(4)) / 100)) <= max(1.5, 0.01 * expect):
            return f"LEADING_DIGIT_SUSPECT(+{d})"
    return "FAIL"


def main():
    mdb = sqlite3.connect(MEDIA_DB)
    recs = mdb.execute(
        "select message_id, telegram_posted_at_utc, content_sha256, storage_relative_path "
        "from media_records where capture_status='MEDIA_CAPTURED' and media_type='PHOTO' "
        "order by telegram_posted_at_utc").fetchall()
    paths = [os.path.join(MEDIA_DIR, r[3]) for r in recs if r[3]]
    per_file = ocr_all(paths)

    out_rows, stats = [], {"images": len(recs), "ocr_errors": 0, "card_images": 0,
                           "rows": 0, "recon_pass": 0, "recon_fail": 0,
                           "leading_digit_suspect": 0, "no_result": 0, "non_card_images": 0}
    for mid, ts, sha, rel in recs:
        fn = os.path.basename(rel)
        lines = per_file.get(fn, [])
        if lines == ["__OCR_ERROR__"]:
            stats["ocr_errors"] += 1; continue
        rows = parse_cards(lines)
        if not rows:
            stats["non_card_images"] += 1; continue
        stats["card_images"] += 1
        # card_state discriminator: same-entry rows with SAME volume across an image = UNDETERMINED;
        # cross-image sequences are assessed downstream. Conservative default.
        for r in rows:
            r["reconciliation"] = reconcile(r)
            stats["rows"] += 1
            k = r["reconciliation"]
            if k == "PASS":
                stats["recon_pass"] += 1
            elif k.startswith("LEADING_DIGIT"):
                stats["leading_digit_suspect"] += 1
            elif k == "NO_RESULT_FIELD":
                stats["no_result"] += 1
            else:
                stats["recon_fail"] += 1
        out_rows.append({
            "record_class": "SOURCE_REPORTED_OUTCOME",
            "eligible_for_prospective_evidence": False, "eligible_for_training": False,
            "survivorship_limited": True,
            "usage": "MECHANICAL_ENTRY_DIVERGENCE_COMPARISON_ONLY_NEVER_EXPECTANCY",
            "message_id": mid, "posted_at_utc": ts, "image_sha256": sha,
            "card_state": "UNDETERMINED", "rows": rows,
        })
    with open(OUT_ROWS, "w", encoding="utf-8") as f:
        for r in out_rows:
            f.write(json.dumps(r) + "\n")

    random.seed(20260721)
    sample = random.sample(out_rows, min(10, len(out_rows)))
    with open(OUT_REPORT, "w", encoding="utf-8") as f:
        f.write("# OQ-10 FULL PASS — FIRST ACCURACY REPORT (2026-07-21)\n\n")
        f.write(f"Stats: {json.dumps(stats)}\n\n")
        f.write("Reconciliation gate: |dP| x 100 x volume vs displayed result (also catches dropped "
                "leading digits). Rows failing reconciliation are NOT trusted.\n\n")
        f.write("## Operator verification sample (10 random card images — check rows vs the stored image)\n")
        for s in sample:
            f.write(f"- msg {s['message_id']} @ {s['posted_at_utc']} sha {s['image_sha256'][:12]}: "
                    f"{json.dumps(s['rows'])}\n")
    print(json.dumps(stats, indent=1))
    print("rows ->", OUT_ROWS)
    print("report ->", OUT_REPORT)


if __name__ == "__main__":
    main()
