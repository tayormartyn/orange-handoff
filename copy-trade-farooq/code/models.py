"""
models.py — the shared schema.

Every other module speaks in terms of these objects, so the shape of a signal
is defined in exactly one place.
"""

from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from typing import List


class Direction(str, Enum):
    LONG = "LONG"
    SHORT = "SHORT"


class AssetClass(str, Enum):
    CRYPTO = "CRYPTO"
    METAL = "METAL"


# ----------------------------------------------------------------------------
# Reference schema (documentation only).
# This is the agreed shape of a signal. The dataclasses below are the real,
# typed version that the code actually uses.
# ----------------------------------------------------------------------------
signal_schema = {
    "ticker":      str,     # "FET", "SOL", "PEPE", "XAUUSD", "XAGUSD"
    "pair":        str,     # full pair e.g. "FET/USDT"
    "direction":   str,     # "LONG" or "SHORT"
    "asset_class": str,     # "CRYPTO" or "METAL"
    "entry_low":   float,   # TRUE min of the entry zone (sorted on ingest)
    "entry_high":  float,   # TRUE max of the entry zone (sorted on ingest)
    "stop_loss":   float,
    "targets":     list,    # variable length [T1, T2, ...] — NOT fixed at 4
    "raw_text":    str,     # original message kept verbatim — always
}


@dataclass
class Signal:
    """
    A parsed, structured trading signal.

    Money/price fields are Decimal (never float) so the risk math stays exact.
    The entry zone is stored as a true (low, high) pair regardless of the order
    it was typed in.
    """
    ticker: str
    pair: str
    direction: str          # "LONG" or "SHORT"
    asset_class: str        # "CRYPTO" or "METAL"
    entry_low: Decimal      # TRUE low end of the entry zone (both ends kept — nothing lost)
    entry_high: Decimal     # TRUE high end of the entry zone
    stop_loss: Decimal
    targets: List[Decimal] = field(default_factory=list)
    raw_text: str = ""
    source: str = ""        # optional: which analyst/trader made the call. Blank is fine.
    session: str = ""       # optional context (CPS): "Asia" / "New York" / "London". Blank is fine.
    level_tf: str = ""      # optional context (CPS): "4H" / "Daily" / "Weekly" / "Monthly".
    # The single CONSERVATIVE entry recorded for sizing — the WORSE fill of the
    # zone (BUY -> the higher price, SELL -> the lower price), never the midpoint,
    # so sizing/expectancy is never flattered. None = not set (risk derives it).
    primary_entry: Decimal = None
    order_type: str = ""    # "market" / "limit" / "" (detected from "buy limit" etc.)


@dataclass
class Ticket:
    """
    The result of sizing a Signal: a description of the trade that WOULD have
    been taken. This is what gets logged in PAPER mode. No order is ever placed.
    """
    signal: Signal
    asset_class: str
    contract_multiplier: Decimal
    asset_verified: bool        # False = contract spec is a placeholder, do not trust live
    pot_size: Decimal
    sizing_entry: Decimal       # the entry the size was calculated from (AFTER slippage)
    stop_loss: Decimal
    first_target: Decimal
    size: Decimal               # units / contracts (already rounded DOWN)
    notional: Decimal           # size * entry * multiplier
    cash_at_risk: Decimal       # what you'd lose if the stop is hit
    risk_pct_of_pot: Decimal    # cash_at_risk / pot  (the ACTUAL risk after rounding)
    rr_first_target: Decimal    # reward : risk to the first target
    rr_targets: List[Decimal] = field(default_factory=list)  # R:R to each target T1..Tn

    # --- CPS / rule-profile fields (additive) -------------------------------
    profile: str = "DEFAULT"            # "CPS" or "DEFAULT"
    phase: int = 0                      # trading phase (1/2/3); 0 = not applicable
    risk_pct: Decimal = Decimal("0")    # the risk % the size was budgeted at
    dollar_risk: Decimal = Decimal("0") # budgeted cash at risk = pot * risk_pct
    lots: Decimal = Decimal("0")        # position size in lots (metals) / units (crypto)
    sl_dollar: Decimal = Decimal("0")   # stop distance in price terms (|entry - stop|)
    stop_mode: str = "SIGNAL"           # "SIGNAL" or "FIXED"
    tp1: Decimal = None                 # exit-ladder target prices (CPS or first 3 signal targets)
    tp2: Decimal = None
    tp3: Decimal = None
    scale_out: List[str] = field(default_factory=list)  # per-target scale-out plan (CPS)
    broker_note: str = ""               # contract-spec confirmation reminder (metals)

    # --- Slippage model (honest fills) --------------------------------------
    slippage: Decimal = Decimal("0")    # per-side price penalty modelled into the entry
    raw_entry: Decimal = None           # the conservative entry BEFORE slippage (for display)

    # --- Multi-asset fields (per-asset-class sizing) ------------------------
    sizing_method: str = ""             # which strategy sized it (dollar_per_point/pip_value/percent_risk)
    size_unit: str = "lot(s)"           # how to label the size on the ticket (lots vs units)
    quote_currency: str = ""            # FOREX: the pair's quote currency (drives pip value)
    flags: List[str] = field(default_factory=list)  # extra honesty flags to print (e.g. crypto fees)
