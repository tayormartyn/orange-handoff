"""
MPK-2A — offline tests (provider onboarding + permission gates). Synthetic fixtures only.

All state-changing work uses TEMP registry DBs with SYNTHETIC providers. No real provider
is registered. Farouk (Test J) is read STRICTLY read-only from the persistent canonical DBs.
No network, no credentials, no live wiring.
"""
from __future__ import annotations
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
import gates as G
from onboarding import OnboardingService, OnboardingConflict
import init_db

MPK_SOURCES = ("__init__.py", "appendonly.py", "registry_db.py", "campaigns_db.py",
               "init_db.py", "legacy_readonly.py", "step2_register_and_map.py",
               "legacy_projection.py", "gates.py", "onboarding.py", "run_step1.py",
               "run_step2.py", "run_step2a.py")

T0, T1, T2, T3 = "2026-06-01", "2026-06-10", "2026-06-20", "2026-06-30"


def _svc(tmp):
    reg = RegistryDB(os.path.join(tmp, "reg.db"))
    return reg, OnboardingService(reg)


# ============================================================ Test A — unknown sender default
def test_A_unknown_sender_default():
    tmp = tempfile.mkdtemp(prefix="a_")
    try:
        reg, svc = _svc(tmp)
        cand = svc.record_source_candidate(platform="TELEGRAM", immutable_sender_id="999",
                                           observed_username="mystery", first_observed_at=T0)
        cur = svc._current_candidate(cand)
        assert cur[1] == "UNVERIFIED" and cur[2] == "NEEDS_REVIEW"
        assert reg.count("providers") == 0           # no provider auto-created
        perm = G.effective_permission(reg.con, "would_be_provider", T1, channel_id="ch1")
        assert perm["capture_status"] == G.CAPTURE_CONTEXT_ONLY
        assert perm["tracking_status"] == G.TRACK_DENIED
        reg.close()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ============================================================ Test B — capture only
def test_B_capture_permission_only():
    tmp = tempfile.mkdtemp(prefix="b_")
    try:
        reg, svc = _svc(tmp)
        svc.register_provider(provider_id="prov_b", display_name="SynthB", effective_from=T0)
        svc.record_capture_permission(provider_id="prov_b", capture_status=G.CAPTURE_ALLOWED,
                                      effective_from=T1)
        perm = G.effective_permission(reg.con, "prov_b", T2)
        assert perm["capture_status"] == G.CAPTURE_ALLOWED
        assert perm["tracking_status"] == G.TRACK_DENIED    # tracking NOT granted
        reg.close()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ============================================================ Test C — review-required
def test_C_review_required_no_campaign():
    tmp = tempfile.mkdtemp(prefix="c_")
    try:
        reg, svc = _svc(tmp)
        svc.register_provider(provider_id="prov_c", display_name="SynthC", effective_from=T0)
        svc.record_tracking_permission(provider_id="prov_c",
                                       tracking_status=G.TRACK_REVIEW_REQUIRED, effective_from=T1)
        perm = G.effective_permission(reg.con, "prov_c", T2)
        assert perm["tracking_status"] == G.TRACK_REVIEW_REQUIRED
        # onboarding has NO campaign-creation capability (review only)
        assert not any("campaign" in m for m in dir(svc) if not m.startswith("_"))
        reg.close()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ============================================================ Test D — tracked timing
def test_D_tracked_provider_timing_no_retroactive():
    tmp = tempfile.mkdtemp(prefix="d_")
    try:
        reg, svc = _svc(tmp)
        svc.register_provider(provider_id="prov_d", display_name="SynthD", effective_from=T0)
        svc.record_tracking_permission(provider_id="prov_d",
                                       tracking_status=G.TRACK_TRACKED_PROVIDER, effective_from=T2)
        assert G.effective_permission(reg.con, "prov_d", T1)["tracking_status"] == G.TRACK_DENIED
        assert G.effective_permission(reg.con, "prov_d", T3)["tracking_status"] == G.TRACK_TRACKED_PROVIDER
        reg.close()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ============================================================ Test E — active channel conflict
def test_E_active_channel_conflict_blocks():
    tmp = tempfile.mkdtemp(prefix="e_")
    try:
        reg, svc = _svc(tmp)
        svc.register_provider(provider_id="prov_A", display_name="A", effective_from=T0)
        svc.register_provider(provider_id="prov_B", display_name="B", effective_from=T0)
        svc.assign_channel(provider_id="prov_A", platform="TELEGRAM",
                           immutable_channel_id="-100chan", effective_from=T1)
        try:
            svc.assign_channel(provider_id="prov_B", platform="TELEGRAM",
                               immutable_channel_id="-100chan", effective_from=T1)
            assert False, "expected conflict"
        except OnboardingConflict:
            pass
        owners = [r[0] for r in reg.con.execute(
            "SELECT provider_id FROM provider_channels WHERE immutable_channel_id='-100chan'")]
        assert owners == ["prov_A"]                  # A unchanged, B never assigned
        reg.close()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ============================================================ Test F — sender conflict
def test_F_sender_conflict_blocks():
    tmp = tempfile.mkdtemp(prefix="f_")
    try:
        reg, svc = _svc(tmp)
        for pid in ("prov_A", "prov_B"):
            svc.register_provider(provider_id=pid, display_name=pid, effective_from=T0)
        svc.assign_sender_id(provider_id="prov_A", platform="TELEGRAM",
                             immutable_sender_id="sid_777", effective_from=T1)
        try:
            svc.assign_sender_id(provider_id="prov_B", platform="TELEGRAM",
                                 immutable_sender_id="sid_777", effective_from=T1)
            assert False, "expected conflict"
        except OnboardingConflict:
            pass
        owners = [r[0] for r in reg.con.execute(
            "SELECT provider_id FROM provider_sender_assignments WHERE immutable_sender_id='sid_777'")]
        assert owners == ["prov_A"]
        reg.close()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ============================================================ Test G — display-name collision
def test_G_display_name_collision_kept_separate():
    tmp = tempfile.mkdtemp(prefix="g_")
    try:
        reg, svc = _svc(tmp)
        svc.register_provider(provider_id="prov_x", display_name="Columbus", effective_from=T0)
        svc.register_provider(provider_id="prov_y", display_name="Columbus", effective_from=T0)
        assert reg.count("providers") == 2           # same display, distinct identity, no merge
        ids = {r[0] for r in reg.con.execute("SELECT provider_id FROM providers")}
        assert ids == {"prov_x", "prov_y"}
        reg.close()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ============================================================ Test H — rename stability
def test_H_username_channel_rename_identity_stable():
    tmp = tempfile.mkdtemp(prefix="h_")
    try:
        reg, svc = _svc(tmp)
        svc.register_provider(provider_id="prov_h", display_name="H", effective_from=T0)
        svc.assign_sender_id(provider_id="prov_h", platform="TELEGRAM",
                             immutable_sender_id="sid_h", effective_from=T0)
        svc.assign_channel(provider_id="prov_h", platform="TELEGRAM",
                           immutable_channel_id="ch_h", channel_title="Old Title", effective_from=T0)
        # username 'rename' = a NEW alias; channel-title 'rename' = a new display title only
        svc.add_alias(provider_id="prov_h", platform="TELEGRAM", sender_identifier="newhandle",
                      verification_status="VERIFIED", effective_from=T1)
        # immutable sender/channel still resolve to the SAME single provider; no new provider
        assert reg.count("providers") == 1
        assert reg.con.execute("SELECT provider_id FROM provider_sender_assignments "
                               "WHERE immutable_sender_id='sid_h'").fetchone()[0] == "prov_h"
        assert {r[0] for r in reg.con.execute("SELECT DISTINCT provider_id FROM provider_channels "
                "WHERE immutable_channel_id='ch_h'")} == {"prov_h"}
        reg.close()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ============================================================ Test I — historical permission query
def test_I_historical_permission_resolution():
    tmp = tempfile.mkdtemp(prefix="i_")
    try:
        reg, svc = _svc(tmp)
        svc.register_provider(provider_id="prov_i", display_name="I", effective_from=T0)
        svc.record_tracking_permission(provider_id="prov_i",
                                       tracking_status=G.TRACK_REVIEW_REQUIRED, effective_from=T1)
        svc.record_tracking_permission(provider_id="prov_i",
                                       tracking_status=G.TRACK_TRACKED_PROVIDER, effective_from=T2)
        svc.record_capture_permission(provider_id="prov_i", capture_status=G.CAPTURE_ALLOWED,
                                      effective_from=T3)
        assert G.effective_permission(reg.con, "prov_i", T0)["tracking_status"] == G.TRACK_DENIED
        assert G.effective_permission(reg.con, "prov_i", T1)["tracking_status"] == G.TRACK_REVIEW_REQUIRED
        assert G.effective_permission(reg.con, "prov_i", T2)["tracking_status"] == G.TRACK_TRACKED_PROVIDER
        midcap = G.effective_permission(reg.con, "prov_i", T3)
        assert midcap["capture_status"] == G.CAPTURE_ALLOWED       # capture changed at T3
        assert midcap["tracking_status"] == G.TRACK_TRACKED_PROVIDER  # tracking carried forward
        # history is not rewritten by the later events
        assert G.effective_permission(reg.con, "prov_i", T1)["tracking_status"] == G.TRACK_REVIEW_REQUIRED
        reg.close()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ============================================================ Test J — Farouk protection
def test_J_farouk_protected_read_only():
    reg = ro_connect(init_db.REGISTRY_DB_PATH, immutable=True)
    cam = ro_connect(init_db.CAMPAIGNS_DB_PATH, immutable=True)
    try:
        assert reg.execute("SELECT COUNT(*) FROM providers").fetchone()[0] == 1
        assert reg.execute("SELECT COUNT(*) FROM providers WHERE provider_id='provider_farouk_001'"
                           ).fetchone()[0] == 1
        assert reg.execute("SELECT display_name FROM providers").fetchone()[0] == "Farouk"
        total = cam.execute("SELECT COUNT(*) FROM legacy_campaign_mapping").fetchone()[0]
        mv = cam.execute("SELECT COUNT(*) FROM legacy_campaign_mapping "
                         "WHERE mapping_status='MAPPED_VERIFIED'").fetchone()[0]
        assert total == 28 and mv == 28
    finally:
        reg.close(); cam.close()


# ============================================================ Test K — provider separation
def test_K_provider_separation():
    tmp = tempfile.mkdtemp(prefix="k_")
    try:
        reg, svc = _svc(tmp)
        for pid in ("prov_A", "prov_B"):
            svc.register_provider(provider_id=pid, display_name=pid, effective_from=T0)
        # both "post the same instrument/direction" — modelled as separate senders + permissions
        svc.assign_sender_id(provider_id="prov_A", platform="TELEGRAM",
                             immutable_sender_id="sid_A", effective_from=T0)
        svc.assign_sender_id(provider_id="prov_B", platform="TELEGRAM",
                             immutable_sender_id="sid_B", effective_from=T0)
        svc.record_tracking_permission(provider_id="prov_A",
                                       tracking_status=G.TRACK_TRACKED_PROVIDER, effective_from=T1)
        # A tracked, B independent (still default DENIED) — no cross-contamination
        assert G.effective_permission(reg.con, "prov_A", T2)["tracking_status"] == G.TRACK_TRACKED_PROVIDER
        assert G.effective_permission(reg.con, "prov_B", T2)["tracking_status"] == G.TRACK_DENIED
        reg.close()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ============================================================ Test L — append-only enforcement
def test_L_append_only_enforcement():
    tmp = tempfile.mkdtemp(prefix="l_")
    try:
        reg, svc = _svc(tmp)
        svc.register_provider(provider_id="prov_l", display_name="L", effective_from=T0)
        svc.record_source_candidate(platform="TELEGRAM", immutable_sender_id="cand_l",
                                    first_observed_at=T0)   # ensure a row exists for the trigger
        svc.record_tracking_permission(provider_id="prov_l",
                                       tracking_status=G.TRACK_REVIEW_REQUIRED, effective_from=T1)
        svc.record_tracking_permission(provider_id="prov_l",
                                       tracking_status=G.TRACK_TRACKED_PROVIDER, effective_from=T2)
        assert reg.con.execute("SELECT COUNT(*) FROM channel_permission_events").fetchone()[0] == 2
        for stmt in ("UPDATE providers SET display_name='x'",
                     "DELETE FROM providers",
                     "UPDATE channel_permission_events SET tracking_status='DENIED'",
                     "DELETE FROM channel_permission_events",
                     "UPDATE provider_status_events SET status='RETIRED'",
                     "UPDATE source_candidates SET identity_status='VERIFIED'"):
            try:
                reg.con.execute(stmt)
                assert False, f"{stmt} should be rejected"
            except sqlite3.Error as e:
                assert "append-only" in str(e).lower()
        assert reg.con.execute("SELECT COUNT(*) FROM channel_permission_events").fetchone()[0] == 2
        reg.close()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ============================================================ Test M — transaction rollback
def test_M_transaction_rollback_no_partial():
    tmp = tempfile.mkdtemp(prefix="m_")
    try:
        reg, svc = _svc(tmp)
        # a multi-insert transaction whose 2nd insert violates a CHECK -> full rollback
        reg.begin()
        reg.append_provider(provider_id="prov_m", display_name="M", commit=False)
        try:
            reg._append("provider_status_events",
                        {"status_event_id": "x", "provider_id": "prov_m", "status": "BOGUS",
                         "effective_from": T0, "reason": None, "created_at": T0,
                         "event_hash": "h"}, commit=False)
            assert False, "expected CHECK violation"
        except sqlite3.IntegrityError:
            reg.rollback()
        assert reg.count("providers") == 0           # the valid insert was rolled back
        assert reg.count("provider_status_events") == 0
        # a service-level conflict leaves nothing partial either
        svc.register_provider(provider_id="prov_n", display_name="N", effective_from=T0)
        svc.assign_sender_id(provider_id="prov_n", platform="TELEGRAM",
                             immutable_sender_id="s1", effective_from=T0)
        admin_before = reg.count("administrative_events")
        try:
            svc.assign_sender_id(provider_id="prov_n", platform="TELEGRAM",
                                 immutable_sender_id="s1", effective_from=T0)  # dup -> fails
            assert False
        except sqlite3.IntegrityError:
            pass
        assert reg.count("administrative_events") == admin_before   # no partial admin row
        reg.close()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ============================================================ Test N — no live wiring
def _mpk_source(name):
    with open(os.path.join(_MPK, name), encoding="utf-8") as f:
        return f.read()


def test_N_no_live_wiring():
    for live in ("module_a_telegram.py", "module_b_parser.py"):
        p = os.path.join(_ROOT, live)
        if os.path.exists(p):
            src = open(p, encoding="utf-8").read()
            assert "import mpk" not in src and "from mpk" not in src
    cred = ("CTRADER_", "TELEGRAM_API", "CLIENT_SECRET", "ACCESS_TOKEN", "ANTHROPIC_API_KEY",
            "os.environ", "getenv", "private_key", "WALLET", "SIGNING_KEY")
    net = ("broker_readonly", "hyperliquid", "ctrader", "twisted", "anthropic", "import socket",
           "import ssl", "urllib", "requests", "websocket")
    for name in MPK_SOURCES:
        src = _mpk_source(name)
        for tok in cred + net:
            assert tok not in src, f"{name} has forbidden token {tok!r}"
    cfg = open(os.path.join(_ROOT, "config.py"), encoding="utf-8").read()
    assert 'MODE = "PAPER"' in cfg and "EXECUTION_ENABLED = False" in cfg
    assert 'LISTENER_MODE = "PREVIEW"' in cfg
    assert "CTRADER_EXECUTION_ENABLED = False" in open(
        os.path.join(_ROOT, "ctrader_config.py"), encoding="utf-8").read()
