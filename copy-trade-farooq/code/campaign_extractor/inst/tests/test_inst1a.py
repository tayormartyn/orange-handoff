"""
INST-1A tests — semantic-duplicate hardening. Synthetic fixtures only; temp DBs for all
mutation; MPK read strictly read-only. No network, no credentials.
"""
from __future__ import annotations
import os
import shutil
import sqlite3
import tempfile

import sys
_HERE = os.path.dirname(os.path.abspath(__file__))
_INST = os.path.dirname(_HERE)
_CE = os.path.dirname(_INST)
_ROOT = os.path.dirname(_CE)
if _INST not in sys.path:
    sys.path.insert(0, _INST)

from _util import ro_connect
from registry_db import InstrumentRegistryDB
from resolver import resolve
import seed as SEED
import migrate_inst1a as MIG

MPK_REGISTRY = os.path.join(_CE, "mpk", "data", "mpk_registry_v1.db")
MPK_CAMPAIGNS = os.path.join(_CE, "mpk", "data", "mpk_campaigns_v1.db")
EFF = "2020-01-01T00:00:00Z"


def _seeded(tmp, name="r.db"):
    db = InstrumentRegistryDB(os.path.join(tmp, name))
    SEED.seed(db)
    return db


def _rule(db, uid, token, u, i=None, scope="GLOBAL", provider=None, version=1,
          effective_from=EFF, effective_to=None, supersedes=None):
    return db.rule(mapping_rule_uid=uid, rule_version=version, scope=scope, provider_id=provider,
                   input_token=token, target_underlying_id=u, target_instrument_id=i,
                   effective_from=effective_from, effective_to=effective_to,
                   supersedes_rule_uid=supersedes, admin_reason="test")


# ===================================================== A — different UUID, same global rule
def test_A_global_semantic_duplicate_rejected():
    tmp = tempfile.mkdtemp(prefix="1aA_")
    try:
        db = _seeded(tmp)
        before = db.con.execute("SELECT COUNT(*) FROM mapping_rules WHERE input_token='OIL' "
                                "AND target_underlying_id='underlying_wti'").fetchone()[0]
        try:
            db._append("mapping_rules", _rule(db, "rule_OIL_wti_DUP", "OIL", "underlying_wti"))
            assert False, "semantic duplicate should be rejected"
        except sqlite3.IntegrityError:
            pass
        after = db.con.execute("SELECT COUNT(*) FROM mapping_rules WHERE input_token='OIL' "
                               "AND target_underlying_id='underlying_wti'").fetchone()[0]
        assert before == 1 and after == 1               # first row unchanged, no partial
        db.close()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ===================================================== B — legitimate global ambiguity
def test_B_legitimate_global_ambiguity():
    tmp = tempfile.mkdtemp(prefix="1aB_")
    try:
        db = _seeded(tmp)
        d = resolve(db, "OIL")
        assert d["candidate_underlyings"] == ["underlying_brent", "underlying_wti"]
        assert d["selected_underlying_id"] is None and d["selected_instrument_id"] is None
        assert d["mapping_status"] == "AMBIGUOUS_NEEDS_REVIEW"
        db.close()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ===================================================== C — NULL effective_to does not bypass
def test_C_null_effective_to_no_bypass():
    tmp = tempfile.mkdtemp(prefix="1aC_")
    try:
        db = _seeded(tmp)
        db._append("mapping_rules", _rule(db, "rule_ZED_a", "ZED", "underlying_gold",
                                          effective_to=None))
        try:
            db._append("mapping_rules", _rule(db, "rule_ZED_b", "ZED", "underlying_gold",
                                              effective_to=None))
            assert False, "duplicate open-ended rule should be rejected"
        except sqlite3.IntegrityError:
            pass
        assert db.con.execute("SELECT COUNT(*) FROM mapping_rules WHERE input_token='ZED'"
                              ).fetchone()[0] == 1
        db.close()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ===================================================== D — nullable target columns
def test_D_nullable_target_columns():
    tmp = tempfile.mkdtemp(prefix="1aD_")
    try:
        db = _seeded(tmp)
        db._append("mapping_rules", _rule(db, "rule_ZTD_a", "ZTD", "underlying_gold", i=None))
        try:
            db._append("mapping_rules", _rule(db, "rule_ZTD_b", "ZTD", "underlying_gold", i=None))
            assert False, "identical (underlying, NULL instrument) should be rejected"
        except sqlite3.IntegrityError:
            pass
        # different target instrument kind remains distinct -> allowed
        db._append("mapping_rules", _rule(db, "rule_ZTD_c", "ZTD", "underlying_gold",
                                          i="instrument_xauusd_cfd"))
        assert db.con.execute("SELECT COUNT(*) FROM mapping_rules WHERE input_token='ZTD'"
                              ).fetchone()[0] == 2
        db.close()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ===================================================== E — provider-specific duplicate
def test_E_provider_duplicate_rejected():
    tmp = tempfile.mkdtemp(prefix="1aE_")
    try:
        db = _seeded(tmp)
        db._append("mapping_rules", _rule(db, "rule_pA_GLDX_a", "GLDX", "underlying_gold",
                                          scope="PROVIDER", provider="provider_synthA"))
        try:
            db._append("mapping_rules", _rule(db, "rule_pA_GLDX_b", "GLDX", "underlying_gold",
                                              scope="PROVIDER", provider="provider_synthA"))
            assert False, "provider semantic duplicate should be rejected"
        except sqlite3.IntegrityError:
            pass
        db.close()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ===================================================== F — provider separation preserved
def test_F_provider_separation_allowed():
    tmp = tempfile.mkdtemp(prefix="1aF_")
    try:
        db = _seeded(tmp)
        db._append("mapping_rules", _rule(db, "rule_pA_PSEP", "PSEP", "underlying_gold",
                                          scope="PROVIDER", provider="provider_synthA"))
        db._append("mapping_rules", _rule(db, "rule_pB_PSEP", "PSEP", "underlying_silver",
                                          scope="PROVIDER", provider="provider_synthB"))
        assert db.con.execute("SELECT COUNT(*) FROM mapping_rules WHERE input_token='PSEP'"
                              ).fetchone()[0] == 2
        assert resolve(db, "PSEP", provider_id="provider_synthA")["selected_underlying_id"] == "underlying_gold"
        assert resolve(db, "PSEP", provider_id="provider_synthB")["selected_underlying_id"] == "underlying_silver"
        db.close()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ===================================================== G — global vs provider separation
def test_G_global_and_provider_coexist():
    tmp = tempfile.mkdtemp(prefix="1aG_")
    try:
        db = _seeded(tmp)
        db._append("mapping_rules", _rule(db, "rule_g_GVP", "GVP", "underlying_gold"))
        db._append("mapping_rules", _rule(db, "rule_pA_GVP", "GVP", "underlying_gold",
                                          scope="PROVIDER", provider="provider_synthA"))
        assert db.con.execute("SELECT COUNT(*) FROM mapping_rules WHERE input_token='GVP'"
                              ).fetchone()[0] == 2
        # provider context uses provider rule; no-provider uses global — both resolve underlying_gold
        assert resolve(db, "GVP", provider_id="provider_synthA")["mapping_status"] == "AMBIGUOUS_NEEDS_REVIEW"
        assert resolve(db, "GVP")["mapping_status"] == "AMBIGUOUS_NEEDS_REVIEW"
        db.close()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ===================================================== H — database-order independence
def _ord_db(tmp, name, order):
    db = _seeded(tmp, name)
    rules = {"wti": _rule(db, "rule_ORD_wti", "ORD", "underlying_wti"),
             "brent": _rule(db, "rule_ORD_brent", "ORD", "underlying_brent")}
    for k in order:
        db._append("mapping_rules", rules[k])
    return db


def test_H_order_independence():
    tmp = tempfile.mkdtemp(prefix="1aH_")
    try:
        d1 = resolve(_ord_db(tmp, "a.db", ["wti", "brent"]), "ORD")
        d2 = resolve(_ord_db(tmp, "b.db", ["brent", "wti"]), "ORD")
        assert d1["candidate_underlyings"] == d2["candidate_underlyings"] == \
            ["underlying_brent", "underlying_wti"]
        assert d1["mapping_status"] == d2["mapping_status"] == "AMBIGUOUS_NEEDS_REVIEW"
        assert d1["canonical_decision_hash"] == d2["canonical_decision_hash"]
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ===================================================== I — migration rerun (idempotent + fail-closed)
def _old_schema_db(path, rows):
    con = sqlite3.connect(path)
    con.execute("""CREATE TABLE mapping_rules (mapping_rule_uid TEXT PRIMARY KEY,
        rule_version INTEGER, scope TEXT, provider_id TEXT, input_token TEXT,
        target_underlying_id TEXT, target_instrument_id TEXT, effective_from TEXT,
        effective_to TEXT, admin_reason TEXT, supersedes_rule_uid TEXT, created_at TEXT,
        schema_version TEXT, row_hash TEXT)""")
    con.execute("CREATE UNIQUE INDEX ux_rule_version ON mapping_rules "
                "(input_token, scope, provider_id, rule_version)")
    con.executemany("INSERT INTO mapping_rules (mapping_rule_uid, rule_version, scope, "
                    "provider_id, input_token, target_underlying_id, target_instrument_id, "
                    "effective_from, row_hash) VALUES (?,?,?,?,?,?,?,?,?)", rows)
    con.commit(); con.close()


def test_I_migration_idempotent_and_failclosed():
    tmp = tempfile.mkdtemp(prefix="1aI_")
    try:
        clean = os.path.join(tmp, "clean.db")
        _old_schema_db(clean, [
            ("u1", 1, "GLOBAL", None, "OIL", "underlying_wti", None, EFF, "h1"),
            ("u2", 1, "GLOBAL", None, "OIL", "underlying_brent", None, EFF, "h2")])
        r1 = MIG.migrate(clean)
        r2 = MIG.migrate(clean)
        assert r1["status"] == "MIGRATED" and r1["index_present"]
        assert r2["status"] == "ALREADY_APPLIED" and r2["index_present"]
        # exactly one semantic index, data unchanged
        con = sqlite3.connect(clean)
        assert con.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='index' AND name="
                           "'ux_rule_semantic'").fetchone()[0] == 1
        assert con.execute("SELECT COUNT(*) FROM mapping_rules").fetchone()[0] == 2
        con.close()
        # fail-closed: a DB with a pre-existing semantic dup is BLOCKED, index NOT created
        dup = os.path.join(tmp, "dup.db")
        _old_schema_db(dup, [
            ("u1", 1, "GLOBAL", None, "OIL", "underlying_wti", None, EFF, "h1"),
            ("u2", 1, "GLOBAL", None, "OIL", "underlying_wti", None, EFF, "h2")])
        rb = MIG.migrate(dup)
        assert rb["status"] == "BLOCKED" and rb["duplicate_groups"] == 1
        con = sqlite3.connect(dup)
        assert con.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='index' AND name="
                           "'ux_rule_semantic'").fetchone()[0] == 0   # not created
        assert con.execute("SELECT COUNT(*) FROM mapping_rules").fetchone()[0] == 2  # unchanged
        con.close()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ===================================================== J — full INST-1 regression
def test_J_full_inst1_regression():
    sys.path.insert(0, _HERE)
    import test_inst1 as T1
    tests = sorted(n for n in dir(T1) if n.startswith("test_"))
    for name in tests:
        getattr(T1, name)()
    assert len(tests) == 19


# ===================================================== K — database isolation
def test_K_database_isolation():
    reg = ro_connect(MPK_REGISTRY, immutable=True)
    cam = ro_connect(MPK_CAMPAIGNS, immutable=True)
    try:
        assert reg.execute("SELECT COUNT(*) FROM providers WHERE provider_id='provider_farouk_001'"
                           ).fetchone()[0] == 1
        assert cam.execute("SELECT COUNT(*) FROM legacy_campaign_mapping WHERE "
                           "mapping_status='MAPPED_VERIFIED'").fetchone()[0] == 28
    finally:
        reg.close(); cam.close()
