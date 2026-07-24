"""Automatic BLIND hypothesis generator — deterministic, causal-only, research-only.

READS ONLY the frozen PRE_TRADE_SNAPSHOT (which itself contains only causal features derived from
bars ts < signal). It NEVER reads: future bars, outcome, later management, result claims,
retrospective videos, Farouk's later explanation, or post-outcome analysis. It performs NO
follower arithmetic and cannot change any follower state.

Frozen methodology (methodology_v0_1, sha-pinned): forms Orange's OWN structural read from the
snapshot's HTF bias + CHoCH/BOS + sweeps + candidate OB/FVG zones + session, then states whether it
agrees with the Farouk-posted setup. Bounded by a wall-clock deadline; any failure is surfaced as a
typed exception so the watcher can record HYPOTHESIS_NOT_GENERATED with the reason.
"""
from __future__ import annotations

import hashlib
import json
import time
from decimal import Decimal as D

METHODOLOGY_VERSION = "methodology_v0_1"
DEADLINE_SECONDS = 5.0
UNKNOWN = "UNKNOWN"

# frozen rule text (pinned so it can't be tuned to fit outcomes)
_RULES = {
    "direction": "LONG if HTF bias BULLISH and latest CHoCH/BOS bullish; SHORT if both bearish; "
                 "else the HTF bias alone with reduced confidence; UNKNOWN if HTF bias UNKNOWN",
    "strongest_zone": "nearest causal candidate OB zone (else FVG) in the read direction; "
                      "else the Farouk-posted zone flagged AS_POSTED_ONLY",
    "invalidation": "beyond the far edge of the chosen zone / opposite structure",
    "confidence": "HIGH if HTF+CHoCH+sweep all align; MEDIUM if two align; LOW otherwise",
}
METHODOLOGY_SHA = hashlib.sha256(json.dumps(_RULES, sort_keys=True).encode()).hexdigest()

FORBIDDEN_SNAPSHOT_KEYS = ("outcome", "realized", "unrealized", "result", "video",
                           "retrospective", "final")


class HypothesisTimeout(Exception):
    pass


class HypothesisMalformed(Exception):
    pass


class MissingFeatures(Exception):
    pass


def _bias_dir(bias):
    return {"BULLISH": "LONG", "BEARISH": "SHORT"}.get(bias, UNKNOWN)


def _choch_dir(choch):
    if not isinstance(choch, dict):
        return UNKNOWN
    t = choch.get("type", "")
    if "BULLISH" in t:
        return "LONG"
    if "BEARISH" in t:
        return "SHORT"
    return UNKNOWN


def generate(snapshot: dict, now_ts: int, deadline_s: float = DEADLINE_SECONDS, _slow=None) -> dict:
    """Return a provisional hypothesis dict. Raises HypothesisTimeout / MissingFeatures /
    HypothesisMalformed on failure. Pure w.r.t. the snapshot (no external reads)."""
    start = time.monotonic()
    if _slow is not None:
        time.sleep(_slow)                      # test hook to force a deadline breach
    # causal-integrity guard: the snapshot must NOT carry outcome/future/video keys
    blob = json.dumps(snapshot, default=str).lower()
    for tok in ("outcome_status", "realized_pips", "unrealized_pips", "retrospective_video",
                "result_claim"):
        if tok in blob:
            raise HypothesisMalformed(f"snapshot carries forbidden non-causal key '{tok}'")
    feats = snapshot.get("causal_features")
    if not isinstance(feats, dict):
        raise HypothesisMalformed("snapshot missing causal_features")
    bias = feats.get("htf_bias", UNKNOWN)
    if bias == UNKNOWN and feats.get("causal_bar_count", 0) < 50:
        raise MissingFeatures("HTF bias UNKNOWN and < 50 causal bars — insufficient structure")
    bdir = _bias_dir(bias)
    cdir = _choch_dir(feats.get("latest_choch_bos"))
    posted_dir = snapshot.get("direction", UNKNOWN)
    # Orange's independent read
    if bdir != UNKNOWN and cdir != UNKNOWN and bdir == cdir:
        exp_dir, agree_signals = bdir, 2
    elif bdir != UNKNOWN:
        exp_dir, agree_signals = bdir, 1
    else:
        exp_dir, agree_signals = UNKNOWN, 0
    sweep = feats.get("latest_sweep_low") if exp_dir == "LONG" else feats.get("latest_sweep_high")
    if isinstance(sweep, dict):
        agree_signals += 1
    # strongest candidate zone from causal OB/FVG in the read direction
    zone = UNKNOWN
    obs = feats.get("candidate_ob_zones")
    want_ob = "BULLISH_OB" if exp_dir == "LONG" else "BEARISH_OB"
    if isinstance(obs, list):
        cand = [o for o in obs if o.get("kind") == want_ob]
        if cand:
            z = cand[-1]
            zone = f"{z['zone_low']}-{z['zone_high']} (causal {want_ob})"
    if zone == UNKNOWN:
        zone = f"{snapshot.get('zone', UNKNOWN)} (AS_POSTED_ONLY — no causal OB in read direction)"
    confidence = "HIGH" if agree_signals >= 3 else "MEDIUM" if agree_signals == 2 else "LOW"
    if time.monotonic() - start > deadline_s:
        raise HypothesisTimeout(f"generation exceeded {deadline_s}s deadline")
    return {
        "expected_direction": exp_dir,
        "agrees_with_posted_setup": (exp_dir == posted_dir) if exp_dir != UNKNOWN else UNKNOWN,
        "strongest_candidate_zone": zone,
        "invalidation": (f"beyond far edge of {zone}" if zone != UNKNOWN else UNKNOWN),
        "structural_rationale": {"htf_bias": bias, "choch": feats.get("latest_choch_bos"),
                                 "sweep_aligned": isinstance(sweep, dict), "session": feats.get("session"),
                                 "signals_aligned": agree_signals, "rules": _RULES},
        "confidence": confidence,
        "alternative_hypothesis": {"direction": ("SHORT" if exp_dir == "LONG" else "LONG"
                                                 if exp_dir == "SHORT" else UNKNOWN),
                                   "note": "opposite read if structure flips before entry"},
        "unknowns": ["actual fills", "personal stop", "OB validity confirmation", "Farouk's intent"],
        "snapshot_hash": snapshot.get("logical_hash", UNKNOWN),
        "methodology_version": METHODOLOGY_VERSION, "methodology_sha256": METHODOLOGY_SHA,
        "generated_at_utc": now_ts, "generation_ms": int((time.monotonic() - start) * 1000),
    }
