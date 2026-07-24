"""Account allowlist for the fail-closed guard. The real ctidTraderAccountId is NEVER hardcoded
or guessed. It starts UNPINNED (no store file -> pinned_ctid() is None) and the guard REFUSES
while unpinned (empty allowlist = no match = stop). In Phase 2 the operator pins the id that the
FIRST account-list read returns (allowlist.pin_ctid), and only then can the account check pass.

The pinned id is not a secret, but it lives OUTSIDE the repository tree (%LOCALAPPDATA%\\Orange)
alongside the other preflight state, and is REDACTED to hash+last4 in every report.
"""
import json
import os

_ENV_DIR = "ORANGE_PREFLIGHT_STORE_DIR"   # test/override hook; default is %LOCALAPPDATA%\Orange
_FILENAME = "ctrader_preflight_allowed_ctid.json"


def _store_dir():
    return os.environ.get(_ENV_DIR) or os.path.join(
        os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "Orange")


def pin_path():
    return os.path.join(_store_dir(), _FILENAME)


def pinned_ctid():
    """Return the pinned ctidTraderAccountId as int, or None if the allowlist is UNPINNED."""
    p = pin_path()
    if not os.path.exists(p):
        return None
    try:
        with open(p, encoding="utf-8") as f:
            v = json.load(f).get("ctidTraderAccountId")
        return int(v) if v is not None else None
    except (ValueError, OSError, json.JSONDecodeError):
        return None      # unreadable / malformed -> treat as UNPINNED (fail closed)


def is_pinned():
    return pinned_ctid() is not None


def pin_ctid(ctid, source_note="pinned from first account-list read (Phase 2)"):
    """Phase-2, operator-authorised: pin the id the first account-list read returned. Refuses to
    silently overwrite a DIFFERENT already-pinned id (raises); re-pinning the same id is a no-op."""
    existing = pinned_ctid()
    if existing is not None and existing != int(ctid):
        raise ValueError("allowlist already pinned to a different account; clear it deliberately "
                         "before re-pinning (no silent overwrite)")
    os.makedirs(_store_dir(), exist_ok=True)
    with open(pin_path(), "w", encoding="utf-8") as f:
        json.dump({"ctidTraderAccountId": int(ctid), "source_note": source_note}, f)
    return int(ctid)


def clear_pin():
    """Deliberate reset (operator/test). Removes the pin so the allowlist is UNPINNED again."""
    p = pin_path()
    if os.path.exists(p):
        os.remove(p)


def store_is_outside_repo(repo_root):
    return not os.path.abspath(pin_path()).startswith(os.path.abspath(repo_root) + os.sep)
