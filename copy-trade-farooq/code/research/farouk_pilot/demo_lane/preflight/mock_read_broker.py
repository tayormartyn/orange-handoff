"""MOCK read-only broker for DRY-RUN proof of the preflight logic. No network, no order
methods whatsoever (deliberately — it is architecturally incapable of placing/closing).
It exposes ONLY account_info() and symbol_meta(), the two read surfaces the preflight uses.

Configurable to exercise every verification branch (live account, wrong id, trading scope
granted, disabled symbol, incomplete metadata)."""


class MockReadOnlyBroker:
    def __init__(self, account=None, symbol=None):
        self.account = account or {
            "endpoint": "demo.ctraderapi.com",
            "isLive": False,
            "ctidTraderAccountId": 1_000_001,
            "broker_environment": "PEPPERSTONE_DEMO",
            "permissionScope": "SCOPE_VIEW",           # view-only granted (the good case)
            "accountType": "HEDGED",                    # present but NEVER used as live/demo test
        }
        self.symbol = symbol or {
            "symbolId": 41,
            "symbolName": "XAUUSD",
            "enabled": True,
            "tradingStatus": "TRADING",
            "digits": 2,
            "pipPosition": 1,
            "tickSize": 0.01,
            "lotSize": 100,
            "minVolume": 1,
            "maxVolume": 10000,
            "stepVolume": 1,
            "minStopDistance": 1.0,
            "minStopDistanceUnit": "PRICE",
            "session": {"status": "OPEN", "windows": [["00:00", "23:59"]]},
        }

    def account_info(self):
        return dict(self.account)

    def symbol_meta(self, symbol_name="XAUUSD"):
        return dict(self.symbol)

    # NOTE: there is intentionally NO place_*, close_*, cancel_*, or modify_* method here.
