"""
Manual Signal Intake Console — smallest local browser front-end over the ALREADY-TESTED services
(image_intake, image_confirm, image_paper_run). It duplicates NO intake / review / Q4A / PaperDB
logic; every step calls the existing tested function. Local only, read-only w.r.t. protected data,
no order/execution path. Stdlib http.server (no framework, no pip install).

Flow: upload -> immutable intake + SHA dedup -> classify SIGNAL/TRADE_RESULT/UNKNOWN -> human field
review -> explicit confirm -> UnifiedSignal -> Q4A (recorded quotes where coverage exists) ->
append-only PAPER observation -> alert -> STOP.

Run:  python campaign_extractor/paper_loop/console/server.py   (serves http://127.0.0.1:8733)
"""
from __future__ import annotations
import base64
import json
import os
import sys
import tempfile
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

_HERE = os.path.dirname(os.path.abspath(__file__))
_PL = os.path.dirname(_HERE)
_CE = os.path.dirname(_PL)
_ROOT = os.path.dirname(_CE)
_Q4 = os.path.join(_CE, "q4_align")
_VIS = os.path.join(_CE, "vision_v1")
for p in (_ROOT, _CE, _Q4, _PL, _VIS):
    if p not in sys.path:
        sys.path.insert(0, p)

import image_intake
import image_confirm
import image_paper_run as R
import console_ext as EXT                    # accelerator: effective status, parent links, queue
import demo_console_ext as DEMO               # adapter over demo_executor (DRY-RUN preview only)
sys.path.insert(0, _ROOT)
import farouk_cohort_monitor as COHORT      # reused read-only; no cohort logic duplicated here
sys.path.insert(0, os.path.join(_ROOT, "campaign_extractor", "trade_lifecycle"))
import lifecycle_console as LIFECYCLE       # DERIVED read-only trade-lifecycle timelines

HOST, PORT = "127.0.0.1", 8733
FRIENDLY = {"GOLD": "XAUUSD", "BITCOIN": "BTCUSD", "XAU": "XAUUSD", "BTC": "BTCUSD"}
VENV_VISION_PY = os.path.join(_ROOT, ".venv-vision", "Scripts", "python.exe")
OCR_RUNNER = os.path.join(_HERE, "ocr_runner.py")


def _ext(filename, data_b64):
    if "image/png" in data_b64[:40] or (filename or "").lower().endswith(".png"):
        return ".png"
    if (filename or "").lower().endswith((".jpg", ".jpeg")) or "image/jpeg" in data_b64[:40]:
        return ".jpg"
    return ".png"


def do_upload(filename, data_b64, *, candidate_db=None, root=None, source=None):
    """Decode an uploaded image, immutably import it (SHA dedup), return the intake summary."""
    raw = base64.b64decode(data_b64.split(",")[-1])
    fd, tmp = tempfile.mkstemp(suffix=_ext(filename, data_b64))
    os.close(fd)
    with open(tmp, "wb") as f:
        f.write(raw)
    try:
        manifest, _mpath = image_intake.import_intake_image(
            tmp, source_server_channel_text=(source or "manual console upload"),
            candidate_db=candidate_db, root=root)
    finally:
        try:
            os.remove(tmp)
        except OSError:
            pass
    return {"intake_id": manifest["intake_id"], "media_id": manifest["imported_media_id"],
            "sha256": manifest["original_image_sha256"], "duplicate": manifest["duplicate"],
            "screenshot_imported_at": manifest["screenshot_imported_at"],
            "intake_status": manifest["intake_status"]}


def _answers(payload):
    instr = (payload.get("instrument") or "").strip().upper()
    instr = FRIENDLY.get(instr, instr)
    ic = (payload.get("intake_class") or "UNKNOWN").upper()
    return {"intake_class": ic,
            "semantic_class": "SIGNAL_ANNOUNCEMENT" if ic == "SIGNAL" else ic,
            "instrument": instr, "direction": payload.get("direction"),
            "entry_low": payload.get("entry_low"), "entry_high": payload.get("entry_high"),
            "stop_price": payload.get("stop_price"), "target_prices": payload.get("target_prices"),
            "provider": payload.get("provider") or "UNKNOWN",
            "provider_posted_at": payload.get("provider_posted_at"),
            "provider_posted_timezone": payload.get("provider_posted_timezone"),
            "provider_posted_provenance": payload.get("provider_posted_provenance"),
            "source_evidence_references": payload.get("source_evidence"),
            "source_provenance": payload.get("source_provenance"),
            "source_attested": bool(payload.get("source_attested")),
            "reviewer_ref": payload.get("reviewer_ref") or "console",
            "visible_result_fields": payload.get("visible_result_fields"),
            "explicit_confirmation": bool(payload.get("confirm"))}


def _final_status(run_result):
    st = run_result.get("status")
    if st == "ALREADY_OBSERVED":
        return "DUPLICATE"
    if st in ("BLOCKED", "REJECTED"):
        return "BLOCKED"
    if st == "TRADE_RESULT_EXCLUDED":
        return "TRADE_RESULT_EXCLUDED"
    if st == "TRADE_UPDATE_EXCLUDED":
        return "TRADE_UPDATE_EXCLUDED"
    if run_result.get("coverage") in ("NO_COVERAGE", "NO_FRESH_QUOTE"):
        return "NO_COVERAGE"
    return "RECORDED"


def do_observe(payload, *, root=None, paper_db=None, bridge_db=None, alert_dir=None,
               quotes=None, move_file=True, status_root=None, _no_status=False):
    """classify -> review -> explicit confirm -> UnifiedSignal -> Q4A -> PAPER observation -> alert."""
    intake_id = payload["intake_id"]
    manifest = image_intake.load_manifest(intake_id, root)
    if manifest is None:
        return {"final_status": "BLOCKED", "reason": "INTAKE_NOT_FOUND"}
    rec = image_confirm.build_review_record(intake_id, manifest, _answers(payload))
    saved, _p, _new = image_confirm.save_review(rec)
    result = R.run(intake_id, saved["review_id"], quotes=quotes, paper_db=paper_db,
                   bridge_db=bridge_db, alert_dir=alert_dir, move_file=move_file)
    final = _final_status(result)
    # append-only effective-status event AFTER the run's own writes (manifest never changed)
    if not _no_status:
        EXT.record_effective_status(intake_id, EXT.effective_from_final(final),
                                    detail={"run_status": result.get("status"),
                                            "review_id": saved["review_id"]}, root=status_root)
    return {"final_status": final, "effective_status": EXT.effective_from_final(final),
            "review_id": saved["review_id"],
            "intake_class": rec["intake_class"], "run_status": result.get("status"),
            "reason": result.get("reason"), "coverage": result.get("coverage"),
            "provider_verification": result.get("provider_verification"),
            "observation_id": result.get("observation_id"),
            "pipeline_excluded": rec.get("pipeline_excluded")}


def do_analyse(intake_id):
    """READ-ONLY OCR assist: run RapidOCR (under .venv-vision) on the immutable image and return
    PROPOSALS only. Creates no review/observation/cohort/alert. Provider is never auto-verified."""
    import subprocess
    try:
        _manifest, orig = image_confirm.load_and_verify_intake(intake_id)   # verifies hash, immutable path
    except Exception as e:                           # noqa: BLE001
        return {"error": "INTAKE_NOT_FOUND", "detail": type(e).__name__}
    if not os.path.exists(VENV_VISION_PY):
        return {"error": "OCR_ENV_MISSING", "detail": ".venv-vision not available"}
    try:
        r = subprocess.run([VENV_VISION_PY, OCR_RUNNER, orig], capture_output=True, text=True, timeout=180)
    except Exception as e:                           # noqa: BLE001
        return {"error": "OCR_RUN_FAILED", "detail": type(e).__name__}
    out = (r.stdout or "").strip().splitlines()
    if r.returncode != 0 or not out:
        return {"error": "OCR_FAILED", "detail": (r.stderr or "")[-200:]}
    try:
        return json.loads(out[-1])
    except Exception:
        return {"error": "OCR_BAD_OUTPUT"}


SNIP_WATCHER = os.path.join(_HERE, "clipboard_snip_watch.py")
SNIP_STATUS_FILE = os.path.join(_ROOT, "data", "snip_watch_status.json")
_snip_proc = [None]                          # boxed so nested funcs can rebind


def do_repair_action(path, payload):
    """Append-only adjudication actions. Each is an EXPLICIT Martyn decision from the console; never
    auto-invoked. Writes only *_CONFIRMED / *_REJECTED / *_EDITED / decision events."""
    import history_repair as HR
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    who = payload.get("reviewer") or "martyn"
    iid = payload.get("intake_id"); cid = payload.get("child_id"); pid = payload.get("parent_signal_id")
    action = path.rsplit("/api/repair_", 1)[-1]
    try:
        if action == "confirm_correction":
            return HR.confirm_signal_correction(iid, who, now, fields=payload.get("fields"))
        if action == "reject_correction":
            return HR.reject_signal_correction(iid, who, now)
        if action == "edit_correction":
            return HR.edit_signal_correction(iid, payload.get("fields") or {}, who, now)
        if action == "confirm_link":
            return HR.confirm_parent_link(cid, pid, who, now)
        if action == "reject_link":
            return HR.reject_parent_link(cid, pid, who, now)
        if action == "confirm_classification":
            return HR.confirm_classification_correction(iid, payload.get("to_class"), who, now)
        if action == "reject_classification":
            return HR.reject_classification_correction(iid, who, now)
        if action == "role_decision":
            return HR.role_conflict_decision(iid, payload.get("role"), who, now)
        if action == "leave_unlinked":
            return HR.leave_unlinked(cid, who, now)
        if action == "classify_unrelated":
            return HR.classify_unrelated_replay(cid, who, now)
    except AssertionError as e:
        return {"error": "INVALID_DECISION", "detail": str(e)}
    return {"error": "UNKNOWN_ACTION", "action": action}


def _alerts_mod():
    import sys as _sys
    _sys.path.insert(0, os.path.join(_ROOT, "campaign_extractor", "demo_executor"))
    import operator_alerts as OA
    return OA


def _advisory_mod():
    import sys as _sys
    _sys.path.insert(0, os.path.join(_ROOT, "campaign_extractor", "demo_executor"))
    import advisory_bridge as AB
    return AB


def do_advisory(since):
    """Read-only advisory handoff: run the bridge (interpretation jobs for genuinely-new intake) and
    return advisory results newer than `since`. Never affects parsing/evidence/safety; no broker action."""
    AB = _advisory_mod()
    now_ms = int(time.time() * 1000)
    try:
        AB.process(now_ms)                               # drives interpretation jobs + alerts
    except Exception as e:                               # noqa: BLE001 — advisory failure must not affect anything
        return {**AB.status(), "results": [], "error": type(e).__name__}
    return {**AB.status(), "results": AB.get_results(since)}


def do_advisory_status():
    return _advisory_mod().status()


def do_advisory_enable():
    return _advisory_mod().enable(int(time.time() * 1000))


def do_alerts(since):
    """Advisory: return alerts (produced by the advisory bridge) newer than `since`. Read-only over the
    append-only alert log. When OFF, returns no notifications (log still records)."""
    OA = _alerts_mod()
    now_ms = int(time.time() * 1000)
    st = OA.load_state()
    try:
        _advisory_mod().process(now_ms)                  # bridge appends any new alerts (idempotent)
    except Exception as e:                               # noqa: BLE001 — alert failure must not affect anything
        return {"enabled": st.get("enabled", True), "alerts": [], "error": type(e).__name__}
    alerts = []
    if st.get("enabled", True) and os.path.exists(OA.ALERT_LOG):
        for l in open(OA.ALERT_LOG, encoding="utf-8"):
            if not l.strip():
                continue
            try:
                a = json.loads(l)
            except Exception:
                continue
            if a.get("seq", 0) > since:
                alerts.append(a)
    return {"enabled": st.get("enabled", True), "alerts": alerts[-50:]}


def do_alerts_status():
    OA = _alerts_mod()
    st = OA.load_state()
    return {"enabled": st.get("enabled", True), "seq": st.get("seq", 0)}


def do_alerts_toggle(payload):
    return _alerts_mod().set_enabled(bool(payload.get("on")))


def do_alerts_test():
    OA = _alerts_mod()
    return OA.test_alert(int(time.time() * 1000))


def do_interpret(payload):
    """Advisory Farouk interpretation of pasted signal text against the live quote health (read-only).
    Constructs no proposal and no broker action; fail-closed."""
    import sys as _sys
    _sys.path.insert(0, os.path.join(_ROOT, "campaign_extractor", "demo_executor"))
    import farouk_contract as FC
    qh = do_quote_health()
    now_ms = int(time.time() * 1000)
    quote = None
    if qh.get("bid") is not None and qh.get("ask") is not None:
        quote = type("Q", (), {"bid": qh["bid"], "ask": qh["ask"],
                               "ts_ms": qh.get("last_event_timestamp_ms") or now_ms})()
    return FC.interpret(raw_text=payload.get("raw_text", ""), ocr_text=payload.get("ocr_text"),
                        provider_ts_ms=payload.get("provider_ts_ms"), now_ms=now_ms, quote=quote,
                        quote_path=payload.get("quote_path"),
                        quote_health_state=qh.get("state", "QUOTES_ERROR"),
                        matched_position=payload.get("matched_position"))


def do_strike_trap():
    """SHADOW-ONLY Qualified Strike & Trap comparison over a demonstration inside-zone SELL path against
    the live quote health. No broker execution; no atomic execution claim."""
    import sys as _sys
    _sys.path.insert(0, os.path.join(_ROOT, "campaign_extractor", "shadow_campaign"))
    _sys.path.insert(0, os.path.join(_ROOT, "campaign_extractor", "demo_executor"))
    import compare as CMP
    import advisory_bridge as AB
    now = int(time.time() * 1000)
    prov = now - 60_000
    # consume the SAME live quote store as the advisory bridge / quote-health panel (read-only)
    lq, qstate, lpath = AB._live_quote_ctx(now)
    if lq is not None:
        quote = {"bid": lq.bid, "ask": lq.ask, "ts_ms": getattr(lq, "ts_ms", now)}
        path = [{"bid": p["bid"], "ask": p["ask"], "ts_ms": p["ts_ms"]} for p in (lpath or [])[:400]]
        low, high = round(lq.bid - 3, 2), round(lq.bid + 7, 2)   # demo zone straddling the live price
        stop, store_source = round(lq.bid + 12, 2), "LIVE ctrader_quotes_v1.db"
    else:
        quote = {"bid": 4123.0, "ask": 4123.2, "ts_ms": now - 2_000}
        path = [{"bid": 4118, "ask": 4118.2, "ts_ms": now - 50_000},
                {"bid": 4121, "ask": 4121.2, "ts_ms": now - 30_000},
                {"bid": 4123, "ask": 4123.2, "ts_ms": now - 5_000}]
        low, high, stop, qstate, store_source = 4120, 4130, 4135, "QUOTES_ACTIVE", "fallback demo"
    try:
        c = CMP.compare_models(direction="SELL", low=low, high=high, quote=quote, quote_path=path,
                               provider_ts_ms=prov, now_ms=now, quote_health_state=qstate,
                               provider_stop=stop, balance=10000)
        c["quote_store_source"], c["live_bid"], c["live_ask"] = store_source, quote["bid"], quote["ask"]
        import risk_policy as RP
        c["risk_policy"] = RP.policy_record(basis_amount=10000, currency="GBP",
                                            allocation_model="QUALIFIED_STRIKE_TRAP_60_25_15",
                                            snapshot_ts_utc=None, now_ms=now)
        c["within_cap"] = RP.within_cap(basis_amount=10000,
                                        tranche_risks=RP.tranche_budgets(10000))["within_cap"]
    except Exception as e:                               # noqa: BLE001
        return {"error": type(e).__name__}
    c["SHADOW_ONLY"] = True
    c["NO_BROKER_EXECUTION"] = True
    c["NO_ATOMIC_EXECUTION_CLAIM"] = True
    return c


def do_quote_health():
    """Read-only XAUUSD quote-health from the append-only quote store (same latest quote the recorder
    wrote). A stored quote's age drives ACTIVE/SILENT/STALE — a connected socket is never assumed."""
    import calendar
    import sqlite3
    import sys as _sys
    _sys.path.insert(0, os.path.join(_ROOT, "campaign_extractor", "demo_executor"))
    import quote_health as QH
    db = os.path.join(_ROOT, "data", "ctrader_quotes_v1.db")
    now_ms = int(time.time() * 1000)
    try:
        c = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
        # carried-forward latest_bid/latest_ask so a one-sided spot tick never blanks the display
        row = c.execute("SELECT COALESCE(latest_bid, norm_bid), COALESCE(latest_ask, norm_ask), "
                        "persisted_utc FROM normalised_quotes WHERE latest_bid IS NOT NULL "
                        "OR norm_bid IS NOT NULL ORDER BY rowseq DESC LIMIT 1").fetchone()
        cnt = c.execute("SELECT COUNT(*) FROM normalised_quotes").fetchone()[0]
        sess = c.execute("SELECT connection_session_id, COUNT(*) FROM raw_spot_events "
                         "GROUP BY connection_session_id ORDER BY MAX(rowid) DESC LIMIT 1").fetchone()
        c.close()
    except Exception as e:                               # noqa: BLE001
        return {"state": "QUOTES_ERROR", "last_safe_error": type(e).__name__}
    if not row:
        return {"state": "QUOTES_SILENT", "events_this_session": 0}
    ev_ms = int(calendar.timegm(time.strptime(row[2], "%Y-%m-%dT%H:%M:%SZ"))) * 1000
    # broker schedule/holiday metadata is AUTHORITATIVE for MARKET_CLOSED vs STALE; if not captured,
    # do NOT assume closure from the calendar (report STALE). Any non-active state still blocks eligibility.
    import symbol_schedule as SS
    sched = hol = None
    sched_path = os.path.join(_ROOT, "data", "xauusd_broker_schedule.json")
    schedule_source = "NONE_CAPTURED"
    if os.path.exists(sched_path):
        try:
            _sc = json.load(open(sched_path, encoding="utf-8"))
            sched, hol = _sc.get("schedule"), _sc.get("holidays")
            schedule_source = _sc.get("source", "BROKER")
        except Exception:
            pass
    market_closed, sched_state, sched_reason = SS.market_closed_flag(now_ms=now_ms, schedule=sched, holidays=hol)
    h = QH.health(latest_bid=row[0], latest_ask=row[1], latest_event_ms=ev_ms, now_ms=now_ms,
                  phase="subscribed", connected=True, subscribed=True, market_closed=market_closed,
                  events_this_session=(sess[1] if sess else 0),
                  session_id=(sess[0] if sess else None), coverage_end_ms=ev_ms)
    h["latest_quote_utc"] = row[2]
    h["quote_source"] = "demo.ctraderapi.com:5035"
    h["total_stored_quotes"] = cnt
    h["schedule_state"] = sched_state                    # MARKET_OPEN/MARKET_CLOSED/SCHEDULE_UNKNOWN
    h["schedule_reason"] = sched_reason
    h["schedule_source"] = schedule_source
    h["eligibility_blocked"] = (h["state"] != "QUOTES_ACTIVE")   # any non-active state blocks campaigns
    return h


def do_intake_ocr(intake_id):
    """On-demand raw OCR text for a review card (read-only). Reuses the OCR runner."""
    try:
        _m, orig = image_confirm.load_and_verify_intake(intake_id)
    except Exception as e:                               # noqa: BLE001
        return {"error": "INTAKE_NOT_FOUND", "detail": type(e).__name__}
    if not os.path.exists(VENV_VISION_PY):
        return {"error": "OCR_ENV_MISSING"}
    import subprocess
    try:
        r = subprocess.run([VENV_VISION_PY, OCR_RUNNER, orig], capture_output=True, text=True, timeout=180)
        res = json.loads((r.stdout or "").strip().splitlines()[-1])
        return {"intake_id": intake_id, "full_text": res.get("full_text", "")}
    except Exception as e:                               # noqa: BLE001
        return {"error": "OCR_FAILED", "detail": type(e).__name__}


def do_intake_image(intake_id):
    """Return the immutable original image as a base64 data URL so the browser can display a
    watcher-imported snip in the open form. Read-only; verifies the hash."""
    try:
        _manifest, orig = image_confirm.load_and_verify_intake(intake_id)
    except Exception as e:                           # noqa: BLE001
        return {"error": "INTAKE_NOT_FOUND", "detail": type(e).__name__}
    with open(orig, "rb") as f:
        b = f.read()
    ext = os.path.splitext(orig)[1].lower().lstrip(".") or "png"
    mime = "jpeg" if ext in ("jpg", "jpeg") else ext
    return {"intake_id": intake_id, "data": f"data:image/{mime};base64," + base64.b64encode(b).decode()}


def do_snip_status():
    st = {"status": "OFF", "pid": None, "last_snip_received": None, "last_intake_id": None,
          "last_proposed_class": None, "last_error": None}
    if os.path.exists(SNIP_STATUS_FILE):
        try:
            st.update(json.load(open(SNIP_STATUS_FILE, encoding="utf-8")))
        except Exception:
            pass
    p = _snip_proc[0]
    if p is not None and p.poll() is not None and st.get("status") in ("ON", "STARTING"):
        st["status"] = "OFF"                 # process died
    return st


def do_snip_start():
    import subprocess
    if _snip_proc[0] is not None and _snip_proc[0].poll() is None:
        return {"status": "ON", "pid": _snip_proc[0].pid, "already_running": True}
    if not os.path.exists(VENV_VISION_PY):
        json.dump({"status": "ERROR", "pid": None, "last_error": "OCR_ENV_MISSING"},
                  open(SNIP_STATUS_FILE, "w"))
        return {"status": "ERROR", "error": "OCR_ENV_MISSING"}
    json.dump({"status": "STARTING", "pid": None, "last_error": None}, open(SNIP_STATUS_FILE, "w"))
    _snip_proc[0] = subprocess.Popen([VENV_VISION_PY, SNIP_WATCHER, "--console",
                                      f"http://{HOST}:{PORT}", "--status-file", SNIP_STATUS_FILE])
    return {"status": "STARTING", "pid": _snip_proc[0].pid}


def do_snip_stop():
    import subprocess
    p = _snip_proc[0]
    if p is not None and p.poll() is None:
        # kill the whole tree (the venv python may re-exec into a child)
        try:
            subprocess.run(["taskkill", "/PID", str(p.pid), "/T", "/F"],
                           capture_output=True, timeout=8)
        except Exception:
            try:
                p.terminate(); p.wait(timeout=5)
            except Exception:
                p.kill()
    _snip_proc[0] = None
    json.dump({"status": "OFF", "pid": None, "last_error": None}, open(SNIP_STATUS_FILE, "w"))
    return {"status": "OFF"}


def do_cohort():
    """READ-ONLY: reuse the tested monitor; return headline + counts only. No logic duplicated."""
    rep = COHORT.assess(COHORT.load_bundles())
    return {"headline": rep["headline"], "complete": rep["complete"], "target": rep["target"],
            "counts": rep["counts"]}


_CLASS_TO_STATUS = {"TRADE_RESULT": "TRADE_RESULT_EXCLUDED", "TRADE_UPDATE": "TRADE_UPDATE_EXCLUDED",
                    "SIGNAL": "SIGNAL_RECORDED", "SIGNAL_ANNOUNCEMENT": "SIGNAL_RECORDED"}


def do_history(root=None, limit=15):
    mdir = os.path.join(image_intake.ensure_structure(root), "manifests")
    _rev_map = EXT.reviews_by_intake()
    try:
        import history_repair as HR
        reclass = HR.confirmed_classifications()          # confirmed SIGNAL->TRADE_RESULT etc.
    except Exception:
        reclass = {}
    items = []
    if os.path.isdir(mdir):
        files = sorted(os.listdir(mdir), key=lambda n: os.path.getmtime(os.path.join(mdir, n)), reverse=True)
        for fn in files[:limit]:
            try:
                m = json.load(open(os.path.join(mdir, fn), encoding="utf-8"))
                iid = m["intake_id"]
                eff = EXT.resolve_effective(iid, _rev_map.get(iid))   # status event or review class
                rev = _rev_map.get(iid) or {}
                orig_class = rev.get("intake_class") or rev.get("semantic_class")
                item = {"intake_id": iid, "imported_at": m.get("screenshot_imported_at"),
                        "effective_status": eff or m.get("intake_status"),
                        "manifest_status": m.get("intake_status"),   # ORIGINAL IMPORT STATUS (audit)
                        "original_confirmed_review_class": orig_class,
                        "effective_class": orig_class, "duplicate": m.get("duplicate")}
                if iid in reclass:                        # apply confirmed classification correction
                    item["effective_class"] = reclass[iid]
                    item["effective_status"] = _CLASS_TO_STATUS.get(reclass[iid], item["effective_status"])
                    item["provenance"] = "REPLAY_VALIDATION_ONLY"
                items.append(item)
            except Exception:
                pass
    return {"recent": items}


def _recorded_signals():
    """Recorded SIGNAL observations (for parent suggestion) sourced read-only from cohort bundles."""
    out = []
    statuses = EXT.all_latest_statuses()
    for b in COHORT.load_bundles():
        rv, m = (b.get("review") or {}), (b.get("manifest") or {})
        if rv.get("intake_class") != "SIGNAL":
            continue
        if statuses.get(b.get("intake_id")) not in ("SIGNAL_RECORDED", "NO_COVERAGE"):
            continue
        br = b.get("bridge_obs") or {}
        f = rv.get("fields") or {}
        out.append({"observation_id": br.get("paper_observation_id") or b.get("intake_id"),
                    "provider": (rv.get("provider") or {}).get("value"),
                    "instrument": (f.get("instrument") or {}).get("value"),
                    "direction": (f.get("direction") or {}).get("value"),
                    "time": rv.get("review_created_at_utc") or m.get("screenshot_imported_at")})
    return out


def do_suggest_parent(payload):
    return EXT.suggest_parent({"provider": payload.get("provider"), "instrument": payload.get("instrument"),
                               "direction": payload.get("direction"),
                               "post_time": payload.get("post_time")}, _recorded_signals())


def do_link(payload):
    if not payload.get("approve"):
        return {"linked": False, "reason": "NOT_APPROVED"}   # no automatic linking without human OK
    return EXT.record_link(payload.get("parent_observation_id"), payload.get("intake_id"),
                           payload.get("kind") or "UPDATE", detail=payload.get("detail"))


def do_queue():
    cohort = do_cohort()
    q = EXT.queue_summary(bundles=COHORT.load_bundles(),
                          cohort={"complete": cohort["complete"], "target": cohort["target"]})
    # reconcile from the SINGLE effective source of truth (same as the lifecycle panel + history)
    try:
        ec = LIFECYCLE.effective_counts()
        q["unlinked_updates_results"] = len(ec["unlinked_updates_results"])
        q["unrelated_replay_children"] = len(ec["unrelated_replay_children"])
        q["parent_link_coverage"] = ec["parent_link_coverage"]
        # pending review = imported intakes with no effective review class (same rows the history shows
        # as IMPORTED_PENDING_REVIEW) — so the headline and the history agree
        hist = do_history(limit=500).get("recent", [])
        q["pending_review"] = sum(1 for r in hist if r.get("effective_status") == "IMPORTED_PENDING_REVIEW")
    except Exception:
        pass
    return q


def do_demo_preview(payload):
    """DRY-RUN demo order preview for a CONFIRMED XAUUSD SIGNAL intake. Sends nothing."""
    review = EXT.reviews_by_intake().get(payload.get("intake_id"))
    if not review:
        return {"error": "NO_CONFIRMED_REVIEW"}
    if review.get("intake_class") != "SIGNAL":
        return {"error": "NOT_A_SIGNAL", "detail": review.get("intake_class")}
    if review.get("explicit_confirmation_state") != "CONFIRMED":
        return {"error": "NOT_HUMAN_CONFIRMED"}
    return DEMO.build_preview(review, risk_pct=payload.get("risk_pct"),
                              manual_entry=payload.get("manual_entry"))


def do_demo_arm(payload):
    return DEMO.arm(payload.get("proposal_id"))


def do_demo_approve(payload):
    return DEMO.approve(payload.get("proposal_id"))     # ends DRY_RUN_APPROVED / NO_ORDER_SENT


def do_update_preview(payload):
    """DRY-RUN TRADE_UPDATE management preview for a confirmed TRADE_UPDATE intake. Sends nothing."""
    review = EXT.reviews_by_intake().get(payload.get("intake_id"))
    if not review:
        return {"error": "NO_CONFIRMED_REVIEW"}
    if review.get("intake_class") not in ("TRADE_UPDATE", "TRADE_RESULT"):
        return {"error": "NOT_A_TRADE_UPDATE", "detail": review.get("intake_class")}
    return DEMO.build_update_preview(review, payload)


def do_update_arm(payload):
    return DEMO.arm_update(payload.get("plan_id"))


def do_update_approve(payload):
    return DEMO.approve_update(payload.get("plan_id"))  # ends UPDATE_PLAN_DRY_RUN_APPROVED / NO_BROKER_ACTION_SENT


# ---------------------------------------------------------------- HTTP plumbing
class Handler(BaseHTTPRequestHandler):
    def _send(self, code, body, ctype="application/json"):
        data = body if isinstance(body, bytes) else json.dumps(body, default=str).encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *a):
        pass                                        # quiet

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            html = open(os.path.join(_HERE, "index.html"), "rb").read()
            return self._send(200, html, "text/html; charset=utf-8")
        if self.path.startswith("/api/history"):
            return self._send(200, do_history())
        if self.path.startswith("/api/cohort"):
            return self._send(200, do_cohort())
        if self.path.startswith("/api/queue"):
            return self._send(200, do_queue())
        if self.path.startswith("/api/submission_readiness"):
            return self._send(200, DEMO.submission_readiness())
        if self.path.startswith("/api/repair_queue"):
            try:
                import history_repair as HR
                return self._send(200, {"roles": HR.reconcile_roles(), "proposals": HR.load_events(),
                                        "confirmed_links": HR.confirmed_links(),
                                        "unlinked_children": LIFECYCLE.unlinked_children_with_candidates()})
            except Exception as e:                       # noqa: BLE001
                return self._send(200, {"error": type(e).__name__})
        if self.path.startswith("/api/timelines"):
            try:
                return self._send(200, {"timelines": LIFECYCLE.build_timelines(),
                                        "inspection": LIFECYCLE.inspect()})
            except Exception as e:                       # noqa: BLE001
                return self._send(200, {"error": type(e).__name__})
        if self.path.startswith("/api/strike_trap"):
            return self._send(200, do_strike_trap())
        if self.path.startswith("/api/quote_health"):
            return self._send(200, do_quote_health())
        if self.path.startswith("/api/advisory_status"):
            return self._send(200, do_advisory_status())
        if self.path.startswith("/api/advisory"):
            from urllib.parse import urlparse, parse_qs
            q = parse_qs(urlparse(self.path).query)
            return self._send(200, do_advisory(int((q.get("since") or ["0"])[0])))
        if self.path.startswith("/api/alerts_status"):
            return self._send(200, do_alerts_status())
        if self.path.startswith("/api/alerts"):
            from urllib.parse import urlparse, parse_qs
            q = parse_qs(urlparse(self.path).query)
            return self._send(200, do_alerts(int((q.get("since") or ["0"])[0])))
        if self.path.startswith("/api/management_readiness"):
            return self._send(200, DEMO.management_readiness())
        if self.path.startswith("/api/snip_status"):
            return self._send(200, do_snip_status())
        if self.path.startswith("/api/intake_image"):
            from urllib.parse import urlparse, parse_qs
            q = parse_qs(urlparse(self.path).query)
            return self._send(200, do_intake_image((q.get("intake_id") or [""])[0]))
        if self.path.startswith("/api/intake_ocr"):
            from urllib.parse import urlparse, parse_qs
            q = parse_qs(urlparse(self.path).query)
            return self._send(200, do_intake_ocr((q.get("intake_id") or [""])[0]))
        return self._send(404, {"error": "not found"})

    def do_POST(self):
        n = int(self.headers.get("Content-Length", 0))
        try:
            payload = json.loads(self.rfile.read(n) or b"{}")
        except Exception:
            return self._send(400, {"error": "bad json"})
        try:
            if self.path == "/api/upload":
                return self._send(200, do_upload(payload.get("filename"), payload.get("data", ""),
                                                 source=payload.get("source")))
            if self.path == "/api/snip_start":
                return self._send(200, do_snip_start())
            if self.path == "/api/snip_stop":
                return self._send(200, do_snip_stop())
            if self.path.startswith("/api/repair_"):
                return self._send(200, do_repair_action(self.path, payload))
            if self.path == "/api/interpret":
                return self._send(200, do_interpret(payload))
            if self.path == "/api/alerts_toggle":
                return self._send(200, do_alerts_toggle(payload))
            if self.path == "/api/alerts_test":
                return self._send(200, do_alerts_test())
            if self.path == "/api/advisory_enable":
                return self._send(200, do_advisory_enable())
            if self.path == "/api/analyse":
                return self._send(200, do_analyse(payload.get("intake_id")))
            if self.path == "/api/observe":
                return self._send(200, do_observe(payload))
            if self.path == "/api/suggest_parent":
                return self._send(200, do_suggest_parent(payload))
            if self.path == "/api/link":
                return self._send(200, do_link(payload))
            if self.path == "/api/demo_preview":
                return self._send(200, do_demo_preview(payload))
            if self.path == "/api/demo_arm":
                return self._send(200, do_demo_arm(payload))
            if self.path == "/api/demo_approve":
                return self._send(200, do_demo_approve(payload))
            if self.path == "/api/update_preview":
                return self._send(200, do_update_preview(payload))
            if self.path == "/api/update_arm":
                return self._send(200, do_update_arm(payload))
            if self.path == "/api/update_approve":
                return self._send(200, do_update_approve(payload))
        except Exception as e:                       # never leak a stack to the browser
            return self._send(500, {"error": type(e).__name__, "detail": str(e)[:200]})
        return self._send(404, {"error": "not found"})


def _advisory_background_loop():
    """Run the read-only advisory bridge server-side, independent of any open browser, so interpretation
    continues and results/alerts are waiting when the console is reopened. Advisory only — no broker
    action. Any error is swallowed so it can never affect the server or safety."""
    import threading
    def _loop():
        while True:
            try:
                _advisory_mod().process(int(time.time() * 1000))
            except Exception:
                pass
            time.sleep(5)
    t = threading.Thread(target=_loop, daemon=True)
    t.start()
    return t


def main():
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"Manual Signal Intake Console -> http://{HOST}:{PORT}  (Ctrl+C to stop)")
    print("PAPER ONLY / NOT A FILL / NOT AN OUTCOME. Execution locks remain false.")
    _advisory_background_loop()          # advisory interpretation continues even with no browser open
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nconsole stopped")
    return 0


if __name__ == "__main__":
    sys.exit(main())
