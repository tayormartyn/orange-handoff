"""
Trade-lifecycle data model (DERIVED, append-only). Nothing here mutates an original intake, review,
signal, update, result, paper observation or broker record — the engine consumes copies and emits a
separate derived view. Three evidence layers are kept strictly separate; provider claims are NEVER
presented as Martyn's realised broker result.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional

# ---- evidence layers (kept strictly separate) ----
PROVIDER_INSTRUCTION = "PROVIDER_INSTRUCTION"          # what Farouk told the group to do
MARKET_PATH_EVIDENCE = "MARKET_PATH_EVIDENCE"          # whether recorded bid/ask touched a level
BROKER_EXECUTION_EVIDENCE = "BROKER_EXECUTION_EVIDENCE"  # what Martyn's demo account actually did
EVIDENCE_LAYERS = (PROVIDER_INSTRUCTION, MARKET_PATH_EVIDENCE, BROKER_EXECUTION_EVIDENCE)

# ---- derived lifecycle states ----
STATES = (
    "SIGNAL_CAPTURED", "AWAITING_ENTRY", "PENDING_ORDER", "FILLED", "OPEN",
    "PARTIAL_PROFIT_INSTRUCTED", "PARTIAL_PROFIT_CONFIRMED", "STOP_MOVE_INSTRUCTED",
    "STOP_MOVED_TO_BREAKEVEN", "RUNNER_OPEN", "ORIGINAL_STOP_HIT", "BREAKEVEN_STOP_HIT",
    "TARGET_HIT", "FULL_CLOSE_CONFIRMED",
    # terminal outcomes
    "CLOSED_WIN", "CLOSED_MANAGED_PROFIT", "CLOSED_BREAKEVEN", "CLOSED_LOSS",
    "CLOSED_PROFIT_R_UNKNOWN", "OPEN_UNRESOLVED", "AMBIGUOUS", "NO_BROKER_EXECUTION",
    "MISSED_NOT_ENTERED",
)
TERMINAL_STATES = ("CLOSED_WIN", "CLOSED_MANAGED_PROFIT", "CLOSED_BREAKEVEN", "CLOSED_LOSS",
                   "CLOSED_PROFIT_R_UNKNOWN", "MISSED_NOT_ENTERED", "NO_BROKER_EXECUTION")

# ---- provenance mode: replay-validation vs prospective demo execution ----
REPLAY_VALIDATION_ONLY = "REPLAY_VALIDATION_ONLY"      # historical screenshot after outcome known
PROSPECTIVE_DEMO_EXECUTION = "PROSPECTIVE_DEMO_EXECUTION"  # fresh demo broker events

# ---- link outcome ----
LINK_LINKED = "LINKED"
LINK_UNLINKED = "UNLINKED"
LINK_AMBIGUOUS = "AMBIGUOUS"


@dataclass(frozen=True)
class Evidence:
    layer: str                      # one of EVIDENCE_LAYERS
    kind: str                       # e.g. TAKE_PROFIT_INSTRUCTION, PRICE_TOUCHED_STOP, ORDER_FILLED
    detail: dict = field(default_factory=dict)
    ts_ms: Optional[int] = None
    source_ref: Optional[str] = None    # intake/review/order id — provenance, never mutated

    def __post_init__(self):
        if self.layer not in EVIDENCE_LAYERS:
            raise ValueError(f"invalid evidence layer {self.layer}")


@dataclass(frozen=True)
class SignalRef:
    signal_id: str
    instrument: str
    direction: Optional[str] = None         # BUY / SELL
    provider: Optional[str] = None
    entry_low: Optional[float] = None
    entry_high: Optional[float] = None
    stop: Optional[float] = None
    targets: tuple = ()
    confirmed: bool = False
    ts_ms: Optional[int] = None
    replay: bool = True                     # historical screenshots default to replay-validation


@dataclass(frozen=True)
class ChildEvent:
    """A confirmed TRADE_UPDATE or TRADE_RESULT to be linked to a parent SIGNAL."""
    child_id: str
    child_class: str                        # TRADE_UPDATE / TRADE_RESULT
    instrument: str
    direction: Optional[str] = None
    provider: Optional[str] = None
    ts_ms: Optional[int] = None
    explicit_parent_signal_id: Optional[str] = None   # approved human link
    signal_id_in_metadata: Optional[str] = None
    broker_order_id: Optional[str] = None
    broker_position_id: Optional[str] = None
    instruction_kind: Optional[str] = None            # e.g. TAKE_PROFIT / MOVE_SL_BREAKEVEN
    replay: bool = True


@dataclass(frozen=True)
class BrokerEvent:
    """Authoritative for Martyn's demo performance."""
    kind: str                               # ORDER_FILLED / PARTIAL_CLOSE / SL_AMENDED / POSITION_CLOSED / STOP_HIT
    signal_id: Optional[str] = None
    broker_order_id: Optional[str] = None
    broker_position_id: Optional[str] = None
    vwap_price: Optional[float] = None
    stop_price: Optional[float] = None
    closed_volume_raw: Optional[float] = None
    realised_pnl: Optional[float] = None
    ts_ms: Optional[int] = None
    prospective: bool = True                # fresh demo broker events


@dataclass(frozen=True)
class LinkResult:
    status: str                             # LINKED / UNLINKED / AMBIGUOUS
    parent_signal_id: Optional[str]
    method: Optional[str]                   # how it matched
    reason: Optional[str] = None
    candidates: tuple = ()


@dataclass
class EffectiveTrade:
    signal_id: str
    state: str
    outcome: Optional[str] = None
    provenance: str = REPLAY_VALIDATION_ONLY
    realised_pnl: Optional[float] = None
    r_multiple: Optional[float] = None
    provider_instructions: list = field(default_factory=list)
    market_path: list = field(default_factory=list)
    broker_events: list = field(default_factory=list)
    linked_updates: list = field(default_factory=list)
    linked_results: list = field(default_factory=list)
    blockers: list = field(default_factory=list)
    counts_in_prospective_stats: bool = False
