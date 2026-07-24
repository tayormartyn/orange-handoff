"""
Append-only history repair + parent-link adjudication. NOTHING here mutates an original intake,
review, manifest, signal, update, result, paper observation or lifecycle record. All proposals are
written as append-only events to a SEPARATE log (repair_events.jsonl). *_PROPOSED events are advisory;
*_CONFIRMED / *_REJECTED events are only ever written by an explicit Martyn action (never automatic).
Role is resolved by the LATEST effective review class per intake (so a re-reviewed intake is not
double-counted as both parent and child).
"""
from __future__ import annotations
import glob
import json
import os
import re

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_REVIEW = os.path.join(_ROOT, "data", "manual_image_intake_v1", "review")
REPAIR_LOG = os.path.join(_ROOT, "data", "manual_image_intake_v1", "repair_events.jsonl")

SIGNAL_CLASSES = ("SIGNAL", "SIGNAL_ANNOUNCEMENT")
CHILD_CLASSES = ("TRADE_UPDATE", "TRADE_RESULT")
_DIR = re.compile(r"\b(buy|sell|long|short)\b", re.I)
_GLUED_DIR = re.compile(r"(?:xau\w*|vip)[\s\-]*?(buy|sell)", re.I)
_ZONE = re.compile(r"(\d{3,5}(?:\.\d+)?)\s*[-–to]{1,3}\s*(\d{3,5}(?:\.\d+)?)")
_STOP = re.compile(r"(?:stop\s*loss|stoploss|\bsl\b|stop)\D{0,4}(\d{3,5}(?:\.\d+)?)", re.I)
_TP = re.compile(r"(?:tp\d?|take\s*profit|target)\D{0,4}(\d{3,5}(?:\.\d+)?)", re.I)
_DIR_NORM = {"buy": "BUY", "long": "BUY", "sell": "SELL", "short": "SELL"}


# ---------------------------------------------------------------- PART 1: role reconciliation
def _reviews(root=None):
    review = os.path.join(root, "data", "manual_image_intake_v1", "review") if root else _REVIEW
    from collections import defaultdict
    by = defaultdict(list)
    for p in sorted(glob.glob(os.path.join(review, "*.json")), key=os.path.getmtime):
        try:
            d = json.load(open(p, encoding="utf-8"))
        except Exception:
            continue
        by[d.get("intake_id")].append({
            "review_id": d.get("review_id"),
            "class": d.get("intake_class") or d.get("semantic_class"),
            "created": d.get("review_created_at_utc"),
            "sha": (d.get("original_image_sha256") or "")[:16],
            "provider": (d.get("provider") or {}).get("value"),
            "mtime": os.path.getmtime(p)})
    return by


def role_decisions():
    """{intake_id: chosen_role} from ROLE_CONFLICT_RESOLVED — the explicit human decision is
    authoritative for the effective role."""
    out = {}
    for e in load_events():
        if e["event_type"] == "ROLE_CONFLICT_RESOLVED":
            out[e["intake_id"]] = e["chosen_role"]
    return out


def reconcile_roles(root=None):
    decided = role_decisions()
    out = {}
    for iid, evs in _reviews(root).items():
        evs = sorted(evs, key=lambda e: e["mtime"])
        latest = evs[-1]
        # explicit role decision wins over the latest-class heuristic
        role = decided.get(iid) or ("PARENT_SIGNAL" if latest["class"] in SIGNAL_CLASSES else "CHILD_UPDATE_RESULT")
        roles_seen = {("PARENT_SIGNAL" if e["class"] in SIGNAL_CLASSES else "CHILD_UPDATE_RESULT")
                      for e in evs}
        out[iid] = {
            "manifest_class": evs[0]["class"], "latest_effective_class": latest["class"],
            "latest_review_id": latest["review_id"], "effective_status": _effective_status(latest["class"]),
            "effective_role": role, "multiple_events": len(evs) > 1,
            "role_conflict": len(roles_seen) > 1, "event_count": len(evs),
            "sha16": latest["sha"], "provider": latest["provider"]}
    return out


def _effective_status(cls):
    return {"SIGNAL": "SIGNAL_RECORDED", "SIGNAL_ANNOUNCEMENT": "SIGNAL_RECORDED",
            "TRADE_UPDATE": "TRADE_UPDATE_EXCLUDED", "TRADE_RESULT": "TRADE_RESULT_EXCLUDED"}.get(cls, "IMPORTED_PENDING_REVIEW")


def latest_role_sets(root=None):
    roles = reconcile_roles(root)
    parents = [i for i, r in roles.items() if r["effective_role"] == "PARENT_SIGNAL"]
    children = [i for i, r in roles.items() if r["effective_role"] == "CHILD_UPDATE_RESULT"]
    conflicts = [i for i, r in roles.items() if r["role_conflict"]]
    return parents, children, conflicts


# ---------------------------------------------------------------- PART 2: field recovery
def recover_fields(ocr_text):
    """Regex recovery from OCR (handles glued tokens). Only returns a field when evidence is present;
    everything else stays UNKNOWN. Never guesses ambiguous glyphs."""
    t = ocr_text or ""
    rec = {}

    m = _GLUED_DIR.search(t) or _DIR.search(t)
    if m:
        rec["direction"] = {"value": _DIR_NORM[m.group(1).lower()], "evidence": m.group(0),
                            "confidence": "HIGH" if _DIR.search(t) else "MEDIUM"}

    if re.search(r"xau", t, re.I) or re.search(r"gold", t, re.I):
        rec["instrument"] = {"value": "XAUUSD", "evidence": "XAU/GOLD token", "confidence": "HIGH"}

    zone_ctx = re.search(r"entry[^0-9]{0,8}(\d{3,5}(?:\.\d+)?)\s*[-–to]{1,3}\s*(\d{3,5}(?:\.\d+)?)", t, re.I)
    if zone_ctx:
        lo, hi = sorted((float(zone_ctx.group(1)), float(zone_ctx.group(2))))
        rec["entry_low"] = {"value": lo, "evidence": zone_ctx.group(0), "confidence": "HIGH"}
        rec["entry_high"] = {"value": hi, "evidence": zone_ctx.group(0), "confidence": "HIGH"}

    ms = _STOP.search(t)
    if ms:
        rec["stop"] = {"value": float(ms.group(1)), "evidence": ms.group(0), "confidence": "HIGH"}

    tps = _TP.findall(t)
    if tps:
        rec["targets"] = {"value": [float(x) for x in tps], "evidence": "tp/target tokens", "confidence": "MEDIUM"}

    return rec


# ---------------------------------------------------------------- append-only event log
def _append(event, write=True):
    event = dict(event)
    event.setdefault("status", event.get("event_type", "").split("_")[-1])
    if write:
        os.makedirs(os.path.dirname(REPAIR_LOG), exist_ok=True)
        with open(REPAIR_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(event) + "\n")
    return event


def load_events():
    """Read the append-only log tolerantly: a concurrent append can leave the final line partially
    written when a reader opens the file, so a malformed trailing line is skipped rather than raising
    (this was the intermittent 'repair queue unreachable' cause)."""
    if not os.path.exists(REPAIR_LOG):
        return []
    out = []
    for l in open(REPAIR_LOG, encoding="utf-8"):
        l = l.strip()
        if not l:
            continue
        try:
            out.append(json.loads(l))
        except Exception:
            continue                                     # skip a torn line from a concurrent append
    return out


def propose_signal_correction(intake_id, recovered, now_iso, write=True):
    supported = {k: v for k, v in recovered.items() if v.get("value") is not None}
    unknown = [k for k in ("instrument", "direction", "entry_low", "entry_high", "stop", "targets")
               if k not in supported]
    return _append({"event_type": "SIGNAL_FIELD_CORRECTION_PROPOSED", "intake_id": intake_id,
                    "proposed_fields": supported, "still_unknown": unknown, "ts": now_iso,
                    "requires": "SIGNAL_FIELD_CORRECTION_CONFIRMED (Martyn approval)"}, write)


def confirm_signal_correction(intake_id, reviewer, now_iso, fields=None, write=True):
    """ONLY called by an explicit Martyn action — never automatically."""
    assert reviewer, "confirmation requires a reviewer"
    ev = {"event_type": "SIGNAL_FIELD_CORRECTION_CONFIRMED", "intake_id": intake_id,
          "reviewer": reviewer, "ts": now_iso}
    if fields is not None:
        ev["confirmed_fields"] = fields
    return _append(ev, write)


def reject_signal_correction(intake_id, reviewer, now_iso, write=True):
    assert reviewer, "rejection requires a reviewer"
    return _append({"event_type": "SIGNAL_FIELD_CORRECTION_REJECTED", "intake_id": intake_id,
                    "reviewer": reviewer, "ts": now_iso}, write)


def edit_signal_correction(intake_id, edited_fields, reviewer, now_iso, write=True):
    """Append-only edit: records Martyn's edited values WITHOUT overwriting the original PROPOSED
    event (its evidence is preserved in the log)."""
    assert reviewer, "edit requires a reviewer"
    return _append({"event_type": "SIGNAL_FIELD_CORRECTION_EDITED", "intake_id": intake_id,
                    "edited_fields": edited_fields, "reviewer": reviewer, "ts": now_iso,
                    "preserves": "original SIGNAL_FIELD_CORRECTION_PROPOSED evidence"}, write)


def role_conflict_decision(intake_id, chosen_role, reviewer, now_iso, write=True):
    assert reviewer and chosen_role in ("PARENT_SIGNAL", "CHILD_UPDATE_RESULT"), "explicit role required"
    return _append({"event_type": "ROLE_CONFLICT_RESOLVED", "intake_id": intake_id,
                    "chosen_role": chosen_role, "reviewer": reviewer, "ts": now_iso}, write)


def leave_unlinked(child_id, reviewer, now_iso, write=True):
    assert reviewer, "decision requires a reviewer"
    return _append({"event_type": "CHILD_LEFT_UNLINKED", "child_intake_id": child_id,
                    "reviewer": reviewer, "ts": now_iso}, write)


def classify_unrelated_replay(child_id, reviewer, now_iso, write=True):
    assert reviewer, "decision requires a reviewer"
    return _append({"event_type": "CHILD_CLASSIFIED_UNRELATED_REPLAY", "child_intake_id": child_id,
                    "reviewer": reviewer, "ts": now_iso}, write)


def propose_classification_correction(intake_id, from_class, to_class, evidence, now_iso, write=True):
    """Append-only proposal to re-classify an intake (e.g. SIGNAL -> TRADE_RESULT). Never mutates the
    original review; requires Martyn's CLASSIFICATION_CORRECTION_CONFIRMED to take effect."""
    return _append({"event_type": "CLASSIFICATION_CORRECTION_PROPOSED", "intake_id": intake_id,
                    "from_class": from_class, "to_class": to_class, "evidence": evidence, "ts": now_iso,
                    "requires": "CLASSIFICATION_CORRECTION_CONFIRMED (Martyn approval)"}, write)


def confirm_classification_correction(intake_id, to_class, reviewer, now_iso, write=True):
    assert reviewer, "confirmation requires a reviewer"
    return _append({"event_type": "CLASSIFICATION_CORRECTION_CONFIRMED", "intake_id": intake_id,
                    "to_class": to_class, "reviewer": reviewer, "ts": now_iso}, write)


def reject_classification_correction(intake_id, reviewer, now_iso, write=True):
    assert reviewer, "rejection requires a reviewer"
    return _append({"event_type": "CLASSIFICATION_CORRECTION_REJECTED", "intake_id": intake_id,
                    "reviewer": reviewer, "ts": now_iso}, write)


def confirmed_classifications():
    """{intake_id: to_class} from CONFIRMED (and not later REJECTED) classification corrections. These
    override the stored review class for EFFECTIVE role/lifecycle purposes; the original review is
    never mutated."""
    conf, rej = {}, set()
    for e in load_events():
        if e["event_type"] == "CLASSIFICATION_CORRECTION_CONFIRMED":
            conf[e["intake_id"]] = e["to_class"]
        elif e["event_type"] == "CLASSIFICATION_CORRECTION_REJECTED":
            rej.add(e["intake_id"])
    return {i: c for i, c in conf.items() if i not in rej}


def pending_classification_corrections():
    """Proposed classification corrections not yet CONFIRMED or REJECTED (for the review card)."""
    resolved = set()
    proposed = {}
    for e in load_events():
        if e["event_type"] == "CLASSIFICATION_CORRECTION_PROPOSED":
            proposed[e["intake_id"]] = e
        elif e["event_type"] in ("CLASSIFICATION_CORRECTION_CONFIRMED", "CLASSIFICATION_CORRECTION_REJECTED"):
            resolved.add(e["intake_id"])
    return [e for i, e in proposed.items() if i not in resolved]


def confirmed_corrections():
    """Effective corrected fields per intake from CONFIRMED (+ later EDITED) events. Never auto-derived
    from PROPOSED alone."""
    out = {}
    for e in load_events():
        if e["event_type"] == "SIGNAL_FIELD_CORRECTION_CONFIRMED":
            out[e["intake_id"]] = e.get("confirmed_fields") or {}
        elif e["event_type"] == "SIGNAL_FIELD_CORRECTION_EDITED" and e["intake_id"] in out:
            out[e["intake_id"]] = e.get("edited_fields") or out[e["intake_id"]]
    return out


# ---------------------------------------------------------------- PART 3: parent-link candidates
def classification_result_cards():
    """{intake_id: result_card} from CLASSIFICATION_CORRECTION_PROPOSED evidence — used to enrich a
    reclassified result child (direction / entry / exit / profit) for candidate matching."""
    out = {}
    for e in load_events():
        if e["event_type"] == "CLASSIFICATION_CORRECTION_PROPOSED":
            rc = (e.get("evidence") or {}).get("result_card")
            if rc:
                out[e["intake_id"]] = rc
    return out


def link_candidates(child, parents):
    """child/parents are dicts with instrument/direction/provider/ts_ms; parents may also carry
    entry_low/entry_high; child may carry entry_candidate. Returns candidates with match evidence.
    SYMBOL ALONE never qualifies (needs >=1 more corroborating dimension)."""
    cands = []
    for p in parents:
        instr = bool(child.get("instrument") and p.get("instrument")
                     and child["instrument"].upper() == p["instrument"].upper())
        direction = bool(child.get("direction") and p.get("direction")
                         and child["direction"] == p["direction"])
        provider = bool(child.get("provider") and p.get("provider") and child["provider"] == p["provider"])
        cts, pts = child.get("ts_ms"), p.get("ts_ms")
        chrono = (pts is None or cts is None or pts <= cts)
        gap = (cts - pts) if (cts is not None and pts is not None) else None
        # price-in-zone: does the child's entry sit inside the parent's entry zone?
        entry, lo, hi = child.get("entry_candidate"), p.get("entry_low"), p.get("entry_high")
        price_in_zone = None
        if entry is not None and lo is not None and hi is not None:
            price_in_zone = (min(lo, hi) <= float(entry) <= max(lo, hi))
        corroborating = sum([direction, provider])
        if not instr or corroborating == 0 or not chrono:
            continue                                         # symbol-alone / non-chronological -> skip
        if price_in_zone is False:
            continue                                         # entry outside this parent's zone -> not a candidate
        conf = "HIGH" if (direction and provider and price_in_zone) else \
               ("HIGH" if price_in_zone else ("MEDIUM" if (direction and provider) else "LOW"))
        cands.append({"parent_signal_id": p["signal_id"], "instrument_match": instr,
                      "direction_match": direction, "provider_match": provider,
                      "time_gap_ms": gap, "chronological": chrono, "price_in_zone": price_in_zone,
                      "parent_entry_zone": ([lo, hi] if lo is not None else None),
                      "child_entry_candidate": entry, "confidence": conf, "ambiguity_warnings": []})
    if len(cands) > 1:
        for c in cands:
            c["ambiguity_warnings"].append("MULTIPLE_CANDIDATES_REQUIRE_MANUAL_ADJUDICATION")
    return cands


def propose_parent_link(child_id, candidate, now_iso, write=True):
    return _append({"event_type": "PARENT_LINK_PROPOSED", "child_intake_id": child_id,
                    "candidate_parent_signal_id": candidate["parent_signal_id"],
                    "match_evidence": candidate, "ts": now_iso,
                    "requires": "PARENT_LINK_CONFIRMED (Martyn approval)"}, write)


def confirm_parent_link(child_id, parent_signal_id, reviewer, now_iso, write=True):
    assert reviewer, "confirmation requires a reviewer"
    return _append({"event_type": "PARENT_LINK_CONFIRMED", "child_intake_id": child_id,
                    "parent_signal_id": parent_signal_id, "reviewer": reviewer, "ts": now_iso}, write)


def reject_parent_link(child_id, parent_signal_id, reviewer, now_iso, write=True):
    assert reviewer, "rejection requires a reviewer"
    return _append({"event_type": "PARENT_LINK_REJECTED", "child_intake_id": child_id,
                    "parent_signal_id": parent_signal_id, "reviewer": reviewer, "ts": now_iso}, write)


def unrelated_replay_children():
    """Children Martyn classified as unrelated replay (e.g. BTC) — excluded from Gold lifecycles but
    kept in immutable history + a separate unrelated-replay audit count."""
    return {e["child_intake_id"] for e in load_events()
            if e["event_type"] == "CHILD_CLASSIFIED_UNRELATED_REPLAY"}


def left_unlinked_children():
    """Children Martyn resolved as intentionally unlinked (a decision — not an unresolved blocker)."""
    return {e["child_intake_id"] for e in load_events() if e["event_type"] == "CHILD_LEFT_UNLINKED"}


def confirmed_links():
    """Only CONFIRMED links (and not later REJECTED) are authoritative; PROPOSED never auto-applies."""
    conf, rej = {}, set()
    for e in load_events():
        if e["event_type"] == "PARENT_LINK_CONFIRMED":
            conf[e["child_intake_id"]] = e["parent_signal_id"]
        elif e["event_type"] == "PARENT_LINK_REJECTED":
            rej.add((e["child_intake_id"], e["parent_signal_id"]))
    return {c: p for c, p in conf.items() if (c, p) not in rej}
