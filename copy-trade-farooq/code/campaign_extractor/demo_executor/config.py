"""
demo_executor configuration — physically isolated DEMO_APPROVAL_ONLY component.

THIS PHASE: BUILD + TEST + PREVIEW ONLY. No order is ever sent. There is deliberately NO live
endpoint anywhere in this package. The global observation locks (EXECUTION_ENABLED /
CTRADER_EXECUTION_ENABLED) stay False and are NOT touched here.
"""
from __future__ import annotations
import os

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(os.path.dirname(_HERE))

# --- HARD local switches: entry-order sending and trade MANAGEMENT are INDEPENDENTLY controlled ---
ORDER_SENDING_ENABLED = False          # entry-order submit path refuses while False (this whole phase)
ORDER_MANAGEMENT_ENABLED = False       # amend/close/cancel path refuses while False — SEPARATE lock

# --- management policy ---
OPERATOR_DEFAULT_CLOSE_PCT = 0.5       # console MAY propose 50% when provider gives no size (policy, not provider)
MANAGEMENT_EVENTS = ("MGMT_REQUESTED", "MGMT_ACCEPTED", "MGMT_REJECTED", "MGMT_RECONCILIATION_REQUIRED",
                     "MGMT_RECONCILED", "SLTP_AMENDED", "POSITION_PARTIALLY_CLOSED", "ORDER_CANCELLED",
                     "MGMT_STATE_MISMATCH", "MANAGEMENT_PLAN_PARTIAL_SUCCESS")
BREAKEVEN_LABEL = "ENTRY_PRICE_BREAKEVEN"

# --- demo firewall constants ---
DEMO_ALLOWLIST_ACCOUNT_IDS = (4257941,)   # the granted Pepperstone DEMO account (login reference)
REQUIRED_ENVIRONMENT = "DEMO"
XAUUSD_SYMBOL_ID = 41
XAUUSD_NAME = "XAUUSD"
DISABLE_FILE = os.path.join(_ROOT, "data", "DEMO_EXECUTION_DISABLED")

# --- risk policy (canonical single source of truth: risk_policy.py, v2.0.0 = 1.0%) ---
import risk_policy as _RP
DEFAULT_RISK_PCT = _RP.DEFAULT_CAMPAIGN_RISK_PCT       # 1.0% (raised from 0.5% under policy v2.0.0)
MAX_RISK_PCT = _RP.MAX_CAMPAIGN_RISK_PCT               # 1.0% hard maximum

# --- freshness thresholds ---
QUOTE_STALE_MS = 5000                  # a quote older than 5s is stale
SIGNAL_STALE_SECONDS = 3600            # a confirmed signal older than 1h is stale for a fresh proposal
FAROUK_INTERPRETATION_CONTRACT_VERSION = "1.0.0"   # versioned deterministic interpretation contract
FRESH_SIGNAL_TTL_SECONDS = 300         # first controlled trial: signal must be <=5 min old (provider ts)
CLOCK_SKEW_TOLERANCE_SECONDS = 60      # a provider ts more than this in the future is UNVERIFIED
DUPLICATE_SIGNAL_WINDOW_SECONDS = 600  # semantic-duplicate comparison window (10 min)
MAX_SPREAD_PRICE = 0.60                # XAUUSD spread policy limit (price units); above -> SPREAD_LIMIT_EXCEEDED

# --- stores ---
AUDIT_DB = os.path.join(_ROOT, "data", "demo_execution_v1.db")

# --- proposal lifecycle events recorded THIS phase (append-only) ---
PHASE_EVENTS = ("PROPOSAL_CREATED", "PROPOSAL_VALIDATED", "PROPOSAL_ARMED", "DRY_RUN_APPROVED",
                "PROPOSAL_EXPIRED", "PROPOSAL_REJECTED")
# --- future submission events: DESIGNED, NOT ENABLED ---
FUTURE_EVENTS = ("ORDER_REQUESTED", "ORDER_ACCEPTED", "ORDER_REJECTED", "ORDER_RECONCILED")

# --- TRADE_UPDATE management phase events recorded THIS phase (append-only) ---
UPDATE_PHASE_EVENTS = ("UPDATE_RECEIVED", "UPDATE_LINKED_TO_SIGNAL", "POSITION_MATCH_PROPOSED",
                       "POSITION_MATCH_CONFIRMED", "MANAGEMENT_PLAN_CREATED", "MANAGEMENT_PLAN_VALIDATED",
                       "MANAGEMENT_PLAN_ARMED", "UPDATE_PLAN_DRY_RUN_APPROVED",
                       "MANAGEMENT_PLAN_REJECTED", "MANAGEMENT_PLAN_EXPIRED")
# --- future management execution events: DESIGNED, NOT ENABLED ---
FUTURE_MGMT_EVENTS = ("SL_AMEND_REQUESTED", "SL_AMEND_ACCEPTED", "SL_AMEND_REJECTED",
                      "PARTIAL_CLOSE_REQUESTED", "PARTIAL_CLOSE_FILLED", "PARTIAL_CLOSE_PARTIALLY_FILLED",
                      "PARTIAL_CLOSE_REJECTED", "MANAGEMENT_PLAN_PARTIAL_SUCCESS", "MANAGEMENT_PLAN_COMPLETED")

# --- submission transport (fake this phase; real send blocked by ORDER_SENDING_ENABLED=False) ---
DEMO_ENDPOINT_HOST = "demo.ctraderapi.com"      # NO live fallback anywhere in this package
REQUIRED_PERMISSION_SCOPE = "SCOPE_TRADE"
SUBMISSION_EVENTS = ("ORDER_REQUESTED", "ORDER_ACCEPTED", "ORDER_REJECTED",
                     "ORDER_RECONCILIATION_REQUIRED", "ORDER_RECONCILED", "POSITION_OPENED",
                     "BROKER_STATE_MISMATCH")
READY_STATE = "READY_FOR_FIRST_CONTROLLED_DEMO_ORDER"     # future state; never auto-activates
COMMISSION_INCLUDED_IN_PLANNED_RISK = False      # commission is EXCLUDED from planned stop-loss risk
ORDER_LABEL = "ST-FAROUK"
DEMO_ENDPOINT_PORT = 5035                        # demo.ctraderapi.com:5035 (no live fallback)
# Official cTrader ProtoOANewOrderReq contract maxima:
OFFICIAL_MAX_LABEL_LEN, OFFICIAL_MAX_COMMENT_LEN, OFFICIAL_MAX_CLIENT_ORDER_ID_LEN = 100, 512, 50
# Internal conservative limits (STRICTER than the API contract; NOT the contract maximum):
INTERNAL_MAX_LABEL_LEN, INTERNAL_MAX_COMMENT_LEN = 30, 255
MAX_CLIENT_ORDER_ID_LEN = OFFICIAL_MAX_CLIENT_ORDER_ID_LEN     # 50 is both official + used
# commission reserve when commission cannot be estimated before entry (fraction of risk budget)
COMMISSION_RESERVE_FRACTION = 0.10              # conservative reserve if COMMISSION_ESTIMATE_STATUS=UNKNOWN

ACCOUNT_TYPES = ("HEDGED", "NETTED", "SPREAD_BETTING")
UPDATE_INTENTS = ("MOVE_SL_TO_BREAKEVEN", "AMEND_STOP_LOSS", "AMEND_TAKE_PROFIT", "PARTIAL_CLOSE",
                  "CANCEL_PENDING_ORDER", "CLOSE_WORST_LEG", "HOLD_BEST_LEG",
                  "COMPOSITE_MANAGEMENT_PLAN", "AMBIGUOUS_UPDATE")

PROPOSAL_TTL_SECONDS = 120             # a proposal expires after 2 minutes
