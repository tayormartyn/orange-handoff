"""
pipeline.py — the connected Signal Terminal pipeline (PAPER MODE ONLY).

This is the piece that wires the separate modules into ONE flow. A single signal
travels through every stage in order:

    1. PARSE           (module_b_parser)  raw text  -> structured Signal
    2. HUMAN CONFIRM   (amber step)        show the numbers, require y/n
    3. ROUTE           (module_router)     classify asset / trader / venue
                                           -> if REVIEW: STOP (needs human eyes)
    4. CIRCUIT BREAKER (limits)            daily 2% / weekly 10% loss limits
                                           -> if a limit is breached: STOP
    5. SIZE            (module_c_risk)     the hard-capped 1% position
                                           -> if it can't size: STOP
    6. LOG             (module_d_logger)   write to paper_log.csv WITH routing tags

If any stage halts the signal — you say the numbers are wrong, the router sends
it to REVIEW, or it can't be sized — the pipeline stops *gracefully* with a
plain-English reason. It never proceeds past a stop, and it never crashes.

NOTHING here connects to an exchange, places an order, or moves money. There is
no live path. The LIVE stub in module_d_logger.py is left untouched.

Run it:
    python pipeline.py            # paste a real signal and watch it flow through
    python pipeline.py --test      # run a built-in demo signal end to end
"""

import csv
from datetime import datetime, timezone
from decimal import Decimal

import config
import module_b_parser as parser
import module_router as router
import module_c_risk as risk
import module_d_logger as logger
import limits
import audit
from models import Signal


class PipelineStop(Exception):
    """A clean, intentional halt. The message is written for the operator to read."""


# ----------------------------------------------------------------------------
# Pretty stage banners
# ----------------------------------------------------------------------------
def _stage(n: int, title: str):
    print()
    print(f"  -- STAGE {n}: {title} " + "-" * max(0, 46 - len(title)))


def _halt(reason: str):
    print()
    print("  " + "=" * 60)
    print("  x PIPELINE STOPPED — nothing was logged past this point.")
    print(f"    {reason}")
    print("  " + "=" * 60)
    print()


# ----------------------------------------------------------------------------
# The connected flow for ONE already-parsed signal
# ----------------------------------------------------------------------------
def run_pipeline(signal: Signal, *, channel: str = None, pot: Decimal = None,
                 confirm_fn=None, do_log: bool = True, log_path: str = None,
                 audit_path: str = None) -> dict:
    """
    Run CONFIRM -> ROUTE -> SIZE -> LOG for one parsed Signal.

    Parsing happens before this (interactively in main(), or pre-built in the
    demo) so this function can be driven both by a human and by the test run.

    confirm_fn(signal) -> bool decides the amber step; defaults to the real
    interactive y/n. Raises PipelineStop if any stage halts the signal; returns
    a result dict {signal, decision, ticket, path} on success.

    Every run writes exactly ONE permanent audit entry (the machine's black box)
    recording the full chain of decisions — whether it completed or stopped.
    """
    pot = pot if pot is not None else Decimal(config.POT_SIZE)
    confirm_fn = confirm_fn or parser.confirm_parsed

    # The audit record is built as we go and written ONCE in the finally below,
    # so the decision chain is captured whether the signal completes or is stopped.
    rec = audit.AuditRecord.from_signal(signal, channel=channel or "")
    try:
        # --- STAGE 2: HUMAN CONFIRM (numbers shown by confirm_fn) -----------
        # (STAGE 1, PARSE, already produced `signal`; main() captured the source.)
        _stage(2, "HUMAN CONFIRM")
        confirmed = bool(confirm_fn(signal))
        rec.confirm(confirmed)
        if not confirmed:
            rec.result_stopped("HUMAN CONFIRM", "operator said the numbers were wrong")
            raise PipelineStop(
                "You said the numbers were wrong. Re-check the signal and paste it "
                "again — nothing was routed, sized, or logged."
            )
        print("  Confirmed. OK")

        # --- STAGE 3: ROUTE ------------------------------------------------
        _stage(3, "ROUTE  (classify asset / trader / venue)")
        decision = router.route(signal, channel=channel)
        rec.route(decision)
        print(router.format_decision(decision))
        if decision.needs_review:
            reasons = "; ".join(decision.review_reasons) or "unclear signal"
            rec.result_stopped("ROUTE", f"sent to REVIEW — {reasons}")
            raise PipelineStop(
                "The router sent this to the REVIEW bucket — it needs HUMAN EYES, "
                f"not automatic handling.\n    Reason(s): {reasons}\n"
                "    Stopped before sizing on purpose (better to ask than to guess)."
            )
        print(f"\n  Routed: {decision.asset_class} via {decision.venue} "
              f"(trader: {decision.trader}, confidence: {decision.confidence}).  OK")

        # --- STAGE 4: CIRCUIT BREAKER --------------------------------------
        # Reads realised losses already logged (today / this week) and refuses a
        # new trade once a loss limit is hit. Checked BEFORE sizing/logging.
        _stage(4, "CIRCUIT BREAKER  (daily 2% / weekly 10% loss limits)")
        breaker = limits.circuit_breaker(path=log_path)
        rec.circuit_breaker(breaker)
        for line in breaker.lines:
            print(f"  {line}")
        for warning in breaker.warnings:
            print(f"  ** {warning}")
        if breaker.blocked:
            rec.result_stopped("CIRCUIT BREAKER", breaker.block_reason)
            raise PipelineStop(breaker.block_reason)
        print("  Within loss limits — clear to proceed. OK")

        # --- STAGE 5: SIZE -------------------------------------------------
        _stage(5, "SIZE  (hard-capped 1% of the pot)")
        try:
            ticket = risk.size_signal(signal, pot)
        except risk.RiskError as e:
            rec.sizing_rejected(str(e))
            rec.result_stopped("SIZE", f"could not be sized: {e}")
            raise PipelineStop(f"This signal could NOT be sized safely:\n    {e}")
        rec.sizing(ticket)
        print(risk.format_ticket(ticket, currency=config.CURRENCY))

        # --- STAGE 6: LOG --------------------------------------------------
        _stage(6, "LOG  (paper_log.csv, with routing tags)")
        if not do_log:
            rec.result_other("SIZED (not logged)", "do_log=False")
            print("  (logging skipped for this run)")
            return {"signal": signal, "decision": decision, "ticket": ticket, "path": None}

        try:
            path = logger.log_ticket(ticket, path=log_path, routing=decision)
        except Exception as e:
            rec.result_stopped("LOG", f"couldn't write to the log file: {e}")
            raise PipelineStop(f"Sized fine, but couldn't write to the log file:\n    {e}")

        rec.result_logged(path)
        print(f"  Logged to {path}")
        print(f"    asset/route : {decision.asset_class}   trader : {decision.trader}"
              f"   venue : {decision.venue}   confidence : {decision.confidence}")
        print(f"    channel     : {decision.channel or '(unknown)'}")
        print("    outcome left blank for you to fill in later (python outcome.py).")
        return {"signal": signal, "decision": decision, "ticket": ticket, "path": path}
    finally:
        # One permanent audit entry per run — success OR stop.
        audit.record(rec, path=audit_path)


# ----------------------------------------------------------------------------
# Interactive front-end (paste a real signal)
# ----------------------------------------------------------------------------
def _read_pasted_signal() -> str:
    """Read a (possibly multi-line) pasted signal. Finish with a blank line."""
    print("\nPaste the signal below.")
    print("When you're done, press Enter on an empty line to finish.")
    print("(Type  quit  on its own to exit.)\n")
    lines = []
    while True:
        try:
            line = input()
        except EOFError:
            break
        if line.strip().lower() == "quit" and not lines:
            return "quit"
        if line.strip() == "" and lines:
            break
        if line.strip() == "" and not lines:
            continue
        lines.append(line)
    return "\n".join(lines).strip()


def _ask(prompt: str) -> str:
    return input(prompt).strip()


def _banner():
    print("=" * 64)
    print("   SIGNAL TERMINAL — CONNECTED PIPELINE   (PAPER MODE)")
    print("=" * 64)
    print(f"   Mode: {config.MODE}    Pot: {config.CURRENCY}{config.POT_SIZE}")
    print("   Flow: parse -> confirm -> route -> size -> log")
    print("   No exchange is connected. No orders are placed. No money moves.")
    print("=" * 64)


def main():
    _banner()
    if config.MODE != "PAPER":
        print("\n  This build only runs in PAPER mode. Set MODE = 'PAPER' in config.py.\n")
        return

    while True:
        raw = _read_pasted_signal()
        if raw in ("quit", ""):
            print("\n  Done.\n")
            break

        # --- STAGE 1: PARSE --------------------------------------------------
        _stage(1, "PARSE  (read the raw signal)")
        try:
            signal = parser.parse_signal(raw)
        except parser.ParserError as e:
            audit.record(audit.AuditRecord().parse_failed(raw, str(e)))
            _halt(f"Couldn't read that signal: {e}")
            continue
        print("  Parsed the raw text into a structured signal. OK")

        # Optional context — captured BEFORE routing so the trader tag works.
        signal.source = _ask("\n  Who called this signal? (optional — Enter to skip): ")
        signal.session = _ask("  Session? Asia / New York / London (optional): ")
        signal.level_tf = _ask("  Level timeframe? 4H / Daily / Weekly / Monthly (optional): ")
        channel = _ask("  Which channel did it come from? (optional): ")

        try:
            run_pipeline(signal, channel=channel)
            print("\n  OK Done — signal completed every stage and was logged.\n")
        except PipelineStop as stop:
            _halt(str(stop))
        # Loop for the next signal.


# ----------------------------------------------------------------------------
# Test run: a real Farouk gold call, end to end (no LLM, auto-confirmed)
# ----------------------------------------------------------------------------
def demo():
    _banner()
    demo_log = "paper_log.demo.csv"
    print("\n  TEST RUN — a real Farouk gold call flowing through every stage.")
    print("  (The parse step is pre-built so no API key is needed, and the amber")
    print("   confirm is auto-answered 'yes' for the demo. Everything else is real,")
    print(f"   including a real LOG write — but to a throwaway file ({demo_log}),")
    print("   so your actual paper_log.csv is left untouched.)")

    # A real Farouk gold call (XAUUSD long limit): entry 5022, stop 5007, targets.
    _stage(1, "PARSE  (pre-built for the demo)")
    signal = Signal(
        ticker="XAUUSD",
        pair="XAUUSD",
        direction="LONG",
        asset_class="METAL",
        entry_low=Decimal("5007"),
        entry_high=Decimal("5022"),
        stop_loss=Decimal("4995"),
        targets=[Decimal("5045"), Decimal("5070"), Decimal("5110")],
        raw_text="FAROUK GOLD: XAUUSD LONG 5022-5007, SL 4995, TPs 5045/5070/5110",
        source="FAROUK-GOLD",
    )
    print("  Parsed signal:")
    print(parser.format_for_confirmation(signal))

    try:
        result = run_pipeline(
            signal,
            channel="Farouk Gold",
            log_path=demo_log,
            audit_path="audit_log.demo.jsonl",
            confirm_fn=lambda s: (print("  [demo] auto-confirming the amber step "
                                        "(a real run waits for your y/n)."), True)[1],
        )
        print("\n  OK DEMO COMPLETE — the signal passed every stage and was logged to")
        print(f"    {result['path']}\n")
    except PipelineStop as stop:
        _halt(str(stop))


def breaker_demo():
    """
    Show the circuit breaker refusing a trade. Seeds a throwaway log where TODAY
    has already hit the daily 2% loss limit, then tries to push a fresh, valid
    gold signal through — the pipeline must STOP at the breaker, before sizing
    or logging it. Uses a throwaway file; your real paper_log.csv is untouched.
    """
    _banner()
    demo_log = "paper_log.breaker_demo.csv"
    print("\n  TEST RUN — CIRCUIT BREAKER")
    print("  Simulating a log where TODAY has already hit the daily 2% loss limit")
    print(f"  (two -1R stop-outs = -{config.CURRENCY}280 = 2% of the pot), in {demo_log}.")
    print("  Then we try to push a fresh, VALID gold signal through the pipeline.")

    # Seed two full stop-outs dated today -> daily 2% limit reached.
    day = datetime.now(timezone.utc).date().isoformat()
    seeded = []
    for i in range(2):
        row = {k: "" for k in logger.FIELDNAMES}
        row.update(
            timestamp=f"{day}T12:0{i}:00+00:00",
            ticker="XAUUSD", asset_class="METAL", direction="LONG",
            source="FAROUK-GOLD", trader="FAROUK", venue="venue_A", route_class="GOLD",
            entry="5000", sl_price="4990", dollar_risk="140.00", risk_pct="0.01",
            outcome="SL",  # a full stop-out = -1R = -£140
        )
        seeded.append(row)
    with open(demo_log, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=logger.FIELDNAMES)
        w.writeheader()
        w.writerows(seeded)

    _stage(1, "PARSE  (pre-built for the demo)")
    signal = Signal(
        ticker="XAUUSD", pair="XAUUSD", direction="LONG", asset_class="METAL",
        entry_low=Decimal("5007"), entry_high=Decimal("5022"),
        stop_loss=Decimal("4995"),
        targets=[Decimal("5045"), Decimal("5070")],
        raw_text="FAROUK GOLD: next XAUUSD long after two losers today",
        source="FAROUK-GOLD",
    )
    print(parser.format_for_confirmation(signal))

    try:
        run_pipeline(
            signal, channel="Farouk Gold", log_path=demo_log,
            audit_path="audit_log.demo.jsonl",
            confirm_fn=lambda s: (print("  [demo] auto-confirming the amber step."), True)[1],
        )
        print("\n  UNEXPECTED: the trade was NOT blocked — check the breaker logic.\n")
    except PipelineStop as stop:
        _halt(str(stop))
        with open(demo_log, newline="", encoding="utf-8") as f:
            n = sum(1 for _ in csv.DictReader(f))
        print("  As designed: the circuit breaker refused the next trade BEFORE")
        print("  sizing or logging it.")
        print(f"  The log still holds {n} rows (the 2 seeded losers) — the blocked")
        print("  trade was NOT added.\n")


if __name__ == "__main__":
    import sys
    args = [a for a in sys.argv[1:] if a.strip()]
    if args and args[0] in ("--test", "--demo", "test", "demo"):
        demo()
    elif args and args[0] in ("--test-breaker", "--breaker", "breaker"):
        breaker_demo()
    elif args:
        print(f"\n  Unknown option: {args[0]}")
        print("  Usage:")
        print("    python pipeline.py                  # paste a real signal and run it through")
        print("    python pipeline.py --test            # demo: a signal flowing through all stages")
        print("    python pipeline.py --test-breaker    # demo: circuit breaker refusing a trade\n")
    else:
        main()
