"""
module_execution.py — the Execution Bridge.

==========================  SCAFFOLD — DISABLED  ==============================
This is the SKELETON of the piece that would one day hand a fully sized, routed,
and circuit-breaker-checked ticket to a broker for real execution.

IT CANNOT PLACE AN ORDER. There is no broker client in this file, and three
independent locks stand between a ticket and any submission:

    Lock 1  config.EXECUTION_ENABLED is False   (a feature flag, off by default)
    Lock 2  config.MODE must be "LIVE"          (it is "PAPER")
    Lock 3  submit_order() raises NotImplementedError where the broker call would
            go — there is simply no order-placing code to run.

Flipping any ONE lock still places nothing. Going live is a deliberate, later
step done on purpose with guidance — never by accident, and never by this file
as it stands.

What IS safe and live here (no side effects):
    * prepare_order(ticket, routing)  — builds a plain ExecutionOrder data object
    * preview_order(order)            — prints what WOULD be sent (a dry run)

This file does NOT touch the LIVE stub in module_d_logger.py — that stays as it
is. This is a separate, clearer scaffold for the execution step specifically.

Run it to see the scaffold build an order preview and then REFUSE to submit:

    python module_execution.py
==============================================================================
"""

from dataclasses import dataclass, field
from decimal import Decimal
from typing import List, Optional

import config


class ExecutionDisabled(Exception):
    """Raised when submission is refused by a safety lock. Operator-facing."""


# ----------------------------------------------------------------------------
# The shape of a would-be broker order (pure data — no side effects)
# ----------------------------------------------------------------------------
@dataclass
class ExecutionOrder:
    """
    A description of the order that WOULD be sent if execution were ever built.
    It is metadata only: building one places nothing and contacts nothing.
    """
    venue: str                      # routing venue label (e.g. "venue_A")
    venue_handle: str               # placeholder broker handle for that venue
    symbol: str                     # instrument (e.g. "XAUUSD")
    side: str                       # "LONG" / "SHORT"
    lots: Decimal                   # size, already risk-capped by module_c_risk
    entry: Decimal                  # the sizing entry (already slippage-adjusted)
    stop: Decimal                   # stop-loss price
    targets: List[Decimal] = field(default_factory=list)
    asset_class: str = ""           # router's finer class (GOLD/SILVER/CRYPTO/FOREX)
    trader: str = ""                # router's trader tag
    dollar_risk: Decimal = Decimal("0")
    cash_at_risk: Decimal = Decimal("0")
    # A loud, permanent reminder of what this object is.
    intent: str = "PAPER SCAFFOLD — NOT FOR SUBMISSION (no execution exists)"


# ----------------------------------------------------------------------------
# Safe operations (no side effects, always allowed)
# ----------------------------------------------------------------------------
def prepare_order(ticket, routing) -> ExecutionOrder:
    """
    Build an ExecutionOrder from the pipeline's output (a sized Ticket + the
    router's RoutingDecision). PURE DATA — it computes a description and returns
    it. It sends nothing, connects to nothing, and changes nothing.

    Only fully-processed signals should reach here: a Ticket means it was sized
    (so it passed risk + the circuit breaker), and a routed RoutingDecision means
    it was not bounced to REVIEW.
    """
    venues = getattr(config, "EXECUTION_VENUES", {})
    venue = getattr(routing, "venue", "") or ""
    targets = [t for t in (getattr(ticket, "tp1", None),
                           getattr(ticket, "tp2", None),
                           getattr(ticket, "tp3", None)) if t is not None]
    s = ticket.signal
    return ExecutionOrder(
        venue=venue,
        venue_handle=venues.get(venue, "PLACEHOLDER (no handle mapped)"),
        symbol=s.ticker,
        side=s.direction,
        lots=ticket.lots,
        entry=ticket.sizing_entry,
        stop=ticket.stop_loss,
        targets=targets,
        asset_class=getattr(routing, "asset_class", ""),
        trader=getattr(routing, "trader", ""),
        dollar_risk=ticket.dollar_risk,
        cash_at_risk=ticket.cash_at_risk,
    )


def _money(d: Decimal) -> str:
    try:
        return f"{Decimal(d).quantize(Decimal('0.01'))}"
    except Exception:
        return str(d)


def format_order(order: ExecutionOrder, currency: str = "£") -> str:
    tps = "  ".join(str(t) for t in order.targets) or "(none)"
    return "\n".join([
        "  WOULD-BE ORDER (dry run — NOT sent):",
        f"      intent      : {order.intent}",
        f"      venue       : {order.venue}  ->  {order.venue_handle}",
        f"      symbol      : {order.symbol}   ({order.asset_class})",
        f"      side        : {order.side}",
        f"      size        : {order.lots} lot(s)",
        f"      entry       : {order.entry}   (slippage-adjusted)",
        f"      stop        : {order.stop}",
        f"      targets     : {tps}",
        f"      trader      : {order.trader}",
        f"      risk        : {currency}{_money(order.cash_at_risk)} at risk "
        f"(budget {currency}{_money(order.dollar_risk)})",
    ])


def preview_order(order: ExecutionOrder, currency: str = "£") -> None:
    """Print what WOULD be sent. A dry run — places nothing."""
    print(format_order(order, currency=currency))


# ----------------------------------------------------------------------------
# The locks — and the deliberately-disconnected submission chokepoint
# ----------------------------------------------------------------------------
def guard_report() -> List[tuple]:
    """
    The state of each safety lock, for display. Returns a list of
    (label, passed: bool, detail). 'passed' True means that lock would ALLOW
    execution — all three must pass before any submission is even attempted.
    """
    enabled = bool(getattr(config, "EXECUTION_ENABLED", False))
    is_live = config.MODE == "LIVE"
    return [
        ("EXECUTION_ENABLED is True", enabled,
         f"config.EXECUTION_ENABLED = {enabled}"),
        ('MODE is "LIVE"', is_live,
         f'config.MODE = "{config.MODE}"'),
        ("broker client implemented", False,
         "none exists — submit_order() raises NotImplementedError"),
    ]


def can_execute() -> bool:
    """True only if EVERY lock would allow execution. (Always False in this build.)"""
    return all(passed for _, passed, _ in guard_report())


def submit_order(order: ExecutionOrder):
    """
    The ONE place a real order would ever be sent — and it cannot send one.

    Three independent locks guard it; even with the two flags flipped, the third
    (no broker client) makes submission impossible. This is the chokepoint that a
    future, deliberate live build would replace — never enable it casually.
    """
    # ----- Lock 1: feature flag --------------------------------------------
    if not getattr(config, "EXECUTION_ENABLED", False):
        raise ExecutionDisabled(
            "Execution is OFF (config.EXECUTION_ENABLED = False). No order placed. "
            "This flag must never be flipped until live trading is built on purpose."
        )

    # ----- Lock 2: trading mode --------------------------------------------
    if config.MODE != "LIVE":
        raise ExecutionDisabled(
            f'Execution refused: config.MODE is "{config.MODE}", not "LIVE". '
            "This build is PAPER only. No order placed."
        )

    # ========================================================================
    # Lock 3 — THE DISCONNECTED ENGINE.
    # This is the single line where a real broker submission would happen. It is
    # deliberately not implemented: there is no broker client, no API call, no
    # credentials, nothing. Building this is a separate, deliberate, guided step.
    # ========================================================================
    raise NotImplementedError(
        "No execution engine exists. The broker bridge is a scaffold only — "
        "there is no order-placing code here. (This is by design.)"
    )
    # broker = <connect to order.venue_handle>          # <-- would go here, later
    # broker.place(order.symbol, order.side, order.lots, ...)   # <-- NEVER in this build


# ----------------------------------------------------------------------------
# Self-test: build a real order preview, then prove it refuses to submit
# ----------------------------------------------------------------------------
def demo():
    # Local imports so the safe scaffold doesn't hard-depend on these to load.
    import module_c_risk as risk
    import module_router as router
    from models import Signal

    print("=" * 64)
    print("   EXECUTION BRIDGE — SCAFFOLD SELF-TEST  (DISABLED)")
    print("=" * 64)
    print("   Builds a would-be order from a sized, routed ticket, previews it,")
    print("   then attempts to submit — which every lock must refuse.")
    print("=" * 64)

    # A real, valid gold call -> size it -> route it (the pipeline's output).
    signal = Signal(
        ticker="XAUUSD", pair="XAUUSD", direction="LONG", asset_class="METAL",
        entry_low=Decimal("5007"), entry_high=Decimal("5022"),
        stop_loss=Decimal("4995"),
        targets=[Decimal("5045"), Decimal("5070"), Decimal("5110")],
        raw_text="FAROUK GOLD: XAUUSD LONG 5022-5007 SL 4995",
        source="FAROUK-GOLD",
    )
    ticket = risk.size_signal(signal, Decimal(config.POT_SIZE))
    decision = router.route(signal, channel="Farouk Gold")

    print("\n  STEP 1 — prepare + preview the would-be order (safe, no side effects):\n")
    order = prepare_order(ticket, decision)
    preview_order(order, currency=config.CURRENCY)

    print("\n  STEP 2 — safety locks (ALL must pass before a submit is attempted):")
    for label, passed, detail in guard_report():
        mark = "PASS" if passed else "BLOCK"
        print(f"      [{mark:>5}] {label:<30} {detail}")
    print(f"      => can_execute(): {can_execute()}")

    print("\n  STEP 3 — attempt to submit (must be refused):")
    try:
        submit_order(order)
        print("      !!! UNEXPECTED: submit_order returned without refusing.")
    except (ExecutionDisabled, NotImplementedError) as e:
        print(f"      REFUSED — {e}")

    print("\n" + "=" * 64)
    print("   RESULT: order PREVIEWED, submission REFUSED. Nothing was sent.")
    print("   The execution engine is a scaffold only — no order can be placed.")
    print("=" * 64 + "\n")


def main():
    demo()


if __name__ == "__main__":
    main()
