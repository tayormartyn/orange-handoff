"""demo_executor data models (plain dataclasses, no trading behaviour)."""
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Optional


@dataclass
class AccountSnapshot:
    account_id: int
    is_live: bool
    balance: float
    currency: str
    trade_scope: str                    # e.g. "trade" for a trade-capable demo token; "" if view-only
    environment: str = "DEMO"

    def masked(self):
        return {"account_id": self.account_id, "is_live": self.is_live, "balance": self.balance,
                "currency": self.currency, "environment": self.environment,
                "trade_capable": "trade" in (self.trade_scope or "").lower()}


@dataclass
class SymbolMeta:
    symbol_id: int
    name: str
    digits: int
    point: float                        # smallest price increment
    lot_size: float                     # contract size per 1.0 lot (XAUUSD: 100 oz)
    min_volume: float                   # in lots
    max_volume: float
    volume_step: float
    min_stop_distance_points: float
    quote_currency: str = "USD"
    enabled: bool = True
    market_open: bool = True


@dataclass
class Quote:
    bid: float
    ask: float
    ts_ms: int


@dataclass
class SignalInput:
    signal_id: str
    intake_class: str
    confirmed: bool
    instrument: str
    direction: str
    entry_low: Optional[float]
    entry_high: Optional[float]
    stop: Optional[float]
    targets: Optional[list]
    provider_verified: bool
    confirmed_at_ms: Optional[int]
    duplicate: bool = False
    synthetic: bool = False


@dataclass
class Check:
    name: str
    passed: bool
    detail: str = ""


@dataclass
class FirewallResult:
    checks: list
    all_passed: bool

    def as_dict(self):
        return {"all_passed": self.all_passed,
                "checks": [asdict(c) if isinstance(c, Check) else c for c in self.checks]}


@dataclass
class RiskSizing:
    ok: bool
    reason: str
    risk_pct: float
    risk_amount: float
    balance: float
    currency: str
    volume_lots: float
    volume_units: float
    planned_stop_loss_risk: float          # renamed from MAX LOSS: the risk if stopped at the planned stop
    expected_margin: Optional[float]
    stop_distance: float


@dataclass
class OrderPlan:
    ok: bool
    reason: str
    order_type: Optional[str]           # BUY_LIMIT / BUY_STOP / SELL_LIMIT / SELL_STOP
    entry: Optional[float]
    zone_low: Optional[float]
    zone_high: Optional[float]
    bid: Optional[float]
    ask: Optional[float]
    selection_reason: str = ""


@dataclass
class BrokerPosition:
    position_id: int
    label: str                          # our signal id stored in label/comment
    symbol: str
    direction: str                      # BUY / SELL
    volume_units: float                 # protocol units
    price: float                        # broker-reported VWAP of the actual fills
    stop_loss: Optional[float]
    take_profit: Optional[float]
    open_time_ms: Optional[int] = None


@dataclass
class BrokerOrder:
    order_id: int
    label: str
    symbol: str
    direction: str
    is_pending: bool = True
    open_time_ms: Optional[int] = None


@dataclass
class MatchResult:
    status: str                         # CONFIRMED / AMBIGUOUS / NO_MATCH / MULTI_LEG
    matched: Optional[object]
    candidates: list = field(default_factory=list)
    reason: str = ""
    match_keys: list = field(default_factory=list)


@dataclass
class PlanAction:
    action_type: str                    # AMEND_STOP_LOSS / PARTIAL_CLOSE / ...
    ok: bool
    reason: str
    detail: dict = field(default_factory=dict)


@dataclass
class ManagementPlan:
    plan_id: str
    signal_id: str
    account_id: int
    intents: list
    actions: list                       # list of PlanAction
    valid: bool
    card: dict
    status: str = "MANAGEMENT_PLAN_CREATED"


@dataclass(frozen=True)
class ApprovedDemoOrderRequest:
    """Immutable, already-validated order values the transport consumes. The transport must NOT
    rebuild or reinterpret any of these."""
    signal_id: str
    proposal_id: str
    client_order_id: str
    account_id: int
    symbol_id: int
    symbol_name: str
    trade_side: str                     # BUY / SELL
    order_type: str                     # LIMIT / STOP (no market)
    volume_raw_protocol: float
    volume_units_underlying: float
    volume_lots: float
    limit_price: Optional[float]
    stop_price: Optional[float]
    stop_loss: float                    # mandatory
    take_profit: Optional[float]
    label: str
    comment: str
    planned_stop_loss_risk: float
    risk_pct: float
    expected_margin: float
    created_at_ms: int


@dataclass(frozen=True)
class ApprovedManagementPlan:
    """Immutable, already-validated management values the management transport consumes verbatim.
    action in MOVE_SL_BREAKEVEN / PARTIAL_CLOSE / CANCEL_PENDING / COMPOSITE."""
    plan_id: str
    action: str
    signal_id: str
    proposal_id: str
    update_intake_id: str
    account_id: int
    symbol_id: int
    symbol_name: str
    direction: str
    client_order_id: Optional[str] = None
    broker_order_id: Optional[str] = None
    broker_position_id: Optional[str] = None
    label: Optional[str] = None
    comment: Optional[str] = None
    broker_vwap: Optional[float] = None
    current_stop: Optional[float] = None
    new_stop_loss: Optional[float] = None          # broker VWAP rounded (ENTRY_PRICE_BREAKEVEN)
    new_take_profit: Optional[float] = None
    open_volume_raw: Optional[float] = None
    close_volume_raw: Optional[float] = None
    close_volume_units: Optional[float] = None
    close_volume_lots: Optional[float] = None
    remaining_volume_raw: Optional[float] = None
    volume_is_operator_policy: bool = False        # True => OPERATOR_POLICY_NOT_PROVIDER_VOLUME
    steps: tuple = ()                              # sub-plans for action=COMPOSITE
    created_at_ms: int = 0


@dataclass
class Proposal:
    proposal_id: str
    version: int
    signal_id: str
    account_id: int
    instrument: str
    created_at_ms: int
    firewall: dict
    risk: dict
    plan: dict
    preview: dict
    status: str = "PROPOSAL_CREATED"
