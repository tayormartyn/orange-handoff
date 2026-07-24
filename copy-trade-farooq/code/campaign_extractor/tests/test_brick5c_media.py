"""
Brick 5C — immutable image preservation, offline. Synthetic image bytes only (no network).

Proves: image-only filter; size limit; content-addressed immutable storage; SHA-256 over
exact bytes; deterministic link to channel/message/revision/evidence; album/multi-image;
append-only index (update/delete rejected); path-traversal-proof names; media failure returns
a named status without raising (raw text never lost); manual-screenshot provenance; secret
rejection; dedupe.
"""
import hashlib
import os
import re
import sqlite3
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from prospective.media_cache import MediaCache
from broker_readonly.secrets import SecretLeak

PNG = b"\x89PNG\r\n\x1a\n" + b"fake-png-pixels"
JPEG = b"\xff\xd8\xff" + b"fake-jpeg-bytes"
NOTIMG = b"this is plainly not an image at all"


def _cache(max_bytes=10 * 1024 * 1024):
    d = tempfile.mkdtemp(prefix="mediacache_")
    return MediaCache(d, max_bytes=max_bytes)


def test_valid_image_cached_content_addressed():
    c = _cache()
    st = c.preserve(PNG, telegram_channel_id=-1001902136163, telegram_message_id="1",
                    evidence_id="ev1")
    assert st == "MEDIA_CACHED"
    files = c.cached_files()
    assert len(files) == 1
    sha = hashlib.sha256(PNG).hexdigest()
    assert files[0] == f"{sha}.png"                      # name IS the content hash
    assert c.count() == 1


def test_sha256_over_exact_bytes():
    c = _cache()
    c.preserve(JPEG, telegram_channel_id=-1, telegram_message_id="2")
    row = c.rows()[0]
    assert row[0] == hashlib.sha256(JPEG).hexdigest() and row[2] == "jpeg"


def test_non_image_rejected_no_file():
    c = _cache()
    st = c.preserve(NOTIMG, telegram_channel_id=-1, telegram_message_id="3")
    assert st == "MEDIA_REJECTED_NOT_IMAGE"
    assert c.cached_files() == [] and c.count() == 1      # status row appended, no file written


def test_too_large_rejected():
    c = _cache(max_bytes=8)
    st = c.preserve(JPEG, telegram_channel_id=-1, telegram_message_id="4")
    assert st == "MEDIA_REJECTED_TOO_LARGE" and c.cached_files() == []


def test_album_multiple_images_supported():
    c = _cache()
    c.preserve(PNG, telegram_channel_id=-1, telegram_message_id="5", album_index=0)
    c.preserve(JPEG, telegram_channel_id=-1, telegram_message_id="5", album_index=1)
    assert c.count() == 2 and len(c.cached_files()) == 2
    albums = sorted(r[4] for r in c.rows())
    assert albums == [0, 1]


def test_dedupe_write_once():
    c = _cache()
    c.preserve(PNG, telegram_channel_id=-1, telegram_message_id="6")
    c.preserve(PNG, telegram_channel_id=-1, telegram_message_id="6")   # same bytes again
    assert c.count() == 2 and len(c.cached_files()) == 1              # two rows, one file


def test_append_only_update_and_delete_rejected():
    c = _cache()
    c.preserve(PNG, telegram_channel_id=-1, telegram_message_id="7")
    for sql in ("UPDATE media_index SET media_status='x'", "DELETE FROM media_index"):
        try:
            c.con.execute(sql); c.con.commit(); assert False
        except sqlite3.Error as e:
            assert "append-only" in str(e).lower()


def test_cached_name_is_traversal_proof():
    c = _cache()
    c.preserve(PNG, telegram_channel_id=-1, telegram_message_id="8")
    name = c.cached_files()[0]
    assert re.fullmatch(r"[0-9a-f]{64}\.(png|jpeg|gif|bmp|webp)", name)   # hex hash only
    assert ".." not in name and "/" not in name and "\\" not in name


def test_media_failure_returns_status_without_raising():
    c = _cache()
    # a non-image (parse-fail analogue) returns a status; it must NOT raise -> raw text (stored
    # elsewhere, first) is never rolled back by a media problem.
    st = c.preserve(b"", telegram_channel_id=-1, telegram_message_id="9")
    assert st == "MEDIA_EMPTY"


def test_link_fields_stored():
    c = _cache()
    c.preserve(PNG, telegram_channel_id=-1001902136163, telegram_message_id="45285",
               message_revision_number=1, evidence_id="d60777eb1257dad9")
    r = c.con.execute("SELECT telegram_channel_id, telegram_message_id, message_revision_number, "
                      "evidence_id FROM media_index").fetchone()
    assert r == ("-1001902136163", "45285", 1, "d60777eb1257dad9")


def test_manual_screenshot_provenance_retained():
    c = _cache()
    c.preserve(PNG, telegram_channel_id=-1, telegram_message_id="btc1",
               source_provenance="MANUAL_TELEGRAM_SCREENSHOT_FIXTURE")
    assert c.rows()[0][5] == "MANUAL_TELEGRAM_SCREENSHOT_FIXTURE"


def test_secret_named_field_rejected_in_index():
    c = _cache()
    try:
        c._append({"media_id": "x", "media_status": "MEDIA_CACHED", "index_hash": "h",
                   "access_token": "S"})
        assert False
    except SecretLeak:
        pass


def test_deterministic_same_bytes_same_hash():
    a, b = _cache(), _cache()
    a.preserve(PNG, telegram_channel_id=-1, telegram_message_id="10")
    b.preserve(PNG, telegram_channel_id=-1, telegram_message_id="10")
    assert a.rows()[0][0] == b.rows()[0][0]              # identical content hash
