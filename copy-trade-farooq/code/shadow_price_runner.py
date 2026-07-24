"""
shadow_price_runner.py — SHADOW MODE Phase 1a, the coverage runner + GO/NO-GO.

Runs the timestamped quote lookup over ALL 28 archived signal timestamps (plus a
selected sample of management-message timestamps), builds the coverage report the
brief asks for, and evaluates the FROZEN GO/NO-GO gates.

This is PURE MEASUREMENT. It computes NO R, NO fill, NO ledger, NO expectancy,
NO no-chase. It only asks: for each timestamp, did we get a clean, well-graded,
reproducible quote — or an honestly-explained absence?

The archive's timestamps are `telegram_posted_at` (the message's own posted time,
minute resolution, no receipt timestamp), so EVERY one is timestamp grade T-C.
By rule, none can be "exact executable" — the price grade still measures how
well-quoted the instant was.

GO/NO-GO thresholds are FROZEN as constants below. They are defined before any
result is computed, so the bar cannot be moved after seeing the numbers.

Usage:
    python shadow_price_runner.py            # full run + report + GO/NO-GO
    python shadow_price_runner.py --no-mgmt  # signals only
    python shadow_price_runner.py --json OUT # also write the full report JSON
"""

import argparse
import json
import sqlite3
import statistics
from datetime import datetime, timezone
from decimal import Decimal

import gold_calendar as calendar
import price_cache
import quote_lookup as ql
import secondary_source as secondary

DB_PATH = price_cache.os.path.join("data", "signal_archive.db")
REPORT_PATH = price_cache.os.path.join("data", "shadow_phase1a_report.json")

# ============================================================================
# FROZEN GO/NO-GO THRESHOLDS  (set before any result is seen — do not tune to fit)
# ============================================================================
GATE_MIN_AB_FRACTION = 0.90          # >=90% of normal-session signal ts must be P-A/P-B
MGMT_SAMPLE_SIZE = 12                # selected management timestamps (supplementary)
SECONDARY_SAMPLE_SIZE = 6           # timestamps to cross-check against the secondary source


# ----------------------------------------------------------------------------
# Timestamp sources (from the permanent archive)
# ----------------------------------------------------------------------------
def _parse_archive_ts(s):
    """Archive timestamps are 'YYYY-MM-DD HH:MM' (UTC, posted-only). -> tz-aware UTC."""
    dt = datetime.strptime(s.strip(), "%Y-%m-%d %H:%M")
    return dt.replace(tzinfo=timezone.utc)


def load_signal_timestamps(db_path=DB_PATH):
    """The 28 signal timestamps (telegram_posted_at), each tagged T-C."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT s.signal_id, s.asset, s.direction, t.telegram_posted_at "
        "FROM signal_timing t JOIN signals s ON s.signal_id = t.signal_id "
        "WHERE t.telegram_posted_at IS NOT NULL "
        "ORDER BY t.telegram_posted_at").fetchall()
    conn.close()
    out = []
    for r in rows:
        out.append({
            "kind": "signal",
            "signal_id": r["signal_id"],
            "asset": r["asset"],
            "direction": r["direction"],
            "ts_raw": r["telegram_posted_at"],
            "when": _parse_archive_ts(r["telegram_posted_at"]),
        })
    return out


def load_management_timestamps(signal_raws, db_path=DB_PATH, n=MGMT_SAMPLE_SIZE):
    """A SELECTED, evenly-spread sample of management/commentary message times
    (raw_message_versions.sent_at_utc) that are NOT signal-entry timestamps.

    These are supplementary coverage (management updates a trader posts after a
    signal). They are NOT part of the GO/NO-GO gate, which is about signals.
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT DISTINCT sent_at_utc FROM raw_message_versions "
        "WHERE sent_at_utc IS NOT NULL AND sent_at_utc != '' "
        "ORDER BY sent_at_utc").fetchall()
    conn.close()
    signal_set = set(signal_raws)
    candidates = [r["sent_at_utc"] for r in rows if r["sent_at_utc"] not in signal_set]
    if not candidates:
        return []
    # Even spread across the whole window (deterministic, no randomness).
    if len(candidates) <= n:
        chosen = candidates
    else:
        step = len(candidates) / n
        chosen = [candidates[int(i * step)] for i in range(n)]
    out = []
    for s in chosen:
        try:
            when = _parse_archive_ts(s)
        except ValueError:
            continue
        out.append({"kind": "management", "ts_raw": s, "when": when})
    return out


# ----------------------------------------------------------------------------
# Run one timestamp
# ----------------------------------------------------------------------------
def run_one(item):
    """Look up one timestamp (always T-C — archive is posted-only) and attach the
    quote result + a few derived fields used by the report."""
    res = ql.lookup(item["when"], timestamp_grade=ql.T_C)
    spread = None
    if res.before is not None:
        spread = res.before.ask - res.before.bid
    elif res.after is not None:
        spread = res.after.ask - res.after.bid
    mid = None
    if res.before is not None:
        mid = (res.before.bid + res.before.ask) / 2
    return {
        "item": item,
        "result": res,
        "spread": spread,
        "mid": mid,
    }


# ----------------------------------------------------------------------------
# Coverage report
# ----------------------------------------------------------------------------
def _pct(n, d):
    return (100.0 * n / d) if d else 0.0


def build_coverage(signal_runs, mgmt_runs):
    """Assemble the coverage report dict the brief specifies."""
    def summarise(runs):
        total = len(runs)
        open_runs = [r for r in runs if r["result"].market_status == ql.OPEN_WITH_TICKS]
        closed = [r for r in runs if r["result"].market_status == ql.MARKET_CLOSED]
        missing = [r for r in runs if r["result"].market_status == ql.DATA_MISSING]
        errors = [r for r in runs if r["result"].market_status == ql.ERROR]
        pa = [r for r in open_runs if r["result"].price_grade == ql.P_A]
        pb = [r for r in open_runs if r["result"].price_grade == ql.P_B]
        pcd = [r for r in open_runs if r["result"].price_grade in (ql.P_C, ql.P_D)]
        pu = [r for r in open_runs if r["result"].price_grade == ql.P_U]
        gaps = [r["result"].quote_gap_ms for r in open_runs
                if r["result"].quote_gap_ms is not None]
        spreads = [r["spread"] for r in open_runs if r["spread"] is not None]
        # normal-session = market open with ticks (includes thin holidays; tracked separately)
        thin = [r for r in open_runs if r["result"].session.thin_liquidity]
        ab = pa + pb
        return {
            "total_requested": total,
            "market_open_with_ticks": len(open_runs),
            "market_closed": len(closed),
            "unexplained_missing": len(missing),
            "errors": len(errors),
            "price_grade": {
                "P-A": len(pa), "P-B": len(pb), "P-C+P-D": len(pcd), "P-U": len(pu),
            },
            "A_or_B_count": len(ab),
            "A_or_B_pct_of_open": round(_pct(len(ab), len(open_runs)), 1),
            "thin_holiday_open": len(thin),
            "quote_gap_ms": {
                "median": int(statistics.median(gaps)) if gaps else None,
                "worst": max(gaps) if gaps else None,
                "n": len(gaps),
            },
            "spread_usd": _spread_distribution(spreads),
        }

    return {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "timestamp_grade_note": ("ALL archive timestamps are posted-only (T-C); "
                                 "none can be 'exact executable' by rule."),
        "signals": summarise(signal_runs),
        "management_sample": summarise(mgmt_runs) if mgmt_runs else None,
    }


def _spread_distribution(spreads):
    if not spreads:
        return None
    s = sorted(spreads)
    def q(p):
        return str(s[min(len(s) - 1, int(p * len(s)))])
    return {
        "min": str(s[0]),
        "median": str(s[len(s) // 2]),
        "p90": q(0.9),
        "max": str(s[-1]),
        "n": len(s),
    }


# ----------------------------------------------------------------------------
# Secondary cross-check (sampled)
# ----------------------------------------------------------------------------
def run_secondary(signal_runs, n=SECONDARY_SAMPLE_SIZE):
    src = secondary.default_source()
    available, reason = src.is_available()
    open_runs = [r for r in signal_runs
                 if r["result"].market_status == ql.OPEN_WITH_TICKS and r["mid"] is not None]
    if not open_runs:
        return {"available": available, "reason": reason, "checks": []}
    # even spread sample
    if len(open_runs) <= n:
        sample = open_runs
    else:
        step = len(open_runs) / n
        sample = [open_runs[int(i * step)] for i in range(n)]
    checks = []
    for r in sample:
        cc = secondary.cross_check(r["mid"], r["item"]["when"], src)
        cc["when_utc"] = r["item"]["when"].isoformat()
        checks.append(cc)
    return {"available": available, "reason": reason, "source": src.name, "checks": checks}


# ----------------------------------------------------------------------------
# Reproducibility / hash verification over every touched hour
# ----------------------------------------------------------------------------
def verify_all_cached(all_runs):
    """Every hour we touched must be hashed AND reproducible (re-decode == stored)."""
    hours = {}
    for r in all_runs:
        when = r["item"]["when"]
        hs = price_cache.adapter._floor_hour(when)
        hours[hs.isoformat()] = hs
    problems = []
    verified = 0
    for iso, hs in sorted(hours.items()):
        ok, probs = price_cache.verify_cached(hs)
        if ok:
            verified += 1
        else:
            problems.append({"hour": iso, "problems": probs})
    return {"hours_touched": len(hours), "verified": verified, "problems": problems}


# ----------------------------------------------------------------------------
# FROZEN GO/NO-GO evaluation
# ----------------------------------------------------------------------------
def evaluate_go_no_go(signal_runs, mgmt_runs, coverage, secondary_report, cache_report):
    """Evaluate each frozen gate -> list of (name, passed, detail). NO threshold is
    computed from the results; they are the constants at the top of this file."""
    gates = []
    all_runs = signal_runs + mgmt_runs

    # G1 + G6: every cached file hashed + reproducible (repeat decode identical).
    g1 = cache_report["problems"] == []
    gates.append(("G1/G6 every cached hour hashed + reproducible", g1,
                  f"{cache_report['verified']}/{cache_report['hours_touched']} hours verified; "
                  f"problems={cache_report['problems']}"))

    # G2: no silent interpolation / forward-fill. Structural: no result may claim a
    # price (exact_executable) without BOTH bracketing ticks, and nothing is P-A
    # while missing a side.
    viol = []
    for r in all_runs:
        res = r["result"]
        if res.exact_executable and (res.before is None or res.after is None):
            viol.append(f"{res.when.isoformat()}: exec without both ticks")
        if res.price_grade in (ql.P_A, ql.P_B, ql.P_C) and (res.before is None or res.after is None):
            viol.append(f"{res.when.isoformat()}: graded {res.price_grade} without both ticks")
    g2 = viol == []
    gates.append(("G2 no silent interpolation / forward-fill", g2,
                  "no result is priced without both real bracketing ticks" if g2
                  else f"violations={viol}"))

    # G3: all normal-session timestamps return a valid result or an explained error.
    # An unexplained DATA_MISSING during an open session fails this gate.
    open_signal = [r for r in signal_runs if r["result"].session.is_open]
    g3_fail = [r["result"].when.isoformat() for r in open_signal
               if r["result"].market_status not in (ql.OPEN_WITH_TICKS, ql.ERROR)]
    g3 = g3_fail == []
    gates.append(("G3 all normal-session signal ts valid-or-explained", g3,
                  f"{len(open_signal)} open-session signals; unexplained={g3_fail}"))

    # G4: >=90% of normal-session (open) signal ts are P-A or P-B.
    n_open = coverage["signals"]["market_open_with_ticks"]
    n_ab = coverage["signals"]["A_or_B_count"]
    frac = (n_ab / n_open) if n_open else 0.0
    g4 = frac >= GATE_MIN_AB_FRACTION
    gates.append((f"G4 >={int(GATE_MIN_AB_FRACTION*100)}% normal-session signals P-A/P-B", g4,
                  f"{n_ab}/{n_open} = {frac*100:.1f}% (threshold {GATE_MIN_AB_FRACTION*100:.0f}%)"))

    # G5: no unresolved timezone/decimal/scaling discrepancies in any touched hour.
    bad_markers = ("SCALING", "INSTRUMENT", "FIELD-SWAP", "OUT-OF-HOUR", "ZERO/NEG")
    anom_hits = []
    for r in all_runs:
        for a in r["result"].anomalies:
            if any(m in a for m in bad_markers):
                anom_hits.append(f"{r['result'].when.isoformat()}: {a}")
    g5 = anom_hits == []
    gates.append(("G5 no unresolved tz/decimal/scaling discrepancy", g5,
                  "instrument/scale/UTC validation clean" if g5 else f"hits={anom_hits}"))

    # G7: secondary source shows no UNEXPLAINED divergence. Unavailable == cannot
    # corroborate (agreed: does NOT fail the gate); only an actual 'diverges' fails.
    diverges = [c for c in secondary_report.get("checks", []) if c.get("status") == "diverges"]
    g7 = diverges == []
    if not secondary_report.get("available"):
        detail = (f"secondary UNAVAILABLE ({secondary_report.get('reason')}) — "
                  f"cannot corroborate; gate not failed by agreement")
    else:
        detail = f"{len(secondary_report.get('checks', []))} checks; diverges={len(diverges)}"
    gates.append(("G7 no unexplained secondary divergence", g7, detail))

    # G8: daily breaks / weekends / holidays correctly identified. Consistency:
    # any timestamp the calendar calls CLOSED must have NO ticks from the feed, and
    # any it calls OPEN in our set that returned ticks confirms the open classification.
    mismatch = []
    for r in all_runs:
        res = r["result"]
        closed_by_cal = not res.session.is_open
        had_ticks = res.market_status == ql.OPEN_WITH_TICKS
        if closed_by_cal and had_ticks:
            mismatch.append(f"{res.when.isoformat()}: calendar=CLOSED but feed had ticks")
    g8 = mismatch == []
    gates.append(("G8 breaks/weekends/holidays correctly identified", g8,
                  "calendar vs feed consistent" if g8 else f"mismatch={mismatch}"))

    overall = all(p for _, p, _ in gates)
    return overall, gates


# ----------------------------------------------------------------------------
# Orchestration + printing
# ----------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-mgmt", action="store_true", help="signals only")
    ap.add_argument("--json", default=REPORT_PATH, help="write full report JSON here")
    args = ap.parse_args()

    print("Loading archived timestamps...")
    signals = load_signal_timestamps()
    signal_raws = {s["ts_raw"] for s in signals}
    mgmt = [] if args.no_mgmt else load_management_timestamps(signal_raws)
    print(f"  {len(signals)} signal timestamps, {len(mgmt)} management timestamps")

    print("Running quote lookups (downloading + caching hours as needed)...")
    signal_runs = [run_one(s) for s in signals]
    mgmt_runs = [run_one(m) for m in mgmt]

    print("Verifying every cached hour is hashed + reproducible...")
    cache_report = verify_all_cached(signal_runs + mgmt_runs)

    print("Sampling secondary-source cross-check...")
    secondary_report = run_secondary(signal_runs)

    coverage = build_coverage(signal_runs, mgmt_runs)
    overall, gates = evaluate_go_no_go(signal_runs, mgmt_runs, coverage,
                                       secondary_report, cache_report)

    _print_report(coverage, secondary_report, cache_report, gates, overall,
                  signal_runs)

    report = {
        "coverage": coverage,
        "secondary": secondary_report,
        "cache_verification": cache_report,
        "go_no_go": {"overall": "GO" if overall else "NO-GO",
                     "gates": [{"name": n, "passed": p, "detail": d} for n, p, d in gates]},
        "per_signal": [_run_dict(r) for r in signal_runs],
        "per_management": [_run_dict(r) for r in mgmt_runs],
    }
    with open(args.json, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, default=str)
    print(f"\nFull report written to {args.json}")
    return 0 if overall else 1


def _run_dict(r):
    d = r["result"].as_dict()
    d["kind"] = r["item"]["kind"]
    d["ts_raw"] = r["item"]["ts_raw"]
    if r["item"]["kind"] == "signal":
        d["asset"] = r["item"].get("asset")
        d["direction"] = r["item"].get("direction")
        d["signal_id"] = r["item"].get("signal_id")
    return d


def _print_report(coverage, secondary_report, cache_report, gates, overall, signal_runs):
    c = coverage["signals"]
    print("\n" + "=" * 72)
    print("  SHADOW MODE — PHASE 1a PRICE-DATA FOUNDATION — COVERAGE REPORT")
    print("=" * 72)
    print(f"  Source: Dukascopy XAU/USD historical ticks (proven reachable)")
    print(f"  {coverage['timestamp_grade_note']}")
    print("  " + "-" * 68)
    print(f"  SIGNAL TIMESTAMPS")
    print(f"    total requested        : {c['total_requested']}")
    print(f"    market-open (w/ ticks) : {c['market_open_with_ticks']}")
    print(f"    market-closed          : {c['market_closed']}")
    print(f"    unexplained-missing    : {c['unexplained_missing']}")
    print(f"    errors                 : {c['errors']}")
    print(f"    price grade  P-A       : {c['price_grade']['P-A']}")
    print(f"                 P-B       : {c['price_grade']['P-B']}")
    print(f"                 P-C/P-D   : {c['price_grade']['P-C+P-D']}")
    print(f"                 P-U       : {c['price_grade']['P-U']}")
    print(f"    P-A or P-B             : {c['A_or_B_count']}/{c['market_open_with_ticks']} "
          f"({c['A_or_B_pct_of_open']}% of open)")
    print(f"    thin-holiday (open)    : {c['thin_holiday_open']}")
    g = c["quote_gap_ms"]
    print(f"    quote gap ms           : median={g['median']}  worst={g['worst']}  (n={g['n']})")
    sd = c["spread_usd"]
    if sd:
        print(f"    spread $ distribution  : min={sd['min']} median={sd['median']} "
              f"p90={sd['p90']} max={sd['max']}")
    if coverage["management_sample"]:
        m = coverage["management_sample"]
        print("  " + "-" * 68)
        print(f"  MANAGEMENT SAMPLE (supplementary, not in GO/NO-GO)")
        print(f"    total={m['total_requested']}  open={m['market_open_with_ticks']}  "
              f"closed={m['market_closed']}  missing={m['unexplained_missing']}  "
              f"A/B={m['A_or_B_count']}")
    print("  " + "-" * 68)
    print(f"  SECONDARY CROSS-CHECK ({secondary_report.get('source', 'n/a')})")
    if not secondary_report.get("available"):
        print(f"    UNAVAILABLE: {secondary_report.get('reason')}")
    else:
        for ch in secondary_report.get("checks", []):
            print(f"    {ch.get('when_utc')}: {ch.get('status')} "
                  f"(primary={ch.get('primary_mid')} secondary={ch.get('secondary_mid')})")
    print("  " + "-" * 68)
    print(f"  CACHE: {cache_report['verified']}/{cache_report['hours_touched']} hours "
          f"hashed + reproducible")
    print("=" * 72)
    print("  FROZEN GO/NO-GO GATES")
    for name, passed, detail in gates:
        print(f"    [{'PASS' if passed else 'FAIL'}] {name}")
        print(f"           {detail}")
    print("  " + "-" * 68)
    print(f"  RESULT: {'>>> GO <<<' if overall else '>>> NO-GO <<<'}")
    if not overall:
        print("  Per the brief: STOP. Do not proceed to Phase 1b. Report and fix.")
    print("=" * 72)


if __name__ == "__main__":
    raise SystemExit(main())
