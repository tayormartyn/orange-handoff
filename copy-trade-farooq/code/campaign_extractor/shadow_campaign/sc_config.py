"""
Shadow Qualified Strike & Trap — configuration. SHADOW ONLY. Nothing here enables, constructs or
transmits a broker order/amend/close/cancel. All thresholds are configurable for shadow comparison;
production values are NOT chosen here (they require evidence from the shadow sweep).
"""
from __future__ import annotations

STRIKE_TRAP_MODEL_VERSION = "1.0.0"

# routing modes
PRE_TOUCH_PASSIVE_LADDER = "PRE_TOUCH_PASSIVE_LADDER"
INSIDE_ZONE_QUALIFIED_STRIKE_TRAP = "INSIDE_ZONE_QUALIFIED_STRIKE_TRAP"
INSIDE_ZONE_BLOCKED = "INSIDE_ZONE_BLOCKED"
ZONE_CONSUMED = "ZONE_CONSUMED"

# risk allocations — consume the CANONICAL risk policy (risk_policy.py, v2.0.0 = 1.0%)
import os as _os
import sys as _sys
_sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), "demo_executor"))
import risk_policy as _RP
TOTAL_CAMPAIGN_RISK_PCT = _RP.DEFAULT_CAMPAIGN_RISK_PCT   # 1.0% full-campaign cap (was 0.5%)
STRIKE_ALLOC = _RP.STRIKE_ALLOC          # T1 60%
TRAP_T2_ALLOC = _RP.TRAP_T2_ALLOC        # T2 25%
TRAP_T3_ALLOC = _RP.TRAP_T3_ALLOC        # T3 15%
RISK_POLICY_VERSION = _RP.RISK_POLICY_VERSION
CONTRACT_OZ_PER_LOT = 100.0             # XAUUSD: 100 oz per 1.00 lot (100 raw = 1 XAU unit = 0.01 lot)
LOT_STEP = 0.01
MIN_LOT = 0.01

# configurable qualification thresholds (shadow-swept, NOT production-fixed)
MAX_INSIDE_ZONE_RESIDENCE_SECONDS = 120
MAX_APPROVAL_LATENCY_SECONDS = 30
MAX_STRIKE_PENETRATION_RATIO = 0.60      # how deep into the zone the executable price may be
MAX_STRIKE_SLIPPAGE_POINTS = 20          # Market-Range slippage ceiling (price points)
MAX_STRIKE_SPREAD = 0.60                 # XAUUSD price units
MAX_QUOTE_GAP_SECONDS = 60               # a bigger gap => quote-path unverified
FRESH_SIGNAL_TTL_SECONDS = 300
POINT = 0.01                             # XAUUSD price point (digits=2)

# threshold sweep grids for the shadow comparison
RESIDENCE_GRID = (30, 60, 120)
PENETRATION_GRID = (0.4, 0.6, 0.8)
SLIPPAGE_GRID = (10, 20, 40)
FILL_ASSUMPTIONS = ("CONSERVATIVE", "STRICT")   # conservative = worst-permitted fill

# comparison model set
COMPARISON_MODELS = ("PASSIVE_EQUAL", "PASSIVE_50_30_20", "PASSIVE_60_25_15", "PASSIVE_70_20_10",
                     "PASSIVE_FRONT_ONLY", "QUALIFIED_STRIKE_TRAP_60_25_15")
