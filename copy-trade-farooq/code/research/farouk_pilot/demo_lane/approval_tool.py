"""OPERATOR approval tool (F3 + ADDENDUM item 1). SEPARATE from the executor.
Writes immutable DEMO_APPROVED records into the approvals directory. Requires an explicit
Martyn action. Has NO order-placement capability (it imports no broker adapter).
In a real deploy the approvals dir has Windows ACLs: this tool's account can write it,
the executor's account cannot."""
import hashlib
import json
import os
import secrets

from . import config

APPROVED_TYPE = "DEMO_APPROVED"
REQUEST_TYPE = "DEMO_APPROVAL_REQUEST"
PLAN_FIELDS = (  # the fourteen bound plan fields (correction 4)
    "campaign_id", "t0_freeze_hash", "approved_account_id", "symbol_id", "direction",
    "entries", "stop", "volume_per_leg", "max_aggregate_volume", "source_message_ids",
    "executor_version_hash", "approval_timestamp", "approval_expiry", "placement_deadline")


def _plan_hash(plan):
    return hashlib.sha256(json.dumps({k: plan[k] for k in PLAN_FIELDS}, sort_keys=True,
                                     default=str).encode()).hexdigest()


def create_approval(request, approvals_dir, martyn_action, now_ts):
    """Create an immutable DEMO_APPROVED from a validated DEMO_APPROVAL_REQUEST.
    martyn_action MUST be the explicit human token — refuses without it (F3: human authority)."""
    if martyn_action != "MARTYN_EXPLICIT_APPROVE":
        raise PermissionError("approval requires explicit Martyn action")
    if request.get("record_type") != REQUEST_TYPE:
        raise ValueError("not a DEMO_APPROVAL_REQUEST")
    plan = {k: request[k] for k in PLAN_FIELDS}
    approval = {
        "record_type": APPROVED_TYPE,
        "plan": plan,
        "plan_hash": _plan_hash(plan),
        "nonce": secrets.token_hex(16),                 # single-use
        "approval_tool_version": config.APPROVAL_TOOL_VERSION,
        "expiry_ts": plan["approval_expiry"],
        "created_ts": now_ts,
        "lifecycle": "MARTYN_APPROVED",
    }
    approval["approval_record_hash"] = hashlib.sha256(
        json.dumps(approval, sort_keys=True, default=str).encode()).hexdigest()
    os.makedirs(approvals_dir, exist_ok=True)
    path = os.path.join(approvals_dir, f"{plan['campaign_id']}.{approval['nonce']}.approved.json")
    # write-once: O_CREAT|O_EXCL so an approval file is never silently overwritten (immutability)
    fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(approval, f)
    return path, approval
