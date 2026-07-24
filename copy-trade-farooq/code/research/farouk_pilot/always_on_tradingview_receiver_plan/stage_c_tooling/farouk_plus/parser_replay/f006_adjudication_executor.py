"""F006 TERMINAL ADJUDICATION EXECUTOR (D-031/D-032; operator-approved with 2 conditions).

Modes: dry (print records, write NOTHING) | apply (append-only; idempotent) | verify.
Appends: XAU_F_SETUP rev4 (terminal, adjudicated) + XAU_F_TERMINAL_ADJUDICATION to the
forward ledger; one close record to the follower ledger. Nothing else touched; cards
are tracker-owned and adopt the terminal at the tracker's next restart (stated honestly).
"""
import copy
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
FP = os.path.abspath(os.path.join(HERE, ".."))
FA = os.path.join(FP, "follower_assistant")
sys.path.insert(0, FA)
import guards  # noqa: E402

FWD = os.path.join(FP, "forward_validation_ledger_v0_2.jsonl")
FOL = os.path.join(FA, "follower_ledger_v0_1.jsonl")
SID = "XAU-F006-20260720"
ADJ_ID = "adjudication_20260720_f006_false_open_v0_1"
T_EFF = "2026-07-20T16:41:00+00:00"

PER_LEG = [
    {"leg": "near", "entry": "4010", "fill_status_at_terminal": "FILLED then CLOSED at ~15:12Z by CLOSE_WORST (msg 45938; worst = highest entry for a LONG)",
     "be_level_dropped_instruction_would_set": "moot - leg already closed before 16:41Z",
     "wick_16_41Z_would_trigger": "N/A (closed)", "terminal_state": "CLOSED_BY_INSTRUCTION (pre-terminal)"},
    {"leg": "mid", "entry": "4005.00", "fill_status_at_terminal": "FILLED, reduced to 1/6 open per card after TP1 (45937) + HOLD_BEST (45938; best = lowest FILLED entry for a LONG)",
     "be_level_dropped_instruction_would_set": "4005.00 (per-leg break-even, Constitution v0.1 unscoped SL-to-entry)",
     "wick_16_41Z_would_trigger": "YES - bar low 4001.30 <= 4005.00", "terminal_state": "BE_STOP_SCRATCH_ADJUDICATED at 4005.00, 16:41Z (the ONLY leg this adjudication closes)"},
    {"leg": "far", "entry": "4000", "fill_status_at_terminal": "NEVER FILLED (PROPOSED throughout; wick low 4001.30 did not reach 4000)",
     "be_level_dropped_instruction_would_set": "n/a unfilled; the dropped SL_TO_ENTRY would have CANCELLED it at ~15:10Z per ratified P14 (risk-off cancels resting)",
     "wick_16_41Z_would_trigger": "NO (4001.30 > 4000)", "terminal_state": "CANCELLED_ADJUDICATED (P14 effect of the dropped instruction; factually never filled either way)"},
]

PRECONDITIONS = {
    "a_independent_price_evidence": "16:41Z single-bar low 4001.30 through BE region; 3992 never traded (tracker ingestion log, PEPPERSTONE_TV_BAR_FEED)",
    "b_corroborating_source_hashed": "video sha256 de34a426ab0ce7680461c556677fc4033bd4bc8b2a258aceb1f45f7d84a67b75, transcript [07:15]/[09:21] 'stop plus entry got hit'",
    "c_named_registered_defect": "PARTIAL_INSTRUCTION_SILENT_LOSS (D-028, registered before proposal)",
    "d_pre_excluded": "statistically excluded at D-028/D-030, before the D-031 proposal",
    "operator_approval": "granted 2026-07-20 subject to Conditions 1+2 (this record satisfies both)",
}


def build_records():
    lines = [json.loads(l) for l in open(FWD, encoding="utf-8")]
    if any(r.get("record_type") == "XAU_F_TERMINAL_ADJUDICATION" and r.get("setup_id") == SID
           for r in lines):
        return None, None, None  # already adjudicated -> idempotent zero-write
    rev3 = [r for r in lines if r.get("setup_id") == SID and r.get("record_type") == "XAU_F_SETUP"
            and r.get("revision") == 3][-1]
    rev4 = copy.deepcopy(rev3)
    rev4["revision"] = 4
    rev4["interpretation_source"] = ADJ_ID + " (human-approved; append-only)"
    rev4["management_timing_8c"]["instruction_events"] = (
        rev3["management_timing_8c"]["instruction_events"] + [{
            "instruction_type": "EXPLICIT_FULL_EXIT", "message_id": None,
            "adjudicated": True, "adjudication_id": ADJ_ID,
            "basis": "BE_STOP_SCRATCH_ADJUDICATED from independent bar evidence (no Telegram message exists; Farouk disclosed only on video)",
            "timestamp_utc": T_EFF}])
    rev4["notes"] = (rev4.get("notes", "") +
                     " | TERMINAL BY ADJUDICATION " + ADJ_ID + " @ " + T_EFF +
                     " | OUTCOME_AFFECTED_BY_DEFECT: PARTIAL_INSTRUCTION_SILENT_LOSS"
                     " | STATISTICALLY EXCLUDED (pre-excluded at D-028/D-030)"
                     " | purpose: terminate false open state (jam + false-outcome risk), never number-improvement")
    adj = {"record_type": "XAU_F_TERMINAL_ADJUDICATION", "setup_id": SID,
           "adjudication_id": ADJ_ID, "status": "BE_STOP_SCRATCH_ADJUDICATED",
           "effective_utc": T_EFF, "price_basis": "4005.00 (mid-leg per-leg break-even)",
           "per_leg_terminal_states": PER_LEG,
           "preconditions_v1": PRECONDITIONS,
           "governance": "TERMINAL_ADJUDICATION_GOVERNANCE_RULE.md (all four preconditions required; divergence alone never sufficient)",
           "provenance_chain": ["D-028 defect discovery", "D-030 independent detection",
                                "D-031 proposal", "D-032 approval w/ conditions"],
           "lane_a_statistics": "EXCLUDED (defect-affected; excluded before proposal)",
           "originals": "all prior records preserved unaltered; append-only",
           "review_only": True, "observation_only": True,
           "executable": False, "trade_ready": False,
           "timestamp_utc": T_EFF}
    fol = {"kind": "FOLLOWER_ADJUDICATED_CLOSE", "setup_id": SID, "adjudication_id": ADJ_ID,
           "effective_utc": T_EFF,
           "detail": "runner (mid leg 1/6) BE-scratched at 4005.00 per adjudication; near closed earlier by instruction; far cancelled per P14 effect of dropped SL_TO_ENTRY; EXCLUDED from Lane A statistics",
           "flag": "OUTCOME_AFFECTED_BY_DEFECT: PARTIAL_INSTRUCTION_SILENT_LOSS"}
    return rev4, adj, fol


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "dry"
    rev4, adj, fol = build_records()
    if rev4 is None:
        print("ALREADY_ADJUDICATED -> zero writes (idempotent)")
        return 0
    guards.assert_clean(rev4, "F006 adjudicated rev4")
    guards.assert_clean(adj, "F006 adjudication record")
    if mode == "dry":
        print("=== DRY RUN (nothing written) ===")
        for r in (rev4, adj, fol):
            print(json.dumps(r, ensure_ascii=False)[:400], "...\n")
        return 0
    if mode == "apply":
        with open(FWD, "a", encoding="utf-8") as f:
            f.write(json.dumps(rev4, ensure_ascii=False) + "\n")
            f.write(json.dumps(adj, ensure_ascii=False) + "\n")
        with open(FOL, "a", encoding="utf-8") as f:
            f.write(json.dumps(fol, ensure_ascii=False) + "\n")
        print("APPLIED: fwd +2 (rev4 + adjudication), follower +1")
        return 0
    print("unknown mode")
    return 1


if __name__ == "__main__":
    sys.exit(main())
