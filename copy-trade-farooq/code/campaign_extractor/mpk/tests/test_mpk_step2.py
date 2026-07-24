"""
MPK-1 Step 2 — offline tests (Farouk registration + signed-off-28 mapping).

State-changing tests use TEMP databases or temp legacy fixtures. Tests that assert the
real canonical state read the persistent DBs that run_step2 populated (read-only). The
legacy archive is only ever read mode=ro. No network, no credentials, no live wiring.
"""
from __future__ import annotations
import hashlib
import json
import os
import shutil
import sqlite3
import tempfile

import sys
_HERE = os.path.dirname(os.path.abspath(__file__))
_MPK = os.path.dirname(_HERE)
_CE = os.path.dirname(_MPK)
_ROOT = os.path.dirname(_CE)
for p in (_MPK, _CE):
    if p not in sys.path:
        sys.path.insert(0, p)

from appendonly import ro_connect
from registry_db import RegistryDB
from campaigns_db import CampaignsDB
import init_db
import step2_register_and_map as S2
import legacy_projection
from step2_register_and_map import Step2Block

LOCKED = {
    "prompt": "95bbf6a4b18ebdd7fc4db2a3e1449ab2e7b7e65a7cf16da461d8ea251a802ef4",
    "j17": "c8b1c3ebfb46441e113570f798e951ffce35829c4e4b50a052f9c2b8eba20339",
    "j24": "a230ce7a704b2d301a00451f91c472a30a77f042dbabd9e47c1888ae3bcba4a2",
    "j25": "22041d7aeb06bd373c21e23cab42eaf8d422b4913625da518bd3dd6d4c649bce",
}
MPK_SOURCES = ("__init__.py", "appendonly.py", "registry_db.py", "campaigns_db.py",
               "init_db.py", "legacy_readonly.py", "step2_register_and_map.py",
               "legacy_projection.py", "run_step1.py", "run_step2.py")
ARCHIVE = os.path.join(_ROOT, "data", "signal_archive.db")


# ---- temp helpers ----
def _make_temp_legacy(path, keys, provider=S2.FAROUK_ALIAS):
    con = sqlite3.connect(path)
    con.execute("""CREATE TABLE signals (signal_id TEXT, source_message_key TEXT,
        source_signal_index INTEGER, provider TEXT, asset TEXT, asset_class TEXT, direction TEXT,
        entry_low TEXT, entry_high TEXT, stop TEXT, tp1 TEXT, tp2 TEXT, tp3 TEXT,
        classification TEXT)""")
    con.execute("""CREATE TABLE outcome_projections (signal_id TEXT, outcome_category TEXT,
        binary_rollup TEXT, calculated_r TEXT, r_is_known INTEGER)""")
    for i, k in enumerate(keys):
        sid = f"sig-{i:03d}"
        con.execute("INSERT INTO signals VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (sid, k, 0, provider, "XAUUSD", "", "SHORT", "4000", "4010", "4030",
                     "3990", None, None, "clean signal"))
        con.execute("INSERT INTO outcome_projections VALUES (?,?,?,?,?)",
                    (sid, "target_hit", "win", "0.17", 1))
    con.commit(); con.close()


def _fresh_mpk(tmp):
    return (os.path.join(tmp, "mpk_registry_v1.db"), os.path.join(tmp, "mpk_campaigns_v1.db"))


# ============================================================ Test 1 — provider registration
def test_1_provider_registration_identity_and_idempotency():
    # persistent state: exactly one provider_farouk_001
    con = ro_connect(init_db.REGISTRY_DB_PATH, immutable=False)
    try:
        assert con.execute("SELECT COUNT(*) FROM providers").fetchone()[0] == 1
        assert con.execute("SELECT COUNT(*) FROM providers WHERE provider_id=?",
                           (S2.PROVIDER_ID,)).fetchone()[0] == 1
        assert con.execute("SELECT display_name FROM providers WHERE provider_id=?",
                           (S2.PROVIDER_ID,)).fetchone()[0] == S2.FAROUK_DISPLAY
    finally:
        con.close()
    # idempotency + identity keyed on provider_id (not display name)
    tmp = tempfile.mkdtemp(prefix="mpk_t1_")
    try:
        reg = RegistryDB(os.path.join(tmp, "r.db"))
        assert S2.register_farouk(reg) == "REGISTERED"
        assert S2.register_farouk(reg) == "ALREADY_PRESENT_VERIFIED"   # no duplicate
        assert reg.count("providers") == 1
        reg.close()
        # a conflicting display under the same provider_id is detected, not silently re-created
        reg2 = RegistryDB(os.path.join(tmp, "r2.db"))
        reg2.append_provider(provider_id=S2.PROVIDER_ID, display_name="NOT_FAROUK")
        try:
            S2.register_farouk(reg2)
            assert False, "conflicting display should block"
        except Step2Block:
            pass
        reg2.close()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ============================================================ Test 2 — exact set membership
def test_2_only_signed_off_set_eligible():
    # in-set Farouk record eligible; outside-set or non-Farouk record NOT eligible
    assert S2._eligible({"source_message_key": "telegram:baseline:16",
                         "provider": S2.FAROUK_ALIAS, "source_signal_index": 0})
    assert not S2._eligible({"source_message_key": "telegram:9999",
                             "provider": S2.FAROUK_ALIAS, "source_signal_index": 0})
    assert not S2._eligible({"source_message_key": "telegram:baseline:16",
                             "provider": ".ccolumbus", "source_signal_index": 0})
    # the loader only ever returns baseline keys
    recs, _ = S2.load_signed_off_28(ARCHIVE)
    assert all(r["source_message_key"] in S2.BASELINE_KEYS for r in recs)
    assert all(r["provider"] == S2.FAROUK_ALIAS for r in recs)


# ============================================================ Test 3 — 28 unique mappings
def test_3_twenty_eight_unique_mapped_verified():
    con = ro_connect(init_db.CAMPAIGNS_DB_PATH, immutable=False)
    try:
        total = con.execute("SELECT COUNT(*) FROM legacy_campaign_mapping").fetchone()[0]
        mv = con.execute("SELECT COUNT(*) FROM legacy_campaign_mapping "
                         "WHERE mapping_status='MAPPED_VERIFIED'").fetchone()[0]
        refs = [r[0] for r in con.execute(
            "SELECT immutable_legacy_reference FROM legacy_campaign_mapping").fetchall()]
        cuids = [r[0] for r in con.execute(
            "SELECT compatibility_record_uid FROM legacy_campaign_mapping").fetchall()]
        campaigns = con.execute("SELECT COUNT(*) FROM campaigns").fetchone()[0]
        assert total == 28 and mv == 28
        assert len(set(refs)) == 28                      # no duplicate legacy references
        assert len(set(cuids)) == 28                     # one-to-one compatibility ids
        assert campaigns == 0                            # NO campaign boundary asserted
    finally:
        con.close()


# ============================================================ Test 4 — ambiguity blocks / rollback
def test_4_incomplete_set_blocks_with_rollback():
    tmp = tempfile.mkdtemp(prefix="mpk_t4_")
    try:
        rp, cp = _fresh_mpk(tmp)
        cam = CampaignsDB(cp)
        recs, _ = S2.load_signed_off_28(ARCHIVE)
        short = recs[:-1]                                # only 27 eligible
        try:
            S2.map_signed_off_28(cam, short)
            assert False, "expected Step2Block for !=28 eligible"
        except Step2Block:
            pass
        assert cam.count("legacy_campaign_mapping") == 0   # nothing partially committed
        # a duplicated legacy ref inside one atomic batch -> UNIQUE violation -> full rollback
        built = [S2._build_mapping_record(r) for r in recs]
        built_dup = built + [built[0]]
        try:
            cam.append_legacy_mappings_atomic(built_dup)
            assert False, "expected UNIQUE violation"
        except sqlite3.IntegrityError:
            pass
        assert cam.count("legacy_campaign_mapping") == 0   # atomic: none committed
        cam.close()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ============================================================ Test 5 — rerun safety
def test_5_rerun_does_not_double():
    tmp = tempfile.mkdtemp(prefix="mpk_t5_")
    try:
        rp, cp = _fresh_mpk(tmp)
        r1 = S2.run(rp, cp, ARCHIVE)
        r2 = S2.run(rp, cp, ARCHIVE)
        assert r1["provider_action"] == "REGISTERED"
        assert r2["provider_action"] == "ALREADY_PRESENT_VERIFIED"
        assert r1["mapping_action"] == "MAPPED"
        assert r2["mapping_action"] == "ALREADY_MAPPED_VERIFIED"
        assert r2["canonical_provider_count"] == 1
        assert r2["legacy_mapping_total"] == 28           # not 56
        assert r2["mapped_verified_count"] == 28
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ============================================================ Test 6 — dirty legacy isolation
def test_6_dirty_providers_unmapped():
    reg = ro_connect(init_db.REGISTRY_DB_PATH, immutable=False)
    cam = ro_connect(init_db.CAMPAIGNS_DB_PATH, immutable=False)
    arch = ro_connect(ARCHIVE, immutable=False)
    try:
        # dirty identities are not registered as providers/aliases
        names = [r[0] for r in reg.execute("SELECT display_name FROM providers").fetchall()]
        assert names == [S2.FAROUK_DISPLAY]
        aliases = [r[0] for r in reg.execute(
            "SELECT sender_identifier FROM provider_aliases").fetchall()]
        for dirty in ("-1001937743421", "Thomas Weller"):
            assert dirty not in aliases
        # none of the mapped legacy refs belong to a dirty-provider signal
        dirty_ids = set()
        for dirty in ("-1001937743421", "Thomas Weller"):
            for (sid,) in arch.execute("SELECT signal_id FROM signals WHERE provider=?",
                                       (dirty,)).fetchall():
                dirty_ids.add(sid)
        mapped_refs = {r[0] for r in cam.execute(
            "SELECT immutable_legacy_reference FROM legacy_campaign_mapping").fetchall()}
        assert mapped_refs.isdisjoint(dirty_ids)
    finally:
        reg.close(); cam.close(); arch.close()


# ============================================================ Test 7 — original-row immutability
def _prompt_hash():
    import extractor as E
    art = (E.SYSTEM_PROMPT + "\n----USER_TEMPLATE----\n" + E._USER_TEMPLATE
           + "\n----VERSION----\n" + E.PROMPT_VERSION)
    return hashlib.sha256(art.encode("utf-8")).hexdigest()


def _truth_hash(name):
    with open(os.path.join(_CE, "phase0", "fixtures", name), encoding="utf-8") as f:
        fx = json.load(f)
    payload = {"authored_campaigns": fx["authored_campaigns"],
               "expected_truth": {m["message_id"]: m["expected_truth"] for m in fx["messages"]}}
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def test_7_protected_truth_unchanged():
    assert _prompt_hash() == LOCKED["prompt"]
    assert _truth_hash("fixture_2026-06-17.json") == LOCKED["j17"]
    assert _truth_hash("fixture_2026-06-24.json") == LOCKED["j24"]
    assert _truth_hash("fixture_2026-06-25.json") == LOCKED["j25"]
    con = ro_connect(ARCHIVE, immutable=False)
    try:
        assert con.execute("SELECT COUNT(*) FROM signals WHERE source_message_key "
                           "LIKE 'telegram:baseline:%'").fetchone()[0] == 28
        # the archive remains read-only: a write attempt fails
        for stmt in ("UPDATE signals SET asset='x'", "DELETE FROM signals"):
            try:
                con.execute(stmt); raise AssertionError("write succeeded on mode=ro")
            except sqlite3.OperationalError as e:
                assert "readonly" in str(e).lower() or "read-only" in str(e).lower()
    finally:
        con.close()


# ============================================================ Test 8 — compatibility projection
def test_8_compatibility_projection_sources_immutable_truth():
    rows = legacy_projection.project_farouk_signed_off(init_db.CAMPAIGNS_DB_PATH, ARCHIVE)
    assert len(rows) == 28
    # every displayed value is sourced from legacy; the tamper hash recomputed from the live
    # legacy read equals the stored mapping hash (no silent recompute/replacement)
    recs, _ = S2.load_signed_off_28(ARCHIVE)
    by_ref = {r["signal_id"]: S2._build_mapping_record(r)["original_record_hash"] for r in recs}
    cam = ro_connect(init_db.CAMPAIGNS_DB_PATH, immutable=False)
    try:
        for row in rows:
            assert row["provider_id"] == S2.PROVIDER_ID
            assert row["source_record_type"] == S2.SOURCE_RECORD_TYPE
            assert "legacy" in row and row["legacy"]["provider"] == S2.FAROUK_ALIAS
            ref = row["legacy"]["signal_id"]
            assert row["original_record_hash"] == by_ref[ref]    # verbatim from legacy truth
    finally:
        cam.close()


# ============================================================ Test 9 — deletion independence
def test_9_deletion_independence_temp_fixture():
    tmp = tempfile.mkdtemp(prefix="mpk_t9_")
    try:
        legacy = os.path.join(tmp, "legacy_truth.db")
        _make_temp_legacy(legacy, S2.BASELINE_KEYS)       # synthetic, independent of MPK
        before = hashlib.sha256(open(legacy, "rb").read()).hexdigest()
        rp, cp = _fresh_mpk(tmp)
        rep = S2.run(rp, cp, legacy)
        assert rep["legacy_mapping_total"] == 28
        # delete the entire MPK layer
        os.remove(rp); os.remove(cp)
        # legacy truth complete, byte-identical, independently usable (the +0.17R value intact)
        assert hashlib.sha256(open(legacy, "rb").read()).hexdigest() == before
        c = sqlite3.connect(legacy)
        assert c.execute("SELECT COUNT(*) FROM signals").fetchone()[0] == 28
        assert c.execute("SELECT calculated_r FROM outcome_projections LIMIT 1").fetchone()[0] == "0.17"
        c.close()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ============================================================ Test 10 — no live wiring
def _mpk_source(name):
    with open(os.path.join(_MPK, name), encoding="utf-8") as f:
        return f.read()


def test_10a_no_import_into_listener_or_live_paths():
    for live in ("module_a_telegram.py", "module_b_parser.py"):
        p = os.path.join(_ROOT, live)
        if os.path.exists(p):
            src = open(p, encoding="utf-8").read()
            assert "import mpk" not in src and "from mpk" not in src, f"{live} imports mpk"


def test_10b_no_credential_loading_in_mpk():
    forbidden = ("CTRADER_", "TELEGRAM_API", "CLIENT_SECRET", "ACCESS_TOKEN",
                 "ANTHROPIC_API_KEY", "os.environ", "getenv", "private_key", "WALLET",
                 "SIGNING_KEY")
    for name in MPK_SOURCES:
        src = _mpk_source(name)
        for tok in forbidden:
            assert tok not in src, f"{name} references {tok!r}"


def test_10c_no_broker_exchange_or_network_dependency():
    forbidden = ("broker_readonly", "hyperliquid", "ctrader", "twisted", "anthropic",
                 "import socket", "import ssl", "urllib", "requests", "websocket")
    for name in MPK_SOURCES:
        src = _mpk_source(name)
        for tok in forbidden:
            assert tok not in src, f"{name} has forbidden dependency {tok!r}"


def test_10d_standing_locks_unchanged_in_source():
    cfg = open(os.path.join(_ROOT, "config.py"), encoding="utf-8").read()
    assert 'MODE = "PAPER"' in cfg
    assert "EXECUTION_ENABLED = False" in cfg
    assert 'LISTENER_MODE = "PREVIEW"' in cfg
    ccfg = open(os.path.join(_ROOT, "ctrader_config.py"), encoding="utf-8").read()
    assert "CTRADER_EXECUTION_ENABLED = False" in ccfg
