"""OFFLINE cTrader protobuf mapper (Chuck-authorised). Canonical demo-lane request -> exact
cTrader protobuf objects, constructed IN MEMORY ONLY.

It does NOT connect, does NOT import any client/connection/transport implementation, does NOT open
a socket, authenticate, or send. It loads ONLY the generated protobuf message classes, via a
stub-bootstrap that AVOIDS running ctrader_open_api/__init__ (which imports the Twisted Client) -
a test asserts twisted / socket / the client module are never imported.

Volume is NOT hard-coded: it is passed in, derived by the caller from the VERIFIED real symbol
metadata and the exact ratified nominal quantity (see brain volume-terminology record).
"""
import hashlib
import json
import os
import sys
import types

_PB2 = None


def _load_pb2():
    """Load ONLY the pb2 message classes, without importing the Twisted client. Installs bare
    package stubs for ctrader_open_api / .messages so the real __init__ (Client import) never runs;
    submodule imports resolve against the real dirs via __path__."""
    global _PB2
    if _PB2 is not None:
        return _PB2
    pkgdir = None
    for p in sys.path:
        cand = os.path.join(p, "ctrader_open_api")
        if os.path.isfile(os.path.join(cand, "messages", "OpenApiMessages_pb2.py")):
            pkgdir = cand
            break
    if pkgdir is None:
        raise RuntimeError("ctrader_open_api protobuf messages not found (run under .venv-ctrader)")
    for name, sub in (("ctrader_open_api", ""), ("ctrader_open_api.messages", "messages")):
        existing = sys.modules.get(name)
        if existing is None or not hasattr(existing, "__path__"):
            m = types.ModuleType(name)
            m.__path__ = [os.path.join(pkgdir, sub) if sub else pkgdir]
            m.__package__ = name
            sys.modules[name] = m
    from ctrader_open_api.messages.OpenApiMessages_pb2 import (
        ProtoOANewOrderReq, ProtoOAClosePositionReq)
    from ctrader_open_api.messages.OpenApiModelMessages_pb2 import (
        ProtoOAOrderType, ProtoOATradeSide, ProtoOATimeInForce)
    _PB2 = {"NewOrder": ProtoOANewOrderReq, "Close": ProtoOAClosePositionReq,
            "OrderType": ProtoOAOrderType, "TradeSide": ProtoOATradeSide,
            "TimeInForce": ProtoOATimeInForce}
    return _PB2


def deterministic_client_order_id(correlation):
    """Correlation only (NOT security): same correlation dict -> same id, deterministically."""
    digest = hashlib.sha256(json.dumps(correlation, sort_keys=True, default=str).encode()).hexdigest()
    return "ORG-" + digest[:20]


def build_new_order_req(*, ctid_trader_account_id, symbol_id, side, volume, limit_price,
                        stop_loss, expiration_timestamp, correlation, client_order_id=None):
    """Approved LIMIT opening -> ProtoOANewOrderReq. The protective stop is set on the INITIAL
    request (stopLoss); orderType is LIMIT and timeInForce is GOOD_TILL_DATE, both fixed. Volume
    is passed in (derived from verified real metadata x ratified nominal) - never hard-coded."""
    if side not in ("BUY", "SELL"):
        raise ValueError(f"side must be BUY or SELL, got {side!r}")
    if stop_loss is None:
        raise ValueError("protective stop (stopLoss) is required on the initial request")
    if not isinstance(volume, int) or volume <= 0:
        raise ValueError("volume must be a positive integer protocol volume")
    if not expiration_timestamp or expiration_timestamp <= 0:
        raise ValueError("GOOD_TILL_DATE requires an exact positive expiration timestamp")
    pb = _load_pb2()
    r = pb["NewOrder"]()
    r.ctidTraderAccountId = ctid_trader_account_id
    r.symbolId = symbol_id
    r.orderType = pb["OrderType"].LIMIT                 # LIMIT-only opening (fixed)
    r.tradeSide = pb["TradeSide"].Value(side)
    r.volume = volume                                   # exact protocol volume (input, not hard-coded)
    r.limitPrice = limit_price
    r.stopLoss = stop_loss                              # protective stop attached AT placement
    r.timeInForce = pb["TimeInForce"].GOOD_TILL_DATE    # GTD (fixed)
    r.expirationTimestamp = expiration_timestamp
    r.clientOrderId = client_order_id or deterministic_client_order_id(correlation)
    r.label = "ORANGE_DEMO"
    return r


def build_close_position_req(*, ctid_trader_account_id, position_id, volume, owner_verified):
    """Risk-reducing close of a POSITIVELY-IDENTIFIED Orange-owned position -> ProtoOAClosePositionReq.
    Refuses to build unless the caller asserts ownership was verified (no touch otherwise)."""
    if owner_verified is not True:
        raise ValueError("close refused: position ownership not positively verified")
    if not isinstance(volume, int) or volume <= 0:
        raise ValueError("close volume must be a positive integer (reduce-only)")
    pb = _load_pb2()
    c = pb["Close"]()
    c.ctidTraderAccountId = ctid_trader_account_id
    c.positionId = position_id
    c.volume = volume                                   # reduce-only quantity
    return c
