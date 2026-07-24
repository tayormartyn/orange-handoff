"""
Assemble one effective trade from a confirmed SIGNAL + linked confirmed TRADE_UPDATE / TRADE_RESULT
events + quote-path evidence + demo broker events. DERIVED and append-only — no original record is
mutated. Only children that LINK to this signal advance it; ambiguous/unlinked children become
blockers. Broker execution evidence is authoritative; provider claims and market-path touches are
carried separately and never presented as Martyn's realised result. Replay-validation trades never
enter prospective demo statistics.
"""
from __future__ import annotations

import linker
import evidence as EV
import outcome_rules
import state_machine
from lc_models import (EffectiveTrade, REPLAY_VALIDATION_ONLY, PROSPECTIVE_DEMO_EXECUTION,
                    LINK_LINKED, LINK_AMBIGUOUS)


def _is_candidate(child, signal):
    """A child is a genuine candidate for THIS signal only if instrument matches AND (direction or
    provider) corroborates AND it is chronologically after the signal. Symbol alone never qualifies."""
    if not child.instrument or not signal.instrument:
        return False
    if child.instrument.upper() != signal.instrument.upper():
        return False
    dir_ok = bool(child.direction and signal.direction and child.direction == signal.direction)
    prov_ok = bool(child.provider and signal.provider and child.provider == signal.provider)
    chrono = (signal.ts_ms is None or child.ts_ms is None or signal.ts_ms <= child.ts_ms)
    return (dir_ok or prov_ok) and chrono


def build_effective_trade(signal, children, broker_events=None, quote_path=None, broker_map=None,
                          levels=None):
    broker_events = list(broker_events or [])
    quote_path = quote_path or []
    seen, linked_updates, linked_results, blockers = set(), [], [], []

    for c in children:
        if c.child_id in seen:                          # idempotent: duplicate updates ignored
            continue
        seen.add(c.child_id)
        # a child CONFIRMED-linked to a specific parent belongs only to that parent
        if c.explicit_parent_signal_id:
            if c.explicit_parent_signal_id == signal.signal_id:
                (linked_updates if c.child_class == "TRADE_UPDATE" else linked_results).append(c)
            continue                                     # linked elsewhere -> NOT this signal's blocker
        # unresolved child: link to (or block) THIS signal only if it is a genuine candidate for it
        lr = linker.link_child(c, [signal], broker_map)
        if lr.status == LINK_LINKED and lr.parent_signal_id == signal.signal_id:
            (linked_updates if c.child_class == "TRADE_UPDATE" else linked_results).append(c)
        elif _is_candidate(c, signal):
            blockers.append(f"UNRESOLVED_CANDIDATE:{c.child_id}")
        # else: not a candidate for this signal -> not a blocker here

    # evidence layers — kept strictly separate
    provider_ev = [EV.provider_instruction(c) for c in (linked_updates + linked_results)]
    broker_ev = [EV.broker_evidence(b) for b in broker_events]
    market_ev = EV.market_touches(quote_path, signal.direction, levels or {}) if levels else []

    provider_only = not broker_events
    state, outcome, realised, r, out_blockers = outcome_rules.determine_outcome(
        signal=signal, broker_events=broker_events, provider_only=provider_only)
    blockers += out_blockers

    fill = next((b for b in broker_events if b.kind == "ORDER_FILLED"), None)
    seq = state_machine.derive_sequence(signal, provider_ev, broker_events, state,
                                        entry_vwap=(fill.vwap_price if fill else None))

    # provenance: fresh demo broker events on a non-replay signal are prospective; else replay-only
    prospective = (any(getattr(b, "prospective", False) for b in broker_events)
                   and not signal.replay and not any(c.replay for c in linked_results))
    provenance = PROSPECTIVE_DEMO_EXECUTION if prospective else REPLAY_VALIDATION_ONLY
    counts = provenance == PROSPECTIVE_DEMO_EXECUTION and bool(broker_events)

    return EffectiveTrade(
        signal_id=signal.signal_id, state=state, outcome=outcome, provenance=provenance,
        realised_pnl=(realised if provenance == PROSPECTIVE_DEMO_EXECUTION else realised),
        r_multiple=r, provider_instructions=[e.__dict__ for e in provider_ev],
        market_path=[e.__dict__ for e in market_ev], broker_events=[e.__dict__ for e in broker_ev],
        linked_updates=[c.child_id for c in linked_updates],
        linked_results=[c.child_id for c in linked_results],
        blockers=blockers, counts_in_prospective_stats=counts), seq
