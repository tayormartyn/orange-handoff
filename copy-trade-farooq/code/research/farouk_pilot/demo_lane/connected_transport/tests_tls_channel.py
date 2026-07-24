"""Item-2 tests: the TLS channel, LOOPBACK ONLY. Every handshake in this file happens on
127.0.0.1 against a throwaway local CA minted in-memory by `cryptography`. The process-wide egress
guard is installed FIRST, and a DNS recorder proves no non-loopback name was ever even queried.
No real connection, no OAuth, no external DNS. Production policy (fixed demo.ctraderapi.com:5035,
required cert + hostname validation, no insecure mode, no override) is asserted structurally.

Run:  .venv-ctrader/Scripts/python.exe -m demo_lane.connected_transport.tests_tls_channel
"""
import datetime
import inspect
import io
import os
import socket
import ssl
import sys
import tempfile
import threading

HERE = os.path.dirname(os.path.abspath(__file__))
FAROUK_PILOT = os.path.dirname(os.path.dirname(HERE))
if FAROUK_PILOT not in sys.path:
    sys.path.insert(0, FAROUK_PILOT)

from demo_lane.connected_transport import egress_guard          # noqa: E402
egress_guard.install_test_egress_guard()                        # FIRST: nothing leaves the machine

# DNS recorder ON TOP of the guard: every host ever passed to getaddrinfo is recorded, so we can
# prove at the end that no non-loopback lookup was even attempted during the TLS tests.
_DNS_SEEN = []
_GUARDED_GAI = socket.getaddrinfo


def _recording_gai(host, *a, **kw):
    _DNS_SEEN.append(host)
    return _GUARDED_GAI(host, *a, **kw)


socket.getaddrinfo = _recording_gai

from demo_lane.connected_transport import (                     # noqa: E402
    credentials as cred, fake_wire, framing, proto_codec, state as st,
    tls_channel as tls, transport as T, transport_config as tc)

PASS = 0


def ok(cond, name):
    global PASS
    assert cond, f"FAIL: {name}"
    PASS += 1


# ================================================================================================
# LOCAL THROWAWAY PKI (cryptography) — a CA + leaf certs with chosen SAN / validity
# ================================================================================================
from cryptography import x509                                   # noqa: E402
from cryptography.hazmat.primitives import hashes, serialization  # noqa: E402
from cryptography.hazmat.primitives.asymmetric import rsa       # noqa: E402
from cryptography.x509.oid import NameOID                       # noqa: E402

_NOW = datetime.datetime.now(datetime.timezone.utc)


def _key():
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


def _name(cn):
    return x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, cn)])


_KU_CA = x509.KeyUsage(digital_signature=False, content_commitment=False, key_encipherment=False,
                       data_encipherment=False, key_agreement=False, key_cert_sign=True,
                       crl_sign=True, encipher_only=False, decipher_only=False)
_KU_LEAF = x509.KeyUsage(digital_signature=True, content_commitment=False, key_encipherment=True,
                         data_encipherment=False, key_agreement=False, key_cert_sign=False,
                         crl_sign=False, encipher_only=False, decipher_only=False)


def make_ca():
    """A throwaway CA carrying the SKI/AKI/keyUsage extensions Python 3.13+'s STRICT verification
    requires."""
    key = _key()
    ski = x509.SubjectKeyIdentifier.from_public_key(key.public_key())
    cert = (x509.CertificateBuilder()
            .subject_name(_name("ORANGE-TEST-CA")).issuer_name(_name("ORANGE-TEST-CA"))
            .public_key(key.public_key()).serial_number(x509.random_serial_number())
            .not_valid_before(_NOW - datetime.timedelta(days=1))
            .not_valid_after(_NOW + datetime.timedelta(days=1))
            .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
            .add_extension(_KU_CA, critical=True)
            .add_extension(ski, critical=False)
            .sign(key, hashes.SHA256()))
    return key, cert


def issue_leaf(ca_key, ca_cert, san_dns, *, expired=False, self_signed=False):
    key = _key()
    nvb = _NOW - datetime.timedelta(days=2 if expired else 1)
    nva = _NOW + (datetime.timedelta(days=-1) if expired else datetime.timedelta(days=1))
    signer_key = key if self_signed else ca_key
    issuer = _name(san_dns) if self_signed else ca_cert.subject
    aki_source = key.public_key() if self_signed else ca_key.public_key()
    cert = (x509.CertificateBuilder()
            .subject_name(_name(san_dns)).issuer_name(issuer)
            .public_key(key.public_key()).serial_number(x509.random_serial_number())
            .not_valid_before(nvb).not_valid_after(nva)
            .add_extension(x509.SubjectAlternativeName([x509.DNSName(san_dns)]), critical=False)
            .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
            .add_extension(_KU_LEAF, critical=True)
            .add_extension(x509.ExtendedKeyUsage([x509.oid.ExtendedKeyUsageOID.SERVER_AUTH]),
                           critical=False)
            .add_extension(x509.SubjectKeyIdentifier.from_public_key(key.public_key()),
                           critical=False)
            .add_extension(x509.AuthorityKeyIdentifier.from_issuer_public_key(aki_source),
                           critical=False)
            .sign(signer_key, hashes.SHA256()))
    return key, cert


def server_context(key, cert):
    """A server-side context from an in-memory key+cert (written to temp files for load_cert_chain)."""
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    with tempfile.NamedTemporaryFile("wb", suffix=".pem", delete=False) as f:
        f.write(cert.public_bytes(serialization.Encoding.PEM))
        f.write(key.private_bytes(serialization.Encoding.PEM,
                                  serialization.PrivateFormat.TraditionalOpenSSL,
                                  serialization.NoEncryption()))
        path = f.name
    try:
        ctx.load_cert_chain(path)
    finally:
        os.unlink(path)
    return ctx


def ca_pem(ca_cert):
    return ca_cert.public_bytes(serialization.Encoding.PEM).decode("ascii")


CA_KEY, CA_CERT = make_ca()

# ================================================================================================
# 1. PRODUCTION POLICY — fixed endpoint, required validation, no insecure mode, no override
# ================================================================================================
ctx = tls.build_client_context()
ok(ctx.check_hostname is True and ctx.verify_mode == ssl.CERT_REQUIRED,
   "client context: certificate AND hostname validation REQUIRED")
ok(ctx.minimum_version >= ssl.TLSVersion.TLSv1_2, "client context: minimum TLS 1.2")
ok(tls.TLS_SERVER_HOSTNAME == "demo.ctraderapi.com" == tc.DEMO_HOST and tc.DEMO_PORT == 5035,
   "fixed identity + endpoint: demo.ctraderapi.com:5035 (single source)")
ok(list(inspect.signature(tls.build_client_context).parameters) == ["test_extra_ca_pem"],
   "no insecure mode: the only context parameter ADDS trust; none can relax validation")
ok(list(inspect.signature(tls.TLSProductionConnector.__init__).parameters) == ["self"],
   "no override: production connector takes NO host/port/flag arguments")
_src = open(tls.__file__.replace(".pyc", ".py"), encoding="utf-8").read()
ok("os.environ" not in _src and "sys.argv" not in _src and "getenv" not in _src
   and "LIVE_HOST" not in _src,
   "no CLI/env override and no live endpoint nameable in tls_channel source")
try:
    tls.TLSProductionConnector().connect()
    ok(False, "production TLS connect must refuse while gates False")
except egress_guard.EgressRefused:
    ok(True, "production TLS connector refuses (gates False) BEFORE any socket exists")
ok(tls.TLSLoopbackConnector.LOOPBACK_HOST == "127.0.0.1"
   and tls.TLSLoopbackConnector(1).host == "127.0.0.1",
   "loopback connector: destination hard-coded to 127.0.0.1 (only the port varies)")

# ================================================================================================
# 2. VALID LOCAL CERT (CA-signed, SAN = demo.ctraderapi.com) -> full lifecycle over TLS + real codec
# ================================================================================================
CODEC = proto_codec.ProtoCodec()
good_key, good_cert = issue_leaf(CA_KEY, CA_CERT, "demo.ctraderapi.com")
broker = fake_wire.FakeBroker(fill_on_open=True)
srv = fake_wire.LoopbackServer(broker, ssl_context=server_context(good_key, good_cert), codec=CODEC)
try:
    conn = tls.TLSLoopbackConnector(srv.port, test_extra_ca_pem=ca_pem(CA_CERT))
    t = T.ConnectedTransport(connector=conn, codec=CODEC,
                             credential_provider=cred.FakeCredentialProvider(ctid=1_000_001),
                             policy=T.test_only_policy())
    ok(t.bring_up() == st.AuthState.READY,
       "valid local cert: TLS handshake + hostname check pass -> full auth sequence -> READY")
    ok(conn._sock is not None and conn._sock.version() in ("TLSv1.2", "TLSv1.3"),
       "the loopback session is really TLS (negotiated TLS 1.2+)")
    t._enqueue_heartbeat()                                 # queued; the sender thread writes it
    deadline = __import__("time").monotonic() + 3.0        # sender+server threads are asynchronous
    while framing.MsgType.HEARTBEAT not in broker.seen and __import__("time").monotonic() < deadline:
        __import__("time").sleep(0.02)
    ok(framing.MsgType.HEARTBEAT in broker.seen,
       "heartbeat travels the TLS channel as a real ProtoMessage")
    t.close()
finally:
    srv.stop()


def _expect_handshake_failure(label, key, cert_, *, trust_ca=True, expect=ssl.SSLError):
    s = fake_wire.LoopbackServer(fake_wire.FakeBroker(),
                                 ssl_context=server_context(key, cert_), codec=CODEC)
    try:
        c = tls.TLSLoopbackConnector(s.port, test_extra_ca_pem=ca_pem(CA_CERT) if trust_ca else None)
        try:
            c.connect()
            c.close()
            ok(False, f"{label}: handshake must FAIL")
        except expect:
            ok(True, label)
    finally:
        s.stop()


# ================================================================================================
# 3-5. UNTRUSTED / HOSTNAME MISMATCH / EXPIRED -> certificate verification fails
# ================================================================================================
uk, uc = issue_leaf(None, None, "demo.ctraderapi.com", self_signed=True)
_expect_handshake_failure("untrusted (self-signed) cert -> verification FAILS",
                          uk, uc, expect=ssl.SSLCertVerificationError)
mk, mc = issue_leaf(CA_KEY, CA_CERT, "wrong-host.invalid")
_expect_handshake_failure("hostname mismatch (SAN != demo.ctraderapi.com) -> verification FAILS",
                          mk, mc, expect=ssl.SSLCertVerificationError)
ek, ec = issue_leaf(CA_KEY, CA_CERT, "demo.ctraderapi.com", expired=True)
_expect_handshake_failure("expired cert -> verification FAILS (harness supports expiry)",
                          ek, ec, expect=ssl.SSLCertVerificationError)

# ================================================================================================
# 6. PLAINTEXT / NON-TLS SERVER -> the TLS client refuses
# ================================================================================================
_plain = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
_plain.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
_plain.bind(("127.0.0.1", 0)); _plain.listen(1)
_plain_port = _plain.getsockname()[1]


def _plain_serve():
    try:
        conn2, _ = _plain.accept()
        conn2.sendall(b"HELLO I AM NOT TLS\r\n")               # plaintext where ServerHello belongs
        conn2.settimeout(5.0)
        try:
            conn2.recv(4096)                                   # hold the socket open so the client
        except OSError:                                        # parses the non-TLS bytes (Windows
            pass                                               # would otherwise abort the connection)
        conn2.close()
    except OSError:
        pass


threading.Thread(target=_plain_serve, daemon=True).start()
try:
    c = tls.TLSLoopbackConnector(_plain_port, test_extra_ca_pem=ca_pem(CA_CERT))
    c.connect()
    ok(False, "plaintext server must be refused")
except ssl.SSLError:
    ok(True, "plaintext / non-TLS endpoint -> handshake refused (SSLError)")
finally:
    _plain.close()

# ================================================================================================
# 7. ZERO EXTERNAL DNS / SOCKET — recorder + guard
# ================================================================================================
ok(_DNS_SEEN and all(egress_guard.is_loopback(h) for h in _DNS_SEEN),
   f"every name resolution in this suite was loopback ({len(_DNS_SEEN)} lookups recorded)")
try:
    socket.getaddrinfo("demo.ctraderapi.com", 5035)
    ok(False, "external DNS must be blocked")
except egress_guard.EgressRefused:
    ok(True, "external DNS (demo.ctraderapi.com) is blocked for the whole suite")

socket.getaddrinfo = _GUARDED_GAI
egress_guard.uninstall_test_egress_guard()

if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    print(f"PASS {PASS} tls-channel checks")
