"""
Provider-side outcome derivation. This describes what the PROVIDER's trade did per provider wording +
recorded market path — it is NEVER Martyn's realised demo result (that requires BROKER_EXECUTION_
EVIDENCE and is produced only by outcome_rules.py). No realised demo P&L is ever emitted here.
"""
from __future__ import annotations

# provider-side event kinds
PROVIDER_PARTIAL_PROFIT_CONFIRMED = "PROVIDER_PARTIAL_PROFIT_CONFIRMED"
MARKET_BREAKEVEN_TOUCH = "MARKET_BREAKEVEN_TOUCH"
MARKET_ORIGINAL_STOP_TOUCH = "MARKET_ORIGINAL_STOP_TOUCH"

# provider-side outcomes
PROVIDER_MANAGED_PROFIT = "PROVIDER_MANAGED_PROFIT"
PROVIDER_BREAKEVEN = "PROVIDER_BREAKEVEN"
PROVIDER_LOSS = "PROVIDER_LOSS"
PROVIDER_PROFIT_R_UNKNOWN = "PROVIDER_PROFIT_R_UNKNOWN"
UNRESOLVED = "UNRESOLVED"


def determine_provider_outcome(*, provider_partial_confirmed=False, provider_profit_claimed=False,
                               provider_volume_known=False, market_breakeven_touch=False,
                               market_original_stop_touch=False, profit_before_stop=False):
    """Pure provider-side classification. Returns (outcome, blockers, note)."""
    blockers = []
    note = ("PROVIDER-SIDE ONLY. This is NOT Martyn's realised demo result — that requires broker "
            "execution evidence.")

    # original stop hit before any confirmed profit -> provider loss
    if market_original_stop_touch and not provider_partial_confirmed and not profit_before_stop:
        return PROVIDER_LOSS, blockers, note

    # confirmed provider partial profit + later breakeven runner -> managed profit
    if provider_partial_confirmed and market_breakeven_touch:
        if not provider_volume_known:
            return PROVIDER_PROFIT_R_UNKNOWN, ["PROVIDER_PARTIAL_VOLUME_UNKNOWN"], note
        return PROVIDER_MANAGED_PROFIT, blockers, note

    # breakeven runner with no confirmed partial -> provider breakeven
    if market_breakeven_touch and not provider_partial_confirmed:
        return PROVIDER_BREAKEVEN, blockers, note

    # provider claims profit but volume / fill unknown -> R unknown
    if provider_profit_claimed and not provider_volume_known:
        return PROVIDER_PROFIT_R_UNKNOWN, ["PROVIDER_PROFIT_VOLUME_OR_FILL_UNKNOWN"], note

    return UNRESOLVED, ["INSUFFICIENT_EVIDENCE"], note
