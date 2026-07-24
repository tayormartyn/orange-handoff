"""Scale-out + runner-lifecycle research helpers (RESEARCH-ONLY / SIMULATION-ONLY).

Result cards are classified as SAME_CAMPAIGN_SCALE_OUT_EVIDENCE (never a new campaign). The runner
lifecycle keeps a campaign OPEN until an explicit terminal event. Lane A "close X% leave Y%" closes X%
of the CURRENTLY REMAINING OPEN FILLED QUANTITY. No broker/size/original-position inference.
"""
from __future__ import annotations

from decimal import Decimal as D
from fractions import Fraction

# events that keep a campaign OPEN (never auto-close)
NON_TERMINAL = {"RESULT_CARD", "PROFIT_PROGRESS_COMMENTARY", "EXPLICIT_PERCENTAGE_PARTIAL_CLOSE",
                "TAKE_PCT_OFF", "TP1_TAKE", "SL_TO_ENTRY", "SCALE_OUT"}
# only these (constitutionally valid terminal evidence) close a runner
TERMINAL = {"FINAL_CLOSE", "RUNNER_STOP_HIT", "RUNNER_TARGET_HIT", "CAMPAIGN_CANCELLED"}


def reconcile_card(entry, exit_, volume_label, displayed_result, direction="SELL"):
    """Source arithmetic: price_movement * 100 * volume_label == displayed_result (source-level only;
    NOT broker verification, NOT a size claim)."""
    move = (D(str(entry)) - D(str(exit_))) if direction == "SELL" else (D(str(exit_)) - D(str(entry)))
    expected = (move * D("100") * D(str(volume_label))).quantize(D("1"))
    return {"price_movement": str(move), "volume_label": str(volume_label),
            "expected_result": str(expected), "displayed_result": str(displayed_result),
            "reconciles": expected == D(str(displayed_result)),
            "note": "source-level arithmetic only; not broker verification; original position size NOT inferred"}


def classify_result_card(card, open_campaign):
    """card: {instrument, direction, entry, exit, volume_label, result, timestamp, provenance}.
    open_campaign: {instrument, direction, entry, ...} or None. Returns a classification that NEVER
    creates a new campaign from a result card alone."""
    if open_campaign is None:
        return {"classification": "SAME_CAMPAIGN_SCALE_OUT_EVIDENCE" if False else "AMBIGUOUS_NO_OPEN_CAMPAIGN",
                "creates_new_campaign": False, "reason": "no open campaign to attach; result card never creates a campaign"}
    same = (card["instrument"] == open_campaign["instrument"] and card["direction"] == open_campaign["direction"]
            and D(str(card["entry"])) == D(str(open_campaign["entry"])))
    return {
        "classification": ("SAME_CAMPAIGN_SCALE_OUT_EVIDENCE" if same else "MISMATCH_NEEDS_REVIEW"),
        "creates_new_campaign": False,
        "reason": ("same instrument+direction+entry, later exit, no fresh signal" if same else "entry/direction mismatch"),
        "preserved": {k: card.get(k) for k in ("entry", "exit", "volume_label", "result", "timestamp", "provenance")},
        "not_inferred": ["original_position_size", "broker_account_size", "orange_profit",
                         "broker_equivalent_fill", "final_campaign_closure"],
        "price_semantics": "TRADINGVIEW_PRICE_SEMANTICS_UNVERIFIED / BROKER_EXECUTION_EQUIVALENCE_UNPROVEN",
    }


def apply_scale_out(remaining_open, close_percentage):
    """Lane A quantity base: close X% of the CURRENTLY REMAINING OPEN FILLED QUANTITY (Fraction)."""
    rem = Fraction(remaining_open)
    closed = rem * Fraction(int(close_percentage), 100)
    return {"quantity_base": "CURRENTLY_REMAINING_OPEN_FILLED_QUANTITY",
            "remaining_before": str(rem), "closed": str(closed), "remaining_after": str(rem - closed)}


def runner_transition(lifecycle, event, residual_after):
    """Deterministic runner lifecycle. Only TERMINAL events close; partials with residual>0 ->
    PARTIALS_BANKED_RUNNER_ACTIVE; result cards / commentary / big profit -> NO transition (stay OPEN)."""
    if event in TERMINAL:
        return "CLOSED"
    if event in ("EXPLICIT_PERCENTAGE_PARTIAL_CLOSE", "TAKE_PCT_OFF", "TP1_TAKE", "SCALE_OUT") and Fraction(residual_after) > 0:
        return "PARTIALS_BANKED_RUNNER_ACTIVE"
    return lifecycle           # RESULT_CARD / PROFIT_PROGRESS_COMMENTARY / anything else -> unchanged


def profit_commentary(text, claimed_pips=None):
    """'X pips if still holding' etc. -> commentary, no transition, pip_convention UNVERIFIED."""
    return {"classification": "PROFIT_PROGRESS_COMMENTARY", "automatic_state_transition": "NONE",
            "claimed_pips_preserved": claimed_pips, "pip_convention": "UNVERIFIED",
            "raw": text, "is_implicit_close": False}
