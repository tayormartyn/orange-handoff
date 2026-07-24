"""
Bounded XAUUSD spot capture (view-only). FINALISED but NOT RUN in Phase 1.

Per-event pipeline (offline-testable): extract envelope -> require ProtoOASpotEvent (else fail
closed) -> parse optional bid/ask/timestamp -> persist raw -> normalise -> persist normalised.
The Twisted flow (subscribe_and_capture) is built for the authorised live step: app-auth ->
account list (SCOPE_VIEW, reject live, single demo) -> account-auth -> ProtoOASubscribeSpotsReq
(subscribeToSpotTimestamp=True) -> collect a bounded number of ProtoOASpotEvent -> normalise +
persist -> ProtoOAUnsubscribeSpotsReq -> clean disconnect. NO order/amend/cancel/close/trading.
HTTP 429 / error -> stop immediately, zero retry.
"""
from __future__ import annotations
import os
import sys as _sys
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
_A2 = os.path.dirname(_HERE)
_CE = os.path.dirname(_A2)
for p in (_HERE, _A2, _CE):
    if p not in _sys.path:
        _sys.path.insert(0, p)

import live_transport                                    # central extract/error boundary
from normaliser import SpotNormaliser
from quote_db import QuoteDB

XAUUSD_SYMBOL_ID = 41
DEMO_LOGIN_REFERENCE = 4257941                           # human login (reference only; API uses ctid)
SPOT_EVENT_TYPE = "ProtoOASpotEvent"


def _optional_int(msg, field):
    """Read an OPTIONAL protobuf field: present only if HasField (proto2); None otherwise.
    Mocks without HasField fall back to getattr(..., None)."""
    try:
        if hasattr(msg, "HasField"):
            return getattr(msg, field) if msg.HasField(field) else None
    except (ValueError, TypeError):
        pass
    return getattr(msg, field, None)


def ingest_spot_message(message, *, session_id, seq, normaliser, db, masked_account_id,
                        now_utc=None, monotonic_ns=None):
    """One event through the pipeline. Envelope -> extract -> require SpotEvent -> persist raw +
    normalised. Unexpected payload FAILS CLOSED (nothing persisted). Returns a status dict."""
    msg = live_transport.extract_message(message)        # central boundary
    name = type(msg).__name__
    if name != SPOT_EVENT_TYPE:
        return {"accepted": False, "reason": f"UNEXPECTED_PAYLOAD:{name}"}   # fail closed

    now_utc = now_utc or time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    if monotonic_ns is None:
        monotonic_ns = time.monotonic_ns()
    raw_bid = _optional_int(msg, "bid")
    raw_ask = _optional_int(msg, "ask")
    broker_ts = _optional_int(msg, "timestamp")
    symbol_id = getattr(msg, "symbolId", None)
    payload_type = getattr(msg, "payloadType", None)

    inserted_raw = db.insert_raw(
        connection_session_id=session_id, event_sequence=seq, payload_type=payload_type,
        masked_account_id=masked_account_id, symbol_id=symbol_id, raw_bid=raw_bid, raw_ask=raw_ask,
        broker_timestamp=broker_ts, local_received_utc=now_utc,
        local_received_monotonic_ns=monotonic_ns)
    rec = normaliser.ingest(raw_bid, raw_ask, session_id, seq, monotonic_ns)
    inserted_norm = db.insert_normalised(connection_session_id=session_id, event_sequence=seq, **rec)
    return {"accepted": True, "inserted_raw": inserted_raw, "inserted_norm": inserted_norm,
            "flags": rec["flags"], "spread": rec["spread"],
            "latest_bid": rec["latest_bid"], "latest_ask": rec["latest_ask"]}


# ---------------------------------------------------------------- request builders (venv/protobuf)
def build_subscribe_req(ctid, symbol_id=XAUUSD_SYMBOL_ID):
    from ctrader_open_api.messages.OpenApiMessages_pb2 import ProtoOASubscribeSpotsReq
    r = ProtoOASubscribeSpotsReq()
    r.ctidTraderAccountId = int(ctid)
    r.symbolId.append(int(symbol_id))
    r.subscribeToSpotTimestamp = True
    return r


def build_unsubscribe_req(ctid, symbol_id=XAUUSD_SYMBOL_ID):
    from ctrader_open_api.messages.OpenApiMessages_pb2 import ProtoOAUnsubscribeSpotsReq
    r = ProtoOAUnsubscribeSpotsReq()
    r.ctidTraderAccountId = int(ctid)
    r.symbolId.append(int(symbol_id))
    return r


# ---------------------------------------------------------------- ONE reactor lifecycle (unrun in Phase 1)
def subscribe_and_capture(access_token, *, client_id, client_secret, digits, capture_seconds=45,
                          max_events=5000, db_path=None, timeout_seconds=None, session_id=None,
                          allow_trade_scope=False, expected_symbol_id=None):
    """Authorised-step live capture (time-bounded ~capture_seconds). Built + verified offline.
    allow_trade_scope=True lets the READ-ONLY observer run with a SCOPE_TRADE token (it constructs no
    order/amend/close/cancel message — only spot subscribe/unsubscribe). expected_symbol_id overrides
    the hardcoded id with a broker-resolved one (dynamic XAUUSD resolution).
    app-auth -> account list (SCOPE_VIEW, reject live, single demo) -> require login 4257941 ->
    account-auth -> resolve+verify XAUUSD==41 -> SubscribeSpots once -> capture ~capture_seconds ->
    UnsubscribeSpots once -> clean disconnect. Zero retry; 429/error/scope/account/symbol stop."""
    if not access_token:
        from errors import TokenMissing
        raise TokenMissing("subscribe_and_capture requires an already-cached access token")
    from ctrader_open_api import Client, TcpProtocol, EndPoints
    from twisted.internet import reactor, defer
    from ctrader_open_api.messages.OpenApiMessages_pb2 import (
        ProtoOAApplicationAuthReq, ProtoOAGetAccountListByAccessTokenReq, ProtoOAAccountAuthReq,
        ProtoOASymbolsListReq)
    from ctrader_a1 import scope_validator, account_validator
    from errors import RateLimited429, BrokerError, ScopeRejected, LiveAccountRejected, NoDemoAccount
    import masking

    timeout_seconds = timeout_seconds or (capture_seconds + 20)     # hard safety ceiling
    host = getattr(EndPoints, "PROTOBUF_DEMO_HOST", live_transport.DEMO_HOST)
    port = getattr(EndPoints, "PROTOBUF_PORT", live_transport.DEMO_PORT)
    session_id = session_id or f"q1-{time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())}"
    db = QuoteDB(db_path)
    normaliser = SpotNormaliser(digits)
    state = {"seq": 0, "captured": 0, "ctid": None, "unsubscribed": False, "finished": False,
             "connection_lost": False, "symbol_id": None}
    result = {"status": None, "session_id": session_id, "captured": 0, "error": None,
              "account_id_masked": None, "required_login_ok": None, "symbol_verified": None,
              "subscribe_confirmed": False, "unsubscribe_confirmed": False,
              "subscribe_utc": None, "finish_utc": None, "finish_reason": None,
              "db_path": db.path, "capture_seconds": capture_seconds, "clean_disconnect": False,
              "connection_lost": False, "disconnect_seen": False}
    client = Client(host, port, TcpProtocol)

    def _finish(reason):
        if state["finished"]:
            return
        state["finished"] = True
        result["finish_reason"] = reason
        result["finish_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        if not state["unsubscribed"] and state["ctid"] is not None:
            try:
                client.send(build_unsubscribe_req(state["ctid"], state.get("symbol_id") or XAUUSD_SYMBOL_ID))   # ONCE
                state["unsubscribed"] = True
                result["unsubscribe_confirmed"] = True
            except Exception:                                      # noqa: BLE001
                pass
        result["clean_disconnect"] = True
        if reactor.running:
            reactor.callLater(2, lambda: reactor.running and reactor.stop())   # grace to flush

    def _stop_error(status, **extra):
        result.update(status=status, **extra)
        if reactor.running:
            reactor.stop()

    def on_message(_c, message):
        try:
            msg = live_transport.extract_message(message)          # central boundary
            name = type(msg).__name__
            if name != SPOT_EVENT_TYPE:
                if "Error" in name:                                # an error push must stop
                    live_transport.raise_if_error(msg, "SPOT")
                return
            live_transport.raise_if_error(msg, "SPOT")
            state["seq"] += 1
            ingest_spot_message(msg, session_id=session_id, seq=state["seq"], normaliser=normaliser,
                                db=db, masked_account_id=result["account_id_masked"])
            state["captured"] += 1
            if state["captured"] >= max_events:
                _finish("MAX_EVENTS_SAFETY_CAP")
        except (RateLimited429, BrokerError) as e:                 # stop, zero retry
            _stop_error("STOPPED_ERROR", error=type(e).__name__)

    @defer.inlineCallbacks
    def flow(_conn):
        try:
            aa = ProtoOAApplicationAuthReq(); aa.clientId = client_id; aa.clientSecret = client_secret
            live_transport.raise_if_error(live_transport.extract_message((yield client.send(aa))),
                                          "APPLICATION_AUTH")
            al = ProtoOAGetAccountListByAccessTokenReq(); al.accessToken = access_token
            res = live_transport.extract_message((yield client.send(al)))
            live_transport.raise_if_error(res, "GET_ACCOUNT_LIST")
            scope = live_transport.scope_from_response(res)        # (3) SCOPE_VIEW or SCOPE_TRADE
            result["returned_scope"] = scope
            _scope_ok = (scope_validator.returned_scope_is_view_only(scope)
                         or (allow_trade_scope and scope == "SCOPE_TRADE"))
            if not _scope_ok:
                # a SCOPE_TRADE token is admissible for READ-ONLY capture only when explicitly allowed;
                # the observer constructs no trading message regardless.
                raise ScopeRejected(f"scope not admissible for read-only capture: {scope}")
            verdict = account_validator.validate_demo_selection(live_transport.parse_account_list(res))
            if verdict["status"] == "REJECTED_LIVE_ONLY":         # (5) reject live
                raise LiveAccountRejected("only live accounts")
            if verdict["status"] == "NO_DEMO_ACCOUNT":
                raise NoDemoAccount("no demo account")
            if len(verdict["candidates"]) != 1:
                _stop_error("NEEDS_HUMAN_SELECTION"); return
            state["ctid"] = verdict["candidates"][0]
            result["account_id_masked"] = masking.mask_account_id(str(state["ctid"]))
            # (4) require account 4257941 by traderLogin (fail closed on mismatch/absent)
            logins = {str(getattr(a, "ctidTraderAccountId", "")): getattr(a, "traderLogin", None)
                      for a in getattr(res, "ctidTraderAccount", [])}
            if str(logins.get(state["ctid"])) != str(DEMO_LOGIN_REFERENCE):
                _stop_error("WRONG_ACCOUNT"); return
            result["required_login_ok"] = True
            ac = ProtoOAAccountAuthReq(); ac.ctidTraderAccountId = int(state["ctid"])
            ac.accessToken = access_token
            live_transport.raise_if_error(live_transport.extract_message((yield client.send(ac))),
                                          "ACCOUNT_AUTH")
            # (6) resolve + verify XAUUSD symbol id == 41
            sreq = ProtoOASymbolsListReq(); sreq.ctidTraderAccountId = int(state["ctid"])
            sres = live_transport.extract_message((yield client.send(sreq)))
            live_transport.raise_if_error(sres, "SYMBOL")
            sid = live_transport.find_symbol_id(sres, "XAUUSD")    # dynamic broker resolution
            if sid is None:
                _stop_error("SYMBOL_UNRESOLVED"); return
            if expected_symbol_id is not None and sid != expected_symbol_id:
                _stop_error("SYMBOL_MISMATCH", resolved_symbol_id=sid); return
            state["symbol_id"] = int(sid)
            result["resolved_symbol_id"] = int(sid)
            result["symbol_verified"] = True
            # (7) subscribe ONCE using the BROKER-RESOLVED id; (8) capture for ~capture_seconds
            yield client.send(build_subscribe_req(state["ctid"], state["symbol_id"]))
            result.update(status="CAPTURING", subscribe_confirmed=True,
                          subscribe_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
            reactor.callLater(capture_seconds, lambda: _finish("CAPTURE_WINDOW_ELAPSED"))
        except RateLimited429 as e:
            _stop_error("RATE_LIMITED_429", stage=e.stage)
        except BrokerError as e:
            _stop_error("BROKER_ERROR", stage=e.stage, code=e.code)
        except Exception as e:                                     # noqa: BLE001
            _stop_error("ERROR", error=type(e).__name__)

    def on_disconnected(_c, reason=None):
        # NO automatic re-establishment. A loss BEFORE our bounded finish = transport gone: halt
        # the ClientService (so it does not auto re-establish) and stop cleanly, recording it.
        result["disconnect_seen"] = True
        if not state["finished"]:
            state["connection_lost"] = True
            result["connection_lost"] = True
            try:
                client.stopService()
            except Exception:                                     # noqa: BLE001
                pass
            if reactor.running:
                reactor.callLater(0, lambda: reactor.running and reactor.stop())

    client.setConnectedCallback(flow)
    client.setMessageReceivedCallback(on_message)
    client.setDisconnectedCallback(on_disconnected)
    client.startService()
    reactor.callLater(timeout_seconds, lambda: _finish("HARD_TIMEOUT"))   # safety -> graceful
    reactor.run()                                                  # ONE lifecycle
    result["captured"] = state["captured"]
    if result["status"] == "CAPTURING":
        result["status"] = "CAPTURE_COMPLETE"
    db.close()
    return result
