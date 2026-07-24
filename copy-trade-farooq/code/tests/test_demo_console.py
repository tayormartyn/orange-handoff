"""Console/demo-executor wiring + clipboard-watch advisory + guarded-hotkey structural tests."""
from __future__ import annotations
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_CON = os.path.join(_ROOT, "campaign_extractor", "paper_loop", "console")
for p in (_ROOT, _CON, os.path.join(_ROOT, "campaign_extractor", "demo_executor")):
    if p not in sys.path:
        sys.path.insert(0, p)

import clipboard_snip_watch as W


class _Img:
    def convert(self, _m):
        return self

    def save(self, buf, format=None):
        buf.write(b"PNGDATA")


def test_clipboard_watch_is_advisory_only():
    calls = []
    W._enum_clipboard_formats = lambda: [(8, "CF_DIB")]
    W._post = lambda url, obj: (calls.append(url) or
                                ((200, {"intake_id": "i", "duplicate": False}) if "upload" in url
                                 else (200, {"classification": {"value": "UNKNOWN"}})))
    W.watch(cycles=1, grab=lambda: _Img())
    assert any("/api/upload" in u for u in calls) and any("/api/analyse" in u for u in calls)
    # NEVER confirms / observes / proposes an order
    for forbidden in ("/api/observe", "/api/demo_approve", "/api/demo_arm", "/api/link"):
        assert not any(forbidden in u for u in calls)


def test_clipboard_dedup_same_image():
    calls = []
    W._enum_clipboard_formats = lambda: [(8, "CF_DIB")]
    W._post = lambda url, obj: (calls.append(url) or (200, {"intake_id": "i", "duplicate": True}))
    img = _Img()
    h1 = W.watch(cycles=3, grab=lambda: img)          # same image 3 cycles -> deduped to one upload
    assert h1 is not None and len([u for u in calls if "upload" in u]) == 1


def test_demo_endpoints_wired_in_server():
    src = open(os.path.join(_CON, "server.py"), encoding="utf-8").read()
    for e in ("/api/demo_preview", "/api/demo_arm", "/api/demo_approve"):
        assert e in src
    assert "demo_console_ext" in src


def test_frontend_demo_panel_and_guarded_hotkey():
    html = open(os.path.join(_CON, "index.html"), encoding="utf-8").read()
    assert "DEMO ORDER PREVIEW — NO ORDER SENT" in html
    assert "ARM DEMO ORDER" in html and "APPROVE DEMO ORDER" in html
    # guarded hotkey: ctrl+shift+enter, requires preview focus + armed + valid + 2s countdown + Esc
    assert "e.ctrlKey&&e.shiftKey&&e.key===" in html
    assert 'activeElement===$("demoPreview")' in html
    assert '$("armDemo").checked' in html and "escPressed" in html and "approving in 2s" in html


def test_frontend_never_sends_order_wording():
    html = open(os.path.join(_CON, "index.html"), encoding="utf-8").read()
    assert "NO ORDER SENT" in html and "order_sent=" in html   # UI shows the dry-run outcome


def test_demo_console_no_order_endpoint_call():
    for fn in ("demo_console_ext.py", "server.py"):
        src = open(os.path.join(_CON, fn), encoding="utf-8").read()
        assert "ProtoOANewOrder" not in src and "NewOrderReq" not in src and "sendorder" not in src.lower()


def test_update_endpoints_wired():
    src = open(os.path.join(_CON, "server.py"), encoding="utf-8").read()
    for e in ("/api/update_preview", "/api/update_arm", "/api/update_approve"):
        assert e in src


def test_frontend_update_panel_and_guarded_hotkey():
    html = open(os.path.join(_CON, "index.html"), encoding="utf-8").read()
    assert "DEMO TRADE UPDATE — NO ACTION SENT" in html
    assert "ARM DEMO UPDATE" in html and "APPROVE UPDATE" in html
    assert 'activeElement!==$("updPreview")' in html and "updEsc" in html and "approving update in 2s" in html


def test_console_update_no_amend_or_close_req():
    for fn in ("demo_console_ext.py", "server.py"):
        src = open(os.path.join(_CON, fn), encoding="utf-8").read()
        assert "ProtoOAAmendPositionSLTPReq" not in src and "ProtoOAClosePositionReq" not in src
