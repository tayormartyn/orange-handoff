"""
run.py — the single command the operator runs.

    python run.py

What it does, in a loop:
  1. Asks you to paste a signal from the Whale Room feed.
  2. Reads it (Module B) and shows you the numbers to confirm (y/n).
  3. Sizes it at a hard-capped 1% of the pot (Module C).
  4. Prints the full ticket.
  5. Logs it to paper_log.csv (Module D) — PAPER only, no orders, no money.
  6. Loops for the next signal.

PAPER MODE ONLY.
"""

from decimal import Decimal

import config
import module_b_parser as parser
import module_c_risk as risk
import module_d_logger as logger
import limits


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
            continue  # ignore leading blank lines
        lines.append(line)
    return "\n".join(lines).strip()


def _banner():
    risk_pct, phase, profile, cap = risk.resolve_risk_profile()
    print("=" * 60)
    print("   SIGNAL TERMINAL   —   PAPER MODE")
    print(f"   Mode: {config.MODE}    Pot: {config.CURRENCY}{config.POT_SIZE}")
    if profile == "CPS":
        print(f"   Rule profile: CPS   Phase {phase} ({risk_pct * 100:.1f}% risk, "
              f"hard cap {cap * 100:.0f}%)")
    else:
        print(f"   Rule profile: DEFAULT   Risk: {risk_pct * 100:.1f}% per trade")
    print("   No exchange is connected. No orders are placed. No money moves.")
    print("=" * 60)


def _ask(prompt: str) -> str:
    return input(prompt).strip()


def main():
    _banner()

    if config.MODE != "PAPER":
        print("\nThis build only runs in PAPER mode. Set MODE = 'PAPER' in config.py.")
        return

    pot = Decimal(config.POT_SIZE)

    while True:
        # --- Discipline rail: daily / weekly loss limits --------------------
        # Warns loudly if today's (or this week's) paper losses crossed a limit.
        limits.print_today_banner(config.PAPER_LOG_FILE)

        raw = _read_pasted_signal()

        if raw == "quit" or raw == "":
            print("\nDone. Your paper trades are saved in", config.PAPER_LOG_FILE)
            break

        # --- Module B: parse -------------------------------------------------
        try:
            signal = parser.parse_signal(raw)
        except parser.ParserError as e:
            print(f"\n  Couldn't read that signal:\n  {e}\n")
            continue

        # --- Amber confirm ---------------------------------------------------
        if not parser.confirm_parsed(signal):
            print("\n  Okay — discarded. Nothing was logged. Paste it again if you like.\n")
            continue

        # --- Optional context (blank is always fine, never blocks logging) ---
        # Lets you segment your edge later by trader, session, and timeframe.
        signal.source = _ask("  Who called this signal? (optional — Enter to skip): ")
        signal.session = _ask("  Session? Asia / New York / London (optional): ")
        signal.level_tf = _ask("  Level timeframe? 4H / Daily / Weekly / Monthly (optional): ")

        # --- Module C: size (risk % / phase come from the active profile) ----
        try:
            ticket = risk.size_signal(signal, pot)
        except risk.RiskError as e:
            print(f"\n  This signal was NOT sized:\n  {e}\n")
            continue

        # --- Show the ticket -------------------------------------------------
        print("\n" + risk.format_ticket(ticket, currency=config.CURRENCY))

        # --- Module D: log (PAPER only) -------------------------------------
        try:
            path = logger.log_ticket(ticket)
            print(f"\n  Logged to {path}  (outcome left blank for you to fill in later).\n")
        except Exception as e:
            print(f"\n  Sized fine, but couldn't write to the log file:\n  {e}\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nStopped. Nothing in progress was logged.")
