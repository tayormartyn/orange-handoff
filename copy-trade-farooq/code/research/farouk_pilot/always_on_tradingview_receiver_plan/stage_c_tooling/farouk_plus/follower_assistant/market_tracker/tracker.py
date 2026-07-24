"""Stage-1.5 LIVE SHADOW MARKET TRACKER — separate process, read-only inputs, review-only outputs.

NO BROKER ACTION. NO ORDER SUBMISSION. REVIEW-ONLY SHADOW PROPOSAL.

Process rules:
  * separate from module_a_telegram.py (PID untouched) and live_wire.py (PID untouched);
    never blocks or restarts either; failure here cannot affect capture or proposals.
  * one authoritative writer (this process) for tracker_ledger_v0_1.jsonl, guarded by an
    instance lock + guards.append_once (exact-hash idempotent, locked).
  * durable cursor (tracker_cursor.json, atomic replace) + restart-safe reconstruction:
    campaign state is RECOMPUTED from the forward ledger + bar stream every cycle, so a
    restart loses nothing.
  * bounded retry (3) then poison-event quarantine (quarantine_v0_1.jsonl) — a bad bar or
    campaign can never stall the loop.
  * cards are regenerated atomically (tmp + os.replace) in the SAME cards/ directory —
    one card system, extended fields.

Modes:  --mode replay --csv <path> [--until <epoch>]   (MODE 1: frozen, deterministic)
        --mode file_tail --csv <path>                  (MODE 2: growing/replaced export)
        --mode live_dukascopy                          (MODE 3: delayed public datafeed,
                                                        existing proven adapter, no credentials)
"""
from __future__ import annotations

import argparse
import io
import json
import os
import sys
import time
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
PARENT = os.path.dirname(HERE)
for p in (HERE, PARENT):
    if p not in sys.path:
        sys.path.insert(0, p)
import guards                                                      # noqa: E402
import live_wire                                                   # noqa: E402  (reused loaders only)
import run_fixtures                                                # noqa: E402  (campaign_from_setup)
import tracker_engine                                              # noqa: E402
from market_events import BarStream, MarketEventError              # noqa: E402
from providers import (ReplayCSVProvider, FileTailProvider, DukascopyBarProvider,  # noqa: E402
                       R2TvBarProvider)

TRACKER_LEDGER = os.path.join(HERE, "tracker_ledger_v0_1.jsonl")
QUARANTINE = os.path.join(HERE, "quarantine_v0_1.jsonl")
CURSOR = os.path.join(HERE, "tracker_cursor.json")
INGEST_LOG = os.path.join(HERE, "ingestion_log_v0_1.jsonl")
INSTANCE_LOCK = os.path.join(HERE, "tracker.instance.lock")
CONST = os.path.join(PARENT, "follower_constitution_v0_1.json")
CARD_DIR = os.path.join(PARENT, "cards")
BANNER = tracker_engine.BANNER


def log(msg):
    print(f"[{datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}] {msg}", flush=True)


def load_cursor():
    if os.path.exists(CURSOR):
        return json.load(open(CURSOR, encoding="utf-8"))
    return {"after_ts": 0, "snapshot_hashes": {}, "fail_counts": {}}


def save_cursor(cur):
    tmp = CURSOR + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(cur, fh, indent=1)
    os.replace(tmp, CURSOR)


def quarantine(kind, detail):
    with open(QUARANTINE, "a", encoding="utf-8") as fh:
        fh.write(json.dumps({"at_utc": datetime.now(timezone.utc).isoformat(),
                             "kind": kind, "detail": str(detail)[:500]}) + "\n")


def write_card(setup, snapshot):
    os.makedirs(CARD_DIR, exist_ok=True)
    base = os.path.join(CARD_DIR, setup["setup_id"])
    a = snapshot["lanes"]["LANE_A"]
    b = snapshot["lanes"]["LANE_B"]
    card = {
        "banner": BANNER, "card_type": "REVIEW_ONLY_SHADOW_PROPOSAL",
        "campaign_id": setup["setup_id"], "direction": snapshot["direction"],
        "zone": snapshot["zone"], "posted_follower_stop": setup["sl"],
        "source_timestamp_utc": setup.get("timestamp_utc"),
        "evidence_links": {"message_ids": setup.get("message_ids", []),
                           "frozen_evidence_sha256": setup.get("frozen_evidence_sha256"),
                           "forward_ledger": "forward_validation_ledger_v0_2.jsonl",
                           "tracker_ledger": "market_tracker/tracker_ledger_v0_1.jsonl"},
        "constitution_sha256": guards.CONSTITUTION_SHA,
        "acknowledgement_note": "REVIEW/ACKNOWLEDGED/REJECTED is an annotation with zero execution consequence",
        "constitution_version": "0.1.0",
        "theoretical_legs": a["engine"]["legs"],
        "campaign_average_entry": a["engine"]["average_entry"],
        "market_data": snapshot["market"],
        "current_theoretical_open_size": a["lifecycle"]["open_size"],
        "strict_follower_lane": {"lifecycle": a["lifecycle"]["current"],
                                 "path": a["lifecycle"]["path"],
                                 "state": a["engine"]["campaign_state"],
                                 "realized_pips_per_unit": a["engine"]["realized_pips_per_unit"],
                                 "unrealized_pips_per_unit": a["engine"]["unrealized_pips_per_unit"],
                                 "mae_pips": a["mae_pips"], "mfe_pips": a["mfe_pips"]},
        "policy_sensitivity_lane": {"lifecycle": b["lifecycle"]["current"],
                                    "state": b["engine"]["campaign_state"],
                                    "realized_pips_per_unit": b["engine"]["realized_pips_per_unit"],
                                    "unrealized_pips_per_unit": b["engine"]["unrealized_pips_per_unit"],
                                    "mae_pips": b["mae_pips"], "mfe_pips": b["mfe_pips"],
                                    "disclaimer": snapshot["lane_b_disclaimer"]},
        "management_instructions": setup["management_timing_8c"]["instruction_events"],
        "unresolved_ambiguities": a["ambiguities"],
        "plus50_diagnostic": a["plus50_diagnostic"],
        "last_state_transition": a["lifecycle"]["current"],
        "outcome_status": ("FROZEN" if a["lifecycle"]["current"] == "OUTCOME_FROZEN"
                           else a["engine"]["follow_through"]),
        "detector_v0_2_label": setup.get("detector_v0_2_label"),
        "detector_v0_3_label": setup.get("detector_v0_3", {}).get("review_label"),
        "pre_mark_comparisons": setup.get("pre_mark_comparison"),
        "acknowledgement_state": "REVIEW",
        "review_only": True, "executable": False, "trade_ready": False, "observation_only": True,
    }
    guards.assert_clean(card, f"tracker card {setup['setup_id']}")
    tmp = base + ".json.tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(card, fh, indent=1, ensure_ascii=False, default=str)
    os.replace(tmp, base + ".json")
    legs = "\n".join(f"| {l['leg_id'].split('/')[-1]} | {l['price']} | {l['kind']} | {l['state']} | "
                     f"{l['fill_price'] or '—'} | {l['open_size']} | {l['be_price'] or '—'} |"
                     for l in card["theoretical_legs"])
    amb = "\n".join(f"- {x['class']} @ bar {x['bar_ts']} ({x.get('event', x.get('note', ''))})"
                    for x in card["unresolved_ambiguities"]) or "- none"
    md = f"""# {card['campaign_id']} — LIVE SHADOW TRACKER (REVIEW-ONLY)

> **NO BROKER ACTION | NO ORDER SUBMISSION | REVIEW-ONLY SHADOW PROPOSAL**

| | |
|---|---|
| Direction / zone | **{card['direction']} {card['zone']}** |
| Posted stop | {card['posted_follower_stop']} |
| Provider / freshness | {card['market_data']['provider']} · last bar {card['market_data']['last_bar_ts']} · stale {card['market_data']['staleness_seconds']}s |
| Last close | {card['market_data']['last_close']} (dist to near edge: {card['market_data']['distance_to_near_edge_pips']} pips) |
| Average entry | {card['campaign_average_entry'] or '—'} |
| Open size | {card['current_theoretical_open_size']} |
| Lifecycle (strict) | **{card['strict_follower_lane']['lifecycle']}** |
| Strict realized / unrealized | {card['strict_follower_lane']['realized_pips_per_unit']} / {card['strict_follower_lane']['unrealized_pips_per_unit'] or '—'} pips/unit |
| Strict MAE / MFE | {card['strict_follower_lane']['mae_pips'] or '—'} / {card['strict_follower_lane']['mfe_pips'] or '—'} pips |
| Sensitivity lane | {card['policy_sensitivity_lane']['lifecycle']} · {card['policy_sensitivity_lane']['realized_pips_per_unit']} / {card['policy_sensitivity_lane']['unrealized_pips_per_unit'] or '—'} pips/unit (NOT Farouk's result) |
| v0.2 / v0.3 | {card['detector_v0_2_label']} / {card['detector_v0_3_label']} |
| Outcome | {card['outcome_status']} |
| Acknowledgement | {card['acknowledgement_state']} (annotation only) |

## Legs (strict lane)
| leg | price | kind | state | fill | open | BE |
|---|---|---|---|---|---|---|
{legs}

## Management instructions
{chr(10).join('- ' + e['timestamp_utc'] + ' msg ' + str(e.get('message_id')) + ': ' + e['instruction_type'] for e in card['management_instructions']) or '- none'}

## Ambiguities
{amb}
"""
    tmp2 = base + ".md.tmp"
    with open(tmp2, "w", encoding="utf-8") as fh:
        fh.write(md)
    os.replace(tmp2, base + ".md")


def run_cycle(provider, stream, cur, now_ts=None):
    """One deterministic cycle. Returns list of (setup_id, lifecycle, appended)."""
    now_ts = now_ts or int(time.time())
    guards.assert_constitution_frozen()           # byte-pin enforced EVERY cycle (finding 6)
    constitution = json.load(open(CONST, encoding="utf-8"))
    if constitution.get("status") != "RATIFIED":
        raise guards.GuardViolation("constitution not ratified — tracker refuses to run")
    # 1) ingest new completed bars (validated per-row; a poison row is quarantined ONCE and
    #    can never stall ingestion — red-team finding 2)
    try:
        for bar in provider.fetch_completed_bars(cur["after_ts"]):
            try:
                stream.ingest(bar)
            except MarketEventError as e:
                quarantine("MARKET_EVENT", e)
            cur["after_ts"] = max(cur["after_ts"], bar.event_ts)
        # providers that resolve gaps definitively advance the cursor past them
        cur["after_ts"] = max(cur["after_ts"], getattr(provider, "cursor_hint", 0))
        for err in getattr(provider, "row_errors", []) or []:
            k = f"row:{err}"
            if k not in cur.setdefault("quarantined", []):
                cur["quarantined"].append(k)
                quarantine("MARKET_ROW", err)
    except Exception as e:                                        # noqa: BLE001
        quarantine("MARKET_FETCH", e)
    # 2) recompute every open campaign from scratch (restart-safe determinism)
    setups, open_ids, paused = live_wire.load_campaign_state()
    results = []
    for sid, rec in sorted(setups.items()):
        if rec.get("record_type") != "XAU_F_SETUP":
            continue
        key = f"{sid}"
        if key in cur.get("skipped_campaigns", []):
            continue                                              # quarantined for good (finding 12)
        try:
            campaign = run_fixtures.campaign_from_setup(rec)
            snap = tracker_engine.track(rec, campaign, stream, constitution, now_ts,
                                        provider.name)
            prev = cur["snapshot_hashes"].get(sid)
            appended = False
            if snap["logical_hash"] != prev:
                ledger_rec = {"record_type": "TRACKER_SNAPSHOT", "schema": "tracker_ledger_v0_1",
                              "setup_id": sid, "logical_hash": snap["logical_hash"],
                              "snapshot": snap,
                              "review_only": True, "executable": False, "trade_ready": False,
                              "observation_only": True}
                appended = guards.append_once(TRACKER_LEDGER, ledger_rec)
                write_card(rec, snap)
                cur["snapshot_hashes"][sid] = snap["logical_hash"]
                save_cursor(cur)
            cur["fail_counts"].pop(key, None)
            results.append((sid, snap["lanes"]["LANE_A"]["lifecycle"]["current"], appended))
        except Exception as e:                                     # noqa: BLE001
            n = cur["fail_counts"].get(key, 0) + 1
            cur["fail_counts"][key] = n
            save_cursor(cur)
            log(f"{sid}: ERROR {type(e).__name__}: {e} (attempt {n}/3)")
            if n >= 3:
                quarantine("CAMPAIGN", f"{sid}: {type(e).__name__}: {e}")
                cur["fail_counts"].pop(key, None)
                cur.setdefault("skipped_campaigns", []).append(key)   # skip for good (finding 12)
                save_cursor(cur)
    save_cursor(cur)
    return results


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["replay", "file_tail", "live_dukascopy", "live_tv_bars"],
                    required=True)
    ap.add_argument("--csv")
    ap.add_argument("--until", type=int, default=None)
    ap.add_argument("--interval", type=int, default=60)
    ap.add_argument("--once", action="store_true")
    args = ap.parse_args()

    if args.mode == "replay":
        provider = ReplayCSVProvider(args.csv, clamp_end_ts=args.until)
    elif args.mode == "file_tail":
        provider = FileTailProvider(args.csv)
    elif args.mode == "live_tv_bars":
        worker_dir = os.path.join(guards.ST_ROOT, "research", "farouk_pilot",
                                  "always_on_tradingview_receiver_plan", "cloud_worker_dark")
        provider = R2TvBarProvider(worker_dir)
    else:
        provider = DukascopyBarProvider(guards.ST_ROOT)

    try:
        fd = os.open(INSTANCE_LOCK, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        os.write(fd, str(os.getpid()).encode())
        os.close(fd)
    except FileExistsError:
        raise SystemExit("another tracker instance holds the lock — refusing to start")
    log(f"tracker started pid={os.getpid()} mode={args.mode} | {BANNER}")
    log("listener PID and live-wire PID are separate processes and are NEVER touched")
    stream = BarStream(INGEST_LOG)
    restored = stream.restore()                   # rebuild full bar history (red-team CRITICAL 1)
    cur = load_cursor()
    if restored:
        log(f"restart recovery: {restored} bars restored from ingestion log "
            f"(stream max ts {stream.max_ts}, cursor after_ts {cur['after_ts']})")
    elif cur["after_ts"] > 0:
        # cursor without history would replay campaigns on a truncated window — refuse
        log("WARNING: cursor is ahead but ingestion log restored 0 bars — resetting after_ts "
            "to 0 so the provider re-fetches (BarStream dedups)")
        cur["after_ts"] = 0
        save_cursor(cur)
    try:
        while True:
            try:
                for sid, life, app in run_cycle(provider, stream, cur):
                    log(f"{sid}: {life} (ledger append={app})")
            except Exception as e:                                 # noqa: BLE001
                log(f"cycle error: {type(e).__name__}: {e} — capture/proposal processes unaffected")
                quarantine("CYCLE", e)
            if args.once:
                break
            time.sleep(args.interval)
    finally:
        os.remove(INSTANCE_LOCK)


if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    main()
