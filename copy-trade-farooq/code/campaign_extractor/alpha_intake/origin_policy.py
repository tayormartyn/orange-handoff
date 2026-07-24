"""
Autonomous-origin policy for the Alpha->QST intake. FAIL CLOSED. An autonomous Alpha module is a
DISTINCT origin from any external human provider route: it has no provider route, no broker route, no
execution authority, and NO inherited authorisation from sea-scalper-farouk. Attempting to present an
external-provider identity or the sea-scalper-farouk route is rejected. Allowed modes are RESEARCH /
REPLAY / SHADOW only; PAPER / DEMO / LIVE are rejected (this adapter never enables execution).
"""
from __future__ import annotations

AUTONOMOUS_KIND = "AUTONOMOUS_ALPHA"
ALLOWED_MODES = ("RESEARCH", "REPLAY", "SHADOW")
REJECTED_MODES = ("PAPER", "DEMO", "LIVE")

# the external provider route this adapter must NEVER reuse / impersonate / inherit from
EXTERNAL_PROVIDER_ROUTE = "sea-scalper-farouk"
EXTERNAL_TRANSPORT_ID = "-1001937743421"        # The Whale Room transport (never an autonomous route)

# any of these appearing anywhere in the origin/payload is treated as external-provider spoofing
_SPOOF_TOKENS = ("sea-scalper-farouk", "seascalperfarouk", "-1001937743421", "whale room",
                 "the whale room", "provider_route", "external_provider")


def check_origin(origin, generated_in_mode, *, raw_payload=None):
    """Return (ok, reason_codes). Fail closed. `origin` is the proposal's origin object; `raw_payload`
    (optional) is the full proposal dict, scanned defensively for route-spoof tokens."""
    codes = []
    if not isinstance(origin, dict):
        return False, ["ORIGIN_MISSING"]
    kind = origin.get("kind")
    module_id = origin.get("moduleId")

    if kind != AUTONOMOUS_KIND:
        codes.append("ORIGIN_NOT_AUTONOMOUS")
    if not isinstance(module_id, str) or not module_id.strip():
        codes.append("MODULE_ID_MISSING")

    # mode gating
    if generated_in_mode in REJECTED_MODES:
        codes.append("MODE_NOT_PERMITTED")          # PAPER / DEMO / LIVE
    elif generated_in_mode not in ALLOWED_MODES:
        codes.append("MODE_UNSUPPORTED")

    # external-provider / route spoofing — fail closed on ANY sign of it
    hay = []
    if isinstance(module_id, str):
        hay.append(module_id.lower())
    for k in ("providerRoute", "provider_route", "route", "brokerRoute", "transportId", "sourceRoom"):
        if k in origin:
            codes.append("EXTERNAL_PROVIDER_ROUTE_PRESENT")
            hay.append(str(origin[k]).lower())
    if raw_payload is not None:
        for k in ("providerRoute", "provider_route", "route", "brokerRoute", "sourceRoom",
                  "source_room", "transportId"):
            if k in raw_payload:
                codes.append("EXTERNAL_PROVIDER_ROUTE_PRESENT")
                hay.append(str(raw_payload[k]).lower())
    blob = " ".join(hay)
    if any(tok in blob for tok in _SPOOF_TOKENS):
        codes.append("EXTERNAL_PROVIDER_ROUTE_SPOOF")

    codes = sorted(set(codes))
    return (not codes), codes


def origin_record(origin, generated_in_mode):
    """Safe, execution-free descriptor of the autonomous origin for the audit record."""
    return {
        "origin_kind": (origin or {}).get("kind"),
        "autonomous_module_id": (origin or {}).get("moduleId"),
        "generated_in_mode": generated_in_mode,
        "provider_route": None,          # autonomous origin has NO provider route
        "broker_route": None,            # ...NO broker route
        "inherited_from_sea_scalper_farouk": False,
        "execution_authority": False,    # explicit: never any execution authority
    }
