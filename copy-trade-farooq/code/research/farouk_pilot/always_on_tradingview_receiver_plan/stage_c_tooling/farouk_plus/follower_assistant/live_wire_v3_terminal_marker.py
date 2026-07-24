"""Stage-1 LIVE PROPOSAL WIRE — connects listener capture to the follower proposal emitter.

REVIEW-ONLY SHADOW PROPOSALS. NO BROKER ACTION. NO ORDER SUBMISSION.

Design:
  * SEPARATE process from the Telegram listener; reads prospective_evidence_v1.db strictly
    READ-ONLY (sqlite mode=ro URI). It can never block, restart, or modify the listener.
  * One canonical interpretation path (interpreter.py) -> XAU_F_SETUP-shaped records into the
    EXISTING forward ledger (no second ledger/source of truth), locked via guards.ledger_lock.
  * Proposal cards are emitted WITHOUT OHLC (legs + stop + lanes declared, NOT adjudicated);
    later adjudication (run_fixtures path) attaches price results when data is imported.
  * Idempotent: cursor file + per-record logical hashes + (campaign, message_id, revision)
    dedup; a re-run of any cycle emits nothing new.
  * Fail-closed: ambiguous entries -> NEEDS_HUMAN_REVIEW record + review-required card, no
    proposal legs. Edited (revision>1) campaign messages -> revision record + campaign pause.
  * Poison-pill protection: a message failing 3 consecutive cycles is recorded
    FAILED_NEEDS_HUMAN_REVIEW and skipped (raw evidence is already durably preserved).
"""
from __future__ import annotations

import io
import json
import os
import sqlite3
import sys
import time
from datetime import datetime, timezone
from decimal import Decimal as D

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import guards                                                    # noqa: E402
import interpreter                                               # noqa: E402
from engine import FollowerEngine, LANES, sha256_obj, sha256_file  # noqa: E402

FP = os.path.dirname(HERE)
ST_ROOT = guards.ST_ROOT
EVIDENCE_DB = os.path.join(ST_ROOT, "campaign_extractor", "prospective", "data",
                           "prospective_evidence_v1.db")
FWD_LEDGER = os.path.join(FP, "forward_validation_ledger_v0_2.jsonl")
FOLLOWER_LEDGER = os.path.join(HERE, "follower_ledger_v0_1.jsonl")
CONST_PATH = os.path.join(HERE, "follower_constitution_v0_1.json")
CURSOR_PATH = os.path.join(HERE, "live_wire_cursor.json")
CARD_DIR = os.path.join(HERE, "cards")
LOG_DIR = os.path.join(HERE, "logs")
INSTANCE_LOCK = os.path.join(HERE, "live_wire.instance.lock")
BANNER = "NO BROKER ACTION | NO ORDER SUBMISSION | REVIEW-ONLY SHADOW PROPOSAL"
INITIAL_CURSOR = 45742          # F001/F002 already session-committed; wire starts after


def log(msg):
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    line = f"[{stamp}] {msg}"
    print(line, flush=True)


# ---------------- state ------------------------------------------------------------------
def load_cursor():
    if os.path.exists(CURSOR_PATH):
        cur = json.load(open(CURSOR_PATH, encoding="utf-8"))
        # v2.2: edit-sweep cursor (rowseq-keyed). 0 is safe on first load: the sweep query
        # excludes CREATED rows and no non-CREATED rows predate this feature.
        cur.setdefault("last_edit_rowseq", 0)
        return cur
    return {"last_processed_id": INITIAL_CURSOR, "fail_counts": {}, "last_edit_rowseq": 0}


def save_cursor(cur):
    tmp = CURSOR_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(cur, fh, indent=1)
    os.replace(tmp, CURSOR_PATH)


def load_campaign_state():
    """Single source of truth = forward ledger. Latest revision per setup_id; a campaign is
    OPEN unless its events contain FINAL_CLOSE/CANCEL-close or a pause record supersedes it."""
    setups, paused, terminated = {}, set(), set()
    if os.path.exists(FWD_LEDGER):
        with open(FWD_LEDGER, encoding="utf-8") as fh:
            for line in fh:
                r = json.loads(line)
                rt = r.get("record_type")
                if rt == "XAU_F_SETUP":
                    setups[r["setup_id"]] = r
                elif rt == "XAU_F_CAMPAIGN_PAUSE":
                    paused.add(r["setup_id"])
                elif rt == "XAU_F_CAMPAIGN_PAUSE_RESOLVED":
                    # append-only adjudication: a later human/session resolution record lifts a
                    # pause (ledger order preserved; the pause record itself is never rewritten)
                    paused.discard(r["setup_id"])
                elif rt in ("XAU_F_TERMINAL_OUTCOME", "XAU_F_TERMINAL_ADJUDICATION"):
                    # v3 (D-063): a campaign whose terminal was OUTCOME-based (BE scratch, final
                    # TP, stop-out) carries no instruction token; an append-only terminal-marker
                    # record closes it in the open-set. XAU_F_TERMINAL_ADJUDICATION (defect-affected,
                    # governance rule) and XAU_F_TERMINAL_OUTCOME (clean outcome, no defect) both
                    # terminate. Marker must name setup_id + effective_ts + basis + per-leg states;
                    # a malformed marker (no setup_id) is ignored (fail-open = campaign STAYS open,
                    # the safe direction here - a missing close never fabricates a terminal).
                    _tsid = r.get("setup_id")
                    if _tsid:
                        terminated.add(_tsid)
    open_ids = []
    for sid, r in setups.items():
        evs = [e["instruction_type"] for e in
               r.get("management_timing_8c", {}).get("instruction_events", [])]
        if (not ({"FINAL_CLOSE", "EXPLICIT_FULL_EXIT"} & set(evs))
                and sid not in paused and sid not in terminated):
            open_ids.append(sid)
    return setups, sorted(open_ids), paused


# hotfix v0.1: management-correlation proximity window (DISCLOSED operational default, NOT a Farouk
# rule). A management message correlates only to an open campaign whose latest activity is within this
# window; a stale campaign (e.g. prior-day F002) is never a fallback target.
PROXIMITY_HOURS = 18


def _campaign_latest_ts(setups, sid):
    r = setups[sid]
    evs = r.get("management_timing_8c", {}).get("instruction_events", [])
    return evs[-1]["timestamp_utc"] if evs else r["timestamp_utc"]


def _within(ts_a, ts_b, hours):
    try:
        da = datetime.fromisoformat(str(ts_a).replace("Z", "+00:00"))
        db = datetime.fromisoformat(str(ts_b).replace("Z", "+00:00"))
        return abs((da - db).total_seconds()) <= hours * 3600
    except Exception:                                            # noqa: BLE001
        return False                                            # unparseable ts -> fail closed (not proximate)


def next_setup_id(setups, date_utc):
    n = 0
    for sid in setups:
        m = sid.split("-")
        if len(m) >= 2 and m[1].startswith("F"):
            try:
                n = max(n, int(m[1][1:]))
            except ValueError:
                pass
    return f"XAU-F{n + 1:03d}-{date_utc}"


# ---------------- evidence (READ-ONLY) ----------------------------------------------------
def new_messages(after_id, db_path=EVIDENCE_DB):
    con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        rows = con.execute(
            "SELECT telegram_message_id, telegram_posted_at_utc, raw_text, raw_text_hash, "
            "message_event_type, message_revision_number FROM prospective_message_evidence "
            "WHERE CAST(telegram_message_id AS INTEGER) > ? "
            "AND message_event_type = 'CREATED' "
            "ORDER BY CAST(telegram_message_id AS INTEGER), message_revision_number",
            (after_id,)).fetchall()
    finally:
        con.close()
    return [{"id": int(r[0]), "posted_at": r[1], "raw_text": r[2], "raw_text_sha256": r[3],
             "event_type": r[4], "revision": r[5]} for r in rows]


def new_edit_rows(after_rowseq, db_path=EVIDENCE_DB):
    """v2.2 edit sweep. The main cursor is keyed by MESSAGE id, so an EDITED row for an
    already-processed message (id <= cursor) would never be seen by new_messages — and
    edit-after-transition is exactly that case. This sweep is keyed by rowseq instead and
    is the ONLY consumer of non-CREATED rows (new_messages now filters to CREATED)."""
    con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        rows = con.execute(
            "SELECT rowseq, telegram_message_id, telegram_posted_at_utc, raw_text, "
            "raw_text_hash, message_event_type, message_revision_number "
            "FROM prospective_message_evidence "
            "WHERE rowseq > ? AND message_event_type != 'CREATED' ORDER BY rowseq",
            (after_rowseq,)).fetchall()
    finally:
        con.close()
    return [{"rowseq": int(r[0]), "id": int(r[1]), "posted_at": r[2], "raw_text": r[3],
             "raw_text_sha256": r[4], "event_type": r[5], "revision": r[6]} for r in rows]


# ---------------- emission ----------------------------------------------------------------
def proposal_card(setup, constitution, lanes_note):
    """Card WITHOUT OHLC: legs proposed, lanes declared, nothing adjudicated."""
    campaign = {"setup_id": setup["setup_id"], "direction": setup["direction"],
                "zone_low": D(setup["entry_zone"].split("-")[0]),
                "zone_high": D(setup["entry_zone"].split("-")[1]),
                "sl": setup["sl"].split(" ")[0], "signal_ts": 0, "attempt_number": 1, "events": []}
    eng = FollowerEngine(campaign, [], "LANE_A", constitution)
    eng.propose_legs()
    legs = [{"leg_id": l.leg_id, "price": str(l.price), "size": str(l.size), "kind": l.kind,
             "state": "PROPOSED"} for l in eng.legs]
    card = {
        "banner": BANNER, "card_type": "REVIEW_ONLY_SHADOW_PROPOSAL",
        "campaign_id": setup["setup_id"], "revision": setup["revision"],
        "source_timestamp_utc": setup["timestamp_utc"],
        "direction": setup["direction"], "zone": setup["entry_zone"],
        "posted_follower_stop": setup["sl"],
        "constitution_version": constitution["version"],
        "constitution_sha256": sha256_file(CONST_PATH),
        "theoretical_legs": legs,
        "fill_state": {"LANE_A": "NOT_ADJUDICATED (no price data used at proposal time)",
                       "LANE_B": "NOT_ADJUDICATED (no price data used at proposal time)"},
        "management_state": {"instruction_events":
                             setup["management_timing_8c"]["instruction_events"]},
        "strict_follower_status": {"state": "PROPOSED", "note": lanes_note},
        "policy_sensitivity_status": {"state": "PROPOSED",
                                      "disclaimer": "POLICY_SENSITIVITY lane; NOT Farouk's actual result"},
        "unresolved_ambiguities": setup.get("pause_reasons", []),
        "detector_v0_2_label": setup["detector_v0_2_label"],
        "detector_v0_3_label": setup["detector_v0_3"]["review_label"],
        "pre_mark_comparisons": setup["pre_mark_comparison"],
        "evidence_links": {"message_ids": setup["message_ids"],
                           "frozen_evidence_sha256": setup["frozen_evidence_sha256"],
                           "forward_ledger": "forward_validation_ledger_v0_2.jsonl"},
        "acknowledgement_state": "REVIEW",
        "acknowledgement_note": "REVIEW/ACKNOWLEDGED/REJECTED is an annotation with zero execution consequence",
        "review_only": True, "executable": False, "trade_ready": False, "observation_only": True,
    }
    guards.assert_clean(card, f"live card {setup['setup_id']}")
    return card


def write_card(card):
    os.makedirs(CARD_DIR, exist_ok=True)
    base = os.path.join(CARD_DIR, card["campaign_id"])
    tmp = base + ".json.tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(card, fh, indent=1, ensure_ascii=False, default=str)
    os.replace(tmp, base + ".json")
    legs = "\n".join(f"| {l['leg_id'].split('/')[-1]} | {l['price']} | {l['kind']} | {l['state']} |"
                     for l in card["theoretical_legs"])
    evs = "\n".join(f"- {e['timestamp_utc']} msg {e.get('message_id')}: {e['instruction_type']}"
                    f"{' (' + str(e.get('scope')) + ')' if e.get('scope') else ''}"
                    for e in card["management_state"]["instruction_events"]) or "- none yet"
    md = f"""# {card['campaign_id']} — REVIEW-ONLY SHADOW PROPOSAL (rev {card['revision']})

> **{card['banner']}**

| | |
|---|---|
| Source timestamp | {card['source_timestamp_utc']} |
| Direction / zone | **{card['direction']} {card['zone']}** |
| Posted follower stop | {card['posted_follower_stop']} |
| Constitution | {card['constitution_version']} (`{card['constitution_sha256'][:12]}…`) |
| v0.2 / v0.3 label | {card['detector_v0_2_label']} / {card['detector_v0_3_label']} |
| Pre-marks | {', '.join(f"{k.split('-')[1]}:{v}" for k, v in card['pre_mark_comparisons'].items())} |
| Adjudication | NOT ADJUDICATED — proposal uses no price data; results attach on OHLC import |
| Acknowledgement | **{card['acknowledgement_state']}** (annotation only) |

## Theoretical legs (both lanes; LANE A headline)
| leg | price | kind | state |
|---|---|---|---|
{legs}

## Management instructions applied so far
{evs}

Evidence: msgs {card['evidence_links']['message_ids']} · frozen `{card['evidence_links']['frozen_evidence_sha256'][:12]}…`
"""
    tmp2 = base + ".md.tmp"
    with open(tmp2, "w", encoding="utf-8") as fh:
        fh.write(md)
    os.replace(tmp2, base + ".md")


def append_forward(record):
    with guards.ledger_lock(FWD_LEDGER):
        with open(FWD_LEDGER, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")


def follower_ledger_append(kind, setup, extra=None):
    rec = {"record_type": kind, "schema": "follower_ledger_v0_1",
           "setup_id": setup["setup_id"], "revision": setup["revision"],
           "logical_hash": sha256_obj({"k": kind, "sid": setup["setup_id"],
                                       "rev": setup["revision"],
                                       "mids": setup["message_ids"],
                                       "const": sha256_file(CONST_PATH)}),
           "provenance": {"source": "live_wire_v0_1",
                          "emitted_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")},
           "detail": extra or {}, "banner": BANNER,
           "review_only": True, "executable": False, "trade_ready": False, "observation_only": True}
    return guards.append_once(FOLLOWER_LEDGER, rec)


# ---------------- core cycle ---------------------------------------------------------------
def process_message(msg, setups, open_ids, constitution):
    """Handle ONE evidence row. Returns a short action string (for logs/tests)."""
    sid_open = open_ids[-1] if open_ids else None

    if msg["event_type"] != "CREATED" or msg["revision"] != 1:
        # edited/revised Telegram message -> explicit revision record; campaign pauses if affected
        touched = [sid for sid, r in setups.items() if msg["id"] in r.get("message_ids", [])]
        for sid in touched:
            append_forward({"record_type": "XAU_F_CAMPAIGN_PAUSE", "setup_id": sid,
                            "why": f"message {msg['id']} EDITED (revision {msg['revision']}) — "
                                   "fail-closed pending human review",
                            "review_only": True, "executable": False, "trade_ready": False,
                            "observation_only": True})
        return f"EDIT_REVISION_RECORDED({touched or 'no campaign affected'})"

    c = interpreter.classify(msg["raw_text"])
    if c["kind"] == "NOT_FAROUK_GOLD":
        return "IGNORED_NOT_FAROUK_GOLD"
    if c["kind"] == "OTHER":
        return "FAROUK_GOLD_COMMENTARY_NO_ACTION"

    if c["kind"] == "NEEDS_HUMAN_REVIEW":
        append_forward({"record_type": "XAU_F_INTERPRETATION_REVIEW", "message_id": msg["id"],
                        "timestamp_utc": msg["posted_at"], "why": c["why"],
                        "raw_text_sha256": msg["raw_text_sha256"],
                        "review_only": True, "executable": False, "trade_ready": False,
                        "observation_only": True})
        return f"FAIL_CLOSED_REVIEW({c['why']})"

    if c["kind"] == "ENTRY":
        # MORPHOLOGY_EXTENSION_v2 unpriced contract (D-020): an AT_MARKET_UNPRICED entry
        # NEVER creates a campaign and NO zone is synthesised — durable review record only.
        if c.get("entry_pricing") == "AT_MARKET_UNPRICED":
            append_forward({"record_type": "XAU_F_INTERPRETATION_REVIEW", "message_id": msg["id"],
                            "revision": msg["rev"], "why": "ENTRY recognised but AT_MARKET_UNPRICED — "
                            "no entry price stated; no campaign created; no zone synthesised "
                            "(MORPHOLOGY_EXTENSION_v2 contract)",
                            "direction": c.get("direction"), "sl": c.get("sl"),
                            "timestamp_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")})
            return "ENTRY_UNPRICED_REVIEW"
        date = msg["posted_at"][:10].replace("-", "")
        sid = next_setup_id(setups, date)
        setup = interpreter.build_setup_record(sid, msg, c)
        if c.get("zone_degenerate"):
            # DEGENERATE_ZONE flag (operator follow-up 1): mark at source so leg-fill
            # statistics can stratify/exclude these campaigns rather than unpick later
            setup["zone_degenerate"] = True
            setup["notes"] = (setup.get("notes", "") +
                              " | DEGENERATE_ZONE: single-price entry, all legs at one price — "
                              "exclude/stratify in leg-fill statistics")
        if len(open_ids) >= 1 and c.get("reentry_language"):
            setup["notes"] += " | re-entry language detected with an open campaign — flagged for review"
        guards.assert_clean(setup, f"setup {sid}")
        append_forward(setup)
        setups[sid] = setup
        open_ids.append(sid)
        card = proposal_card(setup, constitution, "auto proposal at arrival; adjudication pending OHLC")
        write_card(card)
        follower_ledger_append("FOLLOWER_PROPOSAL", setup,
                               {"legs": [l["price"] for l in card["theoretical_legs"]]})
        return f"PROPOSAL_EMITTED({sid})"

    # MANAGEMENT — hotfix v0.1: correlate ONLY to an open campaign chronologically PROXIMATE to this
    # message. NEVER fall back to a stale campaign (e.g. F001/F002) merely because none is newer.
    if not open_ids:
        append_forward({"record_type": "XAU_F_INTERPRETATION_REVIEW", "message_id": msg["id"],
                        "timestamp_utc": msg["posted_at"],
                        "why": "management instruction with no open campaign",
                        "review_only": True, "executable": False, "trade_ready": False,
                        "observation_only": True})
        return "FAIL_CLOSED_REVIEW(management without open campaign)"
    proximate = [sid for sid in open_ids
                 if _within(_campaign_latest_ts(setups, sid), msg["posted_at"], PROXIMITY_HOURS)]
    if not proximate:
        # stale open campaign(s) only (e.g. a prior-day F002) — NOT a valid fallback target
        append_forward({"record_type": "XAU_F_ORPHAN_MANAGEMENT", "message_id": msg["id"],
                        "timestamp_utc": msg["posted_at"],
                        "why": f"no open campaign within {PROXIMITY_HOURS}h of msg — ORPHAN_MANAGEMENT_MESSAGE "
                               "(never defaults to F001/F002)",
                        "open_campaigns_considered": open_ids,
                        "resolution": "MANUAL_REVIEW_REQUIRED / NO_CAMPAIGN_STATE_MUTATION",
                        "review_only": True, "executable": False, "trade_ready": False,
                        "observation_only": True})
        return "ORPHAN_MANAGEMENT_MESSAGE(no proximate open campaign)"
    if len(proximate) > 1:
        for sid in proximate:
            append_forward({"record_type": "XAU_F_CAMPAIGN_PAUSE", "setup_id": sid,
                            "why": f"two+ proximate open campaigns when msg {msg['id']} arrived — "
                                   "association ambiguous (P02 fail-closed)",
                            "review_only": True, "executable": False, "trade_ready": False,
                            "observation_only": True})
        return "FAIL_CLOSED_REVIEW(ambiguous campaign association)"

    sid_open = proximate[0]
    prev = setups[sid_open]
    # ---- v2.1 (D-028): resolve leg-selective holds against the campaign direction; route
    # informational notes to the record WITHOUT entering the engine instruction stream ----
    engine_ins, info_notes = [], []
    for ins in c["instructions"]:
        if ins.get("informational"):
            info_notes.append(ins)
            continue
        if ins["instruction_type"] == "HOLD_LEG_SELECTIVE":
            d, sel = prev.get("direction"), ins.get("selector")
            if (d == "LONG" and sel == "LOWEST") or (d == "SHORT" and sel == "HIGHEST"):
                engine_ins.append(dict(ins, instruction_type="HOLD_BEST",
                                       resolved_from=f"HOLD_LEG_SELECTIVE:{sel}",
                                       resolution_note=f"{sel} = best entry for {d} — deterministic"))
            else:
                append_forward({"record_type": "XAU_F_INTERPRETATION_REVIEW", "message_id": msg["id"],
                                "timestamp_utc": msg["posted_at"],
                                "why": f"leg-selective hold ({sel}) unresolvable against campaign "
                                       f"direction {d} — fail closed, no state change",
                                "review_only": True, "executable": False, "trade_ready": False,
                                "observation_only": True})
                return f"FAIL_CLOSED_REVIEW(leg-selective hold {sel} vs {d})"
        else:
            engine_ins.append(ins)
    if not engine_ins:
        # informational-only management (e.g. a stated TP level): durable record, no state change
        append_forward({"record_type": "XAU_F_INTERPRETATION_REVIEW", "message_id": msg["id"],
                        "timestamp_utc": msg["posted_at"],
                        "why": "informational-only management note — recorded, no state change: "
                               + "; ".join(f"{n['instruction_type']}={n.get('level', n.get('tp_index'))}"
                                           for n in info_notes),
                        "review_only": True, "executable": False, "trade_ready": False,
                        "observation_only": True})
        return "INFORMATIONAL_NOTE_RECORDED"
    new = json.loads(json.dumps(prev, default=str))
    new["revision"] = prev["revision"] + 1
    new["message_ids"] = prev["message_ids"] + [msg["id"]]
    for ins in engine_ins:
        new["management_timing_8c"]["instruction_events"].append(
            dict(ins, message_id=msg["id"], timestamp_utc=msg["posted_at"]))
    if info_notes:
        new["notes"] = (new.get("notes", "") + " | INFO(" + str(msg["id"]) + "): "
                        + "; ".join(f"{n['instruction_type']}={n.get('level', n.get('tp_index'))}"
                                    for n in info_notes))
    guards.assert_clean(new, f"setup rev {new['revision']}")
    append_forward(new)
    setups[sid_open] = new
    if any(i["instruction_type"] in ("FINAL_CLOSE", "EXPLICIT_FULL_EXIT") for i in c["instructions"]):
        open_ids.remove(sid_open)
    card = proposal_card(new, constitution, "management update; adjudication pending OHLC")
    write_card(card)
    follower_ledger_append("FOLLOWER_PROPOSAL_UPDATE", new,
                           {"new_instructions": c["instructions"], "message_id": msg["id"]})
    return f"CARD_UPDATED({sid_open} rev {new['revision']})"


def run_cycle(db_path=EVIDENCE_DB):
    guards.assert_constitution_frozen()           # byte-pin enforced every cycle
    constitution = json.load(open(CONST_PATH, encoding="utf-8"))
    if constitution.get("status") != "RATIFIED":
        raise guards.GuardViolation("constitution not ratified — live wire refuses to run")
    cur = load_cursor()
    setups, open_ids, _ = load_campaign_state()
    actions = []
    for msg in new_messages(cur["last_processed_id"], db_path):
        key = f"{msg['id']}/{msg['revision']}"
        try:
            act = process_message(msg, setups, open_ids, constitution)
            actions.append((key, act))
            cur["last_processed_id"] = max(cur["last_processed_id"], msg["id"])
            cur["fail_counts"].pop(key, None)
            save_cursor(cur)
            log(f"msg {key}: {act}")
        except Exception as e:                                    # noqa: BLE001
            n = cur["fail_counts"].get(key, 0) + 1
            cur["fail_counts"][key] = n
            save_cursor(cur)
            log(f"msg {key}: ERROR ({type(e).__name__}: {e}) attempt {n}/3 — cursor held, will retry")
            if n >= 3:
                append_forward({"record_type": "XAU_F_INTERPRETATION_REVIEW", "message_id": msg["id"],
                                "why": f"live-wire processing failed 3x ({type(e).__name__}); "
                                       "skipped — raw evidence preserved in prospective store",
                                "review_only": True, "executable": False, "trade_ready": False,
                                "observation_only": True})
                cur["last_processed_id"] = max(cur["last_processed_id"], msg["id"])
                cur["fail_counts"].pop(key, None)
                save_cursor(cur)
                actions.append((key, "FAILED_NEEDS_HUMAN_REVIEW"))
            break                                                 # stop cycle; retry next tick

    # v2.2 edit sweep — rowseq-cursored so edits of already-processed ids are seen
    for erow in new_edit_rows(cur["last_edit_rowseq"], db_path):
        ekey = f"edit:{erow['rowseq']}({erow['id']}/r{erow['revision']})"
        try:
            act = process_message(erow, setups, open_ids, constitution)
            actions.append((ekey, act))
            cur["last_edit_rowseq"] = max(cur["last_edit_rowseq"], erow["rowseq"])
            cur["fail_counts"].pop(ekey, None)
            save_cursor(cur)
            log(f"msg {ekey}: {act}")
        except Exception as e:                                    # noqa: BLE001
            n = cur["fail_counts"].get(ekey, 0) + 1
            cur["fail_counts"][ekey] = n
            save_cursor(cur)
            log(f"msg {ekey}: ERROR ({type(e).__name__}: {e}) attempt {n}/3 — cursor held, will retry")
            if n >= 3:
                append_forward({"record_type": "XAU_F_INTERPRETATION_REVIEW", "message_id": erow["id"],
                                "why": f"edit-sweep processing failed 3x ({type(e).__name__}); "
                                       "skipped — raw evidence preserved in prospective store",
                                "review_only": True, "executable": False, "trade_ready": False,
                                "observation_only": True})
                cur["last_edit_rowseq"] = max(cur["last_edit_rowseq"], erow["rowseq"])
                cur["fail_counts"].pop(ekey, None)
                save_cursor(cur)
                actions.append((ekey, "FAILED_NEEDS_HUMAN_REVIEW"))
            break                                                 # stop sweep; retry next tick
    return actions


def watch(interval=30):
    try:
        fd = os.open(INSTANCE_LOCK, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        os.write(fd, str(os.getpid()).encode())
        os.close(fd)
    except FileExistsError:
        raise SystemExit("another live_wire instance holds the lock — refusing to start")
    log(f"live wire WATCH started pid={os.getpid()} interval={interval}s | {BANNER}")
    import hashlib as _hl
    _ih = _hl.sha256(open(interpreter.__file__, "rb").read()).hexdigest()
    _wh = _hl.sha256(open(os.path.abspath(__file__), "rb").read()).hexdigest()
    log(f"HOTFIX v0.1 LOADED | interpreter_sha={_ih[:16]} live_wire_sha={_wh[:16]} | "
        f"PROXIMITY_HOURS={PROXIMITY_HOURS} | parser-morphology + no-F001/F002-fallback active")
    log("listener is a separate process and is NEVER touched by this wire")
    try:
        while True:
            try:
                run_cycle()
            except Exception as e:                                # noqa: BLE001
                log(f"cycle error: {type(e).__name__}: {e} — listener unaffected; retrying next tick")
            time.sleep(interval)
    finally:
        os.remove(INSTANCE_LOCK)


if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    if "--watch" in sys.argv:
        watch()
    else:
        for k, a in run_cycle():
            print(k, a)
        print("single cycle complete")
