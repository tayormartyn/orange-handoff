"""
alpha_intake — SHADOW-ONLY cross-language Alpha->QUALIFIED_STRIKE_AND_TRAP intake adapter.

Validates AlphaSignalProposal JSON, enforces the autonomous-origin and decimal price policies, maps
Alpha vocabulary to the existing QST intake vocabulary, and (optionally) invokes the PURE
strike_trap.route() for a shadow qualification record. Returns only the minimal QstIntakeAck.

Does NOT: reuse sea-scalper-farouk, create a broker route, enable execution, submit/amend/cancel/close
orders, size risk/lots, allocate 60/25/15, modify risk_policy.py, or import any broker / order-sending /
order-management module.
"""
from __future__ import annotations

from .qst_adapter import evaluate, ADAPTER_VERSION, CONFIG_VERSION, DIRECTION_MAP, ENTRY_TYPE_MAP

__all__ = ["evaluate", "ADAPTER_VERSION", "CONFIG_VERSION", "DIRECTION_MAP", "ENTRY_TYPE_MAP"]
