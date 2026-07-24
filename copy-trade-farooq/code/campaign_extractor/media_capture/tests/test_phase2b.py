"""Brick 5C Phase 2B tests — live adapter (descriptor + bytes preserve). Mocks + temp only."""
from __future__ import annotations
import hashlib
import os
import shutil
import sys
import tempfile
import types

_HERE = os.path.dirname(os.path.abspath(__file__))
_MC = os.path.dirname(_HERE)
_CE = os.path.dirname(_MC)
for p in (_MC, _CE):
    if p not in sys.path:
        sys.path.insert(0, p)

import store as STORE
import live_adapter as LA
from media_db import MediaDB

PNG = b"\x89PNG\r\n\x1a\n" + bytes(48)


# --- mock Telethon-shaped media objects (class NAME drives classification) ---
class MessageMediaPhoto:
    def __init__(self, photo): self.photo = photo
class _Photo:
    def __init__(self, id, sizes): self.id = id; self.sizes = sizes
class _Size:
    def __init__(self, type, size): self.type = type; self.size = size
class MessageMediaDocument:
    def __init__(self, document): self.document = document
class _Doc:
    def __init__(self, id, mime): self.id = id; self.mime_type = mime
class MessageMediaWebPage:
    pass
class _Msg:
    def __init__(self, media, grouped=None): self.media = media; self.grouped_id = grouped


def _ident(mid, ref="md1", idx=0, grouped=None):
    return ("TELEGRAM", "-100C", str(mid), 1, grouped, idx, ref)


def _env():
    tmp = tempfile.mkdtemp(prefix="mc2b_")
    return tmp, MediaDB(os.path.join(tmp, "m.db")), os.path.join(tmp, "media")


def _images(d):
    return [] if not os.path.isdir(d) else [f for f in os.listdir(d)
                                            if not f.endswith((".db", ".part")) and ".incoming_" not in f]


# ===================================================== descriptor: photo largest-size
def test_descriptor_photo_largest():
    m = _Msg(MessageMediaPhoto(_Photo(7, [_Size("s", 100), _Size("y", 9000), _Size("m", 500)])))
    d = LA.build_descriptor(m)
    assert d["media_type"] == "photo"
    kind, mime, ext, ref = STORE.classify(d)
    assert kind == "PHOTO" and ref == "y"               # largest size selected


def test_descriptor_document_and_video():
    img = LA.build_descriptor(_Msg(MessageMediaDocument(_Doc(1, "image/png"))))
    assert STORE.classify(img)[0] == "IMAGE_DOCUMENT"
    vid = LA.build_descriptor(_Msg(MessageMediaDocument(_Doc(2, "video/mp4"))))
    assert STORE.classify(vid)[0] == "UNSUPPORTED"
    assert STORE.classify(LA.build_descriptor(_Msg(MessageMediaWebPage())))[0] == "UNSUPPORTED"
    assert STORE.classify(LA.build_descriptor(_Msg(None)))[0] == "NONE"


# ===================================================== preserve_bytes: capture + integrity
def test_preserve_bytes_capture():
    tmp, mdb, mdir = _env()
    try:
        desc = LA.build_descriptor(_Msg(MessageMediaPhoto(_Photo(7, [_Size("y", 9000)]))))
        st = STORE.preserve_bytes(PNG, desc, _ident("100", ref="ph100"), mdb,
                                  media_dir=mdir, max_bytes=10 * 1024 * 1024)
        assert st == "MEDIA_CAPTURED"
        assert mdb.rows()[0][2] == hashlib.sha256(PNG).hexdigest()
        on_disk = open(os.path.join(mdir, _images(mdir)[0]), "rb").read()
        assert on_disk == PNG                            # byte-for-byte
        mdb.close()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_preserve_bytes_dedup_toolarge_invalid_unsupported():
    tmp, mdb, mdir = _env()
    try:
        desc = LA.build_descriptor(_Msg(MessageMediaPhoto(_Photo(7, [_Size("y", 9000)]))))
        ident = _ident("101", ref="ph101")
        assert STORE.preserve_bytes(PNG, desc, ident, mdb, media_dir=mdir) == "MEDIA_CAPTURED"
        assert STORE.preserve_bytes(PNG, desc, ident, mdb, media_dir=mdir) == "DUPLICATE_MEDIA_REFERENCE"
        assert STORE.preserve_bytes(PNG + bytes(50), desc, _ident("102", ref="p102"), mdb,
                                    media_dir=mdir, max_bytes=16) == "MEDIA_TOO_LARGE"
        assert STORE.preserve_bytes(b"not-an-image", desc, _ident("103", ref="p103"), mdb,
                                    media_dir=mdir) == "INVALID_MEDIA"
        vid = LA.build_descriptor(_Msg(MessageMediaDocument(_Doc(2, "video/mp4"))))
        assert STORE.preserve_bytes(b"", vid, _ident("104", ref="p104"), mdb,
                                    media_dir=mdir) == "UNSUPPORTED_MEDIA_TYPE"
        mdb.close()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ===================================================== identical bytes, two messages
def test_preserve_bytes_identical_two_messages():
    tmp, mdb, mdir = _env()
    try:
        desc = LA.build_descriptor(_Msg(MessageMediaPhoto(_Photo(7, [_Size("y", 9000)]))))
        STORE.preserve_bytes(PNG, desc, _ident("105", ref="a"), mdb, media_dir=mdir)
        STORE.preserve_bytes(PNG, desc, _ident("106", ref="b"), mdb, media_dir=mdir)
        assert mdb.count() == 2 and len(_images(mdir)) == 1   # two links, one physical file
        mdb.close()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
