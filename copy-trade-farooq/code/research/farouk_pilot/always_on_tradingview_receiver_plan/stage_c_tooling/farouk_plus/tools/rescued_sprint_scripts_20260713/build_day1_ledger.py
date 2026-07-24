"""
Sprint Day 1 — XAUUSD discretionary Telegram trade ledger builder (observation-only).

Reads the prospective evidence DB + media DB READ-ONLY, builds 4 evidence packs,
runs the ai_review lane (stub reviewer -> fail-closed validator), validates the
Fable-5 manual extractions through the SAME validator, runs a negative
forbidden-field check, and writes the ledger JSON.

No execution surface. No broker fields. RESULT_CLAIM_ONLY statuses.
"""
import sqlite3, json, sys, os, io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = r"C:\Users\Marty\signal-terminal"
sys.path.insert(0, os.path.join(ROOT, "ai_review"))
import schema
import stub_reviewer

EV = os.path.join(ROOT, r"campaign_extractor\prospective\data\prospective_evidence_v1.db")
MEDIA = os.path.join(ROOT, r"campaign_extractor\prospective\data\prospective_media_v1.db")
OUT = os.path.join(ROOT, r"research\farouk_pilot\always_on_tradingview_receiver_plan\stage_c_tooling\SPRINT_DAY1_XAU_LEDGER_v1.json")

SOURCE_CHANNEL = "Telegram -1001902136163 (Whale Discord mirror), sub-channel '\U0001FA99・gold-trades', author seascalperfarouk"

SETUPS = [
    {
        "setup_id": "XAU-S1-20260630",
        "msg_ids": [45331, 45332, 45333, 45334, 45335, 45336, 45338, 45339, 45340,
                    45341, 45342, 45343, 45344, 45345, 45347, 45369],
        "entry_msg": 45331,
        "photo_msgs": [45334, 45339, 45340, 45344, 45345, 45347, 45369, 45370],
    },
    {
        "setup_id": "XAU-S2-20260707",
        "msg_ids": [45499, 45500, 45502, 45559],
        "entry_msg": 45499,
        "photo_msgs": [],
    },
    {
        "setup_id": "XAU-S3-20260708",
        "msg_ids": [45552, 45553, 45554, 45555, 45556, 45557, 45558, 45560, 45561,
                    45562, 45566, 45567],
        "entry_msg": 45552,
        "photo_msgs": [45554, 45555, 45556, 45557, 45558, 45561, 45567],
    },
    {
        "setup_id": "XAU-S4-20260710",
        "msg_ids": [45625, 45626, 45627, 45628, 45629, 45630, 45631, 45632, 45633,
                    45634, 45635],
        "entry_msg": 45625,
        "photo_msgs": [45628, 45629, 45630, 45632],
    },
]

con = sqlite3.connect(f"file:{EV}?mode=ro", uri=True)
con.row_factory = sqlite3.Row
mcon = sqlite3.connect(f"file:{MEDIA}?mode=ro", uri=True)
mcon.row_factory = sqlite3.Row


def fetch_messages(ids):
    rows = []
    for mid in ids:
        r = con.execute(
            """SELECT telegram_message_id, telegram_posted_at_utc, raw_text, media_reference_or_hash
               FROM prospective_message_evidence
               WHERE CAST(telegram_message_id AS INTEGER)=?
               ORDER BY message_revision_number DESC LIMIT 1""", (mid,)).fetchone()
        if r is None:
            raise SystemExit(f"FATAL: msg {mid} not found in evidence DB")
        rows.append(r)
    return rows


def fetch_captured_media(ids):
    items = []
    for mid in ids:
        r = mcon.execute(
            """SELECT message_id, content_sha256, storage_relative_path
               FROM media_records
               WHERE CAST(message_id AS INTEGER)=? AND capture_status='MEDIA_CAPTURED'
               ORDER BY message_revision_number DESC LIMIT 1""", (mid,)).fetchone()
        if r is not None:
            items.append({
                "message_id": int(r["message_id"]),
                "sha256": r["content_sha256"],
                "path": "campaign_extractor/prospective/data/prospective_media_v1/" + r["storage_relative_path"],
            })
    return items


# ---- Fable 5 manual extractions (review-only; validated by the deterministic validator) ----
FABLE_EXTRACTIONS = {
    "XAU-S1-20260630": {
        "direction": "SHORT", "entry_zone": "4060-4075", "sl": "4100",
        "tp_levels": [],
        "result_claim": "progressive: 60 pips (45333) -> 100 pips (45338) -> 150 pips closing 0.5 (45340) -> 180 pips (45343) -> 200 pips take 50% off (45345) -> '1000+ pips I close fully now' (45369, 2026-07-01T02:35Z); WIN_CLAIM",
        "confidence": 0.9,
        "contradictions": [],
        "missing_evidence": [
            "no fixed TP ladder stated (management by progressive pip calls)",
            "screenshots referenced (45334/45339/45340/45344/45345/45347/45369/45370) but binaries NOT captured (pre-fix era) - backfillable",
            "no OHLC for the window -> result unverified",
        ],
        "notes_management": "HIGH RISK; SUPER LOW LOT; sl to entry (45334); closing 0.5 at 150 pips; 50% off at 200 pips; leave 10% sl to entry (45347)",
        "verdict": "EXTRACTED",
    },
    "XAU-S2-20260707": {
        "direction": "SHORT", "entry_zone": "4144-4154", "sl": "4180",
        "tp_levels": ["4135", "4130", "4120", "4115", "4110", "4105"],
        "result_claim": "'Trade failed unfortunately' (45502, 2026-07-07T13:43Z); 'Got stopped out by 0.60 cents' (45559, 2026-07-08T14:18Z); LOSS_CLAIM",
        "confidence": 0.9,
        "contradictions": [],
        "missing_evidence": [
            "no screenshots for this setup",
            "exact stop-out time not stated (between 11:33 and 13:43 UTC)",
            "no OHLC for the window -> loss claim unverified (and '0.60 cents' overshoot claim untestable without 1m data)",
        ],
        "notes_management": "no low-lot note on this one; TP ladder given 4 minutes after entry",
        "verdict": "EXTRACTED",
    },
    "XAU-S3-20260708": {
        "direction": "SHORT", "entry_zone": "4072-4083", "sl": "4125",
        "tp_levels": ["4020"],
        "result_claim": "'200+ pips take more off' (45556) -> 'Lets go 500 pips' (45562) -> 'full tp hit now we wait for fomc' (45567, 2026-07-08T15:32Z); WIN_CLAIM",
        "confidence": 0.85,
        "contradictions": [],
        "missing_evidence": [
            "TP1 level never numerically stated (only '4020' target for the residual 10%)",
            "screenshots referenced (45554/45555/45556/45557/45558/45561/45567) but binaries NOT captured (pre-fix era) - backfillable",
            "existing OHLC file starts 16:12 UTC, AFTER the 15:32 full-tp claim -> window uncovered",
        ],
        "notes_management": "low lot please; close worst hold best sl entry (45553); take 50% off; close 90% leave 10% for 4020 (45561)",
        "verdict": "EXTRACTED",
    },
    "XAU-S4-20260710": {
        "direction": "SHORT", "entry_zone": "4102-4115", "sl": "4152",
        "tp_levels": ["4077", "4055"],
        "result_claim": "'100 pips' (45629, 13:25Z) -> '200 pips' (45632, 13:30Z); TP2 4077 / TP3 4055 conditional (45635); NO full-close message in capture (ends 45642, 16:52Z); WIN_CLAIM_PARTIAL",
        "confidence": 0.85,
        "contradictions": [],
        "missing_evidence": [
            "final close/outcome message absent from local capture window",
            "no OHLC after 08:09 UTC on Jul-10 -> claims unverified",
        ],
        "notes_management": "LOW LOT; take tp1 close worst entry hold best sl to entry (45627); take 50% off sl to entry (45634)",
        "verdict": "EXTRACTED",
    },
}

# ---- OHLC export requirements per setup (1m, UTC, Pepperstone XAUUSD) ----
OHLC_REQUIREMENTS = [
    {"setup_id": "XAU-S1-20260630", "symbol": "XAUUSD (Pepperstone)", "timeframe": "1m",
     "start_utc": "2026-06-30T13:00:00Z", "end_utc": "2026-07-01T04:00:00Z",
     "buffer_rationale": "entry posted 14:25Z Jun-30 (-85min buffer); final claim '1000+ pips close fully' 02:35Z Jul-01 (+85min buffer)",
     "covered_by_existing_files": False,
     "suggested_filename": "XAUUSD_1M_2026-06-30_1300_2026-07-01_0400_UTC.csv"},
    {"setup_id": "XAU-S2-20260707", "symbol": "XAUUSD (Pepperstone)", "timeframe": "1m",
     "start_utc": "2026-07-07T10:00:00Z", "end_utc": "2026-07-07T16:00:00Z",
     "buffer_rationale": "entry posted 11:29Z (-89min buffer); 'Trade failed' 13:43Z (+137min buffer; stop-out time unknown, needs SL-4180 touch check)",
     "covered_by_existing_files": False,
     "suggested_filename": "XAUUSD_1M_2026-07-07_1000_1600_UTC.csv"},
    {"setup_id": "XAU-S3-20260708", "symbol": "XAUUSD (Pepperstone)", "timeframe": "1m",
     "start_utc": "2026-07-08T11:00:00Z", "end_utc": "2026-07-08T16:30:00Z",
     "buffer_rationale": "entry posted 12:14Z (-74min buffer); 'full tp hit' 15:32Z (+58min buffer, joins existing file which starts 16:12Z)",
     "covered_by_existing_files": False,
     "suggested_filename": "XAUUSD_1M_2026-07-08_1100_1630_UTC.csv"},
    {"setup_id": "XAU-S4-20260710", "symbol": "XAUUSD (Pepperstone)", "timeframe": "1m",
     "start_utc": "2026-07-10T11:30:00Z", "end_utc": "2026-07-10T22:00:00Z",
     "buffer_rationale": "entry posted 12:43Z (-73min buffer); last claim 13:38Z but NO close message captured -> extend to Friday market close (~21:59Z) to adjudicate TP2 4077 / TP3 4055 / SL-to-entry",
     "covered_by_existing_files": False,
     "suggested_filename": "XAUUSD_1M_2026-07-10_1130_2200_UTC.csv"},
]

ledger = {
    "ledger_id": "XAU_DISCRETIONARY_TELEGRAM_LEDGER_v1",
    "generated_on": "2026-07-11",
    "mode": "OBSERVATION_ONLY",
    "capture_window": "2026-06-29T13:21:18Z .. 2026-07-10T16:52:49Z (msgs 45285..45642, 269 records)",
    "source_channel": SOURCE_CHANNEL,
    "authority_note": "All result figures are the poster's own claims (RESULT_CLAIM_ONLY). Deterministic validators are the authority; AI review output is review-only, never an executable signal.",
    "setups": [],
    "ohlc_export_requirements": OHLC_REQUIREMENTS,
    "ai_review": {"provider_stub": "stub_reviewer.review(provider='stub')",
                  "provider_fable": "Fable 5 manual extraction validated via schema.validate_reviewer_output",
                  "negative_check": None},
}

print("=" * 80)
for spec in SETUPS:
    sid = spec["setup_id"]
    msgs = fetch_messages(spec["msg_ids"])
    captured = fetch_captured_media(spec["photo_msgs"])
    captured_ids = {m["message_id"] for m in captured}
    referenced_not_captured = [m for m in spec["photo_msgs"] if m not in captured_ids]

    pack = {
        "pack_id": sid,
        "instrument": "XAUUSD",
        "source_channel": SOURCE_CHANNEL,
        "messages": [
            {"message_id": int(r["telegram_message_id"]),
             "timestamp_utc": r["telegram_posted_at_utc"],
             "raw_text": r["raw_text"] or ""}
            for r in msgs
        ],
        "media": captured,
        "ohlc_summary": None,
        "notes": "Discretionary Telegram gold call; observation-only; result numbers are the poster's own claims.",
    }
    schema.validate_evidence_pack(pack)

    # 1) stub reviewer through the fail-closed validator
    stub_out = stub_reviewer.review(pack, provider="stub")

    # 2) Fable 5 extraction through the SAME validator
    fable_raw = dict(FABLE_EXTRACTIONS[sid])
    fable_raw.update({
        "pack_id": sid,
        "extracted_instrument": "XAUUSD",
        "evidence_used": spec["msg_ids"],
        "ohlc_required": True,
    })
    fable_out = schema.validate_reviewer_output(fable_raw)

    agree = (stub_out["direction"] == fable_out["direction"]
             and (stub_out["sl"] or "").replace(",", "") == fable_out["sl"])

    entry_row = next(r for r in msgs if int(r["telegram_message_id"]) == spec["entry_msg"])
    ledger["setups"].append({
        "setup_id": sid,
        "status": "RESULT_CLAIM_ONLY",
        "entry_message_id": spec["entry_msg"],
        "entry_posted_at_utc": entry_row["telegram_posted_at_utc"],
        "message_ids": spec["msg_ids"],
        "direction": fable_out["direction"],
        "entry_zone": fable_out["entry_zone"],
        "sl": fable_out["sl"],
        "tp_levels": fable_out["tp_levels"],
        "result_claim": fable_out["result_claim"],
        "management_notes": FABLE_EXTRACTIONS[sid]["notes_management"],
        "media_captured": captured,
        "media_referenced_not_captured": referenced_not_captured,
        "evidence_pack": pack,
        "ai_review_stub_output": stub_out,
        "ai_review_fable_output": fable_out,
        "stub_vs_fable_direction_sl_agree": agree,
    })
    print(f"{sid}: pack ok | stub verdict={stub_out['verdict']} dir={stub_out['direction']} "
          f"entry={stub_out['entry_zone']} sl={stub_out['sl']} | fable verdict={fable_out['verdict']} "
          f"| review_only={fable_out['review_only']} executable={fable_out['executable']} | agree={agree}")

# 3) negative check: forbidden execution field MUST be rejected
neg = dict(FABLE_EXTRACTIONS["XAU-S4-20260710"])
neg.update({"pack_id": "NEGATIVE-CHECK", "extracted_instrument": "XAUUSD",
            "evidence_used": [], "ohlc_required": True, "lot_size": 0.5})
try:
    schema.validate_reviewer_output(neg)
    ledger["ai_review"]["negative_check"] = "FAIL: forbidden field accepted"
    print("NEGATIVE CHECK FAILED — forbidden field was accepted!")
except schema.ReviewerOutputRejected as e:
    ledger["ai_review"]["negative_check"] = f"PASS: rejected as expected ({e})"
    print(f"negative check: PASS — {e}")

con.close()
mcon.close()

with open(OUT, "w", encoding="utf-8") as fh:
    json.dump(ledger, fh, indent=2, ensure_ascii=False)
print(f"\nledger written: {OUT}")
print(f"setups in ledger: {len(ledger['setups'])}")
