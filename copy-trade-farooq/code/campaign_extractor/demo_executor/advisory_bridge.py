"""
Read-only ADVISORY handoff: Telegram evidence -> Farouk Interpretation Contract 1.0.0 -> advisory
result. This is NOT the execution handoff (module_b stays disabled). For each genuinely-new prospective
message posted AFTER the bridge activation timestamp, it runs ONE interpretation job, consults the live
quote store, stores ONE append-only advisory result, and emits ONE operator alert. It NEVER confirms a
signal, arms a proposal, issues a permit/lease, or calls any broker transport. Deduplicated by Telegram
message id + attachment hash; the 82 historical messages (posted before activation) are never replayed.
"""
from __future__ import annotations
import json
import os
import sqlite3

import config as CFG
import operator_alerts as OA

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
STATE_FILE = os.path.join(_ROOT, "data", "advisory_bridge_state.json")
RESULTS_LOG = os.path.join(_ROOT, "data", "advisory_results.jsonl")
QUOTE_DB = os.path.join(_ROOT, "data", "ctrader_quotes_v1.db")
ADVISORY_HANDOFF_ENABLED_DEFAULT = True     # read-only advisory handoff (NOT execution)


def _fc():
    import farouk_contract as FC
    return FC


def _iso(ms):
    if ms is None:
        return None
    import time as _t
    return _t.strftime("%Y-%m-%dT%H:%M:%SZ", _t.gmtime(ms / 1000))


def load_state():
    if os.path.exists(STATE_FILE):
        try:
            return json.load(open(STATE_FILE, encoding="utf-8"))
        except Exception:
            pass
    return {"enabled": False, "activation_ts_ms": None, "processed_keys": [], "seq": 0}


def save_state(st):
    json.dump(st, open(STATE_FILE, "w", encoding="utf-8"))


def enable(now_ms):
    """Enable the read-only advisory handoff and stamp the activation timestamp (once). Only messages
    newer than this timestamp enter the automatic handoff."""
    st = load_state()
    st["enabled"] = True
    if st.get("activation_ts_ms") is None:
        st["activation_ts_ms"] = now_ms
    save_state(st)
    return {"ADVISORY_HANDOFF_ENABLED": True, "activation_ts_ms": st["activation_ts_ms"]}


def status():
    st = load_state()
    return {"ADVISORY_HANDOFF_ENABLED": bool(st.get("enabled")),
            "activation_ts_ms": st.get("activation_ts_ms"), "jobs_processed": st.get("seq", 0)}


def _live_quote_ctx(now_ms, db_path=None):
    """Read the latest quote + a recent quote-path from the append-only quote store (read-only)."""
    db = db_path or QUOTE_DB
    if not os.path.exists(db):
        return None, "QUOTES_ERROR", []
    try:
        import calendar
        import time as _t
        c = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
        # carried-forward latest_bid/latest_ask (never null on one-sided spot updates); fall back to norm_*
        rows = c.execute("SELECT COALESCE(latest_bid, norm_bid), COALESCE(latest_ask, norm_ask), "
                         "persisted_utc FROM normalised_quotes ORDER BY rowseq DESC LIMIT 400").fetchall()
        c.close()
        rows = [r for r in rows if r[0] is not None and r[1] is not None]
        if not rows:
            return None, "QUOTES_SILENT", []
        def _ms(s):
            return int(calendar.timegm(_t.strptime(s, "%Y-%m-%dT%H:%M:%SZ"))) * 1000
        latest = rows[0]
        ev_ms = _ms(latest[2])
        import quote_health as QH
        state = QH.health(latest_bid=latest[0], latest_ask=latest[1], latest_event_ms=ev_ms,
                          now_ms=now_ms, events_this_session=len(rows))["state"]
        quote = type("Q", (), {"bid": latest[0], "ask": latest[1], "ts_ms": ev_ms})()
        path = [{"bid": r[0], "ask": r[1], "ts_ms": _ms(r[2])} for r in rows]
        return quote, state, path
    except Exception:
        return None, "QUOTES_ERROR", []


def _new_messages(processed, db_path, activation_ts_ms):
    from operator_alerts import PROSPECTIVE_DB, _dedup_key, _ts_ms
    db = db_path or PROSPECTIVE_DB
    if not os.path.exists(db):
        return []
    c = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    cols = {r[1] for r in c.execute("PRAGMA table_info(prospective_message_evidence)")}
    has_sender = "telegram_sender_id" in cols            # sender capture may predate some rows -> NULL
    has_fwd = "telegram_is_forwarded" in cols
    sender_sel = (", telegram_sender_id, telegram_sender_username, telegram_sender_display"
                  if has_sender else "")
    fwd_sel = ", telegram_is_forwarded, telegram_fwd_origin" if has_fwd else ""
    rows = c.execute("SELECT telegram_message_id, telegram_channel_id, telegram_posted_at_utc, "
                     "raw_text, media_reference_or_hash" + sender_sel + fwd_sel +
                     " FROM prospective_message_evidence ORDER BY rowseq ASC").fetchall()
    c.close()
    out = []
    for r in rows:
        mid, chan, posted, raw, media = r[0], r[1], r[2], r[3], r[4]
        i = 5
        sid, suser, sdisp = (r[i], r[i + 1], r[i + 2]) if has_sender else (None, None, None)
        if has_sender:
            i += 3
        is_fwd, fwd_origin = (r[i], r[i + 1]) if has_fwd else (None, None)
        key = _dedup_key(mid, media)
        if key in processed:
            continue
        posted_ms = _ts_ms(posted)
        # ONLY messages newer than activation enter the handoff (no historical replay)
        if activation_ts_ms is not None and posted_ms is not None and posted_ms < activation_ts_ms:
            processed.add(key)                          # mark historical as processed WITHOUT a job
            continue
        out.append({"message_id": mid, "channel_id": chan, "posted_ms": posted_ms, "raw_text": raw,
                    "media": media, "key": key, "sender_id": sid, "sender_username": suser,
                    "sender_display": sdisp, "is_forwarded": is_fwd, "fwd_origin": fwd_origin})
    return out


def process(now_ms, *, db_path=None, quote_ctx=None):
    """Run the advisory handoff once. Returns the newly-created advisory results."""
    st = load_state()
    if not st.get("enabled"):
        return []
    processed = set(st.get("processed_keys", []))
    activation = st.get("activation_ts_ms")
    quote, qstate, qpath = quote_ctx if quote_ctx is not None else _live_quote_ctx(now_ms, db_path=None)
    FC = _fc()
    results = []
    # share the operator-alert dedup/state so exactly one alert is produced per message
    alert_st = OA.load_state()
    alerted = set(alert_st.get("alerted_message_ids", []))
    seen_sem = set(alert_st.get("seen_semantic_keys", []))
    import provider_route_authorisation as PRA
    for m in _new_messages(processed, db_path, activation):
        d = FC.interpret(raw_text=m["raw_text"], provider_ts_ms=m["posted_ms"], now_ms=now_ms,
                         quote=quote, quote_path=qpath, quote_health_state=qstate)
        st["seq"] = st.get("seq", 0) + 1
        job_id = "job-" + str(st["seq"])
        # ROUTE-LEVEL PROVIDER AUTHORISATION (fail closed): the shared Whale Room transport never grants
        # eligibility by itself; only an operator-CONFIRMED source route (sea-scalper-farouk) may. The
        # route is a CANDIDATE for now, so nothing is eligible. Messages are still preserved + classified.
        auth = PRA.authorise_route(sender_id=m.get("sender_id"), fwd_present=bool(m.get("is_forwarded")),
                                   raw_text=m.get("raw_text"), posted_ms=m.get("posted_ms"),
                                   activation_ms=activation)
        elig = bool(d["execution_eligible"] and auth["provider_route_authorised"])
        propose = bool(d["may_create_proposal"] and auth["provider_route_authorised"])
        blockers = list(d["blocking_reasons"])
        if not auth["provider_route_authorised"]:
            for code in auth["authorisation_reason_codes"]:
                if code not in blockers:
                    blockers.append(code)
            if auth["route_status"] == "UNAUTHORISED_PROVIDER_ROUTE" and "UNAUTHORISED_PROVIDER_ROUTE" not in blockers:
                blockers.append("UNAUTHORISED_PROVIDER_ROUTE")
        preview = (m.get("raw_text") or "").replace("\n", " ").strip()[:100]   # safe text preview <=100
        result = {"seq": st["seq"], "job_id": job_id, "message_id": m["message_id"],
                  "channel_id": m.get("channel_id"), "source_timestamp_utc": _iso(m["posted_ms"]),
                  "transport_sender_id": m.get("sender_id"), "transport_display": m.get("sender_display"),
                  "transport_authorised": auth["transport_authorised"],
                  "source_room_raw": auth["source_room_raw"],
                  "source_room_normalized": auth["source_room_normalized"],
                  "source_poster_label": auth["source_poster_label"],
                  "forward_metadata_present": auth["forward_metadata_present"],
                  "wrapper_valid": auth["wrapper_valid"], "route_status": auth["route_status"],
                  "provider_authorisation_type": auth["provider_authorisation_type"],
                  "provider_route_authorised": auth["provider_route_authorised"],
                  "personal_sender_verified": auth["personal_sender_verified"],
                  "authorisation_reason_codes": auth["authorisation_reason_codes"],
                  "text_preview": preview,
                  "contract_version": d["contract_version"], "intent": d["intent"], "flags": d["flags"],
                  "instrument": d["fields"].get("instrument"), "direction": d["fields"].get("direction"),
                  "order_type": d["fields"].get("order_type"), "entry_low": d["fields"].get("entry_low"),
                  "entry_high": d["fields"].get("entry_high"), "stop": d["fields"].get("stop"),
                  "signal_age_seconds": d["signal_age_seconds"], "quote_health_state": qstate,
                  "quote_consulted": quote is not None,
                  "execution_eligible": elig, "may_create_proposal": propose, "no_campaign": (not elig),
                  "human_confirmation_required": d["human_confirmation_required"],
                  "blocking_reasons": blockers, "no_broker_action": True, "created_at_ms": now_ms}
        _append(RESULTS_LOG, result)
        processed.add(m["key"])
        # ONE alert per message (deduped via the shared operator-alert state)
        a = OA.classify_alert(m["raw_text"], posted_at_ms=m["posted_ms"], now_ms=now_ms,
                              seen_semantic_keys=seen_sem)
        alert_st["seq"] = alert_st.get("seq", 0) + 1
        alert = {"seq": alert_st["seq"], "alert_id": m["key"], "message_id": m["message_id"], **a,
                 "instruction": "Open the local console to review — advisory only, no action taken.",
                 "created_at_ms": now_ms}
        OA._append_log(alert)
        alerted.add(m["key"])
        if a.get("semantic_key"):
            seen_sem.add(a["semantic_key"])
        results.append(result)
    st["processed_keys"] = list(processed)[-4000:]
    save_state(st)
    alert_st["alerted_message_ids"] = list(alerted)[-4000:]
    alert_st["seen_semantic_keys"] = list(seen_sem)[-4000:]
    alert_st["baselined"] = True                         # advisory bridge owns baselining via activation ts
    OA.save_state(alert_st)
    return results


def get_results(since):
    if not os.path.exists(RESULTS_LOG):
        return []
    out = []
    for l in open(RESULTS_LOG, encoding="utf-8"):
        if not l.strip():
            continue
        try:
            r = json.loads(l)
        except Exception:
            continue
        if r.get("seq", 0) > since:
            out.append(r)
    return out[-100:]


def _append(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(obj) + "\n")
