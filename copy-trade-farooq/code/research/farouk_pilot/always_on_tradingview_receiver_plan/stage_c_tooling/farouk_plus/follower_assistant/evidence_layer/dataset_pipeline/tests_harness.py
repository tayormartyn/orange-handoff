"""Harness tests on clearly-SYNTHETIC toy data (RESEARCH-ONLY). Proves split integrity, adapter
interfaces, metric calc, reproducibility, leakage rejection, and that promotion/fitting stay disabled.
Synthetic results are NOT trading performance.
"""
from __future__ import annotations

import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import champion_challenger_harness as H                          # noqa: E402

PASS = 0
FAIL = 0


def ok(name, cond):
    global PASS, FAIL
    if cond:
        PASS += 1
    else:
        FAIL += 1
        print(f"FAIL: {name}")


def toy_rows(n=12):
    rows = []
    for i in range(n):
        rows.append({
            "campaign_id": f"TOY-{i:03d}", "decision_ts": 1_000_000 + i * 3600,
            "structural_trigger_state": "BREAK_OF_STRUCTURE" if i % 2 == 0 else "UNKNOWN",
            "session": "LONDON", "direction": "LONG",
            # a POST_DECISION_LABEL that MUST NOT become a feature:
            "mfe_pips": str(10 + i), "outcome_status": "COMPLETE", "activation_result": "ACTIVATED" if i % 2 == 0 else "NEVER_ACTIVATED",
            "eligible_for_training": True, "eligible_for_validation": True,
        })
    return rows


def test_feature_label_boundary():
    rows = toy_rows()
    X = H.build_feature_matrix(rows)
    ok("feature matrix excludes post-decision labels", all("mfe_pips" not in f and "outcome_status" not in f for f in X))
    ok("feature matrix keeps decision-time features", all("structural_trigger_state" in f for f in X))
    try:
        H.assert_no_label_features(["structural_trigger_state", "mfe_pips"])
        ok("leakage guard raises on label-as-feature", False)
    except H.LeakageError:
        ok("leakage guard raises on label-as-feature", True)


def test_grouped_chronological_splits():
    rows = toy_rows(12)
    res = H.grouped_chronological_folds(rows, n_folds=3)
    ok("splits produced", res["status"] == "OK" and len(res["folds"]) >= 1)
    for f in res["folds"]:
        overlap = set(f["train_campaigns"]) & set(f["eval_campaigns"])
        ok("no campaign overlap across a fold", not overlap)
    # chronological: train campaigns precede eval campaigns in time
    order_ok = all(max(f["train_campaigns"]) < min(f["eval_campaigns"]) for f in res["folds"])
    ok("walk-forward chronological ordering", order_ok)


def test_small_sample_guard():
    res = H.grouped_chronological_folds(toy_rows(1), n_folds=3)
    ok("single-campaign -> INSUFFICIENT_SAMPLE", res["status"] == "INSUFFICIENT_SAMPLE")
    m = H.metrics([1, 0, 1], [1, 0, 0])
    ok("tiny metric set -> INSUFFICIENT_SAMPLE", m["status"] == "INSUFFICIENT_SAMPLE" and m["denominator"] == 3)


def test_adapters_no_fit():
    rows = toy_rows()
    X = H.build_feature_matrix(rows)
    for A in H.ADAPTERS:
        a = A()
        preds = a.predict(X)
        ok(f"{a.name} predict deterministic (plumbing)", len(preds) == len(X))
        try:
            a.fit(X, [1] * len(X))                       # no token
            ok(f"{a.name} fit blocked", False)
        except H.FittingNotAuthorised:
            ok(f"{a.name} fit blocked without authorization", True)
        try:
            a.fit(X, [1] * len(X), authorization_token="ANYTOKEN")   # even WITH a token, disabled in v0.1
            ok(f"{a.name} fit disabled even with token", False)
        except H.FittingNotAuthorised:
            ok(f"{a.name} fit disabled even with token", True)


def test_metrics_and_reproducibility():
    yt = [1, 0, 1, 0, 1, 1, 0, 0, 1, 0, 1, 0]
    yp = [1, 0, 0, 0, 1, 1, 0, 1, 1, 0, 1, 0]
    m1 = H.metrics(yt, yp)
    m2 = H.metrics(yt, yp)
    ok("metrics reproducible", m1 == m2)
    ok("metric exposes denominator", m1["denominator"] == 12)
    ok("metric exposes eligibility filter", "eligibility_filter" in m1)
    ok("recall computed", m1["candidate_recall"] is not None)


def test_promotion_disabled():
    cmp = H.compare({"x": 1}, {"x": 2}, dataset_hash="abc")
    ok("promotion SHADOW/DISABLED", cmp["promotion_state"] == "SHADOW_ONLY / DISABLED")
    ok("no automatic promotion", cmp["automatic_promotion"] is False)
    ok("no live model mutation", cmp["live_model_mutation"] is False)
    ok("decision = NO_PROMOTION", cmp["decision"].startswith("NO_PROMOTION"))
    ok("module-level MODEL_FITTING NOT_PERFORMED", H.MODEL_FITTING == "NOT_PERFORMED")
    ok("module-level MODEL_PROMOTION DISABLED", H.MODEL_PROMOTION == "DISABLED")


if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    for fn in [test_feature_label_boundary, test_grouped_chronological_splits, test_small_sample_guard,
               test_adapters_no_fit, test_metrics_and_reproducibility, test_promotion_disabled]:
        fn()
    print(f"\n{PASS} passed, {FAIL} failed  (synthetic toy data — NOT trading performance)")
    sys.exit(1 if FAIL else 0)
