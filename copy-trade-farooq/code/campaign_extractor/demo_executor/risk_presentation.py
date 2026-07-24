"""
All-in risk presentation. PLANNED STOP-LOSS RISK is the price-based stop risk (commission EXCLUDED).
This module surfaces commission/fees explicitly so we NEVER claim an exact "N% all-in" (the canonical
campaign risk percent is set in risk_policy.py) while commission is excluded. If commission cannot be estimated before entry, COMMISSION_ESTIMATE_STATUS
= UNKNOWN and the strict-risk claim is blocked (or a conservative reserve is applied).
"""
from __future__ import annotations

import config as CFG


def all_in_risk(*, risk_budget, planned_stop_loss_risk, open_commission=None, close_commission=None,
                other_fees=None, use_reserve=False):
    known = open_commission is not None and close_commission is not None
    status = "ESTIMATED" if known else "UNKNOWN"
    oc = open_commission if open_commission is not None else 0.0
    cc = close_commission if close_commission is not None else 0.0
    of = other_fees if other_fees is not None else 0.0

    reserve = 0.0
    if not known and use_reserve:
        reserve = round(risk_budget * CFG.COMMISSION_RESERVE_FRACTION, 2)

    all_in = round(planned_stop_loss_risk + oc + cc + of + reserve, 2)
    # strict "exact X% all-in" is only allowed when commission is genuinely estimated (or reserved)
    strict_claim_allowed = known or (use_reserve and reserve > 0)
    headroom = round(risk_budget - planned_stop_loss_risk, 2)
    return {
        "RISK_BUDGET": round(risk_budget, 2),
        "PLANNED_STOP_LOSS_RISK": round(planned_stop_loss_risk, 2),
        "ESTIMATED_OPEN_COMMISSION": (round(oc, 2) if known else None),
        "ESTIMATED_CLOSE_COMMISSION": (round(cc, 2) if known else None),
        "OTHER_ESTIMATED_FEES": (round(of, 2) if other_fees is not None else None),
        "CONSERVATIVE_COMMISSION_RESERVE": (reserve if reserve else None),
        "ALL_IN_ESTIMATED_RISK": all_in,
        "COMMISSION_ESTIMATE_STATUS": status,
        "remaining_risk_headroom": headroom,
        "headroom_covers_commission": None if not known else (headroom >= (oc + cc + of)),
        "strict_all_in_claim_allowed": strict_claim_allowed,
        "note": ("Commission EXCLUDED from PLANNED STOP-LOSS RISK. Do NOT assume the headroom covers "
                 "commission without evidence. Actual realised loss may differ (spread/commission/"
                 "slippage/gapping/execution)."),
    }
