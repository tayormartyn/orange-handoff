"""Demo-lane READ-ONLY configuration (bounded build, v0.3.1 + ADDENDUM_001).
NO credentials here. All gates hard False. Immutable safety caps (correction 12).
Nothing in this package can flip a gate, request OAuth, or connect to place orders."""

# --- GATES (immutable in this build; a real deploy reads them from governed config) ---
EXECUTION_ENABLED = False           # live — hard False, untouched by this lane
CTRADER_EXECUTION_ENABLED = False   # live — hard False, untouched by this lane
DEMO_EXECUTION_ENABLED = False      # demo gate — DEFAULT False; only a signed ratification flips it

# --- account discriminator allowlist (correction 1) ---
DEMO_ENDPOINT = "demo.ctraderapi.com"
ALLOWED_CTID_TRADER_ACCOUNT_ID = 1_000_001        # single known demo account id (placeholder)
EXPECTED_BROKER_ENVIRONMENT = "PEPPERSTONE_DEMO"
REQUIRED_SCOPE = "SCOPE_TRADE"

# --- immutable safety caps (correction 12) ---
SAFETY_CAPS = {
    "instrument": "XAUUSD",
    "order_type": "LIMIT",             # opening placement only (F2)
    "max_concurrent_approved_campaigns": 1,
    "max_entry_orders": 3,
    "no_upward_rounding": True,
    "no_pyramiding": True,
    "no_reverse_trade": True,
    "no_quantity_increasing_modification": True,
    "no_unprotected_position": True,
}

# --- ledger eligibility (correction 11) — every demo record carries exactly these ---
LEDGER_ELIGIBILITY = {
    "eligible_for_strategy_expectancy": False,
    "eligible_for_model_training": False,
    "eligible_for_candidate_ranking": False,
    "eligible_for_freeze_evidence": False,
    "eligible_for_execution_fidelity_analysis": True,
}

APPROVAL_TOOL_VERSION = "approval_tool_v0_3_1"
EXECUTOR_VERSION = "executor_v0_3_1"
