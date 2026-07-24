"""The ONLY cTrader operations this tool may perform - a fixed WHITELIST of view-only read
requests. There is NO generic send, NO arbitrary message type, NO raw-payload input, and NO
trade-capable request class anywhere in this module (a test asserts their absence).

Each builder LAZILY imports ONLY its own specific message class from ctrader_open_api, so the
package is importable (for Phase-1 static proof) without the protobuf library, and no broad
'import * from messages' ever pulls trade classes into scope.
"""

# The seven authorised read request/event types, by name (used by the absence/whitelist tests).
ALLOWED_READ_MESSAGES = (
    "ProtoOAApplicationAuthReq",              # application auth
    "ProtoOAGetAccountListByAccessTokenReq",  # account enumeration
    "ProtoOAAccountAuthReq",                  # demo-account session auth
    "ProtoOATraderReq",                       # account details (isLive / environment)
    "ProtoOASymbolsListReq",                  # symbol list
    "ProtoOASymbolByIdReq",                   # XAUUSD metadata
    "ProtoOAHeartbeatEvent",                  # heartbeat
)


def build_application_auth(client_id, client_secret):
    from ctrader_open_api.messages.OpenApiMessages_pb2 import ProtoOAApplicationAuthReq
    r = ProtoOAApplicationAuthReq()
    r.clientId, r.clientSecret = client_id, client_secret
    return r


def build_account_list(access_token):
    from ctrader_open_api.messages.OpenApiMessages_pb2 import ProtoOAGetAccountListByAccessTokenReq
    r = ProtoOAGetAccountListByAccessTokenReq()
    r.accessToken = access_token
    return r


def build_account_auth(ctid_trader_account_id, access_token):
    from ctrader_open_api.messages.OpenApiMessages_pb2 import ProtoOAAccountAuthReq
    r = ProtoOAAccountAuthReq()
    r.ctidTraderAccountId, r.accessToken = ctid_trader_account_id, access_token
    return r


def build_trader(ctid_trader_account_id):
    from ctrader_open_api.messages.OpenApiMessages_pb2 import ProtoOATraderReq
    r = ProtoOATraderReq()
    r.ctidTraderAccountId = ctid_trader_account_id
    return r


def build_symbols_list(ctid_trader_account_id):
    from ctrader_open_api.messages.OpenApiMessages_pb2 import ProtoOASymbolsListReq
    r = ProtoOASymbolsListReq()
    r.ctidTraderAccountId = ctid_trader_account_id
    return r


def build_symbol_by_id(ctid_trader_account_id, symbol_id):
    from ctrader_open_api.messages.OpenApiMessages_pb2 import ProtoOASymbolByIdReq
    r = ProtoOASymbolByIdReq()
    r.ctidTraderAccountId = ctid_trader_account_id
    r.symbolId.append(symbol_id)
    return r


def build_heartbeat():
    from ctrader_open_api.messages.OpenApiMessages_pb2 import ProtoOAHeartbeatEvent
    return ProtoOAHeartbeatEvent()
