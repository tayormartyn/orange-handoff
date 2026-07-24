"""Day 3: build June XAU ledger JSON from june_history_backfill_v1.db + media DB (read-only),
validate every Fable extraction through the ai_review fail-closed validator."""
import sqlite3, json, os, sys, io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
ROOT = r"C:\Users\Marty\signal-terminal"
sys.path.insert(0, os.path.join(ROOT, "ai_review"))
import schema

JUNE_DB = os.path.join(ROOT, r"campaign_extractor\prospective\data\june_history_backfill_v1.db")
MEDIA_DB = os.path.join(ROOT, r"campaign_extractor\prospective\data\prospective_media_v1.db")
OUT = os.path.join(ROOT, r"research\farouk_pilot\always_on_tradingview_receiver_plan\stage_c_tooling\SPRINT_DAY3_JUNE_XAU_LEDGER_v1.json")

# setup_id, entry_msg, msg_ids (entry+mgmt+result), direction, entry_zone, sl, tp_levels,
# result_claim, outcome_claim, notes
SETUPS = [
 ("XAU-J01-20260602", 44083, [44083,44085,44086,44097], "LONG", "4519-4529", "4500",
  ["4535","4540","4560"], "'almost hit TP1, took partial profits' then closed manually (44097)",
  "UNCLEAR_SMALL", "close worst hold best; closed early"),
 ("XAU-J02-20260602", 44089, [44089,44090,44092,44097], "LONG", "4505-4514", "4480",
  ["4520","4540","4570"], "'TP almost instantly, then SL entry triggered' (44097)",
  "WIN_CLAIM_SMALL", "TP1 + breakeven exit"),
 ("XAU-J03-20260602", 44102, [44102,44106,44107], "LONG", "4490-4502", "4468",
  ["4508","4520","4540","4560"], "'Cutting the trade for -40-50 pips' (44106) — EXPLICIT LOSS",
  "LOSS_CLAIM", "manual cut before SL; 'win streak is over' (44107)"),
 ("XAU-J04-20260603", 44142, [44142,44143,44145,44146,44147,44148,44150,44152,44154,44155,44156,44158,44159,44161,44162,44170], "SHORT", "4463-4470", "4487",
  ["4430"], "waterfall: sl-entry hit then 2-3 re-entries, tp1s, 'Close here' (44170)",
  "WIN_CLAIM", "3 executions (44142, re-enter 44147, re-enter 44155/56 low lot)"),
 ("XAU-J05-20260603", 44173, [44173,44175,44176,44181], "SHORT", "4456-4462", "4480",
  ["4440","4410"], "50 pips tp1 (44175); '100 pips sl enty' (44181)",
  "WIN_CLAIM", "don't risk profits (44174)"),
 ("XAU-J06-20260603", 44198, [44198,44200,44202,44205], "SHORT", "4440-4446", "4470",
  ["4436","4429","4420","4400"], "'Tp 1 hit' (44200); 'close in profit or play it out' (44205)",
  "WIN_CLAIM_SMALL", "evening trade; day recap 'Gold Trades Recap (5X)' (44203)"),
 ("XAU-J07-20260604", 44223, [44223,44224,44233,44236,44238,44239,44244], "SHORT", "4474-4485", "4515",
  ["4461","4445","4420"], "tp1 hit (44236/44238); sl to entry (44239); still in (44244)",
  "WIN_CLAIM", "copy-account scalps same day EXCLUDED (44227/44228/44234 '2 wins on the bot')"),
 ("XAU-J08-20260604", 44248, [44248,44249,44252,44253,44255], "SHORT", "4479-4488", "4515",
  ["4470","4445","4420"], "'close for a small loss... 1 win, 1 loss today' (44255) — EXPLICIT LOSS",
  "LOSS_CLAIM", "manual close before SL ('just missed our sl')"),
 ("XAU-J09-20260611", 44503, [44503,44504,44505,44506,44507,44508], "LONG", "4090-4103", "4080",
  ["4190"], "tp1 70 pips (44505); 'Sl entry hit' (44508)",
  "WIN_CLAIM_SCRATCH", "HIGH RISK; breakeven exit after 70 pips"),
 ("XAU-J10-20260611", 44508, [44508,44509,44534], "LONG", "3-point layered re-entry (zone not restated)", "4060",
  [], "never explicitly closed; 44534 'Sorry it didn't happen on the first trade' + 'wins and losses are part of the game' implies loss",
  "UNCLEAR_IMPLIED_LOSS", "sl moved to 4060 (44509); outcome not explicitly posted"),
 ("XAU-J11-20260611", 44510, [44510,44511,44513,44520,44525,44526,44533,44534,44535], "LONG", "not stated ('Recovery trade: Gold buy')", "4035",
  [], "'500 pips' (44526) -> '800 pips' (44534), out (44535)",
  "WIN_CLAIM", "recovery trade; entry zone never numerically stated"),
 ("XAU-J12-20260615", 44666, [44666,44667,44668,44669], "SHORT", "4339-4345", "4360",
  ["4334","4329","4319"], "50 pips (44667); 'SL at entry hit... still up 50-60 pips' (44669)",
  "WIN_CLAIM_SCRATCH", "scalp"),
 ("XAU-J13-20260615", 44680, [44680,44681,44682,44683,44684,44685,44686,44687], "LONG", "4350-4355", "4330",
  ["4364","4372","4390"], "tp1 instantly (44682); 'SL at entry hit after a 100-pip move' (44687)",
  "WIN_CLAIM", "HIGH RISK"),
 ("XAU-J14-20260615", 44688, [44688,44689,44690,44691], "LONG", "4348-4358", "4330",
  [], "'SL at entry hit again after a 100-pip move' (44691)",
  "WIN_CLAIM", "re-entry of J13 idea"),
 ("XAU-J15-20260615", 44692, [44692,44693,44694,44695,44696], "LONG", "4346-4356", "4330",
  [], "'SL to entry was hit' (44696) — '4 scalps'",
  "WIN_CLAIM_SCRATCH", "re-entry"),
 ("XAU-J16-20260615", 44697, [44697,44698,44699,44700,44701], "LONG", "4340-4350", "4330",
  ["4364","4370","4390"], "'SL to entry was hit again' (44701)",
  "SCRATCH_CLAIM", "low lot re-entry"),
 ("XAU-J17-20260615", 44701, [44701,44704,44707], "LONG", "4330-4339", "4318",
  [], "'SL was hit on this trade. Result: 6 trades, 1 loss.' (44707) — EXPLICIT LOSS",
  "LOSS_CLAIM", "last re-entry; full SL"),
 ("XAU-J18-20260616", 44731, [44731,44732,44733,44734,44735], "SHORT", "4346-4356", "4372",
  [], "tp1, 'out of the trade after securing tp 1' (44735); per 44752 'Trade 1: 50-60 pips'",
  "WIN_CLAIM", "scalp"),
 ("XAU-J19-20260616", 44736, [44736,44737,44739,44740,44741,44743,44745,44746,44749,44752,44753], "SHORT", "4346-4356", "4375",
  [], "'we have 100 pips so tp 2' (44746); 'SL to entry hit after a 130-pips' (44749); per 44752 'Trade 2: 130 pips'",
  "WIN_CLAIM", "'8 trades this week with only 1 loss' (44753)"),
 ("XAU-J20-20260617", 44765, [44765,44766,44769,44770,44771,44772,44773,44776,44778,44781], "LONG", "4315-4323", "4295",
  ["4328","4332","4345"], "'100 pips take tp 2' (44773); 'tp 1-2 hit' (44776); 'sl entry hit after tp 2' (44781)",
  "WIN_CLAIM", ""),
 ("XAU-J21-20260618", 44834, [44834,44835,44836,44837,44838,44839,44841,44842], "SHORT", "4269-4280", "4300",
  [], "'just missed my sl' (44837) then '110 pips tp2' (44838), tp3 (44839), '200 pips' (44841)",
  "WIN_CLAIM", "NEAR-SL: 'if it hit yours wait for the next trade' — followers may have been stopped"),
 ("XAU-J22-20260618", 44843, [44843,44844,44845,44846,44847,44848,44849,44851], "LONG", "4231-4241", "4318 AS POSTED (impossible for a LONG; likely typo for 4218)",
  [], "tp1 (44844/45); risk-free (44849); 'sl entry hit on the BUY' (44851)",
  "WIN_CLAIM_SCRATCH", "SL as posted is above entry — recorded verbatim, flagged"),
 ("XAU-J23-20260619", 44898, [44898,44902,44903,44906,44909], "LONG", "4154-4164", "4135",
  [], "'closed all trades some in profit, some at a loss... I'll count it as a loss overall' (44906/44909) — EXPLICIT LOSS",
  "LOSS_CLAIM", "'win streak is over' (again)"),
 ("XAU-J24-20260623", None, [45014,45015,45016,45017,45018,45021], "SHORT", "NOT CAPTURED (sellzone ~4140 per 45014)", "entry (sl moved to entry)",
  [], "'70 pips take tp 1' (45017); '100 pips tp 2' (45018); '170 pips' (45021)",
  "WIN_CLAIM", "ENTRY MESSAGE MISSING from gold-trades — mgmt-only evidence; entry likely posted elsewhere/deleted"),
 ("XAU-J25-20260623", 45024, [45024,45025,45026,45027,45028,45029,45030,45031,45032,45033,45034,45039], "SHORT", "4138-4155", "4180",
  ["4130 (mgmt level)"], "50 pips (45025); re-enter (45026); '100 pisp' (45030); '130 pips' (45032); 'take tp 3 170 pips' (45034)",
  "WIN_CLAIM", "re-entered once; holding 0.5 sl-to-entry into close (45039)"),
 ("XAU-J26-20260624", 45086, [45086,45087,45089,45090,45093,45095,45097,45099,45102,45116,45117], "SHORT", "4030-4045", "4130",
  [], "'100 pips tp 1' (45087) -> '200 pisp tp 4' (45095) -> '300 pips' (45102) -> '650 pips taking 90% off' (45117)",
  "WIN_CLAIM", "HIGH RISK LOW LOT; re-entry plan 4070-4080 stated (45097) but not needed"),
 ("XAU-J27-20260625", 45150, [45150,45152,45153,45154,45155,45156,45158], "LONG", "4006-4016", "3970",
  ["4022","4027","4040","4065","open"], "'300 pips' (45154); hold 25% (45156); leave 10% (45158)",
  "WIN_CLAIM", ""),
 ("XAU-J28-20260626", 45195, [45195,45196,45197,45198,45199,45200,45201,45202,45203], "SHORT", "4078-4092", "4120",
  [], "100 pips sl-to-entry (45196); re-enter quarter (45198); tp1 again (45200); 'SL got hit again' (45203 — BE stops)",
  "WIN_CLAIM_SCRATCH", "half size high risk; 2 executions with BE stop-outs after profit"),
 ("XAU-J29-20260626", 45203, [45203,45204,45205,45206,45207,45208,45209,45210,45213,45214,45215,45217,45218], "SHORT", "4084-4094", "4120",
  [], "'90 pips take 2 tps' (45208); '100+ pips' (45210); '150 pips' (45215); 'missed by 1 pip... most of you got stopped out at entry. I'll exit' (45217)",
  "WIN_CLAIM", "followers likely BE-stopped; his exit in profit; 'zero losses' week claim (45239)"),
 ("XAU-J30-20260629", 45268, [45268,45269,45270,45271,45274,45275,45276,45278,45279,45280,45281,45284,45285,45287], "LONG", "4035-4045", "4010",
  ["4050","4055","4062","4080","4090"], "tp1 (45270); '170 pips 50%' (45278); '200 pips' (45279); '240 pips' (45281); out 75% (45285); 'SL entry hit out of the trade' (45287)",
  "WIN_CLAIM", "overlaps start of live local capture"),
]

jcon = sqlite3.connect(f"file:{JUNE_DB}?mode=ro", uri=True)
jcon.row_factory = sqlite3.Row
mcon = sqlite3.connect(f"file:{MEDIA_DB}?mode=ro", uri=True)
mcon.row_factory = sqlite3.Row

def msg_row(mid):
    return jcon.execute("SELECT telegram_posted_at_utc t, raw_text x, media_reference_or_hash m "
                        "FROM june_message_evidence WHERE telegram_message_id=?", (str(mid),)).fetchone()

def media_of(mid):
    r = mcon.execute("SELECT content_sha256 s, storage_relative_path p, byte_count b FROM media_records "
                     "WHERE message_id=? AND capture_status='MEDIA_CAPTURED' ORDER BY message_revision_number DESC LIMIT 1",
                     (str(mid),)).fetchone()
    return {"message_id": mid, "sha256": r["s"], "path": "campaign_extractor/prospective/data/prospective_media_v1/" + r["p"], "bytes": r["b"]} if r else None

ledger = {"ledger_id": "XAU_JUNE_DISCRETIONARY_LEDGER_v1", "generated_on": "2026-07-11",
          "mode": "OBSERVATION_ONLY",
          "source": "bounded copied-session backward fetch 2026-06-01..2026-06-29 (1256 msgs whole-channel, 273 gold-trades)",
          "storage": "june_history_backfill_v1.db (append-only) + prospective_media_v1 (photos)",
          "authority_note": "All outcomes are the poster's own claims (RESULT_CLAIM_ONLY); no OHLC matching run.",
          "setups": [], "validator": {"validated": 0, "rejected": 0}}

for sid, entry, mids, direction, zone, sl, tps, claim, outcome, notes in SETUPS:
    media = [m for m in (media_of(i) for i in mids) if m]
    first = msg_row(mids[0])
    ext = {"pack_id": sid, "extracted_instrument": "XAUUSD", "direction": direction,
           "entry_zone": zone, "sl": sl, "tp_levels": tps, "result_claim": claim,
           "evidence_used": mids, "confidence": 0.85 if entry else 0.5,
           "contradictions": [], "missing_evidence": ([] if entry else ["entry message not captured"]),
           "ohlc_required": True, "verdict": "EXTRACTED" if entry else "NEEDS_HUMAN_REVIEW"}
    validated = schema.validate_reviewer_output(ext)
    ledger["validator"]["validated"] += 1
    ledger["setups"].append({
        "setup_id": sid, "status": "RESULT_CLAIM_ONLY",
        "entry_message_id": entry, "first_msg_utc": first["t"] if first else None,
        "message_ids": mids, "direction": direction, "entry_zone": zone, "sl": sl,
        "tp_levels": tps, "result_claim": claim, "outcome_claim_class": outcome,
        "management_notes": notes, "media_captured": media,
        "fable_extraction_validated": {k: validated[k] for k in
            ("review_only", "executable", "trade_ready", "verdict")},
    })

by = {}
for s in ledger["setups"]:
    by[s["outcome_claim_class"]] = by.get(s["outcome_claim_class"], 0) + 1
ledger["summary"] = {
    "distinct_setups": len(SETUPS),
    "entry_executions_including_re-entries": 33,
    "active_trading_days": 14,
    "outcome_claim_classes": by,
    "explicit_loss_claims": ["XAU-J03-20260602", "XAU-J08-20260604", "XAU-J17-20260615", "XAU-J23-20260619"],
    "implied_loss": ["XAU-J10-20260611"],
    "june_claim_comparison": {
        "claimed": "22 trades, 2 losers",
        "reconstructed": "30 distinct setups (33 entry executions) across 14 active days; 4 EXPLICIT self-admitted losses + 1 implied + ~6 breakeven scratches",
        "verdict": "CONTRADICTED (loss count: >=4 admitted vs 2 claimed); trade count ~consistent under setup-idea counting (24-30 vs 22)"},
}
photos = sum(len(s["media_captured"]) for s in ledger["setups"])
ledger["summary"]["setup_linked_photos"] = photos

with open(OUT, "w", encoding="utf-8") as fh:
    json.dump(ledger, fh, indent=2, ensure_ascii=False)

print(f"setups={len(SETUPS)} validator_validated={ledger['validator']['validated']} "
      f"classes={by} setup_linked_photos={photos}")
print(f"written: {OUT}")

# negative check again for the record
try:
    bad = dict(pack_id="NEG", extracted_instrument="XAUUSD", direction="SHORT", entry_zone="1-2",
               sl="3", tp_levels=[], result_claim=None, evidence_used=[], confidence=0.5,
               contradictions=[], missing_evidence=[], ohlc_required=True, verdict="EXTRACTED",
               lot_size=0.5)
    schema.validate_reviewer_output(bad)
    print("NEGATIVE CHECK FAILED")
except schema.ReviewerOutputRejected as e:
    print(f"negative check PASS: {e}")
