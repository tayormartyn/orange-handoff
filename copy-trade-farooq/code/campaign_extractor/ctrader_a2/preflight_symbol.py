"""VIEW-ONLY XAUUSD symbol-metadata read against the PINNED demo account (no order, no select).

Reuses the reviewed ctrader_a2 helpers + ctrader_a1 validators. ONE reactor lifecycle:
    connect(demo TLS) -> app auth -> GetAccountList
      -> AUTHORITATIVE permissionScope gate (SCOPE_VIEW else stop)
      -> confirm the PINNED account (allowlist) is present + isLive==False, account auth it
      -> SymbolsList -> resolve 'XAUUSD' EXACT + UNAMBIGUOUS (exactly one) else stop
      -> SymbolById -> read digits/pip/lotSize/min|max|stepVolume/SL-TP-GSL distances+unit/
         tradingMode(session)/schedule
Returns raw protocol values only. Presentation + candidate conversions are done by the caller;
NOTHING is auto-selected or ratified. Runs ONLY under .venv-ctrader with ORANGE_PREFLIGHT_CONNECT=1.
"""
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_CE = os.path.dirname(_HERE)
_ROOT = os.path.dirname(_CE)
for _p in (_HERE, _CE, _ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from errors import RateLimited429, BrokerError, TokenMissing        # noqa: E402
import live_transport as lt                                          # noqa: E402
from ctrader_a1 import scope_validator                               # noqa: E402


def _enum_label(msg_cls, field, value):
    try:
        return msg_cls.DESCRIPTOR.fields_by_name[field].enum_type.values_by_number[value].name
    except Exception:
        return None


def read_xauusd(access_token, pinned_ctid, *, client_id, client_secret, timeout_seconds=40):
    if not access_token:
        raise TokenMissing("need an access token")
    from ctrader_open_api import Client, TcpProtocol, EndPoints
    from twisted.internet import reactor, defer
    from ctrader_open_api.messages.OpenApiMessages_pb2 import (
        ProtoOAApplicationAuthReq, ProtoOAGetAccountListByAccessTokenReq, ProtoOAAccountAuthReq,
        ProtoOASymbolsListReq, ProtoOASymbolByIdReq)
    from ctrader_open_api.messages.OpenApiModelMessages_pb2 import ProtoOASymbol

    host = getattr(EndPoints, "PROTOBUF_DEMO_HOST", lt.DEMO_HOST)
    port = getattr(EndPoints, "PROTOBUF_PORT", lt.DEMO_PORT)
    result = {"status": None}
    client = Client(host, port, TcpProtocol)

    @defer.inlineCallbacks
    def flow(_conn):
        try:
            aa = ProtoOAApplicationAuthReq(); aa.clientId = client_id; aa.clientSecret = client_secret
            aares = lt.extract_message((yield client.send(aa))); lt.raise_if_error(aares, "APPLICATION_AUTH")

            al = ProtoOAGetAccountListByAccessTokenReq(); al.accessToken = access_token
            res = lt.extract_message((yield client.send(al))); lt.raise_if_error(res, "GET_ACCOUNT_LIST")
            scope = lt.scope_from_response(res)
            result["permission_scope"] = scope
            if not scope_validator.returned_scope_is_view_only(scope):
                result.update(status="SCOPE_REJECTED"); return
            accts = {int(getattr(a, "ctidTraderAccountId", 0)): bool(getattr(a, "isLive", False))
                     for a in (getattr(res, "ctidTraderAccount", None) or [])}
            if pinned_ctid not in accts:
                result.update(status="PINNED_ACCOUNT_NOT_IN_LIST"); return
            if accts[pinned_ctid] is not False:
                result.update(status="PINNED_ACCOUNT_ISLIVE_TRUE"); return

            ac = ProtoOAAccountAuthReq(); ac.ctidTraderAccountId = pinned_ctid; ac.accessToken = access_token
            acres = lt.extract_message((yield client.send(ac))); lt.raise_if_error(acres, "ACCOUNT_AUTH")

            sl = ProtoOASymbolsListReq(); sl.ctidTraderAccountId = pinned_ctid
            slres = lt.extract_message((yield client.send(sl))); lt.raise_if_error(slres, "SYMBOL_LIST")
            exact = [s for s in (getattr(slres, "symbol", None) or [])
                     if str(getattr(s, "symbolName", "")).upper() == "XAUUSD"]
            result["xauusd_exact_match_count"] = len(exact)
            if len(exact) != 1:
                result.update(status="XAUUSD_AMBIGUOUS_OR_MISSING",
                              candidates=[str(getattr(s, "symbolName", "")) for s in
                                          (getattr(slres, "symbol", None) or [])
                                          if "XAUUSD" in str(getattr(s, "symbolName", "")).upper()])
                return
            sid = getattr(exact[0], "symbolId", None)

            sy = ProtoOASymbolByIdReq(); sy.ctidTraderAccountId = pinned_ctid; sy.symbolId.append(sid)
            syres = lt.extract_message((yield client.send(sy))); lt.raise_if_error(syres, "SYMBOL_BY_ID")
            syms = getattr(syres, "symbol", None) or []
            if not syms:
                result.update(status="SYMBOL_DETAIL_EMPTY"); return
            s = syms[0]
            result.update(
                status="READ_OK",
                symbol_id=getattr(s, "symbolId", None),
                symbol_name="XAUUSD",
                digits=getattr(s, "digits", None),
                pip_position=getattr(s, "pipPosition", None),
                lot_size=getattr(s, "lotSize", None),
                min_volume=getattr(s, "minVolume", None),
                max_volume=getattr(s, "maxVolume", None),
                step_volume=getattr(s, "stepVolume", None),
                sl_distance=getattr(s, "slDistance", None),
                tp_distance=getattr(s, "tpDistance", None),
                gsl_distance=getattr(s, "gslDistance", None),
                distance_unit=_enum_label(ProtoOASymbol, "distanceSetIn", getattr(s, "distanceSetIn", None)),
                trading_mode=_enum_label(ProtoOASymbol, "tradingMode", getattr(s, "tradingMode", None)),
                schedule_intervals=len(getattr(s, "schedule", []) or []),
                schedule_timezone=getattr(s, "scheduleTimeZone", None),
                guaranteed_stop_loss=getattr(s, "guaranteedStopLoss", None),
            )
        except RateLimited429 as e:
            result.update(status="RATE_LIMITED_429", stage=getattr(e, "stage", None))
        except BrokerError as e:
            result.update(status="BROKER_ERROR", stage=getattr(e, "stage", None), code=getattr(e, "code", None))
        except Exception as e:                                  # noqa: BLE001
            result.update(status="ERROR", error=type(e).__name__)
        finally:
            if reactor.running:
                reactor.stop()

    client.setConnectedCallback(flow)
    client.setDisconnectedCallback(lambda *_a: None)
    client.startService()
    reactor.callLater(timeout_seconds, lambda: reactor.running and reactor.stop())
    reactor.run()
    return result


if __name__ == "__main__":
    if os.environ.get("ORANGE_PREFLIGHT_CONNECT") != "1":
        print("[BLOCKED] set ORANGE_PREFLIGHT_CONNECT=1 for this step; nothing connected.")
        sys.exit(2)
    from research.farouk_pilot.read_only_ctrader_preflight import credentials as pfc, allowlist, guard
    pinned = allowlist.pinned_ctid()
    if pinned is None:
        print("[BLOCKED] allowlist is UNPINNED; confirm+pin the account first."); sys.exit(2)
    cr = pfc.load_credentials(); tok = pfc.load_token()
    if not cr or not tok:
        print("[BLOCKED] missing stored credentials or token."); sys.exit(2)
    cid, secret = cr
    at = tok.get("accessToken") or tok.get("access_token")
    r = read_xauusd(at, pinned, client_id=cid, client_secret=secret)

    print("=== XAUUSD SYMBOL READ (view-only; pinned account) ===")
    print("status                 :", r.get("status"))
    print("permission_scope       :", r.get("permission_scope"))
    print("xauusd_exact_matches   :", r.get("xauusd_exact_match_count"))
    if r.get("status") != "READ_OK":
        if r.get("candidates"):
            print("xauusd-like candidates :", r.get("candidates"))
        if r.get("error"):
            print("error                  :", r.get("error"))
        print("\nFAIL-CLOSED: not READ_OK -> stop. Nothing selected.")
        sys.exit(1)

    ls = r["lot_size"]; mn = r["min_volume"]; mx = r["max_volume"]; st = r["step_volume"]
    print(f"symbol_id              : {r['symbol_id']}")
    print(f"digits / pipPosition   : {r['digits']} / {r['pip_position']}")
    print(f"lotSize (protocol)     : {ls}")
    print(f"minVolume              : {mn}")
    print(f"maxVolume              : {mx}")
    print(f"stepVolume             : {st}")
    print(f"SL distance (min)      : {r['sl_distance']}   unit={r['distance_unit']}")
    print(f"TP distance (min)      : {r['tp_distance']}   unit={r['distance_unit']}")
    print(f"GSL distance           : {r['gsl_distance']}   unit={r['distance_unit']}  gsl_available={r['guaranteed_stop_loss']}")
    print(f"trading session state  : tradingMode={r['trading_mode']}  schedule_intervals={r['schedule_intervals']}  tz={r['schedule_timezone']}")

    # cTrader convention: protocol volume is in 1/100 of the base asset (centi-units);
    #   lots = protocolVolume / lotSize ; base-asset units (oz) = protocolVolume / 100.
    print("\n=== CANDIDATE NOMINAL-QUANTITY CONVERSIONS (NOT selected/ratified) ===")
    print(f"  anchor: 1.00 lot <-> {ls} protocol volume ; contract size = lotSize/100 = {ls/100:g} oz/lot")
    print(f"  {'lots (human)':>12} | {'protocol volume':>16} | {'base oz':>10} | valid? (>=min, <=max, on step)")
    for lots in (0.01, 0.02, 0.05, 0.10, 0.25, 0.50, 1.00):
        vol = round(lots * ls)
        oz = vol / 100
        valid = (vol >= (mn or 0)) and (mx is None or vol <= mx) and (st in (None, 0) or (vol - (mn or 0)) % st == 0)
        print(f"  {lots:>12.2f} | {vol:>16d} | {oz:>10g} | {'OK' if valid else 'INVALID'}")
    print(f"  boundaries: minVolume={mn} (= {mn/ls if ls else '?':g} lot), stepVolume={st} (= {st/ls if ls else '?':g} lot), maxVolume={mx} (= {mx/ls if ls else '?':g} lot)")

    # Full fail-closed guard now that XAUUSD resolves: should PASS end-to-end.
    observed = {"endpoint": "demo.ctraderapi.com", "port": 5035, "granted_scope": r["permission_scope"],
                "isLive": False, "ctidTraderAccountId": pinned, "environment": "PEPPERSTONE_DEMO",
                "xauusd_symbol_count": r["xauusd_exact_match_count"]}
    v = guard.assess(observed)
    print("\n=== FULL FAIL-CLOSED GUARD (all six conditions) ===")
    for k, f in v["fields"].items():
        print(f"  {k:26s}: ok={f['ok']}")
    print("  OVERALL guard ok        :", v["ok"])
    sys.exit(0)
