"""Embed model comparison + materiality into the S3 leg-check JSON."""
import json, sys, io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
P = r"C:\Users\Marty\signal-terminal\research\farouk_pilot\always_on_tradingview_receiver_plan\stage_c_tooling\farouk_plus\s3_hold_best_leg_check_v0_1.json"
d = json.load(open(P, encoding="utf-8"))

d["leg_reconstruction"] = {
    "near_edge_leg_model_b_baseline": {"fill": 4072.0, "fill_utc": "12:14", "result_pips": 25.0,
        "note": "BE-scratched 12:28 after banking TP1 tranche (Model B v0_1b row)"},
    "far_edge_hold_best_leg": {"fill": 4083.0, "fill_utc": "12:47", "result_pips": 50.0,
        "note": "banked +50p (TP1 12:56, TP2 12:59) then runner BE-stopped 13:05Z — 4 min after the 13:01:19Z instruction; 9 separate returns to >=4083 after the fill bar"},
    "s3_leg_resolved_blend_50_50": 37.5,
    "no_be_counterfactual": "even a runner with NO BE-stop marks only +79p at window end (18:14 close 4075.06) unless it exits near the 15:32 'full tp' moment (4023.3, +597p) — exit timing, not leg choice, is the value"
}
d["comparison"] = {
    "model_A_s3": "large positive (posted-TP/achievable-credited exits; ~+220-500p class per its divergence table)",
    "model_B_s3": 25.0,
    "leg_resolved_s3": 37.5,
    "step_8d_estimate": "+300..+500p on the hold-best leg — REFUTED by this check (actual +50p): the premise that price did not return to 4083 was wrong (9 BE-returns; first post-instruction at 13:05Z)"
}
d["materiality"] = {
    "model_B_raw_total_pips": {"before": 48.0, "after": 60.5, "mean_before": 1.4, "mean_after": 1.8},
    "model_B_filtered_R2b_R4b": {"before_total": 614.4, "after_total": 626.9, "mean_before": 25.6, "mean_after": 26.1},
    "verdict": "IMMATERIAL — the one HIGH-sensitivity leg case resolves to ~+12.5p on the 34-trade total; the Model-A/B band does NOT narrow via leg reconstruction",
    "strengthened_conclusion": "the literal SL-to-entry instruction destroys follower runners REGARDLESS of leg choice (near or far edge); his private edge is that his own stops provably were not at the literal instructed levels (widget evidence). Instruction timing remains the only band-collapsing data (Step-8C capture)."
}
d["safety"] = {"listener_pid_87988": "untouched", "gates": "PAPER/PREVIEW/False/False unchanged",
                "not_integration_ready": "unchanged", "execution_surface": "none",
                "volumes": "no volume/lot/account/ticket fields recorded"}
with open(P, "w", encoding="utf-8") as fh:
    json.dump(d, fh, indent=2)
print("finalized: leg-resolved S3 =", d["leg_reconstruction"]["s3_leg_resolved_blend_50_50"])
