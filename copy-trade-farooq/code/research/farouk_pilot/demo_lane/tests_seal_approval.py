"""Tests for the one-shot sealing action (Chuck Correction 1). Proves inbox->immutable-store
sealing: validation, duplicate/overwrite rejection, atomic create-new, byte+sha verification,
sanitised receipt, and that the executor reads ONLY the sealed store (ignores the inbox).
Run:  python -m research.farouk_pilot.demo_lane.tests_seal_approval   (from repo root)
"""
import importlib
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))
dl = "research.farouk_pilot.demo_lane"
approval_tool = importlib.import_module(dl + ".approval_tool")
seal_approval = importlib.import_module(dl + ".seal_approval")

_p = _f = 0
def ck(n, c):
    global _p, _f
    print(("  ok  " if c else "FAIL  ") + n); _p += bool(c); _f += (not c)
def raises(t, e):
    try:
        t(); return False
    except e:
        return True

NOW = 1000
FAR = 10 ** 12


def make_candidate(inbox, campaign_id="XAU-DEMO-SEAL"):
    req = {"record_type": "DEMO_APPROVAL_REQUEST", "campaign_id": campaign_id, "t0_freeze_hash": "h0",
           "approved_account_id": 47758849, "symbol_id": "XAUUSD", "direction": "BUY",
           "entries": [4063.0, 4058.0, 4053.0], "stop": 4040.0, "volume_per_leg": 0.01,
           "max_aggregate_volume": 300, "source_message_ids": [1, 2], "executor_version_hash": "e",
           "approval_timestamp": NOW, "approval_expiry": FAR, "placement_deadline": FAR}
    _, approval = approval_tool.create_approval(req, inbox, "MARTYN_EXPLICIT_APPROVE", NOW)
    return approval


d = tempfile.mkdtemp(prefix="seal_test_")
inbox = os.path.join(d, "inbox"); store = os.path.join(d, "store"); receipts = os.path.join(d, "receipts")

# 1. seal a candidate from the inbox into the immutable store
cand = make_candidate(inbox)
rec = seal_approval.seal(cand, store, receipts, sealer_identity="svc-orange-sealer", now_ts=NOW)
sealed = seal_approval.executor_load_sealed(store)
ck("candidate seals into the immutable store", len(sealed) == 1)
ck("sealing receipt written with sha256", rec["sealed_sha256"] and len(rec["sealed_sha256"]) == 64)
ck("sealed record preserves plan_hash + approval_record_hash (executor can still validate)",
   sealed[0]["plan_hash"] == cand["plan_hash"] and sealed[0]["approval_record_hash"] == cand["approval_record_hash"])

# 2. duplicate campaign_id (different nonce) is rejected
cand_dupid = make_candidate(inbox)                      # same campaign_id, new nonce/hash
ck("duplicate campaign_id rejected", raises(lambda: seal_approval.seal(cand_dupid, store, receipts, "svc-orange-sealer", NOW), seal_approval.SealError))

# 3. replay / overwrite the exact same candidate is rejected (dup nonce/hash + create-new)
ck("replay of the same candidate rejected", raises(lambda: seal_approval.seal(cand, store, receipts, "svc-orange-sealer", NOW), seal_approval.SealError))

# 4. tampered candidate (plan mutated after hashing) fails validation
cand2 = make_candidate(inbox, campaign_id="XAU-DEMO-SEAL-2")
cand2["plan"]["stop"] = 3999.0                          # tamper
ck("tampered bound plan rejected (hash mismatch)", raises(lambda: seal_approval.seal(cand2, store, receipts, "svc-orange-sealer", NOW), seal_approval.SealError))

# 5. executor reads ONLY the sealed store, ignores the inbox
inbox_only = make_candidate(inbox, campaign_id="XAU-INBOX-ONLY")   # written to inbox, never sealed
store_ids = [(r.get("plan") or {}).get("campaign_id") for r in seal_approval.executor_load_sealed(store)]
ck("executor ignores the inbox (inbox-only candidate NOT in the sealed set)", "XAU-INBOX-ONLY" not in store_ids)
ck("inbox candidate exists on disk but is non-authoritative", os.path.isdir(inbox) and len(os.listdir(inbox)) >= 1)

# 6. receipt is sanitised (no secret material)
rtxt = json.dumps(rec)
ck("sealing receipt carries no secret", not any(x in rtxt for x in ("clientSecret", "accessToken", "password", "secret")))

# 7. a valid distinct campaign seals successfully (positive control)
cand3 = make_candidate(inbox, campaign_id="XAU-DEMO-SEAL-3")
r3 = seal_approval.seal(cand3, store, receipts, "svc-orange-sealer", NOW)
ck("a distinct valid campaign seals", r3["campaign_id"] == "XAU-DEMO-SEAL-3" and len(seal_approval.executor_load_sealed(store)) == 2)

print(f"\n{_p} passed, {_f} failed")
sys.exit(1 if _f else 0)
