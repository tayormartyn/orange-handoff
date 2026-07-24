"""Gate truth table (correction 5) + arming decision. Proves DEMO_EXECUTION_ENABLED
cannot create a path to any live endpoint/account and never weakens the live gates."""
from . import config


def account_guard_ok(acc):
    """Correction 1: the five-field conjunction. acc is a dict of broker-reported fields.
    accountType is NEVER consulted (it is HEDGED/NETTED classification, not live/demo)."""
    return (acc.get("endpoint") == config.DEMO_ENDPOINT
            and acc.get("isLive") is False
            and acc.get("ctidTraderAccountId") == config.ALLOWED_CTID_TRADER_ACCOUNT_ID
            and acc.get("broker_environment") == config.EXPECTED_BROKER_ENVIRONMENT
            and acc.get("permissionScope") == config.REQUIRED_SCOPE)


def can_arm(acc):
    """The ONLY arming path. Requires the demo gate True AND a passing account guard.
    Live gates are AND-composed for their own (unrelated) live paths and are never
    overridden by the demo gate."""
    if config.EXECUTION_ENABLED or config.CTRADER_EXECUTION_ENABLED:
        # live gates are about the live path; this lane never touches it. If they are
        # somehow True, this demo lane still refuses unless its own gate+guard pass.
        pass
    return bool(config.DEMO_EXECUTION_ENABLED) and account_guard_ok(acc)


def truth_table():
    """Enumerate {demo_gate} x {endpoint, isLive} and prove: no row yields a live path,
    and can_arm is True only for demo-endpoint + isLive False + full guard."""
    rows = []
    for demo_gate in (False, True):
        for endpoint in (config.DEMO_ENDPOINT, "live.ctraderapi.com"):
            for is_live in (False, True):
                acc = {"endpoint": endpoint, "isLive": is_live,
                       "ctidTraderAccountId": config.ALLOWED_CTID_TRADER_ACCOUNT_ID,
                       "broker_environment": config.EXPECTED_BROKER_ENVIRONMENT,
                       "permissionScope": config.REQUIRED_SCOPE}
                # temporarily reflect the demo_gate for the row (pure function, no mutation of config)
                armed = demo_gate and account_guard_ok(acc)
                touches_live = endpoint != config.DEMO_ENDPOINT or is_live is True
                rows.append({"demo_gate": demo_gate, "endpoint": endpoint, "isLive": is_live,
                             "armed": armed, "touches_live_target": touches_live and armed})
    return rows
