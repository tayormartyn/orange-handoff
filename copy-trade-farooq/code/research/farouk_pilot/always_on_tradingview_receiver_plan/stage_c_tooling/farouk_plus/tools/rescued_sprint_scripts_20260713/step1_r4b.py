"""Add R4b (no entries after 15:30Z) + rough pip-impact estimates to the comparison JSON."""
import json, sys, io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
P = r"C:\Users\Marty\signal-terminal\research\farouk_pilot\always_on_tradingview_receiver_plan\stage_c_tooling\farouk_plus\winner_loss_comparison_v1.json"

with open(P, encoding="utf-8") as fh:
    data = json.load(fh)

def hour_after_1530(r):
    h = r.get("entry_hour_utc")
    if not h:
        return False
    hh, mm = map(int, h.split(":"))
    return (hh, mm) >= (15, 30)

rem = [r for r in data["setups"] if hour_after_1530(r)]
data["rule_tests"]["R4b_no_entries_after_1530Z"] = {
    "removed_total": len(rem),
    "wins_removed": [r["setup_id"] for r in rem if r["outcome_status"] == "VERIFIED_WIN"],
    "losses_removed": [r["setup_id"] for r in rem if r["outcome_status"] in ("VERIFIED_LOSS","PARTIAL_LOSS")],
    "partials_removed": [r["setup_id"] for r in rem if r["outcome_status"] == "PARTIAL"],
}

data["rule_verdicts"] = {
 "R1_first_touch_only": {"verdict": "INSUFFICIENT_DATA (definition-flawed)",
   "note": "0/20 winners qualify as 'first touch in 4h' — Farouk posts zones at/after price reaches them, so the retrospective proxy removes 29/33 trades indiscriminately. A genuine test needs pre-marked levels (forward TV-alert data)."},
 "R2_attempt_cap_le2": {"verdict": "PROMISING (risk-adjusted)",
   "note": "Removes verified SL loss J17 (attempt 5) + 2 scratches at the cost of one ~150p winner (J29, attempt 3). Roughly pip-neutral, clearly exposure/tail-risk-reducing. CORRECTION to Day-6: J10 was attempt 2 and is NOT filtered by cap<=2."},
 "R2b_no_reentries_cap_le1": {"verdict": "PROMISING (needs more data)",
   "note": "Removes ALL 3 re-entry losses (J08 ~-40p manual, J10 SL ~-250..-400p layered, J17 ~-120..-210p) at the cost of 3 winners (J14~100p, J19~130p, J29~150p; TP1-centric realistic). Rough net +50..+300p AND removes both verified SL losses. Sample of losses is tiny (6)."},
 "R3_disp50_within_60min": {"verdict": "REJECT (as defined)",
   "note": "Zero discrimination: 20/20 wins AND 5/5 measurable losses printed $5-from-zone-mid within 60min (median 0 — entries occur mid-move so the mid is crossed immediately). The real separator in the data is MAE-from-mid: winners median 70p vs losses 284p / partials 387p — i.e. the edge shows up as 'never goes far against', which is a management property, not a timing deadline."},
 "R4_session_filter_LON_NY": {"verdict": "REJECT (as defined)",
   "note": "Removes 5 winners vs 2 losses (off-window trades were 5W/2L/2P). London-lunch and pre-London entries won repeatedly (J02,J04,J07,S3)."},
 "R4b_no_entries_after_1530Z": {"verdict": "PROMISING",
   "note": "Late-day cutoff removes J03 (manual loss, 15:55 touch) + J17 (verified SL loss, 16:40) + J16 (scratch) at the cost of one small winner (J06, ~53p at claim). Rough net clearly positive; matches the late-session-fatigue pattern."},
 "R5_htf_veto": {"verdict": "INSUFFICIENT_DATA",
   "note": "Qualitative notes only: counter-trend S2 lost, but the explicitly counter-trend Jun-26 campaign (J28/J29, half-size) netted a win. 1-1. Farouk's own control is SIZE reduction, not a veto; a veto would have removed winner J29. Needs forward HTF context capture."},
 "R6_claim_discount": {"verdict": "PROMISING (analytic control, zero removal cost)",
   "note": "3 documented inflation cases (J30 +33-56% material, S1 +8% mild, J11 fill-dependent). Rule: compute expectancy on TP1/TP2 structure + scratch modelling, never on runner claims. Applies to the expectancy model, not trade selection."},
}
data["headline_findings"] = [
 "Winners vs losses separate on MAE-from-mid (median 70p vs 284p) and idea_attempt (mean 1.2 vs 2.0) — NOT on displacement timing, session window, or retrospective 'first touch'.",
 "Even losses averaged 157p MFE-from-mid before failing — most of the observable edge is MANAGEMENT (TP1 banking + BE stops), not entry selection.",
 "All three re-entry losses are removed by a no-re-entry rule at acceptable winner cost; the late-day (>=15:30Z) cutoff removes 2 of 6 losses for one small winner.",
 "Day-6 hypothesis corrections: attempt-cap<=2 filters only J17 (J10 was attempt 2); the 50p-displacement deadline does not discriminate at all as measured.",
]

with open(P, "w", encoding="utf-8") as fh:
    json.dump(data, fh, indent=2, ensure_ascii=False)
print("R4b:", json.dumps(data["rule_tests"]["R4b_no_entries_after_1530Z"]))
print("updated:", P)
