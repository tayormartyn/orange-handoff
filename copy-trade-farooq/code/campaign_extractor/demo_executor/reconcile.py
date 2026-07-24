"""
Future submission reconciliation — DESIGNED, NOT ENABLED. Documents the required behaviour for the
later ORDER_* phase: on a submission timeout the system MUST reconcile existing broker orders before
any retry — never blind resubmission. No function here contacts a broker; calling submit_reconciled()
raises to make clear it is not enabled this phase.
"""
from __future__ import annotations

import config as CFG

DESIGN = {
    "future_events": list(CFG.FUTURE_EVENTS),
    "flow": [
        "ORDER_REQUESTED (record intent + proposal_id + deterministic client_order_id)",
        "on send -> await ORDER_ACCEPTED / ORDER_REJECTED",
        "on TIMEOUT -> DO NOT resubmit; call reconcile_open_orders() first",
        "reconcile: fetch existing broker orders by client_order_id; if present -> ORDER_RECONCILED "
        "(adopt existing, no new send); if absent -> a single controlled resend under fresh firewall",
        "ORDER_RECONCILED recorded append-only; never rewrite the original signal/proposal",
    ],
    "no_blind_resubmission": True,
}


def reconcile_open_orders(*args, **kwargs):
    raise NotImplementedError("reconcile is designed but NOT enabled this phase")


def submit_reconciled(*args, **kwargs):
    raise NotImplementedError("submission is designed but NOT enabled this phase")
