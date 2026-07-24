"""
Console adapter (READ-ONLY): reads the immutable review sidecars + append-only parent-link events and
builds derived EffectiveTrades + timelines. Never mutates an original record. Current real records
carry no confirmed entry/stop fields and no broker events, so their derived state is SIGNAL_CAPTURED /
NO_BROKER_EXECUTION with UNLINKED blockers until Martyn links + demo execution occurs.
"""
from __future__ import annotations
import glob
import json
import os

import effective_view as EV
import timeline_api
import history_repair
from lc_models import SignalRef, ChildEvent

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_REVIEW = os.path.join(_ROOT, "data", "manual_image_intake_v1", "review")
_LINKLOG = os.path.join(_ROOT, "data", "manual_image_intake_v1", "parent_link_events.jsonl")
_PROV = {"seascalper": "farouk", "seascalperfarouk": "farouk", "@whale": "farouk", "whale": "farouk"}


def _canon_provider(p):
    return _PROV.get((p or "").lower().replace(" ", ""), (p or "").lower() or None)


def _ts(s):
    try:
        import calendar
        import time
        return int(calendar.timegm(time.strptime(s, "%Y-%m-%dT%H:%M:%SZ"))) * 1000
    except Exception:
        return None


def _explicit_links():
    links = {}
    if os.path.exists(_LINKLOG):
        for ln in open(_LINKLOG, encoding="utf-8"):
            try:
                d = json.loads(ln)
                links[d.get("child_intake_id")] = d.get("parent_observation_id")
            except Exception:
                pass
    return links


def _latest_sidecar_by_intake(review):
    """Return {intake_id: latest review dict} — one effective record per intake (latest review wins),
    so a re-reviewed intake is never counted as both parent and child."""
    latest = {}
    for p in sorted(glob.glob(os.path.join(review, "*.json")), key=os.path.getmtime):
        try:
            d = json.load(open(p, encoding="utf-8"))
        except Exception:
            continue
        latest[d.get("intake_id")] = d               # later mtime overwrites -> latest wins
    return latest


def load_records(root=None):
    """Effective records. Children classified as UNRELATED_REPLAY are excluded from Gold entirely
    (they stay in immutable history). CONFIRMED parent links are applied."""
    review = os.path.join(root, "data", "manual_image_intake_v1", "review") if root else _REVIEW
    links = dict(_explicit_links()); links.update(history_repair.confirmed_links())
    unrelated = history_repair.unrelated_replay_children()
    left = history_repair.left_unlinked_children()
    reclass = history_repair.confirmed_classifications()     # confirmed SIGNAL->TRADE_RESULT etc.
    corrections = history_repair.confirmed_corrections()     # confirmed field values per signal
    result_cards = history_repair.classification_result_cards()
    signals, children, pending = [], [], []
    for iid, d in _latest_sidecar_by_intake(review).items():
        cls = reclass.get(iid) or d.get("intake_class") or d.get("semantic_class")   # confirmed reclass wins
        f = d.get("fields", {})
        g = lambda k: (f.get(k) or {}).get("value")
        corr = corrections.get(iid, {})
        gc = lambda k, dflt: ((corr.get(k) or {}).get("value") if corr.get(k) else dflt)  # confirmed value wins
        prov = _canon_provider((d.get("provider") or {}).get("value"))
        ts = _ts(d.get("review_created_at_utc"))
        if cls in ("SIGNAL", "SIGNAL_ANNOUNCEMENT"):
            signals.append(SignalRef(signal_id=iid, instrument=(gc("instrument", g("instrument")) or "XAUUSD"),
                                     direction=gc("direction", g("direction")), provider=prov,
                                     entry_low=gc("entry_low", g("entry_low")),
                                     entry_high=gc("entry_high", g("entry_high")),
                                     stop=gc("stop", g("stop_price")), confirmed=True, ts_ms=ts, replay=True))
        elif cls in ("TRADE_UPDATE", "TRADE_RESULT"):
            if iid in unrelated:
                continue                                 # unrelated replay -> not a Gold child
            rc = result_cards.get(iid) or {}             # enrich a reclassified result child for matching
            children.append(ChildEvent(child_id=iid, child_class=cls, instrument="XAUUSD",
                                       direction=rc.get("direction"), provider=prov, ts_ms=ts,
                                       explicit_parent_signal_id=links.get(iid),
                                       instruction_kind=("PROVIDER_REPORTED_RESULT" if cls == "TRADE_RESULT" else None),
                                       replay=True))
        else:
            pending.append(iid)
    return signals, children, pending


def unlinked_children_with_candidates(root=None):
    """For every currently-unresolved unlinked Gold child, compute candidate parents (with match
    evidence incl. price-in-zone). Live — surfaces newly-reclassified result children even though no
    PARENT_LINK_PROPOSED event exists for them yet."""
    signals, children, _pending = load_records(root)
    left = history_repair.left_unlinked_children()
    result_cards = history_repair.classification_result_cards()
    parent_meta = [{"signal_id": s.signal_id, "instrument": s.instrument, "direction": s.direction,
                    "provider": s.provider, "ts_ms": s.ts_ms, "entry_low": s.entry_low,
                    "entry_high": s.entry_high} for s in signals]
    out = []
    for c in children:
        if c.explicit_parent_signal_id or c.child_id in left:
            continue                                     # resolved (linked or intentionally unlinked)
        rc = result_cards.get(c.child_id) or {}
        cm = {"instrument": c.instrument, "direction": c.direction, "provider": c.provider,
              "ts_ms": c.ts_ms, "entry_candidate": rc.get("entry_candidate")}
        out.append({"child_intake_id": c.child_id, "child_class": c.child_class,
                    "provider": c.provider, "result_card": rc,
                    "candidates": history_repair.link_candidates(cm, parent_meta)})
    return out


def effective_counts(root=None):
    """SINGLE SOURCE OF TRUTH for every derived dashboard count. Both the top queue strip and the
    lifecycle panel read this so they always agree."""
    signals, children, pending = load_records(root)          # children already exclude unrelated replay
    unrelated = history_repair.unrelated_replay_children()
    left = history_repair.left_unlinked_children()
    linked = {c.child_id for c in children if c.explicit_parent_signal_id}
    # true unresolved unlinked = Gold children with no confirmed link and not intentionally left unlinked
    unresolved = [c.child_id for c in children if not c.explicit_parent_signal_id and c.child_id not in left]
    denom = len(children)                                    # excludes unrelated replay
    return {
        "pending_intake_review": pending,
        "gold_children": [c.child_id for c in children],
        "unrelated_replay_children": sorted(unrelated),
        "left_unlinked_children": sorted(left & {c.child_id for c in children}),
        "linked_children": sorted(linked),
        "unlinked_updates_results": unresolved,             # the ONE authoritative unlinked list
        "parent_link_coverage": f"{len(linked)}/{denom}",
        "signal_count": len(signals),
    }


def build_timelines(root=None):
    signals, children, _pending = load_records(root)
    out = {}
    for s in signals:
        eff, seq = EV.build_effective_trade(s, children)
        out[s.signal_id] = timeline_api.build_timeline(eff, seq)
    return out


def inspect(root=None):
    ec = effective_counts(root)                              # single source of truth
    tls = build_timelines(root)
    linked = {sid: t["linked_updates"] + t["linked_results"] for sid, t in tls.items()}
    reconstructable = [sid for sid, t in tls.items()
                       if t["current_state"] not in ("SIGNAL_CAPTURED", "NO_BROKER_EXECUTION")]
    unknown = [sid for sid, t in tls.items()
               if t["current_state"] in ("SIGNAL_CAPTURED", "NO_BROKER_EXECUTION")
               or t["final_outcome"] in (None, "OPEN_UNRESOLVED", "PROVIDER_INSTRUCTION_ONLY")]
    return {
        "signal_count": ec["signal_count"], "child_count": len(ec["gold_children"]),
        "signals_with_linked_children": {sid: v for sid, v in linked.items() if v},
        "unlinked_updates_results": ec["unlinked_updates_results"],
        "unrelated_replay_children": ec["unrelated_replay_children"],
        "imported_pending_review": ec["pending_intake_review"],
        "reconstructable_lifecycles": reconstructable,
        "genuinely_unknown_outcomes": unknown,
        "parent_link_coverage": ec["parent_link_coverage"],
    }
