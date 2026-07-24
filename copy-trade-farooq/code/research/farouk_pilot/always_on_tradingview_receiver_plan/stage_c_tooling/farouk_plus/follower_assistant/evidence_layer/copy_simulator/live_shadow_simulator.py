"""LIVE SHADOW COPY-SIMULATOR COMPANION v0.1 — sixth independent READ-ONLY process (RESEARCH-ONLY /
SIMULATION_ONLY / NO_BROKER_EXECUTION). Observes authentic GENUINE_PROSPECTIVE Farouk XAUUSD freezes
and shadow-simulates the frozen Lane A (Constitution v0.1) lifecycle on completed market bars, writing
separate append-only live-shadow ledgers + copy-fidelity telemetry.

It never places/modifies/cancels/reconciles a real broker order, holds no credentials, sizes nothing,
touches no gate, and never modifies the listener / wire / tracker / evidence-watcher / outcome-companion.
Every record: SIMULATION_ONLY, NO_BROKER_EXECUTION, eligible_for_training=false,
eligible_for_performance_attribution=false.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import sys
import time
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
EVDIR = os.path.dirname(HERE)
FA = os.path.dirname(EVDIR)
MT = os.path.join(EVDIR, "market_tracker")
for p in (HERE, EVDIR, FA, MT):
    if p not in sys.path:
        sys.path.insert(0, p)
import copy_execution_simulator as SIM                           # noqa: E402
import reconciliation as RC                                      # noqa: E402
import copy_fidelity_metrics as FID                              # noqa: E402

BANNER = "LIVE SHADOW COPY-SIMULATOR | RESEARCH/SIMULATION ONLY | NO BROKER | NO EXECUTION | NO MODEL FIT"
FREEZE_LEDGER = os.path.join(EVDIR, "router_freeze_v0_1.jsonl")           # GENUINE freezes
INGEST_LOG = os.path.join(MT, "ingestion_log_v0_1.jsonl")
MGMT_LEDGER = os.path.join(EVDIR, "management_snapshots_v0_1.jsonl")
CAMP_LEDGER = os.path.join(HERE, "live_shadow_campaigns_v0_1.jsonl")
EVENT_LEDGER = os.path.join(HERE, "live_shadow_events_v0_1.jsonl")
RECON_LEDGER = os.path.join(HERE, "live_shadow_reconciliation_v0_1.jsonl")
FID_LEDGER = os.path.join(HERE, "live_shadow_fidelity_v0_1.jsonl")
CURSOR = os.path.join(HERE, "live_shadow_cursor_v0_1.json")
LOCK = os.path.join(HERE, "live_shadow.instance.lock")

GENUINE = "GENUINE_PROSPECTIVE"
# forbidden classes for the AUTHENTIC live path (isolated / rejected)
REJECT_CLASSES = {"SCHEMA_BACKFILL_NOT_PROSPECTIVE", "SYNTHETIC_INTEGRATION_TEST",
                  "TECHNICAL_FIXTURE_NOT_EDGE_EVIDENCE", "UNTOUCHED_WINDOW_RESEARCH",
                  "ACTIVATION_STRADDLE", "HISTORICAL_REPLAY"}


def log(m):
    print(f"[{datetime.now(timezone.utc):%Y-%m-%dT%H:%M:%SZ}] {m}", flush=True)


def module_content_sha256():
    return hashlib.sha256(open(os.path.abspath(__file__), "rb").read()).hexdigest()


def _load(ledger):
    out = []
    if os.path.exists(ledger):
        for line in open(ledger, encoding="utf-8"):
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return out


def load_cursor(path=CURSOR):
    if os.path.exists(path):
        try:
            return json.load(open(path, encoding="utf-8"))
        except Exception:                                        # noqa: BLE001
            return {"done": {}}
    return {"done": {}}


def save_cursor(cur, path=CURSOR):
    tmp = path + ".tmp"
    json.dump(cur, open(tmp, "w", encoding="utf-8"), indent=1)
    os.replace(tmp, path)


def _iso_epoch(s):
    try:
        return int(datetime.fromisoformat(str(s).replace("Z", "+00:00")).timestamp())
    except Exception:                                            # noqa: BLE001
        return None


def proposal_from_freeze(fz):
    np = fz["hash_envelope"]["normalized_proposal"]
    env = fz["hash_envelope"]
    raw = env.get("raw_source_ref") or {}
    receipt = _iso_epoch(raw.get("source_message_utc")) if isinstance(raw, dict) else None
    return {"campaign_id": np["setup_id"], "direction": np["direction"], "zone_low": np["zone_low"],
            "zone_high": np["zone_high"], "sl": np["posted_stop"],
            "decision_ts": int(env["decision_timestamp"]),
            "receipt_ts": receipt if receipt is not None else int(env["decision_timestamp"]),
            "source_message_hash": (raw.get("pretrade_logical_hash") if isinstance(raw, dict) else "UNKNOWN"),
            "proposal_version": fz.get("router_version", "v0"), "market_data_source": "PEPPERSTONE_1M"}


def bars_from_ingest(path=INGEST_LOG):
    try:
        from market_events import BarStream
        s = BarStream()
        if os.path.exists(path):
            s.log_path = path
            s.restore()
        return s.ordered_tuples()
    except Exception:                                            # noqa: BLE001
        return []


_MGMT_MAP = {"SL_TO_ENTRY": "SL_TO_ENTRY", "TAKE_PCT_OFF": "TAKE_PCT", "TP1_TAKE": "TAKE_PCT",
             "CLOSE_WORST": "CLOSE_WORST", "HOLD_BEST": "HOLD_BEST", "FINAL_CLOSE": "FINAL_CLOSE",
             "RISK_OFF": "RISK_OFF"}


def instructions_from_mgmt(sid, mgmt_ledger=MGMT_LEDGER):
    out = []
    for r in _load(mgmt_ledger):
        if r.get("record_type") != "MANAGEMENT_SNAPSHOT" or r.get("setup_id") != sid:
            continue
        ins = r.get("instruction_interpretation") or {}
        itype = ins.get("instruction_type") if isinstance(ins, dict) else None
        ts = _iso_epoch(r.get("source_ts") or r.get("timestamp_utc"))
        mapped = _MGMT_MAP.get(itype)
        if mapped and ts is not None:
            entry = {"type": mapped, "ts": ts}
            if mapped == "TAKE_PCT" and isinstance(ins, dict) and ins.get("pct") is not None:
                entry["pct"] = ins["pct"]
            out.append(entry)
    return out


def _idem(sid, fhash, profile):
    return hashlib.sha256(f"{sid}|{fhash}|{profile}|live_shadow_v0_1".encode()).hexdigest()


def _stamp(rec, rclass):
    rec.update({"SIMULATION_ONLY": True, "NO_BROKER_EXECUTION": True, "record_class": rclass,
                "eligible_for_training": False, "eligible_for_performance_attribution": False,
                "canonical_utc_ts": int(time.time()), "review_only": True, "observation_only": True})
    return rec


def _append(path, rec):
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, default=str) + "\n")


def run_cycle(*, freeze_ledger=FREEZE_LEDGER, bars=None, instructions_for=None,
              ledgers=None, cursor_path=CURSOR, record_class_override=None,
              profiles=("LANE_A_CONSTITUTION_V0_1",), cost_scenario="ZERO_COST", cost_cfg=None):
    """One live-shadow pass. Authentic path: GENUINE_PROSPECTIVE + prospective-eligible only. Fail-closed."""
    L = ledgers or {"camp": CAMP_LEDGER, "events": EVENT_LEDGER, "recon": RECON_LEDGER, "fid": FID_LEDGER}
    cur = load_cursor(cursor_path)
    actions = []
    if bars is None:
        bars = bars_from_ingest()
    for fz in _load(freeze_ledger):
        if fz.get("record_type") != "ROUTER_FREEZE":
            continue
        try:
            sid = fz["setup_id"]
            fhash = fz["logical_hash"]
            rclass = record_class_override or SIM_normalize(fz.get("record_class"))
            # AUTHENTIC gate: reject non-genuine unless a test override is set
            if record_class_override is None:
                if rclass in REJECT_CLASSES or rclass != GENUINE or not fz.get("eligible_for_prospective_evidence"):
                    continue
            prop = proposal_from_freeze(fz)
            ins = (instructions_for(sid) if instructions_for else instructions_from_mgmt(sid))
            for profile in profiles:
                tag = f"{fhash}:{profile}"
                if cur["done"].get(tag):
                    continue
                sim = SIM.simulate(prop, bars, ins, profile=profile, cost_scenario=cost_scenario, cost_cfg=cost_cfg)
                recon = RC.reconcile(sim["events"], final_legs=sim["legs"])
                fidel = FID.campaign_fidelity(sim)
                idem = _idem(sid, fhash, profile)
                _append(L["camp"], _stamp({"record_type": "LIVE_SHADOW_CAMPAIGN", "campaign_id": sid,
                                           "source_event_hash": prop["source_message_hash"], "lane_a_proposal_hash": fhash,
                                           "simulator_version": SIM.SIM_VERSION, "constitution_version": SIM.CONSTITUTION_VERSION,
                                           "market_data_source": prop["market_data_source"], "profile": profile,
                                           "cost_scenario": cost_scenario, "idempotency_key": idem, "campaign": sim}, rclass))
                for e in sim["events"]:
                    _append(L["events"], _stamp({"record_type": "LIVE_SHADOW_EVENT", "campaign_id": sid,
                                                 "lane_a_proposal_hash": fhash, "profile": profile,
                                                 "idempotency_key": _idem(sid, fhash, profile) + ":" + e.get("idempotency_key", ""),
                                                 "event": e}, rclass))
                _append(L["recon"], _stamp({"record_type": "LIVE_SHADOW_RECONCILIATION", "campaign_id": sid,
                                            "lane_a_proposal_hash": fhash, "profile": profile,
                                            "idempotency_key": idem + ":recon", "reconciliation": recon}, rclass))
                _append(L["fid"], _stamp({"record_type": "LIVE_SHADOW_FIDELITY", "campaign_id": sid,
                                          "lane_a_proposal_hash": fhash, "profile": profile,
                                          "idempotency_key": idem + ":fid", "fidelity": fidel}, rclass))
                cur["done"][tag] = idem
                actions.append(f"LIVE_SHADOW_SIMULATED({sid} profile={profile} recon={recon['status']})")
        except Exception as e:                                    # noqa: BLE001
            actions.append(f"LIVE_SHADOW_ERROR({fz.get('setup_id')}: {type(e).__name__}) — live processes unaffected")
    save_cursor(cur, cursor_path)
    return actions


def SIM_normalize(rc):
    return "GENUINE_PROSPECTIVE" if rc in ("PROSPECTIVE", "GENUINE_PROSPECTIVE") else rc


def watch(interval=60):
    try:
        fd = os.open(LOCK, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        os.write(fd, str(os.getpid()).encode()); os.close(fd)
    except FileExistsError:
        raise SystemExit("another live_shadow_simulator holds the lock — refusing to start")
    log(f"live shadow simulator started pid={os.getpid()} | {BANNER}")
    log(f"SHADOW MODULE SHA {module_content_sha256()[:16]} | LANE_A_PUBLISHED_FOLLOWER_SEMANTICS = FROZEN_AND_KNOWN")
    log(f"constitution {SIM.CONSTITUTION_SHA[:16]} | simulator {SIM.SIM_VERSION} | genuine freeze ledger: {FREEZE_LEDGER}")
    log("listener/wire/tracker/evidence-watcher/outcome-companion are separate processes and are NEVER touched")
    try:
        while True:
            try:
                for a in run_cycle():
                    log(a)
            except Exception as e:                                # noqa: BLE001
                log(f"cycle error: {type(e).__name__}: {e} — live processes unaffected")
            time.sleep(interval)
    finally:
        os.remove(LOCK)


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
