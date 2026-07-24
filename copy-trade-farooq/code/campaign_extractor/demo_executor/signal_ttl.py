"""
Stale-signal TTL. Age is measured ONLY from the provider's own message timestamp -> current UTC.
Screenshot-capture / OCR / ingestion / operator-paste times are NEVER substituted. If the provider
timestamp is absent, ambiguous, or future-dated beyond a small clock-skew tolerance, the signal is
EXECUTION_ELIGIBLE=False with PROVIDER_TIMESTAMP_UNVERIFIED. Freshness is re-checked at every stage;
an earlier valid preview never overrides a later TTL failure.
"""
from __future__ import annotations

import config as CFG

STAGES = ("intake_classification", "proposal_construction", "arming", "final_approval",
          "before_network_attempt")


def evaluate_freshness(*, provider_ts_ms, now_ms, ingestion_ts_ms=None, stage="final_approval",
                       ttl_seconds=None, skew_seconds=None):
    """Returns a full freshness decision dict. Only provider_ts_ms drives age."""
    ttl = CFG.FRESH_SIGNAL_TTL_SECONDS if ttl_seconds is None else ttl_seconds
    skew = CFG.CLOCK_SKEW_TOLERANCE_SECONDS if skew_seconds is None else skew_seconds
    base = {"stage": stage, "provider_timestamp_ms": provider_ts_ms, "ingestion_timestamp_ms": ingestion_ts_ms,
            "current_utc_ms": now_ms, "ttl_seconds": ttl, "clock_skew_tolerance_seconds": skew}

    if provider_ts_ms is None:
        return {**base, "signal_age_seconds": None, "remaining_validity_seconds": None,
                "freshness_decision": "PROVIDER_TIMESTAMP_UNVERIFIED", "execution_eligible": False,
                "effective_state": "BLOCKED", "blocking_reason": "PROVIDER_TIMESTAMP_UNVERIFIED"}

    if provider_ts_ms > now_ms + skew * 1000:            # future-dated beyond tolerance
        return {**base, "signal_age_seconds": round((now_ms - provider_ts_ms) / 1000, 1),
                "remaining_validity_seconds": None, "freshness_decision": "PROVIDER_TIMESTAMP_UNVERIFIED",
                "execution_eligible": False, "effective_state": "BLOCKED",
                "blocking_reason": "PROVIDER_TIMESTAMP_UNVERIFIED"}

    age = (now_ms - provider_ts_ms) / 1000.0
    if age > ttl:
        return {**base, "signal_age_seconds": round(age, 1), "remaining_validity_seconds": 0,
                "freshness_decision": "EXPIRED", "execution_eligible": False,
                "effective_state": "EXPIRED", "blocking_reason": "SIGNAL_TTL_EXCEEDED"}

    return {**base, "signal_age_seconds": round(age, 1),
            "remaining_validity_seconds": round(ttl - age, 1), "freshness_decision": "FRESH",
            "execution_eligible": True, "effective_state": "ELIGIBLE", "blocking_reason": None}


def is_fresh(**kw):
    return evaluate_freshness(**kw)["execution_eligible"]
