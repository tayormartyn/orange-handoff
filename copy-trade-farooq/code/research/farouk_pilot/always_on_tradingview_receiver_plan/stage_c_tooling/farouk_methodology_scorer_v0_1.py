"""FAROUK METHODOLOGY SCORER v0.1 — OFFLINE / OBSERVATION-ONLY SCAFFOLD.

A methodology-aware scoring layer above the classifier / shadow detector / outcome
matcher. It scores how well a shadow candidate aligns with Farouk's DOCUMENTED
methodology (confluence coverage), and emits ONLY the six allowed observation labels.

NON-NEGOTIABLE (enforced by construction):
  * Output labels are limited to: REJECT, CONTEXT_ONLY, WATCH, SHADOW_CANDIDATE_LOW,
    SHADOW_CANDIDATE_MEDIUM, METHODOLOGY_ALIGNED_SHADOW. NONE means trade-ready.
    There is NO buy/sell/enter/execute/size/order/broker concept anywhere.
  * methodology_score is a 0..1 confluence-coverage fraction — descriptive, NOT a
    probability of profit and NOT a signal.
  * candidate_only=true; execution_allowed / broker_execution_allowed / qst_allowed /
    order_intent / risk_sizing_allowed are hard-wired False.
  * `null` context = "not available from our pipeline" -> listed in missing_evidence,
    never counted as satisfied. Grades are literal-only (never inferred).
  * Runs offline over provided dicts. No I/O: no network, no broker/cTrader/QST import.

This module changes nothing about NOT_INTEGRATION_READY.
"""

SCORER_VERSION = "farouk_methodology_scorer_v0_1"

ALLOWED_LABELS = [
    "REJECT", "CONTEXT_ONLY", "WATCH",
    "SHADOW_CANDIDATE_LOW", "SHADOW_CANDIDATE_MEDIUM", "METHODOLOGY_ALIGNED_SHADOW",
]

# Documented-methodology factors and their confluence weights (sum = 1.0).
# Weights reflect the corpus emphasis (structure/liquidity/confluence heavy); they are
# a coverage weighting, NOT a profit model. See FAROUK_METHODOLOGY_FACTOR_MAP_v0_1.md.
FACTOR_WEIGHTS = {
    "session_context": 0.10,
    "liquidity_sweep": 0.12,
    "market_structure": 0.15,   # CHoCH / BOS
    "displacement": 0.12,
    "order_block": 0.10,
    "fvg": 0.10,
    "bpr": 0.08,
    "grade": 0.08,              # A+ / A+++ (literal)
    "direction_alignment": 0.10,
    "outcome_support": 0.05,
}

# Context factors that must be POSITIVELY present to claim strong alignment. If any is
# missing (null), the label is capped at SHADOW_CANDIDATE_MEDIUM — we never claim
# alignment on absent evidence.
REQUIRED_CONTEXT = ["session_context", "displacement", "fvg", "order_block"]

_LONG_TYPES = {"SWEEP_LOW", "CHOCH_UP", "BULLISH_ENGULFING", "A_LONG", "A_PLUS"}
_SHORT_TYPES = {"SWEEP_HIGH", "CHOCH_DOWN", "BEARISH_ENGULFING", "A_SHORT"}


def _bias(et):
    if et in _LONG_TYPES:
        return "LONG"
    if et in _SHORT_TYPES:
        return "SHORT"
    return "NEUTRAL"


def _safe_flags():
    return {
        "candidate_only": True,
        "execution_allowed": False,
        "broker_execution_allowed": False,
        "qst_allowed": False,
        "order_intent": False,
        "risk_sizing_allowed": False,
    }


def score_candidate(candidate, sequence=None, outcome_stats=None, context=None):
    """Score one shadow candidate against documented Farouk methodology factors.

    candidate: dict with at least candidate_type, direction_hint (optional).
    sequence: list of {event_type, direction} (classified). Falls back to
        candidate['events_in_sequence'] if not given.
    outcome_stats: optional dict with 'outcome_label' (FAVOURABLE/MIXED/UNFAVOURABLE/...).
    context: optional education-derived fields (session_context, displacement, fvg,
        order_block, telegram_confirmation, alert_grade). Missing/None -> missing_evidence.
    Returns a dict; never authorises action.
    """
    context = dict(context or {})
    seq = sequence if sequence is not None else candidate.get("events_in_sequence", []) or []
    etypes = [e.get("event_type") for e in seq]
    ctype = candidate.get("candidate_type")
    hint = candidate.get("direction_hint")

    positive, negative, missing, disq = [], [], [], []
    satisfied_weight = 0.0

    def add_pos(factor):
        nonlocal satisfied_weight
        positive.append(factor)
        satisfied_weight += FACTOR_WEIGHTS[factor]

    # ---- hard disqualifiers ----
    biases = {_bias(t) for t in etypes if _bias(t) != "NEUTRAL"}
    if "LONG" in biases and "SHORT" in biases:
        disq.append("contradictory direction within sequence")
    if ctype == "CONTRADICTORY_CLUSTER":
        disq.append("contradictory/noisy cluster")
    for f in (context.get("contradiction_flags") or []):
        disq.append(str(f))

    # ---- lone primitive / noise ----
    directional = [t for t in etypes if _bias(t) != "NEUTRAL"]
    lone = len([t for t in etypes if t]) <= 1

    # ---- factor evaluation (from sequence) ----
    if any(t in ("SWEEP_LOW", "SWEEP_HIGH") for t in etypes):
        add_pos("liquidity_sweep")
    if any(t in ("CHOCH_UP", "CHOCH_DOWN", "BOS") for t in etypes):
        add_pos("market_structure")
    if any(t in ("BPR_FORMED", "BPR_TAPPED") for t in etypes):
        add_pos("bpr")

    # grade: literal only — from context.alert_grade or a graded event type
    grade = context.get("alert_grade")
    if grade in ("A+", "A+++") or any(t in ("A_PLUS", "A_TRIPLE_PLUS") for t in etypes):
        add_pos("grade")
    elif grade in (None,) and not any(t in ("A_PLUS", "A_TRIPLE_PLUS") for t in etypes):
        missing.append("grade (A+/A+++ not present; ungraded)")

    # direction alignment: all directional events share one bias (and no contradiction)
    if directional and len(biases) == 1:
        add_pos("direction_alignment")
    elif directional and len(biases) > 1:
        negative.append("direction not aligned across sequence")

    # ---- context factors (from optional education-derived fields) ----
    def ctx_factor(key, truthy_desc):
        v = context.get(key)
        if v is None:
            missing.append(f"{key} (not available from pipeline)")
        elif v:  # truthy / present
            add_pos(key)
        else:
            negative.append(f"{key} checked but absent")

    ctx_factor("session_context", "session")
    ctx_factor("displacement", "displacement")
    ctx_factor("fvg", "FVG")
    ctx_factor("order_block", "order block")

    # telegram confirmation (not a weighted factor here, but tracked)
    tg = context.get("telegram_confirmation")
    if tg is None:
        missing.append("telegram_confirmation (not cross-checked)")
    elif not tg:
        negative.append("telegram confirmation absent")

    # ---- outcome support ----
    label = (outcome_stats or {}).get("outcome_label")
    favourable = False
    if label == "FAVOURABLE":
        add_pos("outcome_support")
        favourable = True
    elif label == "MIXED":
        satisfied_weight += FACTOR_WEIGHTS["outcome_support"] * 0.5
        positive.append("outcome_support (partial: MIXED)")
    elif label in ("UNFAVOURABLE",):
        negative.append("outcome unfavourable")
    elif label is None:
        missing.append("outcome_stats (not yet outcome-matched)")

    methodology_score = round(min(satisfied_weight, 1.0), 4)

    # ---- label assignment (rubric) ----
    if disq:
        score_label = "REJECT"
    elif lone or not directional:
        score_label = "CONTEXT_ONLY"
    else:
        if methodology_score < 0.20:
            score_label = "WATCH"
        elif methodology_score < 0.45:
            score_label = "SHADOW_CANDIDATE_LOW"
        elif methodology_score < 0.70:
            score_label = "SHADOW_CANDIDATE_MEDIUM"
        else:
            score_label = "METHODOLOGY_ALIGNED_SHADOW"

        # ---- ceiling caps: never claim more than the evidence supports ----
        if any(context.get(k) is None for k in REQUIRED_CONTEXT):
            # required context missing -> cap at MEDIUM
            if score_label == "METHODOLOGY_ALIGNED_SHADOW":
                score_label = "SHADOW_CANDIDATE_MEDIUM"
        if not favourable:
            # no favourable outcome observation -> cap at LOW
            for cap in ("METHODOLOGY_ALIGNED_SHADOW", "SHADOW_CANDIDATE_MEDIUM"):
                if score_label == cap:
                    score_label = "SHADOW_CANDIDATE_LOW"

    assert score_label in ALLOWED_LABELS  # cannot emit anything else

    rec = {
        "scorer_version": SCORER_VERSION,
        "candidate_id": candidate.get("candidate_id"),
        "candidate_type": ctype,
        "direction_hint": hint,
        "methodology_score": methodology_score,
        "score_label": score_label,
        "positive_factors": positive,
        "negative_factors": negative,
        "missing_evidence": missing,
        "disqualifiers": disq,
    }
    rec.update(_safe_flags())
    return rec


if __name__ == "__main__":
    import json
    import sys
    data = json.load(open(sys.argv[1], encoding="utf-8"))
    cands = data["candidates"] if isinstance(data, dict) else data
    print(json.dumps([score_candidate(c) for c in cands], indent=2))
