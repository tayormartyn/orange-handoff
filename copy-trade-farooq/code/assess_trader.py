"""
assess_trader.py — an ADVISORY trader-assessment analyst (PAPER, READ-ONLY).

================================  WHAT THIS IS  ================================
A judgment AID, not an automated decision. It reads a trader's track record from
your paper log (and, optionally, a text file of their raw messages) and writes an
honest, plain-English assessment: are they disciplined, are their claims honest,
are they drifting from trading into selling, and is their edge improving or
fading? It ends with a verdict — KEEP FOLLOWING / WATCH CLOSELY / REDUCE TRUST —
to inform YOUR call.

It is NOT part of the trade pipeline. It changes no sizing, blocks no trade,
routes nothing, and touches no money or the LIVE stub. You read it; you decide.
===============================================================================

How it works:
  * The FACTS are computed in Python from paper_log.csv (win rate, loss record,
    sizing over time, stop usage, edge trend) — so the integrity check is grounded
    in your real data, not guessed. Those facts are shown to you in the report.
  * The WRITTEN assessment is produced by Claude (same API key/setup as
    module_b_parser), reading those facts plus any raw messages you provide.

Run it:
    python assess_trader.py                     # list the traders found in your log
    python assess_trader.py FAROUK              # assess from logged trades
    python assess_trader.py FAROUK --messages traders/farouk_messages.txt
    python assess_trader.py FAROUK --facts-only  # just the computed facts, no API call
    python assess_trader.py FAROUK --out traders/farouk_assessment.txt

If a messages file isn't given, it auto-looks for traders/<name>_messages.txt.

PAPER MODE ONLY. Read-only to paper_log.csv. Needs ANTHROPIC_API_KEY for the
written assessment (the --facts-only mode needs no key).
"""

import csv
import json
import os
import sys
from datetime import datetime
from decimal import Decimal

import config
import review


MODEL = getattr(config, "ASSESSOR_MODEL", getattr(config, "PARSER_MODEL", "claude-sonnet-4-6"))
MESSAGE_CHAR_BUDGET = 24000     # keep the prompt sane; note when we truncate


# ----------------------------------------------------------------------------
# Friendly guards
# ----------------------------------------------------------------------------
def _stop(message: str):
    print("\n  Can't run the assessment:")
    print(f"  {message}\n")


def _client():
    """Anthropic client, or None with a friendly message (same setup as the parser)."""
    try:
        import anthropic
    except ImportError:
        _stop("the 'anthropic' library isn't installed.\n"
              "  Fix: open PowerShell and run:  pip install anthropic")
        return None
    if not os.environ.get("ANTHROPIC_API_KEY"):
        _stop("no API key found (ANTHROPIC_API_KEY isn't set).\n"
              "  Set it the same way as for the parser (see the README), or run with\n"
              "  --facts-only to see the computed track-record facts without the API.")
        return None
    return anthropic.Anthropic()


# ----------------------------------------------------------------------------
# Reading + filtering the log (READ-ONLY)
# ----------------------------------------------------------------------------
def _load_rows(path: str):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _matches_trader(row: dict, name: str) -> bool:
    """A row belongs to `name` if it appears in the source or the trader tag."""
    n = name.upper().strip()
    source = (row.get("source") or "").upper()
    trader = (row.get("trader") or "").upper()
    return bool(n) and (n in source or n == trader or n in trader)


def _known_traders(rows: list) -> list:
    """Distinct trader tags / sources present in the log, with trade counts."""
    counts = {}
    for r in rows:
        tag = (r.get("trader") or "").strip() or (r.get("source") or "").strip()
        if tag:
            counts[tag] = counts.get(tag, 0) + 1
    return sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))


# ----------------------------------------------------------------------------
# Objective facts, computed from the log (grounding for the assessment)
# ----------------------------------------------------------------------------
def _f(value):
    try:
        return float(str(value).strip())
    except (TypeError, ValueError):
        return None


def _date(row):
    return (row.get("timestamp") or "").strip()[:10]


def _win_rate(closed):
    if not closed:
        return None
    wins = sum(1 for t in closed if t["r"] > 0)
    return round(100.0 * wins / len(closed), 1)


def _expectancy(closed):
    if not closed:
        return None
    return round(float(sum((t["r"] for t in closed), Decimal("0")) / Decimal(len(closed))), 3)


def compute_facts(rows: list, name: str) -> dict:
    """
    Build the objective, log-derived facts for one trader. Uses review.realised_r
    so every R matches what review.py would report. NOTHING here is guessed.
    """
    mine = [r for r in rows if _matches_trader(r, name)]
    mine.sort(key=lambda r: (r.get("timestamp") or ""))

    closed, missed, per_trade = [], [], []
    for r in mine:
        rr, reached, status = review.realised_r(r)
        if status == "missed":
            missed.append(r)
        elif status == "ok":
            dr = review.trade_dollar_risk(r)
            closed.append({"r": rr, "pnl": rr * dr})
        # 'open'/'bad' rows are neither filled nor missed for stats purposes.

        per_trade.append({
            "date": _date(r),
            "ticker": (r.get("ticker") or "").strip(),
            "direction": (r.get("direction") or "").strip(),
            "outcome": (r.get("outcome") or "").strip() or "(open)",
            "tps_hit": (r.get("tps_hit") or "").strip(),
            "realised_R": (None if status != "ok" else round(float(rr), 3)),
            "lots": _f(r.get("lots")),
            "has_stop": bool((r.get("sl_price") or "").strip()),
            "confidence": (r.get("confidence") or "").strip(),
            "notes": (r.get("notes") or "").strip(),
        })

    losses = [t for t in per_trade if t["realised_R"] is not None and t["realised_R"] < 0]
    lots_seq = [t["lots"] for t in per_trade if t["lots"]]
    filled = [t for t in per_trade if t["realised_R"] is not None]
    n_with_stop = sum(1 for t in filled if t["has_stop"])

    # Edge trend: first half vs second half of the FILLED trades, chronologically.
    closed_seq = [t for t in closed]   # already in time order
    half = len(closed_seq) // 2
    first_half, second_half = closed_seq[:half], closed_seq[half:]

    facts = {
        "trader": name.upper(),
        "matched_sources": sorted({(r.get("source") or "").strip()
                                    for r in mine if (r.get("source") or "").strip()}),
        "signals_total": len(mine),
        "filled": len(closed),
        "missed": len(missed),
        "wins": sum(1 for t in closed if t["r"] > 0),
        "losses": sum(1 for t in closed if t["r"] < 0),
        "breakeven": sum(1 for t in closed if t["r"] == 0),
        "win_rate_pct": _win_rate(closed),
        "expectancy_R_per_trade": _expectancy(closed),
        "net_R": round(float(sum((t["r"] for t in closed), Decimal("0"))), 2),
        "net_cash": round(float(sum((t["pnl"] for t in closed), Decimal("0"))), 2),
        "currency": config.CURRENCY,
        "first_trade": (mine[0].get("timestamp") or "")[:10] if mine else None,
        "last_trade": (mine[-1].get("timestamp") or "")[:10] if mine else None,
        "loss_dates": [t["date"] for t in losses],
        "stop_usage": {
            "filled_trades": len(filled),
            "with_stop_logged": n_with_stop,
            "pct_with_stop": (round(100.0 * n_with_stop / len(filled), 1) if filled else None),
        },
        "sizing_lots": {
            "first": lots_seq[0] if lots_seq else None,
            "last": lots_seq[-1] if lots_seq else None,
            "min": min(lots_seq) if lots_seq else None,
            "max": max(lots_seq) if lots_seq else None,
            "avg": (round(sum(lots_seq) / len(lots_seq), 4) if lots_seq else None),
        },
        "edge_trend": {
            "first_half_trades": len(first_half),
            "first_half_win_rate_pct": _win_rate(first_half),
            "first_half_expectancy_R": _expectancy(first_half),
            "second_half_trades": len(second_half),
            "second_half_win_rate_pct": _win_rate(second_half),
            "second_half_expectancy_R": _expectancy(second_half),
        },
        "confidence_tags": _confidence_counts(per_trade),
        "per_trade": per_trade,
    }
    return facts


def _confidence_counts(per_trade):
    counts = {}
    for t in per_trade:
        c = (t.get("confidence") or "").upper()
        if c:
            counts[c] = counts.get(c, 0) + 1
    return counts


# ----------------------------------------------------------------------------
# Messages file (optional, for language analysis)
# ----------------------------------------------------------------------------
def _read_messages(path: str):
    """Read a trader's raw messages file. Returns (text, truncated_bool) or (None, False)."""
    if not path or not os.path.exists(path):
        return None, False
    with open(path, encoding="utf-8", errors="replace") as f:
        text = f.read().strip()
    if not text:
        return "", False
    if len(text) > MESSAGE_CHAR_BUDGET:
        return text[:MESSAGE_CHAR_BUDGET], True
    return text, False


# ----------------------------------------------------------------------------
# The Anthropic call (structured assessment)
# ----------------------------------------------------------------------------
_SECTION = {
    "type": "object",
    "properties": {
        "observations": {"type": "array", "items": {"type": "string"}},
        "flag": {"type": "string", "enum": ["ok", "watch", "concern"]},
    },
    "required": ["observations", "flag"],
}

_ASSESS_TOOL = {
    "name": "record_trader_assessment",
    "description": "Record the structured, evidence-grounded assessment of the trader.",
    "input_schema": {
        "type": "object",
        "properties": {
            "headline": {"type": "string",
                         "description": "One honest sentence summarising the trader."},
            "discipline": {**_SECTION,
                           "description": "Stops, consistent sizing, FOMO avoidance, and any "
                                          "drift over time (e.g. 'small size' -> 'bigger size')."},
            "integrity": {
                "type": "object",
                "properties": {
                    "observations": {"type": "array", "items": {"type": "string"}},
                    "claims_vs_record": {"type": "array", "items": {"type": "string"},
                                         "description": "Specific claims (e.g. '20-0', 'risk-free') "
                                                        "checked AGAINST the logged loss record. "
                                                        "Flag mismatches explicitly."},
                    "flag": {"type": "string", "enum": ["ok", "watch", "concern"]},
                },
                "required": ["observations", "claims_vs_record", "flag"],
            },
            "sales_marketing_creep": {**_SECTION,
                                      "description": "Shift from trading to selling: copy-bot "
                                                     "funnels, 'join my', upsells, VIP, affiliate."},
            "edge_trend": {
                "type": "object",
                "properties": {
                    "direction": {"type": "string",
                                  "enum": ["improving", "stable", "declining", "insufficient_data"]},
                    "observations": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["direction", "observations"],
            },
            "verdict": {"type": "string",
                        "enum": ["KEEP_FOLLOWING", "WATCH_CLOSELY", "REDUCE_TRUST"]},
            "verdict_reasons": {"type": "array", "items": {"type": "string"}},
            "caveats": {"type": "array", "items": {"type": "string"},
                        "description": "Honesty caveats — e.g. small sample, no messages provided."},
        },
        "required": ["headline", "discipline", "integrity", "sales_marketing_creep",
                     "edge_trend", "verdict", "verdict_reasons"],
    },
}

_SYSTEM = (
    "You are a sharp, honest trading-desk analyst assessing whether a signal "
    "provider deserves continued trust. You are skeptical but fair, and you back "
    "every claim with evidence.\n"
    "RULES:\n"
    "- The FACTS block is computed from the operator's real paper log. Treat its "
    "numbers (win rate, loss record, sizing, edge trend) as ground truth. NEVER "
    "invent trades, numbers, or losses.\n"
    "- For integrity: compare what the trader SAYS in their messages (e.g. '20-0', "
    "'risk-free', 'never lose') against the actual logged loss record in FACTS. "
    "If they claim perfection but the log shows losses, say so plainly.\n"
    "- If there are no messages, assess discipline/integrity only from the log and "
    "say the language analysis was limited.\n"
    "- Small samples are weak evidence: if the trade count is low, lower your "
    "confidence and add a caveat rather than overstating.\n"
    "- This is ADVISORY: you inform the operator's judgment; you do not control any "
    "trading. Be direct and useful. Always call record_trader_assessment."
)


def _build_user_content(facts: dict, messages: str, truncated: bool) -> str:
    parts = []
    parts.append(f"TRADER: {facts['trader']}")
    parts.append("\nFACTS (computed from the paper log — ground truth):")
    parts.append(json.dumps(facts, indent=2, default=str))
    if messages is None:
        parts.append("\nMESSAGES: (none provided — language analysis is limited to the log)")
    elif messages == "":
        parts.append("\nMESSAGES: (file was empty)")
    else:
        note = "  [truncated to fit]" if truncated else ""
        parts.append(f"\nRAW MESSAGES FROM THE TRADER{note}:\n\"\"\"\n{messages}\n\"\"\"")
    parts.append("\nWrite the assessment now via the record_trader_assessment tool.")
    return "\n".join(parts)


def run_assessment(client, facts: dict, messages, truncated: bool, model: str) -> dict:
    resp = client.messages.create(
        model=model,
        max_tokens=2000,
        system=_SYSTEM,
        tools=[_ASSESS_TOOL],
        tool_choice={"type": "tool", "name": "record_trader_assessment"},
        messages=[{"role": "user", "content": _build_user_content(facts, messages, truncated)}],
    )
    block = next((b for b in resp.content if getattr(b, "type", None) == "tool_use"), None)
    if block is None:
        raise RuntimeError("the model didn't return a structured assessment — try again.")
    return block.input


# ----------------------------------------------------------------------------
# Rendering
# ----------------------------------------------------------------------------
LINE = "=" * 70
THIN = "-" * 70
_VERDICT_LABEL = {
    "KEEP_FOLLOWING": "KEEP FOLLOWING",
    "WATCH_CLOSELY": "WATCH CLOSELY",
    "REDUCE_TRUST": "REDUCE TRUST",
}
_FLAG_MARK = {"ok": "[ ok ]", "watch": "[watch]", "concern": "[CONCERN]"}


def _facts_block(facts: dict) -> list:
    f = facts
    cur = f["currency"]
    et = f["edge_trend"]
    sz = f["sizing_lots"]
    su = f["stop_usage"]
    out = [
        THIN,
        "  FACTS FROM YOUR LOG  (what the verdict is grounded on)",
        THIN,
        f"    Signals logged : {f['signals_total']}   "
        f"({f['filled']} filled / {f['missed']} missed)",
    ]
    if f["filled"]:
        out += [
            f"    Record         : {f['wins']}W / {f['losses']}L / {f['breakeven']}BE   "
            f"(win rate {f['win_rate_pct']}%)",
            f"    Expectancy     : {f['expectancy_R_per_trade']:+} R/trade   "
            f"(net {f['net_R']:+} R = {cur}{f['net_cash']:+,.2f})",
            f"    Date range     : {f['first_trade']}  ->  {f['last_trade']}",
            f"    Loss record    : {f['losses']} logged loss(es)"
            + (f" on {', '.join(f['loss_dates'])}" if f["loss_dates"] else ""),
            f"    Stop usage     : {su['with_stop_logged']}/{su['filled_trades']} filled "
            f"trades had a stop logged"
            + (f" ({su['pct_with_stop']}%)" if su["pct_with_stop"] is not None else ""),
            f"    Sizing (lots)  : first {sz['first']} -> last {sz['last']}   "
            f"(min {sz['min']}, max {sz['max']}, avg {sz['avg']})",
            f"    Edge trend     : first half {et['first_half_win_rate_pct']}% win / "
            f"{et['first_half_expectancy_R']} R  vs  second half "
            f"{et['second_half_win_rate_pct']}% win / {et['second_half_expectancy_R']} R",
        ]
        if f["confidence_tags"]:
            tags = ", ".join(f"{k}:{v}" for k, v in sorted(f["confidence_tags"].items()))
            out.append(f"    Confidence tags: {tags}")
    else:
        out.append("    (no FILLED trades logged for this trader yet)")
    return out


def _section(title: str, data: dict, extra_key: str = None, extra_title: str = None) -> list:
    flag = data.get("flag", "")
    mark = _FLAG_MARK.get(flag, "")
    out = [THIN, f"  {title}   {mark}"]
    for obs in data.get("observations", []):
        out.append(f"    - {obs}")
    if extra_key and data.get(extra_key):
        out.append(f"    {extra_title}:")
        for item in data[extra_key]:
            out.append(f"      * {item}")
    return out


def render_report(facts: dict, a: dict, messages_used: bool) -> str:
    out = [
        LINE,
        f"   TRADER ASSESSMENT — {facts['trader']}".ljust(70),
        f"   {datetime.now().strftime('%Y-%m-%d %H:%M')}   ·   ADVISORY ANALYST AID",
        LINE,
        "   *** ADVISORY ONLY — a judgment aid, NOT an automated decision. ***",
        "   It changes no sizing, blocks no trade, and touches no money. You decide.",
        LINE,
        "",
        f"  HEADLINE: {a.get('headline','')}",
    ]
    out += [""] + _facts_block(facts)

    out += [""] + _section("DISCIPLINE  (stops / sizing / FOMO / drift)", a.get("discipline", {}))
    out += [""] + _section("INTEGRITY  (claims vs the real loss record)", a.get("integrity", {}),
                           extra_key="claims_vs_record", extra_title="Claims checked")
    out += [""] + _section("SALES / MARKETING CREEP", a.get("sales_marketing_creep", {}))

    et = a.get("edge_trend", {})
    out += ["", THIN, f"  EDGE TREND   -> {et.get('direction','?').upper()}"]
    for obs in et.get("observations", []):
        out.append(f"    - {obs}")

    verdict = a.get("verdict", "")
    out += ["", LINE, f"  VERDICT:  {_VERDICT_LABEL.get(verdict, verdict)}", LINE]
    for reason in a.get("verdict_reasons", []):
        out.append(f"    - {reason}")
    if a.get("caveats"):
        out += ["", "  Caveats:"]
        for c in a["caveats"]:
            out.append(f"    - {c}")
    if not messages_used:
        out.append("    - No raw messages were provided, so the language/marketing/"
                   "integrity-claims analysis is limited to the log.")

    out += [
        "",
        LINE,
        "  Reminder: this is an ADVISORY analyst aid to inform YOUR judgment.",
        "  It is not part of the trade pipeline and makes no automated decisions.",
        LINE,
    ]
    return "\n".join(out)


# ----------------------------------------------------------------------------
# CLI
# ----------------------------------------------------------------------------
def _usage():
    print("  Usage:")
    print("    python assess_trader.py                       # list traders in your log")
    print("    python assess_trader.py FAROUK                # assess from logged trades")
    print("    python assess_trader.py FAROUK --messages traders/farouk_messages.txt")
    print("    python assess_trader.py FAROUK --facts-only   # computed facts, no API call")
    print("    python assess_trader.py FAROUK --out traders/farouk_assessment.txt")


def _parse_args(argv):
    opts = {"name": None, "messages": None, "model": MODEL, "facts_only": False, "out": None}
    i = 0
    while i < len(argv):
        a = argv[i]
        if a in ("-h", "--help", "help"):
            opts["help"] = True
        elif a in ("-l", "--list", "list"):
            opts["list"] = True
        elif a == "--facts-only":
            opts["facts_only"] = True
        elif a in ("--messages", "-m"):
            i += 1
            opts["messages"] = argv[i] if i < len(argv) else None
        elif a == "--model":
            i += 1
            opts["model"] = argv[i] if i < len(argv) else MODEL
        elif a == "--out":
            i += 1
            opts["out"] = argv[i] if i < len(argv) else None
        elif not a.startswith("-") and opts["name"] is None:
            opts["name"] = a
        else:
            print(f"  (Ignoring unrecognised option: {a})")
        i += 1
    return opts


def _default_messages_path(name: str) -> str:
    return os.path.join("traders", f"{name.lower()}_messages.txt")


def main():
    argv = [a for a in sys.argv[1:] if a.strip()]
    opts = _parse_args(argv)

    if opts.get("help"):
        _usage()
        return

    path = config.PAPER_LOG_FILE
    if not os.path.exists(path):
        _stop(f"there's no log yet ('{path}'). Log some signals first.")
        return

    try:
        rows = _load_rows(path)
    except PermissionError:
        _stop(f"couldn't open '{path}' — is it open in Excel? Close it and retry.")
        return

    # No name (or --list): show who's in the log.
    if not opts["name"] or opts.get("list"):
        known = _known_traders(rows)
        print(LINE)
        print("   TRADER ASSESSMENT — who's in your log?")
        print(LINE)
        if not known:
            print("   (No traders recorded yet — log some signals with a source first.)")
        else:
            for tag, count in known:
                print(f"   {tag:<18} {count} signal(s)")
            print("\n   Assess one with:  python assess_trader.py <NAME>")
        print(LINE)
        return

    name = opts["name"]
    facts = compute_facts(rows, name)
    if facts["signals_total"] == 0 and not (opts["messages"] or
                                            os.path.exists(_default_messages_path(name))):
        _stop(f"found no logged trades for '{name}' and no messages file.\n"
              "  Check the name (run with no arguments to list traders), or pass\n"
              "  --messages <file> to assess their language only.")
        return

    # Messages: explicit path, else auto-look in traders/<name>_messages.txt.
    msg_path = opts["messages"] or _default_messages_path(name)
    messages, truncated = _read_messages(msg_path)
    if messages is not None:
        print(f"  Using messages file: {msg_path}"
              + ("  (truncated to fit)" if truncated else ""))
    elif opts["messages"]:
        print(f"  (Messages file not found: {opts['messages']} — assessing from the log only.)")

    # --facts-only: print the grounded facts and stop (no API key needed).
    if opts["facts_only"]:
        print(LINE)
        print(f"   TRADER FACTS — {facts['trader']}   (computed, read-only, no API call)")
        print("\n".join(_facts_block(facts)))
        print(THIN)
        print("  This is the raw evidence. Run without --facts-only for the written")
        print("  advisory assessment (needs ANTHROPIC_API_KEY).")
        print(LINE)
        return

    client = _client()
    if client is None:
        print("  Tip: run with --facts-only to see the computed track record without the API.")
        return

    print("  Analysing... (reading the track record and any messages)\n")
    try:
        assessment = run_assessment(client, facts, messages, truncated, opts["model"])
    except Exception as e:
        _stop(f"the assessment call failed: {e}\n"
              "  Check your internet connection and that ANTHROPIC_API_KEY is valid.")
        return

    report = render_report(facts, assessment, messages_used=bool(messages))
    print(report)

    if opts["out"]:
        try:
            os.makedirs(os.path.dirname(opts["out"]) or ".", exist_ok=True)
            with open(opts["out"], "w", encoding="utf-8") as f:
                f.write(report + "\n")
            print(f"\n  Saved to {opts['out']}")
        except OSError as e:
            print(f"\n  (Couldn't save to {opts['out']}: {e})")


if __name__ == "__main__":
    main()
