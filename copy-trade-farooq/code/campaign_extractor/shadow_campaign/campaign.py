"""
Shadow strike-then-reconcile-then-trap sequence runner (v1.0.0). SHADOW ONLY — no atomic execution,
no broker action. T1/T2/T3 are NOT modelled as one simultaneous operation: the strike is sent,
reconciled, protected, and only THEN are traps calculated and placed. Fail-closed on rejection /
uncertainty / protection failure.
"""
from __future__ import annotations

import sc_config as CFG
import strike_trap as ST


def run_shadow_campaign(*, direction, low, high, quote, provider_stop, balance, slippage_points,
                        strike_outcome="FILLED", filled_fraction=1.0, protection_ok=True,
                        exact_stop_ok=True):
    """strike_outcome in FILLED / PARTIAL / REJECTED / UNCERTAIN. Returns the append-only state trail,
    ledger snapshots, traps and final result. No traps are calculated before T1 reconciliation."""
    states = ["INSIDE_ZONE_QUALIFIED", "STRIKE_APPROVAL_PENDING"]
    sizing = ST.size_worst_fill_risk(direction, quote=quote, provider_stop=provider_stop,
                                     balance=balance, slippage_points=slippage_points)
    if not sizing["ok"]:
        return {"states": states + ["INSIDE_ZONE_BLOCKED"], "result": sizing["reason"],
                "aborted": True, "traps": [], "no_broker_action": True}
    strike = ST.strike_shadow(direction, quote, slippage_points=slippage_points)
    if strike["REJECTED_OUTSIDE_RANGE"]:
        return {"states": states + ["STRIKE_SHADOW_SENT", "STRIKE_SHADOW_REJECTED", "CAMPAIGN_ABORTED"],
                "result": "STRIKE_REJECTED", "aborted": True, "traps": [], "strike": strike,
                "no_broker_action": True}

    # 1 revalidate, 2 consume permit (SHADOW — none issued), 3 send T1
    states.append("STRIKE_SHADOW_SENT")

    if strike_outcome == "REJECTED":
        return {"states": states + ["STRIKE_SHADOW_REJECTED", "CAMPAIGN_ABORTED"],
                "result": "STRIKE_REJECTED", "aborted": True, "traps": [], "no_broker_action": True}
    if strike_outcome == "UNCERTAIN":
        return {"states": states + ["STRIKE_RECONCILIATION_REQUIRED"], "result": "NO_TRAPS_ALLOWED",
                "no_traps_allowed": True, "traps": [], "no_broker_action": True}

    # 4-5 reconcile: authoritative filled volume + campaign VWAP (partial => only filled volume counts)
    frac = filled_fraction if strike_outcome == "PARTIAL" else 1.0
    filled_lots = round(sizing["t1_lots"] * frac, 2)
    if filled_lots < CFG.MIN_LOT:
        return {"states": states + ["STRIKE_SHADOW_PARTIAL_FILL", "STRIKE_RECONCILIATION_REQUIRED"],
                "result": "NO_TRAPS_ALLOWED", "no_traps_allowed": True, "traps": [], "no_broker_action": True}
    states.append("STRIKE_SHADOW_PARTIAL_FILL" if strike_outcome == "PARTIAL" else "STRIKE_SHADOW_FILLED")
    vwap = strike["WORST_ALLOWED_FILL"]                     # conservative shadow VWAP = worst permitted
    actual_t1_risk = round(abs(vwap - provider_stop) * filled_lots * CFG.CONTRACT_OZ_PER_LOT, 4)

    # 6 protection FIRST — block all child placement until protection is confirmed
    states.append("STRIKE_FILLED_PROTECTION_PENDING")
    prot = ST.provisional_stop(direction, best_fill=strike["BEST_ALLOWED_FILL"],
                               worst_fill=strike["WORST_ALLOWED_FILL"], provider_stop=provider_stop)
    if not prot["ok"] or not protection_ok:
        return {"states": states + ["PROTECTION_FAILED", "CAMPAIGN_ABORTED"],
                "result": "STRIKE_PROTECTION_UNAVAILABLE", "aborted": True, "traps": [],
                "no_broker_action": True}
    states.append("STRIKE_PROVISIONALLY_PROTECTED")
    states.append("EXACT_STOP_AMEND_PENDING")
    if not exact_stop_ok:                                   # exact stop amend fails -> NO T2/T3, stop, review
        return {"states": states + ["PROTECTION_FAILED"], "result": "EXACT_STOP_AMEND_FAILED",
                "aborted": True, "traps": [], "operator_review_required": True,
                "fully_protected_claim": False, "no_broker_action": True}
    states.append("EXACT_STOP_CONFIRMED")

    # 7-8 update consumed risk + recalc remaining budget from the AUTHORITATIVE remaining
    ledger = ST.risk_ledger(balance=balance, strike_actual_risk=actual_t1_risk,
                            strike_target=sizing["strike_budget"], strike_worst=sizing["t1_worst_fill_risk"])
    remaining = ledger["AVAILABLE_RISK"]

    # 9-11 ONLY NOW: construct + place passive traps, reconcile each
    states.append("TRAPS_CALCULATED")
    traps = ST.passive_traps(direction=direction, low=low, high=high, quote=quote,
                             remaining_risk=remaining, provider_stop=provider_stop, balance=balance)
    placed = [t for t in traps if t.get("status") == "PASSIVE_VALID"]
    states.append("TRAPS_ARMED_SHADOW")
    reserved = round(sum(t["reserved_risk"] for t in placed), 4)
    ledger = ST.risk_ledger(balance=balance, strike_actual_risk=actual_t1_risk, trap_reserved=reserved,
                            strike_target=sizing["strike_budget"], strike_worst=sizing["t1_worst_fill_risk"])
    states.append("CAMPAIGN_COMPLETED_SHADOW")               # 12 relock (shadow)
    return {"states": states, "result": "SHADOW_CAMPAIGN_COMPLETE", "aborted": False, "strike": strike,
            "sizing": sizing, "provisional_protection": prot, "vwap": vwap, "actual_t1_risk": actual_t1_risk,
            "traps": traps, "placed_traps": placed, "ledger": ledger, "atomic": False,
            "no_broker_action": True, "model_version": CFG.STRIKE_TRAP_MODEL_VERSION}
