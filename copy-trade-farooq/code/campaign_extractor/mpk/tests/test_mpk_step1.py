"""
MPK-1 Step 1 — offline safety + correctness tests.

Self-contained. Every test that mutates uses an in-memory or temp database; the real
canonical persistent files are only ever read (read-only) and must stay empty of business
data. No network, no credentials, no spine/listener/broker imports.
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
_CE = os.path.dirname(_MPK)                       # campaign_extractor
_ROOT = os.path.dirname(_CE)                      # signal-terminal
for p in (_MPK, _CE):
    if p not in sys.path:
        sys.path.insert(0, p)

import appendonly
from appendonly import AppendOnlyViolation, reject_mutation, ro_connect
from registry_db import RegistryDB, BUSINESS_TABLES as REG_TABLES
from campaigns_db import CampaignsDB, BUSINESS_TABLES as CAM_TABLES
import init_db
import legacy_readonly

# locked frozen hashes (from the existing guard tests)
LOCKED = {
    "prompt": "95bbf6a4b18ebdd7fc4db2a3e1449ab2e7b7e65a7cf16da461d8ea251a802ef4",
    "j17": "c8b1c3ebfb46441e113570f798e951ffce35829c4e4b50a052f9c2b8eba20339",
    "j24": "a230ce7a704b2d301a00451f91c472a30a77f042dbabd9e47c1888ae3bcba4a2",
    "j25": "22041d7aeb06bd373c21e23cab42eaf8d422b4913625da518bd3dd6d4c649bce",
}
MPK_SOURCES = ("__init__.py", "appendonly.py", "registry_db.py", "campaigns_db.py",
               "init_db.py", "legacy_readonly.py")


# ---------------------------------------------------------------- 1. schema creation
def test_deterministic_empty_schema_creation():
    a = RegistryDB(":memory:"); b = RegistryDB(":memory:")
    assert a.schema_fingerprint() == b.schema_fingerprint()
    c = CampaignsDB(":memory:"); d = CampaignsDB(":memory:")
    assert c.schema_fingerprint() == d.schema_fingerprint()
    a.close(); b.close(); c.close(); d.close()


def test_expected_tables_and_constraints_created():
    reg = RegistryDB(":memory:")
    for t in ("providers", "provider_aliases", "provider_channels",
              "channel_permission_events", "canonical_instruments", "instrument_aliases",
              "administrative_events", "mpk_schema_meta"):
        assert t in reg.table_names(), t
    cam = CampaignsDB(":memory:")
    for t in ("campaigns", "campaign_events", "legacy_campaign_mapping", "mpk_schema_meta"):
        assert t in cam.table_names(), t
    # every business table carries BOTH append-only triggers
    for t in REG_TABLES:
        assert f"noupd_{t}" in reg.trigger_names() and f"nodel_{t}" in reg.trigger_names()
    for t in CAM_TABLES:
        assert f"noupd_{t}" in cam.trigger_names() and f"nodel_{t}" in cam.trigger_names()
    reg.close(); cam.close()


# ---------------------------------------------------------------- 2. valid / invalid INSERT
def test_valid_append_insert_succeeds():
    reg = RegistryDB(":memory:")
    reg.append_provider(provider_id="prv_test", display_name="Test")
    assert reg.count("providers") == 1
    cam = CampaignsDB(":memory:")
    cam.append_campaign(campaign_uid="c1", provider_id="prv_test",
                        campaign_creation_status="CREATED")
    assert cam.count("campaigns") == 1
    reg.close(); cam.close()


def test_invalid_insert_fails_safely_notnull():
    reg = RegistryDB(":memory:")
    try:
        reg.append_provider(provider_id="p", display_name=None)   # NOT NULL violation
        assert False, "expected IntegrityError"
    except sqlite3.IntegrityError:
        pass
    assert reg.count("providers") == 0
    reg.close()


# ---------------------------------------------------------------- 3/4. UPDATE / DELETE rejected (DB level)
def test_update_rejected_at_db_level():
    reg = RegistryDB(":memory:")
    reg.append_provider(provider_id="p1", display_name="A")
    try:
        reg.con.execute("UPDATE providers SET display_name='B' WHERE provider_id='p1'")
        assert False, "UPDATE should have been rejected by trigger"
    except sqlite3.Error as e:
        assert "append-only" in str(e).lower()
    assert reg.con.execute(
        "SELECT display_name FROM providers WHERE provider_id='p1'").fetchone()[0] == "A"
    reg.close()


def test_delete_rejected_at_db_level():
    cam = CampaignsDB(":memory:")
    cam.append_campaign(campaign_uid="c1", provider_id="p1", campaign_creation_status="CREATED")
    try:
        cam.con.execute("DELETE FROM campaigns WHERE campaign_uid='c1'")
        assert False, "DELETE should have been rejected by trigger"
    except sqlite3.Error as e:
        assert "append-only" in str(e).lower()
    assert cam.count("campaigns") == 1
    cam.close()


def test_admin_history_cannot_be_silently_overwritten():
    reg = RegistryDB(":memory:")
    reg.append_provider(provider_id="p1", display_name="A")
    reg.append_administrative_event(admin_event_id="ae1", admin_event_type="PROVIDER_REGISTERED",
                                    subject_provider_id="p1", actor="test")
    for stmt in ("UPDATE administrative_events SET actor='x'",
                 "DELETE FROM administrative_events"):
        try:
            reg.con.execute(stmt)
            assert False, f"{stmt} should be rejected"
        except sqlite3.Error as e:
            assert "append-only" in str(e).lower()
    assert reg.count("administrative_events") == 1
    reg.close()


# ---------------------------------------------------------------- 5. FK integrity
def test_foreign_key_integrity_enforced():
    cam = CampaignsDB(":memory:")
    try:
        cam.append_campaign_event(event_uid="e1", provider_id="p1",
                                  campaign_uid="does_not_exist", association_status="ASSOCIATED")
        assert False, "FK violation expected"
    except sqlite3.IntegrityError:
        pass
    assert cam.count("campaign_events") == 0
    cam.close()


# ---------------------------------------------------------------- 6. duplicate immutable identity
def test_duplicate_primary_identity_rejected():
    reg = RegistryDB(":memory:")
    reg.append_provider(provider_id="dup", display_name="A")
    try:
        reg.append_provider(provider_id="dup", display_name="B")
        assert False, "duplicate provider_id should be rejected"
    except sqlite3.IntegrityError:
        pass
    assert reg.count("providers") == 1
    reg.close()


def test_duplicate_alias_identity_rejected():
    reg = RegistryDB(":memory:")
    reg.append_provider(provider_id="p1", display_name="A")
    reg.append_provider_alias(alias_id="a1", provider_id="p1", platform="TELEGRAM",
                              sender_identifier="x", verification_status="VERIFIED",
                              effective_from_utc="2026-01-01")
    try:
        reg.append_provider_alias(alias_id="a2", provider_id="p1", platform="TELEGRAM",
                                  sender_identifier="x", verification_status="VERIFIED",
                                  effective_from_utc="2026-01-01")
        assert False, "duplicate alias identity should be rejected"
    except sqlite3.IntegrityError:
        pass
    reg.close()


# ---------------------------------------------------------------- app-level mutation guards
def test_application_level_mutation_guard():
    for bad in ("UPDATE providers SET x=1", "DELETE FROM campaigns",
                "REPLACE INTO providers VALUES (1)", "INSERT OR REPLACE INTO providers VALUES(1)",
                "  update providers set x=1"):
        try:
            reject_mutation(bad)
            assert False, f"reject_mutation should raise for {bad!r}"
        except AppendOnlyViolation:
            pass
    # INSERT and schema statements pass the business-row guard
    for ok in ("INSERT INTO providers (provider_id) VALUES ('x')",
               "CREATE TABLE foo (a)", "SELECT * FROM providers", "ALTER TABLE foo ADD b"):
        reject_mutation(ok)


def test_no_public_mutation_methods_on_repositories():
    bad_verbs = ("update", "delete", "remove", "set_", "overwrite", "drop")
    for cls in (RegistryDB, CampaignsDB):
        public = [n for n in dir(cls) if not n.startswith("_")]
        for n in public:
            assert not any(n.lower().startswith(v) or v in n.lower() for v in bad_verbs), \
                f"{cls.__name__}.{n} looks like a mutation method"


# ---------------------------------------------------------------- schema vs business separation
def test_schema_control_separated_from_business_mutation():
    reg = RegistryDB(":memory:")
    # schema_meta has exactly one migration row and is NOT under append-only triggers
    assert len(reg.schema_meta_rows()) == 1
    assert "noupd_mpk_schema_meta" not in reg.trigger_names()
    assert "nodel_mpk_schema_meta" not in reg.trigger_names()
    # business tables ARE under triggers (separation is explicit, not global blocking)
    assert "noupd_providers" in reg.trigger_names()
    # CREATE (schema) passes the application business-row guard
    reject_mutation("CREATE TABLE later_migration (a)")
    reg.close()


# ---------------------------------------------------------------- protected legacy read-only access
def test_protected_legacy_opened_read_only_cannot_write():
    path = os.path.join(_ROOT, "data", "signal_archive.db")
    if not os.path.exists(path):
        raise AssertionError("signal_archive.db missing — cannot prove read-only access")
    con = ro_connect(path, immutable=False)
    try:
        for stmt in ("UPDATE signals SET asset='x'",
                     "CREATE TABLE mpk_should_not_exist (a)",
                     "DELETE FROM signals"):
            try:
                con.execute(stmt)
                raise AssertionError(f"write succeeded on mode=ro connection: {stmt}")
            except sqlite3.OperationalError as e:
                assert "readonly" in str(e).lower() or "read-only" in str(e).lower()
    finally:
        con.close()


# ---------------------------------------------------------------- canonical persistent files empty
def test_canonical_persistent_databases_empty_of_business_data():
    # the real persistent files (created by init_db) must hold 0 business rows
    for path, tables in ((init_db.REGISTRY_DB_PATH,
                          ("providers", "provider_aliases", "provider_channels",
                           "administrative_events")),
                         (init_db.CAMPAIGNS_DB_PATH,
                          ("campaigns", "legacy_campaign_mapping"))):
        assert os.path.exists(path), f"{path} not initialised"
        con = ro_connect(path, immutable=True)       # static file -> immutable safe
        try:
            for t in tables:
                n = con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
                assert n == 0, f"{t} not empty ({n})"
        finally:
            con.close()


# ---------------------------------------------------------------- Test I — legacy integrity
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


def test_I_legacy_frozen_hashes_unchanged():
    assert _prompt_hash() == LOCKED["prompt"]
    assert _truth_hash("fixture_2026-06-17.json") == LOCKED["j17"]
    assert _truth_hash("fixture_2026-06-24.json") == LOCKED["j24"]
    assert _truth_hash("fixture_2026-06-25.json") == LOCKED["j25"]


def test_I_signed_off_28_present_and_unchanged():
    s = legacy_readonly.read_baseline_28()
    assert s["baseline_28_count"] == 28
    # fingerprint is stable across calls (read-only; MPK cannot alter it)
    assert legacy_readonly.read_baseline_28()["rowset_fingerprint"] == s["rowset_fingerprint"]


# ---------------------------------------------------------------- Test J — deletion independence
def test_J_deletion_independence_temp_fixture():
    tmp = tempfile.mkdtemp(prefix="mpk_testJ_")
    try:
        # an isolated synthetic "legacy Farouk truth" db (NO reference to MPK)
        legacy = os.path.join(tmp, "legacy_truth.db")
        lc = sqlite3.connect(legacy)
        lc.execute("CREATE TABLE signals (k TEXT, asset TEXT, r REAL)")
        lc.executemany("INSERT INTO signals VALUES (?,?,?)",
                       [("telegram:baseline:16", "XAUUSD", 0.17),
                        ("telegram:baseline:29", "XAUUSD", 0.34)])
        lc.commit(); lc.close()
        before = legacy_readonly.file_sha256(legacy)
        before_rows = sqlite3.connect(legacy).execute("SELECT COUNT(*) FROM signals").fetchone()[0]

        # build the MPK foundation in temp, then DELETE it entirely
        reg = RegistryDB(os.path.join(tmp, "mpk_registry_v1.db"))
        cam = CampaignsDB(os.path.join(tmp, "mpk_campaigns_v1.db"))
        reg.close(); cam.close()
        os.remove(os.path.join(tmp, "mpk_registry_v1.db"))
        os.remove(os.path.join(tmp, "mpk_campaigns_v1.db"))

        # legacy remains byte-for-byte complete and independently usable
        assert legacy_readonly.file_sha256(legacy) == before
        con = sqlite3.connect(legacy)
        assert con.execute("SELECT COUNT(*) FROM signals").fetchone()[0] == before_rows
        assert con.execute("SELECT r FROM signals WHERE k='telegram:baseline:16'").fetchone()[0] == 0.17
        con.close()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ---------------------------------------------------------------- separation: no live/credential/broker coupling
def _mpk_source(name):
    with open(os.path.join(_MPK, name), encoding="utf-8") as f:
        return f.read()


def test_no_import_into_listener_or_live_paths():
    for live in ("module_a_telegram.py", "module_b_parser.py"):
        p = os.path.join(_ROOT, live)
        if os.path.exists(p):
            with open(p, encoding="utf-8") as f:
                src = f.read()
            assert "mpk" not in src.replace("import", "").lower().split("def ")[0] or \
                "import mpk" not in src and "from mpk" not in src
            assert "import mpk" not in src and "from mpk" not in src, f"{live} imports mpk"


def test_no_credential_loading_in_mpk():
    forbidden = ("CTRADER_", "TELEGRAM_API", "CLIENT_SECRET", "ACCESS_TOKEN",
                 "ANTHROPIC_API_KEY", "os.environ", "getenv", "private_key", "WALLET",
                 "SIGNING_KEY")
    for name in MPK_SOURCES:
        src = _mpk_source(name)
        for tok in forbidden:
            assert tok not in src, f"{name} references credential/env token {tok!r}"


def test_no_broker_exchange_or_network_dependency_in_mpk():
    forbidden = ("broker_readonly", "hyperliquid", "ctrader", "twisted", "anthropic",
                 "import socket", "import ssl", "urllib", "requests", "websocket")
    for name in MPK_SOURCES:
        src = _mpk_source(name)
        for tok in forbidden:
            assert tok not in src, f"{name} has forbidden dependency {tok!r}"
