"""
CANONICAL prospective risk-policy configuration (single source of truth). Every sizing module consumes
THIS module — no scattered hardcoded percentages. Advisory / shadow only: nothing here enables,
constructs or transmits a broker order/amend/close/cancel, or issues a permit/lease.

Policy v2.0.0: prospective XAUUSD demo campaign risk raised 0.5% -> 1.0% (Martyn-approved). The 1.0%
cap is CAMPAIGN-WIDE, not per-tranche. The balance-vs-equity basis is PRESERVED (BALANCE) and NOT
silently changed. Historical records keep the percentage used when they were created.
"""
from __future__ import annotations
import calendar
import time as _time

RISK_POLICY_VERSION = "2.0.0"

# --- canonical percentages ---
DEFAULT_CAMPAIGN_RISK_PERCENT = 1.0            # human-facing percent
MAX_CAMPAIGN_RISK_PERCENT = 1.0
DEFAULT_CAMPAIGN_RISK_PCT = 0.01              # fraction consumed by sizing
MAX_CAMPAIGN_RISK_PCT = 0.01
PREVIOUS_CAMPAIGN_RISK_PERCENT = 0.5         # for the record / report only (never used in sizing)

# --- risk basis (PRESERVED — not silently changed) ---
RISK_BASIS_TYPE = "BALANCE"                   # sizing uses account.balance, exactly as before

# --- campaign allocation weights (fractions of the 1.0% campaign budget; sum to 1.0) ---
STRIKE_ALLOC = 0.60                            # T1 -> 0.60% of basis
TRAP_T2_ALLOC = 0.25                           # T2 -> 0.25%
TRAP_T3_ALLOC = 0.15                           # T3 -> 0.15%

# comparison-model weights (each sums to 100% of the 1.0% campaign budget)
COMPARISON_WEIGHTS = {
    "PASSIVE_EQUAL": (1 / 3, 1 / 3, 1 / 3),
    "PASSIVE_50_30_20": (0.50, 0.30, 0.20),
    "PASSIVE_60_25_15": (0.60, 0.25, 0.15),
    "PASSIVE_70_20_10": (0.70, 0.20, 0.10),
    "PASSIVE_FRONT_ONLY": (1.0, 0.0, 0.0),
    "QUALIFIED_STRIKE_TRAP_60_25_15": (0.60, 0.25, 0.15),
}

# --- prospective activation timestamp: only NEW campaigns after this use 1.0% ---
ACTIVATION_TS_UTC = "2026-07-03T12:30:00Z"
ACTIVATION_TS_MS = calendar.timegm(_time.strptime(ACTIVATION_TS_UTC, "%Y-%m-%dT%H:%M:%SZ")) * 1000


def campaign_budget(basis_amount, *, risk_pct=None):
    """Total campaign risk budget in account currency (1.0% of the risk basis)."""
    return round(float(basis_amount) * (DEFAULT_CAMPAIGN_RISK_PCT if risk_pct is None else risk_pct), 2)


def tranche_budgets(basis_amount, weights=(STRIKE_ALLOC, TRAP_T2_ALLOC, TRAP_T3_ALLOC), *, risk_pct=None):
    """Per-tranche currency allocations from the campaign budget (risk allocations, not lot allocations)."""
    total = campaign_budget(basis_amount, risk_pct=risk_pct)
    return [round(total * w, 2) for w in weights]


def within_cap(*, basis_amount, tranche_risks, cost_allowance=0.0, slippage_allowance=0.0, risk_pct=None):
    """Campaign-wide invariant: sum(tranche stop risk + slippage + cost) <= 1.0% of basis."""
    cap = campaign_budget(basis_amount, risk_pct=risk_pct)
    total = round(sum(tranche_risks) + cost_allowance + slippage_allowance, 4)
    return {"total_worst_case_risk": total, "cap": cap, "within_cap": total <= cap + 1e-6,
            "headroom": round(cap - total, 4)}


def stop_move_within_cap(*, basis_amount, new_campaign_worst_case_risk, risk_pct=None):
    """Management guard: moving a stop FARTHER must block if it raises the campaign above 1.0%. The move
    to 1.0% is NOT permission to add risk after entry — management may only reduce/preserve risk."""
    cap = campaign_budget(basis_amount, risk_pct=risk_pct)
    allowed = new_campaign_worst_case_risk <= cap + 1e-6
    return {"allowed": allowed, "cap": cap, "new_risk": round(new_campaign_worst_case_risk, 4),
            "blocked_reason": None if allowed else "STOP_MOVE_EXCEEDS_CAMPAIGN_CAP",
            "management_may_increase_risk": False}


def policy_record(*, basis_type=None, basis_amount, currency, allocation_model="QUALIFIED_STRIKE_TRAP_60_25_15",
                  snapshot_ts_utc=None, cost_allowance=0.0, now_ms=None):
    """Full stamped record stored with every NEW campaign / shown in every preview."""
    weights = COMPARISON_WEIGHTS.get(allocation_model, (STRIKE_ALLOC, TRAP_T2_ALLOC, TRAP_T3_ALLOC))
    budget = campaign_budget(basis_amount)
    tr = tranche_budgets(basis_amount, weights)
    is_new = (now_ms is None) or (now_ms >= ACTIVATION_TS_MS)
    return {
        "risk_policy_version": RISK_POLICY_VERSION,
        "risk_percent": DEFAULT_CAMPAIGN_RISK_PERCENT if is_new else PREVIOUS_CAMPAIGN_RISK_PERCENT,
        "risk_basis_type": basis_type or RISK_BASIS_TYPE,
        "risk_basis_amount": round(float(basis_amount), 2),
        "currency": currency,
        "currency_risk_budget": budget,
        "allocation_model": allocation_model,
        "tranche_currency_allocations": {"T1": tr[0], "T2": tr[1] if len(tr) > 1 else 0.0,
                                          "T3": tr[2] if len(tr) > 2 else 0.0},
        "tranche_percent_allocations": {"T1": round(weights[0] * DEFAULT_CAMPAIGN_RISK_PERCENT, 4),
                                        "T2": round((weights[1] if len(weights) > 1 else 0) * DEFAULT_CAMPAIGN_RISK_PERCENT, 4),
                                        "T3": round((weights[2] if len(weights) > 2 else 0) * DEFAULT_CAMPAIGN_RISK_PERCENT, 4)},
        "cost_allowance": round(cost_allowance, 2),
        "account_snapshot_ts_utc": snapshot_ts_utc,
        "activation_ts_utc": ACTIVATION_TS_UTC,
        "activation_ts_ms": ACTIVATION_TS_MS,
        "applies_new_campaigns_only": True,
    }
