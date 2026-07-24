"""
gold_review_pack.py — READ-ONLY neutral human-review pack for the 15 approved influential rows.

Emits ONLY the source evidence needed to adjudicate each row: id, source reference, original raw
message text, parsed fields, the detected anomaly, and BLANK reviewer_decision / reviewer_notes.
It deliberately DOES NOT include cleaned expectancy, aggregate impact, shadow-retention conclusions,
the detector's outcome verdict, or any proposed corrected answer — so the reviewer is not biased.
Selection order is preserved. No database row is altered. Writes only under data/reports/.
"""
from __future__ import annotations
import csv
import json
import os
import sqlite3
import sys
import time

ARCHIVE = "data/signal_archive.db"
REPORTS = "data/reports"

# approved selection, in order. id_type: 'signal_prefix' (8-char) or 'message_key'.
SELECTED = [
    (1, "signal_prefix", "ebb58321", "R_KNOWN_BROKEN_PARSE", "implausible R magnitude (221.63) + malformed tp2=60"),
    (2, "signal_prefix", "d743bc19", "R_KNOWN_BROKEN_PARSE", "malformed tp1=30 (absurd TP distance); R=-1"),
    (3, "signal_prefix", "d0e62d04", "R_KNOWN_BROKEN_PARSE", "malformed tp1=30 (absurd TP distance); R=-0.18"),
    (4, "signal_prefix", "7eb17241", "ENTRY_STOP_SCALE_CONFLICT", "entry ~0.06 vs stop ~3515; stop wrong side"),
    (5, "signal_prefix", "aa522ba6", "ENTRY_STOP_SCALE_CONFLICT", "entry ~0.07 vs stop ~3533; stop wrong side"),
    (6, "signal_prefix", "cd9ef59d", "ENTRY_STOP_SCALE_CONFLICT", "entry ~0.1 vs stop ~3560; stop wrong side"),
    (7, "signal_prefix", "4287f2b5", "ENTRY_STOP_SCALE_CONFLICT", "entry ~0.1 vs stop ~3617; malformed TP"),
    (8, "message_key", "telegram:-1001902136163:29549", "CAT5_RECOVERABLE", "genuine gold entry missing a stop field"),
    (9, "message_key", "telegram:-1001902136163:36842", "CAT5_RECOVERABLE", "genuine gold entry missing a stop field"),
    (10, "message_key", "telegram:-1001902136163:38406", "CAT5_RECOVERABLE", "genuine gold entry missing a stop field"),
    (11, "message_key", "telegram:-1001902136163:40123", "CAT5_RECOVERABLE", "genuine gold entry missing a stop field"),
    (12, "message_key", "telegram:-1001902136163:40276", "CAT6_NO_ADMISSIBLE_OUTCOME", "structurally ok, no admissible outcome"),
    (13, "message_key", "telegram:-1001902136163:42393", "CAT6_NO_ADMISSIBLE_OUTCOME", "structurally ok, no admissible outcome"),
    (14, "message_key", "telegram:-1001902136163:42666", "CAT6_NO_ADMISSIBLE_OUTCOME", "structurally ok, no admissible outcome"),
    (15, "message_key", "telegram:baseline:103", "CAT6_NO_ADMISSIBLE_OUTCOME", "structurally ok, no admissible outcome"),
]


def _ro(db):
    c = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    c.row_factory = sqlite3.Row
    return c


def _raw_text(conn, message_key):
    row = conn.execute("SELECT raw_text FROM raw_message_versions WHERE message_key=? "
                       "ORDER BY version_number DESC LIMIT 1", (message_key,)).fetchone()
    return (row["raw_text"] if row else None)


def _signal_by(conn, *, prefix=None, message_key=None):
    if prefix:
        return conn.execute("SELECT * FROM signals WHERE signal_id LIKE ? LIMIT 1", (prefix + "%",)).fetchone()
    return conn.execute("SELECT * FROM signals WHERE source_message_key=? LIMIT 1", (message_key,)).fetchone()


def build():
    conn = _ro(ARCHIVE)
    pack = []
    for rank, id_type, ident, kind, anomaly in SELECTED:
        s = _signal_by(conn, prefix=ident) if id_type == "signal_prefix" else _signal_by(conn, message_key=ident)
        ref = (s["source_message_key"] if s else ident)
        raw = _raw_text(conn, ref) if ref else None
        r_ev = None
        if s:
            op = conn.execute("SELECT calculated_r, r_is_known FROM outcome_projections WHERE signal_id=?",
                              (s["signal_id"],)).fetchone()
            r_ev = (op["calculated_r"] if op and op["r_is_known"] else None)
        parsed = ({"direction": s["direction"], "entry_low": s["entry_low"], "entry_high": s["entry_high"],
                   "stop": s["stop"], "tp1": s["tp1"], "tp2": s["tp2"], "tp3": s["tp3"],
                   "asset": s["asset"], "calculated_r_as_evidence": r_ev}
                  if s else {"note": "no parsed archive row (recovered market-call) — see raw text"})
        pack.append({
            "rank": rank, "row_id": (s["signal_id"] if s else ident), "id_type": id_type,
            "source_reference": ref, "provider": (s["provider"] if s and "provider" in s.keys() else None),
            "sent_at_utc": (s["sent_at_utc"] if s else None),
            "instrument": (s["asset"] if s else "XAUUSD"),
            "original_message_text": raw,
            "parsed_fields": parsed,
            "detected_anomaly": anomaly, "anomaly_kind": kind,
            "reviewer_decision": "", "reviewer_notes": ""})
    conn.close()
    return pack


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    os.makedirs(REPORTS, exist_ok=True)
    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    pack = build()
    jpath = os.path.join(REPORTS, f"gold_influential_review_pack_{stamp}.json")
    cpath = os.path.join(REPORTS, f"gold_influential_review_pack_{stamp}.csv")
    meta = {"pack": "GOLD_INFLUENTIAL_REVIEW_PACK", "as_of_utc": _now(), "rows": len(pack),
            "excluded_from_pack_to_avoid_bias": ["cleaned_expectancy", "aggregate_impact",
                "shadow_retention", "detector_outcome_verdict", "proposed_corrected_answer"],
            "instructions": "Fill reviewer_decision + reviewer_notes per row. Do not delete the R=221.63 row.",
            "items": pack}
    with open(jpath, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2, default=str)
    with open(cpath, "w", newline="", encoding="utf-8") as f:
        cols = ["rank", "row_id", "source_reference", "provider", "sent_at_utc", "instrument",
                "detected_anomaly", "parsed_direction", "parsed_entry_low", "parsed_entry_high",
                "parsed_stop", "parsed_tp1", "parsed_tp2", "parsed_tp3", "calculated_r_as_evidence",
                "original_message_text", "reviewer_decision", "reviewer_notes"]
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for p in pack:
            pf = p["parsed_fields"]
            w.writerow({"rank": p["rank"], "row_id": p["row_id"], "source_reference": p["source_reference"],
                        "provider": p["provider"], "sent_at_utc": p["sent_at_utc"], "instrument": p["instrument"],
                        "detected_anomaly": p["detected_anomaly"], "parsed_direction": pf.get("direction"),
                        "parsed_entry_low": pf.get("entry_low"), "parsed_entry_high": pf.get("entry_high"),
                        "parsed_stop": pf.get("stop"), "parsed_tp1": pf.get("tp1"), "parsed_tp2": pf.get("tp2"),
                        "parsed_tp3": pf.get("tp3"), "calculated_r_as_evidence": pf.get("calculated_r_as_evidence"),
                        "original_message_text": (p["original_message_text"] or "").replace("\n", " ")[:400],
                        "reviewer_decision": "", "reviewer_notes": ""})
    print(f"review pack: {len(pack)} rows")
    print(f"  {jpath}")
    print(f"  {cpath}")
    return 0


def _now():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


if __name__ == "__main__":
    sys.exit(main())
