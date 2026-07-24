"""
shadow_nochase.py — SHADOW MODE Phase 1b, no-chase DIAGNOSTICS (measure, don't enforce).

We measure how much worse a follower's entry was than the conservative reference edge,
and we LOG candidate "don't chase past X adverse R" thresholds as challengers. We do
NOT pick a winning threshold from these 28 signals — that would be optimising on the
same sample the rule is meant to be tested on. Selection is frozen for PROSPECTIVE
testing on NEW signals only (rule-selection-date + data-cutoff are stamped).

Formulae (signed; direction = +1 long, -1 short):
  deterioration_R   = direction * (executable_entry - reference_entry) / reference_risk
                      (positive == worse fill; the gate uses adverse = max(0, det))
  reward_remaining  = direction*(tp1 - executable_entry) / direction*(tp1 - reference_entry)
                      (fraction of the TP1 reward still ahead of you after the worse entry)

A signal a candidate rule WOULD have rejected is still replayed in a COUNTERFACTUAL
ledger, so we can later see whether rejecting it would have helped or hurt.

PAPER mode, read-only.
"""

from decimal import Decimal

import shadow_config as cfg


def deterioration_r(direction_sign, executable_entry, reference_entry, reference_risk):
    """Signed entry deterioration in R. Positive = worse than the reference edge."""
    if reference_risk == 0:
        return None
    return (Decimal(direction_sign) * (Decimal(str(executable_entry)) -
            Decimal(str(reference_entry))) / Decimal(str(reference_risk)))


def adverse_r(det_r):
    """The gating quantity: only adverse (worse) deterioration counts."""
    if det_r is None:
        return None
    return max(Decimal("0"), det_r)


def reward_remaining_fraction(direction_sign, tp1, executable_entry, reference_entry):
    """Fraction of the TP1 reward still ahead after the (worse) executable entry.
    1.0 = full reward intact; <0 = price already past TP1 (no reward left)."""
    if tp1 is None:
        return None
    sign = Decimal(direction_sign)
    denom = sign * (Decimal(str(tp1)) - Decimal(str(reference_entry)))
    if denom == 0:
        return None
    numer = sign * (Decimal(str(tp1)) - Decimal(str(executable_entry)))
    return numer / denom


def evaluate(sig, ledger_c):
    """No-chase diagnostics for one signal/scenario.

    Returns a dict with deterioration_R, adverse_R, reward_remaining, and a
    per-candidate-threshold map {threshold: would_reject(bool)}. These are LOGGED
    challengers only — no decision is taken, no winner is chosen on this sample.
    """
    det = reward = None
    rejects = {}
    detail = ledger_c.get("detail") or {}
    exec_entry = detail.get("entry_price")
    ref_entry = sig.get("ref_entry")
    risk = detail.get("risk")
    try:
        sign = 1 if (sig["direction"] or "").upper() in ("LONG", "BUY") else -1
    except Exception:  # noqa: BLE001
        sign = 0

    if exec_entry is not None and ref_entry is not None and risk not in (None, "0"):
        det = deterioration_r(sign, exec_entry, ref_entry, risk)
        tp1 = sig["targets"][0] if sig.get("targets") else None
        reward = reward_remaining_fraction(sign, tp1, exec_entry, ref_entry) if tp1 else None
        adv = adverse_r(det)
        for thr in cfg.NOCHASE_CANDIDATE_THRESHOLDS_R:
            rejects[str(thr)] = bool(adv is not None and adv > thr)

    return {
        "deterioration_r": str(det) if det is not None else None,
        "adverse_r": str(adverse_r(det)) if det is not None else None,
        "reward_remaining_fraction": str(reward) if reward is not None else None,
        "candidate_thresholds_r": [str(t) for t in cfg.NOCHASE_CANDIDATE_THRESHOLDS_R],
        "would_reject_by_threshold": rejects,
        "rule_selection_date": cfg.RULE_SELECTION_DATE,
        "data_cutoff": cfg.DATA_CUTOFF,
        "note": ("LOGGED challengers only — NOT decision-making; no winner selected "
                 "on this sample; freeze for prospective testing on NEW signals."),
        # the rejected signal is STILL replayed (ledger_c.r_value is the counterfactual
        # outcome had you taken it) so we can later see if rejecting helped or hurt.
        "counterfactual_r_if_taken": ledger_c.get("r_value"),
    }
