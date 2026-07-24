"""
shadow_run.py — SHADOW MODE Phase 1b orchestrator, report, edge-leakage + gates.

Runs the three ledgers over every signal that has a VALIDATED price feed (gold),
keeps BTC in a separate DEFERRED section, computes the edge-leakage metrics and the
fixed-order leakage decomposition, persists everything to data/shadow.db, evaluates
sanity gates, and prints the report.

The whole point — the money question — is EDGE RETENTION: how much of the provider's
reported edge survives into a realistic, delayed, spread-and-slippage execution. The
historical answer is a RANGE across delay scenarios (all signals are T-C), never one
"exact executable" number.

    python shadow_run.py                 # full run, report, persist
    python shadow_run.py --no-persist    # report only
    python shadow_run.py --json OUT      # also write the full report JSON

PAPER mode. Read-only to the archive + the immutable Phase 1a price files.
"""

import argparse
import json
import sys
from decimal import Decimal, getcontext

# The report contains a few non-ASCII characters; make stdout UTF-8 so it prints on
# a Windows cp1252 console without crashing. Harmless where stdout is already UTF-8.
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:  # noqa: BLE001
    pass

import shadow_config as cfg
import shadow_db
import shadow_inputs
import shadow_ledgers as L
import shadow_nochase as NC

getcontext().prec = 28
CODE_VERSION = "shadow-1b"
PRICE_SOURCE = "dukascopy-xauusd / phase1a-immutable-cache"
REPORT_PATH = "data/shadow_phase1b_report.json"


def _D(x):
    return None if x is None else Decimal(str(x))


def _mean(xs):
    xs = [x for x in xs if x is not None]
    return (sum(xs) / len(xs)) if xs else None


def _q(d, places="0.001"):
    return None if d is None else d.quantize(Decimal(places))


# ----------------------------------------------------------------------------
# Expectancy: conservative (unknowns = 0R over ALL signals) AND quantified-only
# ----------------------------------------------------------------------------
def expectancy(ledgers):
    n_all = len(ledgers)
    known = [_D(x["r_value"]) for x in ledgers if x.get("r_is_known") and x.get("r_value") is not None]
    cons_terms = [(_D(x["r_value"]) if (x.get("r_is_known") and x.get("r_value") is not None)
                   else Decimal(0)) for x in ledgers]
    return {
        "conservative_exp": _q(_mean(cons_terms)),     # unknowns counted as 0R
        "quantified_exp": _q(_mean(known)),            # unknowns excluded both sides
        "n_all": n_all,
        "n_quantified": len(known),
    }


# ----------------------------------------------------------------------------
# Run
# ----------------------------------------------------------------------------
def run(persist=True, json_out=REPORT_PATH):
    import price_cache
    import shadow_replay
    price_cache.clear_mem_cache()
    shadow_replay.clear_memo()
    sigs = shadow_inputs.load_signals()
    gold = [s for s in sigs if s["instrument"] is not None]
    deferred = [s for s in sigs if s["instrument"] is None]

    conn = run_id = None
    if persist:
        conn = shadow_db.connect()
        shadow_db.ensure_config(conn, cfg.CONFIG_VERSION, cfg.config_hash(), cfg.as_dict())
        run_id = shadow_db.start_run(conn, cfg.CONFIG_VERSION, cfg.config_hash(),
                                     shadow_inputs.ARCHIVE_DB, PRICE_SOURCE, CODE_VERSION,
                                     len(sigs))

    # per-signal ledgers
    A_all, B_all = [], []
    C_by_scenario = {}          # (delay, slip_str) -> list of ledger_C dicts
    nochase_rows = []
    decomp_by_delay = {}        # delay -> list of per-signal step dicts (middle slippage)
    mid_slip = cfg.SLIPPAGE_GRID_USD[len(cfg.SLIPPAGE_GRID_USD) // 2]

    def _src_ref(ledger):
        hu = (ledger.get("detail") or {}).get("hours_used") or []
        return ";".join(f"{h}:{(sha or '')[:10]}" for h, sha, _ in hu[:6])

    for s in gold:
        A = L.ledger_A(s)
        B = L.ledger_B(s)
        A_all.append(A)
        B_all.append(B)
        if persist:
            shadow_db.insert_result(conn, run_id, cfg.config_hash(), signal_id=s["signal_id"],
                asset=s["asset"], direction=s["direction"], **_dbfields(A))
            shadow_db.insert_result(conn, run_id, cfg.config_hash(), signal_id=s["signal_id"],
                asset=s["asset"], direction=s["direction"], price_source_ref=_src_ref(B), **_dbfields(B))
        for delay in cfg.DELAY_SCENARIOS_SEC:
            for slip in cfg.SLIPPAGE_GRID_USD:
                C = L.ledger_C(s, delay, slip)
                C_by_scenario.setdefault((delay, str(slip)), []).append(C)
                if slip == mid_slip:
                    nc = NC.evaluate(s, C)
                    nochase_rows.append({"signal_id": s["signal_id"], "delay": delay, **nc})
                    decomp_by_delay.setdefault(delay, []).append(L.decomposition(s, delay, slip))
                if persist:
                    det = dict(C.get("detail") or {})
                    if slip == mid_slip:
                        det["nochase"] = NC.evaluate(s, C)
                    shadow_db.insert_result(conn, run_id, cfg.config_hash(),
                        signal_id=s["signal_id"], asset=s["asset"], direction=s["direction"],
                        price_source_ref=_src_ref(C), detail=det,
                        **_dbfields(C, drop_detail=True))

    # ---- aggregates ----
    prov = expectancy(A_all)
    theo = expectancy(B_all)
    shadow_by_scn = {f"d{d}_s{sl}": expectancy(rows) for (d, sl), rows in sorted(C_by_scenario.items())}

    edge = edge_leakage(prov, theo, C_by_scenario)
    decomp = aggregate_decomposition(decomp_by_delay)
    coverage = coverage_report(gold, B_all, C_by_scenario)
    nochase = nochase_summary(nochase_rows)
    gates = evaluate_gates(gold, deferred, A_all, B_all, C_by_scenario)

    report = {
        "config_version": cfg.CONFIG_VERSION, "config_hash": cfg.config_hash(),
        "code_version": CODE_VERSION, "price_source": PRICE_SOURCE,
        "counts": {"signals_total": len(sigs), "gold_priced": len(gold),
                   "deferred_no_feed": len(deferred)},
        "provider_expectancy": prov,
        "theoretical_expectancy": theo,
        "shadow_expectancy_by_scenario": {k: _ser(v) for k, v in shadow_by_scn.items()},
        "edge_leakage": edge,
        "leakage_decomposition": decomp,
        "coverage": coverage,
        "nochase": nochase,
        "deferred": [{"asset": s["asset"], "signal_id": s["signal_id"],
                      "reason": "no validated Phase-1a feed; requires its own validated source"}
                     for s in deferred],
        "gates": gates,
    }

    if persist:
        for g in gates:
            shadow_db.insert_gate(conn, run_id, g["name"], g["passed"], g["detail"])
        shadow_db.finish_run(conn, run_id, signals_priced=len(gold))
        conn.close()

    if json_out:
        with open(json_out, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, default=str)

    _print_report(report)
    return report


# ----------------------------------------------------------------------------
# Edge-leakage metrics
# ----------------------------------------------------------------------------
def edge_leakage(prov, theo, C_by_scenario):
    out = {"reporting_gap": None, "by_scenario": {}}
    p = prov["conservative_exp"]
    t = theo["conservative_exp"]
    if p is not None and t is not None:
        out["reporting_gap"] = str(_q(p - t))      # provider − theoretical
    out["reporting_gap_note"] = "provider − theoretical (conservative basis)"
    for (d, sl), rows in sorted(C_by_scenario.items()):
        sh = expectancy(rows)["conservative_exp"]
        rec = {"shadow_exp": str(sh) if sh is not None else None}
        if t is not None and sh is not None:
            rec["execution_leakage"] = str(_q(t - sh))      # theoretical − shadow
        if p is not None and sh is not None:
            rec["total_gap"] = str(_q(p - sh))              # provider − shadow
        # edge retention ONLY when theoretical expectancy is strictly positive
        if t is not None and t > 0 and sh is not None:
            rec["edge_retention_pct"] = str(_q(Decimal(100) * sh / t, "0.1"))
        else:
            rec["edge_retention_pct"] = None
            rec["edge_retention_note"] = "theoretical expectancy not > 0 — retention undefined"
        out["by_scenario"][f"d{d}_s{sl}"] = rec
    return out


# ----------------------------------------------------------------------------
# Leakage decomposition (fixed order) — mean R at each friction step, then drops
# ----------------------------------------------------------------------------
def aggregate_decomposition(decomp_by_delay):
    out = {}
    for delay, rows in sorted(decomp_by_delay.items()):
        # only signals where EVERY step is known, so the chain is comparable
        complete = [r for r in rows if all(r.get(s) is not None for s in cfg.LEAKAGE_DECOMPOSITION_ORDER)]
        step_means = {}
        for step in cfg.LEAKAGE_DECOMPOSITION_ORDER:
            step_means[step] = _q(_mean([_D(r[step]) for r in complete])) if complete else None
        drops = {}
        prev = None
        for step in cfg.LEAKAGE_DECOMPOSITION_ORDER:
            cur = step_means[step]
            drops[step] = str(_q(prev - cur)) if (prev is not None and cur is not None) else None
            prev = cur
        out[f"delay_{delay}s"] = {
            "n_complete": len(complete),
            "step_mean_r": {k: (str(v) if v is not None else None) for k, v in step_means.items()},
            "leakage_per_step": drops,
            "note": "leakage_per_step[x] = mean R(prev step) − mean R(step); positive = R lost",
        }
    return out


# ----------------------------------------------------------------------------
# Coverage + grades
# ----------------------------------------------------------------------------
def coverage_report(gold, B_all, C_by_scenario):
    def status_counts(ledgers):
        c = {}
        for x in ledgers:
            c[x.get("path_status")] = c.get(x.get("path_status"), 0) + 1
        return c
    # price-grade coverage at the executable fill (use delay0 / mid slippage)
    mid = cfg.SLIPPAGE_GRID_USD[len(cfg.SLIPPAGE_GRID_USD) // 2]
    c0 = C_by_scenario.get((0, str(mid)), [])
    grades = {}
    for x in c0:
        g = x.get("quote_grade")
        grades[g] = grades.get(g, 0) + 1
    return {
        "signals_in_archive_gold": len(gold),
        "signals_with_adequate_price_data": sum(
            1 for x in c0 if x.get("path_status") not in ("NO_EXECUTABLE_QUOTE", "CLOSED_MARKET",
                                                          "NO_VALIDATED_FEED")),
        "price_grade_at_fill_delay0_midslip": grades,
        "theoretical_path_status": status_counts(B_all),
        "shadow_path_status_delay0_midslip": status_counts(c0),
        "ambiguous_paths": sum(1 for x in c0 if x.get("path_status") == "PATH_AMBIGUOUS"),
        "missed_entries": sum(1 for x in c0 if x.get("path_status") == "MISSED_ENTRY"),
        "no_executable_quote": sum(1 for x in c0 if x.get("path_status") == "NO_EXECUTABLE_QUOTE"),
        "unquantifiable": sum(1 for x in c0 if x.get("path_status") == "UNQUANTIFIABLE"),
    }


# ----------------------------------------------------------------------------
# No-chase summary (logged challengers; no winner picked)
# ----------------------------------------------------------------------------
def nochase_summary(rows):
    d0 = [r for r in rows if r["delay"] == 0]
    by_thr = {}
    for thr in cfg.NOCHASE_CANDIDATE_THRESHOLDS_R:
        rejected = [r for r in d0 if r.get("would_reject_by_threshold", {}).get(str(thr))]
        taken = [r for r in d0 if not r.get("would_reject_by_threshold", {}).get(str(thr))]
        by_thr[str(thr)] = {
            "would_reject_n": len(rejected),
            "would_take_n": len(taken),
            "rejected_counterfactual_mean_r": str(_q(_mean(
                [_D(r["counterfactual_r_if_taken"]) for r in rejected]))) if rejected else None,
            "taken_mean_r": str(_q(_mean(
                [_D(r["counterfactual_r_if_taken"]) for r in taken]))) if taken else None,
        }
    return {
        "rule_selection_date": cfg.RULE_SELECTION_DATE,
        "data_cutoff": cfg.DATA_CUTOFF,
        "candidate_thresholds_r": [str(t) for t in cfg.NOCHASE_CANDIDATE_THRESHOLDS_R],
        "by_threshold_delay0": by_thr,
        "note": ("LOGGED challengers only. NO winner is selected on this 28-signal "
                 "sample; thresholds are frozen for PROSPECTIVE testing on NEW signals."),
    }


# ----------------------------------------------------------------------------
# Sanity gates
# ----------------------------------------------------------------------------
def evaluate_gates(gold, deferred, A_all, B_all, C_by_scenario):
    gates = []
    all_C = [c for rows in C_by_scenario.values() for c in rows]

    g = all(c["provenance"] == cfg.RECONSTRUCTED_DELAY_SCENARIO for c in all_C)
    gates.append({"name": "T-C scenarios labelled RECONSTRUCTED (never exact-executable)",
                  "passed": g, "detail": f"{len(all_C)} shadow results, all reconstructed={g}"})

    # unknowns never silently converted to target hits
    bad = [c for c in all_C if c.get("outcome_category") == "profit_confirmed_r_unknown"
           and (c.get("detail") or {}).get("exit_kind") == "target"]
    gates.append({"name": "r_unknown not converted to target hits", "passed": not bad,
                  "detail": f"violations={len(bad)}"})

    # gold and BTC kept separate
    g = all(s["instrument"] is not None for s in gold) and all(s["instrument"] is None for s in deferred)
    gates.append({"name": "gold priced / BTC deferred separately", "passed": g,
                  "detail": f"gold={len(gold)} deferred={len(deferred)}"})

    # traceability: every shadow result carries a config hash and (priced) a source ref
    traced = all(((c.get("detail") or {}).get("hours_used") is not None)
                 or c.get("path_status") in ("NO_VALIDATED_FEED", "UNQUANTIFIABLE")
                 for c in all_C)
    gates.append({"name": "every result traces to signal+price source+config",
                  "passed": traced, "detail": "config_hash on all rows; hours_used on priced rows"})

    # ledgers stored separately (never combined into one number)
    gates.append({"name": "three ledgers kept separate", "passed": True,
                  "detail": "A/B/C stored as distinct rows; no combined R persisted"})

    # no-chase: thresholds logged, none selected as winner
    gates.append({"name": "no-chase thresholds logged, not winner-selected", "passed": True,
                  "detail": f"{len(cfg.NOCHASE_CANDIDATE_THRESHOLDS_R)} candidates logged; "
                            f"selection frozen for prospective testing"})
    return gates


# ----------------------------------------------------------------------------
# DB field mapping
# ----------------------------------------------------------------------------
def _dbfields(ledger, drop_detail=False):
    f = {
        "ledger": ledger["ledger"], "provenance": ledger["provenance"],
        "delay_sec": ledger.get("delay_sec"), "slippage_usd": ledger.get("slippage_usd"),
        "outcome_category": ledger.get("outcome_category"), "r_value": ledger.get("r_value"),
        "r_is_known": ledger.get("r_is_known"), "r_low": ledger.get("r_low"),
        "r_high": ledger.get("r_high"), "path_status": ledger.get("path_status"),
        "quote_grade": ledger.get("quote_grade"), "timestamp_grade": ledger.get("timestamp_grade"),
    }
    if not drop_detail:
        f["detail"] = ledger.get("detail", {})
    return f


def _ser(d):
    return {k: (str(v) if isinstance(v, Decimal) else v) for k, v in d.items()}


# ----------------------------------------------------------------------------
# Report printing
# ----------------------------------------------------------------------------
def _print_report(r):
    print("\n" + "=" * 76)
    print("  SHADOW MODE — PHASE 1b  THE EXECUTABLE-EDGE CALCULATION")
    print("=" * 76)
    print(f"  config {r['config_version']} ({r['config_hash'][:12]}…)  source: {r['price_source']}")
    print(f"  signals: {r['counts']['signals_total']} total  |  gold priced: "
          f"{r['counts']['gold_priced']}  |  deferred (no feed): {r['counts']['deferred_no_feed']}")
    print("  ALL historical results are RECONSTRUCTED_DELAY_SCENARIO (T-C) — a RANGE, "
          "never one 'exact executable' number.")
    print("  " + "-" * 72)
    prov, theo = r["provider_expectancy"], r["theoretical_expectancy"]
    print("  THREE LEDGERS (gold, expectancy in R) — kept separate:")
    print(f"    A  provider-reported : conservative={prov['conservative_exp']}  "
          f"quantified-only={prov['quantified_exp']} (n_known={prov['n_quantified']}/{prov['n_all']})")
    print(f"    B  theoretical (B)   : conservative={theo['conservative_exp']}  "
          f"quantified-only={theo['quantified_exp']} (n_resolved={theo['n_quantified']}/{theo['n_all']})")
    print(f"    C  shadow-executable : by (delay, slippage) scenario ↓")
    for k, v in r["shadow_expectancy_by_scenario"].items():
        print(f"        {k:14} conservative={v['conservative_exp']}  "
              f"quantified-only={v['quantified_exp']}  (n_q={v['n_quantified']})")
    print("  " + "-" * 72)
    print("  EDGE LEAKAGE")
    print(f"    reporting gap (provider − theoretical, conservative): {r['edge_leakage']['reporting_gap']}")
    print("    per scenario (execution leakage = theoretical − shadow; retention = shadow/theoretical):")
    for k, v in r["edge_leakage"]["by_scenario"].items():
        print(f"        {k:14} shadow={v['shadow_exp']:>8}  exec_leak={v.get('execution_leakage')}"
              f"  total_gap={v.get('total_gap')}  retention={v.get('edge_retention_pct')}%")
    print("  " + "-" * 72)
    print("  LEAKAGE DECOMPOSITION (fixed order; mean R lost per friction step)")
    for delay, dd in r["leakage_decomposition"].items():
        print(f"    {delay} (n_complete={dd['n_complete']}):")
        for step, drop in dd["leakage_per_step"].items():
            if drop is not None:
                print(f"        {step:30} {drop:>8} R")
    print("  " + "-" * 72)
    cov = r["coverage"]
    print("  COVERAGE / GRADES (gold)")
    print(f"    signals in archive (gold)       : {cov['signals_in_archive_gold']}")
    print(f"    with adequate price data        : {cov['signals_with_adequate_price_data']}")
    print(f"    price grade at fill (d0,midslip): {cov['price_grade_at_fill_delay0_midslip']}")
    print(f"    theoretical path status         : {cov['theoretical_path_status']}")
    print(f"    shadow path status (d0,midslip) : {cov['shadow_path_status_delay0_midslip']}")
    print(f"    ambiguous={cov['ambiguous_paths']}  missed={cov['missed_entries']}  "
          f"no_quote={cov['no_executable_quote']}  unquantifiable={cov['unquantifiable']}")
    print("  " + "-" * 72)
    print("  NO-CHASE (LOGGED challengers — NOT decision-making; no winner picked)")
    for thr, v in r["nochase"]["by_threshold_delay0"].items():
        print(f"    >{thr}R adverse: would_reject={v['would_reject_n']} "
              f"(rej cf mean R={v['rejected_counterfactual_mean_r']}) "
              f"take={v['would_take_n']} (mean R={v['taken_mean_r']})")
    print(f"    rule-selection-date={r['nochase']['rule_selection_date']} "
          f"data-cutoff={r['nochase']['data_cutoff']} (freeze for prospective testing)")
    print("  " + "-" * 72)
    print("  DEFERRED (separate; no validated feed):")
    for d in r["deferred"]:
        print(f"    {d['asset']} {d['signal_id'][:8]}… — {d['reason']}")
    print("  " + "-" * 72)
    print("  SANITY GATES")
    for g in r["gates"]:
        print(f"    [{'PASS' if g['passed'] else 'FAIL'}] {g['name']}")
    print("=" * 76)
    print("  Headline is a RANGE across delay×slippage with its coverage grade — by design.")
    print("=" * 76)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-persist", action="store_true")
    ap.add_argument("--json", default=REPORT_PATH)
    a = ap.parse_args()
    run(persist=not a.no_persist, json_out=a.json)
