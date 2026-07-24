"""Confirmed Image Paper Bridge V0.1 offline tests (42). Synthetic; reuses Vision V1.1/Q4A/paper-loop unchanged."""
from __future__ import annotations
import glob
import hashlib
import os
import shutil
import sqlite3
import sys
import tempfile
from datetime import datetime, timezone

_HERE = os.path.dirname(os.path.abspath(__file__))
_PL = os.path.dirname(_HERE)
_CE = os.path.dirname(_PL)
_ROOT = os.path.dirname(_CE)
_Q4 = os.path.join(_CE, "q4_align")
_VIS = os.path.join(_CE, "vision_v1")
# _VIS last -> first on path, so Vision V1.1's `from __init__ import` resolves to vision_v1/__init__.py
for p in (_ROOT, _CE, _Q4, _PL, _VIS):
    if p not in sys.path:
        sys.path.insert(0, p)

import image_signal_bridge as bridge
import image_profile
import image_intake
import decimals
import firewalls as vfw
from image_bridge_db import ImageBridgeDB
from paper_db import PaperDB, reject_provider_pnl_from_outcome, PaperOutcomeFirewallError
import kernel as q4a

HASHES = {"kernel.py": "ceda526069167861", "q4_config.py": "91ce10bd7a073b14",
          "paper_gate.py": "0144c4de9ee685a3", "paper_db.py": "de0af77cb23f5bc2"}


def iso(ms):
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).isoformat().replace("+00:00", "Z")


def q(seq, wall, mono, bid, ask, bp=None, ap=None):
    return {"session": "S", "seq": seq, "symbol_id": 41, "raw_bid": int(bid * 100000) if bid else None,
            "raw_ask": int(ask * 100000) if ask else None, "broker_ts": 5_000_000 + seq,
            "wall_ms": wall, "mono_ns": mono, "bid": bid, "ask": ask,
            "spread": round(ask - bid, 2) if (bid and ask) else None, "flags": "OK",
            "bid_prov_seq": bp or (seq if bid else None), "ask_prov_seq": ap or (seq if ask else None)}


def sess(n=5, wall0=1000000, step=500, bid0=4000.00, spread=0.10):
    return [q(i + 1, wall0 + i * step, i * step * 1_000_000, round(bid0 + 0.01 * i, 2),
              round(bid0 + 0.01 * i + spread, 2)) for i in range(n)]


def approved(**o):
    d = {"semantic_class": "SIGNAL_ANNOUNCEMENT", "isolated_signal_block": False,
         "all_facts_human_confirmed": True, "provider_verified": True,
         "instrument": "XAUUSD", "direction": "BUY", "entry_low": "4000.00", "entry_high": "4000.20",
         "stop_price": None, "target_prices": None, "provider_posted_at": iso(1000600),
         "human_confirmed_at": iso(1000600), "reviewer_reference": "martyn",
         "mixed_blocks_not_separated": False, "conflicting_high_impact": False}
    d.update(o)
    return d


def manifest(**o):
    d = {"intake_id": "intake-x", "discord_message_ref": "https://discord.com/msg/1",
         "source_server_channel_text": "server / gold-signals",
         "original_image_sha256": "a" * 64, "screenshot_imported_at": iso(1000600),
         "screenshot_captured_at": iso(1000550)}
    d.update(o)
    return d


REFS = ["review-1", "crop-1"]


def build(**o):
    return bridge.build_image_unified_signal(approved(**o), manifest(), REFS)


def anchors(**o):
    st, u, r = build(**{k: v for k, v in o.items() if k in approved()})
    a = approved(**o)
    return bridge.run_three_anchors(u, sess(), None, provider_posted_at=a["provider_posted_at"],
        provider_posted_provenance=o.get("provenance", "DISCORD_MESSAGE_ID_OR_LINK"),
        screenshot_imported_at=manifest()["screenshot_imported_at"],
        human_confirmed_at=a["human_confirmed_at"]) if st == "IMAGE_CONFIRMED" else None


def _tmp():
    return tempfile.mkdtemp(prefix="imgb_")


def test_01_signal_announcement_proposes(): assert build()[0] == "IMAGE_CONFIRMED"
def test_02_position_ticket_no_signal(): assert build(semantic_class="POSITION_TICKET")[2] == "NOT_A_SIGNAL"
def test_03_position_management_no_signal(): assert build(semantic_class="POSITION_MANAGEMENT")[2] == "NOT_A_SIGNAL"
def test_04_result_claim_no_signal(): assert build(semantic_class="RESULT_CLAIM")[2] == "NOT_A_SIGNAL"
def test_05_analysis_only_no_signal(): assert build(semantic_class="ANALYSIS_ONLY")[2] == "NOT_A_SIGNAL"
def test_06_gold_accepted(): assert build(instrument="GOLD")[0] == "IMAGE_CONFIRMED"
def test_07_btc_rejected(): assert build(instrument="BTCUSD")[2] == "UNSUPPORTED_ASSET"


def test_08_direction_separate_from_entry():
    _, u, _ = build()
    assert u["direction"] == "BUY" and u["entry_low"] == "4000.00" and u["direction"] != u["entry_low"]


def test_09_entry_low_high_separate():
    _, u, _ = build(entry_low="4000.00", entry_high="4000.20")
    assert u["entry_low"] == "4000.00" and u["entry_high"] == "4000.20" and u["entry_low"] != u["entry_high"]


def test_10_single_entry_only_after_confirmation():
    assert build(entry_low=None, entry_high=None)[2] == "MISSING_ENTRY"          # pre-normalisation
    st, u, _ = build(entry_low="4070", entry_high="4070")                        # human-normalised
    assert st == "IMAGE_CONFIRMED" and u["entry_low"] == "4070" and u["entry_high"] == "4070"


def test_11_stop_separate():
    _, u, _ = build(stop_price="3990.00")
    assert u["stop_price"] == "3990.00" and u["stop_price"] != u["entry_low"]


def test_12_high_risk_is_label():
    assert "SIGNAL_RISK_LABEL" in image_profile.NON_NUMERIC_FIELDS
    assert decimals.parse_numeric("HIGH RISK")[0] is None                        # never a number


def test_13_super_low_lot_non_numeric():
    assert "SIGNAL_SIZE_COMMENT" in image_profile.NON_NUMERIC_FIELDS
    assert decimals.parse_numeric("SUPER LOW LOT")[0] is None


def test_14_ambiguous_digit_null():
    assert decimals.parse_numeric("40.0.5")[0] is None                # ambiguous placement -> NULL
    import paper_gate
    _, u, _ = build(entry_low="40??.5")                               # obscured digit
    assert paper_gate.decide(u, sess(), None)["status"] == "NEEDS_REVIEW"   # fails closed at gate
def test_15_ambiguous_decimal_null(): assert decimals.parse_numeric("4000,50")[1] == "AMBIGUOUS_DIGITS"
def test_16_no_arithmetic_reconstruction():
    assert vfw.reconcile_arithmetic(entry=None, exit_price="4020", displayed_profit="200")["computed_value"] is None


def test_17_provider_must_be_verified(): assert build(provider_verified=False)[2] == "PROVIDER_UNVERIFIED"
def test_18_folder_cannot_verify_provider():
    # even with a 'farouk' folder hint in the manifest, unverified provider fails closed
    st, u, r = bridge.build_image_unified_signal(approved(provider_verified=False),
        manifest(source_server_channel_text="farouk/gold"), REFS)
    assert r == "PROVIDER_UNVERIFIED" and u is None


def test_19_provider_pnl_rejected_all():
    try:
        vfw.calculate_account_r({"evidence_domain": "PROVIDER_DISPLAYED", "eligible_for_account_r": 0}); assert False
    except vfw.ProviderProfitFirewallError:
        pass
    try:
        reject_provider_pnl_from_outcome("PROVIDER_DISPLAYED"); assert False
    except PaperOutcomeFirewallError:
        pass


def test_20_post_time_differs_from_capture_import_confirm():
    a = approved(provider_posted_at=iso(1000000), human_confirmed_at=iso(1000600))
    m = manifest(screenshot_imported_at=iso(1000300), screenshot_captured_at=iso(999500))
    _, u, _ = bridge.build_image_unified_signal(a, m, REFS)
    times = {u["source_message_timestamp"], m["screenshot_imported_at"], u["confirmation_timestamp"],
             m["screenshot_captured_at"]}
    assert len(times) == 4                                                       # all distinct


def test_21_visible_time_without_date_incomplete():
    r = anchors(provenance="UNVERIFIABLE")
    assert r["PROVIDER_POST_TIME_RESULT"]["status"] == "PAPER_UNKNOWN" and \
        r["PROVIDER_POST_TIME_RESULT"]["reason"] == "POST_TIME_UNVERIFIABLE"


def test_22_unverifiable_post_time():
    assert anchors(provenance="UNVERIFIABLE")["PROVIDER_POST_TIME_RESULT"]["reason"] == "POST_TIME_UNVERIFIABLE"


def test_23_post_time_no_coverage():
    a = approved(provider_posted_at=iso(999000))
    _, u, _ = bridge.build_image_unified_signal(a, manifest(), REFS)
    r = bridge.run_three_anchors(u, sess(), None, provider_posted_at=iso(999000),
        provider_posted_provenance="DISCORD_MESSAGE_ID_OR_LINK",
        screenshot_imported_at=iso(1000600), human_confirmed_at=iso(1000600))
    assert r["PROVIDER_POST_TIME_RESULT"]["status"] == "PAPER_UNKNOWN" and \
        r["PROVIDER_POST_TIME_RESULT"]["reason"] == "NO_COVERAGE"


def test_24_manual_import_anchor():
    assert anchors()["MANUAL_IMPORT_TIME_RESULT"]["anchor"] == "MANUAL_IMPORT_TIME_RESULT"


def test_25_human_actionable_anchor():
    assert anchors()["HUMAN_CONFIRMED_ACTIONABLE_RESULT"]["anchor"] == "HUMAN_CONFIRMED_ACTIONABLE_RESULT"


def test_26_transport_not_telegram_delivery():
    r = anchors()
    for k, v in r.items():
        assert "Telegram" not in str(v.get("transport", "")).replace("NOT a Telegram", "")
        assert "MANUAL_DISCORD" in str(v.get("transport", "")) or v["status"] == "PAPER_UNKNOWN"


def test_27_buy_uses_ask():
    assert anchors(direction="BUY")["HUMAN_CONFIRMED_ACTIONABLE_RESULT"]["executable_side"] == "ASK"


def test_28_sell_uses_bid():
    assert anchors(direction="SELL", entry_low="3999.90", entry_high="4000.10"
                   )["HUMAN_CONFIRMED_ACTIONABLE_RESULT"]["executable_side"] == "BID"


def test_29_blocks_never_merge():
    ok = [{"signal_block_index": 1, "fields": [{"crop_sha256": "a"}]},
          {"signal_block_index": 2, "fields": [{"crop_sha256": "b"}]}]
    bad = [{"signal_block_index": 1, "fields": [{"crop_sha256": "a"}]},
           {"signal_block_index": 2, "fields": [{"crop_sha256": "a"}]}]
    assert image_profile.blocks_are_separated(ok) and not image_profile.blocks_are_separated(bad)


def test_30_unconfirmed_no_unified(): assert build(all_facts_human_confirmed=False)[2] == "UNCONFIRMED_FACTS"


def test_31_confirmation_creates_image_confirmed_only():
    st, u, _ = build()
    assert st == "IMAGE_CONFIRMED" and u["source_type"] == "IMAGE_CONFIRMED" and u["human_confirmed"] is True
    assert "order" not in u and "fill" not in u and "campaign" not in str(u).lower()


def test_32_duplicate_hash_import_idempotent():
    tmp = _tmp()
    try:
        sys.path.insert(0, _VIS)
        from stores import CandidateDB
        from ingest import make_png
        cdb = CandidateDB(os.path.join(tmp, "media_candidates_v1.db"))
        img = os.path.join(tmp, "s.png"); open(img, "wb").write(make_png(50, 40))
        m1, _ = image_intake.import_intake_image(img, candidate_db=cdb, root=os.path.join(tmp, "intake"))
        m2, _ = image_intake.import_intake_image(img, candidate_db=cdb, root=os.path.join(tmp, "intake"))
        assert m1["imported_media_id"] == m2["imported_media_id"] and m2["duplicate"] is True
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_33_duplicate_source_ref_no_dup_unified():
    tmp = _tmp()
    try:
        db = ImageBridgeDB(os.path.join(tmp, "ib.db"))
        kw = dict(paper_observation_id="p1", intake_id="i1", original_image_sha256="a" * 64,
                  crop_hashes=["c"], review_decision_ids=["r"], timestamp_provenance="UNVERIFIABLE",
                  provider_post_result={}, manual_import_result={}, human_confirmed_actionable_result={},
                  latencies={})
        db.record(bridge_obs_id="ib-1", **kw)
        try:
            db.record(bridge_obs_id="ib-1", **kw); assert False
        except sqlite3.IntegrityError:
            pass
        assert db.count() == 1
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_34_q4a_hashes_unchanged():
    def s(p): return hashlib.sha256(open(p, "rb").read()).hexdigest()[:16]
    assert s(os.path.join(_Q4, "kernel.py")) == HASHES["kernel.py"]
    assert s(os.path.join(_Q4, "q4_config.py")) == HASHES["q4_config.py"]


def test_35_paper_loop_code_unchanged():
    def s(p): return hashlib.sha256(open(p, "rb").read()).hexdigest()[:16]
    assert s(os.path.join(_PL, "paper_gate.py")) == HASHES["paper_gate.py"]
    assert s(os.path.join(_PL, "paper_db.py")) == HASHES["paper_db.py"]


def test_36_paper_db_append_only():
    tmp = _tmp()
    try:
        db = PaperDB(os.path.join(tmp, "p.db"))
        db.conn.execute("INSERT INTO paper_observations (observation_id,provider_id,status) VALUES ('o','FAROUK','PAPER_READY')")
        db.conn.commit()
        for sql in ("UPDATE paper_observations SET status='x'", "DELETE FROM paper_observations"):
            try:
                db.conn.execute(sql); db.conn.commit(); assert False
            except sqlite3.IntegrityError:
                pass
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_37_no_campaign_db():
    src = "".join(open(p, encoding="utf-8").read() for p in glob.glob(os.path.join(_PL, "image_*.py")))
    for bad in ("campaign_v1.db", "mpk_campaigns", "mpk_registry", "write_campaign"):
        assert bad not in src


def test_38_no_broker_order_path():
    from broker_readonly.source_scan import scan_no_order_code
    assert scan_no_order_code([_PL]) == []


def test_39_execution_locks():
    cfg = open(os.path.join(_ROOT, "config.py"), encoding="utf-8").read()
    cc = open(os.path.join(_ROOT, "ctrader_config.py"), encoding="utf-8").read()
    assert 'MODE = "PAPER"' in cfg and "EXECUTION_ENABLED = False" in cfg and "CTRADER_EXECUTION_ENABLED = False" in cc


def test_40_protected_truth():
    def s(p): return hashlib.sha256(open(p, "rb").read()).hexdigest()[:16]
    mpk = os.path.join(_ROOT, "campaign_extractor", "mpk", "data")
    assert s(os.path.join(mpk, "mpk_campaigns_v1.db")) == "6895a1cb71fd93ba"
    assert s(os.path.join(mpk, "mpk_registry_v1.db")) == "c03e928f21ec94ae"


def test_41_no_process_disturbance_code():
    src = "".join(open(p, encoding="utf-8").read() for p in glob.glob(os.path.join(_PL, "image_*.py")))
    for bad in ("Stop-Process", "module_a_telegram", "subscribe_and_capture", "connect_and_read",
                "kill", "taskkill"):
        assert bad not in src


def test_42_inbox_cannot_bypass_import_review():
    # intake ALWAYS immutably imports (records ingested_images); the adapter refuses unconfirmed facts
    tmp = _tmp()
    try:
        sys.path.insert(0, _VIS)
        from stores import CandidateDB
        from ingest import make_png
        cdb = CandidateDB(os.path.join(tmp, "m.db"))
        img = os.path.join(tmp, "x.png"); open(img, "wb").write(make_png(40, 30))
        m, _ = image_intake.import_intake_image(img, candidate_db=cdb, root=os.path.join(tmp, "intake"))
        assert cdb.get_image_by_sha(m["original_image_sha256"]) is not None    # immutably imported
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    assert build(all_facts_human_confirmed=False)[1] is None                    # no bypass to signal
