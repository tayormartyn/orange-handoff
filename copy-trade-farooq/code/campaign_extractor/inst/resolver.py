"""
INST-1 deterministic resolution engine. Fail-closed, order-independent, time-versioned.

resolve() is a PURE function over (raw symbol, provider context, source timestamp, registry
state) — it performs reads only and returns a decision dict with a deterministic decision
hash. log_decision() appends the decision (append-only). The engine NEVER selects a venue
(venue_contract is always NOT_ROUTED) and NEVER picks the first DB row on ambiguity.
"""
from __future__ import annotations
import os

import sys as _sys
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in _sys.path:
    _sys.path.insert(0, _HERE)
from _util import canonical_hash
from normalize import normalise_token

SENTINEL_NOW = "9999-12-31T23:59:59Z"     # when no source timestamp supplied -> latest rules
VENUE = "NOT_ROUTED"


def _rows(con, sql, args):
    cur = con.execute(sql, args)
    names = [d[0] for d in cur.description]
    return [dict(zip(names, r)) for r in cur.fetchall()]


def _applicable_rules(con, token, provider_id, at):
    if provider_id:
        prov = _rows(con,
                     "SELECT * FROM mapping_rules WHERE scope='PROVIDER' AND provider_id=? "
                     "AND input_token=? AND effective_from<=?", (provider_id, token, at))
        if prov:
            return prov, "PROVIDER"
    glob = _rows(con,
                 "SELECT * FROM mapping_rules WHERE scope='GLOBAL' AND input_token=? "
                 "AND effective_from<=?", (token, at))
    return glob, "GLOBAL"


def _active_heads(rules):
    """Collapse each supersedes-lineage to its active head (latest effective_from). Two rules
    with no supersedes link are DISTINCT lineages (genuine candidates), not versions."""
    by_uid = {r["mapping_rule_uid"]: r for r in rules}

    def root(r):
        seen = set()
        cur = r
        while cur["supersedes_rule_uid"] in by_uid and cur["mapping_rule_uid"] not in seen:
            seen.add(cur["mapping_rule_uid"])
            cur = by_uid[cur["supersedes_rule_uid"]]
        return cur["mapping_rule_uid"]

    groups = {}
    for r in rules:
        groups.setdefault(root(r), []).append(r)
    heads = []
    for g in groups.values():
        heads.append(max(g, key=lambda r: (r["effective_from"], r["rule_version"],
                                            r["mapping_rule_uid"])))
    return heads


def resolve(db, raw, *, provider_id=None, source_platform=None, source_message_id=None,
            source_timestamp=None, input_provenance="FIXTURE"):
    con = db.con
    at = source_timestamp or SENTINEL_NOW
    token, validity = normalise_token(raw)

    base = {"original_raw_symbol": raw, "normalised_token": token, "provider_id": provider_id,
            "source_platform": source_platform, "source_message_id": source_message_id,
            "source_message_timestamp": source_timestamp, "input_provenance": input_provenance,
            "venue_contract": VENUE, "candidate_underlyings": [], "candidate_instruments": [],
            "selected_underlying_id": None, "selected_instrument_id": None,
            "asset_class": "UNKNOWN", "contract_type": "UNKNOWN_CONTRACT",
            "mapping_rule_versions": [], "rule_effective_from": None, "rule_effective_to": None,
            "automatically_resolved": False}

    if validity == "REJECTED_INVALID":
        return _finalise(base, "REJECTED_INVALID", "malformed or invalid symbol", raw,
                         token, provider_id, source_timestamp)

    rules, _scope = _applicable_rules(con, token, provider_id, at)
    if not rules:
        return _finalise(base, "UNKNOWN_NEEDS_REVIEW", "no mapping rule matches token", raw,
                         token, provider_id, source_timestamp)

    heads = _active_heads(rules)
    cand_u = sorted({h["target_underlying_id"] for h in heads if h["target_underlying_id"]})
    cand_i = sorted({h["target_instrument_id"] for h in heads if h["target_instrument_id"]})
    distinct_targets = sorted({(h["target_underlying_id"], h["target_instrument_id"]) for h in heads})
    base["candidate_underlyings"] = cand_u
    base["candidate_instruments"] = cand_i
    base["mapping_rule_versions"] = sorted(f"{h['mapping_rule_uid']}:v{h['rule_version']}"
                                           for h in heads)
    if len(heads) == 1:
        base["rule_effective_from"] = heads[0]["effective_from"]
        base["rule_effective_to"] = heads[0]["effective_to"]

    # --- fail-closed decisioning ---
    if len(cand_u) > 1:
        base["asset_class"] = _common_class(con, cand_u)
        return _finalise(base, "AMBIGUOUS_NEEDS_REVIEW",
                         "multiple candidate underlyings — cannot select", raw, token,
                         provider_id, source_timestamp)

    sel_u = cand_u[0] if cand_u else None
    base["selected_underlying_id"] = sel_u
    base["asset_class"] = _class_of(con, sel_u) if sel_u else "UNKNOWN"

    if len(distinct_targets) == 1:
        u, i = distinct_targets[0]
        base["selected_underlying_id"] = u
        base["asset_class"] = _class_of(con, u) if u else "UNKNOWN"
        if i is None:
            return _finalise(base, "AMBIGUOUS_NEEDS_REVIEW",
                             "underlying known; contract/instrument unspecified", raw, token,
                             provider_id, source_timestamp)
        base["selected_instrument_id"] = i
        base["contract_type"] = _contract_of(con, i)
        base["automatically_resolved"] = True
        if _scope == "PROVIDER":
            status = "PROVIDER_ALIAS_MATCH"
        else:
            status = "EXACT_MATCH" if (raw or "").strip() == token else "NORMALISED_MATCH"
        return _finalise(base, status, None, raw, token, provider_id, source_timestamp)

    # one underlying, multiple distinct instrument targets -> ambiguous (never pick first)
    return _finalise(base, "AMBIGUOUS_NEEDS_REVIEW",
                     "multiple candidate instruments for the underlying", raw, token,
                     provider_id, source_timestamp)


def _class_of(con, underlying_id):
    row = con.execute("SELECT asset_class FROM canonical_underlyings WHERE underlying_id=?",
                      (underlying_id,)).fetchone()
    return row[0] if row else "UNKNOWN"


def _common_class(con, underlyings):
    classes = {_class_of(con, u) for u in underlyings}
    return classes.pop() if len(classes) == 1 else "UNKNOWN"


def _contract_of(con, instrument_id):
    row = con.execute("SELECT contract_type FROM canonical_instruments WHERE instrument_id=?",
                      (instrument_id,)).fetchone()
    return row[0] if row else "UNKNOWN_CONTRACT"


def _finalise(base, status, review_reason, raw, token, provider_id, source_timestamp):
    base = dict(base)
    base["mapping_status"] = status
    base["review_reason"] = review_reason
    base["automatically_resolved"] = status in (
        "EXACT_MATCH", "PROVIDER_ALIAS_MATCH", "NORMALISED_MATCH")
    # deterministic decision hash — canonical, non-volatile inputs only
    h = canonical_hash({
        "raw": raw, "token": token, "provider_id": provider_id, "ts": source_timestamp,
        "rules": base["mapping_rule_versions"], "cand_u": base["candidate_underlyings"],
        "cand_i": base["candidate_instruments"], "status": status,
        "sel_u": base["selected_underlying_id"], "sel_i": base["selected_instrument_id"]})
    base["canonical_decision_hash"] = h
    base["decision_id"] = "dec_" + h[:16]
    return base


def log_decision(db, decision, created_at=None):
    """Append a decision to mapping_decisions (append-only). JSON-encodes list fields."""
    import json
    rec = dict(decision)
    rec["candidate_underlyings"] = json.dumps(rec["candidate_underlyings"], sort_keys=True)
    rec["candidate_instruments"] = json.dumps(rec["candidate_instruments"], sort_keys=True)
    rec["mapping_rule_versions"] = json.dumps(rec["mapping_rule_versions"], sort_keys=True)
    rec["automatically_resolved"] = 1 if rec["automatically_resolved"] else 0
    rec["created_at"] = created_at
    rec["schema_version"] = "inst-1.0"
    cols = ("decision_id", "original_raw_symbol", "normalised_token", "provider_id",
            "source_platform", "source_message_id", "source_message_timestamp",
            "input_provenance", "candidate_underlyings", "candidate_instruments",
            "selected_underlying_id", "selected_instrument_id", "asset_class", "contract_type",
            "venue_contract", "mapping_status", "mapping_rule_versions", "rule_effective_from",
            "rule_effective_to", "review_reason", "automatically_resolved",
            "canonical_decision_hash", "created_at", "schema_version")
    return db._append("mapping_decisions", {c: rec.get(c) for c in cols})
