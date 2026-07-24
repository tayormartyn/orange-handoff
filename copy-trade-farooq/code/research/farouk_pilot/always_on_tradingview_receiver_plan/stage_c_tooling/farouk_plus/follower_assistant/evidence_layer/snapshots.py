"""PRE_TRADE_SNAPSHOT, BLIND_HYPOTHESIS, MANAGEMENT_SNAPSHOT, latency/actionability (Parts 1-4).

All records are additive, append-only, idempotent, firewall-guarded. They NEVER modify the
strict follower proposal or any frozen outcome — they are separate research evidence.
"""
from __future__ import annotations

from decimal import Decimal as D

import evidence_schema as es
import smc_features as smc

UNKNOWN = es.UNKNOWN


def _pips(usd):
    return str((D(str(usd)) * D("10")).quantize(D("0.01")))


# ---- PART 1: PRE_TRADE_SNAPSHOT --------------------------------------------------------------
def build_pre_trade_snapshot(*, setup_id, direction, zone_low, zone_high, sl,
                             source_ts, receipt_ts, proposal_ts, market_ts, current_price,
                             incomplete_bar_status, bars, competing_zones=None,
                             indicator_events=None):
    """Immutable snapshot BEFORE any outcome/video. Causal features only. Firewall must be OPEN."""
    es.assert_firewall_open(setup_id, "PRE_TRADE_SNAPSHOT")
    signal_ts = int(source_ts) if isinstance(source_ts, int) else _iso_epoch(source_ts)
    price = current_price if current_price is not None else UNKNOWN
    dist = UNKNOWN
    if price != UNKNOWN:
        near = D(str(zone_high)) if direction == "LONG" else D(str(zone_low))
        dist = _pips((D(str(price)) - near) * (D(1) if direction == "LONG" else D(-1)))
    feats = smc.derive_all(bars, signal_ts, zone_low, zone_high, price)
    rec = {
        "record_type": "PRE_TRADE_SNAPSHOT", "setup_id": setup_id,
        "direction": direction, "zone": f"{zone_low}-{zone_high}", "posted_stop": str(sl),
        "timestamps": {"source_message_utc": source_ts, "telegram_receipt_utc": receipt_ts,
                       "proposal_emission_utc": proposal_ts, "current_market_utc": market_ts,
                       "evidence_commit_note": "commit ts added at write"},
        "current_xauusd_price": str(price) if price != UNKNOWN else UNKNOWN,
        "distance_to_near_edge_pips": dist,
        "price_vs_zone": feats["zone_relation"],
        "incomplete_bar_status": incomplete_bar_status or UNKNOWN,
        "causal_features": feats,
        "indicator_events_available": indicator_events or UNKNOWN,
        "competing_plausible_zones": competing_zones or UNKNOWN,
        "unavailable_features": [k for k, v in feats.items() if v == UNKNOWN],
        "firewall_state_at_commit": "OPEN",
        "leakage_guarantee": "no bar with ts >= source_message_utc used in any feature",
    }
    rec["evidence_commit_ts"] = market_ts
    return es.finalize(rec)


# ---- PART 2: BLIND_HYPOTHESIS ----------------------------------------------------------------
def build_blind_hypothesis(*, setup_id, expected_direction, strongest_zone, invalidation,
                           structural_rationale, confidence, alternative_hypothesis, unknowns,
                           authored_ts, snapshot_hash=None, methodology_version=None,
                           generator="MANUAL", extra=None):
    """Orange's own read, committed BEFORE outcome/video. Research-only; cannot touch strict lane."""
    es.assert_firewall_open(setup_id, "BLIND_HYPOTHESIS")
    rec = {
        "record_type": "BLIND_HYPOTHESIS", "setup_id": setup_id,
        "expected_direction": expected_direction, "strongest_candidate_zone": strongest_zone,
        "invalidation": invalidation, "structural_rationale": structural_rationale,
        "confidence": confidence, "alternative_hypothesis": alternative_hypothesis,
        "unknowns": unknowns or [UNKNOWN],
        "snapshot_hash": snapshot_hash or UNKNOWN,
        "methodology_version": methodology_version or UNKNOWN, "generator": generator,
        "authored_at_utc": authored_ts, "firewall_state_at_commit": "OPEN",
        "binding_note": "research-only; does NOT modify the strict follower proposal, entries, "
                        "stops, campaign state, arithmetic, outcomes, or the Enhanced Entry lane",
    }
    if extra:
        rec.update(extra)
    rec["evidence_commit_ts"] = authored_ts
    return es.finalize(rec)


# ---- PART 3: MANAGEMENT_SNAPSHOT -------------------------------------------------------------
def build_management_snapshot(*, setup_id, message_id, source_ts, receipt_ts, current_price,
                              instruction_interpretation, lane_state_with, lane_state_without):
    """Frozen at each management message. No retroactive mutation: this is a NEW append."""
    e = lane_state_with
    rec = {
        "record_type": "MANAGEMENT_SNAPSHOT", "setup_id": setup_id, "message_id": message_id,
        "timestamps": {"source_message_utc": source_ts, "telegram_receipt_utc": receipt_ts},
        "current_xauusd_price": str(current_price) if current_price is not None else UNKNOWN,
        "filled_legs": e.get("filled_legs", UNKNOWN),
        "average_entry": e.get("average_entry", UNKNOWN),
        "mae_pips": e.get("mae_pips", UNKNOWN), "mfe_pips": e.get("mfe_pips", UNKNOWN),
        "distance_to_stop_pips": e.get("distance_to_stop_pips", UNKNOWN),
        "distance_to_be_pips": e.get("distance_to_be_pips", UNKNOWN),
        "open_size_fraction": e.get("open_size_fraction", UNKNOWN),  # unit fraction, never lots
        "unfilled_legs": e.get("unfilled_legs", UNKNOWN),
        "applicable_instruction_interpretation": instruction_interpretation,
        "counterfactual_if_ignored": lane_state_without,
        "no_retroactive_mutation": True,
    }
    rec["evidence_commit_ts"] = receipt_ts
    return es.finalize(rec)


# ---- PART 4: LATENCY & ACTIONABILITY ---------------------------------------------------------
def latency_actionability(*, source_ts, receipt_ts, proposal_ts, first_zone_touch_ts,
                          first_fill_ts, first_management_ts, price_at_receipt, price_at_proposal,
                          price_vs_zone_at_proposal, source_precision="SECONDS"):
    """Deterministic latency metrics. Never invents sub-second precision it doesn't have."""
    def delta(a, b):
        if a in (None, UNKNOWN) or b in (None, UNKNOWN):
            return UNKNOWN
        return _iso_epoch(b) - _iso_epoch(a)
    src_to_receipt = delta(source_ts, receipt_ts) if source_precision != "UNKNOWN" else UNKNOWN
    move = UNKNOWN
    if price_at_receipt not in (None, UNKNOWN) and price_at_proposal not in (None, UNKNOWN):
        move = _pips(D(str(price_at_proposal)) - D(str(price_at_receipt)))
    had_time_all3 = UNKNOWN
    if first_zone_touch_ts not in (None, UNKNOWN) and proposal_ts not in (None, UNKNOWN):
        gap = _iso_epoch(first_zone_touch_ts) - _iso_epoch(proposal_ts)
        had_time_all3 = gap >= 60 and price_vs_zone_at_proposal != "INSIDE" and price_vs_zone_at_proposal != "THROUGH"
    return {
        "record_type": "LATENCY_ACTIONABILITY",
        "source_to_receipt_seconds": src_to_receipt,
        "source_timestamp_precision": source_precision,
        "receipt_to_proposal_seconds": delta(receipt_ts, proposal_ts),
        "price_move_during_processing_pips": move,
        "proposal_to_first_zone_touch_seconds": delta(proposal_ts, first_zone_touch_ts),
        "time_to_first_fill_seconds": delta(source_ts, first_fill_ts),
        "time_to_first_management_seconds": delta(source_ts, first_management_ts),
        "price_already_inside_or_through_at_proposal": price_vs_zone_at_proposal in ("INSIDE", "THROUGH"),
        "follower_had_time_to_arm_all_three": had_time_all3,
        "precision_note": "no millisecond precision invented; TradingView/Telegram give second-level",
    }


def build_hypothesis_terminal(*, setup_id, committed_ref, missing_features, attempted_ts,
                              firewall_state, follower_continued):
    """Resolved at firewall closure. EXACTLY ONE terminal per campaign: either a reference to a
    BLIND_HYPOTHESIS that was committed before outcome, or an explicit HYPOTHESIS_NOT_GENERATED.
    Failure to generate a hypothesis NEVER blocks the follower (a separate process)."""
    if committed_ref:
        rec = {"record_type": "HYPOTHESIS_TERMINAL", "setup_id": setup_id,
               "state": "BLIND_HYPOTHESIS_COMMITTED", "blind_hypothesis_ref": committed_ref,
               "firewall_state_at_resolution": firewall_state}
    else:
        rec = {"record_type": "HYPOTHESIS_TERMINAL", "setup_id": setup_id,
               "state": "HYPOTHESIS_NOT_GENERATED",
               "reason": "no BLIND_HYPOTHESIS was committed before outcome/video contamination",
               "missing_features": missing_features or [UNKNOWN],
               "attempted_at_utc": attempted_ts or UNKNOWN,
               "firewall_state_at_resolution": firewall_state,
               "follower_campaign_continued_normally": follower_continued}
    rec["evidence_commit_ts"] = attempted_ts or 0
    return es.finalize(rec)


def _iso_epoch(x):
    if isinstance(x, int):
        return x
    from datetime import datetime
    return int(datetime.fromisoformat(str(x).replace("Z", "+00:00")).timestamp())
