"""
Evidence assembly. Each raw item is tagged to exactly ONE layer and the layers are never merged:
  PROVIDER_INSTRUCTION      — provider wording (take profit / TP1 / bank profit / move SL ...).
  MARKET_PATH_EVIDENCE      — recorded bid/ask touched a level. Never asserts a broker fill.
  BROKER_EXECUTION_EVIDENCE — what Martyn's demo account actually did (authoritative).
A provider result screenshot becomes PROVIDER_REPORTED_RESULT (still PROVIDER layer), never a
BROKER_EXECUTION_EVIDENCE and never Martyn's realised result.
"""
from __future__ import annotations

from lc_models import (Evidence, PROVIDER_INSTRUCTION, MARKET_PATH_EVIDENCE, BROKER_EXECUTION_EVIDENCE)


def provider_instruction(child):
    kind = child.instruction_kind or ("PROVIDER_REPORTED_RESULT" if child.child_class == "TRADE_RESULT"
                                       else "PROVIDER_UPDATE")
    return Evidence(PROVIDER_INSTRUCTION, kind, {"provider": child.provider, "class": child.child_class},
                    child.ts_ms, child.child_id)


def broker_evidence(be):
    return Evidence(BROKER_EXECUTION_EVIDENCE, be.kind,
                    {"vwap_price": be.vwap_price, "stop_price": be.stop_price,
                     "closed_volume_raw": be.closed_volume_raw, "realised_pnl": be.realised_pnl,
                     "prospective": be.prospective},
                    be.ts_ms, be.broker_order_id or be.broker_position_id)


def market_touches(quote_path, direction, levels):
    """quote_path: [{'bid','ask','ts_ms'}]. levels: {'entry','stop','target','breakeven'}.
    Returns MARKET_PATH_EVIDENCE items for touched levels — NOT broker fills."""
    out = []
    d = (direction or "").upper()
    for name in ("entry", "stop", "target", "breakeven"):
        lvl = levels.get(name)
        if lvl is None:
            continue
        touched = False
        for q in quote_path:
            bid, ask = q.get("bid"), q.get("ask")
            if bid is None or ask is None:
                continue
            # a level is "touched" if the traded band spans it
            if min(bid, ask) <= lvl <= max(bid, ask):
                touched = True
            elif name == "stop" and d == "BUY" and bid <= lvl:
                touched = True
            elif name == "stop" and d == "SELL" and ask >= lvl:
                touched = True
            elif name == "target" and d == "BUY" and bid >= lvl:
                touched = True
            elif name == "target" and d == "SELL" and ask <= lvl:
                touched = True
            if touched:
                out.append(Evidence(MARKET_PATH_EVIDENCE, "PRICE_TOUCHED_" + name.upper(),
                                    {"level": lvl, "at_ts_ms": q.get("ts_ms"),
                                     "note": "market path only — NOT a broker fill"}, q.get("ts_ms")))
                break
    return out


def split_layers(evidence_items):
    """Return (provider, market, broker) lists — proof the layers stay separate."""
    prov = [e for e in evidence_items if e.layer == PROVIDER_INSTRUCTION]
    mkt = [e for e in evidence_items if e.layer == MARKET_PATH_EVIDENCE]
    brk = [e for e in evidence_items if e.layer == BROKER_EXECUTION_EVIDENCE]
    return prov, mkt, brk
