"""
Strong-provenance matching of a management plan to exactly ONE broker position/order. Never selects
using symbol alone. Requires a broker id match, OR provenance (signal/proposal/clientOrderId) carried
in the broker label/comment metadata plus symbol+direction. More than one candidate => AMBIGUOUS
(blocks the action). Zero => NO_MATCH.
"""
from __future__ import annotations


def _provenance_hit(obj, approved):
    """obj is a broker position/order with id + label/comment metadata."""
    oid = str(getattr(obj, "position_id", None) or obj.get("position_id") if isinstance(obj, dict)
              else getattr(obj, "position_id", None))
    # broker id match (strongest)
    for key, val in (("position_id", approved.broker_position_id), ("order_id", approved.broker_order_id)):
        bid = obj.get(key) if isinstance(obj, dict) else getattr(obj, key, None)
        if val is not None and bid is not None and str(bid) == str(val):
            return "BROKER_ID"
    # provenance in label/comment + symbol + direction
    label = (obj.get("label") if isinstance(obj, dict) else getattr(obj, "label", None)) or ""
    comment = (obj.get("comment") if isinstance(obj, dict) else getattr(obj, "comment", None)) or ""
    meta = f"{label} {comment}"
    sym = (obj.get("symbol") if isinstance(obj, dict) else getattr(obj, "symbol", None))
    direction = (obj.get("direction") if isinstance(obj, dict) else getattr(obj, "direction", None))
    prov_tokens = [t for t in (approved.signal_id, approved.proposal_id, approved.client_order_id) if t]
    prov_ok = any(t and t in meta for t in prov_tokens)
    sym_ok = sym is not None and str(sym).upper() == str(approved.symbol_name).upper()
    dir_ok = direction is not None and str(direction).upper() == str(approved.direction).upper()
    if prov_ok and sym_ok and dir_ok:
        return "PROVENANCE_META"
    return None


def match_cancel_target(approved, candidates):
    """Match a CANCEL_PENDING plan to exactly ONE eligible pending order. Never symbol-alone. Blocks on
    zero / multiple candidates, filled, cancelled, or wrong-account. Returns (status, order_id, reason)."""
    prov_hits = []
    for c in candidates or []:
        acct = c.get("account_id") if isinstance(c, dict) else getattr(c, "account_id", None)
        if acct is not None and str(acct) != str(approved.account_id):
            continue                                         # belongs to another account -> ignore
        if _provenance_hit(c, approved):
            prov_hits.append(c)
    if not prov_hits:
        return "NO_MATCH", None, "ZERO_CANDIDATES"
    if len(prov_hits) > 1:
        return "AMBIGUOUS", None, "MULTIPLE_CANDIDATES"
    c = prov_hits[0]
    state = str((c.get("state") if isinstance(c, dict) else getattr(c, "state", "")) or "").upper()
    oid = c.get("order_id") if isinstance(c, dict) else getattr(c, "order_id", None)
    if state == "FILLED":
        return "BLOCKED", oid, "CANDIDATE_ALREADY_FILLED"
    if state in ("CANCELLED", "CANCELED"):
        return "BLOCKED", oid, "CANDIDATE_ALREADY_CANCELLED"
    if state not in ("PENDING", "ACCEPTED", "OPEN", ""):
        return "BLOCKED", oid, f"CANDIDATE_STATE_{state}"
    return "VERIFIED", oid, "OK"


def match_target(approved, candidates):
    """candidates: broker positions (amend/close) or orders (cancel). Returns
    (status, matched_id, method, evidence). status in VERIFIED / AMBIGUOUS / NO_MATCH."""
    hits = []
    for c in candidates or []:
        method = _provenance_hit(c, approved)
        if method:
            cid = (c.get("position_id") or c.get("order_id")) if isinstance(c, dict) else \
                  (getattr(c, "position_id", None) or getattr(c, "order_id", None))
            hits.append((cid, method))
    # never symbol-alone: _provenance_hit already requires a broker id or provenance+direction
    if len(hits) == 1:
        return "VERIFIED", hits[0][0], hits[0][1], {"candidates": 1}
    if len(hits) > 1:
        return "AMBIGUOUS", None, None, {"candidates": len(hits),
                                         "reason": "MULTIPLE_MATCHES_BLOCK_ACTION"}
    return "NO_MATCH", None, None, {"candidates": 0}
