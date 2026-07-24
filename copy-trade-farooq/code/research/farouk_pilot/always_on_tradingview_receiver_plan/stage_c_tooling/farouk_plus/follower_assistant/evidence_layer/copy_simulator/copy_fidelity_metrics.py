"""Copy-fidelity metrics (RESEARCH-ONLY). Campaign-level + aggregate. Every metric exposes its
denominator, included/excluded record classes, exclusion reasons and cost assumptions. Never claims
profitability from synthetic/backfill campaigns.
"""
from __future__ import annotations

MIN_SAMPLE = 5


def campaign_fidelity(sim):
    legs = sim["legs"]
    filled = [l for l in legs if l["state"] == "FILLED"]
    cancelled = [l for l in legs if l["state"] == "CANCELLED"]
    ambiguous = sim["ambiguous_intrabar_present"]
    be_legs = [l for l in filled if l["be_price"] is not None]
    return {
        "campaign_id": sim["campaign_id"], "profile": sim["profile"], "cost_scenario": sim["cost_scenario"],
        "three_legs_created": len(legs) == 3,
        "legs_filled": len(filled), "legs_cancelled": len(cancelled),
        "per_leg_be_applied": len(be_legs), "be_fidelity": (len(be_legs) == len(filled)),
        "reconciliation": sim["reconciliation"],
        "ambiguous_intrabar": ambiguous,
        "zone_touched_before_receipt": sim["zone_touched_before_receipt"],
        "manual_review_count": len(sim["manual_review"]),
        "eligible_for_training": False, "eligible_for_performance_attribution": False,
        "included_record_class": "SIMULATION_ONLY",
        "cost_assumptions": sim["cost_assumptions"],
    }


def aggregate(sims):
    n = len(sims)
    if n == 0:
        return {"status": "NO_CAMPAIGNS", "denominator": 0}
    def rate(pred):
        d = [s for s in sims]
        num = sum(1 for s in d if pred(s))
        return {"rate": (num / len(d) if d else None), "numerator": num, "denominator": len(d)}
    agg = {
        "denominator": n,
        "included_record_classes": ["SIMULATION_ONLY"],
        "excluded_records": "none (all simulation-only; none eligible for performance attribution)",
        "exclusion_reasons": ["SIMULATION_ONLY: no broker fill; no perf attribution"],
        "three_leg_fidelity": rate(lambda s: len(s["legs"]) == 3),
        "reconciliation_rate": rate(lambda s: s["reconciliation"] == "RECONCILED"),
        "ambiguous_intrabar_rate": rate(lambda s: s["ambiguous_intrabar_present"]),
        "zone_touched_before_receipt_rate": rate(lambda s: s["zone_touched_before_receipt"]),
        "manual_review_rate": rate(lambda s: len(s["manual_review"]) > 0),
        "simulation_completion_rate": rate(lambda s: s["record_type"] == "SIMULATION_CAMPAIGN"),
        "profitability_claim": "NONE (synthetic/backfill/simulation — not a broker result)",
        "price_semantics": "TRADINGVIEW_PRICE_SEMANTICS_UNVERIFIED / BROKER_EXECUTION_EQUIVALENCE_UNPROVEN",
    }
    if n < MIN_SAMPLE:
        agg["sample_warning"] = f"INSUFFICIENT_SAMPLE (n={n} < {MIN_SAMPLE}); rates indicative only"
    return agg
