"""
MPK-2A two-gate permission model + time-versioned historical resolver.

Two INDEPENDENT gates:
  GATE A — EVIDENCE CAPTURE   : DENIED | CONTEXT_ONLY | CAPTURE_ALLOWED
  GATE B — CAMPAIGN-STATE     : DENIED | REVIEW_REQUIRED | TRACKED_PROVIDER

Capture permission and campaign-state (tracking) permission are independent: being
captured never grants tracking. Fail-closed defaults for any sender/channel with no
explicit grant: capture = CONTEXT_ONLY, tracking = DENIED.

Permissions are append-only, time-versioned snapshots stored in channel_permission_events.
The resolver answers "what applied at timestamp T?" using only events whose effective_from
is <= T, so a provider promoted today gains NO retroactive permission over yesterday's
messages. Pure read; no writes.
"""
from __future__ import annotations

# Gate A — evidence capture
CAPTURE_DENIED = "DENIED"
CAPTURE_CONTEXT_ONLY = "CONTEXT_ONLY"
CAPTURE_ALLOWED = "CAPTURE_ALLOWED"
CAPTURE_STATES = (CAPTURE_DENIED, CAPTURE_CONTEXT_ONLY, CAPTURE_ALLOWED)

# Gate B — campaign-state (tracking)
TRACK_DENIED = "DENIED"
TRACK_REVIEW_REQUIRED = "REVIEW_REQUIRED"
TRACK_TRACKED_PROVIDER = "TRACKED_PROVIDER"
TRACK_STATES = (TRACK_DENIED, TRACK_REVIEW_REQUIRED, TRACK_TRACKED_PROVIDER)

# fail-closed defaults (no explicit grant)
DEFAULT_CAPTURE = CAPTURE_CONTEXT_ONLY
DEFAULT_TRACKING = TRACK_DENIED

# sentinel channel for provider-wide (not channel-specific) permission grants
PROVIDER_WIDE = "__PROVIDER_WIDE__"

# provider lifecycle
STATUS_ACTIVE = "ACTIVE"
STATUS_PAUSED = "PAUSED"
STATUS_RETIRED = "RETIRED"


def effective_permission(con, provider_id, at_timestamp, channel_id=PROVIDER_WIDE):
    """Resolve the (capture, tracking) gates effective at `at_timestamp`.

    Considers channel-specific events for `channel_id` AND provider-wide events; the most
    recent (effective_from <= at) wins, with channel-specific overriding provider-wide at an
    equal effective_from. Returns fail-closed defaults when nothing applies. Read-only.
    """
    rows = con.execute(
        "SELECT capture_status, tracking_status, effective_from_utc, immutable_channel_id, "
        "created_at_utc, permission_event_id FROM channel_permission_events "
        "WHERE provider_id=? AND immutable_channel_id IN (?, ?) AND effective_from_utc <= ? ",
        (provider_id, channel_id, PROVIDER_WIDE, at_timestamp)).fetchall()
    if not rows:
        return {"capture_status": DEFAULT_CAPTURE, "tracking_status": DEFAULT_TRACKING,
                "source": "DEFAULT"}

    def rank(r):
        # later effective_from wins; channel-specific (not sentinel) breaks ties; then created_at
        specificity = 0 if r[3] == PROVIDER_WIDE else 1
        return (r[2], specificity, r[4] or "", r[5])

    best = max(rows, key=rank)
    return {"capture_status": best[0], "tracking_status": best[1],
            "source": "EVENT", "effective_from": best[2], "channel_scope": best[3]}


def provider_status_at(con, provider_id, at_timestamp):
    """Resolve provider lifecycle status (ACTIVE/PAUSED/RETIRED) at a timestamp. Default ACTIVE."""
    rows = con.execute(
        "SELECT status, effective_from, created_at FROM provider_status_events "
        "WHERE provider_id=? AND effective_from <= ? ", (provider_id, at_timestamp)).fetchall()
    if not rows:
        return STATUS_ACTIVE
    return max(rows, key=lambda r: (r[1], r[2] or ""))[0]
