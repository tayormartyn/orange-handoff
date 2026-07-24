"""
Brick 3 — automated source scans over broker modules.

(1) NO-ORDER-CODE scan: our broker layer must not DEFINE order/execution methods nor
    IMPORT/expose order-request types. A finding blocks the brick.
(2) SECRET-LEAK scan: no hard-coded secret values, no logging/printing of secret-named
    variables in source.
"""
import os
import re

PROHIBITED_METHODS = ("place_order", "submit_order", "create_order", "modify_order",
                      "cancel_order", "close_position", "execute_trade")
# cTrader Open API order/execution protobuf request types (and generic order-request names).
# Built from fragments so the literal token strings never appear in THIS file's source —
# otherwise the scanner would flag its own pattern list. This keeps the scanner self-covering
# (a genuine order-method definition or order-type reference here would still be detected).
_P, _O, _R = "Proto" + "OA", "Or" + "der", "Re" + "q"
PROHIBITED_TYPES = (
    _P + "New" + _O + _R, _P + "New" + _O, _P + "Cancel" + _O + _R, _P + "Amend" + _O + _R,
    _P + "ClosePosition" + _R, _P + "AmendPositionSLTP" + _R,
    "New" + _O + "Request", _O + "Request", "Execute" + _O + "Request",
)

_SECRET_ASSIGN = re.compile(
    r"(client_secret|access_token|refresh_token|authoris\w*_code|authoriz\w*_code|"
    r"bearer|oauth_verifier)\s*=\s*[\"'][^\"']+[\"']", re.I)
_SECRET_LOG = re.compile(
    r"(print|log\w*)\s*\([^)]*(client_secret|access_token|refresh_token|bearer|verifier)",
    re.I)


def _py_files(path):
    if os.path.isfile(path) and path.endswith(".py"):
        yield path
        return
    for root, _dirs, files in os.walk(path):
        for f in files:
            if f.endswith(".py"):
                yield os.path.join(root, f)


def scan_no_order_code(paths):
    """Return list of (file, kind, token) violations."""
    violations = []
    for p in paths:
        for fp in _py_files(p):
            txt = open(fp, encoding="utf-8").read()
            for m in PROHIBITED_METHODS:
                if re.search(rf"def\s+{re.escape(m)}\b", txt):
                    violations.append((fp, "order-method-def", m))
            for t in PROHIBITED_TYPES:
                if re.search(rf"\b{re.escape(t)}\b", txt):
                    violations.append((fp, "order-type-ref", t))
    return violations


def scan_secret_leaks(paths):
    """Return list of (file, lineno, kind) for hard-coded secrets or secret logging."""
    findings = []
    for p in paths:
        for fp in _py_files(p):
            for i, line in enumerate(open(fp, encoding="utf-8").read().splitlines(), 1):
                if _SECRET_ASSIGN.search(line):
                    findings.append((fp, i, "hardcoded-secret"))
                if _SECRET_LOG.search(line):
                    findings.append((fp, i, "secret-in-log"))
    return findings
