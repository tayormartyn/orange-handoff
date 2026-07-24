"""
ASSOC-1 no-mutation source/dependency scan.

Targets EXECUTABLE code paths only: it tokenises each module and inspects NAME tokens,
ignoring comments, docstrings, and string literals — so prohibited terms appearing inside
negative-test fixtures or documentation do NOT trigger a violation. A finding means ASSOC-1
imports/references a campaign-mutation repository, a reducer that applies events, a broker/
exchange module, or order/stop-management execution code.
"""
from __future__ import annotations
import os
import tokenize

# forbidden EXECUTABLE identifiers (modules, classes, methods)
FORBIDDEN = {
    # campaign mutation repositories / reducers / event application
    "campaigns_db", "CampaignsDB", "event_store", "reducer", "apply_event",
    "append_campaign", "append_campaign_event", "append_legacy_mapping",
    "RegistryDB", "registry_db",
    # broker / exchange / credential modules
    "broker_readonly", "ctrader_auth", "ctrader_config", "hyperliquid", "twisted",
    # order / stop / execution methods
    "place_order", "submit_order", "create_order", "modify_order", "cancel_order",
    "close_position", "execute_trade", "move_stop", "partial_close",
}


def _py_files(path):
    if os.path.isfile(path) and path.endswith(".py"):
        yield path
        return
    for root, _d, files in os.walk(path):
        if os.sep + "tests" in root + os.sep:        # executable engine code only
            continue
        for f in files:
            if f.endswith(".py"):
                yield os.path.join(root, f)


def _code_names(path):
    names = set()
    with open(path, "rb") as f:
        for tok in tokenize.tokenize(f.readline):
            if tok.type == tokenize.NAME:
                names.add(tok.string)
    return names


def scan_no_mutation(paths):
    """Return [(file, forbidden_identifier)] for any prohibited executable reference."""
    violations = []
    for p in paths:
        for fp in _py_files(p):
            for ident in sorted(FORBIDDEN & _code_names(fp)):
                violations.append((fp, ident))
    return violations
