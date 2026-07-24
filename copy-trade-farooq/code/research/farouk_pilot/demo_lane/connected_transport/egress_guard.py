"""EXTERNAL-EGRESS GUARD — the airtight proof that this package (and its whole test suite) can
NEVER open a socket to any non-loopback endpoint.

Two layers:
  1. assert_endpoint_allowed(host, port, gates_armed): the PRODUCTION policy. The only address that
     may EVER be dialled is the FIXED demo endpoint, and only when the authoritative gates arm it.
     Anything else -> EgressRefused. (Gates are hard False, so production dials nothing.)
  2. install_test_egress_guard(): a process-wide booby-trap for the TEST suite. It patches
     socket.socket.connect / connect_ex AND socket.getaddrinfo so that ANY attempt to reach a
     non-loopback host raises EgressRefused before a packet can leave the machine. Loopback
     (127.0.0.1 / ::1) is the only thing permitted, and only so the loopback lifecycle tests can
     run. demo.ctraderapi.com can neither be resolved nor connected while the guard is installed.
"""
import socket

from . import transport_config as tc

LOOPBACK_HOSTS = {"127.0.0.1", "::1"}
LOOPBACK_NAMES = {"localhost", "ip6-localhost"}


class EgressRefused(Exception):
    """A socket connection to a non-permitted endpoint was refused before egress."""


def is_loopback(host):
    h = str(host)
    return h in LOOPBACK_HOSTS or h in LOOPBACK_NAMES or h.startswith("127.")


def assert_endpoint_allowed(host, port, *, gates_armed):
    """PRODUCTION allow-rule. The fixed demo endpoint is the ONLY dialable address, and only when
    gates arm. No live host is nameable; no override is accepted. Fail-closed on everything else."""
    if not gates_armed:
        raise EgressRefused(f"NOT_ARMED — gates False; refusing to dial {host!r}:{port}")
    if str(host) != tc.DEMO_HOST or int(port) != tc.DEMO_PORT:
        raise EgressRefused(
            f"destination {host!r}:{port} is not the fixed demo endpoint "
            f"{tc.DEMO_HOST}:{tc.DEMO_PORT} — no other endpoint is dialable")
    return True


# ---- test-suite booby-trap ----------------------------------------------------------------------
_ORIG = {}


def install_test_egress_guard():
    """Patch socket egress to loopback-only for the whole test process. Idempotent. Returns an
    uninstall() callable. While installed, connecting to (or resolving) any non-loopback host
    raises EgressRefused — so no test can ever reach a real broker, DNS included."""
    if _ORIG:
        return uninstall_test_egress_guard                    # already installed
    _ORIG["connect"] = socket.socket.connect
    _ORIG["connect_ex"] = socket.socket.connect_ex
    _ORIG["getaddrinfo"] = socket.getaddrinfo

    def _host_of(address):
        # AF_INET/AF_INET6 address tuples lead with the host; anything else is refused outright.
        if isinstance(address, tuple) and address:
            return address[0]
        raise EgressRefused(f"non-inet socket address refused: {address!r}")

    def guarded_connect(self, address):
        host = _host_of(address)
        if not is_loopback(host):
            raise EgressRefused(f"egress blocked (test guard): connect to {host!r} — loopback only")
        return _ORIG["connect"](self, address)

    def guarded_connect_ex(self, address):
        host = _host_of(address)
        if not is_loopback(host):
            raise EgressRefused(f"egress blocked (test guard): connect_ex to {host!r} — loopback only")
        return _ORIG["connect_ex"](self, address)

    def guarded_getaddrinfo(host, *args, **kwargs):
        if host is not None and not is_loopback(host):
            raise EgressRefused(f"DNS blocked (test guard): getaddrinfo({host!r}) — loopback only")
        return _ORIG["getaddrinfo"](host, *args, **kwargs)

    socket.socket.connect = guarded_connect
    socket.socket.connect_ex = guarded_connect_ex
    socket.getaddrinfo = guarded_getaddrinfo
    return uninstall_test_egress_guard


def uninstall_test_egress_guard():
    if not _ORIG:
        return
    socket.socket.connect = _ORIG["connect"]
    socket.socket.connect_ex = _ORIG["connect_ex"]
    socket.getaddrinfo = _ORIG["getaddrinfo"]
    _ORIG.clear()
