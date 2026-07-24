"""
Signal Review Accelerator backend (READ-ONLY w.r.t. protected evidence; append-only sidecars only).

Provides, without duplicating Q4A/review/PaperDB/cohort logic:
  * effective-status events (history shows the latest effective status; the manifest is NEVER changed)
  * parent-signal suggestion for TRADE_UPDATE / TRADE_RESULT (human must approve; ambiguous -> unlinked)
  * append-only parent-link events (no new observation, no cohort increment, no signal rewrite)
  * a read-only review-queue summary

Nothing here creates a confirmed review, provider verification, UnifiedSignal, paper observation,
cohort count or alert — only the existing explicit human-confirmation route does that.
"""
from __future__ import annotations
import json
import os
import time
from datetime import datetime, timezone

_HERE = os.path.dirname(os.path.abspath(__file__))
_PL = os.path.dirname(_HERE)
_CE = os.path.dirname(_PL)
_ROOT = os.path.dirname(_CE)
REVIEW_DIR = os.path.join(_ROOT, "data", "manual_image_intake_v1", "review")
STATUS_LOG = "effective_status_events.jsonl"
LINK_LOG = "parent_link_events.jsonl"

FINAL_TO_EFFECTIVE = {"RECORDED": "SIGNAL_RECORDED", "NO_COVERAGE": "NO_COVERAGE",
                      "BLOCKED": "UNKNOWN_BLOCKED", "DUPLICATE": "DUPLICATE",
                      "TRADE_RESULT_EXCLUDED": "TRADE_RESULT_EXCLUDED",
                      "TRADE_UPDATE_EXCLUDED": "TRADE_UPDATE_EXCLUDED"}


def _now():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _path(name, root=None):
    return os.path.join(root or REVIEW_DIR, name)


def _append(name, obj, root=None):
    d = root or REVIEW_DIR
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, name), "a", encoding="utf-8") as f:
        f.write(json.dumps(obj, default=str) + "\n")


def _read(name, root=None):
    p = _path(name, root)
    if not os.path.exists(p):
        return []
    out = []
    for line in open(p, encoding="utf-8"):
        line = line.strip()
        if line:
            try:
                out.append(json.loads(line))
            except Exception:
                pass
    return out


# ---------------------------------------------------------------- effective status
def effective_from_final(final_status):
    return FINAL_TO_EFFECTIVE.get(final_status, final_status)


def record_effective_status(intake_id, effective_status, detail=None, root=None):
    """Append-only. The immutable manifest is never touched."""
    _append(STATUS_LOG, {"intake_id": intake_id, "effective_status": effective_status,
                         "detail": detail, "at": _now()}, root)


def latest_effective_status(intake_id, root=None):
    latest = None
    for ev in _read(STATUS_LOG, root):
        if ev.get("intake_id") == intake_id:
            latest = ev.get("effective_status")
    return latest


def all_latest_statuses(root=None):
    out = {}
    for ev in _read(STATUS_LOG, root):
        out[ev.get("intake_id")] = ev.get("effective_status")
    return out


CLASS_TO_EFFECTIVE = {"TRADE_UPDATE": "TRADE_UPDATE_EXCLUDED", "TRADE_RESULT": "TRADE_RESULT_EXCLUDED",
                      "UNKNOWN": "UNKNOWN_BLOCKED"}


def reviews_by_intake(root=None):
    """Map intake_id -> review record from the review sidecars (read-only)."""
    d = root or REVIEW_DIR
    out = {}
    if os.path.isdir(d):
        for fn in os.listdir(d):
            if fn.startswith("review-img-") and fn.endswith(".json"):
                try:
                    rv = json.load(open(os.path.join(d, fn), encoding="utf-8"))
                    out[rv.get("intake_id")] = rv
                except Exception:
                    pass
    return out


def resolve_effective(intake_id, review=None, root=None):
    """Latest status event wins; else derive from a CONFIRMED review's class; else None (manifest)."""
    ev = latest_effective_status(intake_id, root)
    if ev:
        return ev
    if review and review.get("explicit_confirmation_state") == "CONFIRMED":
        return CLASS_TO_EFFECTIVE.get(review.get("intake_class"))   # SIGNAL -> None (needs an observation)
    return None


# ---------------------------------------------------------------- parent-signal linking
def _gap_seconds(a, b):
    def ms(s):
        if not s:
            return None
        try:
            d = datetime.fromisoformat(str(s).replace("Z", "+00:00"))
            return (d if d.tzinfo else d.replace(tzinfo=timezone.utc)).timestamp()
        except Exception:
            return None
    A, B = ms(a), ms(b)
    return abs(A - B) if (A is not None and B is not None) else 10 ** 12


def suggest_parent(child, recorded_signals):
    """child = {provider, instrument, direction, post_time}. recorded_signals = list of recorded
    SIGNAL observations {observation_id, provider, instrument, direction, time}. Returns a suggestion
    with confidence; a tie / no-match stays UNLINKED (suggested=None)."""
    instr = (child.get("instrument") or "").upper()
    prov = child.get("provider")
    direction = (child.get("direction") or "").upper()
    ctime = child.get("post_time")
    scored = []
    for s in recorded_signals:
        if (s.get("instrument") or "").upper() != instr or not instr:
            continue
        score, why = 1, ["instrument"]                 # instrument match required
        if prov and s.get("provider") == prov:
            score += 2; why.append("provider")
        if direction and (s.get("direction") or "").upper() == direction:
            score += 1; why.append("direction")
        scored.append((score, _gap_seconds(ctime, s.get("time")), s, why))
    if not scored:
        return {"suggested": None, "confidence": None, "reason": "NO_INSTRUMENT_MATCH", "candidates": []}
    scored.sort(key=lambda x: (-x[0], x[1]))
    best = scored[0]
    tied = [x for x in scored if x[0] == best[0]]
    if len(tied) > 1 and min(t[1] for t in tied) == max(t[1] for t in tied):
        # equal score AND indistinguishable time -> ambiguous -> UNLINKED
        return {"suggested": None, "confidence": "LOW", "reason": "AMBIGUOUS_MULTIPLE_MATCHES",
                "candidates": [t[2].get("observation_id") for t in tied]}
    conf = "HIGH" if best[0] >= 4 else ("MEDIUM" if best[0] >= 3 else "LOW")
    return {"suggested": best[2].get("observation_id"), "confidence": conf,
            "reason": "+".join(best[3]), "candidates": [t[2].get("observation_id") for t in tied]}


def record_link(parent_observation_id, child_intake_id, kind, detail=None, root=None):
    """Immutable append. kind in {UPDATE, RESULT}. Creates NO observation / cohort count / signal rewrite."""
    if not parent_observation_id or not child_intake_id:
        return {"linked": False, "reason": "MISSING_PARENT_OR_CHILD"}
    _append(LINK_LOG, {"parent_observation_id": parent_observation_id, "child_intake_id": child_intake_id,
                       "kind": kind, "detail": detail, "at": _now(), "human_approved": True}, root)
    return {"linked": True, "parent_observation_id": parent_observation_id,
            "child_intake_id": child_intake_id, "kind": kind}


def links_for_child(child_intake_id, root=None):
    return [e for e in _read(LINK_LOG, root) if e.get("child_intake_id") == child_intake_id]


def linked_children(root=None):
    return {e.get("child_intake_id") for e in _read(LINK_LOG, root)}


# ---------------------------------------------------------------- review-queue summary
def queue_summary(*, statuses=None, bundles=None, links=None, cohort=None, root=None):
    """Reuse existing records. statuses = {intake_id: effective_status}; bundles = cohort bundles;
    links = linked child intake_ids; cohort = {'complete':X,'target':5}. All optional/injectable."""
    statuses = statuses if statuses is not None else all_latest_statuses(root)
    links = links if links is not None else linked_children(root)
    unknown_blocked = sum(1 for v in statuses.values() if v == "UNKNOWN_BLOCKED")
    pending = 0
    unlinked_updates = 0
    if bundles is not None:
        for b in bundles:
            iid = b.get("intake_id")
            ic = (b.get("review") or {}).get("intake_class")
            eff = statuses.get(iid)
            if eff is None and (b.get("review") or {}).get("explicit_confirmation_state") != "CONFIRMED":
                pending += 1
            if ic in ("TRADE_UPDATE", "TRADE_RESULT") and iid not in links:
                unlinked_updates += 1
    c = cohort or {}
    return {"ready_for_next_screenshot": True, "pending_review": pending,
            "unknown_blocked": unknown_blocked, "unlinked_updates_results": unlinked_updates,
            "cohort_headline": f"COHORT ONE: {c.get('complete', 0)} / {c.get('target', 5)}"}
