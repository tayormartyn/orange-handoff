"""One-shot apply of the F002/F004/F007 XAU_F_TERMINAL_OUTCOME markers (D-063/D-065).
Condition 2: all MISSING records concatenated into ONE newline-terminated buffer and written
with a SINGLE os.write() (never per-record). Idempotent: a marker whose setup_id already has a
XAU_F_TERMINAL_OUTCOME row is skipped, so a re-run writes 0 bytes."""
import hashlib
import json
import os
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
FWD = os.path.normpath(os.path.join(HERE, "..", "forward_validation_ledger_v0_2.jsonl"))
NOW = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

PROV = {"source": "operator_approved_D-063_D-065", "emitted_at_utc": NOW,
        "note": "clean OUTCOME terminal (P10 BE scratch); no defect; NOT an adjudication; number unchanged"}

MARKERS = [
    {"record_type": "XAU_F_TERMINAL_OUTCOME", "setup_id": "XAU-F002-20260714", "direction": "SHORT",
     "terminal_type": "BE_SCRATCH_OUTCOME", "effective_ts_utc": "2026-07-14T14:13:00Z", "basis_price": "4084.58",
     "per_leg_states": [{"leg": "near", "price": "4084", "kind": "MARKET_AT_SIGNAL_CLOSE", "state": "FILLED@4084.58 -> BE_SCRATCH", "be": "4084.58"},
                        {"leg": "mid", "price": "4089.00", "state": "CANCELLED (unfilled)"},
                        {"leg": "far", "price": "4094", "state": "CANCELLED (unfilled)"}],
     "realized_pips_per_unit": "9.95", "defect_affected": False, "statistically_excluded": False,
     "changes_no_number": True, "review_only": True, "executable": False, "observation_only": True, "provenance": PROV},
    {"record_type": "XAU_F_TERMINAL_OUTCOME", "setup_id": "XAU-F004-20260716", "direction": "SHORT",
     "terminal_type": "BE_SCRATCH_OUTCOME", "effective_ts_utc": "2026-07-16T15:21:00Z", "basis_price": "4003",
     "per_leg_states": [{"leg": "near", "price": "4003", "kind": "LIMIT", "state": "FILLED@4003 -> BE_SCRATCH", "be": "4003"},
                        {"leg": "mid", "price": "4008.50", "state": "CANCELLED (unfilled)"},
                        {"leg": "far", "price": "4014", "state": "CANCELLED (unfilled)"}],
     "realized_pips_per_unit": "15.18", "defect_affected": False, "statistically_excluded": False,
     "changes_no_number": True, "review_only": True, "executable": False, "observation_only": True, "provenance": PROV},
    {"record_type": "XAU_F_TERMINAL_OUTCOME", "setup_id": "XAU-F007-20260721", "direction": "LONG",
     "terminal_type": "BE_SCRATCH_OUTCOME", "effective_ts_utc": "2026-07-21T09:29:00Z", "basis_price": "4063",
     "per_leg_states": [{"leg": "near", "price": "4063", "kind": "LIMIT", "state": "FILLED@4063 -> BE_SCRATCH", "be": "4063"},
                        {"leg": "mid", "price": "4058", "state": "CANCELLED (unfilled)"},
                        {"leg": "far", "price": "4053", "state": "CANCELLED (unfilled)"}],
     "realized_pips_per_unit": "5.38", "defect_affected": False, "statistically_excluded": False,
     "changes_no_number": True, "review_only": True, "executable": False, "observation_only": True,
     "model_artefact_terminal": True, "provenance": PROV},
]


def existing_outcome_sids():
    sids = set()
    for line in open(FWD, encoding="utf-8"):
        try:
            r = json.loads(line)
        except ValueError:
            continue
        if r.get("record_type") == "XAU_F_TERMINAL_OUTCOME" and r.get("setup_id"):
            sids.add(r["setup_id"])
    return sids


def main(show_buffer=False):
    before_n = sum(1 for _ in open(FWD, encoding="utf-8"))
    before_sha = hashlib.sha256(open(FWD, "rb").read()).hexdigest()[:16]
    have = existing_outcome_sids()
    missing = [m for m in MARKERS if m["setup_id"] not in have]
    buf = "".join(json.dumps(m, ensure_ascii=False) + "\n" for m in missing)
    if show_buffer:
        print("  --- assembled buffer (Condition 2: ONE buffer, ONE os.write) ---")
        for m in missing:
            print("   ", json.dumps(m, ensure_ascii=False)[:150] + " ...")
        print(f"  buffer bytes: {len(buf.encode('utf-8'))}  |  records to write: {len(missing)}")
    if missing:
        fd = os.open(FWD, os.O_WRONLY | os.O_APPEND)          # append; wire is DOWN so no writer conflict
        try:
            n = os.write(fd, buf.encode("utf-8"))              # <-- SINGLE os.write of the whole buffer
        finally:
            os.close(fd)
        print(f"  APPLIED: 1 os.write, {n} bytes, {len(missing)} record(s)")
    else:
        print("  IDEMPOTENT: all markers already present -> 0 writes, 0 bytes")
    after_n = sum(1 for _ in open(FWD, encoding="utf-8"))
    after_sha = hashlib.sha256(open(FWD, "rb").read()).hexdigest()[:16]
    print(f"  ledger lines {before_n} -> {after_n}  |  sha {before_sha} -> {after_sha}")


if __name__ == "__main__":
    import sys
    main(show_buffer=("--show" in sys.argv))
