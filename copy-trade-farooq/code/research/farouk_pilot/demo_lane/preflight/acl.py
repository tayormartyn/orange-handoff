"""Windows ACL provisioning + verification for the two-identity separation.

Proves (once the two OS principals are provisioned by an administrator):
  1. EXECUTOR identity CANNOT create / modify / rename / delete immutable approvals.
  2. APPROVAL-TOOL identity CANNOT place orders — modelled as: it has NO write on the
     executor outbox/intent store (the only filesystem path an order intent is written to).
  3. EXECUTOR identity MAY write ONLY its own consumption (receipts) and outbox stores.

The three OS principals are created by an administrator at deploy time (a system change
outside this read-only tool). This module EMITS the exact icacls commands and provides a
VERIFIER that reads back `icacls <dir>` output and asserts the required ALLOW/DENY ACEs.
The verifier is proven here against real icacls output (see tests) so its parsing is
trustworthy before it is pointed at the provisioned principals.
"""
import re
import subprocess

# permission letters we assert. icacls masks: W=write, D=delete, DC=delete child,
# WD=write data/add file, AD=append data/add subdir, RC/GR etc for read.
DENY_WRITE_MASKS = ("W", "WD", "AD", "D", "DC")


def provisioning_commands(approvals_dir, receipts_dir, outbox_dir,
                          executor_identity="ORANGE_EXECUTOR",
                          approval_identity="ORANGE_APPROVER"):
    """Return the icacls commands that establish the separation. Administrator runs these
    once, after creating the two local accounts. Parameterised — no identity is hardcoded
    into enforcement."""
    return [
        # approvals_dir: approver has full control; executor is READ-ONLY + explicit DENY
        # on every mutating right (create/modify/rename/delete).
        f'icacls "{approvals_dir}" /inheritance:r',
        f'icacls "{approvals_dir}" /grant:r "{approval_identity}:(OI)(CI)(F)"',
        f'icacls "{approvals_dir}" /grant:r "{executor_identity}:(OI)(CI)(RX)"',
        f'icacls "{approvals_dir}" /deny "{executor_identity}:(OI)(CI)(WD,AD,DC,DE,WA)"',
        # receipts_dir + outbox_dir: executor may write; approver has NO write (so the
        # approval identity cannot produce an order intent -> cannot place orders).
        f'icacls "{receipts_dir}" /inheritance:r',
        f'icacls "{receipts_dir}" /grant:r "{executor_identity}:(OI)(CI)(M)"',
        f'icacls "{receipts_dir}" /deny "{approval_identity}:(OI)(CI)(WD,AD,DC,DE,WA)"',
        f'icacls "{outbox_dir}" /inheritance:r',
        f'icacls "{outbox_dir}" /grant:r "{executor_identity}:(OI)(CI)(M)"',
        f'icacls "{outbox_dir}" /deny "{approval_identity}:(OI)(CI)(WD,AD,DC,DE,WA)"',
    ]


_ACE_RE = re.compile(r"^\s*([^:]+):\(([^)]*(?:\)\([^)]*)*)\)\s*$")


def parse_icacls(output):
    """Parse `icacls <path>` output into {identity: [raw_ace_strings]}. Tolerant of the
    multi-group icacls format e.g. `IDENT:(OI)(CI)(DENY)(WD,AD)`."""
    aces = {}
    for line in output.splitlines():
        line = line.rstrip()
        if not line or line.strip().startswith("Successfully") or "processed file" in line:
            continue
        # capture ONLY the principal token before ':(' — this strips any leading path
        # token on icacls' first line ("C:\dir IDENT:(...)") and any DOMAIN\ prefix,
        # since the identity class excludes spaces, colons, and backslashes.
        m = re.search(r"([^\s:\\/]+):(\(.*\))\s*$", line)
        if not m:
            continue
        ident = m.group(1).strip()
        aces.setdefault(ident, []).append(m.group(2))
    return aces


def _has_deny_write(ace_strings):
    joined = " ".join(a.upper() for a in ace_strings)
    if "(DENY)" not in joined and "DENY" not in joined:
        return False
    return any(f"({m}" in joined or f",{m}" in joined or f"{m})" in joined
               for m in DENY_WRITE_MASKS)


def _has_any_write_allow(ace_strings):
    joined = " ".join(a.upper() for a in ace_strings)
    if "(DENY)" in joined:
        return False
    return any(t in joined for t in ("(F)", "(M)", "(W)", "(WD", "(AD", "(RX,W"))


def verify_approvals_acl(icacls_output, executor_identity, approval_identity):
    """Assert: executor is DENIED write on approvals; approver CAN write approvals."""
    aces = parse_icacls(icacls_output)
    ex = aces.get(executor_identity, [])
    ap = aces.get(approval_identity, [])
    return {
        "executor_denied_write": _has_deny_write(ex),
        "approver_can_write": _has_any_write_allow(ap),
        "ok": _has_deny_write(ex) and _has_any_write_allow(ap),
    }


def verify_executor_store_acl(icacls_output, executor_identity, approval_identity):
    """Assert (for receipts/outbox): executor CAN write; approver is DENIED write (so the
    approval identity cannot create an order intent -> cannot place orders)."""
    aces = parse_icacls(icacls_output)
    ex = aces.get(executor_identity, [])
    ap = aces.get(approval_identity, [])
    return {
        "executor_can_write": _has_any_write_allow(ex),
        "approver_denied_write": _has_deny_write(ap),
        "ok": _has_any_write_allow(ex) and _has_deny_write(ap),
    }


def read_icacls(path):
    """Run `icacls <path>` and return stdout (real Windows call)."""
    r = subprocess.run(["icacls", path], capture_output=True, text=True)
    return r.stdout
