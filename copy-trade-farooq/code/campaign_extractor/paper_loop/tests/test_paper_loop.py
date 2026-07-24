"""Unified Paper Loop V0.1 offline tests (30). Synthetic quotes/signals; reuses Q4A unchanged."""
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
for p in (_ROOT, _CE, _Q4, _PL):
    if p not in sys.path:
        sys.path.insert(0, p)

import paper_gate
import alert as alertmod
import inventory
from paper_db import PaperDB, reject_provider_pnl_from_outcome, PaperOutcomeFirewallError
from unified_signal import build_unified
import kernel as q4a


def iso(ms):
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).isoformat().replace("+00:00", "Z")


def q(seq, wall, mono, bid, ask, bid_prov=None, ask_prov=None):
    return {"session": "S", "seq": seq, "symbol_id": 41,
            "raw_bid": int(bid * 100000) if bid else None, "raw_ask": int(ask * 100000) if ask else None,
            "broker_ts": 5_000_000 + seq, "wall_ms": wall, "mono_ns": mono, "bid": bid, "ask": ask,
            "spread": round(ask - bid, 2) if (bid and ask) else None, "flags": "OK",
            "bid_prov_seq": bid_prov or (seq if bid else None),
            "ask_prov_seq": ask_prov or (seq if ask else None)}


def sess(n=5, wall0=1000000, step=500, bid0=4000.00, spread=0.10, ask=True):
    return [q(i + 1, wall0 + i * step, i * step * 1_000_000, round(bid0 + 0.01 * i, 2),
              round(bid0 + 0.01 * i + spread, 2) if ask else None) for i in range(n)]


def sig(direction="BUY", low="4000.00", high="4000.20", provider="FAROUK", instrument="XAUUSD",
        received=1000600, parsed=1000600, human=True, evidence=("ev1",), stype="TEXT", stop=None):
    return build_unified(provider_id=provider, source_channel_id="-1001902136163",
        source_message_id="45999", source_message_timestamp=iso(received - 2000),
        listener_received_at=iso(received), parsed_at=iso(parsed) if parsed is not None else None,
        source_type=stype, instrument=instrument, direction=direction, entry_low=low, entry_high=high,
        stop_price=stop, target_prices=None, source_evidence_references=list(evidence),
        human_confirmed=human, reviewer_reference="martyn",
        confirmation_timestamp=iso(received + 1000))


def _tmp():
    return tempfile.mkdtemp(prefix="paper_")


def test_01_buy_uses_ask():
    d = paper_gate.decide(sig("BUY"), sess())
    assert d["actionable"]["executable_side"] == "ASK"


def test_02_sell_uses_bid():
    d = paper_gate.decide(sig("SELL"), sess())
    assert d["actionable"]["executable_side"] == "BID"


def test_03_inside_zone_ready():
    assert paper_gate.decide(sig("BUY", "4000.00", "4000.20"), sess())["status"] == "PAPER_READY"


def test_04_outside_zone():
    d = paper_gate.decide(sig("BUY", "4000.00", "4000.11"), sess())   # ask 4000.12 > 4000.11
    assert d["status"] == "PAPER_OUTSIDE_ZONE"


def test_05_no_coverage_unknown():
    d = paper_gate.decide(sig("BUY", received=999000, parsed=999000), sess())
    assert d["status"] == "PAPER_UNKNOWN" and d["reason"] == "NO_COVERAGE"


def test_06_missing_range_needs_review():
    d = paper_gate.decide(sig("BUY", low=None, high=None), sess())
    assert d["status"] == "NEEDS_REVIEW" and "ENTRY_RANGE_MISSING" in d["validation_errors"]


def test_07_ambiguous_direction_needs_review():
    d = paper_gate.decide(sig("HOLD"), sess())
    assert d["status"] == "NEEDS_REVIEW" and "AMBIGUOUS_DIRECTION" in d["validation_errors"]


def test_08_unconfirmed_needs_review():
    d = paper_gate.decide(sig("BUY", human=False), sess())
    assert d["status"] == "NEEDS_REVIEW" and "NOT_HUMAN_CONFIRMED" in d["validation_errors"]


def test_09_btc_cannot_enter_gold_loop():
    d = paper_gate.decide(sig("BUY", instrument="BTCUSD"), sess())
    assert d["status"] == "NEEDS_REVIEW" and "UNSUPPORTED_ASSET" in d["validation_errors"]


def test_10_invalid_range_fails_closed():
    d = paper_gate.decide(sig("BUY", low="abc", high="4000.20"), sess())
    assert d["status"] == "NEEDS_REVIEW" and "ENTRY_RANGE_INVALID" in d["validation_errors"]


def test_11_stale_ask_fails_closed():
    s = sess(step=1000)
    for x in s:
        if x["seq"] == 3:
            x["ask_prov_seq"] = 1                                  # ask 2000ms old
    d = paper_gate.decide(sig("BUY", received=1001500, parsed=1001500), s)
    assert d["status"] == "PAPER_UNKNOWN" and d["reason"] == "STALE_ASK"


def test_12_stale_bid_fails_closed():
    s = sess(step=1000)
    for x in s:
        if x["seq"] == 3:
            x["bid_prov_seq"] = 1
    d = paper_gate.decide(sig("SELL", received=1001500, parsed=1001500), s)
    assert d["status"] == "PAPER_UNKNOWN" and d["reason"] == "STALE_BID"


def test_13_missing_side_fails_closed():
    d = paper_gate.decide(sig("BUY"), sess(ask=False))
    assert d["status"] == "PAPER_UNKNOWN" and d["reason"] == "MISSING_ASK"


def test_14_both_anchors_preserved():
    d = paper_gate.decide(sig("BUY"), sess())
    assert d["delivery"] is not None and d["actionable"] is not None


def test_15_provider_isolation():
    tmp = _tmp()
    try:
        db = PaperDB(os.path.join(tmp, "paper_observations_v1.db"))
        db.record(paper_gate.decide(sig("BUY", provider="FAROUK"), sess()),
                  observation_id="o1", provider_id="FAROUK")
        db.record(paper_gate.decide(sig("BUY", provider="RUPES", instrument="XAUUSD"), sess()),
                  observation_id="o2", provider_id="RUPES")
        assert len(db.by_provider("FAROUK")) == 1 and len(db.by_provider("RUPES")) == 1
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_16_farouk_not_in_rupes_ledger():
    tmp = _tmp()
    try:
        db = PaperDB(os.path.join(tmp, "p.db"))
        db.record(paper_gate.decide(sig("BUY", provider="FAROUK"), sess()),
                  observation_id="f1", provider_id="FAROUK")
        assert db.by_provider("RUPES") == []
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_17_provider_pnl_rejected():
    try:
        reject_provider_pnl_from_outcome("PROVIDER_DISPLAYED"); assert False
    except PaperOutcomeFirewallError:
        pass
    assert reject_provider_pnl_from_outcome("VISIBLE_TRADE_FACT") is True


def test_18_no_fill_asserted():
    d = paper_gate.decide(sig("BUY"), sess())
    a = alertmod.format_alert(d, observation_id="o", provider_id="FAROUK")
    assert "NOT_A_FILL" in a["labels"] and "NOT A FILL" in a["banner"]
    # no field asserts an actual fill/execution
    for k in list(d.keys()) + list(a.keys()):
        assert k.lower() not in ("fill_price", "filled", "executed", "fill", "execution_price")


def test_19_no_outcome_asserted():
    tmp = _tmp()
    try:
        db = PaperDB(os.path.join(tmp, "p.db"))
        cols = [r[1] for r in db.conn.execute("PRAGMA table_info(paper_observations)")]
        for banned in ("pnl", "profit", "realised", "outcome_r", "campaign_r", "expectancy", "win", "loss"):
            assert not any(banned in c.lower() for c in cols)
        db.close()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_20_update_prohibited():
    tmp = _tmp()
    try:
        db = PaperDB(os.path.join(tmp, "p.db"))
        db.record(paper_gate.decide(sig("BUY"), sess()), observation_id="o1", provider_id="FAROUK")
        try:
            db.conn.execute("UPDATE paper_observations SET status='X'"); db.conn.commit(); assert False
        except sqlite3.IntegrityError:
            pass
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_21_delete_prohibited():
    tmp = _tmp()
    try:
        db = PaperDB(os.path.join(tmp, "p.db"))
        db.record(paper_gate.decide(sig("BUY"), sess()), observation_id="o1", provider_id="FAROUK")
        try:
            db.conn.execute("DELETE FROM paper_observations"); db.conn.commit(); assert False
        except sqlite3.IntegrityError:
            pass
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_22_superseding_preserves_original():
    tmp = _tmp()
    try:
        db = PaperDB(os.path.join(tmp, "p.db"))
        db.record(paper_gate.decide(sig("BUY"), sess()), observation_id="orig", provider_id="FAROUK")
        db.record(paper_gate.decide(sig("BUY", low="4000.05"), sess()), observation_id="corr",
                  provider_id="FAROUK", supersedes_observation_id="orig")
        ids = [r[0] for r in db.conn.execute("SELECT observation_id FROM paper_observations")]
        assert "orig" in ids and "corr" in ids and db.count() == 2
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_23_no_campaign_db():
    src = "".join(open(p, encoding="utf-8").read() for p in glob.glob(os.path.join(_PL, "*.py")))
    for bad in ("campaign_v1.db", "mpk_campaigns", "mpk_registry", "write_campaign"):
        assert bad not in src
    viol = []
    orig = sqlite3.connect
    def guard(t, *a, **k):
        if any(m in str(t).lower() for m in ("campaign", "mpk_")):
            viol.append(str(t)); raise RuntimeError("campaign open")
        return orig(t, *a, **k)
    sqlite3.connect = guard
    try:
        tmp = _tmp()
        try:
            PaperDB(os.path.join(tmp, "p.db")).close()
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    finally:
        sqlite3.connect = orig
    assert viol == []


def test_24_q4a_unchanged():
    assert q4a.INSIDE == "INSIDE_ZONE" and q4a.OUTSIDE == "OUTSIDE_ZONE" and q4a.UNKNOWN == "UNKNOWN"
    assert hasattr(q4a, "align") and q4a.LABELS["fill"] == "NOT_A_FILL"


def test_25_protected_truth():
    def s16(p):
        return hashlib.sha256(open(p, "rb").read()).hexdigest()[:16]
    mpk = os.path.join(_ROOT, "campaign_extractor", "mpk", "data")
    assert s16(os.path.join(mpk, "mpk_campaigns_v1.db")) == "6895a1cb71fd93ba"
    assert s16(os.path.join(mpk, "mpk_registry_v1.db")) == "c03e928f21ec94ae"


def test_26_execution_locks():
    cfg = open(os.path.join(_ROOT, "config.py"), encoding="utf-8").read()
    cc = open(os.path.join(_ROOT, "ctrader_config.py"), encoding="utf-8").read()
    assert 'MODE = "PAPER"' in cfg and "EXECUTION_ENABLED = False" in cfg
    assert "CTRADER_EXECUTION_ENABLED = False" in cc


def test_27_no_broker_order_path():
    sys.path.insert(0, _CE)
    from broker_readonly.source_scan import scan_no_order_code
    assert scan_no_order_code([_PL]) == []


def test_28_alert_paper_only():
    a = alertmod.format_alert(paper_gate.decide(sig("BUY"), sess()), observation_id="o", provider_id="FAROUK")
    assert a["banner"] == "PAPER ONLY / NOT A FILL" and set(["OBSERVATION_ONLY", "PAPER_ONLY",
        "NOT_A_FILL", "NOT_AN_OUTCOME"]).issubset(set(a["labels"]))


def test_29_duplicate_idempotent():
    tmp = _tmp()
    try:
        db = PaperDB(os.path.join(tmp, "p.db"))
        d = paper_gate.decide(sig("BUY"), sess())
        db.record(d, observation_id="dup", provider_id="FAROUK")
        try:
            db.record(d, observation_id="dup", provider_id="FAROUK"); assert False
        except sqlite3.IntegrityError:
            pass                                                  # UNIQUE prevents duplicate
        assert db.count() == 1
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_30_no_second_ctrader_connection():
    src = "".join(open(p, encoding="utf-8").read() for p in glob.glob(os.path.join(_PL, "*.py")))
    for bad in ("connect_and_read", "subscribe_and_capture", "ctrader_open_api", "startService",
                "TcpProtocol", "reactor.run"):
        assert bad not in src                                     # paper loop opens no broker connection
