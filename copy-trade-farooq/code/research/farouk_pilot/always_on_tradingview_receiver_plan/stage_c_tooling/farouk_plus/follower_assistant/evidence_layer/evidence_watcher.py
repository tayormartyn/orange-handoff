"""Evidence watcher — the SMALLEST additive activation path for the evidence layer.

A SEPARATE, read-only-input process (4th process; the listener/wire/tracker are NEVER touched).
It cannot block or affect the follower: a failure here only stops evidence capture, never the
proposal wire (a different process). Inputs, all READ-ONLY:
  * prospective_evidence_v1.db      — Telegram messages (same source the wire reads)
  * tracker ingestion_log_v0_1.jsonl — completed 1m bars (via BarStream.restore)
  * forward_validation_ledger_v0_2.jsonl — XAU_F_SETUP + outcome/partial-match records
Outputs, append-only, ONLY under evidence_layer/.

State is DERIVED from durable records each cycle -> idempotent + restart-safe. Per campaign:
  entry msg  -> PRE_TRADE_SNAPSHOT (causal features)              [firewall OPEN]
  mgmt msg   -> MANAGEMENT_SNAPSHOT + LATENCY_ACTIONABILITY
  outcome    -> firewall CLOSES -> HYPOTHESIS_TERMINAL (committed ref or NOT_GENERATED)
                                 -> COST_SCENARIO_VIEWS + SECOND_FEED_DIVERGENCE + STREAM_COVERAGE
"""
from __future__ import annotations

import argparse
import io
import json
import os
import sqlite3
import sys
import time
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
PARENT = os.path.dirname(HERE)
MT = os.path.join(PARENT, "market_tracker")
for p in (HERE, PARENT, MT):
    if p not in sys.path:
        sys.path.insert(0, p)
import guards                                                      # noqa: E402
import interpreter                                                # noqa: E402
import evidence_schema as es                                      # noqa: E402
import snapshots                                                  # noqa: E402
import cost_scenarios                                             # noqa: E402
import stream_coverage                                            # noqa: E402
import second_feed                                                # noqa: E402
import hypothesis_generator as hg                                 # noqa: E402
import backfill_quarantine as bq                                  # noqa: E402
from market_events import BarStream                               # noqa: E402

ST_ROOT = guards.ST_ROOT
EVIDENCE_DB = os.path.join(ST_ROOT, "campaign_extractor", "prospective", "data",
                           "prospective_evidence_v1.db")
FWD_LEDGER = os.path.join(PARENT, "..", "forward_validation_ledger_v0_2.jsonl")
INGEST_LOG = os.path.join(MT, "ingestion_log_v0_1.jsonl")
CURSOR = os.path.join(HERE, "evidence_watcher_cursor.json")
INSTANCE_LOCK = os.path.join(HERE, "evidence_watcher.instance.lock")
BANNER = "CAPTURE/RESEARCH ONLY | NO BROKER | NO EXECUTION"

# firewall-closing forward-ledger record types / markers for a campaign
OUTCOME_MARKERS = ("XAU_F_PARTIAL_MATCH", "TRACKER_SNAPSHOT")   # outcome/adjudication evidence

# --- ENTRY-race fix v0.1 (2026-07-16): a genuine ENTRY whose XAU_F_SETUP has not appeared in the
# forward ledger yet (the wire polls on its own interval) is NEVER silently consumed. It enters a
# durable pending set stored INSIDE the cursor file (so pending-state and cursor commit are one
# atomic write), is retried every cycle, and resolves only by one of:
#   1. setup found -> PRE lifecycle completed exactly once (done-tag guarded);
#   2. bounded-wait timeout / firewall-closed -> explicit durable refusal record appended;
#   3. proven duplicate (done-tag already set).
# A failed setup lookup alone NEVER durably consumes the entry.
ENTRY_REFUSAL_LEDGER = os.path.join(HERE, "entry_refusals_v0_1.jsonl")
ENTRY_SETUP_WAIT_MULTIPLIER = 10        # bounded wait = 10 wire polls (normal latency + margin)


def _wire_poll_seconds():
    """The wire's CONFIGURED polling interval, derived from live_wire itself (not re-hard-coded)."""
    try:
        import inspect
        import live_wire as _lw
        return int(inspect.signature(_lw.watch).parameters["interval"].default)
    except Exception:                                             # noqa: BLE001
        return 30                       # live_wire.watch documented default, used only if import fails


def entry_setup_wait_seconds():
    return _wire_poll_seconds() * ENTRY_SETUP_WAIT_MULTIPLIER


def log(m):
    print(f"[{datetime.now(timezone.utc):%Y-%m-%dT%H:%M:%SZ}] {m}", flush=True)


INITIAL_AFTER_MSG_ID = 45742     # F001/F002 predate the layer; scope = campaign #3 onward


def load_cursor():
    if os.path.exists(CURSOR):
        return json.load(open(CURSOR, encoding="utf-8"))
    return {"after_msg_id": INITIAL_AFTER_MSG_ID, "done": {}}


def save_cursor(c):
    tmp = CURSOR + ".tmp"
    json.dump(c, open(tmp, "w", encoding="utf-8"), indent=1)
    os.replace(tmp, CURSOR)


def bars_from_log():
    s = BarStream()
    if os.path.exists(INGEST_LOG):
        s.log_path = INGEST_LOG
        s.restore()
    return s.ordered_tuples()


def messages(after_id, db_path=EVIDENCE_DB):
    con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        rows = con.execute(
            "SELECT telegram_message_id, telegram_posted_at_utc, listener_received_at_utc, raw_text, "
            "raw_text_hash, telegram_sender_username FROM prospective_message_evidence "
            "WHERE CAST(telegram_message_id AS INTEGER) > ? AND message_event_type='CREATED' "
            "ORDER BY CAST(telegram_message_id AS INTEGER)", (after_id,)).fetchall()
    finally:
        con.close()
    return [{"id": int(r[0]), "posted": r[1], "received": r[2], "raw_text": r[3],
             "sha": r[4], "sender": r[5]} for r in rows]


def message_by_id(mid, db_path=EVIDENCE_DB):
    """Single durable evidence row (CREATED) for a pending-entry retry. Read-only."""
    con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        rows = con.execute(
            "SELECT telegram_message_id, telegram_posted_at_utc, listener_received_at_utc, raw_text, "
            "raw_text_hash, telegram_sender_username FROM prospective_message_evidence "
            "WHERE CAST(telegram_message_id AS INTEGER) = ? AND message_event_type='CREATED' "
            "ORDER BY message_revision_number LIMIT 1", (int(mid),)).fetchall()
    finally:
        con.close()
    if not rows:
        return None
    r = rows[0]
    return {"id": int(r[0]), "posted": r[1], "received": r[2], "raw_text": r[3],
            "sha": r[4], "sender": r[5]}


def _refusal_exists(mid):
    if not os.path.exists(ENTRY_REFUSAL_LEDGER):
        return False
    with open(ENTRY_REFUSAL_LEDGER, encoding="utf-8") as fh:
        for line in fh:
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            if r.get("record_type") == "ENTRY_SETUP_REFUSAL" and r.get("message_id") == int(mid):
                return True
    return False


def _append_entry_refusal(mid, pend, now_ts, reason):
    """Durable, idempotent capture-gap/refusal record: the entry is NOT silently discarded —
    it is explicitly marked prospective-ineligible with full observability fields."""
    if _refusal_exists(mid):
        return False
    rec = es.finalize({
        "record_type": "ENTRY_SETUP_REFUSAL",
        "message_id": int(mid),
        "first_seen_ts": (pend or {}).get("first_seen_ts"),
        "refused_ts": now_ts,
        "retries": (pend or {}).get("retries", 0),
        "configured_wait_window_seconds": entry_setup_wait_seconds(),
        "wire_poll_seconds": _wire_poll_seconds(),
        "reason": reason,
        "eligible_for_prospective_evidence": False,
        "eligible_for_training": False,
        "eligible_for_performance_attribution": False,
        "review_only": True, "executable": False, "trade_ready": False, "observation_only": True})
    return es.append_once(ENTRY_REFUSAL_LEDGER, rec)


def latest_bar_close(bars):
    return bars[-1] if bars else None


def outcome_exists(setup_id):
    """firewall CLOSED once an outcome/adjudication record for this campaign exists."""
    return es.firewall_state(setup_id) == "CLOSED"


def committed_hypothesis_ref(setup_id):
    if not os.path.exists(es.BLIND_HYP_LEDGER):
        return None
    with open(es.BLIND_HYP_LEDGER, encoding="utf-8") as fh:
        for line in fh:
            if setup_id in line:
                r = json.loads(line)
                if r.get("record_type") == "BLIND_HYPOTHESIS":
                    return r.get("logical_hash")
    return None


def already(cur, tag):
    return cur["done"].get(tag) is True


def mark(cur, tag):
    cur["done"][tag] = True


def _entry_lifecycle(m, c, sid, cur, bars, lb, now_ts, actions):
    """PRE snapshot + blind hypothesis + ranking pack for ONE genuine registered ENTRY.
    Exactly-once (done-tag guarded). Returns True when the entry is durably resolved
    (lifecycle completed, provably duplicate, or explicitly refused because the firewall
    already closed); False when it must remain retryable (a write failed)."""
    tag = f"PRE:{sid}:{m['id']}"
    if already(cur, tag):
        actions.append(f"ENTRY_DUPLICATE_ALREADY_COMPLETED({m['id']} -> {sid})")
        return True
    if es.firewall_state(sid) != "OPEN":
        # outcome knowledge already exists: a PRE snapshot/freeze may NEVER be created now.
        # Honest, durable, explicit refusal — never a silent skip, never a retro-repair.
        _append_entry_refusal(m["id"], cur.get("pending_entries", {}).get(str(m["id"])), now_ts,
                              f"firewall CLOSED before PRE lifecycle for {sid} — "
                              "no snapshot/freeze may be created after outcome knowledge")
        mark(cur, tag)
        actions.append(f"ENTRY_REFUSED_FIREWALL_CLOSED({m['id']} -> {sid})")
        return True
    try:
        snap = snapshots.build_pre_trade_snapshot(
            setup_id=sid, direction=c["direction"], zone_low=c["zone_low"],
            zone_high=c["zone_high"], sl=c["sl"], source_ts=m["posted"],
            receipt_ts=m["received"], proposal_ts=_proposal_ts(sid),
            market_ts=(lb[0] + 60 if lb else now_ts),
            current_price=(str(lb[4]) if lb else None),
            incomplete_bar_status=("FORMING" if lb else "NO_BARS"), bars=bars)
        es.append_once(es.PRE_TRADE_LEDGER, snap)
        mark(cur, tag)
        actions.append(f"PRE_TRADE_SNAPSHOT({sid})")
        actions.append(f"ENTRY_PRE_LIFECYCLE_COMPLETED({m['id']} -> {sid})")
        # --- automatic BLIND hypothesis attempt (bounded, causal-only) ---------------
        actions.append(_auto_hypothesis(sid, snap, cur, now_ts))
        # --- campaign-#3 ranking-evidence pack (data-gated; NEVER blocks follower) ----
        actions.append(_ranking_pack(sid, c, m, cur))
        return True
    except Exception as e:                                        # noqa: BLE001
        actions.append(f"ENTRY_LIFECYCLE_WRITE_FAILED({m['id']} -> {sid}: {type(e).__name__}) "
                       "— entry stays pending, retry next cycle")
        return False


def _pending_entry_pass(cur, db_path, bars, lb, now_ts, actions):
    """Retry every durable pending ENTRY (ascending message id — ordering preserved, no
    head-of-line block: new messages keep flowing regardless). Survives restart because the
    pending set lives inside the atomically-written cursor file."""
    pend = cur.setdefault("pending_entries", {})
    wait_s = entry_setup_wait_seconds()
    for key in sorted(list(pend), key=int):
        p = pend[key]
        m = message_by_id(int(key), db_path)
        if m is None:
            _append_entry_refusal(int(key), p, now_ts,
                                  "pending entry's evidence row no longer readable")
            actions.append(f"ENTRY_REFUSED_SETUP_TIMEOUT({key}: evidence row unreadable)")
            del pend[key]
            continue
        c = interpreter.classify(m["raw_text"])
        if c.get("kind") != "ENTRY":
            _append_entry_refusal(int(key), p, now_ts,
                                  f"re-classification is {c.get('kind')} not ENTRY (deterministic "
                                  "parser changed between versions) — refused, not silently dropped")
            actions.append(f"ENTRY_REFUSED_SETUP_TIMEOUT({key}: reclassified {c.get('kind')})")
            del pend[key]
            continue
        sid = _setup_id_for_message(int(key))
        if sid is not None:
            if _entry_lifecycle(m, c, sid, cur, bars, lb, now_ts, actions):
                del pend[key]
            # else: write failed -> stays pending, cursor commit withheld for this entry
        else:
            p["retries"] = p.get("retries", 0) + 1
            if (now_ts - p.get("first_seen_ts", now_ts)) > wait_s:
                _append_entry_refusal(int(key), p, now_ts,
                                      f"no XAU_F_SETUP appeared within {wait_s}s "
                                      f"({ENTRY_SETUP_WAIT_MULTIPLIER}x wire poll "
                                      f"{_wire_poll_seconds()}s) — capture gap, prospective-ineligible")
                actions.append(f"ENTRY_REFUSED_SETUP_TIMEOUT({key} retries={p['retries']} "
                               f"wait_window={wait_s}s)")
                del pend[key]
            else:
                actions.append(f"ENTRY_RETRY({key} retries={p['retries']})")


def run_cycle(db_path=EVIDENCE_DB, now_ts=None):
    guards.assert_constitution_frozen()
    now_ts = now_ts or int(time.time())
    cur = load_cursor()
    bars = bars_from_log()
    lb = latest_bar_close(bars)
    actions = []
    # --- 0. retry durable pending entries FIRST (older ids -> ordering preserved) ------------
    _pending_entry_pass(cur, db_path, bars, lb, now_ts, actions)
    # --- 1. new messages -> pre-trade snapshots / management snapshots -----------------------
    for m in messages(cur["after_msg_id"], db_path):
        cur["after_msg_id"] = max(cur["after_msg_id"], m["id"])
        c = interpreter.classify(m["raw_text"])
        if c["kind"] == "ENTRY":
            # only snapshot entries the WIRE has registered as a real XAU_F_SETUP campaign.
            # ENTRY-race fix v0.1: if the setup is not in the forward ledger yet (the wire
            # hasn't polled this instant), the entry is DEFERRED into the durable pending set
            # — never silently consumed by the after_msg_id advance. A failed lookup alone is
            # not a commit condition (cursor commit rule).
            sid = _setup_id_for_message(m["id"])
            if sid is None:
                cur.setdefault("pending_entries", {})[str(m["id"])] = {
                    "first_seen_ts": now_ts, "retries": 0}
                actions.append(f"ENTRY_DEFERRED_WAITING_FOR_SETUP({m['id']})")
            elif not _entry_lifecycle(m, c, sid, cur, bars, lb, now_ts, actions):
                # lifecycle write failed -> durable pending so the retry survives restart
                cur.setdefault("pending_entries", {})[str(m["id"])] = {
                    "first_seen_ts": now_ts, "retries": 0}
        elif c["kind"] == "MANAGEMENT":
            sid = _latest_open_setup()
            tag = f"MGMT:{sid}:{m['id']}"
            if sid and not already(cur, tag):
                ms = snapshots.build_management_snapshot(
                    setup_id=sid, message_id=m["id"], source_ts=m["posted"], receipt_ts=m["received"],
                    current_price=(str(lb[4]) if lb else None),
                    instruction_interpretation=c["instructions"],
                    lane_state_with={}, lane_state_without={"note": "counterfactual: instruction ignored"})
                es.append_once(es.MGMT_LEDGER, ms)
                mark(cur, tag)
                actions.append(f"MANAGEMENT_SNAPSHOT({sid})")
    save_cursor(cur)
    # --- 1b. ROUTER FREEZE sweep (stage 3: after PRE_TRADE_SNAPSHOT, while firewall OPEN, BEFORE
    #        outcome). Robust to cursor position — derives from the durable PRE_TRADE ledger, so a
    #        campaign whose entry message was already consumed is still frozen on the next cycle.
    #        Additive, fail-closed, done-tag-guarded: it can NEVER block capture/proposal/follower. --
    for sid in _all_setup_ids():
        a = _router_freeze_sweep(sid, cur, bars)
        if a:
            actions.append(a)
    save_cursor(cur)
    # --- 2. campaigns whose firewall just CLOSED -> resolve terminal + post-outcome records ---
    for sid in _all_setup_ids():
        if not outcome_exists(sid):
            continue
        tag = f"RESOLVED:{sid}"
        if already(cur, tag):
            continue
        # exactly-one terminal: if the auto-generator already emitted a NOT_GENERATED terminal,
        # do not emit a second one (just proceed to post-outcome views)
        if not _has_terminal(sid):
            ref = committed_hypothesis_ref(sid)
            term = snapshots.build_hypothesis_terminal(
                setup_id=sid, committed_ref=ref,
                missing_features=["no BLIND_HYPOTHESIS committed before firewall closed"],
                attempted_ts=now_ts, firewall_state="CLOSED", follower_continued=True)
            es.append_once(es.MGMT_LEDGER, term)
        # cost + divergence + coverage (research views; never touch raw outcome)
        cls = {"setup_id": sid, "analytical_class": bq.classification(sid)}
        res = _outcome_numbers(sid)
        cv = es.finalize(cost_scenarios.apply_views(
            realized_pips=res["realized"], unrealized_pips=res["unrealized"],
            n_fills=res["n_fills"], n_partial_exits=res["n_partial_exits"],
            feed_sensitive_events=res["feed_sensitive"]) | cls)
        es.append_once(es.MGMT_LEDGER, cv)
        sf = es.finalize(second_feed.divergence_report(
            pepperstone_bars=bars, comparison_bars=None, comparison_provider="DUKASCOPY_DELAYED",
            levels=[]) | cls)
        es.append_once(es.SECONDFEED_LEDGER, sf)
        cov = es.finalize(stream_coverage.coverage_report(
            _recent_messages_for_coverage(db_path), "auto", "auto") | cls)
        es.append_once(es.COVERAGE_LEDGER, cov)
        mark(cur, tag)
        actions.append(f"RESOLVED+COST+DIVERGENCE+COVERAGE({sid}) hyp={term['state']}")
    save_cursor(cur)
    return actions


def _ranking_pack(sid, classified_entry, msg, cur):
    """Campaign-#3 ranking automation. Only real campaigns (F-index>=3, analytical) get a pack; the
    quarantined backfill is skipped. Data-gated + fail-closed inside the harness. Any failure is
    swallowed so the ranking harness can NEVER affect capture/proposals/follower."""
    try:
        import backfill_quarantine as _bq
        if not _bq.is_analytical(sid):
            return f"RANKING_SKIP({sid} NON_ANALYTICAL_BACKFILL)"
        import ranking_harness as _rh
        c = classified_entry
        sig = int(datetime.fromisoformat(msg["posted"].replace("Z", "+00:00")).timestamp())
        done = set(cur.get("ranking_done", []))
        act = _rh.emit_ranking_pack_for_campaign(sid, sig, c["direction"],
                                                 c["zone_low"], c["zone_high"], done)
        cur.setdefault("ranking_done", [])
        if sid not in cur["ranking_done"] and "EMITTED" in act:
            cur["ranking_done"].append(sid)
        return act
    except Exception as e:                                       # noqa: BLE001
        return f"RANKING_HARNESS_ERROR({sid}: {type(e).__name__}) — follower/capture unaffected"


def _pretrade_for(sid):
    """Latest durable PRE_TRADE_SNAPSHOT for a campaign (read-only)."""
    if not os.path.exists(es.PRE_TRADE_LEDGER):
        return None
    found = None
    with open(es.PRE_TRADE_LEDGER, encoding="utf-8") as fh:
        for line in fh:
            if sid in line:
                try:
                    r = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if r.get("record_type") == "PRE_TRADE_SNAPSHOT" and r.get("setup_id") == sid:
                    found = r
    return found


def _router_frozen(sid):
    import strategy_router as _sr
    if not os.path.exists(_sr.ROUTER_FREEZE_LEDGER):
        return False
    with open(_sr.ROUTER_FREEZE_LEDGER, encoding="utf-8") as fh:
        for line in fh:
            if sid in line:
                try:
                    r = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if r.get("record_type") == "ROUTER_FREEZE" and r.get("setup_id") == sid:
                    return True
    return False


def _router_freeze_sweep(sid, cur, bars):
    """Freeze the router hierarchy for a campaign whose firewall is OPEN and which has a
    PRE_TRADE_SNAPSHOT but no ROUTER_FREEZE yet. RESEARCH-ONLY, additive, fail-closed. Returns a log
    string only when it actually freezes or errors; None on no-op. NEVER blocks the follower."""
    tag = f"ROUTER:{sid}"
    try:
        if already(cur, tag):
            return None
        # only real analytical campaigns (#3 onward); F001/F002 backfill handled separately
        if not bq.is_analytical(sid):
            mark(cur, tag)
            return None
        # freeze ONLY while the chronological firewall is OPEN (stage 3, before outcome/hypothesis)
        if es.firewall_state(sid) != "OPEN":
            return None
        if _router_frozen(sid):
            mark(cur, tag)
            return None
        pt = _pretrade_for(sid)
        if pt is None:
            return None    # no snapshot yet — a later cycle picks it up
        import strategy_router as _sr
        zl, _, zh = pt["zone"].partition("-")
        dts = int(datetime.fromisoformat(pt["timestamps"]["source_message_utc"].replace("Z", "+00:00")).timestamp())
        # Section 9 canonical-clock: decision AFTER hooked activation => PROSPECTIVE, else STRADDLE.
        am = _sr.read_activation_marker()
        act_ts = am["activation_ts_utc"] if am else None
        rclass, clock_reason = _sr.classify_activation(dts, act_ts)
        # test-seam: an integration harness may force SYNTHETIC_INTEGRATION_TEST so the REAL lifecycle
        # is exercised while records are correctly classed + routed to the isolated test ledger.
        # Defaults None in production -> zero effect on genuine operation.
        if getattr(_sr, "RECORD_CLASS_OVERRIDE", None):
            rclass, clock_reason = _sr.RECORD_CLASS_OVERRIDE, "record_class overridden by integration harness"
        # provenance/lifecycle eligibility gate (not merely a numeric id): must be a genuine
        # XAU_F_SETUP campaign, firewall OPEN (already checked), decision strictly after activation.
        prov = {"setup_id": sid, "xau_f_setup_message_ids": _setup_message_ids(sid),
                "proposal_ts": _proposal_ts(sid)}
        raw_ref = {"pretrade_logical_hash": pt.get("logical_hash", es.UNKNOWN),
                   "source_message_utc": pt["timestamps"]["source_message_utc"]}
        rec = _sr.freeze_router(setup_id=sid, direction=pt["direction"], zone_low=zl, zone_high=zh,
                                sl=pt["posted_stop"], decision_ts=dts, bars=bars,
                                objective_lane="A_FOLLOWER", record_class=rclass,
                                raw_source_ref=raw_ref, campaign_provenance=prov, activation_ts=act_ts)
        es.append_once(_sr.ROUTER_FREEZE_LEDGER, rec)
        mark(cur, tag)
        return f"ROUTER_FREEZE({sid} class={rclass}: {clock_reason})"
    except Exception as e:                                        # noqa: BLE001
        return f"ROUTER_FREEZE_ERROR({sid}: {type(e).__name__}) — follower/capture unaffected"


def _has_terminal(sid):
    if not os.path.exists(es.MGMT_LEDGER):
        return False
    with open(es.MGMT_LEDGER, encoding="utf-8") as fh:
        for line in fh:
            if sid in line:
                try:
                    r = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if r.get("record_type") == "HYPOTHESIS_TERMINAL" and r.get("setup_id") == sid:
                    return True
    return False


def _auto_hypothesis(sid, snap, cur, now_ts):
    """Attempt exactly one automatic BLIND_HYPOTHESIS. On any failure or a firewall that closed
    during generation, emit exactly one HYPOTHESIS_NOT_GENERATED terminal with the reason.
    NEVER retried (guarded by a done-tag). The follower is a separate process and is unaffected
    regardless of what happens here."""
    gtag = f"GEN:{sid}"
    if already(cur, gtag) or _has_terminal(sid):
        return f"HYP_SKIP({sid}: already attempted/resolved)"
    reason = None
    try:
        h = hg.generate(snap, now_ts, deadline_s=hg.DEADLINE_SECONDS)
        # re-check the firewall AFTER generation: it may have closed while generating
        if es.firewall_state(sid) != "OPEN":
            reason = "firewall closed during generation"
        else:
            rec = snapshots.build_blind_hypothesis(
                setup_id=sid, expected_direction=h["expected_direction"],
                strongest_zone=h["strongest_candidate_zone"], invalidation=h["invalidation"],
                structural_rationale=h["structural_rationale"], confidence=h["confidence"],
                alternative_hypothesis=h["alternative_hypothesis"], unknowns=h["unknowns"],
                authored_ts=now_ts, snapshot_hash=h["snapshot_hash"],
                methodology_version=h["methodology_version"], generator="AUTO",
                extra={"agrees_with_posted_setup": h["agrees_with_posted_setup"],
                       "generation_ms": h["generation_ms"]})
            es.append_once(es.BLIND_HYP_LEDGER, rec)
            mark(cur, gtag)
            return f"BLIND_HYPOTHESIS_AUTO({sid}: {h['expected_direction']} conf {h['confidence']})"
    except es.FirewallViolation:
        reason = "firewall closed before hypothesis could commit"
    except (hg.HypothesisTimeout, hg.HypothesisMalformed, hg.MissingFeatures) as e:
        reason = f"{type(e).__name__}: {e}"
    except Exception as e:                                        # noqa: BLE001
        reason = f"generator error {type(e).__name__}: {e}"
    # failure path -> exactly one NOT_GENERATED terminal (this IS the campaign's terminal)
    missing = snap.get("unavailable_features") or []
    term = snapshots.build_hypothesis_terminal(
        setup_id=sid, committed_ref=None, missing_features=missing + [reason],
        attempted_ts=now_ts, firewall_state=es.firewall_state(sid), follower_continued=True)
    es.append_once(es.MGMT_LEDGER, term)
    mark(cur, gtag)
    return f"HYPOTHESIS_NOT_GENERATED({sid}: {reason})"


# ---- durable-ledger helpers (all read-only) ---------------------------------------------------
def _fwd_records():
    out = []
    if os.path.exists(FWD_LEDGER):
        for line in open(FWD_LEDGER, encoding="utf-8"):
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return out


def _setup_id_for_message(mid):
    for r in _fwd_records():
        if r.get("record_type") == "XAU_F_SETUP" and mid in (r.get("message_ids") or []):
            return r["setup_id"]
    return None


def _proposal_ts(sid):
    for r in _fwd_records():
        if r.get("record_type") == "XAU_F_SETUP" and r.get("setup_id") == sid:
            return r.get("timestamp_utc")
    return es.UNKNOWN


def _setup_message_ids(sid):
    for r in _fwd_records():
        if r.get("record_type") == "XAU_F_SETUP" and r.get("setup_id") == sid:
            return r.get("message_ids") or []
    return []


def _all_setup_ids():
    return sorted({r["setup_id"] for r in _fwd_records()
                   if r.get("record_type") == "XAU_F_SETUP"})


def _latest_open_setup():
    ids = _all_setup_ids()
    return ids[-1] if ids else None


def _outcome_numbers(sid):
    """Read the deterministic LANE_A result from the latest TRACKER_SNAPSHOT for this campaign
    (the tracker's frozen outcome). TRACKER_SNAPSHOT is a data source here, NOT a firewall
    trigger — the firewall closes on the genuine outcome/adjudication/video marker."""
    realized, unrealized, nf, npx, fs = "0", "UNKNOWN", 1, 1, 0
    for r in _fwd_records():
        if r.get("record_type") == "TRACKER_SNAPSHOT" and r.get("setup_id") == sid:
            a = r["snapshot"]["lanes"]["LANE_A"]["engine"]
            realized = a.get("realized_pips_per_unit", "0")
            unrealized = a.get("unrealized_pips_per_unit") or "UNKNOWN"
            nf = sum(1 for l in a.get("legs", []) if l["state"] == "FILLED") or 1
            npx = sum(1 for s in a.get("slices", []) if s["reason"].startswith(("P12", "P11", "ADD_TP2")))
    return {"realized": realized, "unrealized": unrealized, "n_fills": nf,
            "n_partial_exits": max(npx, 0), "feed_sensitive": fs}


def _recent_messages_for_coverage(db_path, n=40):
    con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        rows = con.execute("SELECT telegram_message_id, raw_text FROM prospective_message_evidence "
                           "WHERE message_event_type='CREATED' ORDER BY CAST(telegram_message_id AS INTEGER) "
                           "DESC LIMIT ?", (n,)).fetchall()
    finally:
        con.close()
    return [{"id": int(r[0]), "raw_text": r[1]} for r in rows]


def watch(interval=45):
    try:
        fd = os.open(INSTANCE_LOCK, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        os.write(fd, str(os.getpid()).encode()); os.close(fd)
    except FileExistsError:
        raise SystemExit("another evidence_watcher holds the lock — refusing to start")
    log(f"evidence watcher started pid={os.getpid()} | {BANNER}")
    log("listener/wire/tracker are separate processes and are NEVER touched")
    # router hooked-build: freeze the canonical activation timestamp + loaded-module hash so the
    # sweep can distinguish genuine-prospective (decision AFTER activation) from ACTIVATION_STRADDLE
    try:
        import strategy_router as _sr
        _am = _sr.write_activation_marker(os.getpid(), int(time.time()))
        log(f"ROUTER SWEEP HOOK REGISTERED | activation_ts={_am['activation_ts_utc']} "
            f"module_sha={_am['module_content_sha256'][:16]} pid={_am['pid']}")
    except Exception as e:                                        # noqa: BLE001
        log(f"router activation-marker write failed: {type(e).__name__} — capture/follower unaffected")
    bq.write_manifest()          # (re)write the backfill quarantine manifest (idempotent)
    log("backfill quarantine manifest written; F001/F002 + placeholder ids = NON_ANALYTICAL_BACKFILL")
    try:
        while True:
            try:
                for a in run_cycle():
                    log(a)
            except Exception as e:                                # noqa: BLE001
                log(f"cycle error: {type(e).__name__}: {e} — follower + capture processes unaffected")
            time.sleep(interval)
    finally:
        os.remove(INSTANCE_LOCK)


if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("--watch", action="store_true")
    ap.add_argument("--once", action="store_true")
    args = ap.parse_args()
    if args.watch:
        watch()
    else:
        for a in run_cycle():
            print(a)
        print("single cycle complete")
