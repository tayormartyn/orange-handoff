"""
H1 — LIVE public-data connector (testnet, public, READ-ONLY).

Connectivity proof only. This module:
  * loads NO key and reads NO account/wallet — it POSTs only the public /info endpoint and
    subscribes to the public WebSocket feeds;
  * runs the hard safety gates (testnet env, execution off, mainnet disallowed, NO signing
    key in the process) BEFORE opening any socket;
  * feeds every received payload through the SAME deterministic classifiers + isolated
    append-only DB used by the offline path;
  * has NO order / transfer / deposit / withdrawal / signing path (proven by source_scan).

The WebSocket client is a minimal RFC-6455 implementation over stdlib socket+ssl, so this
package pulls in NO third-party networking dependency that could carry trading code.
"""
from __future__ import annotations
import base64
import hashlib
import json
import os
import socket
import ssl
import struct
import time
import urllib.request
from urllib.parse import urlparse

from . import config, safety
from .instruments import resolve_perp, parse_universe
from .observations import BookSnapshot, TradeTick, ObsContext
from .observation_db import ObservationDB
from .states import WSConnectionStateMachine
from .adapter import frame_to_book, frame_to_trades

_GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"   # RFC-6455 handshake GUID (public constant)


def _now_ms():
    return int(time.time() * 1000)


# --------------------------------------------------------------------------- /info (REST)
class InfoClient:
    """POSTs the PUBLIC /info endpoint. No auth header, no signing, no body secret."""

    def __init__(self, rest_base=config.APPROVED_TESTNET_REST, timeout=10):
        if config.is_mainnet_endpoint(rest_base) or not config.endpoint_is_approved_testnet(rest_base):
            raise safety.HyperliquidSafetyError(f"refused non-testnet REST base: {rest_base!r}")
        self.url = rest_base.rstrip("/") + config.APPROVED_REST_PATHS[0]
        self.timeout = timeout

    def _post(self, payload: dict):
        body = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(self.url, data=body,
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=self.timeout) as r:
            return json.loads(r.read().decode("utf-8")), r.status

    def meta(self):
        return self._post({"type": "meta"})

    def all_mids(self):
        return self._post({"type": "allMids"})

    def l2_book(self, coin):
        return self._post({"type": "l2Book", "coin": coin})


# --------------------------------------------------------------------------- WebSocket
class MiniWebSocket:
    """Tiny RFC-6455 text client (TLS). Read-only use: connect, subscribe, pump frames, close."""

    def __init__(self, ws_url, timeout=5):
        self.ws_url = ws_url
        self.timeout = timeout
        self.sock = None
        self._buf = b""
        self._msg = bytearray()
        self.closed = False

    def connect(self):
        u = urlparse(self.ws_url)
        host = u.hostname
        port = u.port or 443
        path = u.path or "/ws"
        raw = socket.create_connection((host, port), timeout=self.timeout)
        ctx = ssl.create_default_context()
        self.sock = ctx.wrap_socket(raw, server_hostname=host)
        key = base64.b64encode(os.urandom(16)).decode()
        handshake = (
            f"GET {path} HTTP/1.1\r\nHost: {host}\r\nUpgrade: websocket\r\n"
            f"Connection: Upgrade\r\nSec-WebSocket-Key: {key}\r\n"
            f"Sec-WebSocket-Version: 13\r\n\r\n")
        self.sock.sendall(handshake.encode())
        resp = self._read_until(b"\r\n\r\n")
        if b" 101 " not in resp.split(b"\r\n", 1)[0]:
            raise ConnectionError(f"websocket upgrade failed: {resp.split(chr(13).encode())[0]!r}")
        accept = base64.b64encode(hashlib.sha1((key + _GUID).encode()).digest()).decode()
        if accept.encode() not in resp:
            raise ConnectionError("websocket Sec-WebSocket-Accept mismatch")
        self.sock.settimeout(0.5)
        return True

    def _read_until(self, marker):
        data = b""
        self.sock.settimeout(self.timeout)
        while marker not in data:
            chunk = self.sock.recv(1024)
            if not chunk:
                raise ConnectionError("connection closed during handshake")
            data += chunk
        return data

    def _send_frame(self, opcode, payload=b""):
        b1 = 0x80 | opcode
        ln = len(payload)
        header = bytes([b1])
        if ln < 126:
            header += bytes([0x80 | ln])
        elif ln < 65536:
            header += bytes([0x80 | 126]) + struct.pack(">H", ln)
        else:
            header += bytes([0x80 | 127]) + struct.pack(">Q", ln)
        mask = os.urandom(4)
        masked = bytes(payload[i] ^ mask[i % 4] for i in range(ln))
        self.sock.sendall(header + mask + masked)

    def send_text(self, text):
        self._send_frame(0x1, text.encode("utf-8"))

    def ping(self, payload=b""):
        self._send_frame(0x9, payload)

    def _parse_one(self):
        """Parse a single frame from self._buf if complete; return (opcode, fin, payload) or None."""
        b = self._buf
        if len(b) < 2:
            return None
        b1, b2 = b[0], b[1]
        fin = bool(b1 & 0x80)
        opcode = b1 & 0x0F
        masked = bool(b2 & 0x80)
        ln = b2 & 0x7F
        idx = 2
        if ln == 126:
            if len(b) < idx + 2:
                return None
            ln = struct.unpack(">H", b[idx:idx + 2])[0]
            idx += 2
        elif ln == 127:
            if len(b) < idx + 8:
                return None
            ln = struct.unpack(">Q", b[idx:idx + 8])[0]
            idx += 8
        mask = b""
        if masked:
            if len(b) < idx + 4:
                return None
            mask = b[idx:idx + 4]
            idx += 4
        if len(b) < idx + ln:
            return None
        payload = b[idx:idx + ln]
        if masked:
            payload = bytes(payload[i] ^ mask[i % 4] for i in range(ln))
        self._buf = b[idx + ln:]
        return opcode, fin, payload

    def pump(self):
        """Recv available bytes; return a list of complete text messages (str). Handles
        ping/pong + close control frames internally."""
        try:
            chunk = self.sock.recv(8192)
            if chunk:
                self._buf += chunk
            elif chunk == b"":
                self.closed = True
        except socket.timeout:
            pass
        except (ssl.SSLWantReadError, BlockingIOError):
            pass
        messages = []
        while True:
            parsed = self._parse_one()
            if parsed is None:
                break
            opcode, fin, payload = parsed
            if opcode == 0x8:                 # close
                self.closed = True
                break
            if opcode == 0x9:                 # ping -> pong
                self._send_frame(0xA, payload)
                continue
            if opcode == 0xA:                 # pong
                continue
            self._msg += payload              # text(0x1)/continuation(0x0)
            if fin:
                try:
                    messages.append(self._msg.decode("utf-8"))
                finally:
                    self._msg = bytearray()
        return messages

    def close(self):
        try:
            if self.sock and not self.closed:
                self._send_frame(0x8, b"")
        except OSError:
            pass
        finally:
            try:
                if self.sock:
                    self.sock.close()
            except OSError:
                pass
            self.closed = True


# --------------------------------------------------------------------------- observer
class LivePublicObserver:
    """Drives a short public connectivity burn-in and records everything to the isolated DB."""

    def __init__(self, *, db: ObservationDB = None, environment="testnet",
                 rest_base=config.APPROVED_TESTNET_REST, ws_url=config.APPROVED_TESTNET_WS,
                 max_age_ms=None):
        # HARD GATES before any network: testnet/exec-off/mainnet-off + NO signing key loaded
        safety.assert_observation_preconditions(endpoint=rest_base)
        safety.assert_observation_preconditions(endpoint=ws_url)
        self.db = db or ObservationDB()
        self.environment = environment
        self.rest_base = rest_base
        self.ws_url = ws_url
        self.max_age_ms = max_age_ms if max_age_ms is not None else config.DEFAULT_MAX_AGE_MS
        self.info = InfoClient(rest_base)
        self.sm = WSConnectionStateMachine()
        self.perp = None
        self.samples = {"all_mids_btc": None, "rest_book_top": None, "ws_book_top": None,
                        "ws_trades": [], "latencies_ms": []}
        self.counts = {"book": 0, "trade": 0, "book_admissible": 0, "trade_admissible": 0,
                       "messages": 0}
        self._prev_book = None
        self._seen_tids = set()
        self._last_trade_ms = None
        self.ws = None

    def _ctx(self):
        return ObsContext(connected=True, env_verified_testnet=True,
                          symbol_verified=self.perp is not None, max_age_ms=self.max_age_ms)

    def identify_instrument(self):
        meta, status = self.info.meta()
        universe = parse_universe(meta)
        self.perp = resolve_perp(meta, config.TARGET_PERP_NAME)
        self.db.append_instrument_observation(self.perp, environment=self.environment,
                                              universe_size=len(universe))
        return self.perp, len(universe)

    def sample_rest(self):
        mids, _ = self.info.all_mids()
        self.samples["all_mids_btc"] = mids.get(config.TARGET_PERP_NAME) if isinstance(mids, dict) else None
        book, _ = self.info.l2_book(config.TARGET_PERP_NAME)
        snap = frame_to_book(book, _now_ms())
        st = self.db.append_book_observation(snap, environment=self.environment,
                                             ctx=self._ctx(), prev=None)
        levels = book.get("levels") or [[], []]
        self.samples["rest_book_top"] = {
            "status": st,
            "best_bid": (levels[0][0] if levels[0] else None),
            "best_ask": (levels[1][0] if levels[1] else None)}
        return self.samples["rest_book_top"]

    def _subscribe(self):
        for sub in ({"type": "l2Book", "coin": config.TARGET_PERP_NAME},
                    {"type": "trades", "coin": config.TARGET_PERP_NAME}):
            self.ws.send_text(json.dumps({"method": "subscribe", "subscription": sub}))

    def _handle_message(self, text):
        try:
            msg = json.loads(text)
        except json.JSONDecodeError:
            return
        ch, data = msg.get("channel"), msg.get("data")
        recv_ms = _now_ms()
        if ch == "l2Book" and isinstance(data, dict):
            snap = frame_to_book(data, recv_ms)
            st = self.db.append_book_observation(snap, environment=self.environment,
                                                 ctx=self._ctx(), prev=self._prev_book)
            self.counts["book"] += 1
            et = data.get("time")
            if isinstance(et, int):
                self.samples["latencies_ms"].append(recv_ms - et)
            if st == "COMPLETE_ADMISSIBLE":
                self.counts["book_admissible"] += 1
                self.samples["ws_book_top"] = {
                    "best_bid": (snap.bids[0] if snap.bids else None),
                    "best_ask": (snap.asks[0] if snap.asks else None),
                    "exch_time_ms": et}
            if st not in ("DUPLICATE", "OUT_OF_ORDER", "EMPTY_BOOK", "ONE_SIDED",
                          "INVALID_VALUE", "INVALID_TIMESTAMP"):
                self._prev_book = snap
        elif ch == "trades" and data:
            for t in frame_to_trades(data, recv_ms):
                st = self.db.append_trade_observation(
                    t, environment=self.environment, ctx=self._ctx(),
                    seen_tids=self._seen_tids, last_trade_time_ms=self._last_trade_ms)
                self.counts["trade"] += 1
                if st == "TRADE_ADMISSIBLE":
                    self.counts["trade_admissible"] += 1
                    if t.tid is not None:
                        self._seen_tids.add(t.tid)
                    try:
                        self._last_trade_ms = int(t.exch_time_ms)
                    except (TypeError, ValueError):
                        pass
                    if len(self.samples["ws_trades"]) < 5:
                        self.samples["ws_trades"].append(
                            {"side": t.side, "px": t.px, "sz": t.sz, "time": t.exch_time_ms})

    def _open_ws(self, reason):
        self.ws = MiniWebSocket(self.ws_url)
        self.ws.connect()
        self.sm.transition("CONNECTED", reason)
        self.db.append_connection_event(environment=self.environment, endpoint=self.ws_url,
                                        connection_state="CONNECTED", reason_code=reason,
                                        reconnect_count=self.sm.reconnects)
        # re-walk the verification states on every (re)connect — never jump to STREAMING
        self.sm.transition("META_LOADED", f"meta universe (perp id={self.perp.asset_id})")
        self.sm.transition("SYMBOL_VERIFIED", f"BTC perp id={self.perp.asset_id}")
        self._subscribe()
        self.sm.transition("SUBSCRIBED", "l2Book+trades subscribe sent")

    def run(self, duration_s=60, max_reconnects=3):
        log = []
        # REST first (no socket yet): identify BTC perp from returned metadata + price/book samples
        self.perp, usize = self.identify_instrument()
        self.sample_rest()
        # WS connection phase, driven by the state machine
        self.sm.transition("CONNECTING", "open websocket")
        self._open_ws("ws handshake ok")

        deadline = time.monotonic() + duration_s
        streaming = False
        last_rx = time.monotonic()
        while time.monotonic() < deadline:
            msgs = self.ws.pump()
            if msgs:
                self.counts["messages"] += len(msgs)
                last_rx = time.monotonic()
                if not streaming:
                    self.sm.transition("STREAMING", "first frames received")
                    streaming = True
                for m in msgs:
                    self._handle_message(m)
            if self.ws.closed or (time.monotonic() - last_rx) > 15:
                # drop / stall -> reconnect if budget allows
                if self.sm.reconnects >= max_reconnects:
                    log.append("max reconnects reached; ending early")
                    break
                self.db.append_connection_event(environment=self.environment, endpoint=self.ws_url,
                                                connection_state="STALLED", reason_code="drop/stall",
                                                reconnect_count=self.sm.reconnects)
                if self.sm.state == "STREAMING":
                    self.sm.transition("STALLED", "drop/stall")
                self.sm.transition("CONNECTING", "reconnect")
                try:
                    self.ws.close()
                except OSError:
                    pass
                self._open_ws("ws reconnect handshake ok")
                streaming = False
                last_rx = time.monotonic()
        return log

    def disconnect(self, reason="clean shutdown"):
        try:
            if self.ws:
                self.ws.close()
        except OSError:
            pass
        if self.sm.state in ("STREAMING", "STALLED", "SUBSCRIBED", "CONNECTED", "CONNECTING"):
            self.sm.transition("CLOSING", reason)
            self.sm.transition("CLOSED", reason)
        self.db.append_connection_event(environment=self.environment, endpoint=self.ws_url,
                                        connection_state="CLOSED", reason_code=reason,
                                        reconnect_count=self.sm.reconnects)
        return self.sm.state
