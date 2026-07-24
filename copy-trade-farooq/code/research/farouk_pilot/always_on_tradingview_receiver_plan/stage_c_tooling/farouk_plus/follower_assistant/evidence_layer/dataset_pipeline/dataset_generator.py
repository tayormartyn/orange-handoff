"""PROSPECTIVE_OUTCOME_AND_DATASET_PIPELINE v0.1 — dataset-row generator (RESEARCH-ONLY).

Joins immutable freezes to their outcomes by immutable hashes and emits a versioned, reproducible,
tamper-sensitive dataset + manifest. One row per causally-frozen campaign. POST_DECISION_LABEL fields
are excluded from the model-feature export. No model is fitted here.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
EVDIR = os.path.dirname(HERE)
for p in (HERE, EVDIR):
    if p not in sys.path:
        sys.path.insert(0, p)

SCHEMA_VERSION = "orange_candidate_dataset_v0_1"
GENERATOR_VERSION = "dataset_generator_v0_1"
SCHEMA = json.load(open(os.path.join(HERE, "dataset_schema_v0_1.json"), encoding="utf-8"))
FIELD_CLASS = SCHEMA["fields"]
LABEL_FIELDS = [k for k, v in FIELD_CLASS.items() if v == "POST_DECISION_LABEL"]
from outcome_pipeline import normalize_class                     # noqa: E402


def _sha_file(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest() if os.path.exists(p) else "ABSENT"


def _load(ledger):
    out = []
    if os.path.exists(ledger):
        for line in open(ledger, encoding="utf-8"):
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return out


def _feature(freeze, node, field):
    try:
        return freeze["hierarchy"][node].get(field)
    except Exception:                                            # noqa: BLE001
        return "UNKNOWN"


def _row(freeze, outcome):
    h = freeze["hierarchy"]
    env = freeze["hash_envelope"]
    supp = freeze["supplemental_contracts"]
    labels = (outcome or {}).get("labels", {})
    elig = (outcome or {}).get("eligibility", {})
    row = {
        # identity / provenance
        "dataset_schema_version": SCHEMA_VERSION, "dataset_manifest_version": SCHEMA_VERSION,
        "campaign_id": freeze["setup_id"], "freeze_id": freeze["logical_hash"],
        "freeze_hash": freeze["logical_hash"], "outcome_id": (outcome or {}).get("logical_hash", "NONE"),
        "outcome_hash": (outcome or {}).get("logical_hash", "NONE"), "candidate_id": freeze["setup_id"] + "/campaign",
        "record_class": normalize_class(freeze.get("record_class")), "source_tier": h["1_source_tier"]["selected_value_if_predetermined"],
        "objective_lane": freeze["objective_lane"], "router_version": freeze["router_version"],
        "feature_contract_versions": [c["file"] for c in env["contract_versions_sha256"]],
        "outcome_contract_version": (outcome or {}).get("outcome_contract_version", "NONE"),
        "source_event_hash": env.get("raw_source_ref", "UNKNOWN"),
        # decision-time features (all frozen at/before decision)
        "instrument": "XAUUSD", "session": h["6_session_model"].get("session_utc"),
        "direction": freeze["direction"],
        "setup_family_eligibility": ["FVG_CONTINUATION_5M", "ASIA_SESSION_FAKEOUT"],
        "liquidity_narrative": h["7_liquidity_narrative"]["status"],
        "poi_roles": h["8_poi_family"]["alternatives"],
        "inducement_flag": any("INDUCEMENT" in str(a) for a in h["8_poi_family"]["alternatives"]),
        "structural_trigger_state": h["9_structural_confirmation"]["selected_value_if_predetermined"],
        "completed_candle_state": h["10_completed_candle_confirmation"]["status"],
        "valid_bos_state": supp["valid_bos"]["status"], "scob_state": supp["scob"]["status"],
        "ote_anchor_count": supp["ote_shadow"].get("total_pairs_enumerated"),
        "ote_documented_levels": supp["ote_shadow"].get("documented_levels"),
        "execution_profile_alternatives": h["3_trading_horizon"]["candidate_values"],
        "no_trade_state": h["6_session_model"].get("no_trade_timing_candidates"),
        "candidate_availability_ts": env["decision_timestamp"], "market_data_cutoff_ts": env["market_data_cutoff_timestamp"],
        "decision_ts": env["decision_timestamp"],
        # post-decision labels
        "activation_result": labels.get("activation_result", "PENDING"),
        "activation_time": labels.get("activation_time"), "stop_target_ordering": labels.get("stop_target_ordering"),
        "mfe_pips": labels.get("mfe_pips"), "mae_pips": labels.get("mae_pips"),
        "mfe_price": labels.get("mfe_price"), "mae_price": labels.get("mae_price"),
        "stop_first": labels.get("stop_first"), "target_first": labels.get("target_first"),
        "invalidation_ts": labels.get("invalidation_ts"), "no_trade_result": labels.get("no_trade_result"),
        "lane_comparison": (outcome or {}).get("lane_comparison", "PENDING"),
        "outcome_status": labels.get("outcome_status", "PENDING"),
        # quality flags
        "causal_integrity": labels.get("causal_integrity", "PENDING"),
        "data_integrity": labels.get("data_integrity", "PENDING"),
        "source_provenance": (outcome or {}).get("record_provenance", {}).get("source_provenance", "PENDING"),
        "intrabar_ambiguous": labels.get("intrabar_ambiguous", False),
        # eligibility
        "eligible_for_prospective_evidence": bool(freeze.get("eligible_for_prospective_evidence")),
        "eligible_for_training": bool(elig.get("eligible_for_training", False)),
        "eligible_for_validation": bool(elig.get("eligible_for_validation", False)),
        "eligible_for_performance_attribution": bool(elig.get("eligible_for_performance_attribution", False)),
        "exclusion_reasons": elig.get("exclusion_reasons", ["no outcome attached (PENDING)"]),
    }
    return row


def feature_export_row(row):
    """Model-feature view: POST_DECISION_LABEL fields removed (hard leakage boundary)."""
    return {k: v for k, v in row.items() if FIELD_CLASS.get(k) != "POST_DECISION_LABEL"}


def _canonical(rows):
    ordered = sorted(rows, key=lambda r: (r["campaign_id"], r["freeze_hash"]))
    blob = json.dumps(ordered, sort_keys=True, default=str, ensure_ascii=False)
    return ordered, hashlib.sha256(blob.encode("utf-8")).hexdigest()


def generate(freeze_ledgers, outcome_ledger, out_dir=None, now_ts=None):
    out_dir = out_dir or os.path.join(HERE, "exports")
    os.makedirs(out_dir, exist_ok=True)
    freezes = []
    for L in freeze_ledgers:
        for r in _load(L):
            if r.get("record_type") == "ROUTER_FREEZE":
                freezes.append(r)
    outcomes = {r["freeze_hash"]: r for r in _load(outcome_ledger) if r.get("record_type") == "ROUTER_OUTCOME"}
    rows, included, excluded = [], [], []
    for fz in freezes:
        oc = outcomes.get(fz["logical_hash"])
        rows.append(_row(fz, oc))
        included.append(fz["setup_id"])
    ordered, dataset_hash = _canonical(rows)
    feature_rows = [feature_export_row(r) for r in ordered]
    # counts
    from collections import Counter
    rc = Counter(r["record_class"] for r in ordered)
    lane = Counter(r["objective_lane"] for r in ordered)
    tier = Counter(r["source_tier"] for r in ordered)
    ostat = Counter(r["outcome_status"] for r in ordered)
    manifest = {
        "manifest_schema_version": SCHEMA_VERSION, "generator_version": GENERATOR_VERSION,
        "generation_timestamp_utc": (now_ts if now_ts is not None else int(time.time())),
        "generation_timestamp_note": "VOLATILE — excluded from canonical_dataset_hash",
        "source_freeze_ledger_hashes": {os.path.basename(L): _sha_file(L) for L in freeze_ledgers},
        "source_outcome_ledger_hash": _sha_file(outcome_ledger),
        "included_campaign_ids": sorted(set(included)), "excluded_campaign_ids": sorted(set(excluded)),
        "exclusion_reasons": {},
        "record_class_counts": dict(rc), "lane_counts": dict(lane), "source_tier_counts": dict(tier),
        "outcome_status_counts": dict(ostat),
        "eligible_row_count": sum(1 for r in ordered if r["eligible_for_training"]),
        "ineligible_row_count": sum(1 for r in ordered if not r["eligible_for_training"]),
        "row_count": len(ordered), "canonical_dataset_hash": dataset_hash,
        "feature_export_excludes": LABEL_FIELDS,
        "review_only": True, "observation_only": True,
    }
    # versioned IMMUTABLE export (filename carries the dataset hash; never overwrite a different version)
    tag = dataset_hash[:12]
    ds_path = os.path.join(out_dir, f"{SCHEMA_VERSION}__{tag}.json")
    feat_path = os.path.join(out_dir, f"{SCHEMA_VERSION}__{tag}.features.json")
    man_path = os.path.join(out_dir, f"{SCHEMA_VERSION}__{tag}.manifest.json")
    if not os.path.exists(ds_path):
        json.dump({"schema": SCHEMA_VERSION, "rows": ordered}, open(ds_path, "w", encoding="utf-8"), indent=1, default=str)
        json.dump({"schema": SCHEMA_VERSION, "feature_rows": feature_rows}, open(feat_path, "w", encoding="utf-8"), indent=1, default=str)
        json.dump(manifest, open(man_path, "w", encoding="utf-8"), indent=1, default=str)
    return {"rows": ordered, "feature_rows": feature_rows, "manifest": manifest,
            "dataset_hash": dataset_hash, "paths": {"dataset": ds_path, "features": feat_path, "manifest": man_path}}


if __name__ == "__main__":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    from outcome_pipeline import ROUTER_OUTCOMES
    fl = [os.path.join(EVDIR, "router_freeze_backfill_v0_1.jsonl"),
          os.path.join(EVDIR, "router_freeze_v0_1.jsonl")]
    res = generate(fl, ROUTER_OUTCOMES)
    m = res["manifest"]
    print("rows:", m["row_count"], "| dataset_hash:", res["dataset_hash"][:16])
    print("record_class_counts:", m["record_class_counts"])
    print("outcome_status_counts:", m["outcome_status_counts"])
    print("eligible_for_training rows:", m["eligible_row_count"], "| ineligible:", m["ineligible_row_count"])
    print("export:", os.path.basename(res["paths"]["dataset"]))
