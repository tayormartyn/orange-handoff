"""
Proposal orchestrator: confirmed SIGNAL -> eligibility -> demo firewall -> pending-order plan ->
risk sizing -> DEMO ORDER PREVIEW. Deterministic proposal id (one active version per signal).
Records the append-only lifecycle. NOTHING here sends an order; dry-run approval ends in
DRY_RUN_APPROVED / NO_ORDER_SENT.
"""
from __future__ import annotations
import hashlib

import config as CFG
import account_guard
import risk_sizer
import order_planner
import risk_presentation
from models import Proposal


def make_proposal_id(signal_id, version, account_id, instrument):
    raw = f"{signal_id}|v{version}|{account_id}|{str(instrument).upper()}"
    return "demoprop-" + hashlib.sha256(raw.encode()).hexdigest()[:16]


def check_eligibility(signal):
    if signal.synthetic:
        return False, "SYNTHETIC_OR_TEST"
    if signal.intake_class != "SIGNAL":
        return False, f"NOT_A_SIGNAL:{signal.intake_class}"
    if not signal.confirmed:
        return False, "NOT_HUMAN_CONFIRMED"          # OCR alone / unconfirmed can never proceed
    if str(signal.instrument).upper() != CFG.XAUUSD_NAME:
        return False, "NOT_XAUUSD"
    if str(signal.direction).upper() not in ("BUY", "SELL"):
        return False, "DIRECTION_UNKNOWN"
    if signal.entry_low is None and signal.entry_high is None:
        return False, "ENTRY_UNKNOWN"
    if signal.stop is None:
        return False, "STOP_UNKNOWN"
    if signal.duplicate:
        return False, "DUPLICATE"
    return True, "OK"


def build_proposal(signal, account, symbol, quote, *, risk_pct=None, manual_entry=None, now_ms=0,
                   token_scope="", disable_path=None, fx_quote_to_account=1.0, leverage=100.0,
                   version=1, audit=None):
    pid = make_proposal_id(signal.signal_id, version, account.account_id, signal.instrument)
    elig_ok, elig_reason = check_eligibility(signal)
    fw = account_guard.demo_firewall(account=account, instrument=signal.instrument,
                                     token_scope=token_scope, disable_path=disable_path)
    preview_allowed = account_guard.firewall_allows_preview(fw)

    lo = signal.entry_low if signal.entry_low is not None else signal.entry_high
    hi = signal.entry_high if signal.entry_high is not None else signal.entry_low
    plan = order_planner.plan_order(direction=signal.direction, entry_low=lo, entry_high=hi,
                                    stop=signal.stop, quote=quote, symbol=symbol,
                                    manual_entry=manual_entry, now_ms=now_ms,
                                    signal_confirmed_at_ms=signal.confirmed_at_ms) if elig_ok else None
    risk = (risk_sizer.size_order(account=account, symbol=symbol, entry=plan.entry, stop=signal.stop,
                                  risk_pct=risk_pct, fx_quote_to_account=fx_quote_to_account,
                                  leverage=leverage) if (plan and plan.ok) else None)

    no_tp = not signal.targets
    valid = bool(elig_ok and preview_allowed and plan and plan.ok and risk and risk.ok)

    preview = {
        "banner": "DEMO ORDER PREVIEW — NO ORDER SENT",
        "demo_account": account.masked(), "signal_id": signal.signal_id,
        "provider_verified": signal.provider_verified, "instrument": signal.instrument,
        "direction": str(signal.direction).upper(),
        "entry_zone": [lo, hi], "selected_entry": (plan.entry if plan else None),
        "current_bid": quote.bid, "current_ask": quote.ask,
        "order_type": (plan.order_type if plan else None),
        "selection_reason": (plan.selection_reason if plan else None),
        "stop_loss": signal.stop,
        "take_profit": (signal.targets if signal.targets else "NO TAKE PROFIT SET"),
        "manual_management_required": no_tp,
        "risk_pct": (risk.risk_pct if risk else None), "risk_amount": (risk.risk_amount if risk else None),
        "volume_units": (risk.volume_units if risk else None),
        "volume_lots": (risk.volume_lots if risk else None),
        "planned_stop_loss_risk": (risk.planned_stop_loss_risk if risk else None),
        "planned_stop_loss_risk_note": ("Actual realised loss may differ because of spread, "
                                        "commission, slippage, gapping or execution conditions."),
        "commission_in_planned_risk": "EXCLUDED",
        "all_in_risk": (risk_presentation.all_in_risk(
            risk_budget=risk.risk_amount, planned_stop_loss_risk=risk.planned_stop_loss_risk,
            use_reserve=True) if risk else None),
        "expected_margin": (risk.expected_margin if risk else None),
        "account_currency": account.currency, "account_balance": account.balance,
        "quote_age_ms": now_ms - quote.ts_ms,
        "signal_age_ms": (now_ms - signal.confirmed_at_ms) if signal.confirmed_at_ms else None,
        "eligibility": {"ok": elig_ok, "reason": elig_reason},
        "plan_reason": (plan.reason if plan else "N/A"),
        "risk_reason": (risk.reason if risk else "N/A"),
        "firewall": fw.as_dict(), "valid_for_arming": valid,
        "no_take_profit_set": no_tp,
        "phase_notice": "BUILD+TEST+PREVIEW ONLY — order sending disabled; approval ends DRY_RUN_APPROVED",
    }
    p = Proposal(pid, version, signal.signal_id, account.account_id, signal.instrument, now_ms,
                 fw.as_dict(), (risk.__dict__ if risk else {}), (plan.__dict__ if plan else {}),
                 preview, status="PROPOSAL_VALIDATED" if valid else "PROPOSAL_REJECTED")
    if audit is not None:
        audit.record("PROPOSAL_CREATED", pid, {"signal_id": signal.signal_id})
        audit.record("PROPOSAL_VALIDATED" if valid else "PROPOSAL_REJECTED", pid,
                     {"valid": valid, "elig": elig_reason,
                      "plan": (plan.reason if plan else None), "risk": (risk.reason if risk else None)})
    return p


def arm(proposal, audit=None):
    if proposal.status != "PROPOSAL_VALIDATED":
        return {"armed": False, "reason": "NOT_VALIDATED"}
    proposal.status = "PROPOSAL_ARMED"
    if audit is not None:
        audit.record("PROPOSAL_ARMED", proposal.proposal_id, {})
    return {"armed": True, "proposal_id": proposal.proposal_id}


def dry_run_approve(proposal, *, now_ms=0, audit=None):
    """The ONLY approval available this phase. Sends NOTHING; ends DRY_RUN_APPROVED / NO_ORDER_SENT."""
    if (now_ms - proposal.created_at_ms) > CFG.PROPOSAL_TTL_SECONDS * 1000:
        proposal.status = "PROPOSAL_EXPIRED"
        if audit is not None:
            audit.record("PROPOSAL_EXPIRED", proposal.proposal_id, {})
        return {"result": "PROPOSAL_EXPIRED", "order_sent": False, "reason": "NO_ORDER_SENT"}
    if proposal.status != "PROPOSAL_ARMED":
        return {"result": "NOT_ARMED", "order_sent": False, "reason": "NO_ORDER_SENT"}
    if audit is not None:
        audit.record("DRY_RUN_APPROVED", proposal.proposal_id, {})
    return {"result": "DRY_RUN_APPROVED", "order_sent": False, "reason": "NO_ORDER_SENT"}
