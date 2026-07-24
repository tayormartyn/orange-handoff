"""MOCK cTrader adapter. No network, no real account, no order capability beyond in-memory
simulation. Configurable to exercise every proof test (live account, silent normalization,
lost response, unknown position, partial fill)."""


class MockBroker:
    def __init__(self, account=None, symbol_meta=None,
                 normalize=False, normalize_stop=False, lose_response=False,
                 session_open=True, symbol_tradeable=True, mutate_account=False):
        self.account = account or {
            "endpoint": "demo.ctraderapi.com", "isLive": False,
            "ctidTraderAccountId": 1_000_001, "broker_environment": "PEPPERSTONE_DEMO",
            "permissionScope": "SCOPE_TRADE",
            "accountType": "HEDGED",   # present but MUST NOT be used as the live/demo test
        }
        self._meta = symbol_meta or {"lotSize": 100, "minVolume": 1, "maxVolume": 10000,
                                     "stepVolume": 1, "tickSize": 0.01, "minStopDistance": 1.0,
                                     "session_open": session_open, "tradeable": symbol_tradeable}
        self.normalize = normalize            # silently adjust ENTRY price
        self.normalize_stop = normalize_stop  # silently adjust STOP price (distinct)
        self.mutate_account = mutate_account  # return a DIFFERENT account_id (GAP 1)
        self.lose_response = lose_response
        self.orders = {}          # order_id -> order
        self.positions = {}       # position_id -> {volume, owner}
        self._next = 1
        self.broker_call_count = 0   # instrumentation: increments on any order-placing call

    def account_info(self):
        return dict(self.account)

    def symbol_meta(self, symbol_id):
        return dict(self._meta)

    def place_limit(self, req):
        self.broker_call_count += 1                       # every attempt to reach the broker
        if self.lose_response:
            return None                                   # simulate lost response
        oid = f"O{self._next}"; self._next += 1
        ack = dict(req)
        if self.normalize:                                # silent normalization of ENTRY price
            ack["entry_price"] = round(req["entry_price"] * 1.0001, 2)
        if self.normalize_stop:                           # silent normalization of STOP price
            ack["stop_price"] = round(req["stop_price"] + 0.5, 2)
        if self.mutate_account:                           # order landed on a DIFFERENT account
            ack["account_id"] = (req.get("account_id") or 0) + 999
        ack["order_id"] = oid
        ack["owner"] = "ORANGE"
        self.orders[oid] = ack
        return ack

    def cancel_order(self, order_id):
        return self.orders.pop(order_id, None)

    def orders_past_expiry(self, now_ts):
        return [oid for oid, o in self.orders.items() if o.get("expiry_ts", 1e18) < now_ts]

    def list_orders(self):
        return dict(self.orders)

    def list_positions(self):
        return dict(self.positions)

    # test helpers for close/kill/unknown scenarios
    def open_position(self, position_id, volume, owner="ORANGE"):
        self.positions[position_id] = {"volume": volume, "owner": owner}

    def close_position(self, position_id, volume, owner_check="ORANGE"):
        pos = self.positions.get(position_id)
        if pos is None:
            raise ValueError("no such position")
        if pos["owner"] != owner_check:
            raise PermissionError("not Orange-owned — no touch")
        if volume > pos["volume"]:
            raise ValueError("excessive close quantity")
        pos["volume"] -= volume
        if pos["volume"] == 0:
            del self.positions[position_id]
        return {"closed": volume, "position_id": position_id}
