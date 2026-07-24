"""
Derive the ordered lifecycle-state sequence from provider instructions + broker events. Each emitted
step records which evidence layer produced it, so a provider instruction (INSTRUCTED) is never
confused with a confirmed broker action (CONFIRMED). Ambiguous / unlinked inputs never advance the
machine (the caller passes only linked, confirmed events).
"""
from __future__ import annotations

from lc_models import (PROVIDER_INSTRUCTION, BROKER_EXECUTION_EVIDENCE)

_PROVIDER_STEP = {
    "TAKE_PROFIT": "PARTIAL_PROFIT_INSTRUCTED", "TAKE_MORE_PROFIT": "PARTIAL_PROFIT_INSTRUCTED",
    "TAKE_PARTIAL": "PARTIAL_PROFIT_INSTRUCTED", "BANK_PROFIT": "PARTIAL_PROFIT_INSTRUCTED",
    "MOVE_SL_BREAKEVEN": "STOP_MOVE_INSTRUCTED", "MOVE_STOP": "STOP_MOVE_INSTRUCTED",
}
_BROKER_STEP = {
    "ORDER_PLACED": "PENDING_ORDER", "ORDER_FILLED": "FILLED", "PARTIAL_CLOSE": "PARTIAL_PROFIT_CONFIRMED",
    "SL_AMENDED": "STOP_MOVED_TO_BREAKEVEN", "TARGET_HIT": "TARGET_HIT", "POSITION_CLOSED": "FULL_CLOSE_CONFIRMED",
}


def _step(state, layer, ts, detail=None):
    return {"state": state, "layer": layer, "ts_ms": ts, "detail": detail or {}}


def derive_sequence(signal, provider_instructions, broker_events, outcome_state, entry_vwap=None):
    seq = [_step("SIGNAL_CAPTURED", PROVIDER_INSTRUCTION, signal.ts_ms, {"signal_id": signal.signal_id})]

    prov = [(e.ts_ms if e.ts_ms is not None else 0, "P", e) for e in provider_instructions]
    brk = [(e.ts_ms if e.ts_ms is not None else 0, "B", e) for e in broker_events]
    for _ts, src, e in sorted(prov + brk, key=lambda x: x[0]):
        if src == "P":
            st = _PROVIDER_STEP.get((e.kind or "").upper())
            if st:
                seq.append(_step(st, PROVIDER_INSTRUCTION, e.ts_ms, {"provider": e.detail.get("provider")}))
        else:
            if e.kind == "STOP_HIT":
                be = entry_vwap is not None and e.stop_price is not None and abs(e.stop_price - entry_vwap) <= 0.10
                orig = signal.stop is not None and e.stop_price is not None and abs(e.stop_price - signal.stop) <= 0.10
                st = "BREAKEVEN_STOP_HIT" if be else ("ORIGINAL_STOP_HIT" if orig else "ORIGINAL_STOP_HIT")
                seq.append(_step(st, BROKER_EXECUTION_EVIDENCE, e.ts_ms, {"stop_price": e.stop_price}))
                continue
            st = _BROKER_STEP.get(e.kind)
            if st:
                seq.append(_step(st, BROKER_EXECUTION_EVIDENCE, e.ts_ms,
                                 {k: getattr(e, k) for k in ("vwap_price", "stop_price", "closed_volume_raw")
                                  if getattr(e, k, None) is not None}))
                if st == "FILLED":
                    seq.append(_step("OPEN", BROKER_EXECUTION_EVIDENCE, e.ts_ms))
    if outcome_state and (not seq or seq[-1]["state"] != outcome_state):
        seq.append(_step(outcome_state, BROKER_EXECUTION_EVIDENCE, None, {"terminal": True}))
    return seq
