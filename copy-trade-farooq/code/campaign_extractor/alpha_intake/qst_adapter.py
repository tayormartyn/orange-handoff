"""
Alpha -> QUALIFIED_STRIKE_AND_TRAP shadow intake adapter. SHADOW ONLY. Validates an AlphaSignalProposal
JSON, enforces the autonomous-origin + price policies, maps the Alpha vocabulary to the existing QST
intake vocabulary, and (optionally, only if a quote context is supplied) invokes the PURE, side-effect-
free strike_trap.route() for a shadow qualification record. Returns only the minimal QstIntakeAck.

It NEVER: reuses/impersonates sea-scalper-farouk, creates a broker route, enables paper/demo/live
execution, submits/amends/cancels/closes orders, determines account risk, sizes lots, allocates
60/25/15, modifies risk_policy.py or any execution gate, or imports any broker/order-sending/order-
management module. It does not compute risk; strike_trap.route()/qualify() do not take a stop or size.
"""
from __future__ import annotations
import os
import sys

from . import schemas as SCHEMAS
from . import origin_policy as OP
from . import price_policy as PP

ADAPTER_VERSION = "1.0.0"
CONFIG_VERSION = "alpha-intake-1.0.0"

# explicit vocabulary maps (no silent mapping)
DIRECTION_MAP = {"LONG": "BUY", "SHORT": "SELL"}
# EntryType -> the closest EXISTING QST routing vocabulary. STOP_ON_BREAK has NO native QST primitive
# (QST routes passive-ladder / inside-zone market-range strike only) -> flagged, never silently coerced.
ENTRY_TYPE_MAP = {
    "MARKET_ON_TRIGGER": "INSIDE_ZONE_MARKET_RANGE_STRIKE",
    "LIMIT_IN_ZONE": "PASSIVE_LIMIT_IN_ZONE",
    "STOP_ON_BREAK": None,           # no exact QST equivalent -> ENTRY_TYPE_NO_QST_EQUIVALENT warning
}


class Reject(Exception):
    def __init__(self, reason_code, detail=None):
        self.reason_code = reason_code
        self.detail = detail
        super().__init__(reason_code)


def _ack(accepted, reason_code, idempotency_key):
    """The ONLY thing that crosses back: the minimal QstIntakeAck. No fills/orders/sizing/route/auth."""
    return {"accepted": bool(accepted), "reasonCode": reason_code, "idempotencyKey": idempotency_key}


def _iso_to_ms(iso):
    import calendar
    import time as _t
    s = iso.replace("Z", "").split(".")[0]
    return int(calendar.timegm(_t.strptime(s, "%Y-%m-%dT%H:%M:%S"))) * 1000


def _pure_route(*, direction_qst, low, high, quote_ctx, provider_ts_ms, now_ms):
    """Invoke the PURE, side-effect-free strike_trap.route() for a shadow routing outcome. Imported
    lazily; strike_trap imports only its config (no I/O, no broker, no permit/lease)."""
    sc = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "shadow_campaign")
    de = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "demo_executor")
    for p in (sc, de):
        if p not in sys.path:
            sys.path.insert(0, p)
    import strike_trap as ST
    r = ST.route(direction=direction_qst, low=low, high=high, quote=quote_ctx["quote"],
                 quote_path=quote_ctx.get("quote_path", []), provider_ts_ms=provider_ts_ms,
                 now_ms=now_ms, quote_health_state=quote_ctx.get("quote_health_state", "QUOTES_SILENT"))
    return {"routing_mode": r.get("routing_mode"), "blockers": r.get("blocking_reasons") or r.get("blockers", [])}


def evaluate(proposal, *, now_ms, quote_ctx=None, seen_idempotency_keys=None, price_config=None):
    """Shadow evaluation of one AlphaSignalProposal (a dict). Returns
    {ack, shadow_qualification_record, audit}. now_ms = received time (ms). quote_ctx (optional) enables
    the pure route() shadow qualification. seen_idempotency_keys = a set for duplicate detection."""
    ik = proposal.get("idempotencyKey") if isinstance(proposal, dict) else None
    audit = {"adapter_version": ADAPTER_VERSION, "config_version": CONFIG_VERSION,
             "received_ts_ms": now_ms, "execution_authority": False, "schema_version": None,
             "signal_id": None, "idempotency_key": ik, "autonomous_module_id": None,
             "observed_ts": None, "expiry_ts": None, "price_audit": [], "mapping": {},
             "qualification_outcome": None, "rejection_reason": None, "mapping_warnings": [],
             "semantic_notes": []}
    warnings = []
    try:
        # 1. schema (strict, forbidden fields, expiry refinement)
        try:
            SCHEMAS.validate_proposal(proposal)
        except SCHEMAS.SchemaError as e:
            rc = {"FORBIDDEN_FIELD": "FORBIDDEN_FIELD", "UNKNOWN_FIELD": "UNKNOWN_FIELD",
                  "UNSUPPORTED_INSTRUMENT": "UNSUPPORTED_INSTRUMENT",
                  "UNSUPPORTED_SCHEMA_VERSION": "UNSUPPORTED_SCHEMA_VERSION",
                  "EXPIRES_NOT_AFTER_OBSERVED": "EXPIRES_NOT_AFTER_OBSERVED"}.get(e.code, "MALFORMED")
            raise Reject(rc, str(e))
        audit["schema_version"] = proposal["schemaVersion"]
        audit["signal_id"] = proposal["signalId"]
        audit["autonomous_module_id"] = proposal["origin"].get("moduleId")
        audit["observed_ts"] = proposal["observedAt"]
        audit["expiry_ts"] = proposal["expiresAt"]

        # 2. origin policy (autonomous only; RESEARCH/REPLAY/SHADOW; no sea-scalper-farouk)
        ok, codes = OP.check_origin(proposal["origin"], proposal["generatedInMode"], raw_payload=proposal)
        audit["origin"] = OP.origin_record(proposal["origin"], proposal["generatedInMode"])
        if not ok:
            if "MODE_NOT_PERMITTED" in codes or "MODE_UNSUPPORTED" in codes:
                raise Reject("UNSUPPORTED_MODE", ",".join(codes))
            if any(c.startswith("EXTERNAL_PROVIDER_ROUTE") for c in codes):
                raise Reject("EXTERNAL_PROVIDER_ROUTE_REJECTED", ",".join(codes))
            raise Reject("ORIGIN_REJECTED", ",".join(codes))

        # 3. expiry (received time must be before expiry)
        exp_ms = _iso_to_ms(proposal["expiresAt"])
        if now_ms >= exp_ms:
            raise Reject("EXPIRED", f"now {now_ms} >= expiry {exp_ms}")

        # 4. price policy — parse every boundary price (decimal strings only), keep audit
        entry = proposal["entry"]
        price_fields = {"zoneLow": entry["zoneLow"], "zoneHigh": entry["zoneHigh"],
                        "maxChasePrice": entry["maxChasePrice"], "invalidationPrice": proposal["invalidationPrice"]}
        for i, o in enumerate(proposal["objectives"]):
            price_fields[f"objective[{i}]"] = o["price"]
        parsed = {}
        try:
            for fld, raw in price_fields.items():
                rec = PP.parse_and_check(raw, field=fld, config=price_config)
                audit["price_audit"].append(rec)
                parsed[fld] = rec
        except PP.PricePolicyError as e:
            raise Reject("PRICE_POLICY_VIOLATION", str(e))

        # 5. mapping (explicit; flag mismatches, never silent)
        direction_qst = DIRECTION_MAP[proposal["direction"]]
        entry_route = ENTRY_TYPE_MAP[entry["entryType"]]
        if entry_route is None:
            warnings.append("ENTRY_TYPE_NO_QST_EQUIVALENT:" + entry["entryType"])
        # invalidation -> structural stop: QST route()/qualify() do NOT consume a stop; QST provider_stop
        # is a RISK-SIZING field owned downstream. We record invalidation as a STRUCTURAL stop only and
        # DO NOT feed it into any risk conversion (no conversion invented).
        audit["semantic_notes"].append(
            "invalidationPrice mapped to STRUCTURAL stop only; QST provider_stop is a risk-sizing field "
            "owned by risk_policy (downstream). No risk conversion performed by the adapter.")
        mapping = {"instrument": proposal["instrument"], "direction_qst": direction_qst,
                   "entry_route_hint": entry_route, "zone_low": parsed["zoneLow"]["downstream_float"],
                   "zone_high": parsed["zoneHigh"]["downstream_float"],
                   "structural_stop_from_invalidation": parsed["invalidationPrice"]["downstream_float"],
                   "structural_stop_is_risk_sized": False,
                   "targets": [parsed[f"objective[{i}]"]["downstream_float"] for i in range(len(proposal["objectives"]))]}
        audit["mapping"] = mapping
        audit["mapping_warnings"] = warnings

        # 6. duplicate check (idempotency)
        if seen_idempotency_keys is not None and ik in seen_idempotency_keys:
            audit["qualification_outcome"] = "DUPLICATE"
            return {"ack": _ack(True, "DUPLICATE", ik),
                    "shadow_qualification_record": {"routing_mode": "NOT_RE_EVALUATED_DUPLICATE",
                                                    "mapping": mapping, "warnings": warnings},
                    "audit": audit}

        # 7. PURE shadow qualification (only if a quote context is supplied; route() is side-effect-free)
        shadow = {"routing_mode": "NOT_EVALUATED_NO_QUOTE_CONTEXT", "blockers": [], "mapping": mapping,
                  "warnings": warnings, "shadow_only": True, "executable_campaign": False}
        if quote_ctx is not None:
            provider_ts_ms = _iso_to_ms(proposal["effectiveMarketTime"])
            routed = _pure_route(direction_qst=direction_qst, low=mapping["zone_low"],
                                 high=mapping["zone_high"], quote_ctx=quote_ctx,
                                 provider_ts_ms=provider_ts_ms, now_ms=now_ms)
            shadow.update({"routing_mode": routed["routing_mode"], "blockers": routed["blockers"]})
        audit["qualification_outcome"] = shadow["routing_mode"]

        if seen_idempotency_keys is not None:
            seen_idempotency_keys.add(ik)
        return {"ack": _ack(True, "ACCEPTED", ik), "shadow_qualification_record": shadow, "audit": audit}

    except Reject as r:
        audit["rejection_reason"] = r.reason_code + (f":{r.detail}" if r.detail else "")
        audit["qualification_outcome"] = "REJECTED_AT_INTAKE"
        return {"ack": _ack(False, r.reason_code, ik), "shadow_qualification_record": None, "audit": audit}
