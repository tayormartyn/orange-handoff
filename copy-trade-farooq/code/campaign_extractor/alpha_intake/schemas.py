"""
Versioned Python validation schema mirroring the alpha-contracts AlphaSignalProposal JSON shape
(schemaVersion 1.0.0). Pure stdlib, strict: rejects unknown top-level fields, forbidden execution/
account/route fields, malformed enums/timestamps, and the expiry refinements. This validates SHAPE
only — origin, price, mapping and (pure) qualification are handled by the sibling modules.
"""
from __future__ import annotations
import re

SUPPORTED_SCHEMA_VERSION = "1.0.0"
SUPPORTED_INSTRUMENTS = ("XAUUSD",)             # this adapter is XAUUSD-only by policy

# allowed top-level keys (mirrors AlphaSignalProposal). Unknown keys are rejected (strict).
ALLOWED_TOP_LEVEL = frozenset({
    "schemaVersion", "signalId", "idempotencyKey", "origin", "instrument", "direction", "setupFamily",
    "observedAt", "effectiveMarketTime", "expiresAt", "campaignKey", "entry", "invalidationPrice",
    "objectives", "triggerConfirmed", "marketSnapshotRef", "featureSnapshotRef", "evidenceQuality",
    "decisionTrace", "reproducibility", "generatedInMode",
})

# forbidden fields — presence anywhere (top-level or nested) is a hard rejection (mirrors the TS denylist)
FORBIDDEN_KEYS = frozenset({
    "lotSize", "positionSize", "volume", "units", "accountId", "accountIdentifier", "riskPercent",
    "riskPercentage", "brokerRoute", "brokerCredentials", "credentials", "apiKey", "accessToken",
    "orderId", "brokerOrderId", "executionPermission", "canExecute", "authorised", "authorized",
    "route", "fillPrice", "filledLots", "executed",
})

DIRECTIONS = ("LONG", "SHORT")
SETUP_FAMILIES = ("OPENING_RANGE_BREAKOUT", "FAILED_BREAKOUT", "LIQUIDITY_SWEEP_RECLAIM",
                  "BREAK_AND_RETEST", "MOMENTUM_CONTINUATION", "MOMENTUM_REVERSAL", "OTHER")
ENTRY_TYPES = ("MARKET_ON_TRIGGER", "LIMIT_IN_ZONE", "STOP_ON_BREAK")
MODES = ("RESEARCH", "REPLAY", "SHADOW", "PAPER", "DEMO", "LIVE")

_ISO_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?Z$")
_UUID_RE = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")


class SchemaError(ValueError):
    def __init__(self, code, path=None, detail=None):
        self.code = code
        self.path = path
        self.detail = detail
        super().__init__(f"{code}" + (f" at {path}" if path else "") + (f": {detail}" if detail else ""))


def _find_forbidden(obj, path="$"):
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in FORBIDDEN_KEYS:
                return f"{path}.{k}"
            hit = _find_forbidden(v, f"{path}.{k}")
            if hit:
                return hit
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            hit = _find_forbidden(v, f"{path}[{i}]")
            if hit:
                return hit
    return None


def _req(d, key, path):
    if key not in d:
        raise SchemaError("MISSING_FIELD", f"{path}.{key}")
    return d[key]


def _iso(v, path):
    if not isinstance(v, str) or not _ISO_RE.match(v):
        raise SchemaError("INVALID_TIMESTAMP", path, v)
    return v


def validate_proposal(proposal):
    """Validate the proposal dict against the 1.0.0 schema. Raises SchemaError on any violation;
    returns the proposal unchanged on success. Pure — no side effects."""
    if not isinstance(proposal, dict):
        raise SchemaError("NOT_AN_OBJECT")
    # forbidden fields first (defence in depth, nested)
    hit = _find_forbidden(proposal)
    if hit:
        raise SchemaError("FORBIDDEN_FIELD", hit)
    # strict: no unknown top-level keys
    unknown = set(proposal) - ALLOWED_TOP_LEVEL
    if unknown:
        raise SchemaError("UNKNOWN_FIELD", "$", ",".join(sorted(unknown)))

    if _req(proposal, "schemaVersion", "$") != SUPPORTED_SCHEMA_VERSION:
        raise SchemaError("UNSUPPORTED_SCHEMA_VERSION", "$.schemaVersion", proposal.get("schemaVersion"))
    if not _UUID_RE.match(str(_req(proposal, "signalId", "$"))):
        raise SchemaError("INVALID_SIGNAL_ID", "$.signalId")
    ik = _req(proposal, "idempotencyKey", "$")
    if not isinstance(ik, str) or not (8 <= len(ik) <= 256):
        raise SchemaError("INVALID_IDEMPOTENCY_KEY", "$.idempotencyKey")

    origin = _req(proposal, "origin", "$")
    if not isinstance(origin, dict):
        raise SchemaError("INVALID_ORIGIN", "$.origin")

    if _req(proposal, "instrument", "$") not in SUPPORTED_INSTRUMENTS:
        raise SchemaError("UNSUPPORTED_INSTRUMENT", "$.instrument", proposal.get("instrument"))
    if _req(proposal, "direction", "$") not in DIRECTIONS:
        raise SchemaError("INVALID_DIRECTION", "$.direction", proposal.get("direction"))
    if _req(proposal, "setupFamily", "$") not in SETUP_FAMILIES:
        raise SchemaError("INVALID_SETUP_FAMILY", "$.setupFamily", proposal.get("setupFamily"))

    observed = _iso(_req(proposal, "observedAt", "$"), "$.observedAt")
    _iso(_req(proposal, "effectiveMarketTime", "$"), "$.effectiveMarketTime")
    expires = _iso(_req(proposal, "expiresAt", "$"), "$.expiresAt")
    if expires <= observed:                          # ISO-8601 UTC strings sort chronologically
        raise SchemaError("EXPIRES_NOT_AFTER_OBSERVED", "$.expiresAt")

    _req(proposal, "campaignKey", "$")
    entry = _req(proposal, "entry", "$")
    if not isinstance(entry, dict):
        raise SchemaError("INVALID_ENTRY", "$.entry")
    if _req(entry, "entryType", "$.entry") not in ENTRY_TYPES:
        raise SchemaError("INVALID_ENTRY_TYPE", "$.entry.entryType", entry.get("entryType"))
    for k in ("zoneLow", "zoneHigh", "maxChasePrice"):
        _req(entry, k, "$.entry")
    _req(proposal, "invalidationPrice", "$")
    objs = _req(proposal, "objectives", "$")
    if not isinstance(objs, list):
        raise SchemaError("INVALID_OBJECTIVES", "$.objectives")
    for i, o in enumerate(objs):
        if not isinstance(o, dict) or "label" not in o or "price" not in o:
            raise SchemaError("INVALID_OBJECTIVE", f"$.objectives[{i}]")
    if not isinstance(_req(proposal, "triggerConfirmed", "$"), bool):
        raise SchemaError("INVALID_TRIGGER_CONFIRMED", "$.triggerConfirmed")
    for k in ("marketSnapshotRef", "featureSnapshotRef", "decisionTrace", "reproducibility",
              "evidenceQuality"):
        _req(proposal, k, "$")
    if _req(proposal, "generatedInMode", "$") not in MODES:
        raise SchemaError("INVALID_MODE", "$.generatedInMode", proposal.get("generatedInMode"))
    return proposal
