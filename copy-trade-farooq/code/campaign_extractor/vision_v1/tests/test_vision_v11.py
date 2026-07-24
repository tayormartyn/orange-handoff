"""Vision V1.1 offline tests (35). Reads the real populated store for crop/spatial/provenance;
uses temp DBs + synthetic for schema/firewall/idempotency/logic. No expected values reach the reader."""
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
for p in (_ROOT, _CE, _VIS):
    if p not in sys.path:
        sys.path.insert(0, p)

import ingest
import firewalls
import decimals
import extraction
from stores import CandidateDB, ReviewDB
from review_gate import apply_review

MID = "media-08951b5616218879"
SHA = "08951b561621887959c461ce887dc72cc28b09dad4f9263c403e3feae00e8e57"
W, H = 551, 740
REAL_DB = os.path.join(_ROOT, "data", "media_candidates_v1.db")


def real():
    return sqlite3.connect(f"file:{REAL_DB}?mode=ro", uri=True)


def active(parent, ftype):
    """Return (second_raw, bbox_json, crop_sha, state, accepted, primary_raw) for the active crop."""
    c = real()
    row = c.execute("""SELECT sr.raw_returned_string, cr.bbox, cr.crop_sha256, cmp.comparison_state,
        cmp.accepted_value, cmp.primary_raw FROM field_candidates fc
        JOIN crops cr ON cr.crop_sha256=fc.crop_sha256
        LEFT JOIN second_readings sr ON sr.crop_sha256=fc.crop_sha256
        LEFT JOIN reader_comparisons cmp ON cmp.candidate_field_id=fc.candidate_field_id
        WHERE fc.media_id=? AND fc.region_id=? AND fc.field_type=?""",
        (MID, f"{MID}:{parent}", ftype)).fetchone()
    c.close()
    return row


def _tmp():
    return tempfile.mkdtemp(prefix="v11_")


# ---- crops & provenance (real store) ----
def test_01_crop_files_exist():
    c = real()
    paths = [r[0] for r in c.execute("SELECT crop_path FROM crops WHERE media_id=?", (MID,))]
    c.close()
    base = os.path.join(_ROOT, "data", "vision_fixtures_v1", MID)
    assert paths and all(os.path.exists(os.path.join(base, p)) for p in paths)


def test_02_crops_trace_to_original_hash():
    c = real()
    shas = {r[0] for r in c.execute("SELECT original_sha256 FROM crops WHERE media_id=?", (MID,))}
    c.close()
    assert shas == {SHA}


def test_03_candidates_reference_real_crop_hashes():
    c = real()
    rows = c.execute("SELECT fc.crop_sha256 FROM field_candidates fc WHERE fc.media_id=? AND "
                     "fc.field_type IN ('ENTRY_PRICE','EXIT_PRICE','PROVIDER_DISPLAYED_PNL')", (MID,)).fetchall()
    crops = {r[0] for r in c.execute("SELECT crop_sha256 FROM crops")}
    c.close()
    assert rows and all(len(r[0]) == 64 and r[0] in crops for r in rows)


def test_04_bboxes_within_dimensions():
    import json
    c = real()
    for (b,) in c.execute("SELECT bbox FROM crops WHERE media_id=?", (MID,)):
        x0, y0, x1, y1 = json.loads(b)
        assert 0 <= x0 < x1 <= W and 0 <= y0 < y1 <= H
    c.close()


def test_05_ticket_crops_do_not_swap_or_overlap():
    import json
    b1 = json.loads(active("t1", "ENTRY_PRICE")[1]); b2 = json.loads(active("t2", "ENTRY_PRICE")[1])
    assert b1[3] <= b2[1]                              # ticket1 entry is strictly above ticket2 entry


def test_06_ticket1_entry_spatial():
    raw = active("t1", "ENTRY_PRICE")[0]
    assert "58585" in raw and "58569" not in raw      # correct row, not the other ticket


def test_07_ticket2_entry_spatial():
    raw = active("t2", "ENTRY_PRICE")[0]
    assert "58569" in raw and "58585" not in raw


# ---- independence / blindness (static) ----
def test_08_second_reader_no_primary_or_expected():
    src = open(os.path.join(_VIS, "run_v11_generate.py"), encoding="utf-8").read()
    # the blind reader takes only (ocr, image); no expected/primary passed into the OCR call
    assert "_blind_full_image_read(ocr, ORIG)" in src
    assert "def _blind_full_image_read(ocr, orig):" in src
    fn = src.split("def _blind_full_image_read(")[1].split("def main(")[0]
    # signature takes only (ocr, orig); no expected VALUES appear in the reader body
    assert fn.lstrip().startswith("ocr, orig)")
    for leak in ("58585", "58569", "423.00", "438.92"):
        assert leak not in fn                          # no expected answer literal in the reader


def test_09_no_self_answer_leakage():
    row = active("t1", "ENTRY_PRICE")
    c = real()
    eng = c.execute("SELECT reader_engine FROM second_readings WHERE crop_sha256=?", (row[2],)).fetchone()[0]
    c.close()
    assert "rapidocr" in eng.lower()                   # distinct engine, not the primary visual model


def test_10_both_readings_retained():
    r = active("t1", "ENTRY_PRICE")
    assert r[5] and r[0]                               # primary_raw and second_raw both present


def test_11_disagreement_accepted_null():
    r = active("comm", "COMMENTARY_TEXT")
    assert r[3] == "READERS_DISAGREE" and r[4] is None


def test_12_one_reader_only_accepted_null():
    tmp = _tmp()
    try:
        cdb = CandidateDB(os.path.join(tmp, "media_candidates_v1.db"))
        cdb.insert_comparison(comparison_id="x", candidate_field_id="cf", crop_sha256="c",
            primary_raw="58585.70", primary_confidence=0.99, second_raw=None, second_confidence=None,
            comparison_state="ONE_READER_ONLY", disagreement_reason=None, alternative_readings=[],
            accepted_value=None)
        r = cdb.conn.execute("SELECT accepted_value FROM reader_comparisons").fetchone()
        assert r[0] is None
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_13_readers_agree_still_needs_review():
    r = active("t1", "ENTRY_PRICE")
    assert r[3] == "READERS_AGREE" and r[4] is None    # agreement does NOT approve
    c = real()
    acc = c.execute("SELECT accepted_normalised_value FROM field_candidates WHERE media_id=? AND "
                    "region_id=? AND field_type='ENTRY_PRICE'", (MID, f"{MID}:t1")).fetchone()[0]
    c.close()
    assert acc is None


def test_14_ambiguous_decimal_null():
    for s in ("58585,70", "58.585,70"):
        val, status, alts = decimals.parse_numeric(s)
        assert status == "AMBIGUOUS_DIGITS" and val is None and len(alts) >= 1


def test_15_raw_strings_preserved():
    c = real()
    rows = c.execute("SELECT raw_visible_text, candidate_value_string FROM field_candidates WHERE "
                     "media_id=? AND field_type='DIRECTION'", (MID,)).fetchall()
    c.close()
    assert any(rt == "buy 1" for rt, _ in rows)        # raw kept separate from normalised 'BUY'


def test_16_similar_entries_distinct():
    assert active("t1", "ENTRY_PRICE")[0] != active("t2", "ENTRY_PRICE")[0]
    assert active("t1", "ENTRY_PRICE")[2] != active("t2", "ENTRY_PRICE")[2]   # different crops


def test_17_missing_never_zero():
    val, status, _ = decimals.parse_numeric("")
    assert val is None and status == "AMBIGUOUS_DIGITS"     # never 0


def test_18_exit_pnl_linked_to_correct_ticket():
    assert "423" in active("t1", "PROVIDER_DISPLAYED_PNL")[0]
    assert "438" in active("t2", "PROVIDER_DISPLAYED_PNL")[0]
    assert "59008" in active("t1", "EXIT_PRICE")[0] and "59008" in active("t2", "EXIT_PRICE")[0]


def test_19_btc_never_gold():
    assert extraction.classify_instrument("BTCUSD") == "BTCUSD"
    try:
        extraction.associate_gold("BTCUSD"); assert False
    except extraction.GoldAssociationBlocked:
        pass


def test_20_commentary_not_entry_signal():
    c = real()
    row = c.execute("SELECT classification, is_clean_new_entry_signal FROM image_semantics WHERE media_id=?",
                    (MID,)).fetchone()
    c.close()
    assert row[0] == "POSITION_MANAGEMENT" and row[1] == 0


def test_21_provider_pnl_domain():
    c = real()
    for v in ("423.00", "438.92"):
        d = c.execute("SELECT evidence_domain, field_type FROM field_candidates WHERE media_id=? AND "
                      "candidate_value_string=?", (MID, v)).fetchone()
        assert d == ("PROVIDER_DISPLAYED", "PROVIDER_DISPLAYED_PNL")
    c.close()


def test_22_provider_pnl_rejected_from_r():
    try:
        firewalls.calculate_account_r({"evidence_domain": "PROVIDER_DISPLAYED", "eligible_for_account_r": 0})
        assert False
    except firewalls.ProviderProfitFirewallError:
        pass


def test_23_provider_pnl_rejected_from_expectancy():
    try:
        firewalls.calculate_expectancy([{"evidence_domain": "PROVIDER_DISPLAYED", "eligible_for_expectancy": 0}])
        assert False
    except firewalls.ProviderProfitFirewallError:
        pass


def test_24_no_arithmetic_reconstruction():
    for a in (dict(entry=None, exit_price="59008.70", displayed_profit="423.00"),
              dict(entry="58585.70", exit_price="59008.70", displayed_profit="423.00")):
        assert firewalls.reconcile_arithmetic(**a)["computed_value"] is None


def test_25_buy1_lot_meaning_ambiguous():
    c = real()
    rows = c.execute("SELECT candidate_value_string, raw_visible_text, accepted_normalised_value, "
                     "review_status FROM field_candidates WHERE media_id=? AND field_type='LOT_SIZE'",
                     (MID,)).fetchall()
    c.close()
    assert rows and all(v == "1" and rt == "buy 1" and acc is None for v, rt, acc, _ in rows)  # not auto 1-lot


def test_26_27_28_no_campaign_events():
    c = real()
    tbls = [r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")]
    c.close()
    assert not any("campaign" in t.lower() for t in tbls)   # no campaign/open-leg/accepted tables


def test_29_human_confirm_creates_fact_only():
    tmp = _tmp()
    try:
        rdb = ReviewDB(os.path.join(tmp, "media_reviews_v1.db"))
        cand = {"candidate_field_id": "cf1", "media_id": MID, "region_id": f"{MID}:t1",
                "field_type": "ENTRY_PRICE", "evidence_domain": "VISIBLE_TRADE_FACT", "crop_sha256": "abc"}
        afid = apply_review(candidate=cand, decision="CONFIRM", reviewer_ref="martyn",
                            image_sha256=SHA, confirmed_value="58585.70", review_db=rdb)
        assert afid and rdb.count("approved_media_facts") == 1
        tbls = [r[0] for r in rdb.conn.execute("SELECT name FROM sqlite_master WHERE type='table'")]
        assert not any("campaign" in t.lower() for t in tbls)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_30_vision_cannot_touch_campaign():
    assert firewalls.scan_campaign_write_access() == []
    viol = []
    orig = sqlite3.connect
    sqlite3.connect = firewalls.make_guarded_connect(orig, viol)
    try:
        tmp = _tmp()
        try:
            ReviewDB(os.path.join(tmp, "media_reviews_v1.db")).close()
            CandidateDB(os.path.join(tmp, "media_candidates_v1.db")).close()
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    finally:
        sqlite3.connect = orig
    assert viol == []
    try:
        firewalls.make_guarded_connect(orig, viol)("data/mpk_campaigns_v1.db"); assert False
    except firewalls.CampaignAccessViolation:
        pass


def test_31_idempotent():
    tmp = _tmp()
    try:
        cdb = CandidateDB(os.path.join(tmp, "media_candidates_v1.db"))
        img = os.path.join(tmp, "a.png")
        open(img, "wb").write(ingest.make_png(40, 30))
        m1, c1 = ingest.ingest_image(img, cdb, dest_root=os.path.join(tmp, "vf"))
        m2, c2 = ingest.ingest_image(img, cdb, dest_root=os.path.join(tmp, "vf"))
        assert c1 is True and c2 is False and m1 == m2 and cdb.count("ingested_images") == 1
        cdb.insert_crop(crop_id="k", media_id=m1, original_sha256="s", region_type="TICKET_1",
                        parent_region_id=None, field_type="ENTRY_PRICE", bbox=[0, 0, 5, 5],
                        crop_path="p", crop_sha256="cs1", crop_width=5, crop_height=5,
                        crop_created_at="t", crop_tool_version="v")
        cdb.insert_crop(crop_id="k", media_id=m1, original_sha256="s", region_type="TICKET_1",
                        parent_region_id=None, field_type="ENTRY_PRICE", bbox=[0, 0, 5, 5],
                        crop_path="p", crop_sha256="cs1", crop_width=5, crop_height=5,
                        crop_created_at="t", crop_tool_version="v")
        assert cdb.conn.execute("SELECT COUNT(*) FROM crops").fetchone()[0] == 1   # OR IGNORE
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_32_approved_traces_to_hash_crop_coords():
    tmp = _tmp()
    try:
        rdb = ReviewDB(os.path.join(tmp, "media_reviews_v1.db"))
        cand = {"candidate_field_id": "cf", "media_id": MID, "region_id": f"{MID}:t1",
                "field_type": "ENTRY_PRICE", "evidence_domain": "VISIBLE_TRADE_FACT",
                "crop_sha256": active("t1", "ENTRY_PRICE")[2]}
        apply_review(candidate=cand, decision="CORRECT", reviewer_ref="m", image_sha256=SHA,
                     confirmed_value="58585.70", image_supported=True, review_db=rdb)
        row = rdb.conn.execute("SELECT source_original_sha256, source_crop_sha256, source_region_id "
                               "FROM approved_media_facts").fetchone()
        assert row[0] == SHA and row[1] == cand["crop_sha256"] and row[2] == f"{MID}:t1"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_33_schema_rejects_unknown_domain():
    tmp = _tmp()
    try:
        cdb = CandidateDB(os.path.join(tmp, "m.db"))
        try:
            cdb.insert_candidate(candidate_field_id="b", media_id="m", region_id="r",
                field_type="ENTRY_PRICE", raw_visible_text="x", candidate_value_string="1",
                accepted_normalised_value=None, bbox=[0, 0, 1, 1], crop_sha256="c",
                extractor_confidence=0.9, alternative_readings=["1"], extraction_method_version="v",
                review_status="PENDING", evidence_domain="NONSENSE", dual_reading_state=None)
            assert False
        except sqlite3.IntegrityError:
            pass
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_34_confidence_never_promotes():
    c = real()
    # every field candidate (incl. high-confidence READERS_AGREE numerics) remains unaccepted
    accs = [r[0] for r in c.execute("SELECT accepted_normalised_value FROM field_candidates WHERE media_id=?", (MID,))]
    facts = c.execute("SELECT COUNT(*) FROM reader_comparisons WHERE accepted_value IS NOT NULL").fetchone()[0]
    c.close()
    assert all(a is None for a in accs) and facts == 0


def test_35_protected_truth_untouched():
    import hashlib
    def sha16(p):
        return hashlib.sha256(open(p, "rb").read()).hexdigest()[:16]
    mpk = os.path.join(_ROOT, "campaign_extractor", "mpk", "data")
    assert sha16(os.path.join(mpk, "mpk_campaigns_v1.db")) == "6895a1cb71fd93ba"
    assert sha16(os.path.join(mpk, "mpk_registry_v1.db")) == "c03e928f21ec94ae"
    cfg = open(os.path.join(_ROOT, "config.py"), encoding="utf-8").read()
    assert 'MODE = "PAPER"' in cfg and "EXECUTION_ENABLED = False" in cfg
