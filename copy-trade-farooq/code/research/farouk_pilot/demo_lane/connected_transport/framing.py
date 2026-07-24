"""Wire framing + message envelope for the connected transport.

FRAMING (byte-exact, protocol-shaped): cTrader Open API length-prefixes each message with a 4-byte
big-endian length. This module implements that framing on raw bytes and a Deframer that reassembles
FRAGMENTED and COMBINED reads into whole frames. It is fully exercised offline on bytes — no socket.

ENVELOPE + CODEC: the transport speaks in Envelope(msg_type, client_msg_id, payload). The REAL wire
serialises the mapper's protobuf objects; that ProtoCodec is a later production-only step. This
build carries a FakeCodec (deterministic JSON bytes) so the loopback / fake-wire tests can drive the
whole state machine, correlation, heartbeat and timeout logic WITHOUT importing any protobuf. The
codec is an injected dependency, so nothing here hard-codes the real serialisation.
"""
import json
import struct

from . import transport_config as tc

_LEN = struct.Struct(">I")                       # 4-byte big-endian length prefix


class FramingError(Exception):
    """A frame length was absurd/oversized (fail-closed) or a payload could not be decoded."""


def frame(payload: bytes) -> bytes:
    """length-prefix a single payload."""
    if not isinstance(payload, (bytes, bytearray)):
        raise FramingError("frame payload must be bytes")
    if len(payload) > tc.MAX_FRAME_BYTES:
        raise FramingError(f"payload {len(payload)}B exceeds MAX_FRAME_BYTES {tc.MAX_FRAME_BYTES}")
    return _LEN.pack(len(payload)) + bytes(payload)


class Deframer:
    """Accumulates arbitrary byte reads and yields complete payloads. Handles: a frame split across
    many reads (fragmented), several frames in one read (combined), and any mix. Rejects an
    oversized declared length before allocating (fail-closed)."""
    def __init__(self):
        self._buf = bytearray()

    def feed(self, data: bytes):
        out = []
        if data:
            self._buf.extend(data)
        while True:
            if len(self._buf) < 4:
                break
            (length,) = _LEN.unpack_from(self._buf, 0)
            if length > tc.MAX_FRAME_BYTES:
                raise FramingError(f"declared frame length {length} exceeds cap — refusing")
            if len(self._buf) < 4 + length:
                break                                    # frame not fully arrived yet
            payload = bytes(self._buf[4:4 + length])
            del self._buf[:4 + length]
            out.append(payload)
        return out

    def pending_bytes(self):
        return len(self._buf)


# ---- message families (the ONLY permitted types; symbolic, not the raw cTrader payloadType ints,
#      which the mapper owns in production) -----------------------------------------------------
class MsgType:
    # outbound requests
    APP_AUTH_REQ = "APP_AUTH_REQ"
    ACCOUNT_LIST_REQ = "ACCOUNT_LIST_REQ"        # ProtoOAGetAccountListByAccessTokenReq
    ACCOUNT_AUTH_REQ = "ACCOUNT_AUTH_REQ"
    HEARTBEAT = "HEARTBEAT"                       # both directions
    RECONCILE_REQ = "RECONCILE_REQ"              # get Orange-owned pending orders + positions
    OPEN_LIMIT_REQ = "OPEN_LIMIT_REQ"            # approved LIMIT opening
    CANCEL_PENDING_REQ = "CANCEL_PENDING_REQ"    # cancel Orange-owned pending
    CLOSE_REDUCE_REQ = "CLOSE_REDUCE_REQ"        # risk-reducing close of Orange-owned position
    AMEND_STOP_REQ = "AMEND_STOP_REQ"            # permitted Lane-A stop modification
    # inbound responses / events
    APP_AUTH_RES = "APP_AUTH_RES"
    ACCOUNT_LIST_RES = "ACCOUNT_LIST_RES"        # ProtoOAGetAccountListByAccessTokenRes
    ACCOUNT_AUTH_RES = "ACCOUNT_AUTH_RES"
    RECONCILE_RES = "RECONCILE_RES"
    ORDER_ACK = "ORDER_ACK"
    ORDER_REJECT = "ORDER_REJECT"
    ORDER_FILL = "ORDER_FILL"
    EXECUTION_EVENT = "EXECUTION_EVENT"
    ERROR_RES = "ERROR_RES"


# exactly the outbound families this transport may ever emit (no generic console, no raw send)
PERMITTED_OUTBOUND = frozenset({
    MsgType.APP_AUTH_REQ, MsgType.ACCOUNT_LIST_REQ, MsgType.ACCOUNT_AUTH_REQ, MsgType.HEARTBEAT,
    MsgType.RECONCILE_REQ, MsgType.OPEN_LIMIT_REQ, MsgType.CANCEL_PENDING_REQ,
    MsgType.CLOSE_REDUCE_REQ, MsgType.AMEND_STOP_REQ,
})
# order-family requests that require a fully READY (authed AND reconciled) transport
ACTION_OUTBOUND = frozenset({
    MsgType.OPEN_LIMIT_REQ, MsgType.CANCEL_PENDING_REQ, MsgType.CLOSE_REDUCE_REQ,
    MsgType.AMEND_STOP_REQ,
})
KNOWN_INBOUND = frozenset({
    MsgType.APP_AUTH_RES, MsgType.ACCOUNT_LIST_RES, MsgType.ACCOUNT_AUTH_RES, MsgType.HEARTBEAT,
    MsgType.RECONCILE_RES, MsgType.ORDER_ACK, MsgType.ORDER_REJECT, MsgType.ORDER_FILL,
    MsgType.EXECUTION_EVENT, MsgType.ERROR_RES,
})


class Envelope:
    __slots__ = ("msg_type", "client_msg_id", "payload")

    def __init__(self, msg_type, client_msg_id, payload=None):
        self.msg_type = msg_type
        self.client_msg_id = client_msg_id
        self.payload = payload or {}

    def as_dict(self):
        return {"msg_type": self.msg_type, "client_msg_id": self.client_msg_id,
                "payload": self.payload}

    def __repr__(self):
        return f"Envelope({self.msg_type}, cmid={self.client_msg_id})"


class FakeCodec:
    """Deterministic JSON envelope codec for tests/loopback. IS_FAKE marks it so production refuses
    to use it. The real ProtoCodec (mapper-backed) is a later step and is not present here."""
    IS_FAKE = True

    def encode(self, env: Envelope) -> bytes:
        return json.dumps(env.as_dict(), sort_keys=True, default=str).encode("utf-8")

    def decode(self, data: bytes) -> Envelope:
        try:
            d = json.loads(data.decode("utf-8"))
        except (ValueError, UnicodeDecodeError) as e:
            raise FramingError(f"undecodable envelope: {e}")
        return Envelope(d.get("msg_type"), d.get("client_msg_id"), d.get("payload"))
