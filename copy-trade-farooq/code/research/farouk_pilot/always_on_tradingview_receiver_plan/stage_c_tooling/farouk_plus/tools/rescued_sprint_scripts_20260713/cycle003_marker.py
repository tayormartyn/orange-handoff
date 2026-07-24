"""Cycle 003: clean NO_NEW_XAU_SETUP marker + cursor update. Pre-marks unchanged (market closed)."""
import json, io, sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
BASE = r"C:\Users\Marty\signal-terminal\research\farouk_pilot\always_on_tradingview_receiver_plan\stage_c_tooling\farouk_plus"

marker = {"record_type": "CYCLE_MARKER", "cycle_id": "CYCLE_003", "run_date": "2026-07-11", "revision": 1,
 "mode": "OBSERVATION_ONLY",
 "listener_pid_87988": "running (start 2026-07-10 21:54:45, untouched)",
 "messages_checked": 0, "message_id_range_checked": "none new (store unchanged at 45646 = cursor)",
 "alert_lane_records_checked": 0,
 "alert_lane_note": "market still closed (Saturday evening) - no XAU alerts can fire; R2 read unnecessary",
 "pre_mark_status_check": {
   "PM-F001-SELL-4150-4184": "UNCHANGED - PRE_MARK_OBSERVED, match PENDING, not expired (Jul-17); market closed since creation, zone untouched",
   "PM-F002-SUPPLY-4430-4480": "UNCHANGED - PRE_MARK_OBSERVED, match PENDING, not expired (Jul-31); zone untouched"},
 "new_xau_setups": 0, "result": "NO_NEW_XAU_SETUP",
 "xau_f001": "not created (nothing to create it from)",
 "detector_ab": "v0.2/v0.3 parallel scoring armed",
 "batch_001b_capture_spec": "ARMED for the first real setup: average-entry evidence, tranche schedule, entry count, 4th-entry violation flag, FVG-after-OB artifact, strong-OB rubric components, follower stop-widening marker (expected absent)",
 "labels_emitted": [], "hr_queue_appends": 0, "ohlc_export_requests": [], "outcome_matching_run": False,
 "safety": "no broker/QST/cTrader/nano/copy/demo/live execution; no permits/leases/orders; gates PAPER/PREVIEW/False/False unchanged; NOT_INTEGRATION_READY unchanged",
 "notes": "first cycle with the Batch-001B capture-only additions armed; pre_mark_candidates_v0_1.jsonl left untouched (no status change)"}
with open(BASE + r"\forward_validation_ledger_v0_2.jsonl", "a", encoding="utf-8") as fh:
    fh.write(json.dumps(marker, ensure_ascii=False) + "\n")

cur = json.load(open(BASE + r"\forward_cursor.json", encoding="utf-8"))
cur.update({"last_cycle": "CYCLE_003", "last_cycle_run_at_utc": "2026-07-11T19:30Z"})
with open(BASE + r"\forward_cursor.json", "w", encoding="utf-8") as fh:
    json.dump(cur, fh, indent=2)
print("CYCLE_003 marker appended; cursor updated (still 45646)")
