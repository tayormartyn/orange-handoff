"""
Real (but network-disabled) request adapter. Constructs a cTrader ProtoOANewOrderReq from an
IMMUTABLE ApprovedDemoOrderRequest WITHOUT recalculating or reinterpreting any trade value. Supports
only XAUUSD + LIMIT/STOP + the allowlisted demo account + a mandatory stop-loss; market orders and
every other order type are rejected. Constructing a message does NOT send it — transmission is gated
by network_send.py (blocked while ORDER_SENDING_ENABLED=False). The protobuf import is lazy so this
module loads (and is testable) without the cTrader library present.
"""
from __future__ import annotations

import config as CFG
import order_transport as OT


class UnsupportedOrder(Exception):
    pass


def _validate_supported(approved):
    if str(approved.symbol_name).upper() != CFG.XAUUSD_NAME or approved.symbol_id != CFG.XAUUSD_SYMBOL_ID:
        raise UnsupportedOrder("UNSUPPORTED_SYMBOL")
    if str(approved.order_type).upper() not in ("LIMIT", "STOP"):
        raise UnsupportedOrder("UNSUPPORTED_ORDER_TYPE")     # rejects MARKET and everything else
    if str(approved.trade_side).upper() not in ("BUY", "SELL"):
        raise UnsupportedOrder("UNSUPPORTED_TRADE_SIDE")
    if approved.stop_loss is None:
        raise UnsupportedOrder("MISSING_MANDATORY_STOP_LOSS")
    if approved.account_id not in CFG.DEMO_ALLOWLIST_ACCOUNT_IDS:
        raise UnsupportedOrder("ACCOUNT_NOT_ALLOWLISTED")


def serialize_fields(approved):
    """Offline serialization (plain dict) of the exact request — no protobuf lib, no secrets."""
    _validate_supported(approved)
    return OT.build_new_order_fields(approved)


def build_new_order_request(approved):
    """Construct the REAL ProtoOANewOrderReq (lazy import). Values are copied verbatim from the
    immutable approved request — nothing is recomputed. Constructing != sending."""
    _validate_supported(approved)
    from ctrader_open_api.messages.OpenApiMessages_pb2 import ProtoOANewOrderReq
    from ctrader_open_api.messages.OpenApiModelMessages_pb2 import ProtoOAOrderType, ProtoOATradeSide

    r = ProtoOANewOrderReq()
    r.ctidTraderAccountId = int(approved.account_id)
    r.symbolId = int(approved.symbol_id)
    r.tradeSide = ProtoOATradeSide.BUY if approved.trade_side == "BUY" else ProtoOATradeSide.SELL
    if approved.order_type == "LIMIT":
        r.orderType = ProtoOAOrderType.LIMIT
        r.limitPrice = float(approved.limit_price)
    else:
        r.orderType = ProtoOAOrderType.STOP
        r.stopPrice = float(approved.stop_price)
    r.volume = int(approved.volume_raw_protocol)
    r.stopLoss = float(approved.stop_loss)
    if approved.take_profit is not None:
        r.takeProfit = float(approved.take_profit)
    r.clientOrderId = str(approved.client_order_id)
    r.label = str(approved.label)
    r.comment = str(approved.comment)
    return r
