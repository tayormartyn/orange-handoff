"""ASSOC-1R offline tests (A–L). Read-only over live evidence; isolated replay DB only."""
from __future__ import annotations
import hashlib
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_AR = os.path.dirname(_HERE)
_CE = os.path.dirname(_AR)
_ROOT = os.path.dirname(_CE)
_ASSOC = os.path.join(_CE, "assoc")
for p in (_AR, _ASSOC):
    if p not in sys.path:
        sys.path.insert(0, p)

import provenance
import replay as R
from candidates import classify, FAROUK, CHANNEL
from model import CampaignSnapshot, OPEN

ROWS = provenance.load_live_rows()
BY_ID = {r["message_id"]: r for r in ROWS}
PROTECTED = [
    os.path.join(_ROOT, "campaign_extractor", "prospective", "data", "prospective_evidence_v1.db"),
    os.path.join(_ROOT, "campaign_extractor", "mpk", "data", "mpk_registry_v1.db"),
    os.path.join(_ROOT, "campaign_extractor", "mpk", "data", "mpk_campaigns_v1.db"),
    os.path.join(_ROOT, "campaign_extractor", "inst", "data", "instrument_registry_v1.db"),
    os.path.join(_ROOT, "campaign_extractor", "assoc", "data", "association_decisions_v1.db"),
    os.path.join(_ROOT, "data", "signal_archive.db"),
]


def _dec(mid, **kw):
    return R.build_decisions([BY_ID[mid]], **kw)[0]


# ===================================================== A — live provenance reconciliation
def test_A_live_provenance():
    assert len(ROWS) == 15
    ids = [r["message_id"] for r in ROWS]
    assert ids[0] == "45331" and ids[-1] == "45345"
    for r in ROWS:
        assert r["provenance"] == "LIVE_CAPTURED"
        if r["raw_text"]:                       # text rows carry a real hash
            assert r["raw_text_hash"] and len(r["raw_text_hash"]) == 64
    assert all(f["provenance"] == "MANUAL_SCREENSHOT_FIXTURE"
               for f in provenance.MANUAL_SCREENSHOT_FIXTURES)


# ===================================================== B — TP1 message association
def test_B_tp1_association():
    ctype, intent, meta = classify(BY_ID["45333"])     # "60 pips tp 1 now"
    assert ctype == "MANAGEMENT" and intent == "TP_HIT_REPORTED"
    assert "intent_ambiguity" in meta                  # not silently resolved
    d = _dec("45333")["decision"]
    assert d["association_status"] == "ASSOCIATED" and d["rule_fired"].startswith("RULE_6")


# ===================================================== C — stop-to-entry association
def test_C_stop_to_entry():
    d = _dec("45334")["decision"]                      # "sl to entry"
    assert d["association_status"] == "ASSOCIATED" and d["rule_fired"].startswith("RULE_6")
    assert R.EPHEMERAL_GOLD.lifecycle_status == OPEN   # no stop/lifecycle mutation


# ===================================================== D — unspecified TP instruction
def test_D_tp_now_unspecified():
    res = _dec("45335")                                # "Tp now!!!"
    assert res["intent"] == "TP_HIT_REPORTED"
    assert res["metadata"]["close_fraction"] is None and res["metadata"]["target"] == "UNSPECIFIED"
    assert res["decision"]["association_status"] == "ASSOCIATED"


# ===================================================== E — partial-close message
def test_E_partial_close():
    res = _dec("45340")                                # "I'm closing 0.5 lot now!!! 150 pips"
    assert res["candidate_type"] == "MANAGEMENT" and res["intent"] == "PARTIAL_CLOSE_INSTRUCTION"
    assert res["metadata"]["provider_reported_amount"] == "0.5 lot"
    assert res["metadata"]["provider_claimed_distance"] == "150 pips"
    assert res["metadata"]["exact_fill"] is None and res["metadata"]["broker_confirmed"] is False
    assert res["decision"]["association_status"] == "ASSOCIATED"


# ===================================================== F — analysis-only isolation
def test_F_analysis_only():
    for mid in ("45336", "45341"):                     # rationale + London liquidity/buy zone
        res = _dec(mid)
        assert res["candidate_type"] == "ANALYSIS_ONLY"
        assert res["decision"]["association_status"] == "UNASSOCIATED"   # no management, no campaign


# ===================================================== G — follower isolation
def test_G_follower_isolation():
    res = _dec("45337")                                # "Should we close the limit orders..."
    assert res["candidate_type"] == "FOLLOWER"
    assert res["decision"]["association_status"] == "REJECTED_UNTRACKED_PROVIDER"
    assert res["decision"]["associated_campaign_uid"] is None


# ===================================================== H — most-recent-trade protection
def test_H_second_campaign_needs_review():
    btc = CampaignSnapshot(campaign_uid="ephemeral_farouk_btc", provider_id=FAROUK,
                           lifecycle_status=OPEN, canonical_underlying_id="underlying_btc",
                           direction="LONG", origin_channel_id=CHANNEL,
                           opened_at="2026-06-29T15:36:00+00:00")
    res = R.build_decisions([BY_ID["45334"]], campaigns=[R.EPHEMERAL_GOLD, btc])[0]
    d = res["decision"]
    assert d["association_status"] == "NEEDS_REVIEW"
    assert d["associated_campaign_uid"] is None        # recency must not select
    assert set(d["candidate_campaign_uids"]) == {"ephemeral_farouk_xauusd_20260630",
                                                  "ephemeral_farouk_btc"}


# ===================================================== I — decision-only / no mutation
def _sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest() if os.path.exists(p) else None


def test_I_no_mutation():
    before = {p: _sha(p) for p in PROTECTED}
    R.run(write_db=True)                               # writes ONLY to the isolated replay DB
    after = {p: _sha(p) for p in PROTECTED}
    assert before == after


# ===================================================== J — deterministic replay
def test_J_deterministic_replay():
    d1 = {r["message_id"]: (r["decision"] or {}).get("decision_hash")
          for r in R.build_decisions(ROWS)}
    d2 = {r["message_id"]: (r["decision"] or {}).get("decision_hash")
          for r in R.build_decisions(ROWS)}
    assert d1 == d2
    rev = {r["message_id"]: (r["decision"] or {}).get("decision_hash")
           for r in R.build_decisions(list(reversed(ROWS)))}
    assert rev == d1                                    # order-independent


# ===================================================== K — manual/live provenance separation
def test_K_manual_live_separation():
    live_ids = {r["message_id"] for r in ROWS}
    manual = provenance.MANUAL_SCREENSHOT_FIXTURES
    # manual fixtures are distinct entries (never merged into a single sum)
    floats = [f["value"] for f in manual if f["image_only_field"] == "floating_profit"]
    assert floats == ["831.00", "1239.00", "1457.00"]
    assert len(floats) == 3                             # three separate snapshots, not one total
    assert all(f["fixture_id"] not in live_ids for f in manual)
    assert all(f["broker_confirmed"] is False for f in manual)


# ===================================================== L — no broker claims
def test_L_no_broker_claims():
    for r in R.build_decisions(ROWS):
        d = r["decision"]
        if d is None:
            continue
        assert d["instruction_executed"] is False and d["broker_confirmed"] is False
        for k in ("fill_price", "broker_ticket", "realised_r", "realized_r", "quote", "pnl",
                  "position_volume"):
            assert k not in d
