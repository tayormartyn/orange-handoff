"""
Rights gate — FAIL CLOSED. An asset may be processed for a given step ONLY when its rights record
exists, its rights_status is APPROVED, and the specific permission needed for that step is explicitly
True. A false, unknown, or missing permission refuses processing. This is a mechanical record + rule;
it makes NO legal conclusions.
"""
from __future__ import annotations

import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)
from schemas.pilot_schemas import RIGHTS_STATUS_APPROVED, PERMISSION_FIELDS


def rights_permit(rights_record, permission):
    """Return (permitted, reason). Fail closed. `permission` is one of PERMISSION_FIELDS."""
    if permission not in PERMISSION_FIELDS:
        return False, "UNKNOWN_PERMISSION:" + str(permission)
    if not isinstance(rights_record, dict) or not rights_record:
        return False, "RIGHTS_RECORD_MISSING"
    status = rights_record.get("rights_status")
    if status != RIGHTS_STATUS_APPROVED:
        return False, "RIGHTS_STATUS_NOT_APPROVED:" + str(status or "MISSING")
    val = rights_record.get(permission)
    if val is not True:
        return False, "PERMISSION_FALSE_OR_UNKNOWN:" + permission
    return True, None


def _coerce_bool(v):
    """CSV values arrive as strings; only an explicit truthy token is True (fail closed on blank/unknown)."""
    if isinstance(v, bool):
        return v
    if isinstance(v, str):
        return v.strip().lower() in ("true", "yes", "y", "1")
    return False


def normalize_rights_row(row):
    """Coerce a CSV rights row into a typed rights record (permission strings -> bool)."""
    r = dict(row)
    for p in PERMISSION_FIELDS:
        r[p] = _coerce_bool(row.get(p))
    return r
