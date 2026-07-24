"""
Fix tests for Telegram photo (MessageMediaPhoto) capture + the silent-drop failure-recording bug.

Runnable: python test_media_capture_photo_fix.py   (also pytest-compatible).

Covers:
  - MessageMediaPhoto captured & written to disk (sha256 / provenance recorded)
  - failure path ALWAYS records a row (no silent drop) — incl. against an old narrow CHECK
  - webpages/link previews still classify UNSUPPORTED
  - media_capture imports no broker/qst/ctrader/execution/order/permit/lease code (no exec surface)
"""
import asyncio
import glob
import os
import re
import sqlite3
import sys
import tempfile

_HERE = os.path.dirname(os.path.abspath(__file__))
_PKG = os.path.dirname(_HERE)
for p in (_PKG, _HERE):
    if p not in sys.path:
        sys.path.insert(0, p)

import live_adapter as LA          # noqa: E402
import store as STORE              # noqa: E402
from media_db import MediaDB       # noqa: E402

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 40          # valid PNG magic + padding
IDENT = ("TELEGRAM", "-1001902136163", "45641", 1, None, 0, "media:MessageMediaPhoto:45641")
TS = {"posted_at": "2026-07-10T15:16:51+00:00", "received_at": "2026-07-10T15:16:52+00:00"}


# ---- realistic Telethon-ish photo objects ----
class _Size:
    def __init__(self, t, size): self.type = t; self.size = size


class _Photo:
    def __init__(self): self.id = 777; self.sizes = [_Size("y", 9000)]


class MessageMediaPhoto:                      # class name contains "Photo" (what build_descriptor checks)
    def __init__(self): self.photo = _Photo()


class MessageMediaWebPage:
    def __init__(self): self.webpage = object()


class _Msg:
    def __init__(self, media): self.media = media; self.grouped_id = None; self.id = 45641


class GoodClient:
    """iter_download yields the image bytes as an async generator."""
    def __init__(self, chunks): self.chunks = chunks
    async def iter_download(self, media):
        for c in self.chunks:
            yield c
    async def download_media(self, message, file=bytes):
        return b"".join(self.chunks)


class BadIterClient:
    """iter_download raises AttributeError (like the live bug) -> must be RECORDED, not silently dropped."""
    def iter_download(self, media):
        raise AttributeError("'MessageMediaPhoto' object has no attribute 'document'")


class DeadClient:
    """download fails -> must be recorded as a failure row, never silently dropped."""
    def iter_download(self, media):
        raise AttributeError("boom")


def _mk_db():
    d = tempfile.mkdtemp()
    return MediaDB(os.path.join(d, "m.db")), d


# ===================================================================== capture to disk
def test_photo_captured_to_disk_with_provenance():
    mdb, d = _mk_db()
    st = asyncio.run(LA.preserve_live(GoodClient([PNG]), _Msg(MessageMediaPhoto()),
                                      media_db=mdb, media_dir=d, max_bytes=10 * 1024 * 1024,
                                      identity=IDENT, timestamps=TS))
    assert st == "MEDIA_CAPTURED", st
    files = [f for f in glob.glob(os.path.join(d, "*")) if f.endswith(".png")]
    assert len(files) == 1, files                                   # written to disk
    import hashlib
    sha = hashlib.sha256(PNG).hexdigest()
    assert os.path.basename(files[0]) == f"{sha}.png"               # content-addressed name
    row = mdb.con.execute("SELECT capture_status, content_sha256, byte_count, storage_relative_path, "
                          "telegram_media_reference FROM media_records").fetchone()
    assert row[0] == "MEDIA_CAPTURED" and row[1] == sha and row[2] == len(PNG)
    assert row[3] == f"{sha}.png" and row[4] == IDENT[6]            # provenance metadata


def test_iter_download_error_is_recorded_not_dropped():
    # the sanctioned iter_download primitive raising must be RECORDED (no silent drop)
    mdb, d = _mk_db()
    st = asyncio.run(LA.preserve_live(BadIterClient(), _Msg(MessageMediaPhoto()),
                                      media_db=mdb, media_dir=d, max_bytes=10 * 1024 * 1024,
                                      identity=IDENT, timestamps=TS))
    assert st == "MEDIA_DOWNLOAD_FAILED", st
    assert mdb.by_status("MEDIA_DOWNLOAD_FAILED") == 1
    # the recorded reason carries the real error message for diagnosis
    reason = mdb.con.execute("SELECT failure_reason FROM media_records").fetchone()[0]
    assert "AttributeError" in reason


# ===================================================================== never silently drops
def test_failure_path_records_a_row_not_silent():
    mdb, d = _mk_db()
    st = asyncio.run(LA.preserve_live(DeadClient(), _Msg(MessageMediaPhoto()),
                                      media_db=mdb, media_dir=d, max_bytes=10 * 1024 * 1024,
                                      identity=IDENT, timestamps=TS))
    assert st in ("MEDIA_DOWNLOAD_FAILED", "MEDIA_HANDLING_ERROR"), st
    assert mdb.count() == 1                                          # a failure row exists (not dropped)


def test_record_failure_media_handling_error_is_allowed_now():
    mdb, _ = _mk_db()
    STORE.record_failure(mdb, IDENT, "MEDIA_HANDLING_ERROR", kind="unknown", reason="AttributeError: x")
    assert mdb.by_status("MEDIA_HANDLING_ERROR") == 1


def test_record_failure_resilient_against_old_narrow_check():
    # Simulate an OLDER media DB whose CHECK predates MEDIA_HANDLING_ERROR: record_failure must still
    # write a row (fallback), never raise, never silently drop.
    d = tempfile.mkdtemp()
    path = os.path.join(d, "old.db")
    con = sqlite3.connect(path)
    con.execute("CREATE TABLE media_records (rowseq INTEGER PRIMARY KEY AUTOINCREMENT, "
                "media_record_uid TEXT, evidence_row_uid TEXT, platform TEXT, channel_id TEXT, "
                "message_id TEXT, message_revision_number INTEGER, telegram_media_reference TEXT, "
                "grouped_media_id TEXT, media_index INTEGER, media_type TEXT, mime_type TEXT, "
                "safe_extension TEXT, byte_count INTEGER, content_sha256 TEXT, storage_relative_path TEXT, "
                "capture_status TEXT NOT NULL, failure_reason TEXT, telegram_posted_at_utc TEXT, "
                "listener_received_at_utc TEXT, media_download_started_at_utc TEXT, "
                "media_download_completed_at_utc TEXT, schema_version TEXT, created_at TEXT, "
                "CHECK (capture_status IN ('MEDIA_CAPTURED','MEDIA_DOWNLOAD_FAILED')))")
    con.commit()

    class OldDB:
        def __init__(self, c): self.con = c
        def append(self, rec):
            cols = list(rec.keys())
            self.con.execute(f"INSERT INTO media_records ({','.join(cols)}) VALUES "
                             f"({','.join('?'*len(cols))})", [rec[c] for c in cols])
            self.con.commit()
            return rec

    olddb = OldDB(con)
    out = STORE.record_failure(olddb, IDENT, "MEDIA_HANDLING_ERROR", kind="unknown",
                               reason="AttributeError: y")
    assert out == "MEDIA_HANDLING_ERROR"                            # intended status returned
    n, reason = con.execute("SELECT COUNT(*), MAX(failure_reason) FROM media_records").fetchone()
    assert n == 1                                                   # a row WAS written (fallback)
    assert "MEDIA_HANDLING_ERROR" in reason                         # true status preserved in reason
    con.close()


# ===================================================================== webpages still UNSUPPORTED
def test_webpage_still_unsupported():
    desc = LA.build_descriptor(_Msg(MessageMediaWebPage()))
    assert STORE.classify(desc)[0] == "UNSUPPORTED"
    mdb, d = _mk_db()
    st = asyncio.run(LA.preserve_live(GoodClient([PNG]), _Msg(MessageMediaWebPage()),
                                      media_db=mdb, media_dir=d, max_bytes=10 * 1024 * 1024,
                                      identity=("TELEGRAM", "-1", "1", 1, None, 0, "media:MessageMediaWebPage:1"),
                                      timestamps=TS))
    assert st == "UNSUPPORTED_MEDIA_TYPE", st


def test_descriptor_defensive_on_bad_size_object():
    class Weird:  # a size object that raises on attribute access
        @property
        def size(self): raise AttributeError("nope")
        @property
        def sizes(self): raise AttributeError("nope")
    class P:
        def __init__(self): self.id = 1; self.sizes = [Weird()]
    class M:
        def __init__(self): self.photo = P()
    class Mp:  # name contains Photo
        pass
    m = _Msg(MessageMediaPhoto())
    m.media = type("MessageMediaPhoto", (), {})()
    m.media.photo = P()
    d = LA.build_descriptor(m)                                      # must not raise
    assert d["media_type"] == "photo"


# ===================================================================== no execution surface
def test_no_forbidden_imports_in_media_capture():
    # inspect ONLY real import statements (module path), not arbitrary lines/SQL strings
    imp = re.compile(r"^\s*(?:from|import)\s+([\w\.]+)")
    forbidden = re.compile(r"(broker|ctrader|qst|execution|order|permit|lease|module_b|"
                           r"demo_executor|risk)", re.I)
    pyfiles = glob.glob(os.path.join(_PKG, "*.py"))
    offenders = []
    for f in pyfiles:
        for ln in open(f, encoding="utf-8"):
            m = imp.match(ln)
            if m and forbidden.search(m.group(1)):
                offenders.append((os.path.basename(f), ln.strip()[:80]))
    assert offenders == [], offenders


# ===================================================================== config collision defeated
def _root_dir():
    return os.path.dirname(os.path.dirname(os.path.dirname(_HERE)))   # signal-terminal root


def test_root_config_lacks_image_settings_and_media_config_has_them():
    # Reproduce the collision source: the ROOT project config.py has NO image settings.
    root = _root_dir()
    if root not in sys.path:
        sys.path.insert(0, root)
    import importlib
    rootcfg = importlib.import_module("config")            # this is the ROOT config (MODE/gates)
    assert not hasattr(rootcfg, "PERMITTED_IMAGE_TYPES"), "root config unexpectedly has image settings"
    # media_capture store must still hold ITS OWN config with the image settings
    assert hasattr(STORE.CFG, "PERMITTED_IMAGE_TYPES")
    assert STORE.CFG.PERMITTED_IMAGE_TYPES == ("jpeg", "png", "webp", "bmp")
    assert STORE.CFG is not rootcfg                        # not the root module


def test_store_config_survives_reload_with_root_config_shadowing():
    # Force 'config' in sys.modules to be the ROOT config (as the live listener leaves it), then
    # reload store; store must STILL resolve media_capture/config.py (collision defeated).
    root = _root_dir()
    if root not in sys.path:
        sys.path.insert(0, root)
    import importlib
    importlib.import_module("config")                      # sys.modules['config'] = ROOT config
    importlib.reload(STORE)                                # re-runs store's collision-proof config load
    assert hasattr(STORE.CFG, "PERMITTED_IMAGE_TYPES")
    assert STORE.CFG.TYPE_TO_EXT.get("png") == "png"


def test_photo_capture_works_even_with_root_config_shadowing():
    # End-to-end proof: with root 'config' shadowing, a MessageMediaPhoto still validates + captures.
    root = _root_dir()
    if root not in sys.path:
        sys.path.insert(0, root)
    import importlib
    importlib.import_module("config")                      # simulate the live collision
    mdb, d = _mk_db()
    st = asyncio.run(LA.preserve_live(GoodClient([PNG]), _Msg(MessageMediaPhoto()),
                                      media_db=mdb, media_dir=d, max_bytes=10 * 1024 * 1024,
                                      identity=IDENT, timestamps=TS))
    assert st == "MEDIA_CAPTURED", st                      # would have been MEDIA_HANDLING_ERROR before
    assert mdb.by_status("MEDIA_CAPTURED") == 1


def _run_all():
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    passed, failed = 0, []
    for t in tests:
        try:
            t(); passed += 1; print(f"PASS  {t.__name__}")
        except Exception as e:  # noqa: BLE001
            failed.append((t.__name__, repr(e))); print(f"FAIL  {t.__name__}: {e!r}")
    print(f"\n{passed}/{len(tests)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(_run_all())
