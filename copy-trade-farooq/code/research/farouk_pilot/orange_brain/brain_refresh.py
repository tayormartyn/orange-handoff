"""ORANGE BRAIN — deterministic state refresh (v0.1).

READS live health files, cursors, ledgers, campaign artifacts, registers.
WRITES ONLY inside orange_brain/: project_state_v0_1.json, operator_brief.md,
operator_brief.json. Never touches trading/campaign/freeze ledgers, cursors,
alerts, config or code. No LLM, no network. Run manually or via
ORANGE_BRAIN_REFRESH.ps1 / ORANGE_STATUS.ps1 (--status = print only, no writes).

Determinism: state_core depends only on durable file contents; volatile
(PIDs, timestamps, market lag) is kept in a separate section.
"""
import hashlib
import json
import os
import re
import sqlite3
import subprocess
import sys
from datetime import datetime, timezone, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
ST = r"C:\Users\Marty\signal-terminal"
FP = os.path.join(ST, r"research\farouk_pilot\always_on_tradingview_receiver_plan\stage_c_tooling\farouk_plus")
FA = os.path.join(FP, "follower_assistant")

EXPECTED = [
    ("listener", "module_a_telegram.py"),
    ("tracker", "tracker.py"),
    ("wire", "live_wire.py"),
    ("watcher", "evidence_watcher.py"),
    ("companion", "outcome_companion.py"),
    ("shadow", "live_shadow_simulator.py"),
    ("observer", "intake_observer.py"),
]

GATE_PATTERNS = {
    "MODE": (os.path.join(ST, "config.py"), r'^MODE\s*=\s*"([^"]+)"'),
    "LISTENER_MODE": (os.path.join(ST, "config.py"), r'^LISTENER_MODE\s*=\s*"([^"]+)"'),
    "EXECUTION_ENABLED": (os.path.join(ST, "config.py"), r'^EXECUTION_ENABLED\s*=\s*(\w+)'),
    "CTRADER_EXECUTION_ENABLED": (os.path.join(ST, "ctrader_config.py"), r'^CTRADER_EXECUTION_ENABLED\s*=\s*(\w+)'),
}


def sha16(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()[:16]


def count_lines(path):
    with open(path, "rb") as f:
        return sum(1 for _ in f)


def guarded_write(relname, content):
    p = os.path.abspath(os.path.join(HERE, relname))
    assert p.startswith(os.path.abspath(HERE)), f"write outside orange_brain refused: {p}"
    with open(p, "w", encoding="utf-8") as f:
        f.write(content)


def get_processes():
    try:
        out = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "Get-CimInstance Win32_Process -Filter \"Name like 'python%'\" | "
             "Select-Object ProcessId,CommandLine | ConvertTo-Json -Compress"],
            capture_output=True, text=True, timeout=30).stdout.strip()
        rows = json.loads(out) if out else []
        if isinstance(rows, dict):
            rows = [rows]
    except Exception:
        rows = []
    procs = []
    for name, marker in EXPECTED:
        match = [r for r in rows if r.get("CommandLine") and marker in r["CommandLine"]]
        procs.append({"service": name, "running": len(match) == 1,
                      "duplicates": max(0, len(match) - 1),
                      "pid": match[0]["ProcessId"] if len(match) == 1 else
                             [m["ProcessId"] for m in match] if match else None})
    return procs


def get_gates():
    gates = {}
    for key, (path, pat) in GATE_PATTERNS.items():
        val = "UNREADABLE"
        try:
            for line in open(path, encoding="utf-8", errors="replace"):
                m = re.match(pat, line)
                if m:
                    val = m.group(1)
                    break
        except OSError:
            pass
        gates[key] = val
    gates_ok = (gates.get("MODE") == "PAPER" and gates.get("LISTENER_MODE") == "PREVIEW"
                and gates.get("EXECUTION_ENABLED") == "False"
                and gates.get("CTRADER_EXECUTION_ENABLED") == "False")
    return gates, gates_ok


def tail_line(path):
    with open(path, "rb") as f:
        f.seek(0, 2)
        size = f.tell()
        f.seek(max(0, size - 4096))
        chunk = f.read().decode("utf-8", errors="replace").strip().splitlines()
        return chunk[-1] if chunk else ""


def collect():
    freeze_path = os.path.join(FA, r"evidence_layer\router_freeze_v0_1.jsonl")
    fwd_path = os.path.join(FP, "forward_validation_ledger_v0_2.jsonl")
    quar_path = os.path.join(FA, r"intake_reliability\intake_quarantine_v0_1.jsonl")

    freeze_rows = [json.loads(l) for l in open(freeze_path, encoding="utf-8") if l.strip()]
    genuine = [r["setup_id"] for r in freeze_rows]

    # D-080: SINGLE authoritative source for campaign status + expectancy eligibility.
    # Both generators read this; neither hardcodes counts/ids. Reconciled with the freeze
    # ledger at render time (a mismatch fails loudly in brief()).
    cstat = json.load(open(os.path.join(HERE, "campaign_status_v0_1.json"), encoding="utf-8"))
    cmap = cstat["campaigns"]
    capture_ids = sorted([c for c, v in cmap.items() if v.get("class") == "genuine_prospective"])
    expectancy_ids = sorted([c for c, v in cmap.items()
                             if v.get("class") == "genuine_prospective" and v.get("expectancy_eligible")])
    excluded = {c: v.get("exclusion_reason", "?") for c, v in cmap.items()
                if v.get("class") == "genuine_prospective" and not v.get("expectancy_eligible")}
    latest_campaign = max(capture_ids, key=lambda c: cmap[c]["date"]) if capture_ids else None
    campaign_status = {
        "capture_ids": capture_ids, "capture_count": len(capture_ids),
        "expectancy_ids": expectancy_ids, "expectancy_count": len(expectancy_ids),
        "excluded": excluded,
        "latest_campaign": latest_campaign,
        "latest_date": cmap[latest_campaign]["date"] if latest_campaign else None,
        "reconciled_with_freeze": set(genuine) <= set(capture_ids),
        "reconcile_mismatch": sorted(set(genuine) ^ set(capture_ids)),
        "non_prospective_note": cstat.get("non_prospective_note", ""),
    }

    # Fixes 5/6/7: 'latest learned / decisions / corrections' derived from the registers BY
    # RECENCY (ids are zero-padded, so lexical sort == chronological), never frozen literals.
    def _recent(fname, idkey, n=3):
        rows = [json.loads(l) for l in open(os.path.join(HERE, fname), encoding="utf-8") if l.strip()]
        rows.sort(key=lambda r: r.get(idkey, ""))
        return rows[-n:][::-1]
    recent_claims = [{"id": c["claim_id"], "text": c.get("precise_statement", "")[:88]}
                     for c in _recent("knowledge_claims_v0_1.jsonl", "claim_id")]
    recent_decisions = [{"id": d["decision_id"], "text": d.get("decision", "")[:80]}
                        for d in _recent("decision_log_v0_1.jsonl", "decision_id")]
    recent_corrections = [{"id": r.get("rej_id", "?"), "text": (r.get("reason") or r.get("statement") or "")[:80]}
                          for r in _recent("rejected_and_superseded_v0_1.jsonl", "rej_id")]

    fwd_lines = [l for l in open(fwd_path, encoding="utf-8") if l.strip()]
    setups = sorted({json.loads(l).get("setup_id") for l in fwd_lines
                     if json.loads(l).get("setup_id")})

    fwd_msg_ids = set()
    for l in fwd_lines:
        o = json.loads(l)
        for m in (o.get("message_ids") or []):
            fwd_msg_ids.add(int(m))
        if o.get("message_id"):
            fwd_msg_ids.add(int(o["message_id"]))

    # Actionable = modern-era quarantines (>=45784, intake-lane maturity) whose message
    # never became a ledger campaign/management event, minus operator resolutions from
    # quarantine_review.py (OQ-8 durable format; DEFER stays pending; a resolution binds
    # to the exact raw_text_hash so changed content re-enters the queue).
    sys.path.insert(0, HERE)
    import quarantine_review as _qr
    _rows, _res = _qr.pending_actionable()
    pending = [int(o["message_id"]) for o in _rows]
    resolved_count = len([r for r in _res.values() if r["verdict"] != "DEFER"])

    db = sqlite3.connect(os.path.join(ST, r"campaign_extractor\prospective\data\prospective_evidence_v1.db"))
    head, rows = db.execute(
        "select max(cast(telegram_message_id as integer)), count(*) from prospective_message_evidence").fetchone()
    db.close()

    wire_cur = json.load(open(os.path.join(FA, "live_wire_cursor.json")))
    watch_cur = json.load(open(os.path.join(FA, r"evidence_layer\evidence_watcher_cursor.json")))

    # staleness vs the hash table the registers were built from
    table = json.load(open(os.path.join(HERE, "_source_hash_table.json")))

    def content_sha16_excluding(path, excluded_key):
        """Tracker-owned live cards rewrite their market_data block every cycle during
        market hours; hashing the whole file makes staleness a weekday false alarm and
        trains the operator to ignore it. Hash canonical JSON minus the volatile block —
        genuine changes to campaign identity/legs/instructions/outcome still alarm."""
        obj = json.load(open(path, encoding="utf-8"))
        obj.pop(excluded_key, None)
        blob = json.dumps(obj, sort_keys=True, ensure_ascii=False).encode("utf-8")
        return hashlib.sha256(blob).hexdigest()[:16]

    drift = []
    for k, v in table.items():
        p = os.path.join(ST, v["path"]) if not os.path.isabs(v["path"]) else v["path"]
        if os.path.exists(p):
            cur = content_sha16_excluding(p, v["volatile_excluded"]) if v.get("volatile_excluded") else sha16(p)
            if cur != v["sha16"]:
                drift.append({"source": k, "path": v["path"],
                              "register_sha16": v["sha16"], "current_sha16": cur})
        else:
            drift.append({"source": k, "path": v["path"],
                          "register_sha16": v["sha16"], "current_sha16": "MISSING"})

    defects = json.load(open(os.path.join(HERE, "known_defects_v0_1.json")))
    actions = json.load(open(os.path.join(HERE, "next_actions_v0_1.json")))
    openq = json.load(open(os.path.join(HERE, "open_questions_v0_1.json")))
    rejected = [json.loads(l) for l in
                open(os.path.join(HERE, "rejected_and_superseded_v0_1.jsonl"), encoding="utf-8")
                if l.strip()]

    gates, gates_ok = get_gates()

    # last bar (volatile)
    try:
        last_bar = tail_line(os.path.join(FA, r"market_tracker\ingestion_log_v0_1.jsonl"))
        bar_ts = json.loads(last_bar).get("event_ts")
    except Exception:
        bar_ts = None

    state_core = {
        "gates": gates, "gates_ok": gates_ok,
        "ledgers": {
            "forward_ledger": {"lines": len(fwd_lines), "sha16": sha16(fwd_path)},
            "genuine_freeze": {"records": len(freeze_rows), "sha16": sha16(freeze_path),
                               "campaign_ids": genuine},
            "freeze_backfill_sha16": sha16(os.path.join(FA, r"evidence_layer\router_freeze_backfill_v0_1.jsonl")),
            "constitution_sha16": sha16(os.path.join(FA, "follower_constitution_v0_1.json")),
            "guards_sha16": sha16(os.path.join(FA, "guards.py")),
            "classifications": count_lines(os.path.join(FA, r"intake_reliability\intake_classification_v0_1.jsonl")),
            "quarantine": count_lines(quar_path),
            "alerts": count_lines(os.path.join(FA, r"intake_reliability\intake_alerts_v0_1.jsonl")),
        },
        "campaigns": {"all": setups, "count": len(setups),
                      "genuine_prospective": {"ids": genuine, "count": len(genuine)}},
        "campaign_status": campaign_status,
        "recent_claims": recent_claims,
        "recent_decisions": recent_decisions,
        "recent_corrections": recent_corrections,
        "cursors": {"wire_last_processed": wire_cur.get("last_processed_id"),
                    "watcher_after_msg_id": watch_cur.get("after_msg_id"),
                    "watcher_pending_entries": len(watch_cur.get("pending_entries", {})),
                    "evidence_db_head": head, "evidence_db_rows": rows},
        "quarantine_pending_review": {"count": len(pending), "message_ids": pending,
                                      "operator_resolved_count": resolved_count},
        "known_defects": {"open_code_defects": defects["open_code_defects"],
                          "risks": [r["name"] for r in defects["open_risks_and_limitations"]]},
        "open_questions": len(openq["questions"]),
        "contradiction_register": [r["rej_id"] for r in rejected],
        "register_staleness_drift": drift,
        "priority": actions["actions"][0]["objective"],
        "next_actions": [a["objective"] for a in actions["actions"]],
    }
    procs = get_processes()

    # ADD-2 (D-081): LISTENER HEARTBEAT BACKSTOP. Re-derived here from the OS + the heartbeat
    # file, trusting NO always-on process — so a dead intake_observer (which runs the continuous
    # monitor) cannot hide a dead listener. Absence (missing/stale heartbeat) is NEVER read as
    # healthy. This is the pull-based monitor-of-the-monitor the operator required.
    import time as _time
    if ST not in sys.path:
        sys.path.insert(0, ST)
    try:
        import listener_liveness as _ll
        hb = _ll.read_heartbeat()
        lpids = {p["pid"] for p in procs if p["service"] == "listener" and p["running"] and isinstance(p["pid"], int)}
        listener_running = any(p["service"] == "listener" and p["running"] for p in procs)
        observer_running = any(p["service"] == "observer" and p["running"] for p in procs)
        if not listener_running:
            listener_liveness = {"level": "ALARM", "code": "LISTENER_PROCESS_DOWN",
                                 "reason": "listener process is not running", "detail": {}}
        elif hb is None:
            # process confirmably UP but no heartbeat file: not an outage, but NOT healthy either
            # (monitor staged / not yet activated by a listener restart). Never 'healthy from silence'.
            listener_liveness = {"level": "WARN", "code": "HEARTBEAT_NOT_ACTIVE",
                                 "reason": "listener process UP but no heartbeat file — ADD-2 monitor "
                                           "staged; activate by restarting the listener", "detail": {}}
        else:
            listener_liveness = _ll.assess_listener(hb, _time.time(), lambda pid: pid in lpids)
        monitor_liveness = _ll.assess_monitor(observer_running)
        flag_present = os.path.exists(_ll.FLAG_PATH)
    except Exception as _lv_e:                                       # noqa: BLE001
        hb = None
        listener_liveness = {"level": "ALARM", "code": "LIVENESS_CHECK_FAILED", "reason": str(_lv_e), "detail": {}}
        monitor_liveness = {"level": "UNKNOWN", "code": "?", "reason": ""}
        flag_present = False

    volatile = {
        "refreshed_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "processes": procs,
        "last_bar_event_ts": bar_ts,
        "listener_liveness": listener_liveness,
        "monitor_liveness": monitor_liveness,
        "heartbeat": hb,
        "listener_down_flag_present": flag_present,
    }
    return state_core, volatile


class BriefConsistencyError(Exception):
    """A brief that contradicts itself, fails to reconcile, or presents a frozen literal as
    current state must FAIL LOUDLY rather than render (D-080, same fail-closed principle as
    every other guard)."""


# recency claims: a field asserting current/latest state. LITERAL/POLICY fields must not match.
_RECENCY_RE = re.compile(
    r"\b(latest|currently|as of|no new (?:trade|campaign) since|since\s+(?:F|XAU-F)\d)\b", re.I)


def consistency_guard(fields):
    """GENERAL guard (not a single hard-coded assertion). Catches the CLASS:
    (a) any two fields deriving the SAME underlying fact must agree;
    (b) any field claiming recency ('latest'/'since Fxx'/'current') must be DERIVED, never a
        frozen LITERAL. Raises BriefConsistencyError; the brief is never rendered on failure."""
    # (a) shared-fact agreement across every field that asserts a given fact key
    facts = {}
    for f in fields:
        for k, v in (f.get("asserts") or {}).items():
            facts.setdefault(k, []).append((f["id"], v))
    for k, pairs in facts.items():
        if len({v for _, v in pairs}) > 1:
            raise BriefConsistencyError(f"shared-fact disagreement on '{k}': {pairs}")
    # (b) recency-claiming field must be computed at render time (DERIVED), not literal
    for f in fields:
        if f.get("kind") != "DERIVED" and _RECENCY_RE.search(f.get("text") or ""):
            raise BriefConsistencyError(
                f"field '{f['id']}' is {f.get('kind')} but claims recency (must be DERIVED): "
                f"{(f.get('text') or '')[:90]!r}")
    return True


def render_liveness(lv, mv, flag_present):
    """ADD-1/ADD-2 rendering (pure, testable): a LOUD alarm banner + a one-line liveness summary.
    Absence/stale/disconnect and a down monitor all surface; nothing is read 'healthy' from silence."""
    hbd = lv.get("detail") or {}
    gap = (f" (last captured {hbd.get('last_msg_id')} @ {hbd.get('last_msg_ts')})"
           if hbd.get("last_msg_id") else "")
    alarms, warns = [], []
    if lv.get("level") == "ALARM":
        alarms.append(f"CAPTURE GAP — LISTENER {lv.get('code')}: {lv.get('reason')}{gap}. LIVE CAPTURE IS NOT VERIFIED.")
    elif lv.get("level") == "WARN":
        warns.append(f"listener heartbeat: {lv.get('reason')}")
    if mv.get("level") == "ALARM":
        alarms.append(f"MONITOR-OF-THE-MONITOR — {mv.get('reason')}")
    if flag_present:
        alarms.append("LISTENER_DOWN.flag is present (raised by the continuous monitor).")
    banner = ("".join(f"\n>> !! ALARM: {a}" for a in alarms)) if alarms else ""
    summary = (f" | listener-liveness: {lv.get('level')} ({lv.get('code')}), monitor: {mv.get('level')}"
               + "".join(f"  [!] {w}" for w in warns))
    return banner, summary


def brief(core, vol):
    procs = vol["processes"]
    up = sum(1 for p in procs if p["running"])
    dups = sum(p["duplicates"] for p in procs)
    down = [p["service"] for p in procs if not p["running"]]
    running = (f"{up}/7 services up" + ("" if dups == 0 else f" ({dups} DUPLICATES!)")
               + ("" if not down else f" — DOWN: {', '.join(down)}"))   # ADD-1: NAME the down service(s)

    # ADD-1 + ADD-2: raise a LOUD capture-gap / liveness banner (never a silent '6/7').
    alarm_banner, liveness_summary = render_liveness(
        vol.get("listener_liveness", {}) or {}, vol.get("monitor_liveness", {}) or {},
        vol.get("listener_down_flag_present", False))
    gp = core["campaigns"]["genuine_prospective"]
    prev = {}
    prev_path = os.path.join(HERE, "project_state_v0_1.json")
    if os.path.exists(prev_path):
        try:
            prev = json.load(open(prev_path)).get("state_core", {})
        except Exception:
            prev = {}
    changes = []
    if prev:
        pl = prev.get("ledgers", {})
        cl = core["ledgers"]
        for k in ("classifications", "quarantine", "alerts"):
            if pl.get(k) != cl.get(k):
                changes.append(f"{k}: {pl.get(k)} -> {cl.get(k)}")
        if prev.get("cursors", {}).get("evidence_db_head") != core["cursors"]["evidence_db_head"]:
            changes.append(f"telegram head: {prev.get('cursors', {}).get('evidence_db_head')} -> {core['cursors']['evidence_db_head']}")
        if prev.get("campaigns", {}).get("count") != core["campaigns"]["count"]:
            changes.append("CAMPAIGN COUNT CHANGED")
    if not changes:
        changes = ["no durable-state changes since previous refresh (quiet =/= nothing: capture ran and recorded zero new relevant events)"]

    # Fix 3: item 3 is DERIVED — the latest captured campaign comes from the authoritative
    # source, never a frozen literal; the delta is computed against the previous refresh.
    cs = core["campaign_status"]
    grew = bool(prev and prev.get("ledgers", {}).get("forward_ledger", {}).get("lines")
                != core["ledgers"]["forward_ledger"]["lines"])
    item3_text = (f"Latest captured campaign: {cs['latest_campaign']} ({cs['latest_date']}). "
                  + ("Forward ledger GREW since last refresh — check the tail for a new campaign."
                     if grew else
                     "No forward-ledger change since last refresh (a no-trade stretch is a captured fact, not 'nothing happened')."))
    # Fix 4: BOTH numbers with their meanings, from the authoritative source.
    item4_text = (f"{cs['capture_count']} genuine prospective captures ({', '.join(cs['capture_ids'])}); "
                  f"{cs['expectancy_count']} expectancy rows ({', '.join(cs['expectancy_ids'])}) — excluded: "
                  + ("; ".join(f"{k} [{v}]" for k, v in cs['excluded'].items()) or "none")
                  + f". {cs['non_prospective_note']}")
    # Fixes 5/6/7: derived from the registers by recency.
    item5_text = "; ".join(f"{c['id']}: {c['text']}" for c in core["recent_claims"]) or "no claims registered"
    item6_text = "; ".join(f"{d['id']}: {d['text']}" for d in core["recent_decisions"]) or "no decisions"
    item7_text = "; ".join(f"{c['id']}: {c['text']}" for c in core["recent_corrections"]) or "no corrections/supersessions"

    # RECONCILE + GENERAL CONSISTENCY GUARD (Addition 3) — fail loudly, never render on failure.
    if not cs["reconciled_with_freeze"]:
        raise BriefConsistencyError(
            f"campaign_status_v0_1.json not reconciled with the freeze ledger; mismatch: {cs['reconcile_mismatch']}")
    _fields = [
        {"id": "item3", "kind": "DERIVED", "text": item3_text,
         "asserts": {"latest_campaign": cs["latest_campaign"], "latest_date": cs["latest_date"]}},
        {"id": "item4", "kind": "DERIVED", "text": item4_text,
         "asserts": {"latest_campaign": cs["latest_campaign"], "capture_count": cs["capture_count"],
                     "expectancy_count": cs["expectancy_count"]}},
        {"id": "item5", "kind": "DERIVED", "text": item5_text, "asserts": {}},
        {"id": "item6", "kind": "DERIVED", "text": item6_text, "asserts": {}},
        {"id": "item7", "kind": "DERIVED", "text": item7_text, "asserts": {}},
    ]
    consistency_guard(_fields)

    drift = core["register_staleness_drift"]
    drift_txt = ("none — registers match sources" if not drift else
                 "; ".join(f"{d['source']} ({d['register_sha16']}->{d['current_sha16']})" for d in drift))

    # STANDING WEEKLY TASK (D-034): H-FPL-06 requires each week's pre-open plan captured.
    # Trading week key = ISO week of the Monday after the Sunday 22:00Z open.
    wk_state = {}
    wk_path = os.path.join(HERE, "weekly_plan_capture_state.json")
    if os.path.exists(wk_path):
        wk_state = json.load(open(wk_path)).get("weeks", {})
    now = datetime.fromisoformat(vol["refreshed_at_utc"].replace("Z", "+00:00"))
    ref = now - timedelta(hours=22)          # shift so Sun 22:00Z..Mon 00:00 counts as next week
    iso = (ref + timedelta(days=1)).isocalendar() if ref.weekday() == 6 else ref.isocalendar()
    wk_key = f"{iso[0]}-W{iso[1]:02d}"
    wk = wk_state.get(wk_key, {})
    if wk.get("captured"):
        weekly_plan_line = ""
        changes.append(f"weekly plan {wk_key}: captured ({wk.get('source_id', '?')[:40]})")
    else:
        weekly_plan_line = (f"(0!) CAPTURE THIS WEEK'S PRE-OPEN PLAN ({wk_key}) — not yet registered; "
                            f"without it every campaign this week is permanently NOT_SCORABLE for H-FPL-06 "
                            f"(record in weekly_plan_capture_state.json after corpus ingest); ")

    # D-041: result-card capture alarm — his actual fills exist ONLY on result-card images
    # (media, never read; OQ-10). A terminal campaign without a capture entry silently
    # under-records LANE_A_ENTRY_MODEL_ADVERSE_DIVERGENCE, so it gets weekly-plan alarm parity.
    rc_line = ""
    try:
        rc = json.load(open(os.path.join(HERE, "result_card_capture_state.json"),
                            encoding="utf-8")).get("campaigns", {})
        terminal_states = {"OUTCOME_FROZEN"}
        latest_state = {}                       # LATEST snapshot per campaign, not history
        for ln_ in open(os.path.join(FA, r"market_tracker\tracker_ledger_v0_1.jsonl"), encoding="utf-8"):
            r_ = json.loads(ln_)
            if r_.get("record_type") == "TRACKER_SNAPSHOT":
                latest_state[r_.get("setup_id")] = \
                    r_["snapshot"]["lanes"]["LANE_A"]["lifecycle"]["current"]
        missing = []
        for sid_, st_ in latest_state.items():
            ent = rc.get(sid_, {})
            if st_ in terminal_states and not ent.get("captured") and not ent.get("exempt"):
                missing.append(sid_)
        if missing:
            rc_line = (f"(0!) RESULT-CARD SCREENSHOTS MISSING for terminal campaign(s) "
                       f"{', '.join(sorted(set(missing)))} — his actual fills exist only there; "
                       f"the entry-divergence watch item is under-recording until captured "
                       f"(record in result_card_capture_state.json); ")
    except Exception as _rc_e:                                    # noqa: BLE001
        rc_line = f"(0!) result-card capture check FAILED ({type(_rc_e).__name__}) — inspect; "

    md = f"""# ORANGE OPERATOR BRIEF — {vol['refreshed_at_utc']}
(derived by brain_refresh.py; authority = ledgers/cards/constitution){alarm_banner}

1. **Is Orange running?** {running}. Gates {'OK (PAPER/PREVIEW/False/False)' if core['gates_ok'] else 'VIOLATION — CHECK NOW'}. Telegram head {core['cursors']['evidence_db_head']}, wire cursor {core['cursors']['wire_last_processed']}, watcher {core['cursors']['watcher_after_msg_id']} (pending {core['cursors']['watcher_pending_entries']}).{liveness_summary}
2. **Changed since last refresh:** {'; '.join(changes)}.
3. **New trade captured?** {item3_text}
4. **Prospective captures vs expectancy rows:** {item4_text}
5. **What Orange learned (latest claims):** {item5_text}.
6. **Most recent decisions:** {item6_text}.
7. **Most recent corrections / supersessions:** {item7_text}.
8. **Unresolved:** {core['quarantine_pending_review']['count']} actionable quarantined msgs await your review ({', '.join(str(m) for m in core['quarantine_pending_review']['message_ids'])}) — {core['quarantine_pending_review']['operator_resolved_count']} already resolved via quarantine_review.py (run `python orange_brain/quarantine_review.py --list` for the queue file); open questions {core['open_questions']} (open_questions_v0_1.json); risks: {', '.join(core['known_defects']['risks'][:4])}…
9. **Fable next:** {core['next_actions'][0]}; then: {core['next_actions'][2] if len(core['next_actions']) > 2 else ''}.
10. **Martyn must now (max 3):** {weekly_plan_line}{rc_line}(a) review the {core['quarantine_pending_review']['count']} actionable quarantined messages; (b) decide on OQ-7 (Windows auto-reboots killed capture twice this week — check Update active-hours; Orange will not change power settings); (c) nothing else required.
11. **Martyn must NOT:** enable any execution/broker path; ask for model fitting (no governance sign-off exists; research-proposed floor unmet anyway — D-009); treat Lane B numbers as headline; treat pip-claim messages as exits.
12. **Single current priority:** {core['priority']}.

Open code defects: {core['known_defects']['open_code_defects'] or 'NONE'}. Register staleness: {drift_txt}.
Ledger anchors: fwd {core['ledgers']['forward_ledger']['lines']} lines sha {core['ledgers']['forward_ledger']['sha16']}; freeze {core['ledgers']['genuine_freeze']['records']} sha {core['ledgers']['genuine_freeze']['sha16']}; guards {core['ledgers']['guards_sha16']}; const {core['ledgers']['constitution_sha16']}.
"""
    return md


def main():
    status_only = "--status" in sys.argv
    core, vol = collect()
    md = brief(core, vol)
    if status_only:
        print(md)
        return 0
    guarded_write("project_state_v0_1.json",
                  json.dumps({"schema": "orange_brain_state_v0_1",
                              "state_core": core, "volatile": vol}, indent=1))
    guarded_write("operator_brief.md", md)
    guarded_write("operator_brief.json", json.dumps(
        {"refreshed_at": vol["refreshed_at_utc"], "state_core": core}, indent=1))
    print(md)
    print("refresh written: project_state_v0_1.json, operator_brief.md, operator_brief.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
