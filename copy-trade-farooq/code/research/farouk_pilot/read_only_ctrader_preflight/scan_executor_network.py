"""FIRST-REVIEWER CONDITION: prove EXECUTOR_NETWORK_CAPABILITY == ZERO with the networked
read-only preflight package PRESENT in the repo. A shared import must not have created a
network path into the demo-lane executor.

The demo-lane executor imports only demo_lane modules (`from . import ...`), so the executor's
import closure is the demo_lane package + stdlib. This scan asserts:
  (1) no demo_lane module imports any network module (socket/ssl/requests/websocket/
      ctrader_open_api/twisted) or performs a socket .connect();
  (2) no demo_lane module imports the read_only_ctrader_preflight package (no shared path);
  (3) no demo_lane module imports anything outside demo_lane except stdlib (closure check).
Exit 0 + 'EXECUTOR_NETWORK_CAPABILITY = ZERO' on pass; non-zero + the offending line on fail.
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DEMO_LANE = os.path.abspath(os.path.join(HERE, "..", "demo_lane"))

NET_TOKENS = ("import socket", "import ssl", "import requests", "websocket",
              "ctrader_open_api", "twisted", "http.client", "urllib.request",
              "asyncio.open_connection", ".connect(")
PREFLIGHT_TOKENS = ("read_only_ctrader_preflight",)
_STDLIB_OR_LOCAL = re.compile(r"^\s*(from|import)\s+(?P<mod>[\w\.]+)")


def scan():
    findings = []
    imports_outside = []
    for fn in sorted(os.listdir(DEMO_LANE)):
        if not fn.endswith(".py"):
            continue
        path = os.path.join(DEMO_LANE, fn)
        for i, line in enumerate(open(path, encoding="utf-8"), 1):
            s = line.strip()
            if s.startswith("#"):
                continue
            for tok in NET_TOKENS:
                if tok in line:
                    findings.append((fn, i, "NETWORK", tok, s))
            for tok in PREFLIGHT_TOKENS:
                if tok in line:
                    findings.append((fn, i, "PREFLIGHT_IMPORT", tok, s))
            m = _STDLIB_OR_LOCAL.match(line)
            if m:
                mod = m.group("mod").split(".")[0]
                if mod not in _ALLOWED_MODS:
                    imports_outside.append((fn, i, mod, s))
    return findings, imports_outside


# stdlib + the demo_lane package's own relative imports (`from . import ...` -> mod == '')
_ALLOWED_MODS = {
    "", "hashlib", "json", "os", "sys", "re", "time", "datetime", "math", "decimal",
    "fractions", "collections", "itertools", "functools", "typing", "dataclasses",
    "enum", "pathlib", "io", "tempfile", "unittest", "random", "string", "abc",
    "secrets", "importlib", "warnings", "contextlib", "base64", "struct", "uuid", "copy",
}


def main():
    findings, imports_outside = scan()
    net = [f for f in findings if f[2] == "NETWORK"]
    pre = [f for f in findings if f[2] == "PREFLIGHT_IMPORT"]
    print("=== EXECUTOR ZERO-NETWORK SCAN (preflight present) ===")
    print(f"  demo_lane modules scanned: {sum(1 for x in os.listdir(DEMO_LANE) if x.endswith('.py'))}")
    print(f"  network imports found:            {len(net)}")
    print(f"  preflight imports into demo_lane: {len(pre)}")
    print(f"  imports outside demo_lane+stdlib: {len(imports_outside)}")
    for f in net + pre:
        print(f"    OFFENDING {f[0]}:{f[1]} [{f[2]}] {f[4]!r}")
    for f in imports_outside:
        print(f"    NON-STDLIB IMPORT {f[0]}:{f[1]} module={f[2]} {f[3]!r}")
    ok = not net and not pre and not imports_outside
    print(f"\n  EXECUTOR_NETWORK_CAPABILITY = {'ZERO' if ok else 'NON-ZERO -- FAILURE'}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
