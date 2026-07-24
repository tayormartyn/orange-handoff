"""MOCK order channel (wire simulator) for the RealOrderAdapter. In-memory ONLY: no network, no
protobuf, no ctrader_open_api. Configurable to exercise every scenario Chuck reviews - stop
rejected/omitted, partial fill, lost response, silent entry/stop normalization, account mutation,
closed/untradeable session. This is TEST infrastructure, parallel to mock_broker.MockBroker."""
from .broker_request import BrokerOrderRequest

# the RATIFIED live XAUUSD spec (D-092): lotSize 10000, min/step 100, max 500000, tick 0.01,
# min stop distance 0 points. 0.01 lot -> exactly 100 protocol volume.
RATIFIED_XAUUSD_META = {"lotSize": 10000, "minVolume": 100, "maxVolume": 500000,
                        "stepVolume": 100, "tickSize": 0.01, "minStopDistance": 0.0,
                        "session_open": True, "tradeable": True}


class MockOrderChannel:
    IS_MOCK = True                              # marker: the test-only enabled policy binds to this

    def __init__(self, *, symbol_meta=None, lose_response=False, normalize_entry=False,
                 normalize_stop=False, mutate_account=False, reject_stop=False,
                 fill_mode="PENDING", partial_volume=None, session_open=True, tradeable=True,
                 cancel_outcome_unknown=False):
        self.cancel_outcome_unknown = cancel_outcome_unknown
        self._meta = dict(symbol_meta or RATIFIED_XAUUSD_META)
        self._meta["session_open"] = session_open
        self._meta["tradeable"] = tradeable
        self.lose_response = lose_response
        self.normalize_entry = normalize_entry
        self.normalize_stop = normalize_stop
        self.mutate_account = mutate_account
        self.reject_stop = reject_stop          # broker omits/does not confirm the protective stop
        self.fill_mode = fill_mode              # "PENDING" | "FULL" | "PARTIAL"
        self.partial_volume = partial_volume
        self.orders = {}                        # order_id -> order
        self.positions = {}                     # position_id -> {volume, owner}
        self._n = 1
        self.send_open_count = 0

    def symbol_meta(self, symbol_id):
        return dict(self._meta)

    def send_open(self, spec):
        assert isinstance(spec, BrokerOrderRequest)
        self.send_open_count += 1
        if self.lose_response:
            return None                         # lost response -> adapter returns None
        oid = f"O{self._n}"; self._n += 1
        entry = round(spec.limit_price * 1.0001, 2) if self.normalize_entry else spec.limit_price
        if self.reject_stop:
            stop, stop_accepted = None, False   # broker rejected/omitted the protective stop
        elif self.normalize_stop:
            stop, stop_accepted = round(spec.stop_loss + 0.5, 2), True
        else:
            stop, stop_accepted = spec.stop_loss, True
        acct = spec.ctid_trader_account_id + 999 if self.mutate_account else spec.ctid_trader_account_id
        if self.fill_mode == "FULL":
            filled, status = spec.volume, "FILLED"
        elif self.fill_mode == "PARTIAL":
            filled = self.partial_volume if self.partial_volume is not None else spec.volume // 2
            status = "PARTIALLY_FILLED"
        else:
            filled, status = 0, "PENDING"
        pid = None
        if filled > 0:
            pid = f"P{oid}"
            self.positions[pid] = {"volume": filled, "owner": "ORANGE"}
        order = {"order_id": oid, "account_id": acct, "symbol_id": spec.symbol_id,
                 "trade_side": spec.trade_side, "volume": spec.volume, "limit_price": entry,
                 "stop_loss": stop, "stop_accepted": stop_accepted,
                 "expiration_timestamp": spec.expiration_timestamp,
                 "filled_volume": filled, "pending_volume": max(spec.volume - filled, 0),
                 "position_id": pid, "status": status}
        self.orders[oid] = order
        return dict(order)

    def send_cancel(self, order_id):
        """Structured result. cancel_outcome_unknown -> {'cancelled': None} and the order is NOT
        removed (ambiguous outcome); otherwise remove and report the confirmed result."""
        if self.cancel_outcome_unknown:
            return {"order_id": order_id, "cancelled": None}
        o = self.orders.pop(order_id, None)
        return {"order_id": order_id, "cancelled": o is not None}

    def send_close(self, position_id, volume, owner="ORANGE"):
        """Close-ONLY reduce. Refuses non-owned (no touch), over-close, and any non-positive qty."""
        pos = self.positions.get(position_id)
        if pos is None:
            raise ValueError("no such position")
        if pos["owner"] != owner:
            raise PermissionError("not Orange-owned - no touch")
        if volume <= 0:
            raise ValueError("close volume must be positive")
        if volume > pos["volume"]:
            raise ValueError("excessive close quantity (close-only reduce, never increase/reverse)")
        pos["volume"] -= volume
        if pos["volume"] == 0:
            del self.positions[position_id]
        return {"closed": volume, "position_id": position_id}

    def list_orders(self):
        return dict(self.orders)

    def list_positions(self):
        return dict(self.positions)

    def orders_past_expiry(self, now_ts):
        return [oid for oid, o in self.orders.items() if (o.get("expiration_timestamp") or 1e18) < now_ts]
