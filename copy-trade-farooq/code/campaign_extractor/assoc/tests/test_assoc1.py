"""
ASSOC-1 offline tests (A–V). Synthetic snapshots + temp DBs only. MPK read strictly
read-only. No network, no credentials, no live wiring, no campaign mutation.
"""
from __future__ import annotations
import hashlib
import os
import shutil
import sqlite3
import tempfile

import sys
_HERE = os.path.dirname(os.path.abspath(__file__))
_ASSOC = os.path.dirname(_HERE)
_CE = os.path.dirname(_ASSOC)
_ROOT = os.path.dirname(_CE)
if _ASSOC not in sys.path:
    sys.path.insert(0, _ASSOC)

from _util import ro_connect
import model as M
from model import ManagementCandidate, CampaignSnapshot
from engine import associate
from decisions_db import AssociationDecisionsDB
from scan import scan_no_mutation

MPK_REGISTRY = os.path.join(_CE, "mpk", "data", "mpk_registry_v1.db")
MPK_CAMPAIGNS = os.path.join(_CE, "mpk", "data", "mpk_campaigns_v1.db")
ASSOC_SOURCES = ("__init__.py", "_util.py", "model.py", "engine.py", "decisions_db.py",
                 "scan.py", "run_assoc1.py")
TS = "2026-06-01T00:00:00Z"


def cand(**kw):
    base = dict(source_message_uid="m1", provider_id="provA",
                management_intent="MOVE_STOP_TO_ENTRY", source_message_timestamp=TS,
                immutable_channel_id="ch1", provider_tracking_status_at_message_time="TRACKED_PROVIDER",
                source_identity_approved=True)
    base.update(kw)
    return ManagementCandidate(**base)


def camp(uid, **kw):
    base = dict(campaign_uid=uid, provider_id="provA", lifecycle_status="OPEN")
    base.update(kw)
    return CampaignSnapshot(**base)


# ===================================================== A — explicit campaign reference
def test_A_explicit_reference():
    cs = [camp("c1", provider_campaign_reference="REF1")]
    d = associate(cand(explicit_campaign_reference="REF1"), cs)
    assert d["association_status"] == "ASSOCIATED"
    assert d["rule_fired"] == M.RULE_1 and d["evidence_tier"] == M.TIER_1
    assert d["associated_campaign_uid"] == "c1"
    # direct campaign_uid reference also works
    d2 = associate(cand(explicit_campaign_reference="c1"), cs)
    assert d2["associated_campaign_uid"] == "c1"


# ===================================================== B — reply linkage
def test_B_reply_linkage():
    cs = [camp("c1", linked_message_uids=("sig1", "ev1"))]
    d = associate(cand(reply_to_message_uid="ev1"), cs)
    assert d["association_status"] == "ASSOCIATED" and d["rule_fired"] == M.RULE_2


# ===================================================== C — quoted identity
def test_C_quoted_identity():
    cs = [camp("c1", linked_message_uids=("sig1",))]
    d = associate(cand(quoted_message_uid="sig1"), cs)
    assert d["association_status"] == "ASSOCIATED" and d["rule_fired"] == M.RULE_3


# ===================================================== D — explicit instrument + unique
def test_D_explicit_instrument_unique():
    cs = [camp("g", canonical_underlying_id="underlying_gold"),
          camp("b", canonical_underlying_id="underlying_btc")]
    d = associate(cand(explicit_instrument_underlying="underlying_gold"), cs)
    assert d["association_status"] == "ASSOCIATED" and d["rule_fired"] == M.RULE_4
    assert d["associated_campaign_uid"] == "g"


# ===================================================== E — two open, bare instruction
def test_E_two_open_bare_needs_review():
    cs = [camp("g", canonical_underlying_id="underlying_gold"),
          camp("b", canonical_underlying_id="underlying_btc")]
    d = associate(cand(), cs)        # bare "Move SL to entry"
    assert d["association_status"] == "NEEDS_REVIEW"
    assert d["candidate_campaign_uids"] == ["b", "g"]
    assert d["associated_campaign_uid"] is None


# ===================================================== F — most-recent-trade trap
def test_F_most_recent_trade_trap():
    cs = [camp("c_old", opened_at="2026-05-01T00:00:00Z"),
          camp("c_new", opened_at="2026-05-31T00:00:00Z")]   # closest to message ts
    d = associate(cand(), cs)
    assert d["association_status"] == "NEEDS_REVIEW"
    assert d["associated_campaign_uid"] is None               # recency never selects
    assert set(d["candidate_campaign_uids"]) == {"c_old", "c_new"}


# ===================================================== G — provider mismatch
def test_G_provider_mismatch():
    cs = [camp("cB", provider_id="provB", provider_campaign_reference="REFB")]
    d = associate(cand(explicit_campaign_reference="REFB"), cs)
    assert d["association_status"] == "REJECTED_PROVIDER_MISMATCH"
    assert d["associated_campaign_uid"] is None
    assert cs[0].lifecycle_status == "OPEN"                   # provider B campaign untouched


# ===================================================== H — untracked provider
def test_H_untracked_provider():
    for st in ("DENIED", "REVIEW_REQUIRED"):
        d = associate(cand(provider_tracking_status_at_message_time=st), [camp("c1")])
        assert d["association_status"] == "REJECTED_UNTRACKED_PROVIDER"
        assert d["rule_fired"] == M.RULE_NONE


# ===================================================== I — valid Rule 6 fallback
def test_I_valid_fallback():
    d = associate(cand(), [camp("c1")])
    assert d["association_status"] == "ASSOCIATED" and d["rule_fired"] == M.RULE_6
    assert d["evidence_tier"] == M.TIER_6 and "fallback" in d["review_reason"]


# ===================================================== J — fallback blocked by multiple
def test_J_fallback_blocked_multiple():
    d = associate(cand(), [camp("c1"), camp("c2")])
    assert d["association_status"] == "NEEDS_REVIEW"
    assert d["candidate_campaign_uids"] == ["c1", "c2"]


# ===================================================== K — zero campaigns
def test_K_zero_campaigns():
    d = associate(cand(), [])
    assert d["association_status"] == "UNASSOCIATED"
    assert d["associated_campaign_uid"] is None


# ===================================================== L — risk-free claim
def test_L_risk_free_claim_no_execution():
    d = associate(cand(management_intent="RISK_FREE_CLAIM"), [camp("c1")])
    assert d["association_status"] == "ASSOCIATED"
    assert d["instruction_executed"] is False and d["broker_confirmed"] is False
    for k in ("realised_r", "realized_r", "stop_moved", "pnl", "zero_loss"):
        assert k not in d                                    # asserts no execution/result


# ===================================================== M — TP1 report
def test_M_tp1_report_no_fill():
    before = len([camp("c1")])
    cs = [camp("c1")]
    d = associate(cand(management_intent="TP_HIT_REPORTED"), cs)
    assert d["association_status"] == "ASSOCIATED"
    assert d["instruction_executed"] is False and d["broker_confirmed"] is False
    assert "realised_r" not in d
    assert len(cs) == before and cs[0].lifecycle_status == "OPEN"   # no entry/mutation


# ===================================================== N — retrospective closed campaign
def test_N_retrospective_closed():
    cs = [camp("c1", lifecycle_status="CLOSED", linked_message_uids=("sig1",))]
    d = associate(cand(reply_to_message_uid="sig1", management_intent="STOP_HIT_REPORTED"), cs)
    assert d["association_status"] == "ASSOCIATED" and d["rule_fired"] == M.RULE_2
    assert d["association_context"] == "RETROSPECTIVE_EVIDENCE"
    assert cs[0].lifecycle_status == "CLOSED"                # not reopened


# ===================================================== O — Rule 4 vs Rule 6 labelling
def test_O_rule4_vs_rule6_distinct():
    r4 = associate(cand(explicit_instrument_underlying="underlying_gold"),
                   [camp("g", canonical_underlying_id="underlying_gold")])
    r6 = associate(cand(), [camp("c1")])
    assert r4["rule_fired"] == M.RULE_4 and r4["evidence_tier"] == M.TIER_4
    assert r6["rule_fired"] == M.RULE_6 and r6["evidence_tier"] == M.TIER_6
    assert r4["rule_fired"] != r6["rule_fired"]


# ===================================================== P — deterministic replay
def test_P_deterministic_replay():
    cs = [camp("g", canonical_underlying_id="underlying_gold"),
          camp("b", canonical_underlying_id="underlying_btc")]
    d1 = associate(cand(explicit_instrument_underlying="underlying_gold"), cs)
    d2 = associate(cand(explicit_instrument_underlying="underlying_gold"), cs)
    assert d1["decision_hash"] == d2["decision_hash"]
    assert d1["association_decision_uid"] == d2["association_decision_uid"]


# ===================================================== Q — candidate-order independence
def test_Q_order_independence():
    g = camp("g", canonical_underlying_id="underlying_gold")
    b = camp("b", canonical_underlying_id="underlying_btc")
    d1 = associate(cand(), [g, b])
    d2 = associate(cand(), [b, g])
    assert d1["association_status"] == d2["association_status"] == "NEEDS_REVIEW"
    assert d1["candidate_campaign_uids"] == d2["candidate_campaign_uids"]
    assert d1["rule_fired"] == d2["rule_fired"]
    assert d1["decision_hash"] == d2["decision_hash"]


# ===================================================== R — append-only decision storage
def test_R_append_only_storage():
    tmp = tempfile.mkdtemp(prefix="assocR_")
    try:
        db = AssociationDecisionsDB(os.path.join(tmp, "d.db"))
        d = associate(cand(), [camp("c1")])
        db.append(d, created_at="2026-06-01")
        assert db.count() == 1
        for stmt in ("UPDATE association_decisions SET association_status='UNASSOCIATED'",
                     "DELETE FROM association_decisions"):
            try:
                db.con.execute(stmt); raise AssertionError("should be rejected")
            except sqlite3.Error as e:
                assert "append-only" in str(e).lower()
        # correction = NEW row with supersedes
        db.append(d, created_at="2026-06-02", supersedes_decision_uid=d["association_decision_uid"],
                  correction_reason="human re-review", review_provenance="martyn")
        assert db.count() == 2
        db.close()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ===================================================== S — no mutation path
def test_S_no_mutation_path():
    tmp = tempfile.mkdtemp(prefix="assocS_")
    try:
        # a synthetic campaign snapshot DB — ASSOC-1 must never touch it
        cdb = os.path.join(tmp, "campaigns_snapshot.db")
        con = sqlite3.connect(cdb)
        con.execute("CREATE TABLE campaigns (campaign_uid TEXT, lifecycle_status TEXT)")
        con.execute("INSERT INTO campaigns VALUES ('c1','OPEN')")
        con.commit(); con.close()
        before = hashlib.sha256(open(cdb, "rb").read()).hexdigest()
        associate(cand(), [camp("c1")])               # uses in-memory snapshot, not the DB
        after = hashlib.sha256(open(cdb, "rb").read()).hexdigest()
        assert before == after
        # source/dependency scan over executable engine code
        assert scan_no_mutation([_ASSOC]) == []
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ===================================================== T — Farouk protection
def test_T_farouk_protection():
    reg = ro_connect(MPK_REGISTRY, immutable=True)
    cam = ro_connect(MPK_CAMPAIGNS, immutable=True)
    try:
        assert reg.execute("SELECT COUNT(*) FROM providers WHERE provider_id='provider_farouk_001'"
                           ).fetchone()[0] == 1
        assert cam.execute("SELECT COUNT(*) FROM legacy_campaign_mapping WHERE "
                           "mapping_status='MAPPED_VERIFIED'").fetchone()[0] == 28
    finally:
        reg.close(); cam.close()


# ===================================================== U — no live wiring
def test_U_no_live_wiring():
    for live in ("module_a_telegram.py", "module_b_parser.py"):
        p = os.path.join(_ROOT, live)
        if os.path.exists(p):
            src = open(p, encoding="utf-8").read()
            assert "import assoc" not in src and "from assoc" not in src


# ===================================================== V — no credential / broker access
def _src(name):
    with open(os.path.join(_ASSOC, name), encoding="utf-8") as f:
        return f.read()


def test_V_no_credential_or_broker():
    forbidden = ("CTRADER", "ctrader", "dotenv", "os.environ", "getenv", "HYPERLIQUID",
                 "hyperliquid", "private_key", "WALLET", "SIGNING_KEY", "ACCESS_TOKEN",
                 "CLIENT_SECRET", "import socket", "import ssl", "urllib", "requests",
                 "websocket", "anthropic", "broker_readonly")
    # scan.py is the BLOCKLIST module: it names forbidden identifiers as STRING-LITERAL data.
    # Those are not imports/usage (the token-level scan_no_mutation, which DOES cover scan.py,
    # proves they are STRING tokens, never NAME/import tokens). Per spec §10 the substring
    # check targets non-scanner executable code; the scanner is verified at token level below.
    for name in ASSOC_SOURCES:
        if name == "scan.py":
            continue
        src = _src(name)
        for tok in forbidden:
            assert tok not in src, f"{name} has forbidden token {tok!r}"
    assert scan_no_mutation([_ASSOC]) == []      # token-level: covers scan.py (executable code)


# ----- fixture census (for the report counts) -----
def census():
    scenarios = {
        "A": associate(cand(explicit_campaign_reference="REF1"),
                       [camp("c1", provider_campaign_reference="REF1")]),
        "B": associate(cand(reply_to_message_uid="ev1"),
                       [camp("c1", linked_message_uids=("ev1",))]),
        "C": associate(cand(quoted_message_uid="sig1"),
                       [camp("c1", linked_message_uids=("sig1",))]),
        "D": associate(cand(explicit_instrument_underlying="underlying_gold"),
                       [camp("g", canonical_underlying_id="underlying_gold"),
                        camp("b", canonical_underlying_id="underlying_btc")]),
        "E": associate(cand(), [camp("g", canonical_underlying_id="underlying_gold"),
                                camp("b", canonical_underlying_id="underlying_btc")]),
        "F": associate(cand(), [camp("c_old", opened_at="2026-05-01T00:00:00Z"),
                                camp("c_new", opened_at="2026-05-31T00:00:00Z")]),
        "G": associate(cand(explicit_campaign_reference="REFB"),
                       [camp("cB", provider_id="provB", provider_campaign_reference="REFB")]),
        "H": associate(cand(provider_tracking_status_at_message_time="DENIED"), [camp("c1")]),
        "I": associate(cand(), [camp("c1")]),
        "J": associate(cand(), [camp("c1"), camp("c2")]),
        "K": associate(cand(), []),
        "L": associate(cand(management_intent="RISK_FREE_CLAIM"), [camp("c1")]),
        "M": associate(cand(management_intent="TP_HIT_REPORTED"), [camp("c1")]),
        "N": associate(cand(reply_to_message_uid="sig1", management_intent="STOP_HIT_REPORTED"),
                       [camp("c1", lifecycle_status="CLOSED", linked_message_uids=("sig1",))]),
        "O1": associate(cand(explicit_instrument_underlying="underlying_gold"),
                        [camp("g", canonical_underlying_id="underlying_gold")]),
        "O2": associate(cand(), [camp("c1")]),
    }
    tally = {}
    for d in scenarios.values():
        tally[d["association_status"]] = tally.get(d["association_status"], 0) + 1
    return tally, scenarios
