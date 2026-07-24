"""
Route-level provider authorisation — advisory, FAIL CLOSED. Separates the shared Telegram TRANSPORT
(the "Whale Room" forwarder, which carries many traders and must never grant eligibility) from the exact
forwarded SOURCE ROUTE (the dedicated sea-scalper-farouk source room). Nothing here enables/constructs/
sends a broker order or issues a permit/lease.

Concepts:
  TRANSPORT_SENDER      - the Telegram sender id that delivered the post (the forwarder channel)
  SOURCE_PROVIDER_ROUTE - the exact source room parsed from the machine forwarding wrapper
  SOURCE_POSTER_LABEL   - the poster handle in the wrapper (recorded, NEVER trusted as personal identity)
  CONTENT_PAYLOAD       - the message body, separated from the forwarding header

The route is NOT authorised by this task. Farouk's route is a CANDIDATE pending operator confirmation.
"""
from __future__ import annotations
import re

# the shared forwarder is recognised ONLY as a transport — never eligibility by itself
AUTHORISED_FORWARD_TRANSPORT_IDS = {-1001937743421}     # "The Whale Room"

CANONICAL_FAROUK_ROUTE = "sea-scalper-farouk"

# ROUTE-LEVEL authorisation. Martyn confirmed the exact normalized source route on 2026-07-03. This is
# NOT confirmation of Farouk's personal Telegram identity (personal_sender_verified stays False).
PROVIDER_AUTHORISATION_TYPE = "ROUTE_LEVEL"

# operator-CONFIRMED provider routes (exact normalized source rooms). The shared transport id is NEVER
# added here — only the source route grants (route-level) eligibility.
AUTHORISED_PROVIDER_ROUTES = ("sea-scalper-farouk",)

# route authorisation applies PROSPECTIVELY ONLY from this activation timestamp — no historical replay.
import calendar as _cal
import time as _t
ROUTE_ACTIVATION_TS_UTC = "2026-07-03T20:30:00Z"
ROUTE_ACTIVATION_TS_MS = _cal.timegm(_t.strptime(ROUTE_ACTIVATION_TS_UTC, "%Y-%m-%dT%H:%M:%SZ")) * 1000

# recognised machine-generated forwarding wrapper. Header line:  "<poster> Posted in <emoji>・<room>"
# the U+30FB katakana middle dot is the machine separator; a hand-typed "Posted in sea-scalper-farouk"
# lacks the emoji・ structure and the \n\n content split, so it fails wrapper validation.
_MIDDOT = "・"
_HEADER_RE = re.compile(r"^(?P<poster>\S.*?)\s+Posted in\s+(?P<rooms>.+?)\s*$")
_ROOM_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")


def normalize_room(s):
    """Harmless-formatting normalisation only: take the slug after the machine middot, lower + trim."""
    if not s:
        return None
    part = s.split(_MIDDOT)[-1].strip().lower()
    part = re.sub(r"\s+", "", part)
    return part or None


def parse_forward_envelope(raw_text):
    """Split the machine forwarding wrapper into poster / source room / content. wrapper_valid is True
    only for the exact machine format (header 'X Posted in <emoji>・<room>' + blank-line content split)."""
    out = {"wrapper_valid": False, "source_poster_label": None, "source_room_raw": None,
           "source_room_normalized": None, "content_payload": None}
    if not raw_text:
        return out
    first = raw_text.split("\n", 1)[0]
    m = _HEADER_RE.match(first)
    if not m:
        return out
    rooms_part = m.group("rooms").strip()
    if _MIDDOT not in rooms_part:                        # must use the machine middot separator
        return out
    room_norm = normalize_room(rooms_part)
    if not room_norm or not _ROOM_SLUG_RE.match(room_norm):
        return out
    # content must be separated from the header by a blank line (machine wrapper always does this)
    if "\n\n" not in raw_text:
        return out
    content = raw_text.split("\n\n", 1)[1]
    out.update({"wrapper_valid": True, "source_poster_label": m.group("poster").strip(),
                "source_room_raw": rooms_part, "source_room_normalized": room_norm,
                "content_payload": content})
    return out


def _as_int(v):
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def authorise_route(*, sender_id, fwd_present, raw_text, posted_ms=None, activation_ms=None,
                    confirmed_routes=None):
    """Full route-authorisation decision. FAIL CLOSED. Returns the separated authorisation record."""
    confirmed = tuple(confirmed_routes) if confirmed_routes is not None else AUTHORISED_PROVIDER_ROUTES
    codes = []
    sid = _as_int(sender_id)
    transport_ok = sid in AUTHORISED_FORWARD_TRANSPORT_IDS
    if not transport_ok:
        codes.append("UNRECOGNISED_TRANSPORT")
    if not fwd_present:
        codes.append("FWD_METADATA_MISSING")
    env = parse_forward_envelope(raw_text)
    if not env["wrapper_valid"]:
        codes.append("FORWARD_WRAPPER_INVALID")
    room = env["source_room_normalized"]
    newer = (activation_ms is None) or (posted_ms is not None and posted_ms >= activation_ms)
    if not newer:
        codes.append("BEFORE_ADVISORY_ACTIVATION")
    # STRICT forward-envelope: transport + fwd metadata + machine wrapper + content split + newer
    strict = bool(transport_ok and fwd_present and env["wrapper_valid"]
                  and env["content_payload"] is not None and newer)
    is_farouk_route = bool(strict and room == CANONICAL_FAROUK_ROUTE)
    # route authorisation is PROSPECTIVE ONLY — the message must be newer than the route activation ts
    route_active = (posted_ms is None) or (posted_ms >= ROUTE_ACTIVATION_TS_MS)
    route_authorised = bool(is_farouk_route and room in confirmed and route_active)

    if route_authorised:
        status = "PROVIDER_ROUTE_AUTHORISED"
    elif is_farouk_route and (room in confirmed) and not route_active:
        status = "PROVIDER_ROUTE_CANDIDATE"          # confirmed route, but predates activation
        codes.append("BEFORE_ROUTE_ACTIVATION")
    elif is_farouk_route:
        status = "PROVIDER_ROUTE_CANDIDATE"
        codes.append("OPERATOR_CONFIRMATION_REQUIRED")
    else:
        status = "UNAUTHORISED_PROVIDER_ROUTE"
        if transport_ok and env["wrapper_valid"] and room != CANONICAL_FAROUK_ROUTE:
            codes.append("UNAUTHORISED_PROVIDER_ROUTE")   # a different, non-Farouk source room

    return {
        "provider_authorisation_type": PROVIDER_AUTHORISATION_TYPE,
        "transport_authorised": transport_ok,
        "provider_route_authorised": route_authorised,
        "personal_sender_verified": False,               # NEVER claim the personal poster is Farouk
        "source_poster_label": env["source_poster_label"],
        "source_room_raw": env["source_room_raw"],
        "source_room_normalized": room,
        "forward_metadata_present": bool(fwd_present),
        "wrapper_valid": env["wrapper_valid"],
        "content_payload": env["content_payload"],
        "route_status": status,
        "authorisation_reason_codes": codes,
        # hard gates for the advisory bridge (unauthorised route => no eligibility / proposal / campaign)
        "execution_eligible": route_authorised,
        "may_create_proposal": route_authorised,
        "no_campaign": (not route_authorised),
        "no_broker_action": True,
    }
