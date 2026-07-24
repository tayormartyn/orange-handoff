"""
Real cTrader Open API transport (Twisted/protobuf) — VIEW-ONLY. FINALISED but NOT RUN here.

Runs only under the isolated .venv-ctrader at the separately-authorised connection step. It is
import-safe elsewhere (ctrader_open_api / protobuf are imported lazily inside the reactor fn and
the request builders). ONE Twisted reactor lifecycle per invocation.

Request types used (VIEW-ONLY — no order type anywhere):
  ProtoOAApplicationAuthReq · ProtoOAGetAccountListByAccessTokenReq · ProtoOAAccountAuthReq
  ProtoOATraderReq · ProtoOASymbolsListReq · ProtoOASymbolByIdReq
Endpoint: demo host only. HTTP 429 -> raise RateLimited429 and STOP (no retry, no reconnect).

Security decisions (scope view-only, isLive reject, human selection, masking) are single-sourced
through the reviewed ctrader_a1 validators; this module only adds Twisted I/O + response parsing.
"""
from __future__ import annotations
import os
import time

import sys as _sys
_HERE = os.path.dirname(os.path.abspath(__file__))
_CE = os.path.dirname(_HERE)
_PROJECT_ROOT = os.path.dirname(_CE)
for p in (_HERE, _CE):
    if p not in _sys.path:
        _sys.path.insert(0, p)
DIAG_LOG = os.path.join(_PROJECT_ROOT, "data", "ctrader_a2_diag.log")
from errors import (RateLimited429, ScopeRejected, LiveAccountRejected, NoDemoAccount,
                    TokenMissing, BrokerError)
import masking
from ctrader_a1 import scope_validator, account_validator

DEMO_HOST = "demo.ctraderapi.com"
DEMO_PORT = 5035
ALLOWED_REQUEST_TYPES = (
    "ProtoOAApplicationAuthReq", "ProtoOAGetAccountListByAccessTokenReq",
    "ProtoOAAccountAuthReq", "ProtoOATraderReq", "ProtoOASymbolsListReq", "ProtoOASymbolByIdReq",
)


# ---------------------------------------------------------------- pure, offline-testable helpers
def detect_rate_limit(res):
    """Return True if a response is a rate-limit/429/too-many-requests error. Duck-typed."""
    name = type(res).__name__
    if "Error" not in name and "error" not in name:
        code = getattr(res, "errorCode", None)
    else:
        code = getattr(res, "errorCode", None) or getattr(res, "description", None)
    c = str(code or "").upper()
    return ("429" in c) or ("RATE" in c and "LIMIT" in c) or ("TOO_MANY" in c) \
        or ("BLOCKED" in c and "RATE" in c)


def raise_if_rate_limited(res, stage):
    if detect_rate_limit(res):
        raise RateLimited429(stage=stage)


def raise_if_error(res, stage):
    """429 first (stop), then any other broker error response -> BrokerError(stage, code)."""
    raise_if_rate_limited(res, stage)
    name = type(res).__name__
    if "ErrorRes" in name or name.endswith("Error"):
        from errors import BrokerError
        raise BrokerError(stage=stage, code=str(getattr(res, "errorCode", "UNKNOWN")))


def parse_account_list(res):
    """ProtoOAGetAccountListByAccessTokenRes -> [{account_id, isLive}]. Duck-typed."""
    out = []
    for a in (getattr(res, "ctidTraderAccount", None) or []):
        out.append({"account_id": str(getattr(a, "ctidTraderAccountId", "")),
                    "isLive": bool(getattr(a, "isLive", False))})
    return out


def parse_trader(res):
    """ProtoOATraderRes -> {balance, currency_asset_id, isLive, broker, server}. Duck-typed."""
    tr = getattr(res, "trader", res)
    money_digits = getattr(tr, "moneyDigits", 2) or 2
    bal_raw = getattr(tr, "balance", None)
    balance = (bal_raw / (10 ** money_digits)) if bal_raw is not None else None
    return {"balance": balance,
            "currency_asset_id": getattr(tr, "depositAssetId", None),
            "isLive": getattr(tr, "isLive", None),
            "broker": getattr(tr, "brokerName", None),
            "server": DEMO_HOST}


def find_symbol_id(res, symbol_name):
    for s in (getattr(res, "symbol", None) or []):
        if str(getattr(s, "symbolName", "")).upper() == symbol_name.upper():
            return getattr(s, "symbolId", None)
    return None


def parse_symbol_spec(res):
    syms = getattr(res, "symbol", None) or []
    if not syms:
        return None
    s = syms[0]
    return {"symbol_id": getattr(s, "symbolId", None), "digits": getattr(s, "digits", None),
            "pip_position": getattr(s, "pipPosition", None), "lot_size": getattr(s, "lotSize", None),
            "min_volume": getattr(s, "minVolume", None)}


def describe_response(res):
    """MASKED structural descriptor of a response message — class name, payloadType, and (only
    if present) the raw ctidTraderAccount LENGTH and permissionScope INT. NEVER account ids,
    tokens, balances, logins, or any credential."""
    d = {"msg": type(res).__name__, "payloadType": getattr(res, "payloadType", None),
         "ctid_count": None, "permission_scope_int": None}
    if hasattr(res, "ctidTraderAccount"):
        try:
            d["ctid_count"] = len(res.ctidTraderAccount)      # length only — never the ids
        except (TypeError, AttributeError):
            d["ctid_count"] = None
    ps = getattr(res, "permissionScope", None)
    if isinstance(ps, int):
        d["permission_scope_int"] = ps                        # raw enum int (0/1) — not a secret
    return d


def write_diag(account_count, scope, descriptor=None, path=None):
    """Append ONE masked artifact line: UTC ts + account_count + permission_scope, and (when a
    descriptor is supplied) msg class name + payloadType + ctid_count + permission_scope_int.
    NEVER writes account ids, tokens, balances, logins, or any credential."""
    path = path or DIAG_LOG
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        extra = ""
        if descriptor:
            extra = (f" msg={descriptor.get('msg')} payloadType={descriptor.get('payloadType')}"
                     f" ctid_count={descriptor.get('ctid_count')}"
                     f" permission_scope_int={descriptor.get('permission_scope_int')}")
        with open(path, "a", encoding="utf-8") as f:
            f.write(f"{ts} account_count={int(account_count)} permission_scope={scope}{extra}\n")
    except OSError:
        pass


def scope_from_response(res):
    """AUTHORITATIVE: read permissionScope directly from the account-list response.
    ProtoOAClientPermissionScope: SCOPE_VIEW=0, SCOPE_TRADE=1. Missing/absent/other -> not view.
    (proto2: use HasField to distinguish a genuinely-absent field from the 0 default.)"""
    try:
        if hasattr(res, "HasField") and not res.HasField("permissionScope"):
            return "SCOPE_MISSING"
    except (ValueError, TypeError):
        pass
    v = getattr(res, "permissionScope", None)
    return {0: "SCOPE_VIEW", 1: "SCOPE_TRADE"}.get(v, "SCOPE_UNKNOWN")


def effective_scope():
    """View-only scope guarantee: our auth authority (oauth_scope) only ever emits 'accounts'
    (never 'trading'); config default is 'accounts'. -> SCOPE_VIEW; anything else -> unknown."""
    try:
        from broker_readonly.oauth_scope import OAUTH_ACCOUNTS
        import ctrader_config as cfg
        return "SCOPE_VIEW" if cfg.DEFAULT_SCOPE == OAUTH_ACCOUNTS else "SCOPE_UNKNOWN"
    except Exception:
        return "SCOPE_UNKNOWN"


# ---------------------------------------------------------------- request builders (venv/protobuf)
def build_requests():
    """Construct the 6 VIEW-ONLY request objects (verifies the protobuf field names exist).
    Lazy import: requires the venv. Returns the request instances (no send)."""
    from ctrader_open_api.messages.OpenApiMessages_pb2 import (
        ProtoOAApplicationAuthReq, ProtoOAGetAccountListByAccessTokenReq, ProtoOAAccountAuthReq,
        ProtoOATraderReq, ProtoOASymbolsListReq, ProtoOASymbolByIdReq)
    aa = ProtoOAApplicationAuthReq(); aa.clientId = "x"; aa.clientSecret = "y"
    al = ProtoOAGetAccountListByAccessTokenReq(); al.accessToken = "t"
    ac = ProtoOAAccountAuthReq(); ac.ctidTraderAccountId = 1; ac.accessToken = "t"
    tr = ProtoOATraderReq(); tr.ctidTraderAccountId = 1
    sl = ProtoOASymbolsListReq(); sl.ctidTraderAccountId = 1
    sy = ProtoOASymbolByIdReq(); sy.ctidTraderAccountId = 1; sy.symbolId.append(41)
    return {"app_auth": aa, "account_list": al, "account_auth": ac, "trader": tr,
            "symbols_list": sl, "symbol_by_id": sy}


def _sanitise_error(e):
    return f"{type(e).__name__}: {masking.mask_secret()}" if isinstance(e, (RateLimited429,)) \
        else f"{type(e).__name__}"


def extract_message(res):
    """Unwrap a ProtoMessage envelope to its typed inner message (via Protobuf.extract), so
    describe/parse/error-check see the REAL message (e.g. ProtoOAGetAccountListByAccessTokenRes /
    ProtoOAErrorRes), not the wrapper. Non-envelopes (already extracted, or test mocks) pass
    through unchanged."""
    if type(res).__name__ != "ProtoMessage":
        return res
    try:
        from ctrader_open_api import Protobuf
        return Protobuf.extract(res)
    except Exception:
        return res


# ---------------------------------------------------------------- ONE reactor lifecycle (unrun offline)
def connect_and_read(access_token, *, client_id, client_secret, selected_account_id=None,
                     timeout_seconds=30):
    """ONE Twisted reactor lifecycle: connect(demo TLS) -> app auth -> account list -> require
    SCOPE_VIEW -> reject isLive=true -> (single demo or explicit selection; else stop for human)
    -> account auth -> read balance/currency/broker/server + XAUUSD spec -> clean disconnect.

    NO retry. HTTP 429 -> stop immediately. Runs ONLY at the authorised connection step (venv)."""
    if not access_token:
        raise TokenMissing("connect_and_read requires an already-cached access token")
    from ctrader_open_api import Client, TcpProtocol, EndPoints
    from twisted.internet import reactor, defer
    from ctrader_open_api.messages.OpenApiMessages_pb2 import (
        ProtoOAApplicationAuthReq, ProtoOAGetAccountListByAccessTokenReq, ProtoOAAccountAuthReq,
        ProtoOATraderReq, ProtoOASymbolsListReq, ProtoOASymbolByIdReq)

    host = getattr(EndPoints, "PROTOBUF_DEMO_HOST", DEMO_HOST)
    port = getattr(EndPoints, "PROTOBUF_PORT", DEMO_PORT)
    result = {"status": None, "error": None}
    client = Client(host, port, TcpProtocol)

    @defer.inlineCallbacks
    def flow(_conn):
        try:
            aa = ProtoOAApplicationAuthReq(); aa.clientId = client_id; aa.clientSecret = client_secret
            aares = extract_message((yield client.send(aa)))
            raise_if_error(aares, "APPLICATION_AUTH")
            al = ProtoOAGetAccountListByAccessTokenReq(); al.accessToken = access_token
            res = extract_message((yield client.send(al)))
            # Capture the response's identity FIRST — before any error/scope gate — so the diag
            # artifact records what message actually came back even if it's the wrong type.
            desc = describe_response(res)             # masked: msg class, payloadType, ctid_count, scope int
            scope = scope_from_response(res)          # AUTHORITATIVE per-response permissionScope
            account_count = desc["ctid_count"] if desc["ctid_count"] is not None \
                else len(parse_account_list(res))
            write_diag(account_count, scope, descriptor=desc)   # conclusive masked artifact
            result["account_count"] = account_count
            result["permission_scope"] = scope
            result["response_msg"] = desc["msg"]
            result["response_payload_type"] = desc["payloadType"]
            raise_if_error(res, "GET_ACCOUNT_LIST")
            if not scope_validator.returned_scope_is_view_only(scope):
                raise ScopeRejected(f"returned permissionScope is not view-only: {scope}")
            raw_accounts = parse_account_list(res)
            verdict = account_validator.validate_demo_selection(raw_accounts)
            if verdict["status"] == "REJECTED_LIVE_ONLY":
                raise LiveAccountRejected("only isLive=true accounts present")
            if verdict["status"] == "NO_DEMO_ACCOUNT":
                raise NoDemoAccount("no isLive=false demo account")
            demo_ids = verdict["candidates"]
            chosen = selected_account_id
            if chosen is None:
                if len(demo_ids) == 1:
                    chosen = demo_ids[0]
                else:
                    result.update(status="NEEDS_HUMAN_SELECTION",
                                  demo_candidates=[masking.mask_account_id(c) for c in demo_ids],
                                  raw_candidate_ids=list(demo_ids))
                    return
            if chosen not in demo_ids:
                raise LiveAccountRejected("selected account is not a verified demo candidate")

            ac = ProtoOAAccountAuthReq(); ac.ctidTraderAccountId = int(chosen)
            ac.accessToken = access_token
            acres = extract_message((yield client.send(ac)))
            raise_if_error(acres, "ACCOUNT_AUTH")
            tr = ProtoOATraderReq(); tr.ctidTraderAccountId = int(chosen)
            trres = extract_message((yield client.send(tr))); raise_if_error(trres, "ACCOUNT_INFO")
            info = parse_trader(trres)
            if info.get("isLive") is True:
                raise LiveAccountRejected("selected account reports isLive=true")
            sl = ProtoOASymbolsListReq(); sl.ctidTraderAccountId = int(chosen)
            slres = extract_message((yield client.send(sl))); raise_if_error(slres, "SYMBOL")
            sid = find_symbol_id(slres, "XAUUSD")
            spec = None
            if sid is not None:
                sy = ProtoOASymbolByIdReq(); sy.ctidTraderAccountId = int(chosen)
                sy.symbolId.append(sid)
                syres = extract_message((yield client.send(sy))); raise_if_error(syres, "SYMBOL")
                spec = parse_symbol_spec(syres)
            result.update(status="READ_OK", account_id_masked=masking.mask_account_id(chosen),
                          balance=info.get("balance"), currency_asset_id=info.get("currency_asset_id"),
                          broker=info.get("broker"), server=info.get("server"),
                          xauusd={"available": spec is not None, **(spec or {})})
        except RateLimited429 as e:
            result.update(status="RATE_LIMITED_429", stage=e.stage)   # STOP — no retry
        except BrokerError as e:
            result.update(status="BROKER_ERROR", stage=e.stage, code=e.code)  # STOP — no retry
        except Exception as e:                                        # noqa: BLE001
            result.update(status="ERROR", error=_sanitise_error(e))
        finally:
            if reactor.running:
                reactor.stop()

    client.setConnectedCallback(flow)
    client.setDisconnectedCallback(lambda *_a: None)
    client.startService()
    reactor.callLater(timeout_seconds, lambda: reactor.running and reactor.stop())  # no hang
    reactor.run()                                                    # ONE lifecycle
    return result
