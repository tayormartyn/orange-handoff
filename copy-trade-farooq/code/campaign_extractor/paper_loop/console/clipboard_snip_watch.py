"""
Native Windows clipboard snip watch (ADVISORY ONLY). Runs under .venv-vision (Pillow ImageGrab).

Primary path is a Windows-native AddClipboardFormatListener on a hidden message-only window, so a
Win+Shift+S snip fires WM_CLIPBOARDUPDATE immediately. A polling fallback (used by tests and non-
Windows) shares the same processing core. On each clipboard image it: enumerates formats, extracts
the image (PNG / CF_DIBV5 / CF_DIB via ImageGrab), converts to PNG, SHA-256 dedups, POSTs to the
console /api/upload (source=WINDOWS_CLIPBOARD_SNIP) then /api/analyse, and writes a diagnostics status
file the console + browser read. It NEVER confirms/approves/orders/sends a broker action.

Diagnostics recorded (NEVER image bytes / tokens / secrets): clipboard formats, extraction result,
PNG conversion, SHA-256 prefix, upload status + intake id, analyse status, last safe error.
"""
from __future__ import annotations
import argparse
import base64
import hashlib
import io
import json
import os
import time
import urllib.request

CONSOLE = "http://127.0.0.1:8733"
POLL_SECONDS = 1.5
SNIP_SOURCE = "WINDOWS_CLIPBOARD_SNIP"
WM_CLIPBOARDUPDATE = 0x031D
_KNOWN_FMT = {2: "CF_BITMAP", 3: "CF_METAFILEPICT", 8: "CF_DIB", 17: "CF_DIBV5",
              1: "CF_TEXT", 13: "CF_UNICODETEXT", 15: "CF_HDROP"}


def _post(url, obj, timeout=180):
    req = urllib.request.Request(url, data=json.dumps(obj).encode(),
                                 headers={"Content-Type": "application/json"})
    r = urllib.request.urlopen(req, timeout=timeout)
    return r.getcode(), json.loads(r.read())


def _write_status(path, **fields):
    if not path:
        return
    try:
        cur = json.load(open(path, encoding="utf-8")) if os.path.exists(path) else {}
        cur.update(fields)
        cur["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        json.dump(cur, open(path, "w", encoding="utf-8"))
    except Exception:
        pass


def _console_alive(console):
    try:
        urllib.request.urlopen(console + "/api/snip_status", timeout=3)
        return True
    except Exception:
        return False


def _enum_clipboard_formats():
    """Return [(id, name)] currently on the clipboard (diagnostics only; no bytes read)."""
    try:
        import ctypes
        u = ctypes.windll.user32
        if not u.OpenClipboard(0):
            return []
        out, f = [], 0
        while True:
            f = u.EnumClipboardFormats(f)
            if f == 0:
                break
            buf = ctypes.create_unicode_buffer(64)
            n = u.GetClipboardFormatNameW(f, buf, 64)
            out.append((f, buf.value if n > 0 else _KNOWN_FMT.get(f, "#" + str(f))))
        u.CloseClipboard()
        return out
    except Exception:
        return []


def _extract_png(grab):
    """grab() -> PIL image / str / list / None. Returns (png_bytes|None, extraction_note)."""
    img = grab()
    if img is None:
        return None, "NO_IMAGE_ON_CLIPBOARD"
    if not hasattr(img, "save"):
        return None, "NON_IMAGE_IGNORED"           # clipboard TEXT / file-list
    buf = io.BytesIO()
    img.convert("RGB").save(buf, format="PNG")
    return buf.getvalue(), "PNG_OK"


def _process_once(console, state, status_file, grab):
    """Shared core: extract -> PNG -> dedup -> upload -> analyse -> status. Returns a diag dict."""
    formats = _enum_clipboard_formats()
    fmt_names = [n for _i, n in formats]
    try:
        png, note = _extract_png(grab)
    except Exception as e:                          # noqa: BLE001
        _write_status(status_file, status="ERROR", clipboard_formats=fmt_names,
                      last_error="EXTRACT_" + type(e).__name__)
        return {"uploaded": False, "note": "EXTRACT_ERROR"}
    if png is None:
        return {"uploaded": False, "note": note, "formats": fmt_names}
    h = hashlib.sha256(png).hexdigest()
    if h == state.get("last_hash"):
        return {"uploaded": False, "note": "DUPLICATE_HASH", "sha_prefix": h[:12]}
    state["last_hash"] = h
    b64 = "data:image/png;base64," + base64.b64encode(png).decode()
    try:
        up_code, up = _post(console + "/api/upload",
                            {"filename": "clipboard_snip.png", "data": b64, "source": SNIP_SOURCE})
        intake = up.get("intake_id")
        an_code, an = _post(console + "/api/analyse", {"intake_id": intake}) if intake else (None, {})
        _write_status(status_file, status="ON", pid=os.getpid(),
                      last_snip_received=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                      clipboard_formats=fmt_names, image_extraction=note, png_bytes_len=len(png),
                      sha256_prefix=h[:12], upload_status=up_code, last_intake_id=intake,
                      last_duplicate=up.get("duplicate"), analyse_status=an_code,
                      last_proposed_class=(an.get("classification") or {}).get("value"), last_error=None)
        print(f"[snip] event -> intake={intake} sha={h[:12]} upload={up_code} analyse={an_code} "
              f"class={(an.get('classification') or {}).get('value')} (ADVISORY)")
        return {"uploaded": True, "intake_id": intake, "sha_prefix": h[:12],
                "upload_status": up_code, "analyse_status": an_code, "formats": fmt_names}
    except Exception as e:                          # noqa: BLE001
        _write_status(status_file, status="ERROR", clipboard_formats=fmt_names,
                      sha256_prefix=h[:12], last_error="CONSOLE_POST_" + type(e).__name__)
        return {"uploaded": False, "note": "CONSOLE_POST_ERROR"}


def watch(console=CONSOLE, poll=POLL_SECONDS, cycles=None, grab=None, status_file=None):
    """Polling fallback (also used by tests). cycles=None runs forever."""
    if grab is None:
        from PIL import ImageGrab
        grab = ImageGrab.grabclipboard
    _write_status(status_file, status="ON", pid=os.getpid(), last_error=None)
    state, n = {"last_hash": None}, 0
    while True:
        n += 1
        _process_once(console, state, status_file, grab)
        if cycles is not None and n >= cycles:
            return state["last_hash"]
        if not _console_alive(console):
            _write_status(status_file, status="ERROR", last_error="CONSOLE_UNAVAILABLE")
        time.sleep(poll)


def watch_native(console=CONSOLE, status_file=None):
    """Windows-native path: hidden message-only window + AddClipboardFormatListener + message loop.
    WM_CLIPBOARDUPDATE fires on every Win+Shift+S. Falls back to watch() if the native setup fails."""
    import ctypes
    from ctypes import wintypes
    from PIL import ImageGrab

    user32 = ctypes.windll.user32
    state = {"last_hash": None}
    LRESULT = ctypes.c_ssize_t                       # pointer-sized on x64 (avoids OverflowError)
    user32.DefWindowProcW.restype = LRESULT
    user32.DefWindowProcW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
    WNDPROC = ctypes.WINFUNCTYPE(LRESULT, wintypes.HWND, wintypes.UINT,
                                 wintypes.WPARAM, wintypes.LPARAM)

    def _wndproc(hwnd, msg, wparam, lparam):
        if msg == WM_CLIPBOARDUPDATE:
            try:
                _process_once(console, state, status_file, ImageGrab.grabclipboard)
            except Exception as e:                  # noqa: BLE001
                _write_status(status_file, status="ERROR", last_error="EVENT_" + type(e).__name__)
        return user32.DefWindowProcW(hwnd, msg, wparam, lparam)

    proc = WNDPROC(_wndproc)                         # keep a ref so it is not GC'd
    HWND_MESSAGE = wintypes.HWND(-3)

    class WNDCLASS(ctypes.Structure):
        _fields_ = [("style", wintypes.UINT), ("lpfnWndProc", WNDPROC),
                    ("cbClsExtra", ctypes.c_int), ("cbWndExtra", ctypes.c_int),
                    ("hInstance", wintypes.HINSTANCE), ("hIcon", wintypes.HICON),
                    ("hCursor", wintypes.HANDLE), ("hbrBackground", wintypes.HBRUSH),
                    ("lpszMenuName", wintypes.LPCWSTR), ("lpszClassName", wintypes.LPCWSTR)]
    hinst = ctypes.windll.kernel32.GetModuleHandleW(None)
    wc = WNDCLASS()
    wc.lpfnWndProc = proc
    wc.hInstance = hinst
    wc.lpszClassName = "STSnipWatchWnd"
    if not user32.RegisterClassW(ctypes.byref(wc)):
        _write_status(status_file, status="ERROR", last_error="REGISTER_CLASS_FAILED")
        return watch(console, status_file=status_file)
    hwnd = user32.CreateWindowExW(0, wc.lpszClassName, "STSnipWatch", 0, 0, 0, 0, 0,
                                  HWND_MESSAGE, None, hinst, None)
    if not hwnd:
        _write_status(status_file, status="ERROR", last_error="CREATE_WINDOW_FAILED")
        return watch(console, status_file=status_file)
    if not user32.AddClipboardFormatListener(hwnd):
        _write_status(status_file, status="ERROR", last_error="ADD_LISTENER_FAILED")
        return watch(console, status_file=status_file)
    _write_status(status_file, status="ON", pid=os.getpid(), native_listener=True, last_error=None)
    print("[snip] native AddClipboardFormatListener active (Win+Shift+S -> WM_CLIPBOARDUPDATE)")
    # capture whatever is already on the clipboard once, then wait for events
    _process_once(console, state, status_file, ImageGrab.grabclipboard)
    msg = wintypes.MSG()
    while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
        user32.TranslateMessage(ctypes.byref(msg))
        user32.DispatchMessageW(ctypes.byref(msg))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--console", default=CONSOLE)
    ap.add_argument("--poll", type=float, default=POLL_SECONDS)
    ap.add_argument("--status-file", default=None)
    ap.add_argument("--polling", action="store_true", help="force polling instead of native listener")
    args = ap.parse_args()
    print(f"clipboard snip watch (ADVISORY) -> {args.console}. Confirms nothing.")
    try:
        if os.name == "nt" and not args.polling:
            watch_native(args.console, status_file=args.status_file)
        else:
            watch(args.console, args.poll, status_file=args.status_file)
    except KeyboardInterrupt:
        _write_status(args.status_file, status="OFF", last_error=None)
        print("\nstopped")


if __name__ == "__main__":
    main()
