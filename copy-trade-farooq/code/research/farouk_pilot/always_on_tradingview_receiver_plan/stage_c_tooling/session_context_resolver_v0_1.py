"""SESSION CONTEXT RESOLVER v0.1 — OFFLINE / OBSERVATION-ONLY.

Maps a UTC timestamp to a trading-session label using an EXPLICIT policy config.
If the policy is not `confirmed` (e.g. chart timezone unresolved), the resolver still
returns a proxy label but marks it SESSION_UNCONFIRMED and confidence UNCONFIRMED — it
never asserts a confirmed session on unvalidated data.

NON-NEGOTIABLE (enforced by construction):
  * Output is candidate-only; execution / broker / qst / order_intent / risk_sizing = False.
  * No invented session rules: windows come from the passed policy (see FAROUK_SESSION_POLICY).
  * Offline, pure function. No network, no broker/cTrader/QST.

This module changes nothing about NOT_INTEGRATION_READY.
"""

import datetime as dt

RESOLVER_VERSION = "session_context_resolver_v0_1"

# Default policy — grounded in corpus (London open 08:00Z; NY 13:30-15:00Z) BUT the chart/
# Discord timezone is UNRESOLVED, so confirmed=False and every label is a proxy.
# Windows are [start, end) in UTC hours (floats allow :30). Asia is NOT explicitly defined
# in the corpus as 00:00-07:00 -> marked partially_supported and confidence LOW.
DEFAULT_SESSION_POLICY = {
    "policy_version": "FAROUK_SESSION_POLICY_v0_1",
    "timezone": "UTC",
    "confirmed": False,                 # timezone policy unconfirmed -> proxies only
    "dst_handled": False,
    "sessions": [
        # label,                 start_utc, end_utc, support
        # Asia clock window is NOT in the corpus (Asia is a liquidity LEVEL only) -> unsupported.
        {"label": "ASIA_UTC_PROXY",     "start": 0.0,  "end": 8.0,  "support": "unsupported_proxy"},
        # "London open 08:00 UTC" is documented (Playbook) but no close; TZ unreconciled.
        {"label": "LONDON_UTC_PROXY",   "start": 8.0,  "end": 13.5, "support": "corpus_open_only"},
        # "NY open 13:30 UTC; NY window 13:30-15:00 UTC" (R-NY-1330) — family-scoped, not TZ authority.
        {"label": "NEW_YORK_UTC_PROXY", "start": 13.5, "end": 21.0, "support": "corpus_window"},
        {"label": "OFF_SESSION_UTC_PROXY", "start": 21.0, "end": 24.0, "support": "none"},
    ],
}


def _parse(ts):
    if not ts:
        return None
    s = str(ts).strip().rstrip("Z")
    if "." in s:
        s = s[:26]
        fmt = "%Y-%m-%dT%H:%M:%S.%f"
    else:
        fmt = "%Y-%m-%dT%H:%M:%S"
    try:
        return dt.datetime.strptime(s, fmt).replace(tzinfo=dt.timezone.utc)
    except ValueError:
        return None


def _safe_flags():
    return {
        "candidate_only": True,
        "execution_allowed": False,
        "broker_execution_allowed": False,
        "qst_allowed": False,
        "order_intent": False,
        "risk_sizing_allowed": False,
    }


def resolve_session(timestamp_utc, policy=None):
    """Map a UTC timestamp to a session label per `policy`. Returns a dict."""
    policy = policy or DEFAULT_SESSION_POLICY
    warnings = []
    rec = {
        "resolver_version": RESOLVER_VERSION,
        "timestamp_utc": timestamp_utc,
        "policy_version": policy.get("policy_version"),
        "session_label": None,
        "session_window": None,
        "session_confidence": "UNCONFIRMED",
        "warnings": warnings,
    }
    rec.update(_safe_flags())

    at = _parse(timestamp_utc)
    if at is None:
        warnings.append("unparseable timestamp_utc; no session resolved (not fabricated)")
        rec["session_label"] = "SESSION_UNRESOLVED"
        return rec

    hour = at.hour + at.minute / 60.0
    matched = None
    for s in policy.get("sessions", []):
        if s["start"] <= hour < s["end"]:
            matched = s
            break
    if matched is None:
        rec["session_label"] = "SESSION_UNRESOLVED"
        warnings.append("timestamp did not fall in any policy session window")
        return rec

    rec["session_label"] = matched["label"]
    rec["session_window"] = f"{matched['start']:04.1f}-{matched['end']:04.1f} UTC"

    if not policy.get("confirmed", False):
        warnings.append("SESSION_UNCONFIRMED: timezone policy not validated; label is a proxy")
        rec["session_confidence"] = "UNCONFIRMED"
    else:
        # even confirmed policy: Asia is only partially supported in the corpus
        supp = matched.get("support", "none")
        rec["session_confidence"] = {
            "corpus_window": "MEDIUM", "corpus_open_only": "LOW",
            "unsupported_proxy": "NONE", "none": "NONE",
        }.get(supp, "LOW")
    if not policy.get("dst_handled", False):
        warnings.append("DST not handled; windows assume no daylight-saving shift")
    return rec


if __name__ == "__main__":
    import json
    import sys
    print(json.dumps(resolve_session(sys.argv[1] if len(sys.argv) > 1 else "2026-07-09T04:12:00Z"),
                     indent=2))
