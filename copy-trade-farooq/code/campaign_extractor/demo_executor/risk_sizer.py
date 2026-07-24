"""
Risk sizing from the ACTUAL demo account + ACTUAL cTrader symbol metadata. Rounds volume DOWN to a
valid broker step, recomputes the maximum theoretical loss after rounding, and blocks if it exceeds
the selected risk. Includes expected-margin computation. Never assumes a fixed balance.
"""
from __future__ import annotations
import math

import config as CFG
from models import RiskSizing


def _round_down_step(value, step):
    if step <= 0:
        return value
    return math.floor(round(value / step, 9)) * step


def size_order(*, account, symbol, entry, stop, risk_pct=None, fx_quote_to_account=1.0, leverage=100.0):
    """fx_quote_to_account converts the symbol quote currency (USD) into the account currency."""
    risk_pct = CFG.DEFAULT_RISK_PCT if risk_pct is None else float(risk_pct)
    if risk_pct > CFG.MAX_RISK_PCT:                       # hard cap at 1%
        risk_pct = CFG.MAX_RISK_PCT
    risk_amount = round(account.balance * risk_pct, 2)
    stop_distance = abs(float(entry) - float(stop))
    if stop_distance <= 0:
        return RiskSizing(False, "STOP_DISTANCE_ZERO", risk_pct, risk_amount, account.balance,
                          account.currency, 0.0, 0.0, 0.0, None, stop_distance)

    # loss (account ccy) if 1.0 lot is stopped out = stop_distance * contract_size * fx
    loss_per_lot = stop_distance * symbol.lot_size * fx_quote_to_account
    if loss_per_lot <= 0:
        return RiskSizing(False, "INVALID_SYMBOL_METADATA", risk_pct, risk_amount, account.balance,
                          account.currency, 0.0, 0.0, 0.0, None, stop_distance)

    raw_lots = risk_amount / loss_per_lot
    volume_lots = _round_down_step(raw_lots, symbol.volume_step)          # round DOWN
    volume_lots = min(volume_lots, symbol.max_volume)
    if volume_lots < symbol.min_volume:
        return RiskSizing(False, "BELOW_MIN_VOLUME", risk_pct, risk_amount, account.balance,
                          account.currency, 0.0, 0.0, 0.0, None, stop_distance)

    max_loss = round(volume_lots * loss_per_lot, 2)
    if max_loss > risk_amount + 1e-6:                    # must stay within risk AFTER rounding
        return RiskSizing(False, "LOSS_EXCEEDS_RISK_AFTER_ROUNDING", risk_pct, risk_amount,
                          account.balance, account.currency, volume_lots,
                          volume_lots * symbol.lot_size, max_loss, None, stop_distance)

    # expected margin (account ccy) ~ notional / leverage
    notional = volume_lots * symbol.lot_size * float(entry) * fx_quote_to_account
    expected_margin = round(notional / max(leverage, 1.0), 2)
    if expected_margin <= 0 or expected_margin > account.balance:
        return RiskSizing(False, "INVALID_OR_INSUFFICIENT_MARGIN", risk_pct, risk_amount,
                          account.balance, account.currency, volume_lots,
                          volume_lots * symbol.lot_size, max_loss, expected_margin, stop_distance)

    return RiskSizing(True, "OK", risk_pct, risk_amount, account.balance, account.currency,
                      round(volume_lots, 4), round(volume_lots * symbol.lot_size, 2), max_loss,
                      expected_margin, stop_distance)
