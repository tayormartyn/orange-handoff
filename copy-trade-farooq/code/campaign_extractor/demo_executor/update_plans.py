"""
TRADE_UPDATE management-plan orchestrator (DRY-RUN). confirmed TRADE_UPDATE -> parse intents ->
link to parent signal -> reconcile/match broker position (never symbol alone; ambiguous blocked) ->
build management actions (breakeven/partial-close/composite) -> DEMO TRADE UPDATE card. Records the
append-only lifecycle. NOTHING modifies or closes a position; approval ends
UPDATE_PLAN_DRY_RUN_APPROVED / NO_BROKER_ACTION_SENT.
"""
from __future__ import annotations
import hashlib

import config as CFG
import update_parser
import position_matcher
import management_planner as MP

_PLANS = {}


def make_plan_id(signal_id, version, account_id, update_ref):
    raw = f"{signal_id}|u{version}|{account_id}|{update_ref}"
    return "mgmtplan-" + hashlib.sha256(raw.encode()).hexdigest()[:16]


def build_update_plan(*, signal_id, source_class, confirmed, provider_verified, update_text,
                      update_ts_ms, account, account_type, symbol_digits, point,
                      min_stop_distance_points, positions, orders=None, quote, now_ms,
                      units_per_lot, min_volume_units, step_volume_units, contract_oz_per_lot=100.0,
                      fx=1.0, requested_fraction=None, provider_wording="", version=1, update_ref="u1",
                      audit=None):
    pid = make_plan_id(signal_id, version, account.account_id, update_ref)
    if audit is not None:
        audit.record("UPDATE_RECEIVED", pid, {"signal_id": signal_id})

    def reject(reason, extra=None):
        card = {"banner": "DEMO TRADE UPDATE — NO ACTION SENT", "valid": False, "reason": reason,
                "parent_signal_id": signal_id, "account_type": account_type, **(extra or {})}
        _PLANS[pid] = {"plan_id": pid, "status": "MANAGEMENT_PLAN_REJECTED", "card": card, "valid": False}
        if audit is not None:
            audit.record("MANAGEMENT_PLAN_CREATED", pid, {})
            audit.record("MANAGEMENT_PLAN_REJECTED", pid, {"reason": reason})
        return _PLANS[pid]

    # class / confirmation gates: TRADE_RESULT and OCR-alone can NEVER modify a position
    if source_class == "TRADE_RESULT":
        return reject("TRADE_RESULT_CANNOT_MODIFY_POSITION")
    if source_class != "TRADE_UPDATE":
        return reject(f"NOT_A_TRADE_UPDATE:{source_class}")
    if not confirmed:
        return reject("NOT_HUMAN_CONFIRMED")
    if (now_ms - quote.ts_ms) > CFG.QUOTE_STALE_MS:
        return reject("STALE_QUOTE")
    if update_ts_ms is not None and (now_ms - update_ts_ms) > CFG.SIGNAL_STALE_SECONDS * 1000:
        return reject("STALE_UPDATE")

    parsed = update_parser.parse_update(update_text)
    if audit is not None:
        audit.record("UPDATE_LINKED_TO_SIGNAL", pid, {"primary": parsed["primary"]})

    match = position_matcher.match_position(signal_id=signal_id, account_id=account.account_id,
                                            symbol="XAUUSD", direction=_dir_of(positions, signal_id),
                                            positions=positions, orders=orders, now_ms=now_ms)
    if audit is not None:
        audit.record("POSITION_MATCH_PROPOSED", pid, {"status": match.status})
    if match.status in ("NO_MATCH", "AMBIGUOUS"):
        return reject("POSITION_MATCH_" + match.status,
                      {"match": {"status": match.status, "reason": match.reason,
                                 "candidates": [getattr(c, "position_id", None) for c in match.candidates]}})
    matched = match.matched
    if match.status == "MULTI_LEG":
        matched = None                                # worst/best handled per-intent below

    if audit is not None and matched is not None:
        audit.record("POSITION_MATCH_CONFIRMED", pid, {"position_id": matched.position_id})

    actions = []
    for it in parsed["intents"]:
        intent = it["intent"]
        if intent == "MOVE_SL_TO_BREAKEVEN" and matched is not None:
            actions.append(MP.breakeven_proposal(matched, quote=quote, symbol_digits=symbol_digits,
                                                 point=point, min_stop_distance_points=min_stop_distance_points))
        elif intent == "PARTIAL_CLOSE" and matched is not None:
            actions.append(MP.partial_close_proposal(
                matched, min_volume_units=min_volume_units, step_volume_units=step_volume_units,
                units_per_lot=units_per_lot, quote=quote, contract_oz_per_lot=contract_oz_per_lot, fx=fx,
                requested_fraction=requested_fraction, provider_literal_lots=parsed["provider_literal_lots"],
                provider_wording=provider_wording))
        elif intent == "CLOSE_WORST_LEG":
            sel = position_matcher.close_worst_leg_selection(match.candidates, _dir_of(positions, signal_id),
                                                             account_type)
            from models import PlanAction
            actions.append(PlanAction("CLOSE_WORST_LEG", sel["status"] == "IDENTIFIED",
                                      "OK" if sel["status"] == "IDENTIFIED" else "AMBIGUOUS", sel))
        else:
            from models import PlanAction
            actions.append(PlanAction(intent, False, "NO_ACTION_BUILT_THIS_PHASE", {"intent": intent}))

    composite = MP.composite_plan(actions) if len(actions) > 1 else None
    valid = bool(matched is not None and actions and all(a.ok for a in actions)
                 and account.environment == "DEMO" and not account.is_live
                 and account.account_id in CFG.DEMO_ALLOWLIST_ACCOUNT_IDS)

    card = {
        "banner": "DEMO TRADE UPDATE — NO ACTION SENT",
        "update_text": update_text, "update_ts_ms": update_ts_ms, "provider_verified": provider_verified,
        "parent_signal_id": signal_id, "account": account.masked(), "account_type": account_type,
        "matched_position_id": (matched.position_id if matched else None),
        "instrument": "XAUUSD", "direction": (matched.direction if matched else _dir_of(positions, signal_id)),
        "actual_vwap_entry": (matched.price if matched else None),
        "current_bid": quote.bid, "current_ask": quote.ask,
        "current_sl": (matched.stop_loss if matched else None),
        "current_tp": (matched.take_profit if matched else None),
        "open_volume_units": (matched.volume_units if matched else None),
        "parsed_primary": parsed["primary"], "parsed_intents": parsed["intents"],
        "actions": [{"action_type": a.action_type, "ok": a.ok, "reason": a.reason, "detail": a.detail} for a in actions],
        "composite_plan": composite, "quote_age_ms": now_ms - quote.ts_ms,
        "update_age_ms": (now_ms - update_ts_ms) if update_ts_ms else None,
        "match": {"status": match.status, "reason": match.reason, "keys": match.match_keys},
        "valid_for_arming": valid,
        "phase_notice": "DRY-RUN ONLY — NO_BROKER_ACTION_SENT; ProtoOAAmendPositionSLTP / ClosePosition NOT enabled",
    }
    _PLANS[pid] = {"plan_id": pid, "status": "MANAGEMENT_PLAN_VALIDATED" if valid else "MANAGEMENT_PLAN_REJECTED",
                   "card": card, "valid": valid, "created_at_ms": now_ms}
    if audit is not None:
        audit.record("MANAGEMENT_PLAN_CREATED", pid, {})
        audit.record("MANAGEMENT_PLAN_VALIDATED" if valid else "MANAGEMENT_PLAN_REJECTED", pid, {"valid": valid})
    return _PLANS[pid]


def build_ocr_update_plan(*, signal_id, source_class, confirmed, provider_verified, ocr_text,
                          update_ts_ms, account, account_type, symbol_digits, pip_position, positions,
                          quote, now_ms, units_per_lot, lot_size_raw, min_volume_units, step_volume_units,
                          fx=1.0, operator_policy_fraction=0.5, version=1, update_ref="ocr1", audit=None,
                          mock_ui=False):
    pid = make_plan_id(signal_id, version, account.account_id, update_ref)
    if audit is not None:
        audit.record("UPDATE_RECEIVED", pid, {"signal_id": signal_id})

    def reject(reason, extra=None):
        card = {"banner": "DEMO TRADE UPDATE — NO ACTION SENT", "valid_for_arming": False,
                "reason": reason, "parent_signal_id": signal_id, "account_type": account_type,
                "phase_notice": "DRY-RUN ONLY — NO_BROKER_ACTION_SENT", **(extra or {})}
        _PLANS[pid] = {"plan_id": pid, "status": "MANAGEMENT_PLAN_REJECTED", "card": card, "valid": False}
        if audit is not None:
            audit.record("MANAGEMENT_PLAN_CREATED", pid, {})
            audit.record("MANAGEMENT_PLAN_REJECTED", pid, {"reason": reason})
        return _PLANS[pid]

    if source_class == "TRADE_RESULT":
        return reject("TRADE_RESULT_CANNOT_MODIFY_POSITION")
    if source_class != "TRADE_UPDATE":
        return reject(f"NOT_A_TRADE_UPDATE:{source_class}")
    if not confirmed:
        return reject("NOT_HUMAN_CONFIRMED")
    if (now_ms - quote.ts_ms) > CFG.QUOTE_STALE_MS:
        return reject("STALE_QUOTE")
    if update_ts_ms is not None and (now_ms - update_ts_ms) > CFG.SIGNAL_STALE_SECONDS * 1000:
        return reject("STALE_UPDATE")

    ocr = update_parser.parse_ocr_update(ocr_text)
    if audit is not None:
        audit.record("UPDATE_LINKED_TO_SIGNAL", pid, {"intent": ocr["intent"]})
    # Rule 3: a price pair alone (no action language) must never propose a close
    if ocr["intent"] != "PARTIAL_CLOSE_CANDIDATE":
        return reject("NO_ACTION_LANGUAGE_PRICE_PAIR_ALONE",
                      {"raw_ocr_text": ocr["raw_text"], "normalized_candidate": ocr["normalized_candidate"],
                       "ambiguity_flags": ocr["ambiguity_flags"]})

    direction = _dir_of(positions, signal_id) or ("SELL" if (ocr["provider_leg_candidate"] or "").startswith("SELL") else None)
    match = position_matcher.match_position(signal_id=signal_id, account_id=account.account_id,
                                            symbol="XAUUSD", direction=direction, positions=positions,
                                            now_ms=now_ms)
    if audit is not None:
        audit.record("POSITION_MATCH_PROPOSED", pid, {"status": match.status})
    if match.status in ("NO_MATCH", "AMBIGUOUS"):        # Rule 2: needs an eligible linked position
        return reject("POSITION_MATCH_" + match.status,
                      {"raw_ocr_text": ocr["raw_text"], "normalized_candidate": ocr["normalized_candidate"],
                       "ambiguity_flags": ocr["ambiguity_flags"], "mock_ui": mock_ui,
                       "match": {"status": match.status, "reason": match.reason}})
    matched = match.matched
    if audit is not None and matched is not None:
        audit.record("POSITION_MATCH_CONFIRMED", pid, {"position_id": matched.position_id})

    action = MP.ocr_take_more_proposal(matched, ocr, min_volume_units=min_volume_units,
                                       step_volume_units=step_volume_units, units_per_lot=units_per_lot,
                                       lot_size_raw=lot_size_raw, quote=quote, pip_position=pip_position,
                                       fx=fx, operator_policy_fraction=operator_policy_fraction)
    valid = bool(matched is not None and action.ok and account.environment == "DEMO"
                 and not account.is_live and account.account_id in CFG.DEMO_ALLOWLIST_ACCOUNT_IDS)
    card = {"banner": "DEMO TRADE UPDATE — NO ACTION SENT", "parent_signal_id": signal_id,
            "account": account.masked(), "account_type": account_type,
            "matched_position_id": matched.position_id, "mock_ui": mock_ui,
            "instrument": "XAUUSD", "direction": matched.direction, "actual_vwap_entry": matched.price,
            "current_bid": quote.bid, "current_ask": quote.ask, "open_volume_units": matched.volume_units,
            "raw_ocr_text": ocr["raw_text"], "normalized_candidate": ocr["normalized_candidate"],
            "provider_leg_candidate": ocr["provider_leg_candidate"], "leg_mapping": "PROVIDER_LEG_NOT_YET_MAPPED",
            "instruction_vs_recap": ocr["instruction_vs_recap"], "ambiguity_flags": ocr["ambiguity_flags"],
            "action": action.detail, "quote_age_ms": now_ms - quote.ts_ms,
            "match": {"status": match.status, "keys": match.match_keys},
            "valid_for_arming": valid,
            "phase_notice": "DRY-RUN ONLY — NO_BROKER_ACTION_SENT; ProtoOAClosePosition NOT enabled"}
    _PLANS[pid] = {"plan_id": pid, "status": "MANAGEMENT_PLAN_VALIDATED" if valid else "MANAGEMENT_PLAN_REJECTED",
                   "card": card, "valid": valid, "created_at_ms": now_ms}
    if audit is not None:
        audit.record("MANAGEMENT_PLAN_CREATED", pid, {})
        audit.record("MANAGEMENT_PLAN_VALIDATED" if valid else "MANAGEMENT_PLAN_REJECTED", pid, {"valid": valid})
    return _PLANS[pid]


def _dir_of(positions, signal_id):
    for p in (positions or []):
        if signal_id and signal_id in (getattr(p, "label", "") or ""):
            return p.direction
    return (positions[0].direction if positions else None)


def arm_plan(plan_id, audit=None):
    p = _PLANS.get(plan_id)
    if not p or not p["valid"]:
        return {"armed": False, "reason": "NOT_VALIDATED"}
    p["status"] = "MANAGEMENT_PLAN_ARMED"
    if audit is not None:
        audit.record("MANAGEMENT_PLAN_ARMED", plan_id, {})
    return {"armed": True, "plan_id": plan_id}


def dry_run_approve(plan_id, *, now_ms=0, audit=None):
    p = _PLANS.get(plan_id)
    if not p:
        return {"result": "UNKNOWN_PLAN", "broker_action_sent": False, "reason": "NO_BROKER_ACTION_SENT"}
    if (now_ms - p.get("created_at_ms", now_ms)) > CFG.PROPOSAL_TTL_SECONDS * 1000:
        p["status"] = "MANAGEMENT_PLAN_EXPIRED"
        if audit is not None:
            audit.record("MANAGEMENT_PLAN_EXPIRED", plan_id, {})
        return {"result": "MANAGEMENT_PLAN_EXPIRED", "broker_action_sent": False, "reason": "NO_BROKER_ACTION_SENT"}
    if p["status"] != "MANAGEMENT_PLAN_ARMED":
        return {"result": "NOT_ARMED", "broker_action_sent": False, "reason": "NO_BROKER_ACTION_SENT"}
    if audit is not None:
        audit.record("UPDATE_PLAN_DRY_RUN_APPROVED", plan_id, {})
    return {"result": "UPDATE_PLAN_DRY_RUN_APPROVED", "broker_action_sent": False, "reason": "NO_BROKER_ACTION_SENT"}
