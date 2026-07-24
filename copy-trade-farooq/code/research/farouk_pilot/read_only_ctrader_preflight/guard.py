"""Fail-closed account guard. Proceed ONLY when every field passes; otherwise stop with a
SANITISED error (no secrets, no raw account id) and a non-zero exit. Never fail open."""
import sys

from . import config, allowlist


class PreflightRefusal(Exception):
    """Any field failing the fail-closed conjunction. Caller stops + exits non-zero."""


def assess(observed):
    """observed: dict of locally-checked facts. Returns {ok, fields} with every observed value
    retained for the (redacted) report. Does NOT raise — the caller decides — so the report can
    show exactly which field failed."""
    endpoint = observed.get("endpoint")
    port = observed.get("port")
    scope = observed.get("granted_scope")
    fields = {
        "endpoint": {"observed": endpoint, "expected": config.DEMO_HOST,
                     "ok": endpoint == config.DEMO_HOST},
        "port": {"observed": port, "expected": config.DEMO_PORT, "ok": port == config.DEMO_PORT},
        "granted_scope_view_only": {
            "observed": scope, "expected": config.REQUIRED_GRANTED_SCOPE,
            "ok": scope == config.REQUIRED_GRANTED_SCOPE and scope != config.REFUSED_GRANTED_SCOPE},
        "isLive_false": {"observed": observed.get("isLive"), "expected": False,
                         "ok": observed.get("isLive") is False},
        # UNPINNED allowlist => pinned is None => ok is False => REFUSE (never passes unpinned).
        "account_allowlisted": {
            "observed": "<redacted>",
            "expected": "<pinned demo account>" if allowlist.is_pinned() else "<UNPINNED - refuse>",
            "ok": allowlist.pinned_ctid() is not None
            and observed.get("ctidTraderAccountId") == allowlist.pinned_ctid()},
        "environment_expected": {
            "observed": observed.get("environment"), "expected": config.EXPECTED_ENVIRONMENT,
            "ok": observed.get("environment") == config.EXPECTED_ENVIRONMENT},
        "xauusd_unambiguous": {
            "observed": observed.get("xauusd_symbol_count"), "expected": 1,
            "ok": observed.get("xauusd_symbol_count") == 1},
    }
    return {"ok": all(f["ok"] for f in fields.values()), "fields": fields}


def require_or_exit(observed):
    """Fail-closed gate. Returns the verdict on success; on ANY failure prints a SANITISED
    error and exits non-zero. A SCOPE_TRADE grant is called out explicitly."""
    v = assess(observed)
    if observed.get("granted_scope") == config.REFUSED_GRANTED_SCOPE:
        _stop("granted permission is SCOPE_TRADE (trading). Out of scope for a view-only "
              "preflight. Revoke the app authorization and re-grant 'accounts' (view-only) only.")
    if not v["ok"]:
        failed = [k for k, f in v["fields"].items() if not f["ok"]]
        _stop(f"fail-closed account guard refused on: {failed}")
    return v


def _stop(msg):
    # SANITISED: message names the failing condition, never a secret or the raw account id.
    sys.stderr.write(f"[PREFLIGHT-REFUSED] {msg}\n")
    raise PreflightRefusal(msg)
