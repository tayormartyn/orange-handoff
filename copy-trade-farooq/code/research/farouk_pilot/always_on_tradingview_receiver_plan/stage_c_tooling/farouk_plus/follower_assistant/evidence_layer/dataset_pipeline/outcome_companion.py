"""OUTCOME COMPANION — independent process that turns immutable GENUINE freeze records into outcome
evidence + dataset rows (RESEARCH-ONLY). Separate from the evidence watcher / listener / wire /
tracker; it never touches them, never edits a freeze, places no order, accesses no credential, alters
no gate, fits no model.

Discovery loop (self-driven; no direct outcome-engine call from outside):
  read GENUINE freeze ledger -> for each GENUINE_PROSPECTIVE + prospective-eligible freeze not yet
  done: if authoritative closure evidence exists -> attach exactly one outcome (routed to the genuine
  outcome ledger) + regenerate the versioned dataset; else register PENDING and wait. Fail-closed.
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
EVDIR = os.path.dirname(HERE)
FA = os.path.dirname(EVDIR)
MT = os.path.join(EVDIR, "market_tracker")
for p in (HERE, EVDIR, FA, MT):
    if p not in sys.path:
        sys.path.insert(0, p)
import outcome_pipeline as OP                                    # noqa: E402
import dataset_generator as DG                                   # noqa: E402

BANNER = "OUTCOME COMPANION | RESEARCH/CAPTURE ONLY | NO BROKER | NO EXECUTION | NO MODEL FIT"
FREEZE_LEDGER = os.path.join(EVDIR, "router_freeze_v0_1.jsonl")           # GENUINE freezes
BACKFILL_FREEZE_LEDGER = os.path.join(EVDIR, "router_freeze_backfill_v0_1.jsonl")
CURSOR = os.path.join(HERE, "outcome_companion_cursor.json")
LOCK = os.path.join(HERE, "outcome_companion.instance.lock")
DATASET_DIR = os.path.join(HERE, "exports")


def log(m):
    print(f"[{datetime.now(timezone.utc):%Y-%m-%dT%H:%M:%SZ}] {m}", flush=True)


def module_content_sha256():
    import hashlib
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
            return {"done": {}, "pending": []}
    return {"done": {}, "pending": []}


def save_cursor(cur, path=CURSOR):
    tmp = path + ".tmp"
    json.dump(cur, open(tmp, "w", encoding="utf-8"), indent=1)
    os.replace(tmp, path)


def default_closure_fn(forward_ledger):
    """Authoritative closure oracle from the durable forward ledger: a campaign is COMPLETE only when a
    genuine outcome/adjudication marker exists; observation_cutoff = that marker's bar/ts. Returns
    (is_complete, observation_cutoff) or (False, None). Never invents closure."""
    recs = _load(forward_ledger)

    def closure_for(sid):
        cutoff = None
        complete = False
        for r in recs:
            if r.get("setup_id") == sid and r.get("record_type") in ("XAU_F_PARTIAL_MATCH", "TRACKER_SNAPSHOT", "XAU_F_OUTCOME"):
                complete = True
                c = r.get("observation_cutoff") or r.get("last_bar_ts") or r.get("timestamp_epoch")
                if isinstance(c, int):
                    cutoff = max(cutoff or 0, c)
        return complete, cutoff
    return closure_for


def run_cycle(*, freeze_ledger=FREEZE_LEDGER, outcome_ledger=None, bars=None, closure_fn=None,
              dataset_dir=DATASET_DIR, cursor_path=CURSOR, extra_freeze_ledgers=None,
              source_provenance_override=None):
    """One companion pass. GENUINE-only for the automated path. Fail-closed per-campaign.

    source_provenance_override (integration harness only): forces the outcome's source_provenance so a
    synthetic test run stays training-ineligible (prov!=VERIFIED) even though the freeze is genuine-
    class. Default None -> production computes VERIFIED for a genuine campaign with a real source ref."""
    cur = load_cursor(cursor_path)
    actions = []
    freezes = [r for r in _load(freeze_ledger) if r.get("record_type") == "ROUTER_FREEZE"]
    for fz in freezes:
        try:
            sid = fz["setup_id"]
            fkey = fz["logical_hash"]
            # AUTOMATED PATH: only genuine-prospective + prospective-eligible
            if OP.normalize_class(fz.get("record_class")) != "GENUINE_PROSPECTIVE" or not fz.get("eligible_for_prospective_evidence"):
                continue
            if cur["done"].get(fkey):
                continue
            complete, cutoff = (closure_fn or default_closure_fn(os.path.join(EVDIR, "..", "forward_validation_ledger_v0_2.jsonl")))(sid)
            if not complete or cutoff is None:
                if fkey not in cur["pending"]:
                    cur["pending"].append(fkey)
                    actions.append(f"PENDING({sid})")
                continue
            # closure present -> attach EXACTLY ONE outcome (idempotent), routed to the genuine ledger
            rec = OP.attach_outcome(fz, bars or [], observation_cutoff=cutoff, target=None,
                                    ledger_path=outcome_ledger,      # None -> routed by class = genuine
                                    source_provenance=source_provenance_override)
            cur["done"][fkey] = rec["idempotency_key"]
            if fkey in cur["pending"]:
                cur["pending"].remove(fkey)
            actions.append(f"OUTCOME_ATTACHED({sid} status={rec['labels']['outcome_status']})")
            # regenerate the versioned dataset (immutable exports)
            fls = [freeze_ledger] + (extra_freeze_ledgers or [])
            DG.generate(fls, outcome_ledger or OP.ROUTER_OUTCOMES, out_dir=dataset_dir)
            actions.append(f"DATASET_REGENERATED({sid})")
        except Exception as e:                                    # noqa: BLE001
            actions.append(f"COMPANION_ERROR({fz.get('setup_id')}: {type(e).__name__}) — live processes unaffected")
    save_cursor(cur, cursor_path)
    return actions


def watch(interval=60):
    try:
        fd = os.open(LOCK, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        os.write(fd, str(os.getpid()).encode()); os.close(fd)
    except FileExistsError:
        raise SystemExit("another outcome_companion holds the lock — refusing to start")
    log(f"outcome companion started pid={os.getpid()} | {BANNER}")
    log(f"COMPANION MODULE SHA {module_content_sha256()[:16]} | genuine freeze ledger: {FREEZE_LEDGER}")
    log("listener/wire/tracker/evidence-watcher are separate processes and are NEVER touched")
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
