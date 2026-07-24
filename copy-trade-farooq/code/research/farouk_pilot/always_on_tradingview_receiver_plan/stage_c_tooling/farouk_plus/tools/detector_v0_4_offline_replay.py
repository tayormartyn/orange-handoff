"""
Detector v0.4 — OFFLINE replay (historical, review-only). 2026-07-12.

NOT a live scorer. Reads detector_v0_3_replay_results.json (the 34 matched setups,
in-sample) and evaluates the replay-testable v0.4 candidate features ON TOP of v0.3:

  V4-LIT  mitigated_level_exclusion, literal reading  ("already mitigated" = >=1 prior
          touch episode, 24h proxy) -> hard cap of promoted labels at WATCH
  V4-SP   mitigated_level_exclusion, spent-aligned    (>=3 episodes, same threshold F2
          already calls 'spent') -> hard cap at WATCH
  V4-SPX  V4-SP but records with bar-close-confirmed BOS evidence are EXEMPT from the
          cap (mirrors v0.3's ratified candle-close-offsets-F2 behaviour)
  V4-TF   TF-hierarchy grading of bos_candle_close_confirmed (multi-TF stack = +1,
          single-TF close = +0) applied to the v0.3 score

Features assessed but NOT scored (recorded in the feature-effects output):
  displacement_fvg_artifact_test  — UNTESTABLE in-sample: requires FVG presence in the
      leg that formed each zone; zone formation times are not retrospectively
      recoverable (same limitation that forced F2's 24h proxy). Designed test spec
      goes to the report; remains backlog.
  limit_at_zone / posted_vs_actual_sl_gap / indicator_semantics / claim_conventions —
      capture-only packs; scorability assessed by evidence density in the 34-sample.

Labels stay inside the allowed set. No execution fields. Review-only.
"""
import json
import os
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
FP = os.path.dirname(HERE)
SRC = os.path.join(FP, "detector_v0_3_replay_results.json")

ALLOWED = ["REJECT", "WATCH", "SHADOW_CANDIDATE_LOW", "SHADOW_CANDIDATE_MEDIUM",
           "HUMAN_REVIEW_REQUIRED"]
PROMOTED = {"SHADOW_CANDIDATE_LOW", "SHADOW_CANDIDATE_MEDIUM"}


def score_to_label(score):
    if score >= 2:
        return "SHADOW_CANDIDATE_MEDIUM"
    if score == 1:
        return "SHADOW_CANDIDATE_LOW"
    if score >= -1:
        return "WATCH"
    return "REJECT"


def matrix(rows, label_key):
    m = defaultdict(lambda: {"n": 0, "W": 0, "L": 0, "P": 0})
    for r in rows:
        lab = r[label_key]
        m[lab]["n"] += 1
        m[lab][r["outcome"]] += 1
    return {k: dict(v) for k, v in m.items()}


def promoted_losses(rows, label_key):
    return [r["pack_id"] for r in rows
            if r[label_key] in PROMOTED and r["outcome"] == "L"]


def promoted_winners(rows, label_key):
    return [r["pack_id"] for r in rows
            if r[label_key] in PROMOTED and r["outcome"] == "W"]


def moves(rows, key):
    return [{"pack_id": r["pack_id"], "v03": r["v03_label"], key: r[key],
             "outcome": r["outcome"], "touches": r["touches"]}
            for r in rows if r[key] != r["v03_label"]]


def main():
    with open(SRC, encoding="utf-8") as f:
        src = json.load(f)

    rows = []
    for rec in src["records"]:
        f = rec["flags"]
        cc = f.get("bos_candle_close_confirmed")
        cc_multi = bool(cc) and ("5M" in cc or "15M" in cc)  # S4 multi-TF stack
        rows.append({
            "pack_id": rec["pack_id"],
            "v03_score": rec["v03_score"],
            "v03_label": rec["review_label"],
            "outcome": rec["outcome_retrospective"],
            "touches": f.get("f2_zone_touch_episodes_24h_proxy"),
            "hr": rec["review_label"] == "HUMAN_REVIEW_REQUIRED",
            "cc_present": bool(cc),
            "cc_multi_tf": cc_multi,
            "strong": str(f.get("f3_level_quality_tag", "")).startswith("STRONG"),
        })

    for r in rows:
        t = r["touches"]

        # V4-LIT: literal mitigated exclusion (>=1 prior touch episode)
        lab = r["v03_label"]
        if not r["hr"] and t is not None and t >= 1 and lab in PROMOTED:
            lab = "WATCH"
        r["v4lit_label"] = lab

        # V4-SP: spent-aligned exclusion (>=3)
        lab = r["v03_label"]
        if not r["hr"] and t is not None and t >= 3 and lab in PROMOTED:
            lab = "WATCH"
        r["v4sp_label"] = lab

        # V4-SPX: spent-aligned, candle-close-confirmed records exempt
        lab = r["v03_label"]
        if (not r["hr"] and t is not None and t >= 3 and lab in PROMOTED
                and not r["cc_present"]):
            lab = "WATCH"
        r["v4spx_label"] = lab

        # V4-TF: TF-hierarchy grading — multi-TF stack keeps +1, single-TF close
        # loses its +1 (grade 0). Only S3/S4 carry candle-close evidence.
        score = r["v03_score"]
        if r["cc_present"] and not r["cc_multi_tf"]:
            score = score - 1
        r["v4tf_score"] = score
        r["v4tf_label"] = r["v03_label"] if r["hr"] else score_to_label(score)

    out = {
        "replay_id": "detector_v0_4_offline_replay",
        "generated_on": "2026-07-12",
        "mode": "OFFLINE / IN-SAMPLE ONLY / REVIEW_ONLY / NO LIVE PROMOTION",
        "base": "detector v0.3 replay labels (unchanged, from detector_v0_3_replay_results.json)",
        "n_records": len(rows),
        "variants": {
            "V4-LIT": "mitigated_level_exclusion literal (>=1 touch episode, 24h proxy) hard cap at WATCH",
            "V4-SP": "mitigated_level_exclusion spent-aligned (>=3 episodes) hard cap at WATCH",
            "V4-SPX": "V4-SP with candle-close-confirmed exemption",
            "V4-TF": "TF-hierarchy grading of bos_candle_close_confirmed (multi-TF +1, single-TF +0)",
        },
        "matrices": {
            "v03": matrix(rows, "v03_label"),
            "V4-LIT": matrix(rows, "v4lit_label"),
            "V4-SP": matrix(rows, "v4sp_label"),
            "V4-SPX": matrix(rows, "v4spx_label"),
            "V4-TF": matrix(rows, "v4tf_label"),
        },
        "promoted_tier_losses": {
            "v03": promoted_losses(rows, "v03_label"),
            "V4-LIT": promoted_losses(rows, "v4lit_label"),
            "V4-SP": promoted_losses(rows, "v4sp_label"),
            "V4-SPX": promoted_losses(rows, "v4spx_label"),
            "V4-TF": promoted_losses(rows, "v4tf_label"),
        },
        "promoted_tier_winners_count": {
            "v03": len(promoted_winners(rows, "v03_label")),
            "V4-LIT": len(promoted_winners(rows, "v4lit_label")),
            "V4-SP": len(promoted_winners(rows, "v4sp_label")),
            "V4-SPX": len(promoted_winners(rows, "v4spx_label")),
            "V4-TF": len(promoted_winners(rows, "v4tf_label")),
        },
        "label_moves": {
            "V4-LIT": moves(rows, "v4lit_label"),
            "V4-SP": moves(rows, "v4sp_label"),
            "V4-SPX": moves(rows, "v4spx_label"),
            "V4-TF": moves(rows, "v4tf_label"),
        },
        "records": [{
            "pack_id": r["pack_id"], "outcome": r["outcome"], "touches": r["touches"],
            "v03_label": r["v03_label"], "v4lit_label": r["v4lit_label"],
            "v4sp_label": r["v4sp_label"], "v4spx_label": r["v4spx_label"],
            "v4tf_label": r["v4tf_label"],
            "review_only": True, "executable": False, "trade_ready": False,
            "observation_only": True,
        } for r in rows],
        "review_only": True,
    }

    dst = os.path.join(FP, "detector_v0_4_offline_replay_results.json")
    with open(dst, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    print("wrote", dst)

    for v in ["v03", "V4-LIT", "V4-SP", "V4-SPX", "V4-TF"]:
        key = {"v03": "v03_label", "V4-LIT": "v4lit_label", "V4-SP": "v4sp_label",
               "V4-SPX": "v4spx_label", "V4-TF": "v4tf_label"}[v]
        m = matrix(rows, key)
        pl = promoted_losses(rows, key)
        pw = promoted_winners(rows, key)
        print(f"\n{v}: promoted losses={len(pl)} {pl} promoted winners={len(pw)}")
        for lab in ALLOWED:
            if lab in m:
                d = m[lab]
                print(f"  {lab}: n={d['n']} W={d['W']} L={d['L']} P={d['P']}")
        print(f"  moves vs v03: {len(moves(rows, key)) if key != 'v03_label' else 0}")


if __name__ == "__main__":
    main()
