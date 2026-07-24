#!/usr/bin/env python3
"""
Stage 1 — TradingView logging-only webhook receiver (LOCALHOST ONLY).

DESIGN/SAFETY: This is an OBSERVATION / EVIDENCE-CAPTURE endpoint only.

It does NOT — and structurally CANNOT here —:
  * connect to or import any broker / cTrader / QST / execution / permit / lease / order module,
  * place / size / score / route a trade,
  * make any outbound network request,
  * change any execution gate.

It ONLY: receives a localhost POST, stores the raw body byte-exact + a UTC receipt time + a safe
subset of headers, assigns an event_id, classifies (read-only) for metadata, deduplicates, and
appends one line to an append-only JSONL log. Kill switch = Ctrl+C.

Standard library only (http.server) — no framework required for a single localhost logging endpoint.

Auth model:
  * bind 127.0.0.1 only (never 0.0.0.0),
  * POST only (any other method -> 405),
  * the exact long random SECRET PATH is the PRIMARY authentication control,
  * body size cap.

  Two auth modes (TV_WEBHOOK_AUTH_MODE):
    - PATH_AND_HEADER (default): exact secret path AND a valid X-TV-Token header both required.
      Use for MANUAL LOCAL POST TESTS only (Stage 1). This is the default so Stage 1 behaviour and
      its recorded results remain valid.
    - PATH_ONLY: the exact secret path alone authenticates. Use for real TradingView (Stage 2),
      because TradingView alerts CANNOT be assumed to send custom headers. The X-TV-Token header is
      optional in this mode (recorded if present, but not required).

  NOTE: X-TV-Token header is valid for manual local POST tests only. Real TradingView Stage 2 must
  authenticate by exact long random secret path unless custom header support is independently
  confirmed.

Config via environment (with safe local defaults so the test needs no real credentials):
  TV_WEBHOOK_SECRET_PATH   default: a fixed local test token (NOT a real secret)  [PRIMARY auth]
  TV_WEBHOOK_SHARED_SECRET default: a fixed local test token (NOT a real secret)  [local-test only]
  TV_WEBHOOK_AUTH_MODE     default: "PATH_AND_HEADER"  ("PATH_ONLY" for TradingView compatibility)
  TV_WEBHOOK_PORT          default: 8787
  TV_WEBHOOK_ENABLED       default: "1"  (set "0" to make the receiver refuse+log, a soft kill)
"""
from __future__ import annotations

import hmac
import http.server
import json
import os
import sys
import uuid
from datetime import datetime, timezone
from hashlib import sha256

# --- fail-closed import firewall -------------------------------------------------
# If any execution/broker/QST/permit surface is importable *and already loaded*, refuse to start.
_FORBIDDEN_MODULE_MARKERS = (
    "ctrader", "broker", "qst", "module_execution", "module_c_risk", "module_d_logger",
    "pipeline", "shadow_run", "shadow_db", "archive", "management_permit", "one_shot_permit",
    "activation_lease",
)

HERE = os.path.dirname(os.path.abspath(__file__))
LOG_DIR = os.path.join(HERE, "logs")
LOG_PATH = os.path.join(LOG_DIR, "tradingview_webhook_events.jsonl")

# Local, non-secret defaults (explicitly NOT real credentials).
SECRET_PATH = os.environ.get("TV_WEBHOOK_SECRET_PATH", "tv-local-test-path")       # PRIMARY auth
SHARED_SECRET = os.environ.get("TV_WEBHOOK_SHARED_SECRET", "tv-local-test-secret")  # local-test only
# PATH_AND_HEADER (default, manual local test) | PATH_ONLY (TradingView-compatible, Stage 2)
AUTH_MODE = os.environ.get("TV_WEBHOOK_AUTH_MODE", "PATH_AND_HEADER")
PORT = int(os.environ.get("TV_WEBHOOK_PORT", "8787"))
ENABLED = os.environ.get("TV_WEBHOOK_ENABLED", "1") == "1"
MAX_BODY = 64 * 1024  # 64 KB cap
SAFE_HEADER_KEYS = ("content-type", "content-length", "user-agent")
MODE = "LOGGING_ONLY"


def _startup_safety_check() -> None:
    loaded = set(sys.modules.keys())
    hits = [m for m in loaded if any(k in m.lower() for k in _FORBIDDEN_MODULE_MARKERS)]
    if hits:
        print("REFUSING TO START — forbidden module(s) loaded:", hits)
        raise SystemExit(2)


def _now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def _classify(raw: str):
    """Read-only classification. Never decides anything; only tags metadata. Never raises."""
    parse_status = "UNPARSED"
    ev = {"symbol": None, "timeframe": None, "alert_name": None, "event_type": None,
          "direction": None, "grade": None, "event_text": None}
    try:
        data = json.loads(raw)
        if not isinstance(data, dict):
            return "INVALID_JSON", ev
        parse_status = "PARSED"
        ev["symbol"] = data.get("symbol") or data.get("ticker")
        ev["timeframe"] = data.get("timeframe") or data.get("interval") or data.get("chart_interval")
        ev["alert_name"] = data.get("alert_name")
        ev["direction"] = data.get("direction")
        ev["grade"] = data.get("grade")
        ev["event_text"] = data.get("event_text") or data.get("description")
        raw_type = (data.get("event_type") or ev["event_text"] or "")
        t = str(raw_type).lower()
        if "a+++" in t:
            ev["event_type"] = "A_TRIPLE_PLUS"
        elif "a+" in t:
            ev["event_type"] = "A_PLUS"
        elif "sweep high" in t:
            ev["event_type"] = "SWEEP_HIGH"
        elif "sweep low" in t:
            ev["event_type"] = "SWEEP_LOW"
        elif "choch up" in t or "choch_up" in t:
            ev["event_type"] = "CHOCH_UP"
        elif "choch down" in t or "choch_down" in t:
            ev["event_type"] = "CHOCH_DOWN"
        elif "bpr tapped" in t:
            ev["event_type"] = "BPR_TAPPED"
        elif "bpr formed" in t:
            ev["event_type"] = "BPR_FORMED"
        elif "engulf" in t:
            ev["event_type"] = "ENGULFING"
        elif data.get("event_type"):
            ev["event_type"] = str(data.get("event_type"))
        # unresolved TradingView placeholder detection
        if "{{" in raw and "}}" in raw:
            parse_status = "UNRESOLVED_PLACEHOLDER"
    except json.JSONDecodeError:
        parse_status = "INVALID_JSON"
    except Exception:
        parse_status = "UNPARSED"
    return parse_status, ev


def _dedupe_key(ev, raw: str) -> str:
    basis = "|".join(str(x) for x in (
        ev.get("alert_name"), ev.get("symbol"), ev.get("timeframe"),
        ev.get("event_text"), ev.get("event_type"), ev.get("direction"),
    ))
    if not any((ev.get("alert_name"), ev.get("symbol"), ev.get("event_text"))):
        basis = raw  # degrade to whole-body hash when nothing parseable
    return sha256(basis.encode("utf-8", "replace")).hexdigest()


def _seen_dedupe_keys() -> set:
    keys = set()
    if not os.path.exists(LOG_PATH):
        return keys
    try:
        with open(LOG_PATH, "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                    if rec.get("validation_status") == "ACCEPTED" and rec.get("dedupe_key"):
                        keys.add(rec["dedupe_key"])
                except json.JSONDecodeError:
                    continue
    except OSError:
        pass
    return keys


def _append_jsonl(record: dict) -> None:
    os.makedirs(LOG_DIR, exist_ok=True)
    with open(LOG_PATH, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False) + "\n")
        fh.flush()
        os.fsync(fh.fileno())


class Handler(http.server.BaseHTTPRequestHandler):
    server_version = "TVLoggingOnly/0.1"

    def _reply(self, code: int, payload: dict) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):  # quieter, and never logs bodies/secrets
        sys.stderr.write("[recv] %s - %s\n" % (self.address_string(), fmt % args))

    # Any non-POST method -> 405, no side effects.
    def do_GET(self):
        self._reply(405, {"ok": False, "error": "method_not_allowed", "allow": "POST"})

    do_PUT = do_DELETE = do_HEAD = do_OPTIONS = do_PATCH = do_GET

    def do_POST(self):
        remote = self.client_address[0] if self.client_address else "?"
        # localhost guard (defensive; we also bind 127.0.0.1)
        if remote not in ("127.0.0.1", "::1"):
            self._reply(403, {"ok": False, "error": "localhost_only"})
            return

        if not ENABLED:
            # soft kill switch: refuse but record the hit
            self._record(remote, b"", "REJECTED_DISABLED", "receiver disabled (TV_WEBHOOK_ENABLED=0)")
            self._reply(503, {"ok": False, "error": "receiver_disabled"})
            return

        # PRIMARY auth = exact secret path (works for real TradingView, which cannot be assumed to
        # send custom headers). Any other path -> 404.
        path = self.path.split("?", 1)[0]
        expected_path = "/tv/" + SECRET_PATH
        if not hmac.compare_digest(path, expected_path):
            self._reply(404, {"ok": False, "error": "not_found"})
            return

        # X-TV-Token header: an ADDITIONAL control for MANUAL LOCAL TESTS only.
        #   PATH_AND_HEADER (default): header required (Stage 1 local test).
        #   PATH_ONLY (TradingView-compatible, Stage 2): path alone authenticates; header optional.
        got_secret = self.headers.get("X-TV-Token")
        header_present = got_secret is not None
        header_ok = header_present and hmac.compare_digest(got_secret, SHARED_SECRET)
        if AUTH_MODE == "PATH_AND_HEADER":
            if not header_ok:
                self._record(remote, b"", "REJECTED_AUTH",
                             "PATH_AND_HEADER mode: missing/incorrect X-TV-Token header")
                self._reply(401, {"ok": False, "error": "unauthorized"})
                return
            auth_note = None
        else:  # PATH_ONLY
            auth_note = ("PATH_ONLY: authenticated by secret path; "
                         + ("header present+valid" if header_ok
                            else "header present+INVALID (ignored)" if header_present
                            else "no header (expected for TradingView)"))

        # body size cap
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            length = 0
        if length <= 0 or length > MAX_BODY:
            self._record(remote, b"", "REJECTED_SIZE", f"content-length {length} outside 1..{MAX_BODY}")
            self._reply(413, {"ok": False, "error": "bad_body_size"})
            return

        raw_bytes = self.rfile.read(length)
        rec = self._record(remote, raw_bytes, "ACCEPTED", auth_note)
        self._reply(200, {"ok": True, "event_id": rec["event_id"],
                          "validation_status": rec["validation_status"],
                          "parse_status": rec["parse_status"],
                          "duplicate": rec["validation_status"] == "DUPLICATE"})

    def _record(self, remote, raw_bytes: bytes, validation_status: str, note):
        raw = raw_bytes.decode("utf-8", "replace")
        parse_status, ev = _classify(raw) if raw else ("UNPARSED", {
            "symbol": None, "timeframe": None, "alert_name": None,
            "event_type": None, "direction": None, "grade": None, "event_text": None})
        dedupe = _dedupe_key(ev, raw) if raw else ""
        vstatus = validation_status
        if validation_status == "ACCEPTED" and dedupe and dedupe in _seen_dedupe_keys():
            vstatus = "DUPLICATE"
        safe_headers = {k: self.headers.get(k) for k in SAFE_HEADER_KEYS
                        if self.headers.get(k) is not None}
        record = {
            "event_id": str(uuid.uuid4()),
            "received_at_utc": _now_utc(),
            "source": "TradingView",
            "raw_payload": raw,
            "raw_headers_safe": safe_headers,
            "remote_addr": remote,
            "method": self.command,
            "path": self.path.split("?", 1)[0],
            "parse_status": parse_status,
            "event_type": ev.get("event_type"),
            "direction": ev.get("direction"),
            "grade": ev.get("grade"),
            "symbol": ev.get("symbol"),
            "timeframe": ev.get("timeframe"),
            "dedupe_key": dedupe,
            "validation_status": vstatus,
            "notes": note,
            "mode": MODE,
        }
        _append_jsonl(record)
        return record


def main():
    _startup_safety_check()
    os.makedirs(LOG_DIR, exist_ok=True)
    httpd = http.server.HTTPServer(("127.0.0.1", PORT), Handler)
    print("=" * 60)
    print("  TradingView LOGGING-ONLY receiver (Stage 1, localhost)")
    print("=" * 60)
    print(f"  Mode        : {MODE}   (no execution, no broker/QST, no outbound)")
    print(f"  Bind        : http://127.0.0.1:{PORT}")
    print(f"  POST path   : /tv/{SECRET_PATH}   (PRIMARY auth = exact secret path)")
    print(f"  Auth mode   : {AUTH_MODE}   (PATH_AND_HEADER=local test | PATH_ONLY=TradingView)")
    print(f"  X-TV-Token  : {'required' if AUTH_MODE == 'PATH_AND_HEADER' else 'optional (local-test header; not needed for TradingView)'}")
    print(f"  Log (JSONL) : {LOG_PATH}")
    print(f"  Enabled     : {ENABLED}   (Ctrl+C to stop = kill switch)")
    print("=" * 60)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n  Stopped (Ctrl+C). Nothing was parsed for action, sized, logged as a trade, or sent.")
    finally:
        httpd.server_close()


if __name__ == "__main__":
    main()
