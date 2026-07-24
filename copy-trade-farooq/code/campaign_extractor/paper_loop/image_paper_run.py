"""
Smallest observation orchestrator: a confirmed review -> UnifiedSignal (existing adapter) ->
run_three_anchors (existing, unchanged Q4A) -> at most one append-only PaperDB observation + one
ImageBridgeDB row + one alert. Honest NO_COVERAGE when no quote session covers the timestamp.
Idempotent by deterministic ids. No execution, no broker write, no order path.
"""
from __future__ import annotations
import hashlib
import json
import os
import shutil
import sqlite3
import sys
import time
from datetime import datetime, timezone

_HERE = os.path.dirname(os.path.abspath(__file__))
_CE = os.path.dirname(_HERE)
_ROOT = os.path.dirname(_CE)
_Q4 = os.path.join(_CE, "q4_align")
for p in (_ROOT, _CE, _Q4, _HERE):
    if p not in sys.path:
        sys.path.insert(0, p)

import image_confirm
import image_signal_bridge as bridge
import image_intake
from paper_db import PaperDB
from image_bridge_db import ImageBridgeDB

QUOTES_DB = os.path.join(_ROOT, "data", "ctrader_quotes_v1.db")
ALERT_JSONL = os.path.join(_ROOT, "data", "image_paper_alerts_v1.jsonl")
ALERT_LATEST = os.path.join(_ROOT, "data", "image_paper_alert_latest.json")


def _now():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _ms(s):
    if not s:
        return None
    d = datetime.fromisoformat(str(s).replace("Z", "+00:00"))
    return int((d if d.tzinfo else d.replace(tzinfo=timezone.utc)).timestamp() * 1000)


def _det(*parts):
    return hashlib.sha256("|".join(str(p) for p in parts).encode()).hexdigest()[:16]


def _approved_from_review(review):
    f = review["fields"]
    return {"semantic_class": review.get("semantic_class") or "UNKNOWN", "isolated_signal_block": False,
            "all_facts_human_confirmed": review["explicit_confirmation_state"] == "CONFIRMED",
            "provider_verified": review["provider"]["verification_state"] == "PROVIDER_VERIFIED",
            "instrument": f["instrument"]["value"], "direction": f["direction"]["value"],
            "entry_low": f["entry_low"]["value"], "entry_high": f["entry_high"]["value"],
            "stop_price": f["stop_price"]["value"], "target_prices": f["target_prices"]["value"],
            "provider_posted_at": review["provider_posted_at"]["value"],
            "human_confirmed_at": review["review_created_at_utc"],
            "reviewer_reference": review["reviewer_ref"],
            "mixed_blocks_not_separated": False, "conflicting_high_impact": False}


def _covering_quotes(anchor_ms):
    """Return quotes for a session whose span covers anchor_ms, else [] (honest NO_COVERAGE)."""
    if anchor_ms is None or not os.path.exists(QUOTES_DB):
        return []
    c = sqlite3.connect(f"file:{QUOTES_DB}?mode=ro", uri=True)
    rows = c.execute("SELECT connection_session_id, MIN(local_received_utc), MAX(local_received_utc) "
                     "FROM raw_spot_events GROUP BY connection_session_id").fetchall()
    c.close()
    for sid, a, b in rows:
        if _ms(a) is not None and _ms(b) is not None and _ms(a) <= anchor_ms <= _ms(b):
            sys.path.insert(0, _Q4)
            import quote_source
            return quote_source.load_session_quotes(sid, QUOTES_DB)
    return []


def run(intake_id, review_id, *, quotes=None, paper_db=None, bridge_db=None, move_file=True,
        alert_dir=None):
    alert_dir = alert_dir or os.path.join(_ROOT, "data")
    review = image_confirm.load_review(review_id)
    if review is None:
        return {"status": "REJECTED", "reason": "REVIEW_NOT_FOUND"}
    if review["intake_id"] != intake_id:
        return {"status": "REJECTED", "reason": "INTAKE_REVIEW_MISMATCH"}
    # ---- MANDATORY semantic-class gate (before ANY signal processing) ----
    intake_class = review.get("intake_class", "UNKNOWN")
    if intake_class == "TRADE_RESULT":
        return {"status": "TRADE_RESULT_EXCLUDED", "intake_id": intake_id, "review_id": review_id,
                "reason": review.get("exclusion_reason") or "KNOWN_RESULT_OR_CLOSED_TRADE_IMAGE",
                "pipeline_excluded": True}          # no UnifiedSignal, no Q4A, no PaperDB, no alert
    if intake_class == "TRADE_UPDATE":
        return {"status": "TRADE_UPDATE_EXCLUDED", "intake_id": intake_id, "review_id": review_id,
                "reason": review.get("exclusion_reason") or "MANAGEMENT_OF_EXISTING_POSITION",
                "pipeline_excluded": True}          # position management: no new signal/Q4A/obs/cohort
    if intake_class != "SIGNAL":
        return {"status": "BLOCKED", "intake_id": intake_id, "review_id": review_id,
                "reason": "UNKNOWN_SEMANTIC_CLASS_REQUIRES_REVIEW", "pipeline_excluded": True}
    if review["explicit_confirmation_state"] != "CONFIRMED":
        return {"status": "REJECTED", "reason": "REVIEW_NOT_CONFIRMED"}   # unconfirmed -> nothing
    try:
        manifest, orig = image_confirm.load_and_verify_intake(intake_id)   # verifies image hash
    except image_confirm.IntakeError as e:
        return {"status": "REJECTED", "reason": str(e).split()[0]}
    if review["original_image_sha256"] != manifest["original_image_sha256"]:
        return {"status": "REJECTED", "reason": "IMAGE_HASH_MISMATCH"}

    obs_id = "paperobs-img-" + _det(intake_id, review_id)
    ibo_id = "ib-img-" + _det(intake_id, review_id)
    pdb = paper_db or PaperDB()
    # idempotency: if this observation already exists, print it and exit (no duplicate writes/alert)
    existing = pdb.conn.execute("SELECT status FROM paper_observations WHERE observation_id=?",
                                (obs_id,)).fetchone()
    if existing:
        print(f"ALREADY OBSERVED (idempotent): {obs_id} status={existing[0]}")
        if paper_db is None:
            pdb.close()
        return {"status": "ALREADY_OBSERVED", "observation_id": obs_id, "existing_status": existing[0]}

    approved = _approved_from_review(review)
    refs = [review_id, "sha:" + manifest["original_image_sha256"][:16]]
    verdict_status, unified, verdict_reason = bridge.build_image_unified_signal(approved, manifest, refs)

    # coverage probe: run the anchors on the human-read fields even if provider is unverified
    # (provider identity is orthogonal to quote coverage; the recorded provider stays UNKNOWN)
    probe = unified
    if verdict_status != "IMAGE_CONFIRMED":
        ps, probe, _ = bridge.build_image_unified_signal({**approved, "provider_verified": True},
                                                         manifest, refs)
        if ps != "IMAGE_CONFIRMED":
            probe = None
    post_prov = review["provider_posted_at"]["provenance"]
    if probe is not None:
        q = quotes if quotes is not None else _covering_quotes(_ms(manifest["screenshot_imported_at"]))
        anchors = bridge.run_three_anchors(
            probe, q, None, provider_posted_at=review["provider_posted_at"]["value"],
            provider_posted_provenance=post_prov,
            screenshot_imported_at=manifest["screenshot_imported_at"],
            human_confirmed_at=review["review_created_at_utc"])
    else:
        u = {"status": "PAPER_UNKNOWN", "reason": "SIGNAL_FIELDS_INCOMPLETE"}
        anchors = {"PROVIDER_POST_TIME_RESULT": {"status": "PAPER_UNKNOWN", "reason": "POST_TIME_UNVERIFIABLE"},
                   "MANUAL_IMPORT_TIME_RESULT": dict(u), "HUMAN_CONFIRMED_ACTIONABLE_RESULT": dict(u)}
    hc = anchors["HUMAN_CONFIRMED_ACTIONABLE_RESULT"]

    prov_state = review["provider"]["verification_state"]
    pipeline_validation_only = (prov_state != "PROVIDER_VERIFIED" or post_prov == "UNVERIFIABLE"
                                or hc.get("reason") in ("NO_COVERAGE", "NO_FRESH_QUOTE")
                                or verdict_status != "IMAGE_CONFIRMED")
    overall = "PIPELINE_VALIDATION_ONLY" if pipeline_validation_only else hc["status"]
    lat = bridge.latencies(provider_posted_at=review["provider_posted_at"]["value"],
                           screenshot_captured_at=manifest.get("screenshot_captured_at"),
                           screenshot_imported_at=manifest["screenshot_imported_at"],
                           human_confirmed_at=review["review_created_at_utc"])

    snapshot_unified = {"schema_version": "unified-signal-v0.1", "provider_id": "UNKNOWN",
                        "source_type": "IMAGE_CONFIRMED", "source_platform": "DISCORD",
                        "source_message_id": manifest.get("discord_message_ref") or intake_id,
                        "instrument": approved["instrument"], "direction": approved["direction"],
                        "entry_low": approved["entry_low"], "entry_high": approved["entry_high"],
                        "source_evidence_references": refs,
                        "reviewer_reference": review["reviewer_ref"]}
    decision = {"status": overall, "reason": verdict_reason or hc.get("reason"),
                "unified": snapshot_unified, "delivery": anchors["MANUAL_IMPORT_TIME_RESULT"],
                "actionable": hc, "q4a_config_version": "q4-thresholds-v1",
                "provider_verification_state": prov_state, "excluded_from_aggregates": True}

    # --- WRITES (in order; inbox file moved LAST so a partial failure is recoverable) ---
    pdb.record(decision, observation_id=obs_id, provider_id="UNKNOWN",
               reviewer_reference=review["reviewer_ref"])
    ibdb = bridge_db or ImageBridgeDB()
    try:
        ibdb.record(bridge_obs_id=ibo_id, paper_observation_id=obs_id, intake_id=intake_id,
                    original_image_sha256=manifest["original_image_sha256"], crop_hashes=[],
                    review_decision_ids=[review_id], timestamp_provenance=post_prov,
                    provider_post_result=anchors["PROVIDER_POST_TIME_RESULT"],
                    manual_import_result=anchors["MANUAL_IMPORT_TIME_RESULT"],
                    human_confirmed_actionable_result=hc, latencies=lat)
    except sqlite3.IntegrityError:
        pass                                            # already recorded (idempotent)

    alert = {"banner": "MANUAL IMAGE / PIPELINE VALIDATION ONLY / PAPER ONLY / NO COVERAGE / "
             "NOT A FILL / NOT AN OUTCOME",
             "labels": ["OBSERVATION_ONLY", "PAPER_ONLY", "NOT_A_FILL", "NOT_AN_OUTCOME",
                        "MANUAL_IMAGE", "PIPELINE_VALIDATION_ONLY"],
             "intake_id": intake_id, "observation_id": obs_id, "review_id": review_id,
             "provider": "UNKNOWN", "provider_verification": prov_state,
             "instrument": approved["instrument"], "direction": approved["direction"],
             "entry_range": [approved["entry_low"], approved["entry_high"]],
             "stop": approved["stop_price"], "provider_post_provenance": post_prov,
             "provider_post_quote_result": f"{anchors['PROVIDER_POST_TIME_RESULT']['status']}/"
             f"{anchors['PROVIDER_POST_TIME_RESULT'].get('reason')}",
             "import_time_quote_result": anchors["MANUAL_IMPORT_TIME_RESULT"]["status"],
             "confirmation_time_quote_result": f"{hc['status']}/{hc.get('reason')}",
             "excluded_from_aggregates": True, "actionable_latency_s": lat.get("actionable_latency_s"),
             "source_evidence": review["source_evidence_references"], "emitted_utc": _now()}
    per_obs = os.path.join(alert_dir, f"image_paper_alert_{obs_id}.json")
    if not os.path.exists(per_obs):
        with open(os.path.join(alert_dir, "image_paper_alerts_v1.jsonl"), "a", encoding="utf-8") as f:
            f.write(json.dumps(alert, default=str) + "\n")
        json.dump(alert, open(os.path.join(alert_dir, "image_paper_alert_latest.json"), "w",
                              encoding="utf-8"), indent=2, default=str)
        json.dump(alert, open(per_obs, "w", encoding="utf-8"), indent=2, default=str)
    print(f"[{alert['banner']}] intake={intake_id} obs={obs_id} {approved['instrument']} "
          f"{approved['direction']} zone={alert['entry_range']} -> {overall} "
          f"(provider={prov_state}, post={post_prov}, coverage={hc.get('reason')})")

    # move inbox copy -> processed ONLY after all writes succeeded
    if move_file:
        inbox = os.path.join(image_intake.INTAKE_ROOT, "inbox", manifest["original_filename"])
        if os.path.exists(inbox):
            dest = os.path.join(image_intake.INTAKE_ROOT, "processed", manifest["original_filename"])
            shutil.move(inbox, dest)
        with open(os.path.join(image_intake.INTAKE_ROOT, "review", "intake_status_events.jsonl"),
                  "a", encoding="utf-8") as f:
            f.write(json.dumps({"intake_id": intake_id, "event": "OBSERVATION_RECORDED",
                                "observation_id": obs_id, "status": overall, "at": _now()}) + "\n")

    if paper_db is None:
        pdb.close()
    if bridge_db is None:
        ibdb.close()
    return {"status": overall, "observation_id": obs_id, "bridge_obs_id": ibo_id,
            "provider_verification": prov_state, "post_provenance": post_prov,
            "coverage": hc.get("reason"), "excluded_from_aggregates": True, "anchors": anchors,
            "alert": alert}


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("usage: image_paper_run.py <intake_id> <review_id>"); sys.exit(2)
    r = run(sys.argv[1], sys.argv[2])
    print(json.dumps({k: r[k] for k in r if k != "anchors"}, indent=2, default=str))
