"""BASELINE CHAMPION/CHALLENGER HARNESS v0.1 — BUILT, NOT FIT (RESEARCH-ONLY).

Plumbing only: model adapters (interfaces + deterministic stubs), grouped chronological + walk-forward
splits, a metric contract, and a DISABLED promotion state. No real model is fitted; challengers raise
if fitting is attempted without an authorization token (never supplied). Enforces the feature/label
leakage boundary and training-eligibility filters.
"""
from __future__ import annotations

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

SCHEMA = json.load(open(os.path.join(HERE, "dataset_schema_v0_1.json"), encoding="utf-8"))
FIELD_CLASS = SCHEMA["fields"]
LABEL_FIELDS = {k for k, v in FIELD_CLASS.items() if v == "POST_DECISION_LABEL"}
FEATURE_ALLOWLIST = {k for k, v in FIELD_CLASS.items() if v in ("DECISION_TIME_FEATURE",)}
MIN_SAMPLE = 10                              # below this -> INSUFFICIENT_SAMPLE (not project law)


class FittingNotAuthorised(Exception):
    pass


class LeakageError(Exception):
    pass


# ---- feature/label boundary -------------------------------------------------------------------
def build_feature_matrix(rows):
    """Extract ONLY decision-time features. Hard-rejects any post-decision label used as a feature."""
    X = []
    for r in rows:
        feat = {}
        for k, v in r.items():
            if k in LABEL_FIELDS:
                continue                     # labels never become features
            if FIELD_CLASS.get(k) == "DECISION_TIME_FEATURE":
                feat[k] = v
        X.append(feat)
    return X


def assert_no_label_features(feature_keys):
    bad = [k for k in feature_keys if k in LABEL_FIELDS]
    if bad:
        raise LeakageError(f"post-decision label(s) used as features: {bad}")


# ---- model adapters (interfaces + deterministic stubs; NO fitting) ----------------------------
class _Adapter:
    name = "ABSTRACT"
    is_baseline = False

    def fit(self, X, y, authorization_token=None):
        if not authorization_token:
            raise FittingNotAuthorised(f"{self.name}: fitting requires explicit future authorization (not supplied)")
        raise FittingNotAuthorised(f"{self.name}: model fitting is DISABLED in v0.1 regardless of token")

    def predict(self, X):
        raise NotImplementedError


class DocumentaryFixedPriorityBaseline(_Adapter):
    name = "DOCUMENTARY_FIXED_PRIORITY_BASELINE"
    is_baseline = True

    def predict(self, X):
        # deterministic documentary rule (NOT fitted): predict "activate" if a structural trigger is present
        return [1 if str(f.get("structural_trigger_state")) not in ("UNKNOWN", "None", "") else 0 for f in X]


class NoTradeBaseline(_Adapter):
    name = "NO_TRADE_BASELINE"
    is_baseline = True

    def predict(self, X):
        return [0 for _ in X]                # always no-trade


class LogisticRegressionChallenger(_Adapter):
    name = "LOGISTIC_REGRESSION_CHALLENGER"

    def predict(self, X):                    # UNFITTED stub -> deterministic constant (plumbing only)
        return [0 for _ in X]


class RegularisedLinearChallenger(LogisticRegressionChallenger):
    name = "REGULARISED_LINEAR_CHALLENGER"


class ShallowTreeChallenger(LogisticRegressionChallenger):
    name = "SHALLOW_TREE_OR_GBM_CHALLENGER"


ADAPTERS = [DocumentaryFixedPriorityBaseline, NoTradeBaseline, LogisticRegressionChallenger,
            RegularisedLinearChallenger, ShallowTreeChallenger]


# ---- splits: grouped by campaign, chronological, walk-forward ---------------------------------
def _eligible(rows, phase):
    key = "eligible_for_training" if phase == "train" else "eligible_for_validation"
    return [r for r in rows if r.get(key)]


def grouped_chronological_folds(rows, n_folds=3):
    """Walk-forward expanding train window with NO campaign overlap across splits. Rows ordered by
    decision_ts; grouped by campaign_id (a campaign lands wholly in one position)."""
    # order campaigns chronologically by their earliest decision_ts
    by_campaign = {}
    for r in rows:
        by_campaign.setdefault(r["campaign_id"], []).append(r)
    order = sorted(by_campaign, key=lambda c: min(int(x["decision_ts"]) for x in by_campaign[c]))
    if len(order) < 2:
        return {"status": "INSUFFICIENT_SAMPLE", "campaigns": len(order), "folds": []}
    folds = []
    cut = max(1, len(order) // (n_folds + 1))
    for k in range(1, n_folds + 1):
        tr_campaigns = order[: cut * k]
        ev_campaigns = order[cut * k: cut * (k + 1)]
        if not ev_campaigns:
            break
        overlap = set(tr_campaigns) & set(ev_campaigns)
        if overlap:
            raise LeakageError(f"campaign overlap across split: {overlap}")
        folds.append({"train_campaigns": tr_campaigns, "eval_campaigns": ev_campaigns})
    return {"status": "OK", "campaigns": len(order), "folds": folds}


# ---- metrics (with denominators + INSUFFICIENT_SAMPLE) ----------------------------------------
def metrics(y_true, y_pred, eligibility_filter="eligible_for_validation"):
    n = len(y_true)
    if n < MIN_SAMPLE:
        return {"status": "INSUFFICIENT_SAMPLE", "denominator": n, "min_required": MIN_SAMPLE,
                "eligibility_filter": eligibility_filter,
                "note": "sample too small for reliable statistics; no misleading numbers reported"}
    tp = sum(1 for t, p in zip(y_true, y_pred) if t == 1 and p == 1)
    fp = sum(1 for t, p in zip(y_true, y_pred) if t == 0 and p == 1)
    fn = sum(1 for t, p in zip(y_true, y_pred) if t == 1 and p == 0)
    tn = sum(1 for t, p in zip(y_true, y_pred) if t == 0 and p == 0)
    rec = tp / (tp + fn) if (tp + fn) else None
    prec = tp / (tp + fp) if (tp + fp) else None
    fpr = fp / (fp + tn) if (fp + tn) else None
    brier = sum((p - t) ** 2 for t, p in zip(y_true, y_pred)) / n
    return {"status": "OK", "denominator": n, "eligibility_filter": eligibility_filter,
            "candidate_recall": rec, "precision": prec, "false_positive_rate": fpr,
            "brier_score": brier, "no_trade_accuracy": (tn / (fp + tn)) if (fp + tn) else None,
            "confusion": {"tp": tp, "fp": fp, "fn": fn, "tn": tn},
            "research_price_disclaimer": "TRADINGVIEW_PRICE_SEMANTICS_UNVERIFIED / BROKER_EXECUTION_EQUIVALENCE_UNPROVEN"}


# ---- champion/challenger comparison (promotion DISABLED) ---------------------------------------
def compare(champion_metrics, challenger_metrics, dataset_hash):
    return {"champion": champion_metrics, "challenger": challenger_metrics,
            "dataset_hash": dataset_hash, "promotion_state": "SHADOW_ONLY / DISABLED",
            "automatic_promotion": False, "live_model_mutation": False,
            "rollback_metadata": {"note": "no promotion executed; versions + dataset hash retained"},
            "decision": "NO_PROMOTION (harness built, not fit; authorization + gate required)"}


MODEL_FITTING = "NOT_PERFORMED"
MODEL_PROMOTION = "DISABLED"
