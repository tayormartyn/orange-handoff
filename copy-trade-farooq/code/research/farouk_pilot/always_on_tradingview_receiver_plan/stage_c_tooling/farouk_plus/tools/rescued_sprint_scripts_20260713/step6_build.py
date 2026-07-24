"""Step 6: build june_screenshot_review_v1.json — validator-passed structured extractions."""
import json, os, sys, io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
ROOT = r"C:\Users\Marty\signal-terminal"
BASE = ROOT + r"\research\farouk_pilot\always_on_tradingview_receiver_plan\stage_c_tooling"
sys.path.insert(0, os.path.join(ROOT, "ai_review"))
import schema

OUT = BASE + r"\farouk_plus\june_screenshot_review_v1.json"

# reviewed images: (msg_id, setup, sha8, image_type, instrument, direction, vol_text, entry, cur, profit, classification, finding)
REVIEWED = [
 (44704, "XAU-J17-20260615", "689e696a", "CHART_M5_MT5", "XAUUSD-VIP", "LONG (SL line visible)", None, None, None, None,
  "SUPPORTS_LEDGER",
  "M5 chart 15-Jun 20:45-21:15 broker (17:45-18:15Z): SL line drawn at 4318.00 exactly as posted; price 4320-4326 grazing it with a wick to ~4317.5 — consistent with the deterministic 18:00Z SL touch on Pepperstone (feed diff <= ~$1-2). 'Maybe we survive' matches the visual moment before the confirmed stop."),
 (45015, "XAU-J24-20260623", "70dea261", "POSITION_WIDGET_MT5", "XAUUSD-VIP", "SHORT", "sell 1", 4132.02, 4128.38, 364.00,
  "ADDS_CONTEXT",
  "RECOVERS THE MISSING J24 ENTRY: sell filled at 4132.02 (his 'sellzone 4140' note; fill below it). J24 becomes deterministically matchable with the existing Jun-23 1m coverage."),
 (45017, "XAU-J24-20260623", "834d69e8", "POSITION_WIDGET_MT5", "XAUUSD-VIP", "SHORT", "sell 1", 4132.02, 4124.99, 703.00,
  "SUPPORTS_LEDGER",
  "'70 pips' claim EXACT to the decimal from his fill: 4132.02-4124.99 = $7.03 = 70.3 pips."),
 (45021, "XAU-J24-20260623", "45141125", "POSITION_WIDGET_MT5", "XAUUSD-VIP", "SHORT", "sell 1", 4132.02, 4114.99, 1703.00,
  "SUPPORTS_LEDGER",
  "'170 pips' claim EXACT: $17.03 = 170.3 pips. J24 claims are own-fill-precise."),
 (44505, "XAU-J09-20260611", "5a34301f", "POSITION_WIDGET_MT5", "XAUUSD-VIP", "LONG", "buy 1", 4105.40, 4110.87, 547.00,
  "ADDS_CONTEXT",
  "His fill 4105.40 is ABOVE his posted zone top (4103) — late market entry, matching his own 'hade a late entry'. Widget shows +54.7p while the message claims '70 pips' — claim appears framed on follower zone fills (zone-top 4103 -> 78.7p), not his own position."),
 (44535, "XAU-J11-20260611", "eefd2f43", "POSITION_WIDGET_MT5", "XAUUSD-VIP", "LONG", "buy 1", 4056.64, 4119.555, 6291.50,
  "CONTRADICTS_TEXT",
  "Exit widget timestamped 2026.06.11 20:35:06 broker (=17:35:06Z — confirms broker=UTC+3): realised 4056.64->4119.555 = 629 pips vs '800 pips' claimed one minute earlier. Final headline overstated ~27% against HIS OWN closed position. Entry 4056.64 recovered (no zone was ever posted)."),
 (44525, "XAU-J11-20260611", "6beaa55c", "POSITION_WIDGET_MT5", "XAUUSD-VIP", "LONG", "buy 1", 4056.64, 4100.70, 4406.00,
  "SUPPORTS_LEDGER",
  "'Take 50% off' moment: +441p from his fill; the '500 pips' message 3 min later was a modest round-up."),
 (45117, "XAU-J26-20260624", "62d1a654", "POSITION_WIDGET_MT5", "XAUUSD-VIP", "SHORT", "sell 0.5", 4029.76, 3962.32, 3372.00,
  "SUPPORTS_LEDGER",
  "'650 pips taking 90% off': actual 4029.76->3962.32 = 674 pips — claim ACCURATE and slightly conservative. Fill at/below the posted zone bottom (4030)."),
 (45285, "XAU-J30-20260629", "da6929c1", "POSITION_WIDGET_MT5", "XAUUSD-VIP", "LONG", "buy 0.25", 4027.37, 4048.27, 522.50,
  "ADDS_CONTEXT",
  "MATERIALLY REVISES the Day-4 J30 'magnitude contradiction': his fill was 4027.37, BELOW the posted zone (4035-4045). From HIS fill the '240 pips' claim was TRUE (needs 4051.4; high 4052.53 by 12:12). The follower gap stands (posted-zone max 175p) — reclassified from 'inflation' to FILL DIVERGENCE: claims track his own fills, not replicable from the posted zone. Residual 0.25 volume matches 'out 75%'."),
 (44683, "XAU-J13-20260615", "f393f56a", "POSITION_WIDGET_MT5", "XAUUSD-VIP", "LONG", "buy 1.2", 4357.05, 4365.96, 1069.20,
  "ADDS_CONTEXT",
  "Fill 4357.05 ABOVE the posted zone top (4355) — another confessed late market entry ('late entry')."),
 (44835, "XAU-J21-20260618", "13c85449", "POSITION_WIDGET_MT5", "XAUUSD-VIP", "SHORT", "sell 1", 4270.91, 4264.10, 681.00,
  "SUPPORTS_LEDGER",
  "Fill 4270.91 near the zone bottom (4269-4280) — the immediate-market-fill pattern on the worst zone edge for a short; TP1 at +68p consistent with the ~50-70p TP1 habit."),
]

records = []
validated = 0
for mid, sid, sha8, itype, instr, d, vol, entry, cur, profit, cls, finding in REVIEWED:
    rec = {"pack_id": f"{sid}:msg{mid}", "extracted_instrument": "XAUUSD",
           "direction": ("SHORT" if "SHORT" in d else "LONG"), "entry_zone": None,
           "sl": None, "tp_levels": [], "result_claim": None, "evidence_used": [mid],
           "confidence": 0.9, "contradictions": ([finding] if cls == "CONTRADICTS_TEXT" else []),
           "missing_evidence": [], "ohlc_required": False, "verdict": "EXTRACTED",
           "image_sha256_prefix": sha8, "image_type": itype,
           "visible_instrument": instr, "visible_direction": d,
           "visible_volume_text": vol, "visible_entry_price": entry,
           "visible_current_or_close_price": cur, "visible_profit_usd": profit,
           "classification": cls, "finding": finding}
    rec = schema.validate_reviewer_output(rec)
    validated += 1
    records.append(rec)

# negative check
try:
    bad = dict(records[0]); bad["lot_size_seen"] = 1.0
    schema.validate_reviewer_output(bad)
    neg = "FAIL"
except schema.ReviewerOutputRejected as e:
    neg = f"PASS — {e}"

out = {"review_id": "june_screenshot_review_v1", "generated_on": "2026-07-11",
       "mode": "OBSERVATION_ONLY / REVIEW_ONLY — screenshots are evidence, never signals",
       "inventory": {"june_media_captured_total": 77, "linked_to_setups": 62,
                     "reviewed_in_detail": len(REVIEWED),
                     "selection": "all loss-linked photos (1 exists: J17 chart) + entry/exit position widgets for key setups (J24 recovery, J11, J26, J30, J09, J13, J21) — small ~19KB files are MT5 position widgets; large files are annotated charts"},
       "validator": {"records_validated": validated, "negative_check": neg},
       "records": records,
       "headline_findings": [
         "J24 ENTRY RECOVERED from screenshots: sell 1 @ 4132.02 (Jun-23 ~10:20Z) — the last INSUFFICIENT_DATA setup is now deterministically matchable with existing 1m coverage.",
         "FILL DIVERGENCE is systematic: his fills are immediate market entries at post time (J09 4105.40 > zone 4103; J13 4357.05 > zone 4355; J30 4027.37 < zone 4035; J21/J26 at worst/edge zone prices). Posted zones are follower instructions, not his own orders.",
         "Claims track HIS fills: J24 exact to the decimal (70.3/170.3p), J26 conservative (674 vs 650), J30 TRUE from his fill (revises the Day-4 magnitude contradiction to fill divergence), while J11's final '800 pips' is contradicted by his own exit widget (629p) and J09's '70 pips' exceeds his widget (54.7p).",
         "J17 loss chart SUPPORTS the ledger: SL line at 4318.00 visible, price grazing it 17:45-18:15Z, wick ~4317.5 — matches the deterministic 18:00Z stop within feed tolerance.",
         "Broker timezone confirmed UTC+3 via the 44535 exit timestamp (20:35:06 broker = 17:35:06Z message).",
       ],
       "feature_candidates": {
         "fill_divergence_vs_posted_zone": {"class": "PROMISING_SCORING_FEATURE (for R6/expectancy, not entry scoring)",
            "note": "follower-fill expectancy MUST be computed from posted zones, not his claims; his claims are ~own-fill-accurate. Forward: compare position-widget fills (when posted) vs zone to quantify the divergence distribution."},
         "own_fill_claim_precision": {"class": "WATCHLIST_FEATURE",
            "note": "exact-decimal claim days (J24) vs rounded-up days (J11 final) — a claim-integrity signal for R6 claim_quality once history accumulates."},
         "visual_winner_loss_features": {"class": "NEEDS_FORWARD_EVIDENCE",
            "note": "only ONE loss-linked image exists (J17 chart) — no visual winner-vs-loss comparison is honestly possible from June media; losses simply get fewer screenshots (survivorship in his own posting)."},
       },
       "safety": "read-only; no signals; validator-stamped records; no execution surface; listener untouched"}
with open(OUT, "w", encoding="utf-8") as fh:
    json.dump(out, fh, indent=2, ensure_ascii=False)
print(f"records={validated} negative_check={neg}")
print("written:", OUT)
