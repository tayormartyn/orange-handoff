"""VIEW-ONLY pre-pin ACCOUNT CONFIRMATION read (no pin, no symbols).

Reuses the REVIEWED ctrader_a2 transport helpers (extract_message, scope_from_response,
describe_response, write_diag, raise_if_error, parse_trader) and the ctrader_a1 validators
(returned_scope_is_view_only, validate_demo_selection) so the security decisions stay
single-sourced. Flow, ONE reactor lifecycle:
    connect(demo TLS) -> application auth -> GetAccountList
      -> AUTHORITATIVE permissionScope gate (must be SCOPE_VIEW, else stop)
      -> for each DEMO (isLive==false) candidate: account auth + Trader read -> brokerName
    (NO symbol read, NO account pinned, NO order type anywhere)
Returns, per account: ctidTraderAccountId, isLive, traderLogin, broker (demo candidates only).
Runs ONLY under .venv-ctrader with ORANGE_PREFLIGHT_CONNECT=1.
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
from ctrader_a1 import scope_validator, account_validator            # noqa: E402


def confirm_accounts(access_token, *, client_id, client_secret, timeout_seconds=30):
    if not access_token:
        raise TokenMissing("need an access token")
    from ctrader_open_api import Client, TcpProtocol, EndPoints
    from twisted.internet import reactor, defer
    from ctrader_open_api.messages.OpenApiMessages_pb2 import (
        ProtoOAApplicationAuthReq, ProtoOAGetAccountListByAccessTokenReq,
        ProtoOAAccountAuthReq, ProtoOATraderReq)

    host = getattr(EndPoints, "PROTOBUF_DEMO_HOST", lt.DEMO_HOST)
    port = getattr(EndPoints, "PROTOBUF_PORT", lt.DEMO_PORT)
    result = {"status": None, "accounts": []}
    client = Client(host, port, TcpProtocol)

    @defer.inlineCallbacks
    def flow(_conn):
        try:
            aa = ProtoOAApplicationAuthReq(); aa.clientId = client_id; aa.clientSecret = client_secret
            aares = lt.extract_message((yield client.send(aa))); lt.raise_if_error(aares, "APPLICATION_AUTH")

            al = ProtoOAGetAccountListByAccessTokenReq(); al.accessToken = access_token
            res = lt.extract_message((yield client.send(al)))
            desc = lt.describe_response(res)
            scope = lt.scope_from_response(res)                 # AUTHORITATIVE permissionScope
            lt.write_diag(desc.get("ctid_count") or 0, scope, descriptor=desc)  # masked artifact
            lt.raise_if_error(res, "GET_ACCOUNT_LIST")
            result["permission_scope"] = scope
            result["server"] = host

            if not scope_validator.returned_scope_is_view_only(scope):
                result.update(status="SCOPE_REJECTED")         # fail-closed: not view-only -> stop
                return

            accounts = []
            for a in (getattr(res, "ctidTraderAccount", None) or []):
                accounts.append({
                    "ctidTraderAccountId": int(getattr(a, "ctidTraderAccountId", 0)),
                    "isLive": bool(getattr(a, "isLive", False)),
                    "traderLogin": getattr(a, "traderLogin", None),
                    "broker": None, "trader_isLive": None})

            raw = [{"account_id": str(x["ctidTraderAccountId"]), "isLive": x["isLive"]} for x in accounts]
            verdict = account_validator.validate_demo_selection(raw)
            demo_ids = {int(c) for c in verdict.get("candidates", [])}

            # Trader read for the DEMO candidates only -> brokerName + authoritative isLive.
            for x in accounts:
                if x["ctidTraderAccountId"] in demo_ids:
                    ac = ProtoOAAccountAuthReq(); ac.ctidTraderAccountId = x["ctidTraderAccountId"]
                    ac.accessToken = access_token
                    acres = lt.extract_message((yield client.send(ac))); lt.raise_if_error(acres, "ACCOUNT_AUTH")
                    tr = ProtoOATraderReq(); tr.ctidTraderAccountId = x["ctidTraderAccountId"]
                    trres = lt.extract_message((yield client.send(tr))); lt.raise_if_error(trres, "ACCOUNT_INFO")
                    info = lt.parse_trader(trres)
                    x["broker"] = info.get("broker")
                    x["trader_isLive"] = info.get("isLive")

            result.update(status="OK", accounts=accounts,
                          demo_candidate_ids=sorted(demo_ids), verdict_status=verdict.get("status"))
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
    from research.farouk_pilot.read_only_ctrader_preflight import credentials as pfc
    cr = pfc.load_credentials(); tok = pfc.load_token()
    if not cr or not tok:
        print("[BLOCKED] missing stored credentials or token.")
        sys.exit(2)
    cid, secret = cr
    at = tok.get("accessToken") or tok.get("access_token")
    r = confirm_accounts(at, client_id=cid, client_secret=secret)
    print("=== ACCOUNT-LIST READ (view-only; no pin) ===")
    print("status            :", r.get("status"))
    print("permission_scope  :", r.get("permission_scope"), "(authoritative, from account-list)")
    print("server            :", r.get("server"))
    print("verdict           :", r.get("verdict_status"))
    print("demo_candidate_ids:", r.get("demo_candidate_ids"))
    if r.get("error"):
        print("error             :", r.get("error"))
    for a in r.get("accounts", []):
        print(f"  - ctidTraderAccountId={a['ctidTraderAccountId']}  isLive={a['isLive']}"
              f"  login={a.get('traderLogin')}  broker={a.get('broker')!r}"
              f"  trader_isLive={a.get('trader_isLive')}")
    sys.exit(0 if r.get("status") == "OK" else 1)
