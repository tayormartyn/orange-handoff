"""Canonical broker-request specs for the demo lane (mock-first). These mirror the SEMANTICS of
cTrader ProtoOANewOrderReq / ProtoOAClosePositionReq WITHOUT importing ctrader_open_api or any
protobuf. The wire mapping (spec -> protobuf -> Twisted send) is the SEPARATE, later,
Chuck-reviewed live-channel step. Opening placement is LIMIT-only; a protective stop is REQUIRED
at placement (there is no field, path, or default that yields an unprotected opening order)."""
from dataclasses import dataclass


@dataclass(frozen=True)
class BrokerOrderRequest:
    ctid_trader_account_id: int
    symbol_id: object
    trade_side: str                    # "BUY" | "SELL"
    volume: int                        # protocol volume
    limit_price: float
    stop_loss: float                   # broker-native protective stop, attached AT placement
    expiration_timestamp: int
    order_type: str = "LIMIT"          # opening placement is LIMIT-only
    time_in_force: str = "GOOD_TILL_DATE"
    label: str = "ORANGE_DEMO"


@dataclass(frozen=True)
class BrokerCloseRequest:
    position_id: object
    volume: int                        # reduce-only quantity (never increases/reverses)
    reason: str = "RISK_REDUCTION"
