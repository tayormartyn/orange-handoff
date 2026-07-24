"""Finalize J24 rematch JSON: status + updated June counts."""
import json, sys, io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
P = r"C:\Users\Marty\signal-terminal\research\farouk_pilot\always_on_tradingview_receiver_plan\stage_c_tooling\farouk_plus\j24_deterministic_rematch_v1.json"
d = json.load(open(P, encoding="utf-8"))

d["status"] = "VERIFIED_WIN"
d["status_precision"] = "1m-confirmed"
d["claim_verdict"] = "SUPPORTED (all three claim levels touched 1-6 min BEFORE his messages; widget values exact from his fill)"
d["adjudication_note"] = (
    "SHORT from 4132.02 (screenshot-recovered): 70p level touched 10:42Z (msg 10:43:25), 100p level 10:51Z "
    "(msg 10:57), 170p level 12:13Z (msg 12:14:10); MFE 267p (low 4105.29); no hard SL ever posted; the "
    "position provably survived to +170p (widgets). FOLLOWER-DIVERGENCE CAVEAT: price returned to the fill "
    "price at 10:34Z after the 10:25Z 'sl to entry' instruction — a follower with SL exactly at 4132.02 "
    "would have scratched flat BEFORE the 267p move; his own position survived (stop elsewhere or feed "
    "difference). Third quantified case of his-outcome vs follower-outcome divergence -> R6 follower-fill "
    "expectancy input (preserved for R6 design; NOT an execution artefact).")
d["fill_divergence_preserved_for_R6"] = True
d["updated_final_june_counts"] = {
    "strict_setup_count": 30, "entry_executions": 33, "grouped_campaign_count": 24,
    "VERIFIED_WIN": 19, "VERIFIED_LOSS": 2, "PARTIAL": 9,
    "CONTRADICTED": 0, "AMBIGUOUS_INTRABAR": 0, "INSUFFICIENT_DATA": 0,
    "note": "J24 INSUFFICIENT->VERIFIED_WIN (revision 2, screenshot-recovered entry); Day-4/5 records preserved append-only"}
d["updated_cumulative_sprint_sample"] = {
    "trades_matched": 34, "sessions": 18,
    "VERIFIED_WIN": 21, "VERIFIED_LOSS": 3, "PARTIAL": 10, "CONTRADICTED": 0, "INSUFFICIENT_DATA": 0,
    "precision_split": "11 x 1m-confirmed (J24-J30 June + S1-S4 July), 23 x 5m-fallback"}

with open(P, "w", encoding="utf-8") as fh:
    json.dump(d, fh, indent=2)
print("finalized:", d["status"], "| June:", d["updated_final_june_counts"]["VERIFIED_WIN"], "W /",
      d["updated_final_june_counts"]["VERIFIED_LOSS"], "L /", d["updated_final_june_counts"]["PARTIAL"], "P /",
      d["updated_final_june_counts"]["INSUFFICIENT_DATA"], "insufficient")
