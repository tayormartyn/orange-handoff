"""TLS channel for the connected transport (completion item 2 — LOOPBACK-TESTED ONLY).

PRODUCTION POLICY (fixed; nothing here is overridable by caller, CLI or environment):
  * the ONLY dialable endpoint is the fixed demo endpoint demo.ctraderapi.com:5035 — re-checked
    through egress_guard.assert_endpoint_allowed with the authoritative gates (all False, so the
    production connector refuses before any socket exists);
  * certificate validation is REQUIRED (ssl.CERT_REQUIRED against the system trust store);
  * hostname validation is REQUIRED and always against TLS_SERVER_HOSTNAME (= the fixed demo host);
  * there is NO insecure mode: no function or parameter in this module can set check_hostname False,
    relax verify_mode, change the validated hostname, or name a different endpoint.

TEST SEAM: TLSLoopbackConnector (IS_MOCK) dials 127.0.0.1 ONLY (the address is hard-coded; only the
ephemeral port is a parameter) and may add a TEST CA to the trust store so a local server cert can
verify — but hostname validation still runs against demo.ctraderapi.com and cannot be relaxed, so
the loopback tests prove the SAME validation path production would use. No real connection is made
anywhere: gates are False and the test egress guard blocks every non-loopback socket and DNS call.
"""
import socket
import ssl

from . import egress_guard
from . import transport_config as tc

# the ONE identity certificates are ever validated against (== the fixed demo host)
TLS_SERVER_HOSTNAME = tc.DEMO_HOST
TLS_MIN_VERSION = ssl.TLSVersion.TLSv1_2
CONNECT_TIMEOUT_S = 10


def build_client_context(test_extra_ca_pem=None):
    """The ONLY client TLS context this package can produce. check_hostname and CERT_REQUIRED are
    unconditional — no parameter exists to disable them. `test_extra_ca_pem` may ADD a trust anchor
    (loopback tests with a local CA); it can never relax validation or change the hostname policy."""
    ctx = ssl.create_default_context(purpose=ssl.Purpose.SERVER_AUTH)
    ctx.check_hostname = True
    ctx.verify_mode = ssl.CERT_REQUIRED
    ctx.minimum_version = TLS_MIN_VERSION
    if test_extra_ca_pem is not None:
        ctx.load_verify_locations(cadata=test_extra_ca_pem)
    return ctx


class _FramedTLSSocket:
    """Shared send/recv mechanics over an established TLS socket (timeout -> None, like the other
    connectors, so the transport's OUTCOME_UNKNOWN path is preserved)."""
    def __init__(self):
        self._sock = None

    @property
    def connected(self):
        return self._sock is not None

    def send(self, frame_bytes):
        if self._sock is None:
            raise ConnectionError("TLS channel not connected")
        self._sock.sendall(frame_bytes)

    def recv(self, timeout=None):
        if self._sock is None:
            raise ConnectionError("TLS channel not connected")
        if timeout is not None:
            self._sock.settimeout(timeout)
        try:
            data = self._sock.recv(4096)
            return data or None
        except (socket.timeout, ssl.SSLWantReadError):
            return None

    def close(self):
        if self._sock is not None:
            try:
                self._sock.close()
            finally:
                self._sock = None


class TLSProductionConnector(_FramedTLSSocket):
    """The production TLS connector. FIXED endpoint (takes no host/port); full certificate +
    hostname validation against the fixed demo identity. connect() first runs the egress allow-rule
    with the authoritative gates — all False, so it refuses before any socket is created."""
    IS_MOCK = False

    def __init__(self):
        super().__init__()
        self.host, self.port = tc.DEMO_HOST, tc.DEMO_PORT

    def connect(self):
        egress_guard.assert_endpoint_allowed(self.host, self.port, gates_armed=tc.production_armed())
        ctx = build_client_context()
        raw = socket.create_connection((self.host, self.port), timeout=CONNECT_TIMEOUT_S)
        try:
            self._sock = ctx.wrap_socket(raw, server_hostname=TLS_SERVER_HOSTNAME)
        except BaseException:
            raw.close()
            raise


class TLSLoopbackConnector(_FramedTLSSocket):
    """TEST-ONLY TLS connector: dials 127.0.0.1 (hard-coded — only the ephemeral port varies) and
    validates the server certificate against demo.ctraderapi.com exactly as production would. The
    optional test CA is ADDITIVE trust only; validation itself is not relaxable."""
    IS_MOCK = True
    LOOPBACK_HOST = "127.0.0.1"

    def __init__(self, port, test_extra_ca_pem=None):
        super().__init__()
        self.host, self.port = self.LOOPBACK_HOST, int(port)
        self._ca_pem = test_extra_ca_pem

    def connect(self):
        ctx = build_client_context(test_extra_ca_pem=self._ca_pem)
        raw = socket.create_connection((self.host, self.port), timeout=CONNECT_TIMEOUT_S)
        try:
            # hostname validation ALWAYS against the fixed demo identity — never the dialed IP
            self._sock = ctx.wrap_socket(raw, server_hostname=TLS_SERVER_HOSTNAME)
        except BaseException:
            raw.close()
            raise
