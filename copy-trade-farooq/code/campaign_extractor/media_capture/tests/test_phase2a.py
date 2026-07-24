"""Brick 5C Phase 2A offline tests (A–Q). Mocks + temp DBs/dirs only. No live Telegram."""
from __future__ import annotations
import hashlib
import os
import shutil
import sqlite3
import sys
import tempfile
import tokenize

_HERE = os.path.dirname(os.path.abspath(__file__))
_MC = os.path.dirname(_HERE)
_CE = os.path.dirname(_MC)
_ROOT = os.path.dirname(_CE)
for p in (_MC, _CE):
    if p not in sys.path:
        sys.path.insert(0, p)

import config as CFG
import store as STORE
import pipeline as PIPE
import catchup as CATCH
from media_db import MediaDB
from banner import truthful_banner
from prospective.prospective_db import ProspectiveDB

PNG = b"\x89PNG\r\n\x1a\n" + bytes(48)
JPEG = b"\xff\xd8\xff\xe0" + bytes(48)
MC_SOURCES = ("__init__.py", "config.py", "_util.py", "media_db.py", "store.py", "pipeline.py",
              "catchup.py", "banner.py", "live_adapter.py", "run_phase2a.py")
CH = "-1001902136163"


def _photo(ref="ph_large"):
    return {"media_type": "photo", "sizes": [{"bytes": 100, "ref": "ph_small"},
                                             {"bytes": 9000, "ref": ref}], "telegram_media_id": "ph"}


def _msg(mid, *, text=None, media=None, media_ref=None, revision=1, grouped=None, media_index=0):
    return {"channel_id": CH, "message_id": mid, "raw_text": text, "media_reference": media_ref,
            "media_descriptor": media, "posted_at": "2026-06-30T14:00:00Z",
            "received_at": "2026-06-30T14:00:01Z", "revision": revision,
            "grouped_media_id": grouped, "media_index": media_index}


def _dl(data, chunk=8):
    def f(descriptor, ref):
        for i in range(0, len(data), chunk):
            yield data[i:i + chunk]
    return f


def _dl_raises_if_called(descriptor, ref):
    raise AssertionError("downloader must not be called")
    yield b""  # pragma: no cover


def _env():
    tmp = tempfile.mkdtemp(prefix="mc2a_")
    text_db = ProspectiveDB(os.path.join(tmp, "text.db"))
    media_db = MediaDB(os.path.join(tmp, "prospective_media_v1.db"))
    media_dir = os.path.join(tmp, "prospective_media_v1")
    return tmp, text_db, media_db, media_dir


def _images(media_dir):
    if not os.path.isdir(media_dir):
        return []
    return [f for f in os.listdir(media_dir) if not f.endswith((".db", ".part")) and
            ".incoming_" not in f]


def _preserve(media_db, media_dir, msg, downloader, max_bytes=None):
    ident = PIPE._identity(msg, msg.get("media_index", 0))
    return STORE.preserve(msg["media_descriptor"], ident, downloader, media_db,
                          media_dir=media_dir, max_bytes=max_bytes)


# ===================================================== A — flag defaults False
def test_A_flag_default_false():
    assert CFG.TELEGRAM_MEDIA_CAPTURE_ENABLED is True   # Phase 2B activated (was False pre-2B)
    tmp, tdb, mdb, mdir = _env()
    try:
        res = PIPE.process(_msg("1", text="hi", media=_photo(), media_ref="ph"),
                           text_db=tdb, media_db=mdb, downloader=_dl_raises_if_called,
                           flag_enabled=False)
        assert res["media_status"] == "DISABLED" and res["text_committed"]
        assert mdb.count() == 0
        assert tdb.count("prospective_message_evidence") == 1
        tdb.close(); mdb.close()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ===================================================== B — text-first commit, media fails
def test_B_text_first_media_fail():
    tmp, tdb, mdb, mdir = _env()
    try:
        def boom(d, r):
            raise IOError("drop")
            yield b""
        res = PIPE.process(_msg("2", text="signal", media=_photo(), media_ref="ph"),
                           text_db=tdb, media_db=mdb, downloader=boom, flag_enabled=True,
                           media_dir=mdir)
        assert res["text_committed"] and res["media_status"] == "MEDIA_DOWNLOAD_FAILED"
        assert tdb.count("prospective_message_evidence") == 1     # text intact
        tdb.close(); mdb.close()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ===================================================== C — image-only (chars=0)
def test_C_image_only():
    tmp, tdb, mdb, mdir = _env()
    try:
        res = PIPE.process(_msg("3", text=None, media=_photo(), media_ref="ph"),
                           text_db=tdb, media_db=mdb, downloader=_dl(PNG), flag_enabled=True,
                           media_dir=mdir)
        assert res["media_status"] == "MEDIA_CAPTURED"
        # text row preserved with raw_text NULL (chars=0)
        rt = tdb.con.execute("SELECT raw_text, raw_text_hash FROM prospective_message_evidence "
                             "WHERE telegram_message_id='3'").fetchone()
        assert rt[0] is None and rt[1] is None                     # media-only -> NULL text + NULL hash
        row = mdb.rows()[0]
        assert row[2] == hashlib.sha256(PNG).hexdigest()           # content sha recorded
        assert row[0] == "3" and len(_images(mdir)) == 1           # linkage + file
        tdb.close(); mdb.close()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ===================================================== D — text plus image
def test_D_text_plus_image():
    tmp, tdb, mdb, mdir = _env()
    try:
        text = "XAUUSD update"
        tdb.append_message_evidence(telegram_channel_id=CH, telegram_message_id="4",
                                    telegram_posted_at_utc="t", listener_received_at_utc="t",
                                    raw_text=text)
        stored = tdb.con.execute("SELECT raw_text_hash FROM prospective_message_evidence "
                                 "WHERE telegram_message_id='4'").fetchone()[0]
        assert stored == hashlib.sha256(text.encode()).hexdigest()   # text hash unchanged
        st = _preserve(mdb, mdir, _msg("4", media=_photo(), media_ref="ph"), _dl(JPEG))
        assert st == "MEDIA_CAPTURED" and mdb.count() == 1            # independent media record
        tdb.close(); mdb.close()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ===================================================== E — original-byte integrity + largest size
def test_E_original_bytes():
    tmp, tdb, mdb, mdir = _env()
    try:
        kind, mime, ext, ref = STORE.classify(_photo(ref="ph_largest"))
        assert ref == "ph_largest"                                   # largest size selected
        _preserve(mdb, mdir, _msg("5", media=_photo(), media_ref="ph"), _dl(PNG))
        f = _images(mdir)[0]
        on_disk = open(os.path.join(mdir, f), "rb").read()
        assert on_disk == PNG                                        # byte-for-byte, no transform
        assert mdb.rows()[0][2] == hashlib.sha256(PNG).hexdigest()
        tdb.close(); mdb.close()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ===================================================== F — streaming size cap
def test_F_streaming_cap():
    tmp, tdb, mdb, mdir = _env()
    try:
        big = PNG + bytes(500)
        st = _preserve(mdb, mdir, _msg("6", media=_photo(), media_ref="ph"), _dl(big, chunk=16),
                       max_bytes=32)
        assert st == "MEDIA_TOO_LARGE"
        assert _images(mdir) == []                                   # no final file
        assert not any(".part" in f or ".incoming_" in f for f in os.listdir(mdir))
        assert mdb.by_status("MEDIA_TOO_LARGE") == 1
        tdb.close(); mdb.close()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ===================================================== G — atomic interruption
def test_G_atomic_interruption():
    tmp, tdb, mdb, mdir = _env()
    try:
        def mid_fail(d, r):
            yield PNG[:8]
            raise IOError("network drop mid-stream")
        st = _preserve(mdb, mdir, _msg("7", media=_photo(), media_ref="ph"), mid_fail)
        assert st == "MEDIA_DOWNLOAD_FAILED"
        assert _images(mdir) == []                                   # no partial final file
        assert not any(".incoming_" in f for f in os.listdir(mdir))  # temp removed
        tdb.close(); mdb.close()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ===================================================== H — duplicate delivery
def test_H_duplicate_delivery():
    tmp, tdb, mdb, mdir = _env()
    try:
        m = _msg("8", media=_photo(), media_ref="ph")
        assert _preserve(mdb, mdir, m, _dl(PNG)) == "MEDIA_CAPTURED"
        assert _preserve(mdb, mdir, m, _dl(PNG)) == "DUPLICATE_MEDIA_REFERENCE"
        assert mdb.count() == 1                                      # one logical row
        tdb.close(); mdb.close()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ===================================================== I — identical bytes, separate messages
def test_I_identical_bytes_two_messages():
    tmp, tdb, mdb, mdir = _env()
    try:
        _preserve(mdb, mdir, _msg("9", media=_photo(), media_ref="phA"), _dl(PNG))
        _preserve(mdb, mdir, _msg("10", media=_photo(), media_ref="phB"), _dl(PNG))
        assert mdb.count() == 2                                      # two separate links
        shas = {r[2] for r in mdb.rows()}
        assert shas == {hashlib.sha256(PNG).hexdigest()}            # same content hash
        assert len(_images(mdir)) == 1                              # one physical file (write-once)
        tdb.close(); mdb.close()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ===================================================== J — grouped album
def test_J_grouped_album():
    tmp, tdb, mdb, mdir = _env()
    try:
        a = _msg("11", media=_photo("a"), media_ref="ga0", grouped="grp1", media_index=0)
        b = _msg("11", media=_photo("b"), media_ref="ga1", grouped="grp1", media_index=1)
        assert _preserve(mdb, mdir, a, _dl(PNG)) == "MEDIA_CAPTURED"
        assert _preserve(mdb, mdir, b, _dl(JPEG)) == "MEDIA_CAPTURED"
        assert _preserve(mdb, mdir, a, _dl(PNG)) == "DUPLICATE_MEDIA_REFERENCE"
        idxs = sorted(r[1] for r in mdb.rows())
        assert idxs == [0, 1] and mdb.count() == 2                  # deterministic, no dup
        tdb.close(); mdb.close()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ===================================================== K — unsupported video
def test_K_unsupported_video():
    tmp, tdb, mdb, mdir = _env()
    try:
        vid = {"media_type": "video", "telegram_media_id": "vid1"}
        m = _msg("12", text="caption", media=vid, media_ref="vid1")
        st = _preserve(mdb, mdir, m, _dl_raises_if_called)          # must NOT download
        assert st == "UNSUPPORTED_MEDIA_TYPE"
        assert _images(mdir) == [] and mdb.by_status("UNSUPPORTED_MEDIA_TYPE") == 1
        tdb.close(); mdb.close()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ===================================================== L — metadata-write failure -> orphan
def test_L_metadata_failure_orphan():
    tmp, tdb, mdb, mdir = _env()
    try:
        class FailMD:
            def exists(self, **k):
                return False
            def append(self, rec):
                raise sqlite3.OperationalError("simulated metadata failure")
        st = _preserve(FailMD(), mdir, _msg("13", media=_photo(), media_ref="ph"), _dl(PNG))
        assert st == "ORPHAN_FILE_NEEDS_RECONCILIATION"
        assert len(_images(mdir)) == 1                              # file durable, not claimed CAPTURED
        tdb.close(); mdb.close()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ===================================================== M — file/hash mismatch reconcile
def test_M_file_hash_mismatch():
    tmp, tdb, mdb, mdir = _env()
    try:
        _preserve(mdb, mdir, _msg("14", media=_photo(), media_ref="ph"), _dl(PNG))
        row = mdb.rows()[0]
        assert STORE.reconcile(row, media_dir=mdir) == "OK"
        # corrupt the file -> mismatch detected, no overwrite/redownload
        with open(os.path.join(mdir, row[4]), "wb") as f:
            f.write(b"corrupted")
        assert STORE.reconcile(row, media_dir=mdir) == "FILE_MISSING_OR_HASH_MISMATCH"
        tdb.close(); mdb.close()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ===================================================== N — bounded catch-up
def test_N_bounded_catchup():
    tmp, tdb, mdb, mdir = _env()
    try:
        tdb.append_message_evidence(telegram_channel_id=CH, telegram_message_id="101",
                                    telegram_posted_at_utc="t", listener_received_at_utc="t",
                                    raw_text="already captured")     # overlap row
        msgs = [_msg("99", text="below"), _msg("101", text="dup"), _msg("102", text="new"),
                _msg("150", text="above")]
        rep = CATCH.run_catchup(CH, 100, 120, iter(msgs), text_db=tdb, media_db=mdb,
                                downloader=_dl(PNG), allowlist={CH}, flag_enabled=False)
        assert rep["out_of_bounds_skipped"] == 2                    # 99 and 150
        assert rep["text_duplicate_skipped"] == 1                   # 101 overlap
        assert rep["text_new"] == 1                                 # 102
        tdb.close(); mdb.close()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ===================================================== O — no OCR / interpretation
def _code_names(name):
    names = set()
    with open(os.path.join(_MC, name), "rb") as f:
        for tok in tokenize.tokenize(f.readline):
            if tok.type == tokenize.NAME:
                names.add(tok.string)
    return names


def test_O_no_ocr_or_interpretation():
    # token-level: ignore docstrings/strings (which legitimately SAY "no OCR/vision")
    forbidden = {"pytesseract", "cv2", "PIL", "Pillow", "tensorflow", "torch", "easyocr", "Image"}
    for name in MC_SOURCES:
        bad = forbidden & _code_names(name)
        assert not bad, f"{name} imports/uses {bad}"
    cols = [c[1] for c in MediaDB(":memory:").con.execute("PRAGMA table_info(media_records)")]
    for bad in ("entry", "stop", "sl", "tp", "volume", "lot", "pnl", "realised_r", "realized_r"):
        assert not any(bad == c.lower() for c in cols)


# ===================================================== P — Phase 2B wiring is gated + text-first
def test_P_phase2b_wiring_gated_and_textfirst():
    src = open(os.path.join(_ROOT, "module_a_telegram.py"), encoding="utf-8").read()
    assert "media_capture" in src and "_preserve_media" in src        # wired (Phase 2B)
    # media runs AFTER the text-evidence commit (text-first)
    assert src.index("_record_prospective(recorder, event") < src.index("_preserve_media(event")
    assert "if media_ctx is not None" in src                          # gated on the flag-built ctx
    # the media_capture engine sources carry NO network/credential/broker references
    forbidden = {"telethon", "TelegramClient", "download_media", "iter_messages", "socket",
                 "ssl", "urllib", "requests", "websocket", "hyperliquid", "ctrader"}
    for name in MC_SOURCES:
        bad = forbidden & _code_names(name)
        assert not bad, f"{name} has forbidden executable reference {bad}"
    assert any("disabled" in ln.lower() for ln in truthful_banner(False))
    assert any("preserved" in ln.lower() for ln in truthful_banner(True))


# ===================================================== Q — protected truth
def test_Q_protected_unchanged():
    prot = [
        os.path.join(_ROOT, "campaign_extractor", "prospective", "data", "prospective_evidence_v1.db"),
        os.path.join(_ROOT, "campaign_extractor", "mpk", "data", "mpk_registry_v1.db"),
        os.path.join(_ROOT, "campaign_extractor", "mpk", "data", "mpk_campaigns_v1.db"),
        os.path.join(_ROOT, "campaign_extractor", "inst", "data", "instrument_registry_v1.db"),
    ]
    def sha(p):
        return hashlib.sha256(open(p, "rb").read()).hexdigest() if os.path.exists(p) else None
    before = {p: sha(p) for p in prot}
    tmp, tdb, mdb, mdir = _env()
    try:
        _preserve(mdb, mdir, _msg("200", media=_photo(), media_ref="ph"), _dl(PNG))
        tdb.close(); mdb.close()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    assert {p: sha(p) for p in prot} == before
