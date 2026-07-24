"""
marketcall_allin_report.py — price recovered gold MARKET-CALLS at realistic market
fill (shadow mode) and report the CLEAN vs ALL-IN edge side by side.

Pricing (realistic, includes losses, no best-case):
  * Entry = MARKET fill at posted+delay: executable ASK (long) / BID (short) on real
    Dukascopy ticks, + adverse slippage. Risk = |fill - stop|.
  * Targets: recovered absolute prices as-is; pip targets converted at the project's
    gold pip = $0.10 (CALC_VERSION r-goldpip-v1): tp = fill + dir*pips*0.10. Targets
    on the wrong side of the fill are dropped.
  * Replay on real ticks (shadow_replay): furthest target before stop.
  * No-TP calls: replay to the stop within a bounded session horizon
    H = min(next gold signal, posted + 12h). Stop hit -> loss; otherwise exit
    mark-to-market at H (the real P&L the market gave) — never a best-case TP.

Two numbers, side by side:
  * CLEAN limit-zone edge   = provider/ signed-off R on the clean signals (the +0.28R).
  * ALL-IN edge             = clean limit-zone  +  shadow-priced market-calls.
The market-call leg is shadow-EXECUTABLE R (realistic fill); the limit-zone leg is
provider-reported R — stated plainly (market-calls have no zone entry to score).

Scoring logic unchanged. Archive + signed-off 28 + LIVE stub untouched. PAPER mode.

Usage: python marketcall_allin_report.py [delay_sec]   (default 0)
"""

import json
import statistics
import sys
from datetime import timedelta
from decimal import Decimal

import backfill_audit as BA
import config
import gold_clean_report as G
import shadow_replay as R
import sqlite3

REVISIONS_DB = "data/parser_revisions.db"
PIP_USD = Decimal("0.10")           # project gold pip convention
SLIPPAGE = Decimal(str(config.ASSET_CLASSES["GOLD"]["slippage"]))   # 0.30/side
HORIZON_H = 12                       # hours; session-scale cap for no-TP scalps
GAP_LIMIT_MS = 5000


def _parse_dt(s):
    from datetime import datetime, timezone
    s = str(s).strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    d = datetime.fromisoformat(s)
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


def load_recovered(conn):
    rows = conn.execute(
        "SELECT message_key, sent_at_utc, direction, stop, targets_abs, targets_pips, "
        "validation, raw_text FROM market_call_recoveries "
        "WHERE validation LIKE 'accepted%'").fetchall()
    return [dict(r) for r in rows]


def price_one(mc, gold_times, delay_sec):
    """Shadow-price one recovered market-call. Returns dict with r, status, win/loss."""
    from datetime import timezone
    sign = R.dir_sign(mc["direction"])
    posted = _parse_dt(mc["sent_at_utc"])
    entry_time = posted + timedelta(seconds=delay_sec)
    later = [t for t in gold_times if t > posted]
    boundary = min(later[0] if later else posted + timedelta(hours=HORIZON_H),
                   posted + timedelta(hours=HORIZON_H))
    stop = mc["stop"]
    if stop is None:
        return {"status": "NO_STOP", "r": None}

    # get the executable market fill first (so risk = |fill - stop|)
    ticks, _ = R.ticks_in_range(entry_time, boundary)
    if not ticks:
        return {"status": "CLOSED_OR_MISSING", "r": None}
    entry_ms = int(entry_time.timestamp() * 1000)
    idx = R.first_tick_at_or_after(ticks, entry_ms)
    if idx is None or (ticks[idx].epoch_ms - entry_ms) > GAP_LIMIT_MS:
        return {"status": "NO_EXECUTABLE_QUOTE", "r": None}
    fill = R._entry_price(ticks[idx], sign, True, SLIPPAGE)

    # assemble targets (abs + pip->abs), keep only those on the favorable side, nearest-first
    tabs = [Decimal(str(x)) for x in json.loads(mc["targets_abs"] or "[]")]
    tpip = [Decimal(str(x)) for x in json.loads(mc["targets_pips"] or "[]")]
    tabs += [fill + Decimal(sign) * p * PIP_USD for p in tpip]
    good = [t for t in tabs if (t > fill if sign > 0 else t < fill)]
    good = sorted(good, key=lambda t: abs(t - fill))

    res = R.simulate(mc["direction"], ref_entry=fill, stop=stop, targets=good,
                     entry_time=entry_time, boundary=boundary,
                     entry_mode="market_on_acting", use_bidask=True, slippage=SLIPPAGE)
    r = res.get("r")
    status = res.get("path_status")
    note = res.get("exit_kind")
    if r is None and status == R.OPEN_AT_BOUNDARY:
        # no-TP (or unreached) survivor -> exit mark-to-market at the horizon (real P&L)
        r = res.get("detail_mark_to_boundary_r")
        note = "marked_to_horizon"
    return {"status": status, "r": r, "exit": note, "fill": str(fill),
            "n_targets": len(good)}


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    delay = int(sys.argv[1]) if len(sys.argv) > 1 else 0

    arch = BA._ro_conn()
    gold = BA.load_gold(arch)
    # clean limit-zone provider-R values (the +0.28 set)
    clean_known = []
    for s in gold:
        is_b, _ = G.classify(s)
        if not is_b and s["r_is_known"] and BA._f(s["calculated_r"]) is not None:
            clean_known.append(s)
    clean_R = [float(s["calculated_r"]) for s in clean_known]
    gold_times = sorted(_parse_dt(s["sent_at_utc"]) for s in gold if s["sent_at_utc"])
    arch.close()

    rev = sqlite3.connect(f"file:{REVISIONS_DB}?mode=ro", uri=True)
    rev.row_factory = sqlite3.Row
    mcs = load_recovered(rev)
    rev.close()

    priced, no_price = [], []
    for mc in mcs:
        p = price_one(mc, gold_times, delay)
        p["mc"] = mc
        (priced if p["r"] is not None else no_price).append(p)

    mc_R = [float(p["r"]) for p in priced]
    wins = sum(1 for r in mc_R if r > 1e-9)
    losses = sum(1 for r in mc_R if r < -1e-9)
    be = sum(1 for r in mc_R if abs(r) <= 1e-9)

    def stats(xs):
        return (len(xs), round(statistics.mean(xs), 4), round(statistics.median(xs), 4)) if xs else (0, None, None)

    cn, cmean, cmed = stats(clean_R)
    mn, mmean, mmed = stats(mc_R)
    allin = clean_R + mc_R
    an, amean, amed = stats(allin)

    print("=" * 96)
    print("  GOLD EDGE — CLEAN LIMIT-ZONE vs ALL-IN (incl. recovered market-calls)")
    print("=" * 96)
    print(f"  market-call entries recovered+priced (delay={delay}s, slippage=${SLIPPAGE}/side, "
          f"pip=$0.10):")
    print(f"    priced: {len(priced)}   unpriceable: {len(no_price)} "
          f"({', '.join(sorted(set(p['status'] for p in no_price))) or '-'})")
    print(f"    WINS: {wins}   LOSSES: {losses}   breakeven: {be}")
    print("  " + "-" * 92)
    print("  TWO NUMBERS, SIDE BY SIDE  (mean is outlier-sensitive; median robust)")
    print(f"    CLEAN limit-zone (provider R)     : n={cn:3d}  mean={cmean}  median={cmed}")
    print(f"    market-calls only (shadow exec R) : n={mn:3d}  mean={mmean}  median={mmed}")
    print(f"    ALL-IN (limit-zone + market-calls): n={an:3d}  mean={amean}  median={amed}")
    print(f"    -> market-calls move the mean by {round((amean or 0)-(cmean or 0),4)} "
          f"and the median by {round((amed or 0)-(cmed or 0),4)}")
    print("    (limit-zone leg = provider-reported R; market-call leg = realistic shadow fill)")
    print("  " + "-" * 92)
    # win/loss detail of recovered market-calls
    print("  RECOVERED MARKET-CALLS — per trade (R, outcome):")
    for p in sorted(priced, key=lambda x: float(x["r"])):
        mc = p["mc"]
        print(f"    {mc['sent_at_utc'][:16]} {mc['direction']:5} sl={mc['stop']} "
              f"R={float(p['r']):+.3f} [{p.get('exit')}]  {(mc['raw_text'] or '')[:60].split('Whale')[-1].strip()}")
    # by-month all-in
    print("  " + "-" * 92)
    print("  ALL-IN BY MONTH:")
    from collections import defaultdict
    bymonth = defaultdict(list)
    for s in clean_known:
        bymonth[str(s["sent_at_utc"])[:7]].append(float(s["calculated_r"]))
    for p in priced:
        bymonth[p["mc"]["sent_at_utc"][:7]].append(float(p["r"]))
    posm = 0
    for m in sorted(bymonth):
        xs = bymonth[m]
        mu = statistics.mean(xs)
        posm += 1 if mu > 0 else 0
        print(f"    {m}: n={len(xs):2d}  mean={mu:+.3f}R")
    print(f"    -> positive in {posm}/{len(bymonth)} months")
    # top / worst all-in contributors
    allrows = ([("limit", float(s['calculated_r']), s['sent_at_utc'][:10], s['direction']) for s in clean_known]
               + [("mcall", float(p['r']), p['mc']['sent_at_utc'][:10], p['mc']['direction']) for p in priced])
    allrows.sort(key=lambda x: x[1], reverse=True)
    print("  " + "-" * 92)
    print("  ALL-IN top 5 / worst 5:")
    for kind, r, d, dr in allrows[:5]:
        print(f"    +{r:.3f}R  {d} {dr:5} ({kind})")
    for kind, r, d, dr in allrows[-5:][::-1]:
        print(f"    {r:+.3f}R  {d} {dr:5} ({kind})")
    print("=" * 96)
    print(f"  VERDICT: clean limit-zone {cmean}R mean / {cmed}R median  →  ALL-IN "
          f"{amean}R mean / {amed}R median  (n {cn}→{an}).")
    print("  Realistic market fill, losses included; scorer unchanged; archive/signed-off/LIVE untouched.")
    print("=" * 96)


if __name__ == "__main__":
    main()
