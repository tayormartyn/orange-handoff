"""READ_ONLY_DEMO_PREFLIGHT_v0_1 — orchestrator + CLI.

Assembles a VIEW-ONLY preflight package for Martyn from a supplied read-only broker
adapter. It performs NO order/position action and imports NO order/close message. It:
  1. verifies the connection is the allowlisted Pepperstone DEMO account, isLive False,
     with the GRANTED scope observed and required to be view-only (SCOPE_TRADE -> refuse);
  2. retrieves read-only XAUUSD metadata;
  3. reports CANDIDATE quantity conversions (never selecting/rounding/ratifying);
  4. redacts the account identity to hash + last four.

Default invocation is DRY-RUN against the mock read broker (no network, no OAuth), which
proves the logic. A live read requires Martyn's accounts-scope OAuth grant AND an explicit
opt-in (preflight_config.LIVE_READ_OPT_IN); this tool never performs the OAuth grant itself.
"""
import json
import sys

from . import preflight_config as cfg
from . import verify, metadata, conversions, credentials
from .mock_read_broker import MockReadOnlyBroker


def build_report(broker):
    """Produce the read-only preflight package from a read-only broker adapter."""
    account = broker.account_info()

    # (1) connection verification — observed values retained; scope reported AS OBSERVED
    v = verify.check(account)

    # redact account identity in the returned package to hash + last4
    redacted = credentials.redact_account(account.get("ctidTraderAccountId"))

    report = {
        "tool": cfg.TOOL_VERSION,
        "mode": "LIVE_READ" if cfg.LIVE_READ_OPT_IN else "DRY_RUN_MOCK",
        "connection": {
            "endpoint_observed": account.get("endpoint"),
            "isLive_observed": account.get("isLive"),
            "account_redacted": redacted,
            "broker_environment_observed": account.get("broker_environment"),
            "granted_scope_observed": v["scope"]["granted_scope_observed"],
            "granted_scope_is_view_only": v["scope"]["is_view_only"],
            "granted_scope_is_trading": v["scope"]["is_trading"],
            "field_verdicts": v["fields"],
            "view_only_verification_ok": v["ok"],
        },
        "refused": None,
    }

    # fail closed: if the grant is a trading scope, or verification fails, REFUSE and stop —
    # do not retrieve metadata or present candidates under an unverified/over-scoped grant.
    if v["scope"]["is_trading"]:
        report["refused"] = ("granted permission is SCOPE_TRADE (trading). Out of scope for a "
                             "view-only preflight. Revoke and re-grant 'accounts' only.")
        return report
    if not v["ok"]:
        failed = [k for k, f in v["fields"].items() if not f["ok"]]
        report["refused"] = f"view-only verification failed on {failed}"
        return report

    # (2) read-only XAUUSD metadata
    raw = broker.symbol_meta(cfg.GOLD_SYMBOL)
    md = metadata.normalise(raw)
    report["xauusd_metadata"] = md

    # (3) CANDIDATE conversions (no selection, no rounding)
    report["candidate_conversions"] = conversions.candidate_table(
        cfg.candidate_nominal_lots(),
        {"lotSize": md["volume"]["lot_size"], "minVolume": md["volume"]["min_volume"],
         "maxVolume": md["volume"]["max_volume"], "stepVolume": md["volume"]["step_volume"]})

    report["ratification_required"] = (
        "Martyn must ratify a specific (nominal_lots, protocol_volume) pair knowingly. "
        "This tool selected nothing and rounded nothing.")
    return report


def _live_broker():
    """Placeholder for the view-only client used during the separately-authorised burn-in.
    It is NOT wired here: this tool never performs the OAuth grant and never imports order
    messages. Enabling it requires Martyn's accounts-scope token AND LIVE_READ_OPT_IN."""
    raise NotImplementedError(
        "Live read is not wired into this tool. Perform the accounts-scope OAuth grant "
        "(see OAUTH_INSTRUCTIONS_FOR_MARTYN.md), then the view-only read client is attached "
        "during the separately-authorised activation burn-in — never by this preflight tool.")


def main(argv=None):
    argv = argv or sys.argv[1:]
    if cfg.LIVE_READ_OPT_IN:
        broker = _live_broker()          # will raise until the burn-in wires it, by design
    else:
        broker = MockReadOnlyBroker()
    report = build_report(broker)
    print(json.dumps(report, indent=2, default=str))
    return 0 if report.get("refused") is None else 1


if __name__ == "__main__":
    sys.exit(main())
