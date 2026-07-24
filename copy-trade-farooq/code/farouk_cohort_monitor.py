"""
farouk_cohort_monitor.py — READ-ONLY tracker for the first five GENUINE Farouk SIGNAL records.

It reads the review sidecars, intake manifests, and (if present) the append-only paper-observation
and image-bridge stores, and reports progress toward COHORT ONE: X / 5 COMPLETE. It writes only
data/reports/farouk_cohort_one_status.{json,md} and modifies NO evidence database. Safely rerunnable.
No recomputation of outcomes, no order/execution path. Missing timestamps stay unknown (never invented).
"""
from __future__ import annotations
import json
import os
import sqlite3
import sys
import time

_ROOT = os.path.dirname(os.path.abspath(__file__))
INTAKE_ROOT = os.path.join(_ROOT, "data", "manual_image_intake_v1")
REVIEW_DIR = os.path.join(INTAKE_ROOT, "review")
MANIFEST_DIR = os.path.join(INTAKE_ROOT, "manifests")
PAPER_DB = os.path.join(_ROOT, "data", "paper_observations_v1.db")
BRIDGE_DB = os.path.join(_ROOT, "data", "image_bridge_observations_v1.db")
REPORTS = os.path.join(_ROOT, "data", "reports")
FAROUK = "seascalperfarouk"
TARGET = 5
NO_COVERAGE_REASONS = ("NO_COVERAGE", "NO_FRESH_QUOTE")


def _now():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _is_synthetic(intake_id, provider, review):
    blob = f"{intake_id} {provider} {review.get('reviewer_ref', '')}".lower()
    return any(t in blob for t in ("test", "synthetic", "fixture", "dummy"))


def _classify(b):
    """Return the cohort status for one intake bundle. Never counts unverified as verified Farouk."""
    rv, m, po = (b.get("review") or {}), (b.get("manifest") or {}), b.get("paper_obs")
    ic = rv.get("intake_class")
    prov = (rv.get("provider") or {}).get("value")
    ver = (rv.get("provider") or {}).get("verification_state")
    conf = rv.get("explicit_confirmation_state")
    iid = b.get("intake_id", "")
    if _is_synthetic(iid, prov or "", rv):
        return "EXCLUDED_SYNTHETIC"
    if ic == "TRADE_RESULT":
        return "EXCLUDED_TRADE_RESULT"
    if ic == "TRADE_UPDATE":
        return "EXCLUDED_TRADE_UPDATE"
    if ic == "UNKNOWN":
        return "BLOCKED_UNKNOWN"
    if ic != "SIGNAL":
        return "EXCLUDED_NOT_SIGNAL"
    if m.get("duplicate"):
        return "EXCLUDED_DUPLICATE"
    if prov != FAROUK:
        return "EXCLUDED_NON_FAROUK"
    if conf != "CONFIRMED":
        return "AWAITING_CONFIRMATION"
    if ver != "PROVIDER_VERIFIED":
        return "PROVIDER_UNVERIFIED"                       # shown, never silently counted
    if not po:
        return "AWAITING_OBSERVATION"
    return "COMPLETE"


def _coverage_of(b):
    """Coverage status from the bridge's human-confirmed result, else the paper reason_code."""
    br = b.get("bridge_obs") or {}
    hc = br.get("human_confirmed_actionable_result") or {}
    if isinstance(hc, str):
        try:
            hc = json.loads(hc)
        except Exception:
            hc = {}
    reason = hc.get("reason")
    if reason is None and b.get("paper_obs"):
        reason = (b["paper_obs"] or {}).get("reason_code")
    return reason


def _member_fields(pos, b, status):
    rv, m = (b.get("review") or {}), (b.get("manifest") or {})
    po, br = (b.get("paper_obs") or {}), (b.get("bridge_obs") or {})
    fields = rv.get("fields") or {}

    def fv(k):
        return (fields.get(k) or {}).get("value")
    prov = rv.get("provider") or {}
    ppa = rv.get("provider_posted_at") or {}
    return {
        "cohort_position": pos, "intake_id": b.get("intake_id"), "review_id": rv.get("review_id"),
        "paper_observation_id": br.get("paper_observation_id") or po.get("observation_id"),
        "instrument": fv("instrument"), "direction": fv("direction"),
        "provider": prov.get("value"), "provider_verification": prov.get("verification_state"),
        "provider_posted_time": ppa.get("value"), "provider_posted_provenance": ppa.get("provenance"),
        "import_time": m.get("screenshot_imported_at"),
        "confirmation_time": rv.get("review_created_at_utc"),
        "q4a_decision_time": po.get("decision_timestamp"),
        "paper_recorded_time": po.get("persisted_utc"),
        "quote_coverage_status": _coverage_of(b),
        "q4a_result": po.get("status"),
        "duplicate": bool(m.get("duplicate")),
        "alert_status": ("EMITTED" if po.get("observation_id") else "NONE"),
        "capture_latency_s": br.get("capture_latency_s"),
        "import_latency_s": br.get("import_latency_s"),
        "confirmation_latency_s": br.get("actionable_latency_s"),
        "total_pipeline_latency_s": br.get("actionable_latency_s"),
        "errors_or_corrections": rv.get("corrections") or [],
        "cohort_status": status,
    }


def assess(bundles):
    """Pure assessment: bundles -> cohort status artifact. Injectable for tests."""
    members, complete = [], []
    for b in bundles:
        status = _classify(b)
        rec = _member_fields(0, b, status)
        members.append(rec)
        if status == "COMPLETE":
            complete.append(rec)
    for i, rec in enumerate(complete[:TARGET], 1):
        rec["cohort_position"] = i
    counts = {
        "awaiting_confirmation": sum(1 for x in members if x["cohort_status"] == "AWAITING_CONFIRMATION"),
        "no_coverage": sum(1 for x in complete if x["quote_coverage_status"] in NO_COVERAGE_REASONS),
        "recorded_successfully": sum(1 for x in complete if x["quote_coverage_status"] not in NO_COVERAGE_REASONS),
        "blocked": sum(1 for x in members if x["cohort_status"] in ("BLOCKED_UNKNOWN", "EXCLUDED_NOT_SIGNAL")),
        "duplicates_excluded": sum(1 for x in members if x["cohort_status"] == "EXCLUDED_DUPLICATE"),
        "provider_unverified": sum(1 for x in members if x["cohort_status"] == "PROVIDER_UNVERIFIED"),
        "trade_result_excluded": sum(1 for x in members if x["cohort_status"] == "EXCLUDED_TRADE_RESULT"),
        "trade_update_excluded": sum(1 for x in members if x["cohort_status"] == "EXCLUDED_TRADE_UPDATE"),
        "non_farouk_excluded": sum(1 for x in members if x["cohort_status"] == "EXCLUDED_NON_FAROUK"),
    }
    return {"cohort": "COHORT_ONE", "as_of_utc": _now(), "target": TARGET,
            "complete": min(len(complete), TARGET), "headline": f"COHORT ONE: {min(len(complete), TARGET)} / {TARGET} COMPLETE",
            "counts": counts, "members": members,
            "cohort_members": [x for x in members if x["cohort_status"] == "COMPLETE"][:TARGET]}


# ---------------------------------------------------------------- live read-only loader
def _read_json(path):
    try:
        return json.load(open(path, encoding="utf-8"))
    except Exception:
        return None


def _load_table(db, table, key):
    if not os.path.exists(db):
        return {}
    c = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    c.row_factory = sqlite3.Row
    out = {}
    try:
        for r in c.execute(f"SELECT * FROM {table}"):
            out[r[key]] = dict(r)
    except sqlite3.OperationalError:
        pass
    c.close()
    return out


def load_bundles():
    manifests = {}
    if os.path.isdir(MANIFEST_DIR):
        for fn in os.listdir(MANIFEST_DIR):
            m = _read_json(os.path.join(MANIFEST_DIR, fn))
            if m:
                manifests[m.get("intake_id")] = m
    paper = _load_table(PAPER_DB, "paper_observations", "observation_id")
    bridge_rows = _load_table(BRIDGE_DB, "image_bridge_observations", "intake_id")
    bundles = []
    if os.path.isdir(REVIEW_DIR):
        for fn in os.listdir(REVIEW_DIR):
            if not fn.startswith("review-img-") or not fn.endswith(".json"):
                continue
            rv = _read_json(os.path.join(REVIEW_DIR, fn))
            if not rv:
                continue
            iid = rv.get("intake_id")
            br = bridge_rows.get(iid)
            po = paper.get(br["paper_observation_id"]) if br and br.get("paper_observation_id") else None
            bundles.append({"intake_id": iid, "review": rv, "manifest": manifests.get(iid, {}),
                            "paper_obs": po, "bridge_obs": br})
    return bundles


def _markdown(rep):
    L = [f"# Farouk Cohort One — {rep['as_of_utc']} (READ-ONLY)\n", f"## {rep['headline']}\n", "### Counts"]
    for k, v in rep["counts"].items():
        L.append(f"- {k}: {v}")
    L.append("\n### Signals")
    if not rep["members"]:
        L.append("_(no intake records yet)_")
    for x in rep["members"]:
        L.append(f"- **{x['cohort_status']}** · intake `{x['intake_id']}` · {x['instrument'] or '?'} "
                 f"{x['direction'] or '?'} · provider {x['provider'] or '?'} ({x['provider_verification'] or '?'}) "
                 f"· coverage {x['quote_coverage_status'] or '-'} · obs {x['paper_observation_id'] or '-'}")
    L.append("\n_Read-only monitor; no evidence database modified. PAPER ONLY / NOT A FILL / NOT AN OUTCOME._")
    return "\n".join(L) + "\n"


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    os.makedirs(REPORTS, exist_ok=True)
    rep = assess(load_bundles())
    json.dump(rep, open(os.path.join(REPORTS, "farouk_cohort_one_status.json"), "w"),
              indent=2, default=str)
    open(os.path.join(REPORTS, "farouk_cohort_one_status.md"), "w", encoding="utf-8").write(_markdown(rep))
    print(rep["headline"])
    print("counts:", json.dumps(rep["counts"]))
    print(f"artifacts: {os.path.join(REPORTS, 'farouk_cohort_one_status.json')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
