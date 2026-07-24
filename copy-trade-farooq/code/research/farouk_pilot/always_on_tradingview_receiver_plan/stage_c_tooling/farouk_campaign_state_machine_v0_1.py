"""
Farouk Campaign State Machine v0.1  —  OFFLINE, OBSERVATION-ONLY.

Converts a captured/classified Farouk alert + resolved context evidence into an
observation-only *campaign state*. It encodes the Human Review Batch 001 lessons as
DETERMINISTIC transitions. It NEVER emits broker / demo / live execution.

Hard guarantees (enforced below):
  * No broker fields, no account fields, no lot size, no order intent, no execution
    route, no risk sizing, no permit/lease/order creation.
  * Deterministic transitions only (no time, no randomness, no I/O).
  * Every output is candidate-only / observation-only; all execution flags hard-wired False.
  * No candidate can become "trade-ready" (trade_ready is always False).

This module does NOT read or write execution gates, and does not change
NOT_INTEGRATION_READY (which remains True / in force).
"""

from dataclasses import dataclass, field
from typing import Optional

# ---- module-level, observation-only guards (informational; never toggled here) ----
OBSERVATION_ONLY = True
NOT_INTEGRATION_READY = True  # unchanged by this module

# The complete set of campaign states (per spec).
STATES = (
    "IDLE",
    "ALERT_CAPTURED",
    "CLASSIFIED",
    "CONTEXT_PENDING",
    "HTF_CHECK_PENDING",
    "HTF_ALIGNED",
    "HTF_OPPOSED",
    "LIQUIDITY_SWEEP_CONFIRMED",
    "STRUCTURE_CONFIRMED",
    "POI_CONFIRMED",
    "CONTRADICTION_FOUND",
    "WATCH_ONLY",
    "SHADOW_REJECTED",
    "SHADOW_CANDIDATE_LOW",
    "SHADOW_CANDIDATE_MEDIUM",
    "OUTCOME_TRACKING",
    "HUMAN_REVIEW_REQUIRED",
    "REVIEWED",
    "JOURNALLED",
)

# Terminal *classification* states (the "label").
CAMPAIGN_STATES = ("SHADOW_CANDIDATE_MEDIUM", "SHADOW_CANDIDATE_LOW", "WATCH_ONLY", "SHADOW_REJECTED")

# substrings that mark an execution/broker surface
FORBIDDEN_KEY_SUBSTRINGS = (
    "broker", "account", "lot", "order", "route", "risk_siz", "permit", "lease",
    "position", "demo_exec", "live_exec", "qty", "size",
)
# The ONLY keys allowed to contain those substrings are the explicit NEGATIVE safety
# flags — and they must every one be False. Anything else containing a forbidden
# substring is a real execution surface and is rejected.
ALLOWED_NEGATIVE_FLAGS = frozenset({
    "execution_allowed", "broker_execution_allowed", "qst_allowed",
    "order_intent", "risk_sizing_allowed", "trade_ready",
})

# Enumerations for input evidence (resolved facts from proxies + human review).
SWEEP = ("NONE", "PRESENT", "CONFIRMED")
STRUCT = ("NONE", "WEAK", "CONFIRMED")
OB = ("NONE", "FRESH", "FRESH_BREACHED", "MITIGATED_SPENT")
DISP = ("NONE", "WEAK", "MODERATE", "STRONG", "AGAINST")
HTF = ("UNKNOWN", "ALIGNED", "OPPOSED")
OUTCOME = ("UNKNOWN", "FAVOURABLE", "MIXED", "UNFAVOURABLE")

# human-review label -> campaign state mapping
HUMAN_LABEL_TO_STATE = {
    "SHADOW_CANDIDATE_MEDIUM": "SHADOW_CANDIDATE_MEDIUM",
    "SHADOW_CANDIDATE_LOW": "SHADOW_CANDIDATE_LOW",
    "WATCH": "WATCH_ONLY",
    "WATCH_ONLY": "WATCH_ONLY",
    "CONTEXT_ONLY": "WATCH_ONLY",
    "REJECT": "SHADOW_REJECTED",
    "SHADOW_REJECTED": "SHADOW_REJECTED",
}


@dataclass(frozen=True)
class Observation:
    """Resolved evidence for one Farouk alert anchor (facts, not proxies-only)."""
    campaign_id: str = "UNSET"
    alert_raw: str = ""
    classified_family: str = "UNKNOWN"
    direction_hint: Optional[str] = None      # "LONG" | "SHORT" | None
    sweep: str = "NONE"                        # SWEEP
    sweep_late: bool = False
    structure_choch: str = "NONE"             # STRUCT
    choch_in_chop: bool = False
    order_block: str = "NONE"                 # OB
    displacement: str = "NONE"                # DISP
    htf: str = "UNKNOWN"                       # HTF
    contradiction: bool = False
    outcome: str = "UNKNOWN"                   # OUTCOME
    human_review: Optional[dict] = None        # {"label": "...", "status": "REVIEWED"}


@dataclass
class CampaignResult:
    campaign_id: str
    state_path: list = field(default_factory=list)
    campaign_state: str = "WATCH_ONLY"        # machine classification (the "label")
    final_state: str = "HUMAN_REVIEW_REQUIRED"
    resolved_label: str = "WATCH_ONLY"
    reasons: list = field(default_factory=list)
    machine_human_agree: Optional[bool] = None
    # hard-wired observation-only guarantees (NEVER an execution surface):
    candidate_only: bool = True
    trade_ready: bool = False
    execution_allowed: bool = False
    broker_execution_allowed: bool = False
    qst_allowed: bool = False
    order_intent: bool = False
    risk_sizing_allowed: bool = False
    observation_only: bool = True

    def to_dict(self) -> dict:
        return {
            "campaign_id": self.campaign_id,
            "state_path": list(self.state_path),
            "campaign_state": self.campaign_state,
            "final_state": self.final_state,
            "resolved_label": self.resolved_label,
            "reasons": list(self.reasons),
            "machine_human_agree": self.machine_human_agree,
            "candidate_only": self.candidate_only,
            "trade_ready": self.trade_ready,
            "execution_allowed": self.execution_allowed,
            "broker_execution_allowed": self.broker_execution_allowed,
            "qst_allowed": self.qst_allowed,
            "order_intent": self.order_intent,
            "risk_sizing_allowed": self.risk_sizing_allowed,
            "observation_only": self.observation_only,
        }


def _decide(o: Observation):
    """Deterministic classification from resolved evidence. Returns (state, reasons)."""
    reasons = []
    sweep_ok = o.sweep in ("PRESENT", "CONFIRMED")
    choch_ok = (o.structure_choch == "CONFIRMED") and (not o.choch_in_chop)
    choch_weak = (o.structure_choch == "WEAK") or o.choch_in_chop
    ob_valid = o.order_block == "FRESH"
    ob_breached = o.order_block == "FRESH_BREACHED"
    ob_dead = o.order_block == "MITIGATED_SPENT"
    outcome_bad = o.outcome == "UNFAVOURABLE"
    disp_against = o.displacement == "AGAINST"
    htf_opposed = o.htf == "OPPOSED"
    htf_aligned = o.htf == "ALIGNED"

    # (1) REJECT — invalidated thesis (batch-001: spent OB / contradiction / displacement-against + adverse)
    if ob_dead and (o.contradiction or outcome_bad or disp_against):
        reasons.append("spent/mitigated OB with contradiction / adverse outcome / against-displacement -> reject")
        return "SHADOW_REJECTED", reasons
    if o.contradiction and outcome_bad:
        reasons.append("signal against effective bias + unfavourable outcome -> reject")
        return "SHADOW_REJECTED", reasons
    if disp_against and outcome_bad:
        reasons.append("displacement against direction + unfavourable outcome -> reject")
        return "SHADOW_REJECTED", reasons

    # (2) WATCH_ONLY — strong negatives that block candidacy
    if ob_breached:
        reasons.append("fresh OB breached post-entry -> watch only (failed POI)")
        return "WATCH_ONLY", reasons
    if ob_dead:
        reasons.append("spent/mitigated OB -> watch only (no valid POI)")
        return "WATCH_ONLY", reasons
    if choch_weak and outcome_bad:
        reasons.append("weak CHoCH in chop + unfavourable outcome -> watch only")
        return "WATCH_ONLY", reasons
    if htf_opposed and outcome_bad and not ob_valid:
        reasons.append("HTF opposed + unfavourable outcome + no valid POI -> watch only")
        return "WATCH_ONLY", reasons

    # (3) any candidate REQUIRES a valid (fresh, un-breached) POI + a sweep
    if not (ob_valid and sweep_ok):
        reasons.append("insufficient confluence (need fresh POI + sweep) -> watch only")
        return "WATCH_ONLY", reasons

    # (4) MEDIUM — the HTF-alignment gate (batch-001: HTF alignment is the differentiator)
    if (ob_valid and sweep_ok and choch_ok and htf_aligned
            and not o.contradiction and not outcome_bad and not disp_against):
        reasons.append("valid POI + sweep + confirmed CHoCH + HTF aligned + clean -> medium")
        return "SHADOW_CANDIDATE_MEDIUM", reasons

    # (5) LOW — real confluence but capped (HTF not aligned, or weak CHoCH); outcome not adverse
    if ob_valid and sweep_ok and not outcome_bad:
        if htf_opposed:
            reasons.append("valid POI + sweep but HTF opposed -> capped at LOW")
        elif choch_weak:
            reasons.append("valid POI + sweep but weak CHoCH -> capped at LOW")
        else:
            reasons.append("valid POI + sweep, HTF not confirmed-aligned -> LOW")
        return "SHADOW_CANDIDATE_LOW", reasons

    # (6) fallback
    reasons.append("valid POI + sweep but adverse/insufficient -> watch only")
    return "WATCH_ONLY", reasons


def run(obs) -> CampaignResult:
    """Walk the deterministic state machine for one observation. obs: Observation or dict."""
    if isinstance(obs, dict):
        obs = Observation(**obs)

    res = CampaignResult(campaign_id=obs.campaign_id)
    path = ["IDLE", "ALERT_CAPTURED", "CLASSIFIED", "CONTEXT_PENDING"]

    if obs.sweep in ("PRESENT", "CONFIRMED"):
        path.append("LIQUIDITY_SWEEP_CONFIRMED")
    if obs.structure_choch == "CONFIRMED" and not obs.choch_in_chop:
        path.append("STRUCTURE_CONFIRMED")
    if obs.order_block == "FRESH":
        path.append("POI_CONFIRMED")

    path.append("HTF_CHECK_PENDING")
    if obs.htf == "ALIGNED":
        path.append("HTF_ALIGNED")
    elif obs.htf == "OPPOSED":
        path.append("HTF_OPPOSED")

    if obs.contradiction:
        path.append("CONTRADICTION_FOUND")

    campaign_state, reasons = _decide(obs)
    res.campaign_state = campaign_state
    res.reasons = reasons
    path.append(campaign_state)

    if obs.outcome != "UNKNOWN":
        path.append("OUTCOME_TRACKING")

    # lifecycle
    if campaign_state in ("SHADOW_CANDIDATE_LOW", "SHADOW_CANDIDATE_MEDIUM", "WATCH_ONLY"):
        path.append("HUMAN_REVIEW_REQUIRED")

    res.resolved_label = campaign_state
    if obs.human_review:
        label = str(obs.human_review.get("label", "")).upper()
        mapped = HUMAN_LABEL_TO_STATE.get(label)
        res.machine_human_agree = (mapped == campaign_state) if mapped else None
        if mapped:
            res.resolved_label = obs.human_review.get("label")
        path.append("REVIEWED")
        path.append("JOURNALLED")
        res.final_state = "JOURNALLED"
    else:
        if campaign_state == "SHADOW_REJECTED":
            path.append("JOURNALLED")
            res.final_state = "JOURNALLED"
        else:
            res.final_state = "HUMAN_REVIEW_REQUIRED"

    res.state_path = path
    _assert_no_execution_surface(res)
    return res


def _assert_no_execution_surface(res: CampaignResult) -> None:
    """Fail-closed guard: no result may ever carry an execution/broker surface.

    A key may contain an execution-related substring ONLY if it is one of the explicit
    negative safety flags, and then its value MUST be False. Any other such key is a real
    execution surface and fails the assertion.
    """
    d = res.to_dict()
    for k, v in d.items():
        if any(bad in k.lower() for bad in FORBIDDEN_KEY_SUBSTRINGS):
            assert k in ALLOWED_NEGATIVE_FLAGS, f"forbidden execution-surface key in output: {k}"
            assert v is False, f"execution flag must be False: {k}={v!r}"
    assert d["trade_ready"] is False
    assert d["execution_allowed"] is False
    assert d["broker_execution_allowed"] is False
    assert d["qst_allowed"] is False
    assert d["order_intent"] is False
    assert d["risk_sizing_allowed"] is False
    assert d["observation_only"] is True
    assert d["candidate_only"] is True


def emits_execution(res: CampaignResult) -> bool:
    """By construction, ALWAYS False. No state can emit broker/demo/live execution."""
    return False


# ---- reviewed fixtures (Human Review Batch 001) ----
def fixture_hr0001() -> Observation:
    # ALIGNED_CHOCH_TO_A, LONG: real sweep + confirmed CHoCH + FRESH (held) OB; HTF opposed; MIXED outcome.
    return Observation(
        campaign_id="HR-0001", alert_raw="Farouks Playbook: A LONG on XAUUSD 3",
        classified_family="A_SIGNAL", direction_hint="LONG",
        sweep="CONFIRMED", structure_choch="CONFIRMED", choch_in_chop=False,
        order_block="FRESH", displacement="MODERATE", htf="OPPOSED",
        contradiction=False, outcome="MIXED",
    )


def fixture_hr0002() -> Observation:
    # SWEEP_TO_CHOCH_CONTEXT, LONG: real sweep (late) but weak CHoCH-in-chop; FRESH-but-BREACHED OB;
    # HTF opposed; UNFAVOURABLE outcome.
    return Observation(
        campaign_id="HR-0002", alert_raw="Farouks Playbook: CHoCH UP on XAUUSD 3",
        classified_family="STRUCTURE", direction_hint="LONG",
        sweep="CONFIRMED", sweep_late=True, structure_choch="WEAK", choch_in_chop=True,
        order_block="FRESH_BREACHED", displacement="MODERATE", htf="OPPOSED",
        contradiction=False, outcome="UNFAVOURABLE",
    )


def fixture_hr0003() -> Observation:
    # BPR_TO_A_CONTEXT, SHORT: spent/mitigated bearish OB; displacement bullish AGAINST the short;
    # contradiction (fired into a reversal); HTF opposed; strongly UNFAVOURABLE.
    return Observation(
        campaign_id="HR-0003", alert_raw="Farouks Playbook: A SHORT on XAUUSD 3",
        classified_family="A_SIGNAL", direction_hint="SHORT",
        sweep="PRESENT", structure_choch="WEAK", choch_in_chop=True,
        order_block="MITIGATED_SPENT", displacement="AGAINST", htf="OPPOSED",
        contradiction=True, outcome="UNFAVOURABLE",
    )
