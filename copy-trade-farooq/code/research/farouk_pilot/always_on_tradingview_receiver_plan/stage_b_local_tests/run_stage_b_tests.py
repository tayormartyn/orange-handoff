#!/usr/bin/env python3
"""
Stage B — LOCAL UNIT TESTS for the always-on TradingView receiver logic.

LOCAL ONLY. No deployment, no public URL, no tunnel, no TradingView traffic, no Cloudflare, no
broker/QST/execution imports, no permits/leases/orders. Binds 127.0.0.1 on an ephemeral port and
drives requests in-process.

Design decision under test: REPORT-TIME DEDUPE as default.
  * Ingest is lossless + append-only: every accepted POST is stored as ACCEPTED (duplicates too).
  * Duplicates are NEVER discarded or flagged at ingest.
  * Distinct/deduped counts are computed LATER in a read-only report step (here, at the end).

Parity: this harness reuses the Stage-1/2 receiver's OWN functions (_classify, _dedupe_key, _now_utc,
SAFE_HEADER_KEYS) as the behavioural oracle, so the always-on logic reproduces proven behaviour.
"""
from __future__ import annotations

import hmac
import http.client
import http.server
import importlib.util
import json
import os
import sys
import threading
import types
import uuid

HERE = os.path.dirname(os.path.abspath(__file__))
ORACLE_PATH = os.path.abspath(os.path.join(
    HERE, "..", "..", "tradingview_webhook_plan", "stage1_local_receiver", "receiver.py"))
STAGE_B_LOG = os.path.join(HERE, "STAGE_B_TEST_EVENT_LOG.jsonl")

# --- import the proven receiver as the oracle (defines functions; does NOT run main()) ---
_spec = importlib.util.spec_from_file_location("stage1_receiver_oracle", ORACLE_PATH)
oracle = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(oracle)

MAXB = 64 * 1024
SECRET = "stageB-" + uuid.uuid4().hex          # local test secret path (NOT a real secret)
STATE = {"enabled": True}                       # kill-switch flag for B8


def append_log(rec):
    with open(STAGE_B_LOG, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
        fh.flush()
        os.fsync(fh.fileno())


class Handler(http.server.BaseHTTPRequestHandler):
    def _reply(self, code, payload):
        body = json.dumps(payload).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *a):
        pass

    def do_GET(self):
        self._reply(405, {"ok": False, "error": "method_not_allowed", "allow": "POST"})

    do_PUT = do_DELETE = do_HEAD = do_OPTIONS = do_PATCH = do_GET

    def do_POST(self):
        remote = self.client_address[0]
        if not STATE["enabled"]:
            self._reply(503, {"ok": False, "error": "receiver_disabled"})
            return
        path = self.path.split("?", 1)[0]
        if not hmac.compare_digest(path, "/tv/" + SECRET):
            self._reply(404, {"ok": False, "error": "not_found"})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            length = 0
        if length <= 0 or length > MAXB:
            self._reply(413, {"ok": False, "error": "bad_body_size"})
            return
        raw = self.rfile.read(length).decode("utf-8", "replace")
        parse_status, ev = oracle._classify(raw)           # oracle parity
        dedupe = oracle._dedupe_key(ev, raw)               # oracle parity
        tp = tt = sth = None
        try:
            p = json.loads(raw)
            if isinstance(p, dict):
                tp, tt, sth = p.get("trigger_price"), p.get("trigger_time"), p.get("server_time_hint")
        except Exception:
            pass
        safe_headers = {k: self.headers.get(k) for k in oracle.SAFE_HEADER_KEYS
                        if self.headers.get(k) is not None}
        rec = {
            "event_id": str(uuid.uuid4()),
            "received_at_utc": oracle._now_utc(),
            "source": "TradingView",
            "raw_payload": raw,
            "raw_headers_safe": safe_headers,
            "remote_addr": remote,
            "method": self.command,
            "path": path,
            "parse_status": parse_status,
            "event_type": ev.get("event_type"),
            "direction": ev.get("direction"),
            "grade": ev.get("grade"),
            "symbol": ev.get("symbol"),
            "timeframe": ev.get("timeframe"),
            "trigger_price": tp,
            "trigger_time": tt,
            "server_time_hint": sth,
            "dedupe_key": dedupe,
            "validation_status": "ACCEPTED",   # REPORT-TIME DEDUPE: never DUPLICATE at ingest
            "notes": "PATH_ONLY ingest; report-time dedupe (lossless append-only, no ingest discard)",
            "mode": "LOGGING_ONLY",
        }
        append_log(rec)
        self._reply(200, {"ok": True, "event_id": rec["event_id"],
                          "validation_status": "ACCEPTED", "parse_status": parse_status})


# ---- test payloads ----
P1 = json.dumps({
    "schema_version": "tv-webhook-0.1", "source": "TradingView", "lane": "LOGGING_ONLY", "test": True,
    "alert_name": "LIVE001_WEBHOOK_TEST_ALWAYSON", "symbol": "XAUUSD", "exchange": "PEPPERSTONE",
    "timeframe": "3", "event_text": "always-on receiver test - harmless, no signal, no instruction",
    "trigger_price": "4142.14", "trigger_time": "2026-07-07T16:15:00Z",
    "server_time_hint": "2026-07-07T16:15:38Z"})
P2 = json.dumps({
    "schema_version": "tv-webhook-0.1", "source": "TradingView",
    "alert_name": "LIVE001_WEBHOOK_TEST_ALWAYSON", "symbol": "{{ticker}}", "exchange": "{{exchange}}",
    "timeframe": "{{interval}}", "event_text": "always-on placeholder test",
    "trigger_price": "{{close}}", "trigger_time": "{{time}}", "server_time_hint": "{{timenow}}"})
P3 = "XAUUSD Crossing 4,134.00"


def req(method, path, port, body=None):
    c = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
    headers = {"Content-Type": "application/json"} if body is not None else {}
    c.request(method, path, body=(body.encode() if isinstance(body, str) else body), headers=headers)
    r = c.getresponse()
    data = r.read().decode()
    c.close()
    return r.status, data


def main():
    # fresh test artifact each run (this is a TEST log, deterministic per run)
    open(STAGE_B_LOG, "w", encoding="utf-8").close()
    httpd = http.server.HTTPServer(("127.0.0.1", 0), Handler)
    port = httpd.server_address[1]
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    good = "/tv/" + SECRET
    results = []

    def check(tid, desc, cond, detail):
        results.append((tid, desc, "PASS" if cond else "FAIL", detail))

    # B1 valid JSON -> 200 ACCEPTED/PARSED
    s, d = req("POST", good, port, P1)
    j = json.loads(d)
    check("B1", "valid JSON -> ACCEPTED/PARSED",
          s == 200 and j.get("validation_status") == "ACCEPTED" and j.get("parse_status") == "PARSED",
          f"status={s} {d}")
    # B2 wrong path -> 404
    s, d = req("POST", "/tv/WRONG" + SECRET + "WRONG", port, P1)
    check("B2", "wrong path -> 404", s == 404, f"status={s} {d}")
    # B3 GET -> 405
    s, d = req("GET", good, port)
    check("B3", "GET -> 405", s == 405, f"status={s} {d}")
    # B4 default text -> ACCEPTED/INVALID_JSON
    s, d = req("POST", good, port, P3)
    j = json.loads(d)
    check("B4", "default text -> ACCEPTED/INVALID_JSON",
          s == 200 and j.get("parse_status") == "INVALID_JSON", f"status={s} {d}")
    # B5 placeholders literal -> UNRESOLVED_PLACEHOLDER
    s, d = req("POST", good, port, P2)
    j = json.loads(d)
    check("B5", "literal {{...}} -> UNRESOLVED_PLACEHOLDER",
          s == 200 and j.get("parse_status") == "UNRESOLVED_PLACEHOLDER", f"status={s} {d}")
    # B6 duplicate of B1 -> ACCEPTED append-only, distinct unchanged in report
    s, d = req("POST", good, port, P1)
    j = json.loads(d)
    b6_accepted = (s == 200 and j.get("validation_status") == "ACCEPTED")
    # B7 oversize -> 413
    s, d = req("POST", good, port, "x" * (MAXB + 10))
    check("B7", "oversize body -> 413", s == 413, f"status={s} {d}")
    # B8 disabled -> 503
    STATE["enabled"] = False
    s, d = req("POST", good, port, P1)
    check("B8", "kill switch (enabled=false) -> 503", s == 503, f"status={s} {d}")
    STATE["enabled"] = True

    # ---- report-time dedupe (read-only) ----
    recs = [json.loads(x) for x in open(STAGE_B_LOG, encoding="utf-8") if x.strip()]
    accepted = [r for r in recs if r["validation_status"] == "ACCEPTED"]
    raw_ingested = len(accepted)
    distinct = len({r["dedupe_key"] for r in accepted})
    any_dup_flag_at_ingest = any(r["validation_status"] == "DUPLICATE" for r in recs)
    p1_key = accepted[0]["dedupe_key"]
    p1_ingested = sum(1 for r in accepted if r["dedupe_key"] == p1_key)
    p1_distinct = 1  # by definition of a single key
    check("B6", "duplicate: ACCEPTED append-only + distinct unchanged (report-time)",
          b6_accepted and raw_ingested == 4 and distinct == 3
          and p1_ingested == 2 and not any_dup_flag_at_ingest,
          f"raw_ingested={raw_ingested} distinct={distinct} p1_ingested={p1_ingested} "
          f"dup_flag_at_ingest={any_dup_flag_at_ingest}")

    # B10 UTC + provider time verbatim + raw byte-exact
    r0 = accepted[0]
    utc_ok = r0["received_at_utc"].endswith("Z")
    provider_verbatim = json.loads(r0["raw_payload"]).get("trigger_time") == "2026-07-07T16:15:00Z"
    raw_exact = r0["raw_payload"] == P1
    evid_ok = bool(r0["event_id"])
    check("B10", "UTC receiver ts + provider time verbatim + raw byte-exact + event_id",
          utc_ok and provider_verbatim and raw_exact and evid_ok,
          f"utc={utc_ok} provider_verbatim={provider_verbatim} raw_exact={raw_exact} event_id={evid_ok}")

    # B9 import firewall (fail-closed)
    clean_ok = True
    try:
        oracle._startup_safety_check()
    except SystemExit:
        clean_ok = False
    sys.modules["ctrader_fake_injected"] = types.ModuleType("ctrader_fake_injected")
    refused = False
    try:
        oracle._startup_safety_check()
    except SystemExit as e:
        refused = (e.code == 2)
    del sys.modules["ctrader_fake_injected"]
    check("B9", "import firewall: clean passes, forbidden module refused",
          clean_ok and refused, f"clean_pass={clean_ok} forbidden_refused={refused}")

    httpd.shutdown()

    # ---- output ----
    print("=== STAGE B UNIT TEST RESULTS ===")
    order = ["B1", "B2", "B3", "B4", "B5", "B6", "B7", "B8", "B9", "B10"]
    by = {r[0]: r for r in results}
    npass = 0
    for tid in order:
        _, desc, verdict, detail = by[tid]
        if verdict == "PASS":
            npass += 1
        print(f"  {tid}: {verdict}  {desc}")
        print(f"        {detail}")
    print(f"=== {npass}/{len(order)} PASSED ===")
    print("REPORT-TIME DEDUPE:")
    print(f"  raw_ingested_accepted = {raw_ingested}")
    print(f"  distinct_events (by dedupe_key) = {distinct}")
    print(f"  duplicate_flag_at_ingest = {any_dup_flag_at_ingest}  (must be False = lossless ingest)")
    print(f"  P1 ingested {p1_ingested}x -> distinct 1 (duplicate collapses only in report)")
    print(f"STAGE_B_LOG = {STAGE_B_LOG}")
    print("OVERALL:", "PASS" if npass == len(order) else "FAIL")


if __name__ == "__main__":
    main()
