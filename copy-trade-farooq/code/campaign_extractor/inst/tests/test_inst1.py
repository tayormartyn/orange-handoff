"""
INST-1 offline tests (A–S). Synthetic fixtures only; no real provider registered; no network;
no credentials. Farouk/MPK are read STRICTLY read-only for the protection/isolation tests.
"""
from __future__ import annotations
import hashlib
import os
import shutil
import sqlite3
import tempfile

import sys
_HERE = os.path.dirname(os.path.abspath(__file__))
_INST = os.path.dirname(_HERE)
_CE = os.path.dirname(_INST)
_ROOT = os.path.dirname(_CE)
for p in (_INST,):
    if p not in sys.path:
        sys.path.insert(0, p)

from _util import ro_connect, AppendOnlyViolation
from registry_db import InstrumentRegistryDB
from resolver import resolve, log_decision
import seed as SEED

INST_SOURCES = ("__init__.py", "_util.py", "registry_db.py", "normalize.py", "resolver.py",
                "seed.py", "run_inst1.py")
MPK_REGISTRY = os.path.join(_CE, "mpk", "data", "mpk_registry_v1.db")
MPK_CAMPAIGNS = os.path.join(_CE, "mpk", "data", "mpk_campaigns_v1.db")


def _seeded(tmp, name="r.db"):
    db = InstrumentRegistryDB(os.path.join(tmp, name))
    SEED.seed(db)
    return db


# ============================================================ A — gold formatting aliases
def test_A_gold_formatting_aliases():
    tmp = tempfile.mkdtemp(prefix="A_")
    try:
        db = _seeded(tmp)
        outs = [resolve(db, r) for r in ("XAUUSD", "xauusd", "XAU/USD", "XAU USD")]
        for d, raw in zip(outs, ("XAUUSD", "xauusd", "XAU/USD", "XAU USD")):
            assert d["original_raw_symbol"] == raw            # raw preserved
            assert d["selected_underlying_id"] == "underlying_gold"
            assert d["selected_instrument_id"] == "instrument_xauusd_spot_reference"
            assert d["venue_contract"] == "NOT_ROUTED"
        assert outs[0]["mapping_status"] == "EXACT_MATCH"
        assert all(o["mapping_status"] == "NORMALISED_MATCH" for o in outs[1:])
        db.close()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ============================================================ B — bare GOLD ambiguity
def test_B_bare_gold_ambiguous():
    tmp = tempfile.mkdtemp(prefix="B_")
    try:
        db = _seeded(tmp)
        d = resolve(db, "GOLD")
        assert d["selected_underlying_id"] == "underlying_gold"
        assert d["selected_instrument_id"] is None
        assert d["contract_type"] == "UNKNOWN_CONTRACT"
        assert d["mapping_status"] == "AMBIGUOUS_NEEDS_REVIEW"
        assert d["venue_contract"] == "NOT_ROUTED"
        db.close()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ============================================================ C — BTC ambiguity
def test_C_btc_ambiguous():
    tmp = tempfile.mkdtemp(prefix="C_")
    try:
        db = _seeded(tmp)
        for raw in ("BTC", "BITCOIN"):
            d = resolve(db, raw)
            assert d["selected_underlying_id"] == "underlying_btc"
            assert d["selected_instrument_id"] is None
            assert d["contract_type"] == "UNKNOWN_CONTRACT"
            assert d["mapping_status"] == "AMBIGUOUS_NEEDS_REVIEW"
            assert d["venue_contract"] == "NOT_ROUTED"
        db.close()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ============================================================ D — explicit BTC perpetual
def test_D_explicit_btc_perpetual():
    tmp = tempfile.mkdtemp(prefix="D_")
    try:
        db = _seeded(tmp)
        d = resolve(db, "BTC PERPETUAL")
        assert d["selected_instrument_id"] == "instrument_btcusd_perpetual"
        assert d["contract_type"] == "PERPETUAL"
        assert d["venue_contract"] == "NOT_ROUTED"
        assert d["mapping_status"] == "NORMALISED_MATCH"
        db.close()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ============================================================ E — provider-specific alias separation
def _add_provider_rule(db, provider, token, underlying, instrument):
    db._append("mapping_rules", db.rule(
        mapping_rule_uid=f"prule_{provider}_{token}_v1", rule_version=1, scope="PROVIDER",
        provider_id=provider, input_token=token, target_underlying_id=underlying,
        target_instrument_id=instrument, effective_from="2020-01-01T00:00:00Z",
        admin_reason="synthetic provider alias"))


def test_E_provider_specific_alias_separation():
    tmp = tempfile.mkdtemp(prefix="E_")
    try:
        db = _seeded(tmp)
        _add_provider_rule(db, "provider_synthA", "GLD", "underlying_gold",
                           "instrument_xauusd_cfd")
        da = resolve(db, "GLD", provider_id="provider_synthA")
        assert da["mapping_status"] == "PROVIDER_ALIAS_MATCH"
        assert da["selected_instrument_id"] == "instrument_xauusd_cfd"
        db_ = resolve(db, "GLD", provider_id="provider_synthB")    # B has no rule, no global GLD
        assert db_["mapping_status"] == "UNKNOWN_NEEDS_REVIEW"
        assert db_["selected_underlying_id"] is None
        db.close()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ============================================================ F — same underlying, distinct contracts
def test_F_same_underlying_distinct_contracts():
    tmp = tempfile.mkdtemp(prefix="F_")
    try:
        db = _seeded(tmp)
        rows = db.con.execute(
            "SELECT instrument_id, contract_type FROM canonical_instruments "
            "WHERE canonical_underlying_id='underlying_gold' ORDER BY instrument_id").fetchall()
        ids = {r[0] for r in rows}
        cts = {r[1] for r in rows}
        assert ids == {"instrument_xauusd_spot_reference", "instrument_xauusd_cfd",
                       "instrument_gold_future", "instrument_gold_perpetual"}
        assert cts == {"SPOT_REFERENCE", "CFD", "FUTURE", "PERPETUAL"}   # distinct contracts
        db.close()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ============================================================ G — OIL ambiguity
def test_G_oil_ambiguous():
    tmp = tempfile.mkdtemp(prefix="G_")
    try:
        db = _seeded(tmp)
        d = resolve(db, "OIL")
        assert d["candidate_underlyings"] == ["underlying_brent", "underlying_wti"]
        assert d["selected_underlying_id"] is None
        assert d["selected_instrument_id"] is None
        assert d["mapping_status"] == "AMBIGUOUS_NEEDS_REVIEW"
        db.close()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ============================================================ H — Silver ambiguity
def test_H_silver_ambiguous():
    tmp = tempfile.mkdtemp(prefix="H_")
    try:
        db = _seeded(tmp)
        d = resolve(db, "SILVER")
        assert d["selected_underlying_id"] == "underlying_silver"
        assert d["selected_instrument_id"] is None
        assert d["mapping_status"] == "AMBIGUOUS_NEEDS_REVIEW"
        db.close()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ============================================================ I — invalid / unsupported
def test_I_invalid_and_unknown():
    tmp = tempfile.mkdtemp(prefix="I_")
    try:
        db = _seeded(tmp)
        bad = resolve(db, "@@@##")
        assert bad["mapping_status"] == "REJECTED_INVALID"
        empty = resolve(db, "   ")
        assert empty["mapping_status"] == "REJECTED_INVALID"
        unknown = resolve(db, "ZZZZ")           # well-formed but unrecognised
        assert unknown["mapping_status"] == "UNKNOWN_NEEDS_REVIEW"
        for d in (bad, empty, unknown):
            assert d["selected_instrument_id"] is None and d["venue_contract"] == "NOT_ROUTED"
        db.close()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ============================================================ J — deterministic replay
def test_J_deterministic_replay():
    tmp = tempfile.mkdtemp(prefix="J_")
    try:
        db = _seeded(tmp)
        kw = dict(provider_id=None, source_timestamp="2024-03-01T00:00:00Z")
        d1 = resolve(db, "XAUUSD", **kw)
        d2 = resolve(db, "XAUUSD", **kw)
        assert d1["canonical_decision_hash"] == d2["canonical_decision_hash"]
        assert d1["decision_id"] == d2["decision_id"]
        db.close()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ============================================================ K — historical rule versioning
def test_K_historical_versioning():
    tmp = tempfile.mkdtemp(prefix="K_")
    try:
        db = _seeded(tmp)
        db._append("mapping_rules", db.rule(
            mapping_rule_uid="rule_VER_v1", rule_version=1, scope="GLOBAL", input_token="VER",
            target_underlying_id="underlying_gold", effective_from="2021-01-01T00:00:00Z",
            admin_reason="v1"))
        db._append("mapping_rules", db.rule(
            mapping_rule_uid="rule_VER_v2", rule_version=2, scope="GLOBAL", input_token="VER",
            target_underlying_id="underlying_silver", effective_from="2022-01-01T00:00:00Z",
            supersedes_rule_uid="rule_VER_v1", admin_reason="corrected to silver"))
        at_t1 = resolve(db, "VER", source_timestamp="2021-06-01T00:00:00Z")
        at_t3 = resolve(db, "VER", source_timestamp="2022-06-01T00:00:00Z")
        assert at_t1["selected_underlying_id"] == "underlying_gold"
        assert at_t3["selected_underlying_id"] == "underlying_silver"
        # a logged historical decision is append-only / unchanged by the new rule
        log_decision(db, at_t1, created_at="2021-06-01T00:00:00Z")
        again = resolve(db, "VER", source_timestamp="2021-06-01T00:00:00Z")
        assert again["selected_underlying_id"] == "underlying_gold"   # history not rewritten
        db.close()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ============================================================ L — no first-match selection
def _amb_db(tmp, name, order):
    db = InstrumentRegistryDB(os.path.join(tmp, name))
    SEED.seed(db)
    rules = {
        "cfd": db.rule(mapping_rule_uid="rule_AMB_cfd_v1", rule_version=1, scope="GLOBAL",
                       input_token="AMB", target_underlying_id="underlying_gold",
                       target_instrument_id="instrument_xauusd_cfd",
                       effective_from="2020-01-01T00:00:00Z", admin_reason="amb"),
        "fut": db.rule(mapping_rule_uid="rule_AMB_fut_v1", rule_version=1, scope="GLOBAL",
                       input_token="AMB", target_underlying_id="underlying_gold",
                       target_instrument_id="instrument_gold_future",
                       effective_from="2020-01-01T00:00:00Z", admin_reason="amb"),
    }
    for k in order:
        db._append("mapping_rules", rules[k])
    return db


def test_L_no_first_match_order_independent():
    tmp = tempfile.mkdtemp(prefix="L_")
    try:
        d1 = resolve(_amb_db(tmp, "a.db", ["cfd", "fut"]), "AMB")
        d2 = resolve(_amb_db(tmp, "b.db", ["fut", "cfd"]), "AMB")
        assert d1["mapping_status"] == "AMBIGUOUS_NEEDS_REVIEW"
        assert d1["selected_instrument_id"] is None
        assert d1["candidate_instruments"] == ["instrument_gold_future", "instrument_xauusd_cfd"]
        assert d1["candidate_instruments"] == d2["candidate_instruments"]
        assert d1["canonical_decision_hash"] == d2["canonical_decision_hash"]   # order-independent
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ============================================================ M — provider isolation
def test_M_provider_isolation():
    tmp = tempfile.mkdtemp(prefix="M_")
    try:
        db = _seeded(tmp)
        _add_provider_rule(db, "provider_synthA", "GLD", "underlying_gold", "instrument_xauusd_cfd")
        assert resolve(db, "GLD", provider_id="provider_synthA")["mapping_status"] == "PROVIDER_ALIAS_MATCH"
        assert resolve(db, "GLD", provider_id="provider_synthB")["mapping_status"] == "UNKNOWN_NEEDS_REVIEW"
        assert resolve(db, "GLD", provider_id=None)["mapping_status"] == "UNKNOWN_NEEDS_REVIEW"
        db.close()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ============================================================ N — append-only enforcement
def test_N_append_only_enforcement():
    tmp = tempfile.mkdtemp(prefix="N_")
    try:
        db = _seeded(tmp)
        log_decision(db, resolve(db, "GOLD"), created_at="2024-01-01")   # a decision row exists
        for stmt in ("UPDATE canonical_underlyings SET asset_class='UNKNOWN'",
                     "DELETE FROM canonical_underlyings",
                     "UPDATE mapping_rules SET target_underlying_id='x'",
                     "DELETE FROM mapping_rules",
                     "UPDATE mapping_decisions SET mapping_status='EXACT_MATCH'",
                     "DELETE FROM mapping_decisions"):
            try:
                db.con.execute(stmt)
                assert False, f"{stmt} should be rejected"
            except sqlite3.Error as e:
                assert "append-only" in str(e).lower()
        # correction = NEW rule version; old remains queryable
        db._append("mapping_rules", db.rule(
            mapping_rule_uid="rule_GOLD_correction_v2", rule_version=2, scope="GLOBAL",
            input_token="GOLD", target_underlying_id="underlying_gold",
            effective_from="2023-01-01T00:00:00Z", supersedes_rule_uid="rule_GOLD_gold_v1",
            admin_reason="example correction"))
        assert db.con.execute("SELECT COUNT(*) FROM mapping_rules WHERE input_token='GOLD'"
                              ).fetchone()[0] == 2
        db.close()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ============================================================ O — transaction rollback
def test_O_transaction_rollback():
    tmp = tempfile.mkdtemp(prefix="O_")
    try:
        db = InstrumentRegistryDB(os.path.join(tmp, "r.db"))
        # batch: one valid underlying + one instrument with an illegal contract_type (CHECK fail)
        good = ("canonical_underlyings", db.underlying(underlying_id="u_tmp",
                display_label="Tmp", asset_class="METAL"))
        bad = ("canonical_instruments", db.instrument(instrument_id="i_tmp",
               canonical_underlying_id="u_tmp", contract_type="NONSENSE"))
        try:
            db.append_many_atomic([good, bad])
            assert False, "expected CHECK violation"
        except sqlite3.IntegrityError:
            pass
        assert db.count("canonical_underlyings") == 0     # full rollback, nothing partial
        assert db.count("canonical_instruments") == 0
        db.close()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ============================================================ P — database isolation / deletion independence
def test_P_database_isolation_deletion_independence():
    tmp = tempfile.mkdtemp(prefix="P_")
    try:
        path = os.path.join(tmp, "instrument_registry_v1.db")
        db = InstrumentRegistryDB(path)
        SEED.seed(db)
        db.close()
        assert os.path.exists(path)
        os.remove(path)                                   # remove INST-1 entirely
        # MPK / Farouk remain usable & unchanged
        reg = ro_connect(MPK_REGISTRY, immutable=True)
        cam = ro_connect(MPK_CAMPAIGNS, immutable=True)
        try:
            assert reg.execute("SELECT COUNT(*) FROM providers WHERE provider_id="
                               "'provider_farouk_001'").fetchone()[0] == 1
            assert cam.execute("SELECT COUNT(*) FROM legacy_campaign_mapping").fetchone()[0] == 28
        finally:
            reg.close(); cam.close()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ============================================================ Q — Farouk protection
def test_Q_farouk_protection():
    reg = ro_connect(MPK_REGISTRY, immutable=True)
    cam = ro_connect(MPK_CAMPAIGNS, immutable=True)
    try:
        assert reg.execute("SELECT COUNT(*) FROM providers").fetchone()[0] == 1
        assert reg.execute("SELECT COUNT(*) FROM providers WHERE provider_id='provider_farouk_001'"
                           ).fetchone()[0] == 1
        total = cam.execute("SELECT COUNT(*) FROM legacy_campaign_mapping").fetchone()[0]
        mv = cam.execute("SELECT COUNT(*) FROM legacy_campaign_mapping "
                         "WHERE mapping_status='MAPPED_VERIFIED'").fetchone()[0]
        assert total == 28 and mv == 28
    finally:
        reg.close(); cam.close()


# ============================================================ R — no live wiring
def _inst_src(name):
    with open(os.path.join(_INST, name), encoding="utf-8") as f:
        return f.read()


def test_R_no_live_wiring():
    for live in ("module_a_telegram.py", "module_b_parser.py"):
        p = os.path.join(_ROOT, live)
        if os.path.exists(p):
            src = open(p, encoding="utf-8").read()
            assert "import inst" not in src and "from inst" not in src
    # INST-1 has no campaign creation and no venue/broker route
    for name in INST_SOURCES:
        src = _inst_src(name)
        for tok in ("place_order", "submit_order", "create_campaign", "campaigns_db",
                    "select_venue", "route("):
            assert tok not in src, f"{name} has forbidden token {tok!r}"


# ============================================================ S — no credential / network access
def test_S_no_credential_or_network():
    forbidden = ("CTRADER", "ctrader", "dotenv", "os.environ", "getenv", "HYPERLIQUID",
                 "hyperliquid", "private_key", "WALLET", "seed_phrase", "SIGNING_KEY",
                 "broker_readonly", "import socket", "import ssl", "urllib", "requests",
                 "websocket", "anthropic", "ACCESS_TOKEN", "CLIENT_SECRET")
    for name in INST_SOURCES:
        src = _inst_src(name)
        for tok in forbidden:
            assert tok not in src, f"{name} has forbidden token {tok!r}"
