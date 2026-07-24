"""TEST wire infrastructure: an in-memory FakeBroker plus two connectors (in-memory FakeConnector
and a real 127.0.0.1 LoopbackConnector/LoopbackServer). NO external network, NO protobuf, NO real
credentials. This is the ONLY 'broker' the tests ever talk to. It is deliberately parallel to
demo_lane.mock_order_channel, and it never dials anything but loopback.
"""
import socket
import ssl
import threading

from . import framing
from .framing import Envelope, MsgType


class FakeBroker:
    """Computes response envelope(s) for each inbound request envelope. Configurable to reject, lose
    responses, partially fill, and to push an unknown event. Tracks Orange-owned orders/positions so
    reconcile + cancel + close behave coherently."""
    def __init__(self, *, reject_open=False, fill_on_open=False, partial_volume=None,
                 unknown_event=False, owned_orders=None, owned_positions=None,
                 account_list=None, account_scope="SCOPE_TRADE"):
        self.reject_open = reject_open
        self.fill_on_open = fill_on_open
        self.partial_volume = partial_volume
        self.unknown_event = unknown_event
        self.orders = dict(owned_orders or {})
        self.positions = dict(owned_positions or {})
        # default account list = exactly the single allowlisted demo account (id 1_000_001, demo)
        self.account_list = (account_list if account_list is not None
                             else [{"ctidTraderAccountId": 1_000_001, "isLive": False}])
        self.account_scope = account_scope
        self._n = 1
        self.seen = []                       # msg_types received (for assertions)

    def handle(self, env: Envelope):
        self.seen.append(env.msg_type)
        cmid = env.client_msg_id
        p = env.payload or {}
        mt = env.msg_type
        if mt == MsgType.APP_AUTH_REQ:
            return [Envelope(MsgType.APP_AUTH_RES, cmid, {"ok": True})]
        if mt == MsgType.ACCOUNT_LIST_REQ:
            return [Envelope(MsgType.ACCOUNT_LIST_RES, cmid,
                             {"accounts": self.account_list, "permissionScope": self.account_scope})]
        if mt == MsgType.ACCOUNT_AUTH_REQ:
            return [Envelope(MsgType.ACCOUNT_AUTH_RES, cmid, {"ok": True})]
        if mt == MsgType.HEARTBEAT:
            return [Envelope(MsgType.HEARTBEAT, cmid, {})]
        if mt == MsgType.RECONCILE_REQ:
            return [Envelope(MsgType.RECONCILE_RES, cmid,
                             {"orders": self.orders, "positions": self.positions})]
        if mt == MsgType.OPEN_LIMIT_REQ:
            return self._open(cmid, p)
        if mt == MsgType.CANCEL_PENDING_REQ:
            oid = p.get("order_id")
            existed = self.orders.pop(oid, None) is not None
            return [Envelope(MsgType.ORDER_ACK, cmid, {"order_id": oid, "cancelled": existed})]
        if mt == MsgType.CLOSE_REDUCE_REQ:
            return self._close(cmid, p)
        if mt == MsgType.AMEND_STOP_REQ:
            return [Envelope(MsgType.ORDER_ACK, cmid,
                             {"order_id": p.get("order_id"), "stop_loss": p.get("stop_loss"),
                              "amended": True})]
        return [Envelope(MsgType.ERROR_RES, cmid, {"why": f"unhandled {mt}"})]

    def _open(self, cmid, p):
        if self.reject_open:
            return [Envelope(MsgType.ORDER_REJECT, cmid, {"why": "broker rejected (test)"})]
        oid = f"O{self._n}"; self._n += 1
        vol = int(p.get("volume", 0) or 0)
        order = {"order_id": oid, "account_id": p.get("account_id"), "symbol_id": p.get("symbol_id"),
                 "trade_side": p.get("trade_side"), "volume": vol, "limit_price": p.get("limit_price"),
                 "stop_loss": p.get("stop_loss"), "stop_accepted": p.get("stop_loss") is not None,
                 "expiration_timestamp": p.get("expiration_timestamp"),
                 "filled_volume": 0, "pending_volume": vol, "position_id": None, "status": "PENDING"}
        out = []
        if self.fill_on_open:
            filled = self.partial_volume if self.partial_volume is not None else vol
            pid = f"P{oid}"
            order.update(filled_volume=filled, pending_volume=max(vol - filled, 0),
                         position_id=pid, status="FILLED" if filled == vol else "PARTIALLY_FILLED")
            self.positions[pid] = {"volume": filled, "owner": "ORANGE"}
        self.orders[oid] = order
        out.append(Envelope(MsgType.ORDER_ACK, cmid, dict(order)))
        if self.unknown_event:
            out.append(Envelope(MsgType.EXECUTION_EVENT, None, {"subtype": "UNKNOWN_MARGIN_CALL_XYZ"}))
        return out

    def _close(self, cmid, p):
        pid = p.get("position_id"); vol = int(p.get("volume", 0) or 0)
        pos = self.positions.get(pid)
        if pos is None:
            return [Envelope(MsgType.ORDER_REJECT, cmid, {"why": "no such position"})]
        if pos.get("owner") != "ORANGE":
            return [Envelope(MsgType.ORDER_REJECT, cmid, {"why": "not owned"})]
        pos["volume"] = max(pos["volume"] - vol, 0)
        if pos["volume"] == 0:
            del self.positions[pid]
        return [Envelope(MsgType.ORDER_ACK, cmid, {"position_id": pid, "closed": vol})]


class FakeConnector:
    """In-memory connector. Speaks the real framing but no socket. Fault injection: fragment/combine
    recv chunking, lose_send (fails before egress), lose_after_send (drops the response = lost ack)."""
    IS_MOCK = True

    def __init__(self, broker, *, codec=None, fragment=False, combine=True, lose_send=False,
                 lose_after_send=False):
        self.broker = broker
        self.codec = codec or framing.FakeCodec()    # must match the transport's codec
        self.fragment = fragment
        self.combine = combine
        self.lose_send = lose_send
        self.lose_after_send = lose_after_send
        self.host, self.port = "in-memory", 0
        self._inbox = bytearray()
        self._inbox_lock = threading.Lock()          # reader thread vs test-side inject()
        self.connected = False
        self.sent_frames = 0

    def connect(self):
        self.connected = True

    def send(self, frame_bytes):
        if self.lose_send:
            raise ConnectionError("simulated send-phase failure (zero/unknown bytes on the wire)")
        self.sent_frames += 1
        for payload in framing.Deframer().feed(frame_bytes):
            env = self.codec.decode(payload)
            responses = self.broker.handle(env)
            if self.lose_after_send:
                continue                                 # bytes went out; response is lost (ambiguous)
            with self._inbox_lock:
                for r in responses:
                    self._inbox.extend(framing.frame(self.codec.encode(r)))

    def inject(self, env):
        """Test seam: push an ASYNC broker-initiated envelope (fill/event) into the inbound stream,
        as the real broker would while no request is awaiting."""
        with self._inbox_lock:
            self._inbox.extend(framing.frame(self.codec.encode(env)))

    def recv(self, timeout=None):
        with self._inbox_lock:
            if not self._inbox:
                return None                              # nothing pending -> timeout/None
            if self.fragment:
                b = bytes(self._inbox[:1]); del self._inbox[:1]
                return b
            if self.combine:
                b = bytes(self._inbox); self._inbox.clear()
                return b
            b = bytes(self._inbox[:64]); del self._inbox[:64]
            return b

    def close(self):
        self.connected = False


# ---- REAL 127.0.0.1 loopback (proves framing over an actual socket, loopback-only) -------------
class LoopbackServer:
    """A tiny broker server bound to 127.0.0.1 on an ephemeral port. One thread per connection,
    reading framed request envelopes and writing framed responses via a FakeBroker. Optionally wraps
    each accepted connection in a server-side TLS context (for the TLS-channel tests), and uses an
    injected codec (FakeCodec or the real ProtoCodec)."""
    def __init__(self, broker=None, *, ssl_context=None, codec=None):
        self.broker = broker or FakeBroker()
        self.ssl_context = ssl_context
        self.codec = codec or framing.FakeCodec()
        self._srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._srv.bind(("127.0.0.1", 0))
        self._srv.listen(1)
        self.host, self.port = self._srv.getsockname()
        self._stop = False
        self._t = threading.Thread(target=self._serve, daemon=True)
        self._t.start()

    def _serve(self):
        try:
            self._srv.settimeout(0.5)
            while not self._stop:
                try:
                    conn, _ = self._srv.accept()
                except socket.timeout:
                    continue
                threading.Thread(target=self._handle, args=(conn,), daemon=True).start()
        except OSError:
            pass

    def _handle(self, conn):
        deframer = framing.Deframer()
        try:
            if self.ssl_context is not None:
                conn = self.ssl_context.wrap_socket(conn, server_side=True)
            conn.settimeout(1.0)
            while not self._stop:
                try:
                    data = conn.recv(4096)
                except socket.timeout:
                    continue
                if not data:
                    break
                for payload in deframer.feed(data):
                    env = self.codec.decode(payload)
                    for r in self.broker.handle(env):
                        conn.sendall(framing.frame(self.codec.encode(r)))
        except (OSError, ssl.SSLError):
            pass
        finally:
            try:
                conn.close()
            except OSError:
                pass

    def stop(self):
        self._stop = True
        try:
            self._srv.close()
        except OSError:
            pass


class LoopbackConnector:
    """Real TCP connector to a LoopbackServer on 127.0.0.1 (the egress guard permits loopback)."""
    IS_MOCK = True

    def __init__(self, host, port):
        self.host, self.port = host, port
        self._sock = None

    @property
    def connected(self):
        return self._sock is not None

    def connect(self):
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock.settimeout(2.0)
        self._sock.connect((self.host, self.port))          # loopback only; guard-permitted

    def send(self, frame_bytes):
        self._sock.sendall(frame_bytes)

    def recv(self, timeout=None):
        if timeout is not None:
            self._sock.settimeout(timeout)
        try:
            data = self._sock.recv(4096)
            return data or None
        except socket.timeout:
            return None

    def close(self):
        if self._sock is not None:
            self._sock.close()
            self._sock = None
