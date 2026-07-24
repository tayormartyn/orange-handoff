"""Build validator-passed structured reviews for the two Farouk explainer videos."""
import json, os, sys, io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
ROOT = r"C:\Users\Marty\signal-terminal"
BASE = ROOT + r"\research\farouk_pilot\always_on_tradingview_receiver_plan\stage_c_tooling\farouk_plus"
sys.path.insert(0, os.path.join(ROOT, "ai_review"))
import schema

V2 = {
 "pack_id": "FP-LIVE-VIDEO-EXPLAINER-002",
 "extracted_instrument": "XAUUSD",
 "direction": "SHORT",
 "entry_zone": "posted 4072-4083 (S3); his drawn sell box tops ~4087-4088 on his own chart",
 "sl": "S3 posted 4125; S2 stop discussion: followers at 4180/4186",
 "tp_levels": ["4020 stated exit: 'if we come to 4,020 I will exit the trade'"],
 "result_claim": "'I took two TPs, letting a small part run for lower levels' (S3, at recording time 14:19Z Jul-8)",
 "evidence_used": [45560],
 "confidence": 0.85,
 "contradictions": [],
 "missing_evidence": ["his own S2/S3 fill prices not shown in this video (chart-only, no position widgets)"],
 "ohlc_required": False,
 "verdict": "EXTRACTED",
 "evidence_id": "FP-LIVE-VIDEO-EXPLAINER-002",
 "source_filename": "Schermopname 2026-07-08 om 16.19.48.mov",
 "source_path": "C:/Users/Marty/Downloads/",
 "modified_time_local": "2026-07-11 16:33:36",
 "bytes": 200778955,
 "sha256": "f061b23cc55c04071cccba7ea674eb1187f42d2293213029ba460bccf93d4cf4",
 "duration_min": 5.5,
 "rights_status": "RIGHTS_PENDING_PRIVATE_REVIEW (his own breakdown video, distributed by him to members via msg 45560 CDN link; private research use only; no redistribution; no long quotes)",
 "apparent_trade_dates": "explains S2 (Jul-7 LOSS) retrospect + S3 (Jul-8 SELL) live-running + forward levels",
 "linked_setups": ["XAU-S2-20260707", "XAU-S3-20260708"],
 "explanation_timing": "S2 = post-hoc; S3 = mid-trade (recorded ~14:19Z, before the 15:32Z full-tp); forward levels = pre-planned",
 "key_points": [
   "S2 stop-out confirmed in his own words: 'just stopped out and then dropped'; followers had stops 4180/4186 — matches deterministic 4180.52 graze",
   "STOP-WIDTH LESSON (explicit): 'Next time I'm gonna put my stop loss a little bit higher... or look for a nice entry' — stop placement is adaptive/discretionary, learned from near-misses",
   "S3 construction: OB + broken Asia low with big candle close + retest + M5 CHoCH; 'I was hoping it would go a bit higher to grab more of my sells' (layered sell intent)",
   "His chart's drawn sell box tops ~4087-4088 vs posted 4072-4083 — the private zone is wider/higher than the posted one (fill-divergence mechanism visible)",
   "Indicator panel publishes machine-readable levels live: CHoCH 4065.38, Asia break LOW, OB retest 4065.94, Current/Fresh OB 4045.18 — Lane-6 pre-marking = his own indicator output",
   "Pre-announced forward levels: 4150 sell zone, 4120 good, CHoCH 4099, sell possible 4165, buy zone monthly-low ~4000-4020 (1h OB + BPR)",
   "EXPLICIT HTF VETO in his own words: 'I'm not actually wanting to look for buys today at all... the market is bearish on the four hour' (R5 evidence)",
   "FOMC discipline: 'today's FOMC, I recommend you guys not to take a lot of trades' (news feature evidence)",
   "Claim culture: 'win rates always between the 90 and 80 percent'; 'end of month we always end clean'",
   "Management at recording time: 'stop loss to entry and let the trade run' — yet deterministic data shows 9 returns to 4083 by 13:05Z; his position survived to full-tp 15:32 -> his BE reference was his own (lower/better) fill, not the posted zone edge",
 ],
 "widget_or_sensitive_fields": "none visible in this video (charts only); indicator names visible and recorded as evidence",
}

V1 = {
 "pack_id": "FP-LIVE-VIDEO-EXPLAINER-001",
 "extracted_instrument": "XAUUSD",
 "direction": None,
 "entry_zone": None, "sl": None, "tp_levels": [],
 "result_claim": None,
 "evidence_used": [45642],
 "confidence": 0.7,
 "contradictions": [],
 "missing_evidence": ["full 95-min transcript pending completion at write time; frame survey done"],
 "ohlc_required": False,
 "verdict": "EXTRACTED",
 "evidence_id": "FP-LIVE-VIDEO-EXPLAINER-001",
 "source_filename": "Live with Farouk, Friday, 10 July 2026.mp4",
 "source_path": "C:/Users/Marty/Downloads/",
 "modified_time_local": "2026-07-11 16:27:42",
 "bytes": 386910020,
 "sha256": "f1200fed0ebc5832613bff5882cd976ef80fbe3bba5bd60e360a1d5f853ed892",
 "duration_min": 95.1,
 "rights_status": "RIGHTS_PENDING_PRIVATE_REVIEW (his own YouTube live, linked by him in msg 45642; private research use only; no redistribution; no long quotes)",
 "apparent_trade_dates": "Jul-10 evening stream (~17:16-18:52Z per on-screen clock): S4 recap + weekend/next-week outlook",
 "linked_setups": ["XAU-S4-20260710"],
 "explanation_timing": "post-hoc for S4 + pre-planned forward levels",
 "key_points": [
   "HIS LIVE FEED IS VANTAGE (12h chart tab 'Gold Spot / U.S. Dollar - Vantage'; MT5 'XAUUSD-VIP') — explains his-fill vs Pepperstone-feed divergences",
   "Same indicator stack as video 002 across all tabs (Farouk's Playbook Smart Money Suite, SeaScalper Bias Levels v2, BGS Liquidity Inefficiency, [kyle] v1/v2)",
   "PRE-MARKED forward supply zones drawn on the DAILY: ~4150-4180 and ~4430-4480 (green boxes) — testable Lane-6 pre-marks for the coming week",
   "HTF red levels marked: 4246.34/4244.10 and 4180.46 (the S2 stop region remains a mapped level)",
   "Multi-asset tabs: XAUUSD (multiple), BTCUSDT.P, SOLUSDT.P — one workspace for all his lanes",
 ],
 "widget_or_sensitive_fields": "broker-platform tabs visible; no account ids/tickets readable in sampled frames; nothing recorded beyond platform name as evidence",
}

recs = []
for v in (V1, V2):
    recs.append(schema.validate_reviewer_output(v))
try:
    bad = dict(recs[0]); bad["broker_route"] = "x"
    schema.validate_reviewer_output(bad)
    neg = "FAIL"
except schema.ReviewerOutputRejected as e:
    neg = f"PASS — {e}"

with open(BASE + r"\farouk_video_explainer_001_review.json", "w", encoding="utf-8") as fh:
    json.dump({"review": recs[0], "validator_negative_check": neg}, fh, indent=2, ensure_ascii=False)
with open(BASE + r"\farouk_video_explainer_002_review.json", "w", encoding="utf-8") as fh:
    json.dump({"review": recs[1], "validator_negative_check": neg}, fh, indent=2, ensure_ascii=False)
print("validated=2 negative_check:", neg)
