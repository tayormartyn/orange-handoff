"""Offline tests for live_transport pure helpers (duck-typed mocks; no connection).
The build_requests() protobuf check runs only under .venv-ctrader (skipped if lib absent)."""
from __future__ import annotations
import importlib.util
import os
import shutil
import sys
import types

_HERE = os.path.dirname(os.path.abspath(__file__))
_A2 = os.path.dirname(_HERE)
_CE = os.path.dirname(_A2)
_ROOT = os.path.dirname(_CE)
for p in (_A2, _CE, _ROOT):
    if p not in sys.path:
        sys.path.insert(0, p)

import live_transport as LT
from errors import RateLimited429


def _ns(**k):
    return types.SimpleNamespace(**k)


def test_detect_rate_limit():
    assert LT.detect_rate_limit(_ns(errorCode="RATE_LIMIT_EXCEEDED")) is True
    assert LT.detect_rate_limit(_ns(errorCode="TOO_MANY_REQUESTS")) is True
    assert LT.detect_rate_limit(_ns(errorCode="CH_ACCESS_TOKEN_INVALID")) is False
    assert LT.detect_rate_limit(_ns(balance=1)) is False
    try:
        LT.raise_if_rate_limited(_ns(errorCode="429_TOO_MANY"), "GET_ACCOUNT_LIST")
        assert False
    except RateLimited429 as e:
        assert e.stage == "GET_ACCOUNT_LIST"


def test_parse_account_list_and_islive():
    res = _ns(ctidTraderAccount=[_ns(ctidTraderAccountId=20000012345678, isLive=False),
                                 _ns(ctidTraderAccountId=99, isLive=True)])
    accts = LT.parse_account_list(res)
    assert accts == [{"account_id": "20000012345678", "isLive": False},
                     {"account_id": "99", "isLive": True}]


def test_parse_trader_balance_scaled():
    res = _ns(trader=_ns(balance=1000000, moneyDigits=2, depositAssetId=8, isLive=False))
    info = LT.parse_trader(res)
    assert info["balance"] == 10000.0 and info["currency_asset_id"] == 8
    assert info["isLive"] is False and info["server"] == LT.DEMO_HOST


def test_find_symbol_and_spec():
    sl = _ns(symbol=[_ns(symbolName="EURUSD", symbolId=1), _ns(symbolName="XAUUSD", symbolId=41)])
    assert LT.find_symbol_id(sl, "XAUUSD") == 41
    assert LT.find_symbol_id(sl, "NOPE") is None
    spec = LT.parse_symbol_spec(_ns(symbol=[_ns(symbolId=41, digits=2, pipPosition=-1,
                                                lotSize=100, minVolume=1)]))
    assert spec["digits"] == 2 and spec["symbol_id"] == 41


def test_effective_scope_view_only():
    assert LT.effective_scope() == "SCOPE_VIEW"      # config default 'accounts' -> view-only


def test_no_order_types_declared():
    joined = " ".join(LT.ALLOWED_REQUEST_TYPES)
    for tok in ("NewOrder", "CancelOrder", "AmendOrder", "ClosePosition"):
        assert tok not in joined


def test_build_requests_protobuf_fields_venv_only():
    """Under .venv-ctrader this proves the real protobuf field names exist; skipped otherwise."""
    if importlib.util.find_spec("ctrader_open_api") is None:
        print("  (skipped: ctrader_open_api not in this interpreter — run under .venv-ctrader)")
        return
    reqs = LT.build_requests()
    assert set(reqs) == {"app_auth", "account_list", "account_auth", "trader", "symbols_list",
                         "symbol_by_id"}
    assert reqs["app_auth"].clientId == "x" and reqs["account_list"].accessToken == "t"
    assert reqs["account_auth"].ctidTraderAccountId == 1
    assert list(reqs["symbol_by_id"].symbolId) == [41]


# ---- A2 NoDemoAccount diagnosis: endpoint, authoritative scope, filtering proofs ----
from ctrader_a1 import scope_validator as SV, account_validator as AV   # noqa: E402


def _acct_res(*accounts, scope=0):
    return _ns(permissionScope=scope,
               ctidTraderAccount=[_ns(ctidTraderAccountId=a[0], isLive=a[1]) for a in accounts])


def test_reader_uses_demo_endpoint():
    assert LT.DEMO_HOST == "demo.ctraderapi.com" and LT.DEMO_PORT == 5035
    src = open(os.path.join(_A2, "live_transport.py"), encoding="utf-8").read()
    assert "PROTOBUF_DEMO_HOST" in src and "PROTOBUF_LIVE_HOST" not in src   # demo only, never live


def test_permission_scope_authoritative_from_response():
    assert LT.scope_from_response(_ns(permissionScope=0)) == "SCOPE_VIEW"
    assert LT.scope_from_response(_ns(permissionScope=1)) == "SCOPE_TRADE"
    assert LT.scope_from_response(_ns(permissionScope=7)) == "SCOPE_UNKNOWN"
    assert LT.scope_from_response(_ns()) == "SCOPE_UNKNOWN"                  # absent -> not view
    assert SV.returned_scope_is_view_only(LT.scope_from_response(_ns(permissionScope=0))) is True
    for bad in (1, 7):
        assert SV.returned_scope_is_view_only(LT.scope_from_response(_ns(permissionScope=bad))) is False


def test_empty_account_list_stays_no_demo():
    accts = LT.parse_account_list(_acct_res(scope=0))          # zero accounts
    assert accts == []
    assert AV.validate_demo_selection(accts)["status"] == "NO_DEMO_ACCOUNT"


def test_demo_account_survives_filtering():
    accts = LT.parse_account_list(_acct_res((20000012345678, False), scope=0))
    v = AV.validate_demo_selection(accts)
    assert v["status"] == "SINGLE_DEMO_CANDIDATE" and v["candidates"] == ["20000012345678"]


def test_live_account_rejected():
    v = AV.validate_demo_selection(LT.parse_account_list(_acct_res((99, True), scope=0)))
    assert v["status"] == "REJECTED_LIVE_ONLY" and v["candidates"] == []


def test_mixed_returns_only_demo():
    v = AV.validate_demo_selection(
        LT.parse_account_list(_acct_res((99, True), (20000012345678, False), scope=0)))
    assert v["candidates"] == ["20000012345678"]


def test_diag_log_masked():
    import tempfile
    tmp = tempfile.mkdtemp(prefix="a2diag_")
    try:
        p = os.path.join(tmp, "data", "ctrader_a2_diag.log")
        LT.write_diag(0, "SCOPE_VIEW", path=p)
        LT.write_diag(3, "SCOPE_TRADE", path=p)
        lines = open(p, encoding="utf-8").read().splitlines()
        assert len(lines) == 2                                   # append-only, one line each
        assert "account_count=0 permission_scope=SCOPE_VIEW" in lines[0]
        assert "account_count=3 permission_scope=SCOPE_TRADE" in lines[1]
        # masked: no account ids, tokens, or balances anywhere in the log
        blob = "\n".join(lines)
        for forbidden in ("access_token", "accessToken", "20000012345678", "balance", "traderLogin"):
            assert forbidden not in blob
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


class _AcctListRes:                          # mimics ProtoOAGetAccountListByAccessTokenRes
    payloadType = 2150
    permissionScope = 0
    ctidTraderAccount = (1, 2, 3)            # length only is used; contents never read into the log


class _AppAuthRes:                           # a different message lacking both fields
    payloadType = 2101


# rename so type(instance).__name__ matches the real protobuf class names
_AcctListRes.__name__ = "ProtoOAGetAccountListByAccessTokenRes"
_AppAuthRes.__name__ = "ProtoOAApplicationAuthRes"


def test_describe_response_masked_structure():
    d = LT.describe_response(_AcctListRes())
    assert d["msg"] == "ProtoOAGetAccountListByAccessTokenRes" and d["payloadType"] == 2150
    assert d["ctid_count"] == 3 and d["permission_scope_int"] == 0        # length + raw enum int only
    d2 = LT.describe_response(_AppAuthRes())                              # wrong message type
    assert d2["msg"] == "ProtoOAApplicationAuthRes"
    assert d2["ctid_count"] is None and d2["permission_scope_int"] is None


def test_diag_log_with_descriptor_masked():
    import tempfile
    tmp = tempfile.mkdtemp(prefix="a2diag2_")
    try:
        p = os.path.join(tmp, "data", "ctrader_a2_diag.log")
        desc = LT.describe_response(_AcctListRes())
        LT.write_diag(desc["ctid_count"], "SCOPE_VIEW", descriptor=desc, path=p)
        line = open(p, encoding="utf-8").read().strip()
        assert "account_count=3 permission_scope=SCOPE_VIEW" in line
        assert "msg=ProtoOAGetAccountListByAccessTokenRes" in line
        assert "payloadType=2150" in line and "ctid_count=3" in line and "permission_scope_int=0" in line
        # masked: no ids/tokens/balances/logins in the enriched line
        for forbidden in ("access_token", "accessToken", "20000012345678", "balance",
                          "traderLogin", "ctidTraderAccountId"):
            assert forbidden not in line
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_extract_message_passthrough_non_envelope():
    # a non-ProtoMessage (already-extracted message or a mock) passes through unchanged
    m = _ns(permissionScope=0, ctidTraderAccount=[1])
    assert LT.extract_message(m) is m


def test_extract_message_unwraps_envelope_venv_only():
    """PROOF: a real ProtoOAGetAccountListByAccessTokenRes wrapped in a ProtoMessage envelope
    extracts back to a populated inner message; and raise_if_error sees the REAL type, not
    'ProtoMessage'. Runs under .venv-ctrader; skipped otherwise."""
    if importlib.util.find_spec("ctrader_open_api") is None:
        print("  (skipped: ctrader_open_api not in this interpreter — run under .venv-ctrader)")
        return
    import ctrader_open_api.messages.OpenApiMessages_pb2 as MSG
    import ctrader_open_api.messages.OpenApiCommonMessages_pb2 as COM
    from errors import BrokerError

    # --- account-list response wrapped as an envelope (as client.send actually returns) ---
    inner = MSG.ProtoOAGetAccountListByAccessTokenRes()
    inner.accessToken = "dummy-token"                           # required field (response echoes it)
    inner.permissionScope = 0                                   # SCOPE_VIEW
    a = inner.ctidTraderAccount.add(); a.ctidTraderAccountId = 4257941; a.isLive = False
    env = COM.ProtoMessage(); env.payloadType = inner.payloadType; env.payload = inner.SerializeToString()
    assert type(env).__name__ == "ProtoMessage"                 # pre-fix: this is what we saw

    out = LT.extract_message(env)
    assert type(out).__name__ == "ProtoOAGetAccountListByAccessTokenRes"   # now the real message
    assert len(out.ctidTraderAccount) == 1 and out.permissionScope == 0
    assert LT.scope_from_response(out) == "SCOPE_VIEW"          # authoritative scope now readable
    d = LT.describe_response(out)
    assert d["msg"] == "ProtoOAGetAccountListByAccessTokenRes" and d["ctid_count"] == 1 \
        and d["permission_scope_int"] == 0
    assert "dummy-token" not in str(d)                         # echoed accessToken never in descriptor
    assert LT.parse_account_list(out) == [{"account_id": "4257941", "isLive": False}]

    # --- an ERROR response wrapped as an envelope: raise_if_error must see the real error type ---
    err = MSG.ProtoOAErrorRes(); err.errorCode = "SOME_ERROR"
    eenv = COM.ProtoMessage(); eenv.payloadType = err.payloadType; eenv.payload = err.SerializeToString()
    eout = LT.extract_message(eenv)
    assert "Error" in type(eout).__name__                        # not 'ProtoMessage'
    raised = False
    try:
        LT.raise_if_error(eout, "GET_ACCOUNT_LIST")
    except BrokerError:
        raised = True
    assert raised                                               # error now correctly detected
