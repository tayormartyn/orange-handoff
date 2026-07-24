"""
test_archive.py — the eight Phase-1 acceptance tests for the permanent archive.

All deterministic, no Telegram, no API. Each test runs against its own temporary
SQLite DB. Run:  python test_archive.py   (also pytest-compatible).
"""

import os
import shutil
import tempfile

import archive as A
import module_a_telegram as listener


# ----------------------------------------------------------------------------
# helpers
# ----------------------------------------------------------------------------
_T = 0


def _ts(n):
    return f"2026-01-0{n}T10:00:00+00:00" if n < 10 else f"2026-01-{n}T10:00:00+00:00"


def _msg(channel, mid, text, sent, asset="", direction="", entry="", stop="",
         tp1="", tp2="", tp3=""):
    return {"channel_id": channel, "message_id": str(mid), "raw_text": text,
            "sent_at_utc": sent, "edited_at_utc": "", "sender": "farouk",
            "classification": "clean signal" if (asset and direction and entry) else "commentary",
            "asset": asset, "direction": direction, "entry": entry, "stop": stop,
            "tp1": tp1, "tp2": tp2, "tp3": tp3}


def _fresh_db():
    d = tempfile.mkdtemp(prefix="arch_test_")
    return d, os.path.join(d, "t.db")


def _count(conn, table):
    return conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]


def _gold_signal(channel="c1", mid=1, sent=None):
    sent = sent or _ts(1)
    return _msg(channel, mid, "XAUUSD buy 4000-4010 sl 3980 tp1 4030 tp2 4050 tp3 4090",
                sent, "XAUUSD", "LONG", "4000-4010", "3980", "4030", "4050", "4090")


# ----------------------------------------------------------------------------
# 1. Import the same pull twice -> no duplicate messages / signals.
# ----------------------------------------------------------------------------
def test_import_same_pull_twice_no_duplicates():
    d, db = _fresh_db()
    try:
        conn = A.connect(db)
        recs = [_gold_signal(mid=1), _msg("c1", 2, "tp1 hit", _ts(2))]
        s1 = A.import_messages(conn, recs)
        m1, g1 = _count(conn, "raw_message_versions"), _count(conn, "signals")
        s2 = A.import_messages(conn, recs)             # same pull again
        m2, g2 = _count(conn, "raw_message_versions"), _count(conn, "signals")
        assert m1 == m2 == 2, (m1, m2)
        assert g1 == g2 == 1, (g1, g2)
        assert s2["duplicates_skipped"] == 2 and s2["messages_inserted"] == 0
        conn.close()
    finally:
        shutil.rmtree(d, ignore_errors=True)


# ----------------------------------------------------------------------------
# 2. Import an overlapping pull -> only genuinely new messages added.
# ----------------------------------------------------------------------------
def test_overlapping_pull_adds_only_new():
    d, db = _fresh_db()
    try:
        conn = A.connect(db)
        A.import_messages(conn, [_msg("c1", 1, "A", _ts(1)),
                                 _msg("c1", 2, "B", _ts(2)),
                                 _msg("c1", 3, "C", _ts(3))])
        s = A.import_messages(conn, [_msg("c1", 2, "B", _ts(2)),
                                     _msg("c1", 3, "C", _ts(3)),
                                     _msg("c1", 4, "D", _ts(4))])
        assert s["messages_inserted"] == 1 and s["duplicates_skipped"] == 2
        assert _count(conn, "raw_message_versions") == 4
        conn.close()
    finally:
        shutil.rmtree(d, ignore_errors=True)


# ----------------------------------------------------------------------------
# 3. Telegram window slides -> previously-archived signals REMAIN.
# ----------------------------------------------------------------------------
def test_window_slides_old_signals_remain():
    d, db = _fresh_db()
    try:
        conn = A.connect(db)
        A.import_messages(conn, [_gold_signal(mid=1, sent=_ts(1))])
        sid_old = _signal_keys(conn)
        # a later, non-overlapping pull (the window has slid forward)
        A.import_messages(conn, [_msg("c1", 50, "XAUUSD sell 4200-4210 sl 4230 tp1 4180",
                                      _ts(5), "XAUUSD", "SHORT", "4200-4210", "4230", "4180")])
        keys_now = _signal_keys(conn)
        assert sid_old.issubset(keys_now)              # the old signal still present
        assert _count(conn, "signals") == 2
        conn.close()
    finally:
        shutil.rmtree(d, ignore_errors=True)


def _signal_keys(conn):
    return {r["source_message_key"] for r in conn.execute(
        "SELECT source_message_key FROM signals").fetchall()}


# ----------------------------------------------------------------------------
# 4. A later TP message updates the RIGHT signal's projection, no duplicate signal.
# ----------------------------------------------------------------------------
def test_later_tp_updates_projection_no_duplicate_signal():
    d, db = _fresh_db()
    try:
        conn = A.connect(db)
        A.import_messages(conn, [_gold_signal(mid=1, sent=_ts(1))])
        A.rebuild_projections(conn)
        before = conn.execute("SELECT outcome_category, binary_rollup FROM outcome_projections"
                              ).fetchone()
        assert before["binary_rollup"] != "win"        # no result yet
        n_sig = _count(conn, "signals")
        # the TP confirmation arrives in a LATER pull
        A.import_messages(conn, [_msg("c1", 2, "tp1 hit", _ts(2))])
        A.rebuild_projections(conn)
        after = conn.execute("SELECT outcome_category, binary_rollup FROM outcome_projections"
                             ).fetchone()
        assert after["binary_rollup"] == "win"
        assert after["outcome_category"] == listener.OUT_TARGET_HIT
        assert _count(conn, "signals") == n_sig        # NO duplicate signal
        conn.close()
    finally:
        shutil.rmtree(d, ignore_errors=True)


# ----------------------------------------------------------------------------
# 5. Post-re-entry TP does NOT leak backwards into the parent (stored accepted=0).
# ----------------------------------------------------------------------------
def test_post_reentry_tp_not_leaked_and_stored_rejected():
    d, db = _fresh_db()
    try:
        conn = A.connect(db)
        recs = [_gold_signal(mid=1, sent=_ts(1)),
                _msg("c1", 2, "50 pips", _ts(2)),
                _msg("c1", 3, "Re-enter playing it out", _ts(3)),
                _msg("c1", 4, "take tp 3 170 pips", _ts(4))]
        A.import_messages(conn, recs)
        A.rebuild_projections(conn)
        proj = conn.execute("SELECT outcome_category, binary_rollup, primary_evidence_message_key "
                            "FROM outcome_projections").fetchone()
        # parent scored to the PRE-re-entry 50 pips, NOT the post-re-entry 170/tp3
        assert proj["binary_rollup"] == "win"
        assert proj["outcome_category"] == listener.OUT_MANAGED_PROFIT
        post_key = A._message_key("c1", 4)
        assert proj["primary_evidence_message_key"] != post_key
        # the post-re-entry message is recorded as REJECTED evidence (not dropped)
        rej = conn.execute(
            "SELECT accepted, rejection_reason FROM outcome_evidence "
            "WHERE evidence_message_key=?", (post_key,)).fetchone()
        assert rej is not None and rej["accepted"] == 0
        assert rej["rejection_reason"] == "POST_REENTRY_BOUNDARY"
        conn.close()
    finally:
        shutil.rmtree(d, ignore_errors=True)


# ----------------------------------------------------------------------------
# 6. A manual override SURVIVES a parser/projection re-run.
# ----------------------------------------------------------------------------
def test_manual_override_survives_rerun():
    d, db = _fresh_db()
    try:
        conn = A.connect(db)
        A.import_messages(conn, [_gold_signal(mid=1, sent=_ts(1)),
                                 _msg("c1", 2, "tp1 hit", _ts(2))])
        A.rebuild_projections(conn)
        sid = conn.execute("SELECT signal_id FROM signals").fetchone()["signal_id"]
        auto = conn.execute("SELECT outcome_category FROM outcome_projections WHERE signal_id=?",
                            (sid,)).fetchone()["outcome_category"]
        assert auto == listener.OUT_TARGET_HIT
        # operator overrides it to a manual loss
        A.add_override(conn, sid, "outcome_category",
                       {"outcome_category": "manual_loss", "calculated_r": "-1",
                        "r_is_known": True},
                       reason="audit: trade was actually cut for a loss")
        A.rebuild_projections(conn)                    # the auto-run must NOT replace it
        p = conn.execute("SELECT outcome_category, binary_rollup, source, override_conflict "
                         "FROM outcome_projections WHERE signal_id=?", (sid,)).fetchone()
        assert p["outcome_category"] == "manual_loss"
        assert p["binary_rollup"] == "loss"
        assert p["source"] == "override"
        assert p["override_conflict"]                  # the conflict is REPORTED, not silently lost
        assert A.active_override(conn, sid) is not None
        conn.close()
    finally:
        shutil.rmtree(d, ignore_errors=True)


# ----------------------------------------------------------------------------
# 7. Crash mid-import -> transaction rolls back, no partial batch.
# ----------------------------------------------------------------------------
def test_crash_mid_import_rolls_back():
    d, db = _fresh_db()
    try:
        conn = A.connect(db)
        A.import_messages(conn, [_msg("c1", 1, "A", _ts(1))])     # one good batch
        m0, b0 = _count(conn, "raw_message_versions"), _count(conn, "import_batches")
        crashed = False
        try:
            A.import_messages(conn, [_msg("c1", 2, "B", _ts(2)),
                                     _msg("c1", 3, "C", _ts(3)),
                                     _msg("c1", 4, "D", _ts(4))], _fail_after=2)
        except RuntimeError:
            crashed = True
        assert crashed
        # nothing from the failed import persisted: same message + batch counts
        assert _count(conn, "raw_message_versions") == m0
        assert _count(conn, "import_batches") == b0
        conn.close()
    finally:
        shutil.rmtree(d, ignore_errors=True)


# ----------------------------------------------------------------------------
# 8. Two exports from an unchanged DB -> identical signal data.
# ----------------------------------------------------------------------------
def test_two_exports_identical():
    d, db = _fresh_db()
    try:
        conn = A.connect(db)
        A.import_messages(conn, [_gold_signal(mid=1, sent=_ts(1)),
                                 _msg("c1", 2, "tp1 hit", _ts(2)),
                                 _msg("c1", 5, "XAUUSD sell 4200-4210 sl 4230 tp1 4180",
                                      _ts(5), "XAUUSD", "SHORT", "4200-4210", "4230", "4180")])
        A.rebuild_projections(conn)
        p1, p2 = os.path.join(d, "e1.csv"), os.path.join(d, "e2.csv")
        A.export_csv(conn, p1)
        A.export_csv(conn, p2)
        with open(p1, encoding="utf-8") as f1, open(p2, encoding="utf-8") as f2:
            assert f1.read() == f2.read()
        conn.close()
    finally:
        shutil.rmtree(d, ignore_errors=True)


# ----------------------------------------------------------------------------
# Timestamp + price-context capture (groundwork for shadow mode — NOT shadow mode)
# ----------------------------------------------------------------------------
def _live_signal(channel="c1", mid=1, posted=None, received=None, parsed=None):
    r = _gold_signal(channel=channel, mid=mid, sent=posted or "2026-01-01T10:00:00+00:00")
    r["listener_received_at"] = received or ""
    r["parsed_at"] = parsed or ""
    return r


def test_timing_captured_at_each_stage():
    d, db = _fresh_db()
    try:
        conn = A.connect(db)
        rec = _live_signal(posted="2026-01-01T10:00:00+00:00",
                           received="2026-01-01T10:00:03+00:00",
                           parsed="2026-01-01T10:00:03.500000+00:00")
        A.import_messages(conn, [rec])
        sid = conn.execute("SELECT signal_id FROM signals").fetchone()["signal_id"]
        t = A.get_timing(conn, sid)
        assert t is not None
        assert t["telegram_posted_at"] == "2026-01-01T10:00:00+00:00"
        assert t["listener_received_at"] == "2026-01-01T10:00:03+00:00"
        assert t["parsed_at"] == "2026-01-01T10:00:03.500000+00:00"
        conn.close()
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_delay_calculation_between_stages():
    d, db = _fresh_db()
    try:
        conn = A.connect(db)
        rec = _live_signal(posted="2026-01-01T10:00:00+00:00",
                           received="2026-01-01T10:00:03+00:00",
                           parsed="2026-01-01T10:00:03.500000+00:00")
        A.import_messages(conn, [rec])
        sid = conn.execute("SELECT signal_id FROM signals").fetchone()["signal_id"]
        t = A.get_timing(conn, sid)
        assert t["received_minus_posted_sec"] == 3.0
        assert t["parsed_minus_received_sec"] == 0.5
        conn.close()
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_delay_seconds_helper_units():
    # direct unit test of the delay helper, incl. the historical baseline format
    assert A._delay_seconds("2026-01-01T10:00:05+00:00", "2026-01-01T10:00:00+00:00") == 5.0
    assert A._delay_seconds("2026-05-25 09:51", "2026-05-25 09:50") == 60.0
    assert A._delay_seconds("", "2026-01-01T10:00:00+00:00") is None   # missing endpoint
    assert A._delay_seconds("not-a-date", "2026-01-01T10:00:00+00:00") is None


def test_baseline_record_has_posted_only_delays_null():
    # historical back-fill: only the telegram timestamp is known -> delays NULL.
    d, db = _fresh_db()
    try:
        conn = A.connect(db)
        rec = _gold_signal(mid=1, sent="2026-05-25 09:50")   # no received/parsed
        A.import_messages(conn, [rec])
        sid = conn.execute("SELECT signal_id FROM signals").fetchone()["signal_id"]
        t = A.get_timing(conn, sid)
        assert t["telegram_posted_at"] == "2026-05-25 09:50"
        assert t["listener_received_at"] is None
        assert t["parsed_at"] is None
        assert t["received_minus_posted_sec"] is None
        assert t["parsed_minus_received_sec"] is None
        conn.close()
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_price_context_captured_with_market_price_placeholder():
    import json
    d, db = _fresh_db()
    try:
        conn = A.connect(db)
        A.import_messages(conn, [_live_signal()])
        sid = conn.execute("SELECT signal_id FROM signals").fetchone()["signal_id"]
        t = A.get_timing(conn, sid)
        pc = json.loads(t["price_context"])
        # the signal's own levels + any message prices are captured...
        assert pc["signal_entry_low"] == "4000" and pc["signal_entry_high"] == "4010"
        assert "4030" in pc["message_prices"]
        # ...and the real market price is a CLEARLY-LABELLED, currently-null slot.
        assert pc["market_price"] is None
        assert pc["market_price_source"] is None
        assert "shadow-mode" in pc["note"].lower()
        conn.close()
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_timing_is_append_only_idempotent():
    d, db = _fresh_db()
    try:
        conn = A.connect(db)
        rec = _live_signal(received="2026-01-01T10:00:03+00:00",
                           parsed="2026-01-01T10:00:03.500000+00:00")
        A.import_messages(conn, [rec])
        sid = conn.execute("SELECT signal_id FROM signals").fetchone()["signal_id"]
        first = A.get_timing(conn, sid)
        # re-import the same signal with DIFFERENT stage times -> original is kept
        rec2 = _live_signal(received="2026-01-01T11:00:00+00:00",
                            parsed="2026-01-01T11:00:09+00:00")
        A.import_messages(conn, [rec2])
        rows = conn.execute("SELECT COUNT(*) FROM signal_timing WHERE signal_id=?",
                            (sid,)).fetchone()[0]
        again = A.get_timing(conn, sid)
        assert rows == 1                                   # never duplicated
        assert again["listener_received_at"] == first["listener_received_at"]  # never overwritten
        assert again["received_minus_posted_sec"] == first["received_minus_posted_sec"]
        conn.close()
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_every_signal_gets_timing_row():
    d, db = _fresh_db()
    try:
        conn = A.connect(db)
        A.import_messages(conn, [_live_signal(mid=1),
                                 _msg("c1", 5, "XAUUSD sell 4200-4210 sl 4230 tp1 4180",
                                      _ts(5), "XAUUSD", "SHORT", "4200-4210", "4230", "4180")])
        A.rebuild_projections(conn)
        ok, problems = A.integrity_check(conn)
        assert ok, problems
        assert A.timing_summary(conn)["timing_rows"] == 2
        conn.close()
    finally:
        shutil.rmtree(d, ignore_errors=True)


# ----------------------------------------------------------------------------
# Minimal runner
# ----------------------------------------------------------------------------
def _run():
    tests = [v for k, v in sorted(globals().items())
             if k.startswith("test_") and callable(v)]
    passed = failed = 0
    print("=" * 64)
    print("  ARCHIVE — PHASE 1 ACCEPTANCE TESTS")
    print("=" * 64)
    for fn in tests:
        try:
            fn()
            print(f"  PASS  {fn.__name__}")
            passed += 1
        except AssertionError as e:
            print(f"  FAIL  {fn.__name__}: {e}")
            failed += 1
        except Exception as e:                       # noqa: BLE001
            import traceback
            print(f"  ERROR {fn.__name__}: {type(e).__name__}: {e}")
            traceback.print_exc()
            failed += 1
    print("-" * 64)
    print(f"  {passed} passed, {failed} failed, {len(tests)} total")
    print("=" * 64)
    return failed == 0


if __name__ == "__main__":
    import sys
    sys.exit(0 if _run() else 1)
