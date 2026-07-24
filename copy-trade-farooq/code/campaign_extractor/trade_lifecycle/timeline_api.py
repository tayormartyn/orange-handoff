"""
Build the expandable trade-timeline payload for the console UI from an EffectiveTrade + derived state
sequence. Pure formatting — no mutation. Provider/market/broker layers stay labelled and separate;
realised P&L and R are shown only when the engine actually produced them.
"""
from __future__ import annotations


def build_timeline(effective, seq):
    chain = " → ".join(s["state"] for s in seq)
    return {
        "signal_id": effective.signal_id,
        "current_state": effective.state,
        "final_outcome": effective.outcome,
        "provenance": effective.provenance,
        "counts_in_prospective_stats": effective.counts_in_prospective_stats,
        "realised_demo_pnl": effective.realised_pnl if effective.provenance == "PROSPECTIVE_DEMO_EXECUTION" else None,
        "realised_pnl_replay_only": effective.realised_pnl if effective.provenance == "REPLAY_VALIDATION_ONLY" else None,
        "r_multiple": effective.r_multiple,
        "chain": chain,
        "steps": seq,
        "linked_updates": effective.linked_updates,
        "linked_results": effective.linked_results,
        "provider_instructions": effective.provider_instructions,
        "market_path_evidence": effective.market_path,
        "broker_execution_evidence": effective.broker_events,
        "blockers": effective.blockers,
        "note": ("Broker execution evidence is authoritative for demo performance. Provider "
                 "instructions and market-path touches are shown separately and are NOT our realised "
                 "broker result."),
    }
