"""Cycle 002: instantiate the two video-derived PRE_MARK_CANDIDATE seeds (validator-passed) +
append the cycle marker to the forward ledger. No new setup exists (store unchanged at 45646)."""
import json, os, sys, io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
ROOT = r"C:\Users\Marty\signal-terminal"
BASE = ROOT + r"\research\farouk_pilot\always_on_tradingview_receiver_plan\stage_c_tooling\farouk_plus"
sys.path.insert(0, os.path.join(ROOT, "ai_review"))
import schema

SEEDS = [
 {"pre_mark_id": "PM-F001-SELL-4150-4184",
  "pre_mark_time_utc": "2026-07-11T18:30:00Z (instantiated; evidence recorded 2026-07-10 ~17:16-18:52Z)",
  "pre_mark_source": "FP-LIVE-VIDEO-EXPLAINER-001 (sha256 f1200fed…d892): daily green supply box ~4150-4180 drawn on stream + spoken plan '80-84 [4180-4184]-ish we're gonna put our stop loss to entry' + weekly OB bounce note",
  "pre_mark_direction": "SHORT",
  "pre_mark_zone": "4150-4184",
  "level_type_tag": ["HTF_SUPPLY_DEMAND", "OB", "RETEST(S2 stop region 4180.46 marked on his chart)"],
  "zone_touch_count_since_formation": 0,
  "confluence_ranking_cited": ["HTF supply box (chart-drawn)", "weekly OB (spoken)", "prior S2-region liquidity (4180.46 level marked)"],
  "stop_outside_zone_candidate": "structure-relative: beyond zone top 4184 + level-type width (HTF/untagged median $20 from F6 calibration -> ~4204); formula FROZEN for this window",
  "invalidation_width_usd": 20.0,
  "bar_close_confirmed": "N/A — source is his own recorded stream (not an indicator value); repaint guard not applicable",
  "repaint_guard_status": "CLEAN (non-indicator source)",
  "leakage_check_status": "CLEAN (all evidence timestamps 2026-07-10, before pre-mark time; no post exists yet)",
  "expiry_time_utc": "2026-07-17T21:00:00Z (his stated 'next week' horizon)",
  "farouk_post_match_status": "PENDING",
  "label": "PRE_MARK_OBSERVED"},
 {"pre_mark_id": "PM-F002-SUPPLY-4430-4480",
  "pre_mark_time_utc": "2026-07-11T18:30:00Z (instantiated; evidence recorded 2026-07-10 ~17:16-18:52Z)",
  "pre_mark_source": "FP-LIVE-VIDEO-EXPLAINER-001: large daily green supply box ~4430-4480 drawn on stream",
  "pre_mark_direction": "SHORT",
  "pre_mark_zone": "4430-4480",
  "level_type_tag": ["HTF_SUPPLY_DEMAND"],
  "zone_touch_count_since_formation": 0,
  "confluence_ranking_cited": ["HTF supply box (chart-drawn)"],
  "stop_outside_zone_candidate": "structure-relative: beyond zone top 4480 + HTF width (STRONG-class widths ran $20-85; use $40 midpoint -> ~4520); formula FROZEN for this window",
  "invalidation_width_usd": 40.0,
  "bar_close_confirmed": "N/A — non-indicator source",
  "repaint_guard_status": "CLEAN (non-indicator source)",
  "leakage_check_status": "CLEAN",
  "expiry_time_utc": "2026-07-31T21:00:00Z (multi-week HTF horizon, documented choice)",
  "farouk_post_match_status": "PENDING",
  "label": "PRE_MARK_OBSERVED"},
]

lines = []
for s in SEEDS:
    rec = {"pack_id": s["pre_mark_id"], "extracted_instrument": "XAUUSD",
           "direction": s["pre_mark_direction"], "entry_zone": s["pre_mark_zone"], "sl": None,
           "tp_levels": [], "result_claim": None, "evidence_used": [45642],
           "confidence": 0.5, "contradictions": [], "missing_evidence": [],
           "ohlc_required": False, "verdict": "EXTRACTED", **{k: v for k, v in s.items() if k != "pre_mark_direction"}}
    rec = schema.validate_reviewer_output(rec)
    if rec["label"] not in ("PRE_MARK_OBSERVED", "PRE_MARK_MATCHED_FAROUK", "PRE_MARK_DID_NOT_MATCH",
                             "PRE_MARK_INSUFFICIENT_CONTEXT", "PRE_MARK_EXPIRED"):
        raise SystemExit("bad label")
    lines.append(rec)

with open(BASE + r"\pre_mark_candidates_v0_1.jsonl", "w", encoding="utf-8") as fh:
    for r in lines:
        fh.write(json.dumps(r, ensure_ascii=False) + "\n")

marker = {"record_type": "CYCLE_MARKER", "cycle_id": "CYCLE_002", "run_date": "2026-07-11", "revision": 1,
          "mode": "OBSERVATION_ONLY", "listener_pid_87988": "running (start 2026-07-10 21:54:45, untouched)",
          "messages_checked": 0, "message_id_range_checked": "none new (store unchanged at 45646 = cursor)",
          "alert_lane_records_checked": 0,
          "alert_lane_note": "Saturday, market closed - no XAU alerts can fire; R2 archive read unnecessary (nothing new can exist); local Gate-G/H archives unchanged",
          "new_xau_setups": 0, "result": "NO_NEW_XAU_SETUP",
          "pre_mark_candidates_created": ["PM-F001-SELL-4150-4184 (PRE_MARK_OBSERVED, expires 2026-07-17)",
                                            "PM-F002-SUPPLY-4430-4480 (PRE_MARK_OBSERVED, expires 2026-07-31)"],
          "detector_ab": "v0.2/v0.3 parallel scoring armed; no setup to score this cycle",
          "labels_emitted": [], "hr_queue_appends": 0, "ohlc_export_requests": [],
          "outcome_matching_run": False,
          "safety": "no broker/QST/cTrader/nano/copy/demo/live execution; no permits/leases/orders; gates PAPER/PREVIEW/False/False unchanged; NOT_INTEGRATION_READY unchanged",
          "notes": "first cycle under the full 8C+8D+8F+v0.3+Lane-6-builder stack; seeds instantiated from video-001 evidence (leak-free: all evidence ts 2026-07-10 < pre-mark ts)"}
with open(BASE + r"\forward_validation_ledger_v0_2.jsonl", "a", encoding="utf-8") as fh:
    fh.write(json.dumps(marker, ensure_ascii=False) + "\n")

cur = json.load(open(BASE + r"\forward_cursor.json", encoding="utf-8"))
cur.update({"last_cycle": "CYCLE_002", "last_cycle_run_at_utc": "2026-07-11T18:30Z",
            "note": cur["note"] + "; CYCLE_002 clean (no new msgs); 2 pre-mark seeds instantiated"})
with open(BASE + r"\forward_cursor.json", "w", encoding="utf-8") as fh:
    json.dump(cur, fh, indent=2)

print("pre-mark candidates written:", len(lines), "| cycle marker appended | cursor updated (still 45646)")
