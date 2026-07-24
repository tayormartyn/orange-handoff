"""READ_ONLY_CTRADER_PREFLIGHT_v0_1 - CLI orchestrator.

Phase 1 (default): STATIC proof - print the fixed authority + scope, run the fail-closed guard
against supplied observed facts, redact the account. NO OAuth, NO socket, NO connect.
Phase 2 (--connect): gated behind the operator's accounts-scope grant + ORANGE_PREFLIGHT_CONNECT=1;
NOT run in Phase 1. It would verify the guard against LIVE-observed facts then read XAUUSD
metadata via the view-only transport - never here.
"""
import json
import sys

from . import config, guard, credentials, allowlist


def static_report(observed=None):
    """Phase-1 static readiness + fail-closed guard verdict. No network."""
    rep = {
        "tool": config.TOOL_VERSION,
        "phase": "1_STATIC",
        "authority": {"host": config.DEMO_HOST, "port": config.DEMO_PORT,
                      "live_path_exists": False},
        "oauth": {"emit_scope": config.OAUTH_EMIT_SCOPE,
                  "required_granted_scope": config.REQUIRED_GRANTED_SCOPE,
                  "refused_scope": config.REFUSED_GRANTED_SCOPE},
        # allowlist starts UNPINNED; guard refuses until the real id is pinned in Phase 2.
        "allowlist": {"pinned": allowlist.is_pinned()},
        "connect_opt_in": config.PHASE2_CONNECT_OPT_IN,
    }
    if observed is not None:
        v = guard.assess(observed)
        rep["guard"] = {"ok": v["ok"], "fields": v["fields"]}
        if "ctidTraderAccountId" in observed:
            rep["account_redacted"] = credentials.redact_account(observed["ctidTraderAccountId"])
    return rep


def main(argv=None):
    argv = argv if argv is not None else sys.argv[1:]
    if "--connect" in argv:
        # Phase 2 - explicitly NOT executed in this build.
        print("[PHASE 2] Live connect is gated. Perform the accounts-scope OAuth grant "
              "(see OAUTH_INSTRUCTIONS.md), set ORANGE_PREFLIGHT_CONNECT=1, then a separately "
              "authorised run performs the view-only read. This Phase-1 build does not connect.")
        return 2
    print(json.dumps(static_report(), indent=2, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
