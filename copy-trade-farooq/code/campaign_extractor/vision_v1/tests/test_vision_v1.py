"""Vision V1 offline tests (25). Synthetic fixture-1 data; no real image, no vision model, no network."""
from __future__ import annotations
import os
import shutil
import sqlite3
import sys
import tempfile

_HERE = os.path.dirname(os.path.abspath(__file__))
_VIS = os.path.dirname(_HERE)
_CE = os.path.dirname(_VIS)
_ROOT = os.path.dirname(_CE)
for p in (_ROOT, _CE, _VIS):          # _VIS inserted last -> searched first (shadows root pipeline.py)
    if p not in sys.path:
        sys.path.insert(0, p)

import ingest
import firewalls
import extraction
from stores import CandidateDB, ReviewDB
from pipeline import run_extraction, _review_status
from review_gate import apply_review
from extraction import MockFixture1Extractor, dual_reading, classify_instrument, associate_gold


def build(tmp, run=True):
    img = os.path.join(tmp, "btc.png")
    with open(img, "wb") as f:
        f.write(ingest.make_png(160, 90))
    sha = ingest.sha256_file(img)
    cdb = CandidateDB(os.path.join(tmp, "media_candidates_v1.db"))
    rdb = ReviewDB(os.path.join(tmp, "media_reviews_v1.db"))
    mid, created = ingest.ingest_image(img, cdb, dest_root=os.path.join(tmp, "vision_fixtures_v1"))
    summary = run_extraction(mid, sha, MockFixture1Extractor(), cdb) if run else None
    return {"img": img, "sha": sha, "cdb": cdb, "rdb": rdb, "mid": mid, "created": created,
            "summary": summary}


def cands_by(cdb, mid, **where):
    cur = cdb.conn.execute("SELECT * FROM field_candidates WHERE media_id=?", (mid,))
    cols = [d[0] for d in cur.description]
    out = [dict(zip(cols, r)) for r in cur.fetchall()]
    for k, v in where.items():
        out = [c for c in out if c.get(k) == v]
    return out


def _run(fn):
    tmp = tempfile.mkdtemp(prefix="vis_")
    try:
        return fn(tmp)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_01_original_hashed_immutable():
    def f(tmp):
        e = build(tmp, run=False)
        rec = e["cdb"].get_image_by_sha(e["sha"])
        assert rec and rec["sha256"] == e["sha"]
        stored = os.path.join(tmp, "vision_fixtures_v1", e["mid"], f"original_{e['sha']}.png")
        assert os.path.exists(stored) and not os.access(stored, os.W_OK)   # read-only original
    _run(f)


def test_02_derived_preserves_original_hash():
    def f(tmp):
        e = build(tmp, run=False)
        d = ingest.register_derived(e["cdb"], media_id=e["mid"], original_sha256=e["sha"],
                                    artifact_type="CROP", path_bytes=b"cropbytes", region_id="r1")
        row = e["cdb"].conn.execute("SELECT original_sha256 FROM derived_artifacts WHERE sha256=?",
                                    (d,)).fetchone()
        assert row[0] == e["sha"] and d != e["sha"]
    _run(f)


def test_03_instrument_btc_never_gold():
    def f(tmp):
        e = build(tmp)
        inst = cands_by(e["cdb"], e["mid"], field_type="INSTRUMENT")[0]
        assert inst["candidate_value_string"] == "BTCUSD"
        assert classify_instrument("BTCUSD") == "BTCUSD"
        assert classify_instrument("BTCUSD") != "XAUUSD"
        try:
            associate_gold("BTCUSD"); assert False
        except extraction.GoldAssociationBlocked:
            pass
    _run(f)


def test_04_exactly_two_ticket_regions():
    def f(tmp):
        e = build(tmp)
        assert len(e["cdb"].regions_of_type(e["mid"], "TICKET_1")) == 1
        assert len(e["cdb"].regions_of_type(e["mid"], "TICKET_2")) == 1
    _run(f)


def test_05_entry_candidates_separate():
    def f(tmp):
        e = build(tmp)
        entries = cands_by(e["cdb"], e["mid"], field_type="ENTRY_PRICE")
        vals = {c["candidate_value_string"] for c in entries}
        regs = {c["region_id"] for c in entries}
        assert vals == {"58585.70", "58569.78"} and len(regs) == 2      # separate, not combined
    _run(f)


def test_06_digit_disagreement_null():
    def f(tmp):
        assert dual_reading("58585.70", "58585.10") == "READERS_DISAGREE"
        st = _review_status({"dual_reading_state": "READERS_DISAGREE", "field_type": "ENTRY_PRICE",
                             "alternative_readings": ["58585.70", "58585.10"]})
        assert st == "AMBIGUOUS_DIGITS"
        e = build(tmp)
        e["cdb"].insert_candidate(candidate_field_id="x:amb", media_id=e["mid"],
            region_id=e["mid"] + ":t1", field_type="ENTRY_PRICE", raw_visible_text="585??.70",
            candidate_value_string="58585.70", accepted_normalised_value=None,
            bbox=[0, 0, 1, 1], crop_sha256="c", extractor_confidence=0.6,
            alternative_readings=["58585.70", "58585.10"], extraction_method_version="v",
            review_status="AMBIGUOUS_DIGITS", evidence_domain="VISIBLE_TRADE_FACT",
            dual_reading_state="READERS_DISAGREE")
        row = e["cdb"].candidate("x:amb")
        assert row["review_status"] == "AMBIGUOUS_DIGITS" and row["accepted_normalised_value"] is None
    _run(f)


def test_07_missing_never_zero():
    def f(tmp):
        e = build(tmp)
        rows = cands_by(e["cdb"], e["mid"])
        assert all(c["accepted_normalised_value"] is None for c in rows)   # none coerced to 0
        assert not any(c["accepted_normalised_value"] == "0" or c["accepted_normalised_value"] == 0
                       for c in rows)
    _run(f)


def test_08_exit_linked_to_correct_ticket():
    def f(tmp):
        e = build(tmp)
        exits = cands_by(e["cdb"], e["mid"], field_type="EXIT_PRICE")
        by_region = {c["region_id"]: c for c in exits}
        assert e["mid"] + ":t1" in by_region and e["mid"] + ":t2" in by_region
        assert all(c["candidate_value_string"] == "59008.70" for c in exits)   # same value, separate rows
        assert len(exits) == 2
    _run(f)


def test_09_423_provider_pnl():
    def f(tmp):
        e = build(tmp)
        c = cands_by(e["cdb"], e["mid"], candidate_value_string="+423.00")[0]
        assert c["field_type"] == "PROVIDER_DISPLAYED_PNL" and c["evidence_domain"] == "PROVIDER_DISPLAYED"
    _run(f)


def test_10_438_provider_pnl():
    def f(tmp):
        e = build(tmp)
        c = cands_by(e["cdb"], e["mid"], candidate_value_string="+438.92")[0]
        assert c["field_type"] == "PROVIDER_DISPLAYED_PNL" and c["evidence_domain"] == "PROVIDER_DISPLAYED"
    _run(f)


def test_11_provider_pnl_rejected_from_r():
    ev = {"evidence_domain": "PROVIDER_DISPLAYED", "candidate_value_string": "+423.00",
          "eligible_for_account_r": 0}
    try:
        firewalls.calculate_account_r(ev); assert False
    except firewalls.ProviderProfitFirewallError:
        pass


def test_12_provider_pnl_rejected_from_expectancy():
    ev = {"evidence_domain": "PROVIDER_DISPLAYED", "eligible_for_expectancy": 0}
    try:
        firewalls.calculate_expectancy([ev]); assert False
    except firewalls.ProviderProfitFirewallError:
        pass


def test_13_commentary_classified_management():
    def f(tmp):
        e = build(tmp)
        row = e["cdb"].conn.execute("SELECT classification, is_clean_new_entry_signal, "
                                    "has_clean_entry_range FROM image_semantics WHERE media_id=?",
                                    (e["mid"],)).fetchone()
        assert row[0] == "POSITION_MANAGEMENT" and row[1] == 0 and row[2] == 0
    _run(f)


def test_14_no_new_campaign():
    def f(tmp):
        e = build(tmp)
        assert e["summary"]["new_campaign_events"] == 0 and e["summary"]["accepted_campaign_events"] == 0
        # neither vision DB has any campaign table
        for db in (e["cdb"].conn, e["rdb"].conn):
            tbls = [r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")]
            assert not any("campaign" in t.lower() for t in tbls)
    _run(f)


def test_15_no_open_leg():
    def f(tmp):
        e = build(tmp)
        assert e["summary"]["open_leg_events"] == 0
    _run(f)


def test_16_move_stop_candidate_only():
    def f(tmp):
        e = build(tmp)
        m = [c for c in cands_by(e["cdb"], e["mid"], field_type="MANAGEMENT_INSTRUCTION")
             if c["candidate_value_string"] == "MOVE_STOP_TO_ENTRY_INSTRUCTION"][0]
        assert m["review_status"] in ("PENDING", "AMBIGUOUS_DIGITS")
        assert e["rdb"].approved_for(m["candidate_field_id"]) == 0
    _run(f)


def test_17_no_gold_association():
    try:
        associate_gold("BTCUSD"); assert False
    except extraction.GoldAssociationBlocked:
        pass
    assert associate_gold("XAUUSD") is True     # only permitted for human-confirmed gold


def test_18_rejected_candidate_no_fact():
    def f(tmp):
        e = build(tmp)
        c = cands_by(e["cdb"], e["mid"], field_type="ENTRY_PRICE")[0]
        r = apply_review(candidate=c, decision="REJECT", reviewer_ref="martyn",
                         image_sha256=e["sha"], review_db=e["rdb"])
        assert r is None and e["rdb"].count("approved_media_facts") == 0
    _run(f)


def test_19_confirmation_creates_fact_only():
    def f(tmp):
        e = build(tmp)
        inst = cands_by(e["cdb"], e["mid"], field_type="INSTRUMENT")[0]
        afid = apply_review(candidate=inst, decision="CONFIRM", reviewer_ref="martyn",
                            image_sha256=e["sha"], confirmed_value="BTCUSD", review_db=e["rdb"])
        assert afid and e["rdb"].count("approved_media_facts") == 1
        tbls = [r[0] for r in e["rdb"].conn.execute("SELECT name FROM sqlite_master WHERE type='table'")]
        assert not any("campaign" in t.lower() for t in tbls)    # no campaign event created
    _run(f)


def test_20_vision_cannot_touch_campaign():
    assert firewalls.scan_campaign_write_access() == []          # static: no campaign refs
    violations = []
    orig = sqlite3.connect
    sqlite3.connect = firewalls.make_guarded_connect(orig, violations)
    try:
        def f(tmp):
            e = build(tmp)                                       # ingest + extract (opens media DBs)
            inst = cands_by(e["cdb"], e["mid"], field_type="INSTRUMENT")[0]
            apply_review(candidate=inst, decision="REJECT", reviewer_ref="m",
                         image_sha256=e["sha"], review_db=e["rdb"])
        _run(f)
    finally:
        sqlite3.connect = orig
    assert violations == []                                      # no campaign DB opened at runtime
    # and the guard actually fires if a campaign path is attempted
    try:
        firewalls.make_guarded_connect(orig, violations)("data/campaign_v1.db"); assert False
    except firewalls.CampaignAccessViolation:
        pass


def test_21_idempotent_reingest():
    def f(tmp):
        e = build(tmp, run=False)
        mid2, created2 = ingest.ingest_image(e["img"], e["cdb"],
                                             dest_root=os.path.join(tmp, "vision_fixtures_v1"))
        assert created2 is False and mid2 == e["mid"] and e["cdb"].count("ingested_images") == 1
    _run(f)


def test_22_no_arithmetic_reconstruction():
    for args in (dict(entry=None, exit_price="59008.70", displayed_profit="+423.00"),
                 dict(entry="58585.70", exit_price=None, displayed_profit="+423.00"),
                 dict(entry="58585.70", exit_price="59008.70", displayed_profit=None),
                 dict(entry="58585.70", exit_price="59008.70", displayed_profit="+423.00")):
        r = firewalls.reconcile_arithmetic(**args)
        assert r["computed_value"] is None                      # a value is NEVER manufactured
    # behavioural proof suffices: reconcile can only ever FLAG, never fill a missing value.


def test_23_confirmed_traces_to_provenance():
    def f(tmp):
        e = build(tmp)
        entry = cands_by(e["cdb"], e["mid"], field_type="ENTRY_PRICE")[0]
        apply_review(candidate=entry, decision="CORRECT", reviewer_ref="martyn",
                     image_sha256=e["sha"], confirmed_value="58585.70", image_supported=True,
                     review_db=e["rdb"])
        row = e["rdb"].conn.execute("SELECT source_original_sha256, source_region_id, source_crop_sha256 "
                                    "FROM approved_media_facts").fetchone()
        assert row[0] == e["sha"] and row[1] == entry["region_id"] and row[2] == entry["crop_sha256"]
    _run(f)


def test_24_schema_rejects_unknown_domain():
    def f(tmp):
        e = build(tmp, run=False)
        try:
            e["cdb"].insert_candidate(candidate_field_id="bad", media_id=e["mid"], region_id="r",
                field_type="ENTRY_PRICE", raw_visible_text="x", candidate_value_string="1",
                accepted_normalised_value=None, bbox=[0, 0, 1, 1], crop_sha256="c",
                extractor_confidence=0.9, alternative_readings=["1"], extraction_method_version="v",
                review_status="PENDING", evidence_domain="BOGUS_DOMAIN", dual_reading_state=None)
            assert False
        except sqlite3.IntegrityError:
            pass
    _run(f)


def test_25_confidence_never_promotes():
    def f(tmp):
        e = build(tmp)
        # every high-confidence extracted candidate is still unaccepted + unreviewed
        rows = cands_by(e["cdb"], e["mid"])
        assert all(c["accepted_normalised_value"] is None for c in rows)
        assert all(c["review_status"] in ("PENDING", "AMBIGUOUS_DIGITS") for c in rows)
        assert e["rdb"].count("approved_media_facts") == 0     # nothing promoted without review
    _run(f)
