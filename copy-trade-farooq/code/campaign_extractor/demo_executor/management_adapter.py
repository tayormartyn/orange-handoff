"""
Real (but network-disabled) trade-MANAGEMENT request adapters. Constructs, from an IMMUTABLE
ApprovedManagementPlan, exactly one of:
  ProtoOAAmendPositionSLTPReq  (move SL — e.g. to broker-VWAP breakeven)
  ProtoOAClosePositionReq      (partial/full close by volume)
  ProtoOACancelOrderReq        (cancel a pending order)
It does NOT enable general order amendment or any market-entry route, and does NOT recompute/
reinterpret trade values. Constructing a message does NOT send it — transmission is gated by
management_transport.py (blocked while ORDER_MANAGEMENT_ENABLED=False). The protobuf import is lazy so
this module loads (and is testable) without the cTrader library present. XAUUSD + allowlisted demo
account only.
"""
from __future__ import annotations

import config as CFG


class UnsupportedManagement(Exception):
    pass


def _validate(approved, *, need_position=False, need_order=False):
    if str(approved.symbol_name).upper() != CFG.XAUUSD_NAME or approved.symbol_id != CFG.XAUUSD_SYMBOL_ID:
        raise UnsupportedManagement("UNSUPPORTED_SYMBOL")
    if approved.account_id not in CFG.DEMO_ALLOWLIST_ACCOUNT_IDS:
        raise UnsupportedManagement("ACCOUNT_NOT_ALLOWLISTED")
    if need_position and not approved.broker_position_id:
        raise UnsupportedManagement("POSITION_ID_REQUIRED")
    if need_order and not approved.broker_order_id:
        raise UnsupportedManagement("ORDER_ID_REQUIRED")


# ---- offline serialization (no protobuf lib, no secrets) ----
def serialize_amend_sltp(approved):
    _validate(approved, need_position=True)
    if approved.new_stop_loss is None:
        raise UnsupportedManagement("NEW_STOP_LOSS_REQUIRED")
    return {"_req": "ProtoOAAmendPositionSLTPReq", "ctidTraderAccountId": approved.account_id,
            "positionId": approved.broker_position_id, "stopLoss": approved.new_stop_loss,
            "takeProfit": approved.new_take_profit}


def serialize_close(approved):
    _validate(approved, need_position=True)
    if approved.close_volume_raw is None:
        raise UnsupportedManagement("CLOSE_VOLUME_REQUIRED")
    return {"_req": "ProtoOAClosePositionReq", "ctidTraderAccountId": approved.account_id,
            "positionId": approved.broker_position_id, "volume": int(approved.close_volume_raw)}


def serialize_cancel(approved):
    _validate(approved, need_order=True)
    return {"_req": "ProtoOACancelOrderReq", "ctidTraderAccountId": approved.account_id,
            "orderId": approved.broker_order_id}


# ---- real protobuf construction (lazy import; only reachable on a passed management gate) ----
def build_amend_position_sltp(approved):
    _validate(approved, need_position=True)
    if approved.new_stop_loss is None:
        raise UnsupportedManagement("NEW_STOP_LOSS_REQUIRED")
    from ctrader_open_api.messages.OpenApiMessages_pb2 import ProtoOAAmendPositionSLTPReq
    r = ProtoOAAmendPositionSLTPReq()
    r.ctidTraderAccountId = int(approved.account_id)
    r.positionId = int(approved.broker_position_id)
    r.stopLoss = float(approved.new_stop_loss)
    if approved.new_take_profit is not None:
        r.takeProfit = float(approved.new_take_profit)
    return r


def build_close_position(approved):
    _validate(approved, need_position=True)
    if approved.close_volume_raw is None:
        raise UnsupportedManagement("CLOSE_VOLUME_REQUIRED")
    from ctrader_open_api.messages.OpenApiMessages_pb2 import ProtoOAClosePositionReq
    r = ProtoOAClosePositionReq()
    r.ctidTraderAccountId = int(approved.account_id)
    r.positionId = int(approved.broker_position_id)
    r.volume = int(approved.close_volume_raw)
    return r


def build_cancel_order(approved):
    _validate(approved, need_order=True)
    from ctrader_open_api.messages.OpenApiMessages_pb2 import ProtoOACancelOrderReq
    r = ProtoOACancelOrderReq()
    r.ctidTraderAccountId = int(approved.account_id)
    r.orderId = int(approved.broker_order_id)
    return r
