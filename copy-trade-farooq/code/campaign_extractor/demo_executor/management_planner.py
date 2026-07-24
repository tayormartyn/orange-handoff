"""
DRY-RUN management-plan builders. Breakeven uses the broker position VWAP (ProtoOAPosition.price),
NOT the signal entry. Partial close works in broker protocol units, rounds down to a valid step, and
NEVER blindly maps a provider's absolute lot instruction onto our differently-sized position. Nothing
here modifies or closes a position; it produces proposal cards only.
"""
from __future__ import annotations
import math

from models import PlanAction


def _round_down(v, step):
    return math.floor(round(v / step, 9)) * step if step > 0 else v


def breakeven_proposal(position, *, quote, symbol_digits, point, min_stop_distance_points):
    d = str(position.direction).upper()
    proposed_stop = round(position.price, symbol_digits)          # exact broker VWAP, digits-rounded only
    market_side = quote.ask if d == "SELL" else quote.bid         # side the stop would be measured against
    distance = abs(proposed_stop - market_side)
    dist_points = distance / point
    ok = dist_points >= min_stop_distance_points
    card = {
        "action_type": "AMEND_STOP_LOSS", "label": "ENTRY-PRICE BREAKEVEN",
        "note": "TRADING COSTS MAY STILL PRODUCE A SMALL NET LOSS",
        "broker_position_id": position.position_id, "actual_vwap_entry": position.price,
        "current_stop": position.stop_loss, "proposed_stop": proposed_stop,
        "current_bid": quote.bid, "current_ask": quote.ask,
        "distance_from_market": round(distance, symbol_digits), "distance_points": round(dist_points, 1),
        "broker_min_distance_ok": ok,
        "remaining_risk_after_amendment": "ENTRY_PRICE_BREAKEVEN (no buffer added; costs may net small loss)",
        "no_silent_buffer": True}
    return PlanAction("AMEND_STOP_LOSS", ok, "OK" if ok else "MIN_DISTANCE_VIOLATION", card)


def partial_close_proposal(position, *, min_volume_units, step_volume_units, units_per_lot, quote,
                           contract_oz_per_lot=100.0, fx=1.0, requested_fraction=None,
                           provider_literal_lots=None, provider_wording=""):
    open_units = float(position.volume_units)
    open_lots = round(open_units / units_per_lot, 4)
    if open_units <= 0:
        return PlanAction("PARTIAL_CLOSE", False, "POSITION_NOT_OPEN", {})

    def est_pnl(close_units):
        oz_per_unit = contract_oz_per_lot / units_per_lot
        mkt = quote.bid if str(position.direction).upper() == "SELL" else quote.ask
        sign = 1 if str(position.direction).upper() == "SELL" else -1
        return round((position.price - mkt) * sign * close_units * oz_per_unit * fx, 2)

    base = {"action_type": "PARTIAL_CLOSE", "broker_position_id": position.position_id,
            "open_volume_units": open_units, "open_volume_lots": open_lots,
            "provider_wording": provider_wording, "min_volume_units": min_volume_units,
            "step_volume_units": step_volume_units}

    # provider absolute-lot instruction that does NOT equal our position -> unmapped, operator must choose
    if provider_literal_lots is not None:
        literal_units = provider_literal_lots * units_per_lot
        if abs(literal_units - open_units) > (step_volume_units / 2):
            steps = int(round(open_units / step_volume_units))
            choices = [{"close_units": round(i * step_volume_units, 4),
                        "close_lots": round(i * step_volume_units / units_per_lot, 4),
                        "remaining_lots": round((open_units - i * step_volume_units) / units_per_lot, 4)}
                       for i in range(1, steps + 1)]
            card = {**base, "PROVIDER_LITERAL_VOLUME": f"{provider_literal_lots:.2f} LOT",
                    "mapping": "UNMAPPED_TO_OUR_POSITION", "requirement": "OPERATOR SELECTION REQUIRED",
                    "operator_choices": choices,
                    "note": "provider absolute lot != our risk-sized volume; no automatic choice"}
            return PlanAction("PARTIAL_CLOSE", False, "PROVIDER_LITERAL_UNMAPPED", card)

    if requested_fraction is None:
        # present the quick fraction choices with per-choice validity
        fracs = {"25%": 0.25, "33.33%": 0.3333, "50%": 0.5, "66.67%": 0.6667}
        choices = []
        for lbl, fr in fracs.items():
            cu = _round_down(open_units * fr, step_volume_units)
            rem = open_units - cu
            valid = cu >= min_volume_units and cu <= open_units and (rem == 0 or rem >= min_volume_units)
            choices.append({"choice": lbl, "close_units": round(cu, 4),
                            "close_lots": round(cu / units_per_lot, 4),
                            "remaining_units": round(rem, 4), "valid": valid,
                            "est_pnl": est_pnl(cu) if valid else None})
        card = {**base, "quick_choices": choices,
                "exact_broker_valid_note": "or enter an exact step-valid close volume"}
        return PlanAction("PARTIAL_CLOSE", True, "CHOICES_PRESENTED", card)

    # a specific requested fraction
    close_units = _round_down(open_units * float(requested_fraction), step_volume_units)
    remaining = open_units - close_units
    if close_units <= 0:
        return PlanAction("PARTIAL_CLOSE", False, "CLOSE_VOLUME_ZERO_OR_BELOW_STEP", {**base})
    if close_units > open_units:
        return PlanAction("PARTIAL_CLOSE", False, "CLOSE_EXCEEDS_OPEN", {**base})
    if abs((close_units / step_volume_units) - round(close_units / step_volume_units)) > 1e-6:
        return PlanAction("PARTIAL_CLOSE", False, "NOT_STEP_VALID", {**base})
    if remaining != 0 and remaining < min_volume_units:
        return PlanAction("PARTIAL_CLOSE", False, "REMAINING_BELOW_MIN_VOLUME", {**base})
    card = {**base, "proposed_close_units": round(close_units, 4),
            "proposed_close_lots": round(close_units / units_per_lot, 4),
            "remaining_units": round(remaining, 4), "remaining_lots": round(remaining / units_per_lot, 4),
            "estimated_pnl_at_current": est_pnl(close_units)}
    return PlanAction("PARTIAL_CLOSE", True, "OK", card)


def ocr_take_more_proposal(position, ocr, *, min_volume_units, step_volume_units, units_per_lot,
                           lot_size_raw, quote, pip_position, contract_oz_per_lot=100.0, fx=1.0,
                           operator_policy_fraction=0.5):
    """A 'take more profit' OCR candidate. No provider volume -> the OPERATOR scale-out policy (50%)
    is suggested and clearly labelled as NOT the provider's volume. Provider claimed pips are shown
    separately from provider price movement, broker pip calc and estimated P&L from our VWAP."""
    import volume_terms as VT
    d = str(position.direction).upper()
    open_units = float(position.volume_units)
    pip = 10 ** (-pip_position)
    move = ocr.get("provider_price_movement")
    broker_pips_of_move = round(move / pip, 1) if move else None

    def vb(v):
        return VT.breakdown(v, lot_size_raw_protocol=lot_size_raw)

    def est_pnl(close_units):
        oz_per_unit = contract_oz_per_lot / units_per_lot
        mkt = quote.bid if d == "SELL" else quote.ask
        sign = 1 if d == "SELL" else -1
        return round((position.price - mkt) * sign * close_units * oz_per_unit * fx, 2)

    fracs = {"25%": 0.25, "33.33%": 0.3333, "50%": 0.5, "66.67%": 0.6667}
    choices = []
    for lbl, fr in fracs.items():
        cu = _round_down(open_units * fr, step_volume_units)
        rem = open_units - cu
        valid = cu >= min_volume_units and (rem == 0 or rem >= min_volume_units)
        choices.append({"choice": lbl, **vb(cu), "remaining_raw_protocol": round(rem, 4),
                        "valid": valid, "est_pnl_from_our_vwap": est_pnl(cu) if valid else None})

    policy_units = _round_down(open_units * operator_policy_fraction, step_volume_units)
    policy_rem = open_units - policy_units
    policy_valid = policy_units >= min_volume_units and (policy_rem == 0 or policy_rem >= min_volume_units)

    card = {
        "action_type": "PARTIAL_CLOSE_CANDIDATE",
        "raw_ocr_text": ocr["raw_text"], "normalized_candidate": ocr["normalized_candidate"],
        "provider_leg_candidate": ocr["provider_leg_candidate"], "leg_mapping": "PROVIDER_LEG_NOT_YET_MAPPED",
        "provider_close_volume": ocr["provider_close_volume"],
        "operator_policy_fraction": operator_policy_fraction,
        "operator_policy_label": "OPERATOR_POLICY_NOT_PROVIDER_VOLUME",
        "operator_policy_close": vb(policy_units), "operator_policy_remaining": vb(policy_rem),
        "quick_choices": choices,
        "open_volume": vb(open_units),
        "provider_claimed_pips": ocr["provider_claimed_pips"],
        "provider_price_movement": ocr["provider_price_movement"],
        "broker_pip_calc_of_move": broker_pips_of_move,
        "estimated_pnl_from_our_vwap": est_pnl(policy_units) if policy_valid else None,
        "actual_realised_pnl": "UNKNOWN_UNTIL_FILLED",
        "instruction_vs_recap": ocr["instruction_vs_recap"],
        "ambiguity_flags": ocr["ambiguity_flags"],
    }
    return PlanAction("PARTIAL_CLOSE_CANDIDATE", policy_valid, "OPERATOR_POLICY_SUGGESTED", card)


def composite_plan(actions):
    """One displayed plan; future execution is SEQUENTIAL + separately audited (no atomic claim)."""
    return {"plan_type": "COMPOSITE MANAGEMENT PLAN",
            "actions": [{"n": i + 1, "action_type": a.action_type, "ok": a.ok, "reason": a.reason,
                         "detail": a.detail} for i, a in enumerate(actions)],
            "all_actions_valid": all(a.ok for a in actions),
            "execution_note": ("future execution SEQUENTIAL: reconcile -> validate -> amend SL -> "
                               "confirm -> reconcile -> partial close -> confirm -> reconcile. On any "
                               "failure: STOP, show partial-success, require a NEW approval. No atomic claim.")}
