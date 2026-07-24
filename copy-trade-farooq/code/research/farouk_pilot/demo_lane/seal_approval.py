"""One-shot SEALING action (Chuck Correction 1). Runs as a TRUSTED NON-APPROVER identity.

Promotes a Martyn-approved CANDIDATE from the APPROVAL_INBOX into the IMMUTABLE_APPROVAL_STORE:
  * validate the candidate + recompute the full bound-plan hash AND the approval-record hash;
  * reject duplicate campaign_id / nonce / approval-record hash (already sealed);
  * create the final record ATOMICALLY with create-new semantics (O_CREAT|O_EXCL - never overwrite);
  * verify the final bytes + SHA-256 match what was intended;
  * write a SANITISED sealing receipt (campaign_id, nonce, hashes, sha256, sealer identity - the
    approval carries no secret, and none is added).
Ownership assignment + the immutable ACL are installed at the OS layer by the provisioning tool
(Provision-OrangeAcl.ps1); this module never mutates a sealed record and adds nothing to its bytes,
so the executor's plan_hash / approval_record_hash validation keeps holding on the sealed record.
The approver never runs this; the executor reads ONLY the immutable store, never the inbox.
"""
import hashlib
import json
import os

from .approval_tool import APPROVED_TYPE, PLAN_FIELDS, _plan_hash


class SealError(Exception):
    pass


def _record_hash(approval):
    return hashlib.sha256(json.dumps({k: approval[k] for k in approval if k != "approval_record_hash"},
                                     sort_keys=True, default=str).encode()).hexdigest()


def validate_candidate(candidate):
    if candidate.get("record_type") != APPROVED_TYPE:
        raise SealError("candidate is not a DEMO_APPROVED record")
    if candidate.get("lifecycle") != "MARTYN_APPROVED":
        raise SealError("candidate lifecycle is not MARTYN_APPROVED")
    plan = candidate.get("plan") or {}
    missing = [k for k in PLAN_FIELDS if k not in plan]
    if missing:
        raise SealError(f"candidate plan missing bound fields: {missing}")
    if _plan_hash(plan) != candidate.get("plan_hash"):
        raise SealError("bound-plan hash mismatch")
    if _record_hash(candidate) != candidate.get("approval_record_hash"):
        raise SealError("approval_record_hash mismatch (candidate tampered)")
    return plan


def _sealed_index(store_dir):
    ids, nonces, hashes = set(), set(), set()
    if os.path.isdir(store_dir):
        for fn in os.listdir(store_dir):
            if fn.endswith(".sealed.json"):
                try:
                    rec = json.load(open(os.path.join(store_dir, fn), encoding="utf-8"))
                except (OSError, json.JSONDecodeError):
                    continue
                ids.add((rec.get("plan") or {}).get("campaign_id"))
                nonces.add(rec.get("nonce"))
                hashes.add(rec.get("approval_record_hash"))
    return ids, nonces, hashes


def seal(candidate, store_dir, receipt_dir, sealer_identity, now_ts):
    """Seal a validated candidate into the immutable store. Returns the sanitised receipt."""
    plan = validate_candidate(candidate)
    cid, nonce, rhash = plan["campaign_id"], candidate["nonce"], candidate["approval_record_hash"]
    ids, nonces, hashes = _sealed_index(store_dir)
    if cid in ids or nonce in nonces or rhash in hashes:
        raise SealError("duplicate: campaign_id / nonce / approval-record hash already sealed")
    os.makedirs(store_dir, exist_ok=True)
    os.makedirs(receipt_dir, exist_ok=True)
    # the sealed record is the candidate VERBATIM (canonical bytes) - nothing added, so the
    # executor's plan_hash / approval_record_hash validation keeps holding.
    payload = json.dumps(candidate, sort_keys=True, default=str).encode("utf-8")
    final_path = os.path.join(store_dir, f"{cid}.{nonce}.sealed.json")
    try:
        fd = os.open(final_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)   # atomic create-NEW
    except FileExistsError:
        raise SealError("a sealed record with this campaign_id.nonce already exists (no overwrite)")
    with os.fdopen(fd, "wb") as f:
        f.write(payload)
    on_disk = open(final_path, "rb").read()
    if on_disk != payload:
        raise SealError("post-write byte mismatch")
    sealed_sha = hashlib.sha256(on_disk).hexdigest()
    receipt = {"record_type": "DEMO_SEALING_RECEIPT", "campaign_id": cid, "nonce": nonce,
               "plan_hash": candidate["plan_hash"], "approval_record_hash": rhash,
               "sealed_sha256": sealed_sha, "sealed_ts": now_ts, "sealer_identity": sealer_identity,
               "final_file": os.path.basename(final_path)}
    with open(os.path.join(receipt_dir, f"{cid}.{nonce}.receipt.json"), "w", encoding="utf-8") as f:
        json.dump(receipt, f)
    return receipt


def executor_load_sealed(store_dir):
    """The executor reads ONLY the immutable store (never the inbox). Returns the sealed records."""
    out = []
    if os.path.isdir(store_dir):
        for fn in sorted(os.listdir(store_dir)):
            if fn.endswith(".sealed.json"):
                out.append(json.load(open(os.path.join(store_dir, fn), encoding="utf-8")))
    return out
