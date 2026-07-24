"""REAL cTrader ProtoCodec (completion item 1). Maps the transport's symbolic Envelope families to
concrete generated cTrader message classes and back, through the ProtoMessage envelope:

  encode:  Envelope -> concrete request/response message -> ProtoMessage(payloadType, payload,
           clientMsgId) -> serialized bytes   (framing.frame adds the 4-byte length prefix)
  decode:  serialized bytes -> ProtoMessage -> concrete message -> Envelope(msg_type, clientMsgId,
           payload dict) -> the EXISTING state machine

Order/close payloads are built by the ACCEPTED offline mapper (protobuf_mapper) — NOT re-implemented
here. No sizing/approval/reconciliation/campaign logic. The generated classes load via the mapper's
stub-bootstrap (no Twisted client, no socket). Fail-closed: malformed ProtoMessage -> FramingError;
payloadType/payload mismatch -> FramingError; unmapped payloadType -> an UNKNOWN_PAYLOAD envelope
that is NOT in KNOWN_INBOUND (the transport then fail-closes).
"""
from . import framing
from .framing import Envelope, FramingError, MsgType
from .. import protobuf_mapper

_PB = None


def _load():
    global _PB
    if _PB is not None:
        return _PB
    protobuf_mapper._load_pb2()                       # installs ctrader_open_api stubs (no Twisted)
    from ctrader_open_api.messages.OpenApiCommonMessages_pb2 import ProtoMessage, ProtoHeartbeatEvent
    from ctrader_open_api.messages.OpenApiCommonModelMessages_pb2 import ProtoPayloadType
    from ctrader_open_api.messages.OpenApiMessages_pb2 import (
        ProtoOAApplicationAuthReq, ProtoOAApplicationAuthRes,
        ProtoOAGetAccountListByAccessTokenReq, ProtoOAGetAccountListByAccessTokenRes,
        ProtoOAAccountAuthReq, ProtoOAAccountAuthRes, ProtoOAReconcileReq, ProtoOAReconcileRes,
        ProtoOACancelOrderReq, ProtoOAAmendOrderReq, ProtoOAExecutionEvent, ProtoOAOrderErrorEvent,
        ProtoOAErrorRes)
    from ctrader_open_api.messages.OpenApiModelMessages_pb2 import (
        ProtoOAPayloadType as PT, ProtoOAExecutionType as ET, ProtoOAClientPermissionScope as SC,
        ProtoOACtidTraderAccount, ProtoOATradeSide, ProtoOAOrderType, ProtoOAOrderStatus,
        ProtoOAPositionStatus)
    from google.protobuf.message import DecodeError
    _PB = dict(
        ProtoMessage=ProtoMessage, Heartbeat=ProtoHeartbeatEvent, HB_PT=ProtoPayloadType.HEARTBEAT_EVENT,
        AppAuthReq=ProtoOAApplicationAuthReq, AppAuthRes=ProtoOAApplicationAuthRes,
        AcctListReq=ProtoOAGetAccountListByAccessTokenReq, AcctListRes=ProtoOAGetAccountListByAccessTokenRes,
        AcctAuthReq=ProtoOAAccountAuthReq, AcctAuthRes=ProtoOAAccountAuthRes,
        ReconReq=ProtoOAReconcileReq, ReconRes=ProtoOAReconcileRes,
        CancelReq=ProtoOACancelOrderReq, AmendReq=ProtoOAAmendOrderReq,
        ExecEvent=ProtoOAExecutionEvent, OrderErr=ProtoOAOrderErrorEvent, ErrorRes=ProtoOAErrorRes,
        CtidAcct=ProtoOACtidTraderAccount, TradeSide=ProtoOATradeSide, PT=PT, ET=ET, SC=SC,
        OrderType=ProtoOAOrderType, OrderStatus=ProtoOAOrderStatus, PosStatus=ProtoOAPositionStatus,
        DecodeError=DecodeError)
    return _PB


class ProtoCodec:
    """The REAL codec (IS_FAKE = False). Interchangeable with FakeCodec: encode(Envelope)->bytes,
    decode(bytes)->Envelope."""
    IS_FAKE = False

    # ---------- encode ----------
    def encode(self, env: Envelope) -> bytes:
        pb = _load()
        inner, pt = self._build_inner(env, pb)
        if hasattr(inner, "payloadType"):
            inner.payloadType = pt            # force onto the wire so decode can verify pt vs payload
        msg = pb["ProtoMessage"]()
        msg.payloadType = pt
        msg.payload = inner.SerializeToString()
        if env.client_msg_id is not None:
            msg.clientMsgId = str(env.client_msg_id)
        return msg.SerializeToString()

    def _build_inner(self, env, pb):
        p = env.payload or {}
        mt = env.msg_type
        PT, ET, SC = pb["PT"], pb["ET"], pb["SC"]
        if mt == MsgType.APP_AUTH_REQ:
            m = pb["AppAuthReq"](clientId=p.get("client_id", ""), clientSecret=p.get("client_secret", ""))
            return m, PT.PROTO_OA_APPLICATION_AUTH_REQ
        if mt == MsgType.APP_AUTH_RES:
            return pb["AppAuthRes"](), PT.PROTO_OA_APPLICATION_AUTH_RES
        if mt == MsgType.ACCOUNT_LIST_REQ:
            return pb["AcctListReq"](accessToken=p.get("access_token", "")), PT.PROTO_OA_GET_ACCOUNTS_BY_ACCESS_TOKEN_REQ
        if mt == MsgType.ACCOUNT_LIST_RES:
            m = pb["AcctListRes"]()
            m.accessToken = p.get("access_token", "")     # proto2 REQUIRED on the generated class
            m.permissionScope = SC.Value(p.get("permissionScope", "SCOPE_VIEW"))
            for a in p.get("accounts", []):
                m.ctidTraderAccount.add(ctidTraderAccountId=int(a["ctidTraderAccountId"]),
                                        isLive=bool(a.get("isLive", False)))
            return m, PT.PROTO_OA_GET_ACCOUNTS_BY_ACCESS_TOKEN_RES
        if mt == MsgType.ACCOUNT_AUTH_REQ:
            return (pb["AcctAuthReq"](ctidTraderAccountId=int(p.get("ctid", 0)),
                                      accessToken=p.get("access_token", "")),
                    PT.PROTO_OA_ACCOUNT_AUTH_REQ)
        if mt == MsgType.ACCOUNT_AUTH_RES:
            return pb["AcctAuthRes"](ctidTraderAccountId=int(p.get("ctid", 0))), PT.PROTO_OA_ACCOUNT_AUTH_RES
        if mt == MsgType.HEARTBEAT:
            return pb["Heartbeat"](), pb["HB_PT"]
        if mt == MsgType.RECONCILE_REQ:
            return pb["ReconReq"](ctidTraderAccountId=int(p.get("ctid", 0))), PT.PROTO_OA_RECONCILE_REQ
        if mt == MsgType.RECONCILE_RES:
            m = pb["ReconRes"](ctidTraderAccountId=int(p.get("ctid", 0)))
            for oid, o in (p.get("orders") or {}).items():
                self._fill_order(m.order.add(), {**o, "order_id": o.get("order_id", oid)}, pb)
            for pid, pos in (p.get("positions") or {}).items():
                self._fill_position(m.position.add(),
                                    {**pos, "position_id": pos.get("position_id", pid)}, pb)
            return m, PT.PROTO_OA_RECONCILE_RES
        if mt == MsgType.OPEN_LIMIT_REQ:
            m = protobuf_mapper.build_new_order_req(
                ctid_trader_account_id=int(p["account_id"]), symbol_id=int(p["symbol_id"]),
                side=p["trade_side"], volume=int(p["volume"]), limit_price=p["limit_price"],
                stop_loss=p["stop_loss"], expiration_timestamp=int(p["expiration_timestamp"]),
                correlation=p.get("correlation", p), client_order_id=p.get("client_order_id"))
            return m, PT.PROTO_OA_NEW_ORDER_REQ
        if mt == MsgType.CANCEL_PENDING_REQ:
            return (pb["CancelReq"](ctidTraderAccountId=int(p.get("account_id", 0)),
                                    orderId=int(p["order_id"])), PT.PROTO_OA_CANCEL_ORDER_REQ)
        if mt == MsgType.CLOSE_REDUCE_REQ:
            m = protobuf_mapper.build_close_position_req(
                ctid_trader_account_id=int(p.get("account_id", 0)), position_id=int(p["position_id"]),
                volume=int(p["volume"]), owner_verified=True)
            return m, PT.PROTO_OA_CLOSE_POSITION_REQ
        if mt == MsgType.AMEND_STOP_REQ:
            m = pb["AmendReq"](ctidTraderAccountId=int(p.get("account_id", 0)),
                               orderId=int(p["order_id"]))
            m.stopLoss = p["stop_loss"]
            return m, PT.PROTO_OA_AMEND_ORDER_REQ
        if mt == MsgType.ORDER_ACK:
            m = pb["ExecEvent"](ctidTraderAccountId=int(p.get("account_id", 0)),
                                executionType=ET.ORDER_ACCEPTED)
            self._fill_order(m.order, p, pb)
            if p.get("client_order_id"):
                m.order.clientOrderId = str(p["client_order_id"])
            if p.get("stop_loss") is not None:
                m.order.stopLoss = p["stop_loss"]
            return m, PT.PROTO_OA_EXECUTION_EVENT
        if mt == MsgType.ORDER_FILL:
            m = pb["ExecEvent"](ctidTraderAccountId=int(p.get("account_id", 0)),
                                executionType=ET.ORDER_FILLED)
            self._fill_order(m.order, p, pb, status="ORDER_STATUS_FILLED")
            m.order.executedVolume = int(p.get("filled_volume", 0))
            if p.get("position_id") is not None:
                self._fill_position(m.position, p, pb)
            return m, PT.PROTO_OA_EXECUTION_EVENT
        if mt == MsgType.EXECUTION_EVENT:
            sub = p.get("subtype", "SWAP")
            m = pb["ExecEvent"](ctidTraderAccountId=int(p.get("account_id", 0)),
                                executionType=ET.Value(sub) if sub in ET.keys() else ET.SWAP)
            return m, PT.PROTO_OA_EXECUTION_EVENT
        if mt == MsgType.ORDER_REJECT:
            m = pb["OrderErr"](ctidTraderAccountId=int(p.get("account_id", 0)),
                               errorCode=str(p.get("errorCode", "REJECTED")),
                               orderId=int(p.get("order_id", 0)), description=str(p.get("why", "")))
            return m, PT.PROTO_OA_ORDER_ERROR_EVENT
        if mt == MsgType.ERROR_RES:
            return (pb["ErrorRes"](errorCode=str(p.get("errorCode", "ERROR")),
                                   description=str(p.get("why", ""))), PT.PROTO_OA_ERROR_RES)
        raise FramingError(f"ProtoCodec cannot encode unknown family {mt!r}")

    # ProtoOAOrder / ProtoOAPosition are proto2 messages with REQUIRED nested fields (orderId,
    # tradeData{symbolId,volume,tradeSide}, orderType/orderStatus resp. positionStatus, swap);
    # every required member must be present before SerializeToString will accept the message.
    @staticmethod
    def _fill_order(o, p, pb, *, status="ORDER_STATUS_ACCEPTED"):
        o.orderId = int(p.get("order_id", 0) or 0)
        o.orderType = pb["OrderType"].LIMIT
        o.orderStatus = pb["OrderStatus"].Value(status)
        o.tradeData.symbolId = int(p.get("symbol_id", 0) or 0)
        o.tradeData.volume = int(p.get("volume", 0) or 0)
        o.tradeData.tradeSide = pb["TradeSide"].Value(p.get("trade_side") or "BUY")
        return o

    @staticmethod
    def _fill_position(pos, p, pb):
        pos.positionId = int(p.get("position_id", 0) or 0)
        pos.positionStatus = pb["PosStatus"].POSITION_STATUS_OPEN
        pos.swap = int(p.get("swap", 0) or 0)
        pos.tradeData.symbolId = int(p.get("symbol_id", 0) or 0)
        pos.tradeData.volume = int(p.get("volume", p.get("filled_volume", 0)) or 0)
        pos.tradeData.tradeSide = pb["TradeSide"].Value(p.get("trade_side") or "BUY")
        return pos

    # ---------- decode ----------
    def decode(self, data: bytes) -> Envelope:
        pb = _load()
        wrap = pb["ProtoMessage"]()
        try:
            wrap.ParseFromString(data)
        except pb["DecodeError"] as e:
            raise FramingError(f"malformed ProtoMessage: {e}")
        cmid = wrap.clientMsgId or None
        pt = wrap.payloadType
        msg_type, cls, extractor = self._decoder_for(pt, pb)
        if cls is None:
            # unmapped payloadType -> fail-closed (NOT a KNOWN_INBOUND family)
            return Envelope(f"UNKNOWN_PAYLOAD_{pt}", cmid, {"payloadType": pt})
        inner = cls()
        try:
            inner.ParseFromString(wrap.payload)
        except pb["DecodeError"] as e:
            raise FramingError(f"malformed inner payload for payloadType {pt}: {e}")
        inner_pt = getattr(inner, "payloadType", None)
        if inner_pt not in (None, 0) and inner_pt != pt:
            raise FramingError(f"payloadType mismatch: envelope={pt} inner={inner_pt}")
        if extractor is None:                    # execution-event family -> refine by executionType
            rt, payload = self._refine_exec(inner, pb)
            return Envelope(rt, cmid, payload)
        return Envelope(msg_type, cmid, extractor(inner, pb))

    def _decoder_for(self, pt, pb):
        PT = pb["PT"]
        table = {
            PT.PROTO_OA_APPLICATION_AUTH_REQ: (MsgType.APP_AUTH_REQ, pb["AppAuthReq"],
                                               lambda m, _: {}),
            PT.PROTO_OA_APPLICATION_AUTH_RES: (MsgType.APP_AUTH_RES, pb["AppAuthRes"],
                                               lambda m, _: {"ok": True}),
            PT.PROTO_OA_GET_ACCOUNTS_BY_ACCESS_TOKEN_REQ: (MsgType.ACCOUNT_LIST_REQ, pb["AcctListReq"],
                                                           lambda m, _: {"access_token": m.accessToken}),
            PT.PROTO_OA_GET_ACCOUNTS_BY_ACCESS_TOKEN_RES: (MsgType.ACCOUNT_LIST_RES, pb["AcctListRes"],
                                                           self._x_acct_list),
            PT.PROTO_OA_ACCOUNT_AUTH_REQ: (MsgType.ACCOUNT_AUTH_REQ, pb["AcctAuthReq"],
                                           lambda m, _: {"ctid": m.ctidTraderAccountId,
                                                         "access_token": m.accessToken}),
            PT.PROTO_OA_ACCOUNT_AUTH_RES: (MsgType.ACCOUNT_AUTH_RES, pb["AcctAuthRes"],
                                           lambda m, _: {"ok": True}),
            pb["HB_PT"]: (MsgType.HEARTBEAT, pb["Heartbeat"], lambda m, _: {}),
            PT.PROTO_OA_RECONCILE_REQ: (MsgType.RECONCILE_REQ, pb["ReconReq"],
                                        lambda m, _: {"ctid": m.ctidTraderAccountId}),
            PT.PROTO_OA_RECONCILE_RES: (MsgType.RECONCILE_RES, pb["ReconRes"], self._x_recon),
            PT.PROTO_OA_NEW_ORDER_REQ: (MsgType.OPEN_LIMIT_REQ, protobuf_mapper._load_pb2()["NewOrder"],
                                        self._x_new_order),
            PT.PROTO_OA_CANCEL_ORDER_REQ: (MsgType.CANCEL_PENDING_REQ, pb["CancelReq"],
                                           lambda m, _: {"account_id": m.ctidTraderAccountId,
                                                         "order_id": m.orderId}),
            PT.PROTO_OA_CLOSE_POSITION_REQ: (MsgType.CLOSE_REDUCE_REQ,
                                             protobuf_mapper._load_pb2()["Close"],
                                             lambda m, _: {"account_id": m.ctidTraderAccountId,
                                                           "position_id": m.positionId, "volume": m.volume}),
            PT.PROTO_OA_AMEND_ORDER_REQ: (MsgType.AMEND_STOP_REQ, pb["AmendReq"],
                                          lambda m, _: {"account_id": m.ctidTraderAccountId,
                                                        "order_id": m.orderId, "stop_loss": m.stopLoss}),
            PT.PROTO_OA_EXECUTION_EVENT: (None, pb["ExecEvent"], None),   # resolved by executionType
            PT.PROTO_OA_ORDER_ERROR_EVENT: (MsgType.ORDER_REJECT, pb["OrderErr"],
                                            lambda m, _: {"why": m.description, "order_id": m.orderId,
                                                          "errorCode": m.errorCode}),
            PT.PROTO_OA_ERROR_RES: (MsgType.ERROR_RES, pb["ErrorRes"],
                                    lambda m, _: {"why": m.description, "errorCode": m.errorCode}),
        }
        entry = table.get(pt)
        if entry is None:
            return (None, None, None)
        if pt == PT.PROTO_OA_EXECUTION_EVENT:
            return (MsgType.EXECUTION_EVENT, pb["ExecEvent"], None)      # msg_type refined post-parse
        return entry

    # execution events carry the real outcome in executionType; refine there
    def _refine_exec(self, inner, pb):
        ET = pb["ET"]
        et = inner.executionType
        if et == ET.ORDER_ACCEPTED:
            return MsgType.ORDER_ACK, {"order_id": inner.order.orderId,
                                       "client_order_id": inner.order.clientOrderId,
                                       "stop_loss": inner.order.stopLoss,
                                       "stop_accepted": inner.order.stopLoss > 0, "status": "ACCEPTED"}
        if et in (ET.ORDER_FILLED, ET.ORDER_PARTIAL_FILL):
            return MsgType.ORDER_FILL, {"order_id": inner.order.orderId,
                                        "filled_volume": inner.order.executedVolume,
                                        "position_id": inner.position.positionId}
        if et == ET.ORDER_REJECTED:
            return MsgType.ORDER_REJECT, {"why": "execution ORDER_REJECTED",
                                          "order_id": inner.order.orderId}
        return MsgType.EXECUTION_EVENT, {"subtype": ET.Name(et)}

    # decode override for execution events (needs post-parse refinement)
    def _x_acct_list(self, m, pb):
        return {"permissionScope": pb["SC"].Name(m.permissionScope),
                "accounts": [{"ctidTraderAccountId": a.ctidTraderAccountId, "isLive": a.isLive}
                             for a in m.ctidTraderAccount]}

    def _x_recon(self, m, _pb):
        return {"orders": {str(o.orderId): {"order_id": o.orderId} for o in m.order},
                "positions": {str(p.positionId): {"position_id": p.positionId} for p in m.position}}

    def _x_new_order(self, m, pb):
        return {"account_id": m.ctidTraderAccountId, "symbol_id": m.symbolId,
                "trade_side": pb["TradeSide"].Name(m.tradeSide), "volume": m.volume,
                "limit_price": m.limitPrice, "stop_loss": m.stopLoss,
                "expiration_timestamp": m.expirationTimestamp, "client_order_id": m.clientOrderId}
