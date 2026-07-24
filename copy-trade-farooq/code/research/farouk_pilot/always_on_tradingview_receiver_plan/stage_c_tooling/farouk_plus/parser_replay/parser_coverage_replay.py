"""PARSER COVERAGE REPLAY (D-015 step 3) — RETROSPECTIVE_NOT_PROSPECTIVE.

Replays the FULL historical Telegram archive (signal_archive.db, all revisions)
plus the live prospective evidence DB through the CURRENT interpreter, read-only.
Every row resolves to exactly one disposition (zero silent drops, reconciled by
count). No campaign creation, no freezes, no ledger writes — outputs land only
in this directory.
"""
import hashlib
import json
import os
import re
import sqlite3
import sys
from collections import Counter
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
FA = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(FA, "follower_assistant"))
import interpreter  # noqa: E402

ST = r"C:\Users\Marty\signal-terminal"
ARCHIVE = os.path.join(ST, r"data\signal_archive.db")
PROSPECTIVE = os.path.join(ST, r"campaign_extractor\prospective\data\prospective_evidence_v1.db")

INTERP_SHA = hashlib.sha256(
    open(os.path.join(FA, "follower_assistant", "interpreter.py"), "rb").read()).hexdigest()[:16]

CRYPTO_RE = re.compile(r"\b(btc|bitcoin|eth|ethereum|sol|solana|sui|ltc|xrp|doge|bnb|crypto|altcoin)\b", re.I)
CRYPTO_CHANNEL_RE = re.compile(r"sea-scalper|quant-flow|columbus-trades|crypto", re.I)
PIPS_RE = re.compile(r"\b\d{2,4}\s*pips?\b", re.I)


def disposition(raw):
    if raw is None or not str(raw).strip():
        return "EXPLICITLY_REJECTED_EMPTY", None, {}
    c = interpreter.classify(raw)
    kind = c["kind"]
    if kind == "NOT_FAROUK_GOLD":
        scope = ("CRYPTO" if (CRYPTO_RE.search(raw) or CRYPTO_CHANNEL_RE.search(raw.splitlines()[0]))
                 else "OTHER")
        return f"NOT_FAROUK_GOLD_{scope}", None, {}
    if kind == "ENTRY":
        return "PARSED_ENTRY", None, c
    if kind == "MANAGEMENT":
        types = tuple(sorted({i["instruction_type"] for i in c["instructions"]}))
        return "PARSED_MANAGEMENT", types, c
    if kind == "NEEDS_HUMAN_REVIEW":
        why = re.sub(r"\d+", "N", c.get("why", ""))[:60]
        return "QUARANTINED_REVIEW", why, c
    return "PARSED_COMMENTARY", None, c


def replay_db(path, table, id_col, text_col, label):
    db = sqlite3.connect(path)
    rows = db.execute(f"select {id_col}, {text_col} from {table}").fetchall()
    db.close()
    n_in = len(rows)
    disp = Counter()
    mgmt_types = Counter()
    quar_whys = Counter()
    crypto_gold_header = []   # crypto-content rows that PASS the gold header (leak-surface)
    pips_terminal_violation = []  # pips-mention rows that produced a terminal instruction
    samples = {}
    n_out = 0
    for rid, raw in rows:
        d, sub, c = disposition(raw)
        disp[d] += 1
        n_out += 1
        if d == "PARSED_MANAGEMENT":
            for t in sub:
                mgmt_types[t] += 1
            if PIPS_RE.search(raw or "") and any(
                    i["instruction_type"] in ("EXPLICIT_FULL_EXIT", "FINAL_CLOSE")
                    for i in c["instructions"]):
                # pips-count present AND terminal typed — check it is not a bare result card
                if not re.search(r"full[\s-]*(exit|close)|close\s+(all|everything|the\s+trade|100)|trade\s+closed|closed\s+in|fully\s+exit|exit\s+fully", (raw or ""), re.I):
                    pips_terminal_violation.append((label, rid, (raw or "")[:120]))
        if d == "QUARANTINED_REVIEW":
            quar_whys[sub] += 1
        if d.startswith("PARSED_") and CRYPTO_RE.search(raw or "") and interpreter.is_farouk_gold(raw):
            if d == "PARSED_ENTRY":
                crypto_gold_header.append((label, rid, (raw or "")[:120]))
        if d not in samples and d != "NOT_FAROUK_GOLD_OTHER":
            samples[d] = (rid, (raw or "")[:100])
    assert n_in == n_out, f"SILENT DROP: {n_in} in vs {n_out} out"
    return {"label": label, "rows_in": n_in, "rows_dispositioned": n_out,
            "dispositions": dict(disp), "management_instruction_types": dict(mgmt_types),
            "quarantine_reason_classes": dict(quar_whys),
            "crypto_content_parsed_as_gold_entry": crypto_gold_header,
            "pips_terminal_violations": pips_terminal_violation}


HDR = "seascalperfarouk Posted in 🪙・gold-trades\n\n"
REGRESSION = [
    ("labelled-field zone form", HDR + "XAUUSD Sell Zone: 4050-4060 / Stop Loss: 4075",
     lambda c: c["kind"] in ("ENTRY", "NEEDS_HUMAN_REVIEW")),
    ("plain entry form", HDR + "`Whale` XAUUSD SELL 4050-4060 SL 4075",
     lambda c: c["kind"] == "ENTRY"),
    ("full exit", HDR + "full exit here guys",
     lambda c: c["kind"] == "MANAGEMENT" and any(i["instruction_type"] == "EXPLICIT_FULL_EXIT" for i in c["instructions"])),
    ("close 90% leave 10%", HDR + "350 pips! close 90% leave 10%",
     lambda c: c["kind"] == "MANAGEMENT" and any(i["instruction_type"] == "EXPLICIT_PERCENTAGE_PARTIAL_CLOSE" for i in c["instructions"])),
    ("close 100%", HDR + "close 100%",
     lambda c: c["kind"] == "MANAGEMENT" and any(i["instruction_type"] == "EXPLICIT_FULL_EXIT" for i in c["instructions"])),
    ("tp 1 now", HDR + "tp 1 now",
     lambda c: c["kind"] == "MANAGEMENT" and any(i["instruction_type"] == "TP1_TAKE" for i in c["instructions"])),
    ("put sl to entry", HDR + "put sl to entry",
     lambda c: c["kind"] == "MANAGEMENT" and any(i["instruction_type"] == "SL_TO_ENTRY" for i in c["instructions"])),
    ("claimed-pips commentary NOT terminal", HDR + "we made 700 pips on this one!",
     lambda c: not (c["kind"] == "MANAGEMENT" and any(i["instruction_type"] in ("EXPLICIT_FULL_EXIT", "FINAL_CLOSE") for i in c.get("instructions", [])))),
    ("140-150 pips result NOT terminal", HDR + "140-150 pips locked in so far",
     lambda c: not (c["kind"] == "MANAGEMENT" and any(i["instruction_type"] in ("EXPLICIT_FULL_EXIT", "FINAL_CLOSE") for i in c.get("instructions", [])))),
    ("lot-fraction result card NOT entry/terminal", HDR + "0.5 lots banked +250 pips, screenshot attached",
     lambda c: c["kind"] not in ("ENTRY",) and not any(i["instruction_type"] in ("EXPLICIT_FULL_EXIT", "FINAL_CLOSE") for i in c.get("instructions", []))),
    ("crypto in gold channel refused as XAU entry", HDR + "BTC BUY 64000-64500 SL 63000",
     lambda c: c["kind"] == "NEEDS_HUMAN_REVIEW"),
    ("crypto channel not gold", "wazwithazed Posted in 🧮・quant-flow\n\n`Whale` BTC Short 64000",
     lambda c: c["kind"] == "NOT_FAROUK_GOLD"),
]


def main():
    started = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    res = [replay_db(ARCHIVE, "raw_message_versions", "row_id", "raw_text", "signal_archive"),
           replay_db(PROSPECTIVE, "prospective_message_evidence", "evidence_id", "raw_text", "prospective_live")]

    reg_results = []
    for name, text, ok in REGRESSION:
        c = interpreter.classify(text)
        verdict = "PASS" if ok(c) else "FAIL"
        reg_results.append({"fixture": name, "verdict": verdict, "kind": c["kind"],
                            "detail": c.get("why") or [i["instruction_type"] for i in c.get("instructions", [])] or c.get("direction", "")})

    out = {"schema": "parser_coverage_replay_v1", "tag": "RETROSPECTIVE_NOT_PROSPECTIVE",
           "run_at_utc": started, "interpreter_sha16": INTERP_SHA,
           "databases": res, "regression": reg_results}
    with open(os.path.join(HERE, "parser_coverage_replay_results.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1, ensure_ascii=False)

    print(f"interpreter sha {INTERP_SHA}")
    for r in res:
        print(f"\n== {r['label']}: {r['rows_in']} rows -> {r['rows_dispositioned']} dispositions (ZERO silent drops)")
        for k, v in sorted(r["dispositions"].items(), key=lambda x: -x[1]):
            print(f"   {k:<28} {v}")
        print("   mgmt types:", dict(sorted(r["management_instruction_types"].items(), key=lambda x: -x[1])))
        print("   quarantine reasons:", dict(sorted(r["quarantine_reason_classes"].items(), key=lambda x: -x[1])))
        print("   crypto->gold-entry leaks:", len(r["crypto_content_parsed_as_gold_entry"]),
              "| pips-terminal violations:", len(r["pips_terminal_violations"]))
        for row in r["crypto_content_parsed_as_gold_entry"][:5]:
            print("     LEAK:", row)
        for row in r["pips_terminal_violations"][:5]:
            print("     PIPS-TERMINAL:", row)
    print("\n== regression fixtures ==")
    for rr in reg_results:
        print(f"   [{rr['verdict']}] {rr['fixture']:<44} kind={rr['kind']} {rr['detail']}")
    fails = [r for r in reg_results if r["verdict"] == "FAIL"]
    print(f"\nREGRESSION: {len(reg_results) - len(fails)}/{len(reg_results)} PASS")
    return 0 if not fails else 1


if __name__ == "__main__":
    sys.exit(main())
