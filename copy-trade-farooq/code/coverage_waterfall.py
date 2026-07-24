"""
coverage_waterfall.py — READ-ONLY coverage waterfall for ALL gold candidate records.

Accounts for every distinct gold candidate record and where it went, with MUTUALLY
EXCLUSIVE terminal categories assigned by a fixed PRIORITY ORDER (first match wins),
so the arithmetic reconciles EXACTLY:

    total candidates = (exclusions cat 1..6) + (quantified cat 7 = 123)

Universe = the 296 archive XAUUSD signals  ∪  the recovered market-call entries
(deduped by message_key). cat 7 (quantified) = the 123 that actually carry an R in
the edge measurement: 66 clean limit-zone (provider R) + 57 priced market-calls
(shadow R). Every other record gets the first matching exclusion 1..6.

For excluded GENUINE trades (cat 5 & 6) we classify each by its outcome HINT —
loss-leaning / win-leaning / breakeven-neutral / contradictory / NO-USABLE-HINT —
so we can detect honestly whether the excluded set skews toward LOSSES (which would
mean +0.17R is still flattered). "We cannot tell" is its own category (no-usable-
hint); it is NEVER called neutral.

Advisory only. No scores changed. Archive + signed-off 28 + LIVE stub untouched.
Outputs data/audit/coverage_waterfall.csv (every record -> its one category).

Usage: python coverage_waterfall.py
"""

import csv
import os
import re
import sqlite3
import sys
from collections import Counter, defaultdict
from datetime import timedelta

import backfill_audit as BA
import gold_clean_report as G

REVISIONS_DB = "data/parser_revisions.db"
OUT_CSV = "data/audit/coverage_waterfall.csv"
GOLD_BAND = (800.0, 8000.0)
REENTRY_MIN = 90

CATS = {
    1: "duplicate",
    2: "non_independent_layer_or_reentry",
    3: "false_signal_or_commentary",
    4: "invalid_or_garbled_parse",
    5: "genuine_trade_potentially_recoverable",
    6: "genuine_trade_no_admissible_outcome",
    7: "quantified_independent_signal",
}

LOSS_RE = re.compile(r"\b(stopped out|hit (?:our |the )?sl|hit (?:our |the )?stop|"
                     r"stop ?loss hit|took? the loss|took? a loss|full loss|"
                     r"-\s?\d+\s?pips|cut .{0,15}loss|closed .{0,15}loss|loss on)\b", re.I)
WIN_RE = re.compile(r"\b(tp\s*\d?\s*(?:hit|done|secured)|all ?tps? hit|target hit|"
                    r"\+\s?\d+\s?pips|take tp|tp 1|profit secured|hit full tp|in profit)\b", re.I)
BE_RE = re.compile(r"\b(break\s?even|\bbe\b|sl to entry|scratch|closed at entry)\b", re.I)

# Channels that are commentary/macro/other-asset, NOT gold trade calls — a "signal"
# parsed from one of these is a false signal regardless of a gold-plausible number.
NONTRADE_CHANNEL_RE = re.compile(
    r"Wall-Street-Sailor|Daily-Candle|economic-edge|quant-flow", re.I)


def _ro_rev():
    c = sqlite3.connect(f"file:{REVISIONS_DB}?mode=ro", uri=True)
    c.row_factory = sqlite3.Row
    return c


def build_universe(conn):
    gold = BA.load_gold(conn)                       # 296 archive XAUUSD signals
    rev = _ro_rev()
    mc = {r["message_key"]: dict(r) for r in rev.execute(
        "SELECT message_key, sent_at_utc, direction, stop, validation FROM "
        "market_call_recoveries WHERE validation LIKE 'accepted%'")}
    rev.close()

    # cat 7 keys
    clean_known, mc_priced = set(), set()
    for s in gold:
        if not G.classify(s)[0] and s["r_is_known"] and BA._f(s["calculated_r"]) is not None:
            clean_known.add(s["source_message_key"])
    for k, r in mc.items():
        if r["stop"]:
            mc_priced.add(k)
    cat7 = clean_known | mc_priced

    # unified records by message_key
    recs = {}
    for s in gold:
        recs[s["source_message_key"]] = {
            "key": s["source_message_key"], "sent_at": s["sent_at_utc"], "in_296": True,
            "direction": (s["direction"] or "").upper(), "entry_low": s["entry_low"],
            "entry_high": s["entry_high"], "stop": s["stop"],
            "tps": [s["tp1"], s["tp2"], s["tp3"]], "category": s["outcome_category"],
            "r_is_known": bool(s["r_is_known"]), "calculated_r": s["calculated_r"],
            "binary": s["binary_rollup"], "is_mc": s["source_message_key"] in mc,
        }
    for k, r in mc.items():
        if k in recs:
            recs[k]["is_mc"] = True
            recs[k]["mc_dir"] = r["direction"]
            recs[k]["mc_stop"] = r["stop"]
        else:
            recs[k] = {"key": k, "sent_at": r["sent_at_utc"], "in_296": False,
                       "direction": (r["direction"] or "").upper(), "entry_low": "",
                       "entry_high": "", "stop": r["stop"], "tps": [], "category": None,
                       "r_is_known": False, "calculated_r": None, "binary": None, "is_mc": True}
    # attach raw text
    for k, r in recs.items():
        row = conn.execute("SELECT raw_text FROM raw_message_versions WHERE message_key=? "
                           "ORDER BY version_number DESC LIMIT 1", (k,)).fetchone()
        r["raw"] = (row["raw_text"] if row else "") or ""
    return recs, cat7, clean_known, mc_priced


def _compat(r):
    """A dict shaped for gold_clean_report.classify()."""
    tps = (r.get("tps") or []) + [None, None, None]
    return {"entry_low": r["entry_low"], "entry_high": r["entry_high"], "stop": r["stop"],
            "tp1": tps[0], "tp2": tps[1], "tp3": tps[2], "direction": r["direction"],
            "calculated_r": r["calculated_r"], "r_is_known": r["r_is_known"]}


def _entry_mid(r):
    lo, hi = BA._f(r["entry_low"]), BA._f(r["entry_high"])
    if lo is not None and hi is not None:
        return (lo + hi) / 2
    return lo


def assign_categories(recs, cat7):
    keys_sorted = sorted(recs, key=lambda k: recs[k]["sent_at"] or "")
    # entry timestamps for re-entry detection (genuine entries only)
    from datetime import datetime, timezone
    def dt(s):
        for f in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
            try:
                return datetime.strptime(str(s).strip(), f).replace(tzinfo=timezone.utc)
            except ValueError:
                continue
        try:
            d = datetime.fromisoformat(str(s)); return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
        except Exception:
            return None
    for r in recs.values():
        r["_dt"] = dt(r["sent_at"])

    # duplicate detection: identical (dir, entry_low, entry_high, stop) with non-empty
    # levels appearing more than once within 48h -> later ones are duplicates.
    seen = {}
    dup_keys = set()
    for k in keys_sorted:
        r = recs[k]
        if not r["direction"]:
            continue
        sig = (r["direction"], r["entry_low"], r["entry_high"], r["stop"])
        if all(x not in (None, "") for x in (r["entry_low"], r["stop"])) and r["_dt"]:
            if sig in seen and r["_dt"] - seen[sig] <= timedelta(hours=48):
                dup_keys.add(k)
            else:
                seen[sig] = r["_dt"]

    # genuine-entry timeline for re-entry: a record that looks like a real entry
    def is_entry_like(r):
        return bool(r["direction"]) and (r["is_mc"] or (_entry_mid(r) and GOLD_BAND[0] <= _entry_mid(r) <= GOLD_BAND[1]))
    entry_times = sorted(r["_dt"] for r in recs.values() if is_entry_like(r) and r["_dt"])

    def prior_entry_within(r, mins):
        if not r["_dt"]:
            return False
        for t in entry_times:
            if t < r["_dt"] and (r["_dt"] - t) <= timedelta(minutes=mins):
                return True
        return False

    for k in keys_sorted:
        r = recs[k]
        em = _entry_mid(r)
        gold_entry = em is not None and GOLD_BAND[0] <= em <= GOLD_BAND[1]
        cat = r["category"] or ""
        broken, reasons = (G.classify(_compat(r)) if r["in_296"] else (True, []))
        # ---- priority order, first match wins ----
        if k in cat7:
            r["cat"] = 7; r["why"] = "in the 123 quantified edge set"
        elif k in dup_keys:
            r["cat"] = 1; r["why"] = "repeat of an identical earlier signal (<=48h)"
        elif is_entry_like(r) and prior_entry_within(r, REENTRY_MIN):
            r["cat"] = 2; r["why"] = f"another gold entry within {REENTRY_MIN}min before -> layer/re-entry"
        elif (cat in ("instruction_only", "missed", "unclear")) or \
             NONTRADE_CHANNEL_RE.search(r["raw"]) or \
             (not r["is_mc"] and em is not None and not gold_entry) or \
             (not r["direction"] and not r["is_mc"]):
            r["cat"] = 3
            r["why"] = ("instruction/commentary" if cat in ("instruction_only", "missed", "unclear")
                        else ("commentary/macro channel (not a gold trade call)"
                              if NONTRADE_CHANNEL_RE.search(r["raw"])
                              else f"non-gold/garbled entry ({r['entry_low']}-{r['entry_high']}) -> not a real gold trade"))
        elif gold_entry and any(x in " ".join(reasons).lower() for x in
                                ("malformed", "absurd", "implausible", "tiny risk", "huge risk")):
            r["cat"] = 4; r["why"] = "gold trade but garbled levels: " + "; ".join(reasons)[:80]
        elif (r["is_mc"] and not r["stop"]) or (gold_entry and (r["stop"] in (None, "") or BA._f(r["stop"]) in (None, 0))):
            r["cat"] = 5; r["why"] = "genuine gold trade missing a field (stop/entry) -> recoverable"
        elif r["is_mc"] or gold_entry:
            r["cat"] = 6; r["why"] = "genuine gold trade, structurally ok, but no admissible outcome (R unknown)"
        else:
            r["cat"] = 6; r["why"] = "no admissible outcome (fallback)"
    return recs


_LOSS_CATS = {"manual_loss", "original_stop_loss", "stop_loss", "net_loss"}
_WIN_CATS = {"target_hit", "managed_profit_confirmed", "profit_confirmed_r_unknown"}


def outcome_hint(conn, r):
    """Outcome hint for an excluded genuine trade (cat 5/6).

    PRIMARY (reliable): the signed-off detector already decided the outcome DIRECTION
    for archived records — `binary_rollup` (win/loss/breakeven) and `outcome_category`
    know win-vs-loss even when R is unquantifiable. Use them.
    FALLBACK (market-calls with no archive record): a NARROW same-thread scan; if it
    can't tell, that's `no_usable_hint` — never silently 'neutral'.
    """
    b = (r.get("binary") or "").lower()
    cat = (r.get("category") or "")
    if b == "loss" or cat in _LOSS_CATS:
        return "loss_leaning"
    if b == "win" or cat in _WIN_CATS:
        return "win_leaning"
    if b == "breakeven" or cat == "breakeven":
        return "breakeven_neutral"
    # market-call (not in archive) or genuinely undetermined -> narrow scan, else no-hint
    if not r["in_296"] and r.get("_dt"):
        hi = (r["_dt"] + timedelta(hours=18)).isoformat()
        rows = conn.execute(
            "SELECT raw_text FROM raw_message_versions WHERE sent_at_utc>=? AND sent_at_utc<=? "
            "AND raw_text LIKE '%gold-trades%' ORDER BY sent_at_utc", (r["sent_at"], hi)).fetchall()
        loss = any(LOSS_RE.search(x["raw_text"] or "") for x in rows)
        win = any(WIN_RE.search(x["raw_text"] or "") for x in rows)
        if loss and win:
            return "contradictory"
        if loss:
            return "loss_leaning"
        if win:
            return "win_leaning"
    return "no_usable_hint"


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    os.makedirs("data/audit", exist_ok=True)
    conn = BA._ro_conn()
    recs, cat7, clean_known, mc_priced = build_universe(conn)
    assign_categories(recs, cat7)

    # outcome hints for cat 5 & 6
    for r in recs.values():
        r["hint"] = outcome_hint(conn, r) if r["cat"] in (5, 6) else ""

    total = len(recs)
    bycat = Counter(r["cat"] for r in recs.values())
    print("=" * 92)
    print("  GOLD COVERAGE WATERFALL — every record -> exactly one terminal category")
    print("=" * 92)
    print(f"  UNIVERSE (distinct gold candidate records): {total}")
    print(f"  = 296 archive signals  ∪  {total-296} fully-missing market-calls")
    print("  " + "-" * 88)
    for c in range(1, 8):
        print(f"   cat {c}  {CATS[c]:38} {bycat.get(c,0):4d}")
    excl = sum(bycat.get(c, 0) for c in range(1, 7))
    print("  " + "-" * 88)
    print(f"  RECONCILE: exclusions(1-6)={excl}  +  quantified(cat7)={bycat.get(7,0)}  =  {excl+bycat.get(7,0)}")
    print(f"             universe total = {total}   ->  {'EXACT ✓' if excl+bycat.get(7,0)==total else 'MISMATCH ✗'}")
    print(f"             cat7 == 123 ?  {bycat.get(7,0)} ({'yes' if bycat.get(7,0)==123 else 'NO'})")

    # by month
    print("  " + "-" * 88)
    print("  EXCLUSIONS BY MONTH (cat 1-6):")
    bm = defaultdict(Counter)
    for r in recs.values():
        if r["cat"] != 7:
            bm[(r["sent_at"] or "")[:7]][r["cat"]] += 1
    for m in sorted(bm):
        cc = bm[m]
        print(f"    {m}: total={sum(cc.values()):3d}  " + " ".join(f"c{c}={cc[c]}" for c in range(1,7) if cc[c]))

    # limit-zone vs market-call split of exclusions
    print("  " + "-" * 88)
    lz = Counter(r["cat"] for r in recs.values() if r["cat"] != 7 and not r["is_mc"])
    mcx = Counter(r["cat"] for r in recs.values() if r["cat"] != 7 and r["is_mc"])
    print("  EXCLUSIONS — limit-zone style:", dict(sorted(lz.items())))
    print("  EXCLUSIONS — market-call style:", dict(sorted(mcx.items())))

    # cat5 vs cat6 + outcome-hint distribution (the honest check)
    print("  " + "-" * 88)
    cat5 = [r for r in recs.values() if r["cat"] == 5]
    cat6 = [r for r in recs.values() if r["cat"] == 6]
    print(f"  GENUINE EXCLUDED TRADES: cat5 (potentially recoverable)={len(cat5)}  "
          f"cat6 (no admissible outcome)={len(cat6)}")
    hints = Counter(r["hint"] for r in (cat5 + cat6))
    print("  OUTCOME-HINT DISTRIBUTION (cat 5 & 6) — 'we cannot tell' = no_usable_hint, NOT neutral:")
    for h in ("loss_leaning", "win_leaning", "breakeven_neutral", "contradictory", "no_usable_hint"):
        print(f"    {h:20} {hints.get(h,0)}")
    ll, wl = hints.get("loss_leaning", 0), hints.get("win_leaning", 0)
    usable = ll + wl + hints.get("breakeven_neutral", 0) + hints.get("contradictory", 0)
    print(f"    -> of {ll+wl} directional hints: loss-leaning {ll} vs win-leaning {wl}")

    # examples per category
    print("  " + "-" * 88)
    print("  EXAMPLES (one per category):")
    for c in range(1, 7):
        ex = next((r for r in recs.values() if r["cat"] == c), None)
        if ex:
            print(f"   cat{c} {CATS[c]}:")
            print(f"     {(ex['sent_at'] or '')[:16]} {ex['direction']:5} "
                  f"e={ex['entry_low']}-{ex['entry_high']} sl={ex['stop']} | {ex['why'][:70]}")
            print(f"       raw: {ex['raw'][:90].replace(chr(10),' ').strip()}")

    # CSV: every record -> its one category
    with open(OUT_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["message_key", "sent_at", "in_296", "is_market_call", "direction",
                    "entry_low", "entry_high", "stop", "category_num", "category", "why",
                    "outcome_hint", "raw_excerpt"])
        for r in sorted(recs.values(), key=lambda x: (x["cat"], x["sent_at"] or "")):
            w.writerow([r["key"], r["sent_at"], r["in_296"], r["is_mc"], r["direction"],
                        r["entry_low"], r["entry_high"], r["stop"], r["cat"], CATS[r["cat"]],
                        r["why"], r["hint"], (r["raw"][:120].replace("\n", " ").strip())])
    conn.close()
    print("  " + "-" * 88)
    print(f"  Full per-record CSV: {OUT_CSV} ({total} rows)")
    # honest verdict
    print("=" * 92)
    if ll > wl * 1.5 and ll >= 3:
        print(f"  VERDICT: excluded genuine trades LEAN LOSS ({ll} loss vs {wl} win hints) — "
              f"+0.17R is likely STILL somewhat flattered.")
    elif wl >= ll:
        print(f"  VERDICT: excluded genuine trades do NOT lean loss ({ll} loss vs {wl} win hints) — "
              f"exclusions look benign; +0.17R holds.")
    else:
        print(f"  VERDICT: mild loss-lean ({ll} loss vs {wl} win) but small; see hint table + CSV.")
    print("  Advisory only; no scores changed; archive + signed-off 28 + LIVE stub untouched.")
    print("=" * 92)


if __name__ == "__main__":
    main()
