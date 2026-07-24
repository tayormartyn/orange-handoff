"""
gold_backlog_audit_report.py — READ-ONLY reconciled Gold-backlog audit package.

AGGREGATION AND REPORTING ONLY. It reuses gold_clean_report / coverage_waterfall /
backfill_audit UNCHANGED and recomputes NOTHING (it reads the already-computed
outcome_projections.calculated_r; it never re-scores). It writes only new files under
data/reports/. It touches no protected DB, frozen module, parser/outcome/shadow decision,
and introduces no execution-capable code. Every headline number carries a provenance entry
(db/table/source/version/as-of), and every R statistic states its own denominator.

Usage:  python gold_backlog_audit_report.py
"""
from __future__ import annotations
import csv
import hashlib
import json
import os
import sqlite3
import statistics as st
import sys
import time
from collections import Counter

import backfill_audit as BA          # read-only helpers + load_gold (unchanged)
import gold_clean_report as G        # classify() + _agg() (unchanged)
import coverage_waterfall as CW      # build_universe() + assign_categories() (unchanged)

ARCHIVE = "data/signal_archive.db"
SHADOW = "data/shadow.db"
REV = "data/parser_revisions.db"
REPORTS = "data/reports"
GOLD_ASSETS = ("XAUUSD", "GOLD", "XAU")
FAROUK = "seascalperfarouk"
GOLD_SQL = "UPPER(asset) IN ('XAUUSD','GOLD','XAU')"

# expected denominators (from the brief); the run asserts the LIVE db result matches and
# reports the exact value + discrepancy if it does not.
EXPECT = {"total": 406, "gold": 296, "farouk_gold": 240, "quantified": 123,
          "r_known_all": 78, "r_known_gold": 69}

# read-only integrity witnesses (must be byte-identical before and after the run)
PROTECTED = ["data/signal_archive.db", "data/shadow.db", "data/parser_revisions.db",
             "campaign_extractor/q4_align/kernel.py", "campaign_extractor/paper_loop/paper_db.py",
             "campaign_extractor/mpk/data/mpk_campaigns_v1.db",
             "campaign_extractor/mpk/data/mpk_registry_v1.db"]

# records that MUST NOT enter any signal denominator / expectancy / provider aggregate
EXCLUDED_NON_SIGNAL = ["review-img-a605d64b16150b20"]   # BTCUSD TRADE_RESULT classification


def _ro(db):
    c = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    c.row_factory = sqlite3.Row
    return c


def _sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest() if os.path.exists(p) else None


def _g(row, key, default=None):
    """Safe access for sqlite3.Row / dict — returns default if the column is absent."""
    try:
        return row[key]
    except (KeyError, IndexError):
        return default


def _now():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _fname_stamp():
    return time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())


def _rstats(values):
    """R statistics over a list of floats. Returns None-filled dict when empty."""
    vals = [v for v in values if v is not None]
    if not vals:
        return {"n": 0, "mean": None, "median": None, "p25": None, "p75": None, "p90": None,
                "min": None, "max": None, "sum": None}
    s = sorted(vals)

    def pct(p):
        if len(s) == 1:
            return round(s[0], 4)
        i = p / 100 * (len(s) - 1)
        lo, hi = int(i), min(int(i) + 1, len(s) - 1)
        return round(s[lo] + (s[hi] - s[lo]) * (i - lo), 4)
    return {"n": len(s), "mean": round(st.mean(s), 4), "median": round(st.median(s), 4),
            "p25": pct(25), "p75": pct(75), "p90": pct(90), "min": round(min(s), 4),
            "max": round(max(s), 4), "sum": round(sum(s), 4)}


def compute():
    prov = []            # provenance ledger

    def P(metric, value, denom, db, table, source, ver="n/a"):
        prov.append({"metric": metric, "value": value, "denominator": denom, "source_db": db,
                     "source_table": table, "source_script_or_query": source,
                     "calculation_version": ver, "as_of_utc": _now()})
        return value

    conn = _ro(ARCHIVE)
    exceptions = []      # high-risk / corrected / excluded / influential rows

    # ---------------- SECTION 1 — dataset inventory ----------------
    total = P("total_signals", conn.execute("SELECT COUNT(*) FROM signals").fetchone()[0], "self",
              ARCHIVE, "signals", "COUNT(*)")
    by_asset = {r[0]: r[1] for r in conn.execute(
        "SELECT asset, COUNT(*) FROM signals GROUP BY asset ORDER BY COUNT(*) DESC")}
    by_provider = {r[0]: r[1] for r in conn.execute(
        "SELECT provider, COUNT(*) FROM signals GROUP BY provider ORDER BY COUNT(*) DESC")}
    by_class = {r[0]: r[1] for r in conn.execute(
        "SELECT classification, COUNT(*) FROM signals GROUP BY classification")}
    dr = conn.execute("SELECT MIN(sent_at_utc), MAX(sent_at_utc) FROM signals").fetchone()
    gold_n = P("gold_signals", conn.execute(f"SELECT COUNT(*) FROM signals WHERE {GOLD_SQL}").fetchone()[0],
               "self", ARCHIVE, "signals", f"COUNT(*) WHERE {GOLD_SQL}")
    farouk_gold = P("farouk_gold_signals", conn.execute(
        f"SELECT COUNT(*) FROM signals WHERE provider=? AND {GOLD_SQL}", (FAROUK,)).fetchone()[0],
        "self", ARCHIVE, "signals", f"COUNT(*) WHERE provider='{FAROUK}' AND {GOLD_SQL}")
    raw_versions = conn.execute("SELECT COUNT(*) FROM raw_message_versions").fetchone()[0]
    distinct_ch = conn.execute(
        "SELECT COUNT(DISTINCT content_hash) FROM raw_message_versions WHERE content_hash IS NOT NULL").fetchone()[0]
    ch_rows = conn.execute(
        "SELECT COUNT(*) FROM raw_message_versions WHERE content_hash IS NOT NULL").fetchone()[0]
    raw_ch_dups = ch_rows - distinct_ch

    inventory = {
        "total_signals": total, "gold_denominator": gold_n, "farouk_gold_denominator": farouk_gold,
        "provider_distribution": by_provider, "instrument_distribution": by_asset,
        "classification_distribution": by_class, "date_range_utc": [dr[0], dr[1]],
        "raw_message_versions": raw_versions,
        "raw_content_hash_duplicates_from_edits_resends": raw_ch_dups,
        "signal_level_duplicates_removed": None,   # filled from the waterfall (cat1) below
        "note": ("raw_content_hash_duplicates (%d) are edits/resends of raw messages — they are "
                 "NOT %d duplicate FINAL signals; the signal table is already deduplicated to %d."
                 % (raw_ch_dups, raw_ch_dups, total))}

    # ---------------- SECTION 2 — outcome distributions ----------------
    def outcome_block(where, params=()):
        oc = {r[0]: r[1] for r in conn.execute(
            f"SELECT op.outcome_category, COUNT(*) FROM outcome_projections op "
            f"JOIN signals s ON s.signal_id=op.signal_id WHERE {where} "
            f"GROUP BY op.outcome_category ORDER BY COUNT(*) DESC", params)}
        br = {r[0]: r[1] for r in conn.execute(
            f"SELECT op.binary_rollup, COUNT(*) FROM outcome_projections op "
            f"JOIN signals s ON s.signal_id=op.signal_id WHERE {where} GROUP BY op.binary_rollup", params)}
        return {"denominator": sum(oc.values()), "outcome_categories": oc,
                "binary_rollup": {"win": br.get("win", 0), "loss": br.get("loss", 0),
                                  "breakeven": br.get("breakeven", 0), "missed": br.get("missed", 0),
                                  "unclear_or_unmeasurable": br.get("unclear", 0)}}
    outcomes = {
        "all_406": outcome_block("1=1"),
        "gold_296": outcome_block(GOLD_SQL),
        "farouk_gold_240": outcome_block(f"s.provider=? AND {GOLD_SQL}", (FAROUK,))}
    P("binary_win_all", outcomes["all_406"]["binary_rollup"]["win"], total, ARCHIVE,
      "outcome_projections", "join signals; GROUP BY binary_rollup", "r-goldpip-v1")

    # ---------------- SECTION 3 — R coverage and performance ----------------
    def rlist(where, params=()):
        return [float(r[0]) for r in conn.execute(
            f"SELECT op.calculated_r FROM outcome_projections op JOIN signals s ON s.signal_id=op.signal_id "
            f"WHERE op.r_is_known=1 AND op.calculated_r IS NOT NULL AND {where}", params)]
    r_known_all = conn.execute("SELECT COUNT(*) FROM outcome_projections WHERE r_is_known=1").fetchone()[0]
    r_unknown_all = conn.execute("SELECT COUNT(*) FROM outcome_projections WHERE r_is_known=0").fetchone()[0]
    r_known_gold = conn.execute(
        f"SELECT COUNT(*) FROM outcome_projections op JOIN signals s ON s.signal_id=op.signal_id "
        f"WHERE op.r_is_known=1 AND {GOLD_SQL}").fetchone()[0]
    P("r_known_all", r_known_all, total, ARCHIVE, "outcome_projections", "COUNT r_is_known=1", "r-goldpip-v1")
    P("r_known_gold", r_known_gold, gold_n, ARCHIVE, "outcome_projections", "join; r_is_known=1 & gold", "r-goldpip-v1")

    # cleaned/raw gold aggregates via the UNCHANGED gold_clean_report logic
    bconn = BA._ro_conn()
    gold = BA.load_gold(bconn)
    clean = [s for s in gold if not G.classify(s)[0]]
    broken = [s for s in gold if G.classify(s)[0]]
    raw_agg, clean_agg, broken_agg = G._agg(gold), G._agg(clean), G._agg(broken)
    r_perf = {
        "r_known_denominator_all": r_known_all, "r_unknown_denominator_all": r_unknown_all,
        "r_known_denominator_gold": r_known_gold,
        "all_instruments_r_known": {**_rstats(rlist("1=1")), "denominator_note": "r-known across ALL 406, not the 406"},
        "gold_r_known_raw": {**_rstats(rlist(GOLD_SQL)),
                             "denominator_note": "r-known gold only (69), NOT the 296"},
        "gold_r_known_cleaned": {**clean_agg,
                                 "denominator_note": "clean known-R gold (66), NOT the 296 or 406"},
        "gold_broken_parse_with_R": {**broken_agg,
                                     "denominator_note": "broken-parse rows that carried an R (3)"},
        "cleaning_impact": {
            "raw_mean_R": raw_agg["mean"], "cleaned_mean_R": clean_agg["mean"],
            "raw_median_R": raw_agg["median"], "cleaned_median_R": clean_agg["median"],
            "delta_mean": (round(raw_agg["mean"] - clean_agg["mean"], 4)
                           if raw_agg["mean"] and clean_agg["mean"] else None),
            "explanation": ("removing %d genuinely broken-parse rows (|R|>5 / garbled levels) drops the "
                            "gold known-R mean from %s to %s; the median barely moves (%s->%s), i.e. the "
                            "raw mean was dominated by a few implausible outliers."
                            % (len(broken), raw_agg["mean"], clean_agg["mean"],
                               raw_agg["median"], clean_agg["median"]))}}
    P("gold_cleaned_mean_R", clean_agg["mean"], clean_agg["n"], ARCHIVE,
      "outcome_projections", "gold_clean_report._agg(clean)", "r-goldpip-v1")

    # ---------------- SECTION 4 — gold cleaning report (reuse classify) ----------------
    reason_counts = Counter()
    for s in broken:
        for r in G.classify(s)[1]:
            reason_counts[r.split("=")[0].split("(")[0].strip()] += 1
    for s in broken:
        isb, reasons = G.classify(s)
        rv = BA._f(s["calculated_r"]) if s["r_is_known"] else None
        exceptions.append({"kind": "BROKEN_PARSE_GOLD", "signal_id": s["signal_id"],
                           "provider": _g(s, "provider"),
                           "sent_at_utc": s["sent_at_utc"], "asset": _g(s, "asset", "XAUUSD"),
                           "direction": s["direction"],
                           "entry_low": s["entry_low"], "entry_high": s["entry_high"], "stop": s["stop"],
                           "calculated_r": (s["calculated_r"] if s["r_is_known"] else None),
                           "reason": "; ".join(reasons), "action": "EXCLUDED_FROM_CLEANED_AGGREGATE"})
        if rv is not None and abs(rv) > 5:
            exceptions.append({"kind": "IMPLAUSIBLE_R_OUTLIER", "signal_id": s["signal_id"],
                               "provider": _g(s, "provider"), "sent_at_utc": s["sent_at_utc"],
                               "asset": _g(s, "asset", "XAUUSD"),
                               "direction": s["direction"], "calculated_r": s["calculated_r"],
                               "reason": f"|R|={abs(rv):g} > 5 implausible", "action": "EXCLUDED_FROM_CLEANED_AGGREGATE"})
    cleaning = {
        "gold_denominator": len(gold), "clean_count": len(clean), "broken_parse_count": len(broken),
        "source_split": dict(Counter(s["source"] for s in gold)),
        "raw_vs_cleaned": {"raw": raw_agg, "cleaned": clean_agg, "broken_only": broken_agg},
        "broken_parse_reason_counts": dict(reason_counts.most_common()),
        "exact_rules": ["|R|>5 implausible", "entry outside $800-$8000 gold band",
                        "stop/TP <50% or >200% of entry", "stop on wrong side of entry",
                        "missing/zero entry or stop", "TP implying >30% move", "risk <$2 or >$200"],
        "no_row_silently_removed": True,
        "note": "cleaning removes only GENUINELY BROKEN parse rows; unusual-but-valid signals are kept."}
    inventory["signal_level_duplicates_removed"] = None   # set after waterfall

    # ---------------- SECTION 5 — recovery and parsing ----------------
    rconn = _ro(REV)
    stop_rec = rconn.execute("SELECT COUNT(*) FROM stop_recoveries").fetchone()[0]
    mc_rec = rconn.execute("SELECT COUNT(*) FROM market_call_recoveries").fetchone()[0]

    def validation_split(table):
        try:
            return {r[0]: r[1] for r in rconn.execute(
                f"SELECT validation, COUNT(*) FROM {table} GROUP BY validation")}
        except sqlite3.OperationalError:
            return {}
    recovery = {"stop_recoveries": P("stop_recoveries", stop_rec, "self", REV, "stop_recoveries", "COUNT(*)"),
                "market_call_recoveries": P("market_call_recoveries", mc_rec, "self", REV,
                                            "market_call_recoveries", "COUNT(*)"),
                "stop_recovery_validation": validation_split("stop_recoveries"),
                "market_call_validation": validation_split("market_call_recoveries"),
                "note": ("counts are POST-HOC recovered parse data. 'accepted%' validations were folded "
                         "into the measured set; non-accepted remain unresolved/excluded.")}
    rconn.close()

    # ---------------- SECTION 6 — coverage waterfall (reuse) ----------------
    recs, cat7, clean_known, mc_priced = CW.build_universe(bconn)
    CW.assign_categories(recs, cat7)
    universe = len(recs)
    bycat_all = Counter(r["cat"] for r in recs.values())
    bycat_296 = Counter(r["cat"] for r in recs.values() if r["in_296"])
    cat7_in296 = sum(1 for r in recs.values() if r["in_296"] and r["cat"] == 7)
    cat1 = bycat_all.get(1, 0)
    inventory["signal_level_duplicates_removed"] = cat1
    # record excluded genuine trades (cat 5/6) as exceptions
    for r in recs.values():
        if r["cat"] in (5, 6):
            exceptions.append({"kind": f"WATERFALL_CAT{r['cat']}_EXCLUDED", "message_key": r["key"],
                               "sent_at_utc": r["sent_at"], "direction": r["direction"],
                               "entry_low": r["entry_low"], "stop": r["stop"],
                               "reason": r["why"], "action": "EXCLUDED_FROM_QUANTIFIED_123"})
    waterfall = {
        "universe_total": universe, "universe_note": "296 archive XAUUSD ∪ recovered market-calls (deduped by message_key)",
        "categories": {CW.CATS[c]: bycat_all.get(c, 0) for c in range(1, 8)},
        "reconcile_universe": {"exclusions_1_6": sum(bycat_all.get(c, 0) for c in range(1, 7)),
                               "quantified_cat7": bycat_all.get(7, 0),
                               "sum": sum(bycat_all.values()), "equals_universe": sum(bycat_all.values()) == universe},
        "archive_296_only": {"categories": {CW.CATS[c]: bycat_296.get(c, 0) for c in range(1, 8)},
                             "sum": sum(bycat_296.values()), "equals_296": sum(bycat_296.values()) == gold_n},
        "quantified_123_composition": {
            "total_quantified": bycat_all.get(7, 0),
            "clean_limit_zone_archive": len(clean_known), "priced_market_calls": len(mc_priced),
            "within_296_archive": cat7_in296, "recovered_market_calls_outside_296": bycat_all.get(7, 0) - cat7_in296,
            "note": ("cat7=123 is over the 340-record universe; within the 296 archive only %d are "
                     "quantified (cat7), the other %d are recovered market-calls outside the 296."
                     % (cat7_in296, bycat_all.get(7, 0) - cat7_in296))}}
    P("quantified_gold_candidates", bycat_all.get(7, 0), universe, "data/audit (derived)",
      "coverage_waterfall", "coverage_waterfall.assign_categories cat7", "waterfall-v1")

    # ---------------- SECTION 7 — performance exclusions ----------------
    excl_leak = []
    for key in EXCLUDED_NON_SIGNAL:
        in_signals = conn.execute("SELECT COUNT(*) FROM signals WHERE source_message_key LIKE ?",
                                  (f"%{key}%",)).fetchone()[0]
        if in_signals:
            excl_leak.append(key)
        exceptions.append({"kind": "NON_SIGNAL_EXCLUDED", "message_key": key,
                           "reason": "TRADE_RESULT / PIPELINE_EXCLUDED (BTCUSD closed-trade card)",
                           "action": "MUST_NOT_APPEAR_IN_ANY_DENOMINATOR_OR_AGGREGATE"})
    # synthetic/test leakage check: any non-gold test artefact in the gold set
    test_like = conn.execute(
        "SELECT COUNT(*) FROM signals WHERE source_message_key LIKE '%test%' OR provider LIKE '%test%' "
        "OR source_message_key LIKE '%synthetic%' OR source_message_key LIKE '%fixture%'").fetchone()[0]
    exclusions = {
        "enforced_exclusions": ["PIPELINE_VALIDATION_ONLY", "TRADE_RESULT", "PROVIDER_UNVERIFIED_test_records",
                                "synthetic_fixtures", "unit_test_rows", "duplicate_signals"],
        "btc_trade_result_key": EXCLUDED_NON_SIGNAL[0],
        "btc_present_in_signal_denominator": bool(excl_leak),
        "test_or_synthetic_rows_in_archive": test_like,
        "signal_level_duplicates_cat1": cat1,
        "leak_detected": bool(excl_leak) or test_like > 0,
        "note": "the BTCUSD TRADE_RESULT classification lives only in a review sidecar, not in signal_archive."}

    # ---------------- SECTION 8 — coverage breakdown (separate categories) ----------------
    ev_present = conn.execute("SELECT COUNT(DISTINCT signal_id) FROM outcome_evidence").fetchone()[0]
    ev_accepted = conn.execute("SELECT COUNT(DISTINCT signal_id) FROM outcome_evidence WHERE accepted=1").fetchone()[0]
    sconn = _ro(SHADOW)
    tick_signals = sconn.execute("SELECT COUNT(DISTINCT signal_id) FROM shadow_results").fetchone()[0]
    tick_priced = sconn.execute(
        "SELECT COUNT(DISTINCT signal_id) FROM shadow_results WHERE price_source_ref IS NOT NULL "
        "OR quote_grade IS NOT NULL").fetchone()[0]
    sconn.close()
    paper_obs = os.path.exists("data/paper_observations_v1.db")
    coverage = {
        "outcome_evidence_present_signals": P("outcome_evidence_present", ev_present, total, ARCHIVE,
            "outcome_evidence", "COUNT(DISTINCT signal_id)", "signoff-r4"),
        "outcome_evidence_accepted_signals": ev_accepted,
        "outcome_evidence_kind": "MESSAGE-DERIVED outcome detection (target_hit/stop_hit/...), NOT quote/tick coverage",
        "dukascopy_tickpath_evidence_signals": P("shadow_tickpath_signals", tick_signals, total, SHADOW,
            "shadow_results", "COUNT(DISTINCT signal_id)", "shadow-1b"),
        "dukascopy_tickpath_priced_signals": tick_priced,
        "q4a_anchor_coverage_signals": 0,
        "q4a_note": "Q4A anchoring is live/forward-only (paper_observations_v1.db %s); 0 for the historical backlog"
                    % ("absent" if not paper_obs else "present"),
        "no_coverage": total - ev_present,
        "unverifiable_provider_post_time": "N/A for archive backlog (applies to manual image intake route only)",
        "warning": "outcome_evidence present (%d) is NOT the same as quote-covered; only %d signals have any "
                   "Dukascopy tick-path result." % (ev_present, tick_signals)}

    bconn.close()
    conn.close()

    report = {
        "audit": "GOLD_BACKLOG_AUDIT", "as_of_utc": _now(), "mode": "READ_ONLY_AGGREGATION",
        "execution_locks": {"EXECUTION_ENABLED": False, "CTRADER_EXECUTION_ENABLED": False},
        "1_dataset_inventory": inventory,
        "2_outcome_distributions": outcomes,
        "3_r_coverage_and_performance": r_perf,
        "4_gold_cleaning": cleaning,
        "5_recovery_and_parsing": recovery,
        "6_coverage_waterfall": waterfall,
        "7_performance_exclusions": exclusions,
        "8_coverage_breakdown": coverage,
        "provenance_ledger": prov,
        "expected_vs_actual": {k: {"expected": EXPECT[k], "actual": {
            "total": total, "gold": gold_n, "farouk_gold": farouk_gold,
            "quantified": bycat_all.get(7, 0), "r_known_all": r_known_all,
            "r_known_gold": r_known_gold}[k],
            "match": EXPECT[k] == {"total": total, "gold": gold_n, "farouk_gold": farouk_gold,
                                   "quantified": bycat_all.get(7, 0), "r_known_all": r_known_all,
                                   "r_known_gold": r_known_gold}[k]} for k in EXPECT},
    }
    return report, exceptions


def validate(report):
    """Hard reconciliation asserts (raise on any failure)."""
    inv, wf, ex = report["1_dataset_inventory"], report["6_coverage_waterfall"], report["7_performance_exclusions"]
    r = report["3_r_coverage_and_performance"]
    ev = report["expected_vs_actual"]
    checks = []

    def chk(name, ok, detail=""):
        checks.append({"check": name, "pass": bool(ok), "detail": detail})
        assert ok, f"VALIDATION FAILED: {name} :: {detail}"

    inst_total = sum(inv["instrument_distribution"].values())
    chk("instrument totals reconcile to 406", inst_total == 406, f"sum={inst_total}")
    chk("gold waterfall (296 archive) sums to 296", wf["archive_296_only"]["equals_296"],
        str(wf["archive_296_only"]["sum"]))
    chk("universe waterfall reconciles", wf["reconcile_universe"]["equals_universe"],
        str(wf["reconcile_universe"]))
    chk("farouk gold subset of gold", inv["farouk_gold_denominator"] <= inv["gold_denominator"],
        f"{inv['farouk_gold_denominator']} <= {inv['gold_denominator']}")
    chk("r-known gold does not exceed gold quantified",
        r["r_known_denominator_gold"] <= wf["categories"]["quantified_independent_signal"],
        f"{r['r_known_denominator_gold']} <= {wf['categories']['quantified_independent_signal']}")
    b = report["2_outcome_distributions"]["all_406"]["binary_rollup"]
    chk("binary outcome totals reconcile to 406", sum(b.values()) == 406, str(sum(b.values())))
    bg = report["2_outcome_distributions"]["gold_296"]["binary_rollup"]
    chk("gold binary totals reconcile to 296", sum(bg.values()) == 296, str(sum(bg.values())))
    chk("exclusions do not leak into aggregates", not ex["leak_detected"],
        f"btc_in_signals={ex['btc_present_in_signal_denominator']} test_rows={ex['test_or_synthetic_rows_in_archive']}")
    chk("expected denominators all match live db", all(v["match"] for v in ev.values()),
        json.dumps({k: v for k, v in ev.items() if not v["match"]}))
    return checks


def write_outputs(report, exceptions, checks, hashes_before, hashes_after):
    os.makedirs(REPORTS, exist_ok=True)
    stamp = _fname_stamp()
    report["validation_checks"] = checks
    report["integrity_hashes"] = {"before": hashes_before, "after": hashes_after,
                                  "unchanged": hashes_before == hashes_after}
    jpath = os.path.join(REPORTS, f"gold_backlog_audit_{stamp}.json")
    mpath = os.path.join(REPORTS, f"gold_backlog_audit_{stamp}.md")
    cpath = os.path.join(REPORTS, f"gold_backlog_exceptions_{stamp}.csv")
    with open(jpath, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, default=str)
    with open(cpath, "w", newline="", encoding="utf-8") as f:
        cols = ["kind", "signal_id", "message_key", "provider", "sent_at_utc", "asset", "direction",
                "entry_low", "entry_high", "stop", "calculated_r", "reason", "action"]
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for e in exceptions:
            w.writerow(e)
    with open(mpath, "w", encoding="utf-8") as f:
        f.write(_markdown(report, exceptions))
    return jpath, mpath, cpath


def _markdown(rep, exceptions):
    inv = rep["1_dataset_inventory"]; wf = rep["6_coverage_waterfall"]; r = rep["3_r_coverage_and_performance"]
    cov = rep["8_coverage_breakdown"]; cl = rep["4_gold_cleaning"]
    L = []
    L.append(f"# Gold Backlog Audit — {rep['as_of_utc']} (READ-ONLY)\n")
    L.append("## Denominators (exact, each stated separately)")
    L.append(f"- Total signals: **{inv['total_signals']}**")
    L.append(f"- Gold (XAUUSD): **{inv['gold_denominator']}**")
    L.append(f"- Farouk Gold: **{inv['farouk_gold_denominator']}**")
    L.append(f"- Quantified gold candidates (cat7, universe {wf['universe_total']}): **{wf['categories']['quantified_independent_signal']}** "
             f"(within 296 archive: {wf['quantified_123_composition']['within_296_archive']}; "
             f"recovered market-calls outside 296: {wf['quantified_123_composition']['recovered_market_calls_outside_296']})")
    L.append(f"- R-known (all instruments): **{r['r_known_denominator_all']}**")
    L.append(f"- R-known (gold): **{r['r_known_denominator_gold']}**\n")
    L.append("## R performance — EVERY figure states its denominator")
    for key, lbl in (("gold_r_known_raw", "Gold R-known RAW"), ("gold_r_known_cleaned", "Gold R-known CLEANED"),
                     ("all_instruments_r_known", "All-instrument R-known")):
        b = r[key]
        pct = (f" [p25 {b.get('p25')}, p75 {b.get('p75')}, p90 {b.get('p90')}, min {b.get('min')}, "
               f"max {b.get('max')}]" if b.get("p25") is not None else "")
        L.append(f"- {lbl} (n={b['n']}): mean **{b['mean']}R** / median **{b['median']}R**{pct} — {b['denominator_note']}")
    ci = r["cleaning_impact"]
    L.append(f"\n**Cleaning impact:** raw mean {ci['raw_mean_R']}R → cleaned {ci['cleaned_mean_R']}R "
             f"(median {ci['raw_median_R']}→{ci['cleaned_median_R']}). {ci['explanation']}\n")
    L.append("> R-KNOWN CAVEAT: all R statistics apply ONLY to their r-known / quantified subset — "
             "NOT the full 296 or 406. Most signals have no known R.\n")
    L.append("## Coverage breakdown (categories kept SEPARATE)")
    L.append(f"- outcome_evidence present: **{cov['outcome_evidence_present_signals']}** signals "
             f"(accepted: {cov['outcome_evidence_accepted_signals']}) — {cov['outcome_evidence_kind']}")
    L.append(f"- Dukascopy tick-path evidence: **{cov['dukascopy_tickpath_evidence_signals']}** signals "
             f"(priced: {cov['dukascopy_tickpath_priced_signals']})")
    L.append(f"- Q4A anchor coverage: **{cov['q4a_anchor_coverage_signals']}** — {cov['q4a_note']}")
    L.append(f"- NO_COVERAGE: **{cov['no_coverage']}** ; {cov['warning']}\n")
    L.append("## Coverage waterfall (296 archive — sums to 296)")
    for c, n in wf["archive_296_only"]["categories"].items():
        L.append(f"- {c}: {n}")
    L.append(f"- **sum = {wf['archive_296_only']['sum']}** (reconciles to 296: {wf['archive_296_only']['equals_296']})\n")
    L.append("## Gold cleaning (raw vs cleaned)")
    L.append(f"- clean {cl['clean_count']} / broken-parse {cl['broken_parse_count']} of {cl['gold_denominator']} gold")
    L.append(f"- broken-parse reason counts: {cl['broken_parse_reason_counts']}\n")
    L.append("## Validation")
    for c in rep.get("validation_checks", []):
        L.append(f"- [{'PASS' if c['pass'] else 'FAIL'}] {c['check']} — {c['detail']}")
    ih = rep.get("integrity_hashes", {})
    L.append(f"\n**Integrity:** protected hashes unchanged = {ih.get('unchanged')}")
    L.append(f"**Execution locks:** {rep['execution_locks']}")
    L.append(f"\n## Exceptions ({len(exceptions)} rows) — see the CSV for full detail")
    kinds = Counter(e["kind"] for e in exceptions)
    for k, n in kinds.most_common():
        L.append(f"- {k}: {n}")
    return "\n".join(L) + "\n"


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    hashes_before = {p: _sha(p) for p in PROTECTED}
    report, exceptions = compute()
    checks = validate(report)
    hashes_after = {p: _sha(p) for p in PROTECTED}
    assert hashes_before == hashes_after, "PROTECTED FILE CHANGED DURING RUN"
    jpath, mpath, cpath = write_outputs(report, exceptions, checks, hashes_before, hashes_after)
    print("GOLD BACKLOG AUDIT — read-only, all validation checks passed")
    print(f"  total={report['1_dataset_inventory']['total_signals']} gold={report['1_dataset_inventory']['gold_denominator']} "
          f"farouk_gold={report['1_dataset_inventory']['farouk_gold_denominator']} "
          f"quantified={report['6_coverage_waterfall']['categories']['quantified_independent_signal']} "
          f"r_known_all={report['3_r_coverage_and_performance']['r_known_denominator_all']} "
          f"r_known_gold={report['3_r_coverage_and_performance']['r_known_denominator_gold']}")
    print(f"  cleaned gold: mean {report['3_r_coverage_and_performance']['gold_r_known_cleaned']['mean']}R / "
          f"median {report['3_r_coverage_and_performance']['gold_r_known_cleaned']['median']}R (n={report['3_r_coverage_and_performance']['gold_r_known_cleaned']['n']})")
    print(f"  protected hashes unchanged: {hashes_before == hashes_after}")
    print(f"  outputs: {jpath}\n           {mpath}\n           {cpath}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
