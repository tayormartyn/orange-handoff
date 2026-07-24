"""
READ-ONLY demo preflight (runs under .venv-ctrader). Reuses the PROVEN spot_reader connection flow
(app-auth -> account list -> SCOPE_VIEW check -> demo/account validation -> account-auth) and then
issues READ-ONLY ProtoOATraderReq (balance/isLive) + ProtoOASymbolByIdReq (XAUUSD metadata). It
sends NO order. Prints a masked JSON snapshot (never the token/secret). Zero retry; 429/error stop.
"""
from __future__ import annotations
import json
import os
import sys
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
_CE = os.path.dirname(_HERE)
_A2 = os.path.join(_CE, "ctrader_a2")
_QUOTES = os.path.join(_A2, "quotes")
_ROOT = os.path.dirname(_CE)
for p in (_HERE, _CE, _A2, _QUOTES, _ROOT):
    if p not in sys.path:
        sys.path.insert(0, p)

XAUUSD_SYMBOL_ID = 41
DEMO_LOGIN_REFERENCE = 4257941


def main():
    out = {"ok": False, "stage": None, "account": None, "symbol": None, "error": None}
    try:
        from ctrader_a1 import dotenv_loader as DL
        import token_loader
        import live_transport
        from ctrader_open_api import Client, TcpProtocol, EndPoints
        from twisted.internet import reactor, defer
        from ctrader_open_api.messages.OpenApiMessages_pb2 import (
            ProtoOAApplicationAuthReq, ProtoOAGetAccountListByAccessTokenReq, ProtoOAAccountAuthReq,
            ProtoOATraderReq, ProtoOASymbolByIdReq)
        from ctrader_a1 import scope_validator, account_validator
        import masking

        env = DL.load_ctrader_env()
        tok = token_loader.load_cached_token()
        if not tok or not tok.get("access_token"):
            out["error"] = "NO_TOKEN"; print(json.dumps(out)); return 2
        access = tok["access_token"]
        host = getattr(EndPoints, "PROTOBUF_DEMO_HOST", live_transport.DEMO_HOST)
        port = getattr(EndPoints, "PROTOBUF_PORT", live_transport.DEMO_PORT)
        client = Client(host, port, TcpProtocol)
        state = {"ctid": None, "done": False}

        def stop(err=None, stage=None):
            if err:
                out["error"] = err
            if stage:
                out["stage"] = stage
            if reactor.running:
                reactor.callLater(0, lambda: reactor.running and reactor.stop())

        @defer.inlineCallbacks
        def flow(_c):
            try:
                out["stage"] = "APP_AUTH"
                aa = ProtoOAApplicationAuthReq(); aa.clientId = env.get("CTRADER_CLIENT_ID")
                aa.clientSecret = env.get("CTRADER_CLIENT_SECRET")
                live_transport.raise_if_error(live_transport.extract_message((yield client.send(aa))), "APP_AUTH")
                out["stage"] = "ACCOUNT_LIST"
                al = ProtoOAGetAccountListByAccessTokenReq(); al.accessToken = access
                res = live_transport.extract_message((yield client.send(al)))
                live_transport.raise_if_error(res, "ACCOUNT_LIST")
                scope = live_transport.scope_from_response(res)
                is_view = scope_validator.returned_scope_is_view_only(scope)
                out["permission_scope_int"] = getattr(res, "permissionScope", None)
                out["permission_scope"] = "SCOPE_VIEW" if is_view else "SCOPE_TRADE"
                out["token_scope"] = "view-only" if is_view else "trade-capable"
                verdict = account_validator.validate_demo_selection(live_transport.parse_account_list(res))
                if verdict["status"] == "REJECTED_LIVE_ONLY":
                    stop("LIVE_ONLY", "ACCOUNT_LIST"); return
                if verdict["status"] == "NO_DEMO_ACCOUNT":
                    stop("NO_DEMO_ACCOUNT", "ACCOUNT_LIST"); return
                if len(verdict["candidates"]) != 1:
                    stop("NEEDS_HUMAN_SELECTION", "ACCOUNT_LIST"); return
                state["ctid"] = verdict["candidates"][0]
                logins = {str(getattr(a, "ctidTraderAccountId", "")): getattr(a, "traderLogin", None)
                          for a in getattr(res, "ctidTraderAccount", [])}
                if str(logins.get(state["ctid"])) != str(DEMO_LOGIN_REFERENCE):
                    stop("WRONG_ACCOUNT", "ACCOUNT_LIST"); return
                out["stage"] = "ACCOUNT_AUTH"
                ac = ProtoOAAccountAuthReq(); ac.ctidTraderAccountId = int(state["ctid"]); ac.accessToken = access
                live_transport.raise_if_error(live_transport.extract_message((yield client.send(ac))), "ACCOUNT_AUTH")
                out["stage"] = "TRADER"
                tr = ProtoOATraderReq(); tr.ctidTraderAccountId = int(state["ctid"])
                tres = live_transport.extract_message((yield client.send(tr)))
                live_transport.raise_if_error(tres, "TRADER")
                trader = getattr(tres, "trader", None)
                money_digits = getattr(trader, "moneyDigits", 2) or 2
                bal_raw = getattr(trader, "balance", None)
                balance = (bal_raw / (10 ** money_digits)) if bal_raw is not None else None
                acct_type_raw = getattr(trader, "accountType", None)
                out["account"] = {
                    "account_id_login": DEMO_LOGIN_REFERENCE,
                    "ctid_masked": masking.mask_account_id(str(state["ctid"])),
                    "is_live": bool(getattr(trader, "isLive", False)) if hasattr(trader, "isLive") else False,
                    "balance": round(balance, 2) if balance is not None else None,
                    "currency_id": getattr(trader, "depositAssetId", None),
                    "account_type_raw": acct_type_raw,
                    "account_type": {0: "HEDGED", 1: "NETTED", 2: "SPREAD_BETTING"}.get(acct_type_raw, str(acct_type_raw))}
                out["stage"] = "SYMBOL"
                sr = ProtoOASymbolByIdReq(); sr.ctidTraderAccountId = int(state["ctid"]); sr.symbolId.append(XAUUSD_SYMBOL_ID)
                sres = live_transport.extract_message((yield client.send(sr)))
                live_transport.raise_if_error(sres, "SYMBOL")
                syms = list(getattr(sres, "symbol", []))
                if syms:
                    s = syms[0]
                    out["symbol"] = {"symbol_id": XAUUSD_SYMBOL_ID,
                                     "digits": getattr(s, "digits", None),
                                     "pip_position": getattr(s, "pipPosition", None),
                                     "min_volume": getattr(s, "minVolume", None),
                                     "max_volume": getattr(s, "maxVolume", None),
                                     "step_volume": getattr(s, "stepVolume", None),
                                     "lot_size": getattr(s, "lotSize", None),
                                     "min_stop_distance": getattr(s, "minStopDistance", None)}
                # READ-ONLY expected-margin request (NOT an order) for XAUUSD volume 1200 (=0.12 lot)
                out["stage"] = "EXPECTED_MARGIN"
                try:
                    from ctrader_open_api.messages.OpenApiMessages_pb2 import ProtoOAExpectedMarginReq
                    em = ProtoOAExpectedMarginReq(); em.ctidTraderAccountId = int(state["ctid"])
                    em.symbolId = XAUUSD_SYMBOL_ID; em.volume.append(1200)   # volume is a repeated field
                    emres = live_transport.extract_message((yield client.send(em)))
                    live_transport.raise_if_error(emres, "EXPECTED_MARGIN")
                    margins = list(getattr(emres, "margin", []))
                    out["expected_margin"] = {"healthy": True, "money_digits": getattr(emres, "moneyDigits", 2),
                                              "entries": [{"buy": getattr(m, "buyMargin", None),
                                                           "sell": getattr(m, "sellMargin", None)} for m in margins]}
                except Exception as _e:                 # noqa: BLE001
                    out["expected_margin"] = {"healthy": False, "reason": type(_e).__name__}
                out["ok"] = True
                stop(None, "DONE")
            except Exception as e:                      # noqa: BLE001
                stop(type(e).__name__, out["stage"])

        client.setConnectedCallback(flow)
        client.setDisconnectedCallback(lambda *_a, **_k: None)
        client.startService()
        reactor.callLater(40, lambda: stop("HARD_TIMEOUT", out["stage"]))
        reactor.run()
    except Exception as e:                              # noqa: BLE001
        out["error"] = type(e).__name__
    print(json.dumps(out, default=str))
    return 0 if out["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
