"""
Demo cTrader client. THIS PHASE: read-only preflight (account + symbol metadata) via an INJECTED
fetcher (mocked in tests; a real read-only runner may be supplied), and a submit_order() that
ALWAYS REFUSES — it never calls a broker order endpoint. There is no live endpoint in this package.
Secrets/tokens are never returned or printed.
"""
from __future__ import annotations

import config as CFG
import account_guard
from models import AccountSnapshot, SymbolMeta


def preflight(*, account_fetch, symbol_fetch):
    """account_fetch() -> AccountSnapshot ; symbol_fetch() -> SymbolMeta. Both injected (read-only).
    The real fetchers perform read-only cTrader reads (ProtoOATrader / ProtoOASymbolById) under
    .venv-ctrader; tests pass mocks. NO order request is made here."""
    account = account_fetch()
    symbol = symbol_fetch()
    return account, symbol


def submit_order(proposal, *, account, token_scope, disable_path=None, transport=None,
                 order_sending_enabled=None):
    """REFUSES to send in this phase. Even when later enabled, it will fail closed unless the full
    demo firewall passes. It NEVER falls back to a live endpoint. Returns a status dict; sends nothing."""
    ose = CFG.ORDER_SENDING_ENABLED if order_sending_enabled is None else order_sending_enabled
    if not ose:
        return {"sent": False, "reason": "ORDER_SENDING_DISABLED_DRY_RUN_PHASE",
                "endpoint_called": False}
    fw = account_guard.demo_firewall(account=account, instrument=proposal.instrument,
                                     token_scope=token_scope, disable_path=disable_path,
                                     order_sending_enabled=ose)
    if not fw.all_passed:
        return {"sent": False, "reason": "FIREWALL_BLOCKED", "endpoint_called": False,
                "firewall": fw.as_dict()}
    # Even with everything green, this build has no order endpoint wired. Fail closed.
    return {"sent": False, "reason": "ORDER_ENDPOINT_NOT_WIRED_THIS_PHASE", "endpoint_called": False}
