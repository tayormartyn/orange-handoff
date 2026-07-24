"""
check_rules.py — does a trader follow their OWN stated rules, and does it pay?

================================  WHAT THIS IS  ================================
An ADVISORY, read-only analysis. It takes a trader's stated rules (a plain-English
JSON you control, e.g. traders/farouk_rules.json) and their logged trades from
paper_log.csv, and reports:

  1. RULE ADHERENCE   — for each rule, how often the logged trades appear to follow
                        it. Where the data can't show it, it says "can't determine
                        from data" rather than guessing.
  2. RULE PROFITABILITY — do rule-COMPLIANT trades outperform rule-BREAKING ones?
                        (e.g. trades with a stop vs without; in-size vs oversized.)
  3. PLAIN-ENGLISH SUMMARY — which rules correlate with wins, which breaks with
                        losses, with a loud note on the data's limits.

It is NOT part of the trade pipeline. It changes no sizing, blocks no trade,
routes nothing, and touches no money or the LIVE stub. You read it; you decide.
===============================================================================

Run it:
    python check_rules.py                 # list traders + whether a rules file exists
    python check_rules.py FAROUK          # check FAROUK against traders/farouk_rules.json
    python check_rules.py FAROUK --rules traders/farouk_rules.json
    python check_rules.py FAROUK --out traders/farouk_rules_report.txt

PAPER MODE ONLY. Read-only to paper_log.csv. No API key needed — this is pure
analysis of your own logged data.
"""

import csv
import json
import os
import sys
from datetime import datetime
from decimal import Decimal

import config
import review

SMALL_SAMPLE = 5          # below this, a group's numbers are a hint, not a verdict
LINE = "=" * 70
THIN = "-" * 70


# ----------------------------------------------------------------------------
# Friendly guards
# ----------------------------------------------------------------------------
def _stop(message: str):
    print("\n  Can't run the rule check:")
    print(f"  {message}\n")


# ----------------------------------------------------------------------------
# Reading the log + rules (READ-ONLY)
# ----------------------------------------------------------------------------
def _load_rows(path: str):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _matches_trader(row: dict, name: str) -> bool:
    n = name.upper().strip()
    source = (row.get("source") or "").upper()
    trader = (row.get("trader") or "").upper()
    return bool(n) and (n in source or n == trader or n in trader)


def _known_traders(rows: list) -> list:
    counts = {}
    for r in rows:
        tag = (r.get("trader") or "").strip() or (r.get("source") or "").strip()
        if tag:
            counts[tag] = counts.get(tag, 0) + 1
    return sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))


def _default_rules_path(name: str) -> str:
    return os.path.join("traders", f"{name.lower()}_rules.json")


def _load_rules(path: str):
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return data.get("rules", []), data


# ----------------------------------------------------------------------------
# Build the per-trade facts we can actually check rules against
# ----------------------------------------------------------------------------
def _f(value):
    try:
        return float(str(value).strip())
    except (TypeError, ValueError):
        return None


def build_trades(rows: list, name: str, pot: Decimal):
    """
    Returns (filled, missed_count). `filled` is a list of dicts for trades that
    were actually taken (a real entry), in time order, each carrying its realised
    R (via review, so it matches review.py) plus the fields the rule checks need.
    """
    mine = [r for r in rows if _matches_trader(r, name)]
    mine.sort(key=lambda r: (r.get("timestamp") or ""))

    filled = []
    missed = 0
    for r in mine:
        rr, _reached, status = review.realised_r(r)
        if status == "missed":
            missed += 1
            continue
        if status != "ok":
            continue   # 'open' / 'bad' rows aren't a taken trade we can score
        dr = review.trade_dollar_risk(r)

        # Risk % per trade: prefer the logged risk_pct (a fraction), else derive
        # from dollar_risk / pot. None if neither is available.
        risk_pct = _f(r.get("risk_pct"))
        if risk_pct is not None:
            risk_pct_value = risk_pct * 100.0
        else:
            d = _f(r.get("dollar_risk")) or _f(r.get("cash_at_risk"))
            risk_pct_value = (d / float(pot) * 100.0) if (d and float(pot)) else None

        filled.append({
            "date": (r.get("timestamp") or "")[:10],
            "source": (r.get("source") or "").strip(),
            "r": rr,
            "pnl": rr * dr,
            "win": rr > 0,
            "loss": rr < 0,
            "has_stop": bool((r.get("sl_price") or "").strip()),
            "risk_pct_value": risk_pct_value,
            "notes": (r.get("notes") or "").lower(),
        })
    return filled, missed


# ----------------------------------------------------------------------------
# The rule checks. Each returns a dict:
#   detectable   bool  — can the log show this at all?
#   reason       str   — why not, if not detectable
#   statuses     list|None — per-filled-trade "compliant"/"breaking"/"undetermined"
#   evidence     str   — optional aggregate note
#   split        None | "clean" | "soft" — kind of compliant-vs-breaking comparison
#   group_labels (compliant_label, breaking_label) for the profitability section
# ----------------------------------------------------------------------------
def _check_stop_present(rule, filled, ctx):
    statuses = ["compliant" if t["has_stop"] else "breaking" for t in filled]
    return {"detectable": True, "statuses": statuses, "split": "clean",
            "group_labels": ("had a stop", "no stop logged")}


def _check_risk_band(rule, filled, ctx):
    p = rule.get("params", {})
    lo = float(p.get("min_pct", 0.0))
    hi = float(p.get("max_pct", 100.0))
    eps = 1e-9
    statuses = []
    for t in filled:
        v = t["risk_pct_value"]
        if v is None:
            statuses.append("undetermined")
        elif lo - eps <= v <= hi + eps:
            statuses.append("compliant")
        else:
            statuses.append("breaking")
    return {"detectable": True, "statuses": statuses, "split": "clean",
            "group_labels": (f"risk {lo:g}-{hi:g}%", "out of size band"),
            "evidence": f"size band checked: {lo:g}% to {hi:g}% risk per trade"}


def _check_notes_evidence(rule, filled, ctx):
    p = rule.get("params", {})
    kws = [k.lower() for k in p.get("keywords", [])]
    shows = (p.get("shows") or "compliance").lower()
    statuses = []
    for t in filled:
        hit = any(k in t["notes"] for k in kws)
        if shows == "breach":
            statuses.append("breaking" if hit else "undetermined")
        else:
            statuses.append("compliant" if hit else "undetermined")
    n_hit = sum(1 for s in statuses if s in ("compliant", "breaking"))
    if shows == "breach":
        evidence = (f"{n_hit} trade(s) show breach wording in notes"
                    if n_hit else "no breach wording found in notes")
        labels = ("no breach noted", "breach noted")
    else:
        evidence = (f"{n_hit} trade(s) note doing this"
                    if n_hit else "no notes mention this")
        labels = ("noted doing it", "not mentioned")
    # 'soft' because notes only PROVE the cited side; the absence isn't proof of
    # the opposite. We still offer a clearly-caveated comparison when useful.
    split = "soft" if n_hit else None
    return {"detectable": True, "statuses": statuses, "split": split,
            "evidence": evidence, "group_labels": labels, "shows": shows}


def _check_one_per_day(rule, filled, ctx):
    counts = {}
    for t in filled:
        counts[t["date"]] = counts.get(t["date"], 0) + 1
    statuses = ["compliant" if counts[t["date"]] == 1 else "breaking" for t in filled]
    multi = sum(1 for d, c in counts.items() if c > 1)
    maxc = max(counts.values()) if counts else 0
    evidence = (f"{len(counts)} trading day(s); {multi} had several entries "
                f"(up to {maxc} in a day) — proxy for 'one good trade is enough'")
    return {"detectable": True, "statuses": statuses, "split": "clean",
            "evidence": evidence,
            "group_labels": ("one trade that day", "several that day")}


def _check_misses_not_chase(rule, filled, ctx):
    limit_src = sum(1 for t in filled if "LIMIT" in t["source"].upper())
    evidence = (f"{ctx['missed']} signal(s) logged as MISSED (recorded, not chased); "
                f"{limit_src} filled trade(s) came from a LIMIT-order source")
    return {"detectable": True, "statuses": None, "split": None, "evidence": evidence,
            "reason": "whether he CHASED a missed entry isn't directly loggable — "
                      "this is supporting evidence only"}


def _check_not_detectable(rule, filled, ctx):
    reason = rule.get("params", {}).get("reason", "not recorded in the log")
    return {"detectable": False, "reason": reason, "statuses": None, "split": None}


CHECKS = {
    "stop_present": _check_stop_present,
    "risk_pct_band": _check_risk_band,
    "notes_evidence": _check_notes_evidence,
    "one_trade_per_day": _check_one_per_day,
    "logs_misses_not_chase": _check_misses_not_chase,
    "not_detectable": _check_not_detectable,
}


def run_check(rule, filled, ctx):
    fn = CHECKS.get(rule.get("check"), _check_not_detectable)
    res = fn(rule, filled, ctx)
    if rule.get("check") not in CHECKS:
        res = {"detectable": False,
               "reason": f"unknown check '{rule.get('check')}' — treated as not detectable",
               "statuses": None, "split": None}
    res["rule"] = rule
    return res


# ----------------------------------------------------------------------------
# Group stats (reuse review's R for consistency)
# ----------------------------------------------------------------------------
def _group_stats(trades):
    n = len(trades)
    if n == 0:
        return {"n": 0}
    wins = sum(1 for t in trades if t["win"])
    total_r = sum((t["r"] for t in trades), Decimal("0"))
    return {
        "n": n,
        "win_pct": round(100.0 * wins / n, 1),
        "exp": round(float(total_r / Decimal(n)), 3),
        "net_r": round(float(total_r), 2),
    }


def _split_groups(res, filled):
    """Compliant vs breaking trade lists for a rule with statuses."""
    statuses = res.get("statuses")
    if not statuses:
        return [], []
    compliant = [t for t, s in zip(filled, statuses) if s == "compliant"]
    breaking = [t for t, s in zip(filled, statuses) if s == "breaking"]
    return compliant, breaking


# ----------------------------------------------------------------------------
# Rendering
# ----------------------------------------------------------------------------
def _flag(n):
    return "  [<5, hint only]" if n < SMALL_SAMPLE else ""


def render(name, rules, results, filled, missed, pot):
    out = [
        LINE,
        f"   RULE ADHERENCE & PROFITABILITY — {name.upper()}",
        f"   {datetime.now().strftime('%Y-%m-%d %H:%M')}   ·   ADVISORY ANALYST AID",
        LINE,
        "   *** ADVISORY ONLY — informs YOUR judgment. It changes no sizing,",
        "   blocks no trade, and touches no pipeline or money. You decide. ***",
        LINE,
        "",
        f"  Trades assessed : {len(filled)} filled  ({missed} missed signals excluded)",
        f"  Source/trader   : {name.upper()}   ·   Log: {config.PAPER_LOG_FILE} (read-only)",
    ]
    if filled:
        overall = _group_stats(filled)
        out.append(f"  Overall record  : {overall['win_pct']}% win, "
                   f"{overall['exp']:+} R/trade across {overall['n']} trades")

    # --- 1. ADHERENCE -------------------------------------------------------
    out += ["", THIN, "  1) RULE ADHERENCE  (only what the logged data can actually show)", THIN]
    for res in results:
        rule = res["rule"]
        out.append(f"  • {rule['statement']}")
        if not res["detectable"]:
            out.append(f"      can't determine from data — {res.get('reason','not loggable')}")
            out.append("")
            continue
        statuses = res.get("statuses")
        if statuses:
            c = statuses.count("compliant")
            b = statuses.count("breaking")
            u = statuses.count("undetermined")
            detectable_n = c + b
            if res.get("shows") == "breach":
                # For breach-type notes rules, framing is "breaches found".
                out.append(f"      breaches found : {b}   "
                           f"(no breach wording on the other {u})")
            elif detectable_n:
                out.append(f"      followed in {c}/{detectable_n} where detectable   "
                           f"(compliant {c} · breaking {b} · undetermined {u})")
            else:
                out.append(f"      undetermined for all {u} trades (notes don't say)")
        if res.get("evidence"):
            out.append(f"      evidence: {res['evidence']}")
        if res.get("reason"):
            out.append(f"      note: {res['reason']}")
        out.append("")

    # --- 2. PROFITABILITY ---------------------------------------------------
    out += [THIN, "  2) RULE PROFITABILITY  (do compliant trades outperform breaking ones?)", THIN]
    any_compare = False
    summary_points = []
    for res in results:
        if not res.get("split"):
            continue
        rule = res["rule"]
        compliant, breaking = _split_groups(res, filled)
        if res["split"] == "soft":
            # evidence-vs-rest, clearly caveated (absence isn't proof of breaking)
            if res.get("shows") == "breach":
                grp_a = breaking
                grp_b = [t for t in filled if t not in breaking]
                la, lb = "breach noted", "rest"
            else:
                grp_a = compliant
                grp_b = [t for t in filled if t not in compliant]
                la, lb = "noted doing it", "not mentioned"
            if not grp_a or not grp_b:
                continue
            sa, sb = _group_stats(grp_a), _group_stats(grp_b)
            out.append(f"  • {rule['statement']}   [soft — notes-based, absence isn't proof]")
            out.append(f"      {la:<16}: n={sa['n']:<3} win {sa['win_pct']}%  "
                       f"exp {sa['exp']:+} R{_flag(sa['n'])}")
            out.append(f"      {lb:<16}: n={sb['n']:<3} win {sb['win_pct']}%  "
                       f"exp {sb['exp']:+} R{_flag(sb['n'])}")
            out.append("")
            any_compare = True
            # A clearly-caveated summary point when the evidenced side stands out.
            if res.get("shows") != "breach" and (sa["exp"] - sb["exp"]) > 0.05:
                summary_points.append(
                    f"Trades where he NOTED \"{rule['statement']}\" did better "
                    f"({sa['exp']:+} R vs {sb['exp']:+} R) — notes-based, suggestive not proof.")
            continue

        # clean compliant-vs-breaking split
        la, lb = res.get("group_labels", ("compliant", "breaking"))
        if not compliant or not breaking:
            note = ("all trades complied — no breaking trades to compare"
                    if compliant and not breaking else
                    "no compliant trades to compare" if breaking else
                    "not enough data to compare")
            out.append(f"  • {rule['statement']}")
            out.append(f"      {note}.")
            out.append("")
            continue
        sc, sb = _group_stats(compliant), _group_stats(breaking)
        diff = sc["exp"] - sb["exp"]
        if diff > 0.05:
            verdict = f"compliant outperform by {diff:+.2f} R/trade"
            summary_points.append(f"Following \"{rule['statement']}\" correlates with "
                                  f"better results ({la} {sc['exp']:+} R vs {lb} {sb['exp']:+} R).")
        elif diff < -0.05:
            verdict = f"BREAKING did better by {-diff:.2f} R/trade (unexpected — small sample?)"
            summary_points.append(f"Oddly, breaking \"{rule['statement']}\" looks better in the "
                                  f"log ({lb} {sb['exp']:+} R vs {la} {sc['exp']:+} R) — check the sample.")
        else:
            verdict = "about the same"
        out.append(f"  • {rule['statement']}")
        out.append(f"      {la:<16}: n={sc['n']:<3} win {sc['win_pct']}%  "
                   f"exp {sc['exp']:+} R{_flag(sc['n'])}")
        out.append(f"      {lb:<16}: n={sb['n']:<3} win {sb['win_pct']}%  "
                   f"exp {sb['exp']:+} R{_flag(sb['n'])}")
        out.append(f"      -> {verdict}")
        out.append("")
        any_compare = True
    if not any_compare:
        out.append("  (Nothing had both a compliant AND a breaking group to compare yet.)")
        out.append("")

    # --- 3. PLAIN-ENGLISH SUMMARY ------------------------------------------
    out += [THIN, "  3) PLAIN-ENGLISH SUMMARY", THIN]
    if summary_points:
        for p in summary_points:
            out.append(f"    - {p}")
    else:
        out.append("    - No rule yet shows a clear, comparable profit difference in the log.")
    # Adherence highlights
    for res in results:
        st = res.get("statuses")
        if res["detectable"] and st:
            b = st.count("breaking")
            if res.get("shows") == "breach" and b:
                out.append(f"    - Possible breaches of \"{res['rule']['statement']}\" "
                           f"in {b} trade(s) (from notes).")
    out.append("")

    # --- DATA LIMITS --------------------------------------------------------
    out += [THIN, "  DATA LIMITS  (be honest about what the log can't show)", THIN]
    for res in results:
        rule = res["rule"]
        if not res["detectable"]:
            out.append(f"    - \"{rule['statement']}\": {res.get('reason','not loggable')}.")
        elif res.get("shows") == "breach":
            out.append(f"    - \"{rule['statement']}\": scanned trade notes for breach "
                       "wording — not finding it is NOT proof it never happened "
                       "(absence isn't proof).")
        elif res.get("split") == "soft" or res.get("statuses") is None:
            why = res.get("reason") or ("based on trade notes — absence of a note is "
                                        "NOT proof the rule was broken")
            out.append(f"    - \"{rule['statement']}\": {why}.")
        elif res.get("statuses") and "undetermined" in res["statuses"]:
            u = res["statuses"].count("undetermined")
            if u:
                out.append(f"    - \"{rule['statement']}\": {u} trade(s) undetermined "
                           "(notes don't say either way).")
    out += [
        "    - Small groups (flagged [<5]) are hints, not verdicts.",
        "    - Correlation is not proof of cause — these are observations to weigh,",
        "      not rules for the machine to act on.",
        "",
        LINE,
        "  Reminder: ADVISORY analyst aid — read-only, not part of the trade",
        "  pipeline, and it makes no automated decisions. PAPER mode.",
        LINE,
    ]
    return "\n".join(out)


# ----------------------------------------------------------------------------
# CLI
# ----------------------------------------------------------------------------
def _usage():
    print("  Usage:")
    print("    python check_rules.py                 # list traders + rules-file status")
    print("    python check_rules.py FAROUK          # check against traders/farouk_rules.json")
    print("    python check_rules.py FAROUK --rules <path.json>")
    print("    python check_rules.py FAROUK --out traders/farouk_rules_report.txt")


def _parse_args(argv):
    opts = {"name": None, "rules": None, "out": None}
    i = 0
    while i < len(argv):
        a = argv[i]
        if a in ("-h", "--help", "help"):
            opts["help"] = True
        elif a in ("-l", "--list", "list"):
            opts["list"] = True
        elif a == "--rules":
            i += 1
            opts["rules"] = argv[i] if i < len(argv) else None
        elif a == "--out":
            i += 1
            opts["out"] = argv[i] if i < len(argv) else None
        elif not a.startswith("-") and opts["name"] is None:
            opts["name"] = a
        else:
            print(f"  (Ignoring unrecognised option: {a})")
        i += 1
    return opts


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

    if not opts["name"] or opts.get("list"):
        print(LINE)
        print("   RULE CHECK — who's in your log?")
        print(LINE)
        known = _known_traders(rows)
        if not known:
            print("   (No traders recorded yet.)")
        for tag, count in known:
            base = tag.split("-")[0]
            rules_path = _default_rules_path(base)
            has = "rules: yes" if os.path.exists(rules_path) else f"rules: none ({rules_path})"
            print(f"   {tag:<18} {count:>3} signal(s)   {has}")
        print("\n   Check one with:  python check_rules.py <NAME>")
        print(LINE)
        return

    name = opts["name"]
    rules_path = opts["rules"] or _default_rules_path(name)
    if not os.path.exists(rules_path):
        _stop(f"no rules file for '{name}'.\n"
              f"  Expected: {rules_path}\n"
              "  Create one (see traders/farouk_rules.json for the format), or pass\n"
              "  --rules <path>.")
        return
    try:
        rules, _meta = _load_rules(rules_path)
    except (json.JSONDecodeError, OSError) as e:
        _stop(f"couldn't read the rules file '{rules_path}': {e}")
        return
    if not rules:
        _stop(f"'{rules_path}' has no rules in it.")
        return

    pot = Decimal(config.POT_SIZE)
    filled, missed = build_trades(rows, name, pot)
    if not filled and missed == 0:
        _stop(f"found no logged trades for '{name}'. Run with no arguments to list traders.")
        return

    ctx = {"missed": missed, "pot": pot}
    results = [run_check(rule, filled, ctx) for rule in rules]
    report = render(name, rules, results, filled, missed, pot)
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
