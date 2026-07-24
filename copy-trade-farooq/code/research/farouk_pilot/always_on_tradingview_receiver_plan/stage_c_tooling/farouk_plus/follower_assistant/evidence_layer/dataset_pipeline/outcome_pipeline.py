"""PROSPECTIVE_OUTCOME_AND_DATASET_PIPELINE v0.1 — outcome attachment engine (RESEARCH-ONLY).

Additive + watcher-independent. Reads an IMMUTABLE router freeze and append-only market evidence,
computes deterministic post-decision labels, and appends an outcome record to a SEPARATE append-only
ledger (router_outcomes_v0_1.jsonl). It NEVER edits the freeze, never places an order, never sizes.

Causal separation is hard: features come from bars with close<=decision_ts (the freeze); labels come
from bars with open>=decision_ts (this module). The decision-straddling bar belongs to neither.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import time
from decimal import Decimal as D

HERE = os.path.dirname(os.path.abspath(__file__))
EVDIR = os.path.dirname(HERE)
FA = os.path.dirname(EVDIR)
for p in (HERE, EVDIR, FA):
    if p not in sys.path:
        sys.path.insert(0, p)

UNKNOWN = "UNKNOWN"
PIP = D("0.10")                          # XAUUSD research convention (DR-301); NOT a broker claim
OUTCOME_CONTRACT_VERSION = "outcome_contract_v0_1"
EVALUATOR_VERSION = "outcome_evaluator_v0_1"
ROUTER_OUTCOMES = os.path.join(EVDIR, "router_outcomes_v0_1.jsonl")                       # GENUINE only
ROUTER_OUTCOMES_BACKFILL = os.path.join(EVDIR, "router_outcomes_backfill_v0_1.jsonl")     # backfill/fixture/etc
ROUTER_OUTCOMES_INTEGRATION = os.path.join(EVDIR, "router_outcomes_integration_test_v0_1.jsonl")


def ledger_for_class(record_class):
    """Route outcomes by record class so the GENUINE outcome ledger never receives a
    non-genuine record. Genuine-prospective -> genuine ledger; synthetic -> integration ledger;
    everything else (backfill/fixture/straddle/replay/untouched-window) -> backfill ledger."""
    n = normalize_class(record_class)
    if n == "GENUINE_PROSPECTIVE":
        return ROUTER_OUTCOMES
    if n == "SYNTHETIC_INTEGRATION_TEST":
        return ROUTER_OUTCOMES_INTEGRATION
    return ROUTER_OUTCOMES_BACKFILL

# the live strategy_router (frozen, watcher-loaded) emits "PROSPECTIVE"; the work order's canonical
# name is "GENUINE_PROSPECTIVE". They are SYNONYMS. We normalize here rather than modify the live module.
GENUINE_CLASSES = {"PROSPECTIVE", "GENUINE_PROSPECTIVE"}
TRAINABLE_CLASS = "GENUINE_PROSPECTIVE"


def normalize_class(rc):
    return "GENUINE_PROSPECTIVE" if rc in GENUINE_CLASSES else rc


def _sha(s):
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def outcome_idempotency_key(freeze, observation_cutoff):
    return _sha(f"{freeze['setup_id']}|{freeze['logical_hash']}|{observation_cutoff}|{OUTCOME_CONTRACT_VERSION}")


def _zone(freeze):
    zl, _, zh = freeze["zone"].partition("-")
    return D(zl), D(zh)


def _first_touch(post, level, side):
    """first bar index touching `level`. side 'ge' = high>=level; 'le' = low<=level."""
    for i, b in enumerate(post):
        if side == "ge" and b[2] >= level:
            return i
        if side == "le" and b[3] <= level:
            return i
    return None


def compute_labels(freeze, bars, observation_cutoff, target=None):
    """Deterministic RESEARCH-MARKET labels from bars strictly AFTER the decision. target optional;
    when absent, target-first labels stay UNKNOWN (never invented)."""
    decision_ts = int(freeze["hash_envelope"]["decision_timestamp"])
    direction = freeze["direction"]
    zl, zh = _zone(freeze)
    stop = D(str(freeze["hash_envelope"]["normalized_proposal"]["posted_stop"]))
    entry_ref = zh if direction == "LONG" else zl          # near edge of the posted zone
    # labels: bars whose OPEN is at/after the decision (excludes the straddling bar); within cutoff
    post = [b for b in bars if b[0] >= decision_ts and b[0] + 60 <= observation_cutoff]
    # data-integrity: sorted + no duplicate ts in the label window
    ts = [b[0] for b in post]
    data_integrity = "PASS" if ts == sorted(ts) and len(ts) == len(set(ts)) else "DATA_INTEGRITY_FAILURE"
    # causal-integrity: the freeze must attest its features closed at/before the decision
    lb_close = freeze["hash_envelope"].get("market_data_cutoff_timestamp")
    caus_close = freeze["causality"].get("latest_source_bar_close_time")
    causal_integrity = "PASS" if (isinstance(caus_close, int) and caus_close <= decision_ts) else "CAUSAL_INTEGRITY_FAILURE"

    if not post:
        return {"outcome_status": "INCOMPLETE_DATA", "activation_result": "NO_POST_DECISION_BARS",
                "causal_integrity": causal_integrity, "data_integrity": data_integrity,
                "intrabar_ambiguous": False}

    # activation = first bar touching the zone [zl, zh]
    act_i = next((i for i, b in enumerate(post) if b[3] <= zh and b[2] >= zl), None)
    if act_i is None:
        return {"outcome_status": "COMPLETE", "activation_result": "NEVER_ACTIVATED",
                "no_trade_result": "CANDIDATE_NEVER_ACTIVATED", "activation_time": None,
                "mfe_pips": None, "mae_pips": None, "stop_first": None, "target_first": None,
                "causal_integrity": causal_integrity, "data_integrity": data_integrity,
                "intrabar_ambiguous": False}

    seg = post[act_i:]
    act_ts = seg[0][0]
    hi = max(b[2] for b in seg)
    lo = min(b[3] for b in seg)
    if direction == "LONG":
        mfe = (hi - entry_ref) / PIP
        mae = (entry_ref - lo) / PIP
        mfe_price, mae_price = hi, lo
        stop_i = _first_touch(seg, stop, "le")
        tgt_i = _first_touch(seg, D(str(target)), "ge") if target is not None else None
    else:
        mfe = (entry_ref - lo) / PIP
        mae = (hi - entry_ref) / PIP
        mfe_price, mae_price = lo, hi
        stop_i = _first_touch(seg, stop, "ge")
        tgt_i = _first_touch(seg, D(str(target)), "le") if target is not None else None

    intrabar = False
    stop_first = target_first = None
    ordering = "UNKNOWN"
    alt = None
    if target is None:
        ordering = "TARGET_UNKNOWN_NOT_PROVIDED"
    elif stop_i is not None and tgt_i is not None:
        if stop_i == tgt_i:
            # both touched in the SAME bar -> ambiguous; never choose the profitable order
            intrabar = True
            ordering = "AMBIGUOUS_INTRABAR_ORDER"
            alt = {"pessimistic_case": "STOP_FIRST", "optimistic_case": "TARGET_FIRST", "ordering_unknown": True}
        elif stop_i < tgt_i:
            stop_first, ordering = True, "STOP_FIRST"
        else:
            target_first, ordering = True, "TARGET_FIRST"
    elif stop_i is not None:
        stop_first, ordering = True, "STOP_ONLY"
    elif tgt_i is not None:
        target_first, ordering = True, "TARGET_ONLY"
    else:
        ordering = "NEITHER_STOP_NOR_TARGET_REACHED"

    status = "AMBIGUOUS_INTRABAR_ORDER" if intrabar else "COMPLETE"
    if causal_integrity != "PASS":
        status = "CAUSAL_INTEGRITY_FAILURE"
    elif data_integrity != "PASS":
        status = "DATA_INTEGRITY_FAILURE"
    return {"outcome_status": status, "activation_result": "ACTIVATED", "activation_time": act_ts,
            "time_to_activation_s": act_ts - decision_ts,
            "mfe_pips": str(mfe.quantize(D("0.01"))), "mae_pips": str(mae.quantize(D("0.01"))),
            "mfe_price": str(mfe_price), "mae_price": str(mae_price),
            "stop_first": stop_first, "target_first": target_first, "stop_target_ordering": ordering,
            "intrabar_ambiguous": intrabar, "intrabar_alternatives": alt,
            "definitive_training_label_withheld": intrabar,
            "causal_integrity": causal_integrity, "data_integrity": data_integrity,
            "price_result_class": "RESEARCH_MARKET_RESULT (TV semantics unverified; broker equivalence unproven)"}


def lane_comparison(freeze, labels):
    """Descriptive, NON-MUTATING Lane A/B/C comparison. Never rewrites a lane, never fits weights,
    never declares a lane superior on one campaign."""
    ote = freeze["supplemental_contracts"]["ote_shadow"]
    return {
        "lane_A_posted_follower": {"zone": freeze["zone"], "activation": labels.get("activation_result"),
                                   "ordering": labels.get("stop_target_ordering"), "mfe_pips": labels.get("mfe_pips"),
                                   "mae_pips": labels.get("mae_pips"), "semantics": "FROZEN_AND_KNOWN (not rewritten)"},
        "lane_B_enhanced": {"ote_anchor_pairs": ote.get("total_pairs_enumerated"),
                            "note": "OTE candidates DISABLED shadow; not selected; no per-campaign superiority claim"},
        "lane_C_independent": {"note": "router independent representation; blind hypothesis in a separate ledger; not evaluated here"},
        "superiority_claim": "NONE (single campaign; descriptive only)",
        "weights_fitted": False, "lane_A_governance_modified": False,
    }


def copy_fidelity_telemetry(freeze):
    """How faithfully/quickly Orange processed the instruction. Unavailable timestamps stay
    NOT_AVAILABLE — never fabricated. Any price-drift metric is research-only."""
    env = freeze["hash_envelope"]
    raw = env.get("raw_source_ref") or {}
    return {
        "telemetry_contract_version": "copy_fidelity_telemetry_v0_1",
        "source_message_utc": (raw.get("source_message_utc") if isinstance(raw, dict) else "NOT_AVAILABLE"),
        "router_freeze_decision_ts": env.get("decision_timestamp"),
        "market_data_cutoff_ts": env.get("market_data_cutoff_timestamp"),
        "activation_ts_reference": env.get("activation_timestamp"),
        "pretrade_logical_hash": (raw.get("pretrade_logical_hash") if isinstance(raw, dict) else "NOT_AVAILABLE"),
        "message_to_capture_latency": "NOT_MEASURED", "capture_to_normalization_latency": "NOT_MEASURED",
        "normalization_to_freeze_latency": "NOT_MEASURED", "total_source_to_freeze_latency": "NOT_MEASURED",
        "duplicate_message_count": "NOT_AVAILABLE", "parser_fallback_used": "NOT_AVAILABLE",
        "human_intervention_required": "NOT_AVAILABLE",
        "quoted_vs_observed_price_drift": "RESEARCH_ONLY / UNVERIFIED (TV vs broker price equivalence unproven)",
        "proposal_after_zone_touched": "NOT_MEASURED", "stale_proposal_classification": "NOT_MEASURED",
    }


def _existing(ledger):
    out = []
    if os.path.exists(ledger):
        for line in open(ledger, encoding="utf-8"):
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return out


def attach_outcome(freeze, bars, observation_cutoff, target=None, ledger_path=None,
                   source_provenance=None):
    """Attach ONE outcome to an immutable freeze. Idempotent by key. Append-only. Returns the record
    (existing one if already attached; a CONTRADICTION record if a same-key non-deterministic conflict
    is somehow observed). NEVER modifies the freeze. When ledger_path is None the outcome is ROUTED by
    the freeze's record class so a non-genuine record can never land in the genuine ledger."""
    if ledger_path is None:
        ledger_path = ledger_for_class(freeze.get("record_class"))
    key = outcome_idempotency_key(freeze, observation_cutoff)
    existing = _existing(ledger_path)
    labels = compute_labels(freeze, bars, observation_cutoff, target=target)
    prov = source_provenance or ("VERIFIED" if (normalize_class(freeze.get("record_class")) == TRAINABLE_CLASS
                                                and isinstance(freeze["hash_envelope"].get("raw_source_ref"), dict))
                                 else "UNVERIFIED")
    for r in existing:
        if r.get("idempotency_key") == key and r.get("record_type") == "ROUTER_OUTCOME":
            # idempotent: same inputs -> if labels differ, it's non-determinism -> CONTRADICTION event
            if r.get("labels", {}).get("outcome_status") != labels["outcome_status"]:
                contradiction = _finalize({"record_type": "OUTCOME_CONTRADICTION", "of_idempotency_key": key,
                                           "campaign_id": freeze["setup_id"], "prior_status": r["labels"]["outcome_status"],
                                           "new_status": labels["outcome_status"], "note": "non-deterministic conflict"})
                _append(ledger_path, contradiction)
                return contradiction
            return r                                          # already attached, unchanged
    # revision linkage: a later cutoff for the same (campaign, freeze) references the prior newest
    prior = [r for r in existing if r.get("record_type") == "ROUTER_OUTCOME"
             and r.get("freeze_hash") == freeze["logical_hash"]]
    revision_of = (prior[-1]["idempotency_key"] if prior else None)
    rec = _finalize({
        "record_type": "ROUTER_OUTCOME", "outcome_contract_version": OUTCOME_CONTRACT_VERSION,
        "evaluator_version": EVALUATOR_VERSION, "campaign_id": freeze["setup_id"],
        "freeze_id": freeze["logical_hash"], "freeze_hash": freeze["logical_hash"],
        "source_event_hash": (freeze["hash_envelope"].get("raw_source_ref") or UNKNOWN),
        "decision_timestamp": freeze["hash_envelope"]["decision_timestamp"],
        "market_data_cutoff_timestamp": freeze["hash_envelope"]["market_data_cutoff_timestamp"],
        "router_version": freeze["router_version"],
        "outcome_observation_cutoff": observation_cutoff,
        "outcome_contract": OUTCOME_CONTRACT_VERSION,
        "record_class": freeze.get("record_class"),
        "record_provenance": {"freeze_record_class": freeze.get("record_class"),
                              "source_provenance": prov, "revision_of": revision_of},
        "labels": labels, "lane_comparison": lane_comparison(freeze, labels),
        "copy_fidelity": copy_fidelity_telemetry(freeze),
        "eligibility": _eligibility(freeze, labels, prov),
        "idempotency_key": key,
    })
    _append(ledger_path, rec)
    return rec


def _eligibility(freeze, labels, prov):
    rc = normalize_class(freeze.get("record_class"))
    reasons = []
    trainable = True
    if rc != TRAINABLE_CLASS:
        trainable = False; reasons.append(f"record_class={rc}")
    if not freeze.get("eligible_for_prospective_evidence"):
        trainable = False; reasons.append("not prospective-eligible")
    if labels.get("outcome_status") != "COMPLETE":
        trainable = False; reasons.append(f"outcome_status={labels.get('outcome_status')}")
    if labels.get("causal_integrity") != "PASS":
        trainable = False; reasons.append("causal_integrity!=PASS")
    if labels.get("data_integrity") != "PASS":
        trainable = False; reasons.append("data_integrity!=PASS")
    if prov != "VERIFIED":
        trainable = False; reasons.append("source_provenance!=VERIFIED")
    return {"eligible_for_prospective_evidence": bool(freeze.get("eligible_for_prospective_evidence")),
            "eligible_for_training": trainable, "eligible_for_validation": trainable,
            "eligible_for_performance_attribution": bool(freeze.get("eligible_for_performance_attribution")) and labels.get("outcome_status") == "COMPLETE",
            "exclusion_reasons": reasons}


def _finalize(rec):
    # stamps must be added BEFORE hashing so the hash covers them; only logical_hash and the volatile
    # attachment timestamp are excluded from the hashed core (deterministic + reproducible).
    rec["review_only"] = True
    rec["executable"] = False
    rec["trade_ready"] = False
    rec["observation_only"] = True
    rec["outcome_attachment_timestamp"] = int(time.time())
    core = {k: v for k, v in rec.items() if k not in ("logical_hash", "outcome_attachment_timestamp")}
    rec["logical_hash"] = _sha(json.dumps(core, sort_keys=True, default=str))
    return rec


def _append(ledger_path, rec):
    with open(ledger_path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, default=str) + "\n")
