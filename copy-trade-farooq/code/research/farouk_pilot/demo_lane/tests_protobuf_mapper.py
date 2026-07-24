"""Offline cTrader protobuf mapper proof. Runs under .venv-ctrader (needs the protobuf messages).
Builds exact protobuf objects IN MEMORY; asserts NO twisted / socket / client import.
Run:  .venv-ctrader/Scripts/python -m research.farouk_pilot.demo_lane.tests_protobuf_mapper
"""
import importlib
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))
pm = importlib.import_module("research.farouk_pilot.demo_lane.protobuf_mapper")

_p = _f = 0
def ck(n, c):
    global _p, _f
    print(("  ok  " if c else "FAIL  ") + n); _p += bool(c); _f += (not c)
def raises(t, e):
    try:
        t(); return False
    except e:
        return True

FAR = 10 ** 12
corr = {"campaign_id": "XAU-DEMO-TEST", "leg": 0, "account": 47758849, "symbol": 41,
        "entry": 4063.00, "expiry": FAR}

r = pm.build_new_order_req(ctid_trader_account_id=47758849, symbol_id=41, side="BUY", volume=100,
    limit_price=4063.00, stop_loss=4040.00, expiration_timestamp=FAR, correlation=corr)
pb = pm._load_pb2()

ck("approved demo account id set", r.ctidTraderAccountId == 47758849)
ck("allowlisted XAUUSD symbol id set (41)", r.symbolId == 41)
ck("orderType == LIMIT", r.orderType == pb["OrderType"].LIMIT)
ck("tradeSide == BUY", r.tradeSide == pb["TradeSide"].BUY)
ck("exact protocol volume (100)", r.volume == 100)
ck("exact limit price", abs(r.limitPrice - 4063.00) < 1e-9)
ck("protective stop in the INITIAL request (stopLoss)", abs(r.stopLoss - 4040.00) < 1e-9)
ck("timeInForce == GOOD_TILL_DATE", r.timeInForce == pb["TimeInForce"].GOOD_TILL_DATE)
ck("exact expiration timestamp", r.expirationTimestamp == FAR)
ck("deterministic clientOrderId (correlation only)", isinstance(r.clientOrderId, str) and r.clientOrderId.startswith("ORG-"))

r2 = pm.build_new_order_req(ctid_trader_account_id=47758849, symbol_id=41, side="BUY", volume=100,
    limit_price=4063.00, stop_loss=4040.00, expiration_timestamp=FAR, correlation=corr)
ck("clientOrderId deterministic (same correlation -> same id)", r.clientOrderId == r2.clientOrderId)
r3 = pm.build_new_order_req(ctid_trader_account_id=47758849, symbol_id=41, side="BUY", volume=100,
    limit_price=4063.00, stop_loss=4040.00, expiration_timestamp=FAR, correlation={**corr, "leg": 1})
ck("clientOrderId differs for a different correlation", r.clientOrderId != r3.clientOrderId)

r250 = pm.build_new_order_req(ctid_trader_account_id=47758849, symbol_id=41, side="SELL", volume=250,
    limit_price=4000.00, stop_loss=4010.00, expiration_timestamp=FAR, correlation=corr)
ck("volume is an INPUT (250 -> 250; NOT hard-coded 100)", r250.volume == 250 and r250.tradeSide == pb["TradeSide"].SELL)

ck("missing protective stop refused", raises(lambda: pm.build_new_order_req(ctid_trader_account_id=1,
    symbol_id=41, side="BUY", volume=100, limit_price=4063.0, stop_loss=None, expiration_timestamp=FAR, correlation=corr), ValueError))
ck("bad side refused", raises(lambda: pm.build_new_order_req(ctid_trader_account_id=1, symbol_id=41,
    side="LONG", volume=100, limit_price=4063.0, stop_loss=4040.0, expiration_timestamp=FAR, correlation=corr), ValueError))
ck("non-positive volume refused", raises(lambda: pm.build_new_order_req(ctid_trader_account_id=1, symbol_id=41,
    side="BUY", volume=0, limit_price=4063.0, stop_loss=4040.0, expiration_timestamp=FAR, correlation=corr), ValueError))

c = pm.build_close_position_req(ctid_trader_account_id=47758849, position_id=555, volume=40, owner_verified=True)
ck("close req: account + position + reduce volume set", c.ctidTraderAccountId == 47758849 and c.positionId == 555 and c.volume == 40)
ck("close refused unless ownership POSITIVELY verified",
   raises(lambda: pm.build_close_position_req(ctid_trader_account_id=1, position_id=1, volume=1, owner_verified=False), ValueError))

# ---- OFFLINE proof: no connection/transport/socket pulled in ----
ck("OFFLINE: twisted NOT imported", "twisted" not in sys.modules)
ck("OFFLINE: ctrader_open_api.client NOT imported", "ctrader_open_api.client" not in sys.modules)
ck("OFFLINE: socket NOT imported", "socket" not in sys.modules)
_src = open(os.path.join(os.path.dirname(__file__), "protobuf_mapper.py"), encoding="utf-8").read()
ck("mapper imports no Client/TcpProtocol/EndPoints", not any(x in _src for x in ("import Client", "TcpProtocol", "EndPoints", "from ctrader_open_api import")))
ck("mapper does NOT hard-code volume (passes the input through)", "r.volume = volume" in _src)

print(f"\n{_p} passed, {_f} failed")
sys.exit(1 if _f else 0)
