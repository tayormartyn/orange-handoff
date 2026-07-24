"""Snip Watch tests — clipboard image watcher is ADVISORY only. Fake clipboard + fake console (no
real HTTP, no Pillow). Proves text ignored, first image imported + auto-OCR, duplicate ignored, and
that it NEVER confirms / approves / orders / sends a broker action."""
from __future__ import annotations
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_CONSOLE = os.path.join(_ROOT, "campaign_extractor", "paper_loop", "console")
for p in (_ROOT, _CONSOLE):
    if p not in sys.path:
        sys.path.insert(0, p)

import clipboard_snip_watch as CSW


class FakeImg:
    """Mimics a PIL image just enough for the watcher (convert().save(buf, format))."""
    def __init__(self, payload):
        self.payload = payload

    def convert(self, mode):
        return self

    def save(self, buf, format):        # noqa: A002
        buf.write(self.payload)


def _install_fake_console(monkey_calls):
    """Replace _post so nothing hits the network; record every (url, payload)."""
    def fake_post(url, obj, timeout=180):
        monkey_calls.append((url, obj))
        if url.endswith("/api/upload"):
            return 200, {"intake_id": "intake-snip-1", "duplicate": False}
        if url.endswith("/api/analyse"):
            return 200, {"classification": {"value": "SIGNAL"}}
        return 200, {}
    CSW._post = fake_post
    CSW._console_alive = lambda console: True
    CSW._enum_clipboard_formats = lambda: [(8, "CF_DIB"), (49290, "PNG")]


def _run(grab, calls, cycles=1):
    _install_fake_console(calls)
    return CSW.watch(console="http://x", poll=0, cycles=cycles, grab=grab)


# ---- text ignored ----
def test_text_clipboard_ignored():
    calls = []
    _run(lambda: "SELL XAUUSD 4100 — this is clipboard text", calls, cycles=1)
    assert calls == []                                    # no upload/analyse for text


def test_none_and_filelist_ignored():
    calls = []
    _run(lambda: None, calls, cycles=1)
    _run(lambda: ["C:/some/file.png"], calls, cycles=1)   # file list has no .save
    assert calls == []


# ---- first image imported + auto OCR ----
def test_first_image_imported_and_ocr_auto():
    calls = []
    _run(lambda: FakeImg(b"SNIP-IMAGE-BYTES-1"), calls, cycles=1)
    urls = [u for u, _ in calls]
    assert any(u.endswith("/api/upload") for u in urls)
    assert any(u.endswith("/api/analyse") for u in urls)   # OCR begins automatically
    upload = next(o for u, o in calls if u.endswith("/api/upload"))
    assert upload["source"] == "WINDOWS_CLIPBOARD_SNIP"    # intake source recorded


# ---- duplicate image ignored ----
def test_duplicate_image_ignored():
    calls = []
    img = FakeImg(b"SAME-BYTES")
    _run(lambda: img, calls, cycles=3)                     # same image three cycles
    uploads = [u for u, _ in calls if u.endswith("/api/upload")]
    assert len(uploads) == 1                               # SHA dedup -> imported once only


# ---- NEVER confirms / approves / orders / broker action ----
def test_never_confirms_approves_or_orders():
    calls = []
    _run(lambda: FakeImg(b"SNIP-IMAGE-BYTES-2"), calls, cycles=1)
    urls = [u for u, _ in calls]
    for forbidden in ("/api/observe", "/api/demo_approve", "/api/demo_arm", "/api/update_approve",
                      "/api/update_arm", "/api/snip_start"):
        assert not any(forbidden in u for u in urls)       # advisory only
    # watcher only ever touches upload + analyse
    assert set(u.split("/api/")[-1] for u in urls) <= {"upload", "analyse"}


def test_source_and_advisory_constant():
    assert CSW.SNIP_SOURCE == "WINDOWS_CLIPBOARD_SNIP"
    src = open(os.path.join(_CONSOLE, "clipboard_snip_watch.py"), encoding="utf-8").read()
    # forbid actual confirm/approve/order CALLS (not the docstring word "confirms")
    for bad in ("ProtoOANewOrderReq", "/api/demo_approve", "/api/update_approve", "/api/observe"):
        assert bad not in src


def test_status_file_written(tmp_path=None):
    import tempfile
    tmp = tempfile.mkdtemp()
    try:
        sf = os.path.join(tmp, "snip_status.json")
        calls = []
        _install_fake_console(calls)
        CSW.watch(console="http://x", poll=0, cycles=1, grab=lambda: FakeImg(b"S"), status_file=sf)
        import json
        st = json.load(open(sf))
        assert st["status"] == "ON" and st["last_intake_id"] == "intake-snip-1"
        assert st["last_proposed_class"] == "SIGNAL" and st.get("last_error") is None
    finally:
        import shutil
        shutil.rmtree(tmp, ignore_errors=True)
