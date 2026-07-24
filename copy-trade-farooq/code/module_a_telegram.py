"""
module_a_telegram.py — Module A: the Signal Listener (Telegram path).

================================  PREVIEW ONLY  ================================
This watches a Telegram channel you are a member of and, when a new message
arrives, PRINTS it so you can see what the listener WOULD have captured.

It is NOT connected to the trading pipeline. It does not parse, size, log, or
trade anything. It catches a message and prints it — that is all it does today.

Going live (handing messages to the Module B parser) is a single, clearly-marked
line below that is deliberately left disabled. You and your guide will enable it
together, on purpose, after the manual pipeline has been proven on a real signal.
===============================================================================

How it reads Telegram:
  It uses Telethon — a "user client" that logs in AS YOU and can read channels
  you're already a member of. This is the safer automated route (unlike reading
  Discord with a user account, which is against Discord's rules — see
  module_a_discord.py).

What you need first (see the README for step-by-step):
  * The 'telethon' library:        pip install telethon
  * Two credentials, set as environment variables (NEVER hardcoded):
        TELEGRAM_API_ID
        TELEGRAM_API_HASH
    Get them from https://my.telegram.org  ->  "API development tools".
  * The channel to watch, set as TELEGRAM_CHANNEL in config.py.

Run it with:
    python module_a_telegram.py             # watch the channel(s) in PREVIEW mode
    python module_a_telegram.py --list      # list channels/groups you're in + their IDs
    python module_a_telegram.py --history 500   # back-log the last 500 messages (review only)

The --list helper is read-only: it logs in, prints every channel/group your
account belongs to with its numeric ID, then exits. Use it to find the ID of a
PRIVATE channel that has no public @username.

The --history mode is also read-only to Telegram: it pulls the last N PAST
messages from the configured channel, prints each one, and shows what it WOULD be
classified as (clean signal / commentary / REVIEW) by the existing parser +
router + quality filter — then writes a reviewable history_review.csv with clean,
dedicated columns. It does NOT log anything to paper_log.csv; you review the CSV
and decide. Optional flags:  --sender <name>  (isolate one poster),  --no-parse
(skip the LLM, heuristic only),  --out <file>  (choose the review file). The count
is capped and Telegram's FloodWait cool-down is respected — one careful fetch.

It also captures OUTCOMES: for each clean entry signal it looks at the later
messages on the SAME asset (after the entry, before the next entry on that asset)
for result cues — "tp1 hit"/"all tp hit" (win), "sl hit"/"stopped out" (loss),
"sl to entry"/"breakeven" (breakeven — NOT a loss), "+X pips" (win), "no fill"
(missed) — and writes two columns, DetectedOutcome and OutcomeEvidence (the exact
follow-up text it matched), so you can VERIFY each before trusting it. It is
conservative: anything it can't confidently match is left "unclear" with no
evidence — it never guesses, and never auto-logs.
"""

import asyncio
import csv
import os
import re
import sys
from datetime import datetime, timedelta

import config

# How long a FloodWait we're willing to simply sleep through (and retry ONCE).
# Anything longer than this we report and exit — we never sit blocked for hours,
# and we never retry in a tight loop (that's what re-triggers a ban).
_SHORT_WAIT_SECONDS = 60

# --- History back-log mode (--history) defaults -----------------------------
# A sensible default pull, and a hard cap so a typo can't ask for a huge fetch
# that hammers the API. Telethon paginates internally and (with the flood
# threshold below) auto-sleeps small FloodWaits; a big one is reported and we stop.
HISTORY_DEFAULT = 200
# Hard cap so a typo can't ask for an enormous fetch. Raised to allow a deliberate
# deep back-fill of a channel's full accessible history; Telethon still paginates
# internally and we still STOP on a big FloodWait (never hammer the API).
HISTORY_MAX = 100000
HISTORY_REVIEW_FILE = getattr(config, "HISTORY_REVIEW_FILE", "history_review.csv")

# Set by pull_for_archive: the FloodWait seconds if Telegram cut a fetch short
# (None if the fetch completed / exhausted the channel). Lets callers report honestly.
_LAST_PULL_FLOOD = None

# Clean, dedicated columns for the review CSV (sort/filter-friendly in Excel).
# DetectedOutcome / OutcomeEvidence are filled (for clean entry signals) by
# matching later management/result messages back to the entry — see below. They
# are an AID for you to VERIFY before trusting; nothing is auto-logged.
HISTORY_COLUMNS = [
    "Date", "Sender", "Asset", "Direction", "Entry", "Stop",
    "TP1", "TP2", "TP3", "Classification", "Confidence",
    "DetectedOutcome", "OutcomeEvidence", "RawMessage",
]

# Classification buckets.
CLASS_CLEAN = "clean signal"
CLASS_COMMENTARY = "commentary"
CLASS_REVIEW = "REVIEW"

# NOTE: the Module B parser is intentionally NOT imported and NOT called here.
# Keeping it disconnected is the whole point of PREVIEW mode. The single line
# that would connect it is shown (disabled) inside the handler below.
# import module_b_parser   # <-- uncomment together with the handoff line, to go live


def _friendly_stop(message: str):
    """Print a clear, plain-English reason we can't start, and return None."""
    print("\n  Can't start the listener yet:")
    print(f"  {message}\n")


def _console_safe(text) -> str:
    """
    Make a string safe to PRINT on the current console. Real Telegram messages
    are full of emoji and non-Latin characters; a Windows cp1252 console can't
    encode them and would crash. We replace anything the console can't show with
    '?' for DISPLAY only — the review CSV is written in UTF-8 and keeps the
    original text intact.
    """
    enc = getattr(sys.stdout, "encoding", None) or "utf-8"
    try:
        return str(text).encode(enc, errors="replace").decode(enc, errors="replace")
    except Exception:
        return str(text).encode("ascii", errors="replace").decode("ascii")


def _load_telethon():
    """Import Telethon, or print a friendly install hint. Returns (TelegramClient, events) or None."""
    try:
        from telethon import TelegramClient, events
        return TelegramClient, events
    except ImportError:
        _friendly_stop(
            "the 'telethon' library isn't installed.\n"
            "  Fix: open PowerShell and run:  pip install telethon"
        )
        return None


def _read_credentials():
    """Read TELEGRAM_API_ID / TELEGRAM_API_HASH from the environment. Returns (api_id, api_hash) or None."""
    api_id_raw = os.environ.get("TELEGRAM_API_ID")
    api_hash = os.environ.get("TELEGRAM_API_HASH")
    if not api_id_raw or not api_hash:
        _friendly_stop(
            "your Telegram credentials aren't set.\n"
            "  You need TELEGRAM_API_ID and TELEGRAM_API_HASH as environment\n"
            "  variables (see the README — same idea as the Anthropic key).\n"
            "  Get them from https://my.telegram.org -> 'API development tools'."
        )
        return None
    try:
        api_id = int(api_id_raw)
    except ValueError:
        _friendly_stop(
            f"TELEGRAM_API_ID should be a number, but it's set to '{api_id_raw}'.\n"
            "  Double-check what you copied from my.telegram.org."
        )
        return None
    return api_id, api_hash


def _format_duration(seconds: int) -> str:
    """Turn a wait in seconds into a friendly 'X minutes' / 'X hours' string."""
    seconds = int(seconds or 0)
    if seconds <= 0:
        return "a short while"
    if seconds < 60:
        return f"{seconds} second{'s' if seconds != 1 else ''}"
    minutes = seconds // 60
    if minutes < 60:
        return f"{minutes} minute{'s' if minutes != 1 else ''}"
    hours = minutes // 60
    rem_minutes = minutes % 60
    text = f"{hours} hour{'s' if hours != 1 else ''}"
    if rem_minutes:
        text += f" {rem_minutes} minute{'s' if rem_minutes != 1 else ''}"
    return text


def _report_flood_wait(seconds: int):
    """
    Explain a FloodWait in plain English and make clear we are STOPPING, not
    retrying. A FloodWait is Telegram's anti-abuse cool-down: the only safe thing
    to do is wait it out, so we report when to come back and exit cleanly.
    """
    human = _format_duration(seconds)
    resume_at = (datetime.now() + timedelta(seconds=int(seconds or 0))).strftime(
        "%Y-%m-%d %H:%M"
    )
    print("\n  Can't start the listener — Telegram asked us to slow down (FloodWait):")
    print(f"  Telegram has asked us to wait {human} before trying again.")
    print("  The script will NOT hammer the API. Stopping cleanly —")
    print(f"  try again after {resume_at}.")
    print("\n  (FloodWait is Telegram's normal rate-limit cool-down. Waiting it out")
    print("   is exactly what keeps the account safe. Just re-run the command after")
    print("   that time — do NOT keep retrying before then.)\n")


async def _make_client_and_login(TelegramClient, api_id, api_hash):
    """
    Build the client (reusing the saved session) and run the one-time login flow
    with plain-English prompts. Returns a connected, logged-in client, or None.

    This is an *async* coroutine and MUST be awaited from inside a running event
    loop (see run_preview / list_dialogs, which drive it via asyncio.run). The
    client is created here, inside that loop, so it binds to the loop that will
    actually run it — this is what keeps Python 3.14 from later complaining that
    the "event loop is closed" when the client tries to disconnect.
    """
    # Telethon raises FloodWaitError when Telegram tells us to back off. Import
    # it here (telethon is already known-importable by this point); fall back to a
    # never-matching dummy so this stays robust across telethon versions.
    try:
        from telethon.errors import FloodWaitError
    except Exception:  # pragma: no cover - telethon always provides this
        class FloodWaitError(Exception):
            seconds = 0

    client = TelegramClient(config.TELEGRAM_SESSION_NAME, api_id, api_hash)

    print("\nConnecting to Telegram...")
    print("If this is your first time, Telegram will send you a login code in the")
    print("Telegram app itself. Type it in when asked. (If you use 2-step")
    print("verification, you'll also be asked for that password.)\n")

    from getpass import getpass

    async def _attempt_login():
        """One single login attempt. May raise FloodWaitError or other errors."""
        await client.start(
            phone=lambda: input(
                "  Your Telegram phone number, with country code (e.g. +44...): "
            ).strip(),
            code_callback=lambda: input(
                "  Telegram just sent you a login code — type it here: "
            ).strip(),
            password=lambda: getpass(
                "  Your Telegram 2-step password (just press Enter if you don't use one): "
            ),
        )

    # ONE clean attempt. For a SHORT FloodWait we may wait it out and retry
    # exactly ONCE. We NEVER retry rapidly in a loop — that's what re-triggers a
    # ban — and we NEVER auto-sleep for long (hours) waits.
    already_retried = False
    while True:
        try:
            await _attempt_login()
            return client
        except KeyboardInterrupt:
            print("\n  Cancelled before logging in. Nothing was changed.")
            await client.disconnect()
            return None
        except FloodWaitError as e:
            seconds = int(getattr(e, "seconds", 0) or 0)
            if seconds <= _SHORT_WAIT_SECONDS and not already_retried:
                # Short cool-down: wait it out once, then a single retry.
                already_retried = True
                print(
                    f"\n  Telegram asked us to wait {_format_duration(seconds)} "
                    "(a short FloodWait)."
                )
                print("  Waiting it out once, then trying ONE more time...")
                await asyncio.sleep(seconds + 1)
                continue
            # Long wait, or we've already used our single retry: STOP cleanly.
            # Do not sleep for hours and do not retry again.
            _report_flood_wait(seconds)
            await client.disconnect()
            return None
        except Exception as e:
            # Any other auth/connection error: report clearly and STOP. No loop.
            _friendly_stop(
                f"couldn't log in to Telegram: {e}\n"
                "  Check your phone number, the code, your internet connection, and\n"
                "  that TELEGRAM_API_ID / TELEGRAM_API_HASH are correct."
            )
            await client.disconnect()
            return None


def run_preview():
    """Connect to Telegram and print (preview) every new message in the channel."""

    tele = _load_telethon()
    if not tele:
        return
    TelegramClient, events = tele

    creds = _read_credentials()
    if not creds:
        return
    api_id, api_hash = creds

    # --- Which channel(s)? --------------------------------------------------
    # TELEGRAM_CHANNEL may be a single value ("@thewhaleroom") or a list of them.
    raw = config.TELEGRAM_CHANNEL
    raw_items = raw if isinstance(raw, (list, tuple)) else [raw]
    channel_names = [str(c).strip() for c in raw_items if str(c).strip()]
    if not channel_names:
        return _friendly_stop(
            "no channel is set.\n"
            "  Open config.py and set TELEGRAM_CHANNEL to the channel's @username\n"
            "  (e.g. \"@thewhaleroom\") or its numeric ID (e.g. \"-1001234567890\").\n"
            "  You can watch several at once with a list, e.g.\n"
            "      TELEGRAM_CHANNEL = [\"@thewhaleroom\", \"-1001234567890\"]"
        )
    # Accept either a numeric ID or an @username for each entry.
    channels = [int(c) if c.lstrip("-").isdigit() else c for c in channel_names]

    # --- Banner -------------------------------------------------------------
    print("=" * 64)
    print("   SIGNAL LISTENER (Telegram)   —   PREVIEW MODE")
    print("=" * 64)
    print(f"   Watching channel(s) : {', '.join(channel_names)}")
    print(f"   Listener mode    : {config.LISTENER_MODE}")
    print("   PREVIEW observational capture is active.")
    print("   Allowlisted Telegram messages are stored as raw evidence in")
    print("   prospective_evidence_v1.db. Only safe metadata is printed; message")
    print("   content remains in the evidence database. Broker quotes are")
    print("   unavailable and remain NULL / BROKER_NOT_CONNECTED. No trading-pipeline")
    print("   handoff, sizing, scoring, broker connection or execution is enabled.")
    if _media_enabled():
        print("   Supported Telegram IMAGE bytes ARE preserved (the ORIGINAL Telegram-")
        print("   delivered bytes) into prospective_media_v1 — append-only, content-")
        print("   addressed, atomic. No OCR or image interpretation occurs. Unsupported")
        print("   media (video/audio/etc.) remains reference/status only. Execution disabled.")
    else:
        print("   Image-byte preservation is DISABLED (media references recorded only).")
    print("=" * 64)

    if config.LISTENER_MODE != "PREVIEW":
        # Even if someone flips config to LIVE, the handoff line below is still
        # commented out, so nothing actually connects. Make that explicit.
        print("\n  Note: LISTENER_MODE is not 'PREVIEW', but the handoff to the")
        print("  pipeline is still disabled in code. Running in preview anyway.\n")

    # All the Telegram work runs inside a single event loop owned by asyncio.run,
    # which creates it, runs the coroutine, and closes it cleanly afterwards. This
    # is the supported pattern on modern Python (3.14 included) and avoids the
    # "Event loop is closed" crash you get from the old sync-magic / manual-loop
    # approach.
    try:
        asyncio.run(_preview_async(TelegramClient, events, api_id, api_hash, channels))
    except KeyboardInterrupt:
        print("\n  Stopped listening. Nothing was parsed, logged, or traded.")


def _prospective_recorder():
    """GATE 1: build the observational prospective recorder (writes ONLY to
    prospective_evidence_v1.db). Lazy import so a plain preview without recording, and
    test imports, don't construct the DB. No broker, no network beyond Telegram read."""
    ce = os.path.join(os.path.dirname(os.path.abspath(__file__)), "campaign_extractor")
    if ce not in sys.path:
        sys.path.insert(0, ce)
    from prospective.prospective_db import ProspectiveDB
    from prospective.recorder import ProspectiveRecorder
    db_path = os.path.join(ce, "prospective", "data", "prospective_evidence_v1.db")
    return ProspectiveRecorder(ProspectiveDB(db_path))


def _record_prospective(recorder, event, allowed_chat_ids=None):
    """Persist one captured message as raw evidence (BEFORE any parsing) plus a
    BROKER_NOT_CONNECTED quote-context row. Observational only — NO fills/R/wins inferred,
    NO trading pipeline, NO broker. Raw content goes to the evidence DB, never to logs.

    NewMessage (message_event_type=CREATED) path. EDIT capture is wired separately
    (2026-07-21, D-028 fix): events.MessageEdited -> listener_edit_capture.py appends
    EDITED revisions append-only. Deletion capture remains NOT wired and NOT supported.

    CHANNEL ALLOWLIST (fail closed): if allowed_chat_ids is provided and the event's
    chat_id is not in it, refuse to record (raise PermissionError) — no row is created."""
    if allowed_chat_ids is not None and event.chat_id not in allowed_chat_ids:
        raise PermissionError(f"channel {event.chat_id} not on allowlist")
    from datetime import timezone
    msg = event.message
    raw = event.raw_text                     # None for a media-only message -> stored NULL
    media_ref = None
    if getattr(msg, "media", None) is not None:
        media_ref = f"media:{type(msg.media).__name__}:{getattr(msg, 'id', None)}"
    now = datetime.now(timezone.utc).isoformat()
    posted = msg.date.astimezone(timezone.utc).isoformat() if getattr(msg, "date", None) else None
    # capture the Telegram SENDER identity (a channel has many posters — provider authorisation needs
    # the stable numeric sender id; username/display where safe). NEVER inferred from message wording.
    sender_id = getattr(msg, "sender_id", None) or getattr(event, "sender_id", None)
    sender_username = sender_display = None
    try:
        _s = getattr(msg, "sender", None)
        if _s is not None:
            sender_username = getattr(_s, "username", None)
            _nm = ((getattr(_s, "first_name", None) or "") + " " + (getattr(_s, "last_name", None) or "")).strip()
            sender_display = _nm or getattr(_s, "title", None) or None
    except Exception:
        pass
    # forward-envelope metadata: whether the post is a Telegram FORWARD + a stable origin identifier.
    # Route authorisation requires genuine fwd_from metadata — a typed "Posted in ..." must not pass.
    fwd = getattr(msg, "fwd_from", None)
    is_forwarded = 1 if fwd is not None else 0
    fwd_origin = None
    try:
        if fwd is not None:
            _fid = getattr(fwd, "from_id", None)
            fwd_origin = (str(getattr(_fid, "channel_id", None) or getattr(_fid, "user_id", None) or _fid)
                          if _fid is not None else None)
            _cp = getattr(fwd, "channel_post", None)
            if _cp is not None:
                fwd_origin = (fwd_origin or "") + ":post" + str(_cp)
    except Exception:
        pass
    rec_msg = {"channel_id": str(event.chat_id), "message_id": getattr(msg, "id", None),
               "raw_text": raw, "media_reference": media_ref,
               "posted_at_utc": posted, "received_at_utc": now,
               "listener_observed_at_utc": now, "message_event_type": "CREATED",
               "sender_id": str(sender_id) if sender_id is not None else None,
               "sender_username": sender_username, "sender_display": sender_display,
               "is_forwarded": is_forwarded, "fwd_origin": fwd_origin}
    recorder.record_message(rec_msg)                              # raw evidence first/always
    recorder.record_quote_context(rec_msg["message_id"])         # broker NULL / BROKER_NOT_CONNECTED


def _media_enabled():
    """Phase 2B media-capture flag (default False). Lazy + import-safe."""
    try:
        ce = os.path.join(os.path.dirname(os.path.abspath(__file__)), "campaign_extractor")
        if ce not in sys.path:
            sys.path.insert(0, ce)
        from media_capture import config as _mcfg
        return bool(_mcfg.TELEGRAM_MEDIA_CAPTURE_ENABLED)
    except Exception:
        return False


def _media_components():
    """Lazily build (MediaDB, media_dir, max_bytes); creates the isolated prospective_media_v1.db
    + prospective_media_v1/ on first use. Returns None on any error so media NEVER blocks text."""
    try:
        ce = os.path.join(os.path.dirname(os.path.abspath(__file__)), "campaign_extractor")
        if ce not in sys.path:
            sys.path.insert(0, ce)
        from media_capture import config as _mcfg
        from media_capture.media_db import MediaDB
        os.makedirs(_mcfg.MEDIA_DIR, exist_ok=True)
        return (MediaDB(_mcfg.MEDIA_DB), _mcfg.MEDIA_DIR, _mcfg.TELEGRAM_MEDIA_MAX_BYTES)
    except Exception as e:
        print(f"  [media] components unavailable ({type(e).__name__}); image capture inactive")
        return None


async def _preserve_media(event, media_ctx, allowed_chat_ids):
    """Preserve supported Telegram IMAGE bytes AFTER the text row is committed. Guarded by the
    caller; any failure here is contained and never affects the committed text evidence."""
    if media_ctx is None:
        return "NO_MEDIA_CTX"
    if allowed_chat_ids is not None and event.chat_id not in allowed_chat_ids:
        return "OFF_ALLOWLIST"
    from datetime import timezone
    from media_capture import live_adapter
    msg = event.message
    media_db, media_dir, max_bytes = media_ctx
    grouped = getattr(msg, "grouped_id", None)
    posted = msg.date.astimezone(timezone.utc).isoformat() if getattr(msg, "date", None) else None
    identity = ("TELEGRAM", str(event.chat_id), str(getattr(msg, "id", None)), 1,
                str(grouped) if grouped else None, 0,
                f"media:{type(msg.media).__name__}:{getattr(msg, 'id', None)}")
    return await live_adapter.preserve_live(
        event.client, msg, media_db=media_db, media_dir=media_dir, max_bytes=max_bytes,
        identity=identity,
        timestamps={"posted_at": posted,
                    "received_at": datetime.now(timezone.utc).isoformat()})


async def _preview_async(TelegramClient, events, api_id, api_hash, channels):
    """Async core of the preview: log in, attach the capture handler, listen."""
    client = await _make_client_and_login(TelegramClient, api_id, api_hash)
    if client is None:
        return

    recorder = _prospective_recorder()        # GATE 1 (approved): observational capture on
    # CHANNEL ALLOWLIST (fail closed): only numeric configured channel ids may be recorded.
    allowed_ids = {c for c in channels if isinstance(c, int)}
    # GATE 1b (Phase 2B): supported image-byte preservation, only when the flag is True.
    media_ctx = _media_components() if _media_enabled() else None

    # ADD-2 (D-081): emit a liveness heartbeat every 60s so the EXTERNAL monitor (intake_observer)
    # and the pull backstop (operator brief) can detect a dead OR silently-disconnected listener.
    # This heartbeat is the ONLY in-listener part; all alarm logic is external. A dead listener
    # simply stops emitting -> the readers treat missing/stale as DOWN (never healthy-from-silence).
    try:
        import listener_liveness as _ll
    except Exception:                       # noqa: BLE001
        _ll = None
    _last = {"id": None, "ts": None}

    async def _heartbeat_loop():
        import os as _os
        while True:
            if _ll is not None:
                try:
                    _ll.write_heartbeat(_os.getpid(), client.is_connected(), _last["id"], _last["ts"])
                except Exception:           # noqa: BLE001 -- heartbeat must NEVER break capture
                    pass
            await asyncio.sleep(_ll.HEARTBEAT_INTERVAL_S if _ll else 60)

    @client.on(events.NewMessage(chats=channels))
    async def _handler(event):
        import hashlib as _hl
        stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        raw = event.raw_text                  # message CONTENT — never printed to terminal/logs
        safe_len = len(raw) if raw else 0
        safe_hash = _hl.sha256((raw or "").encode("utf-8")).hexdigest()[:12] if raw else "NONE"
        mid = getattr(event.message, "id", None)

        # RAW-TEXT CONTAINMENT: print only safe identifiers — counts, hash, status, ids.
        # The full content is written ONLY to prospective_evidence_v1.db.
        print(f"\n[PREVIEW] Captured event at {stamp}  channel={event.chat_id}  msg_id={mid}")
        print(f"          chars={safe_len}  sha256[:12]={safe_hash}  (content -> evidence DB only)")

        # GATE 1 (approved): observational prospective capture -> prospective_evidence_v1.db
        # ONLY. Raw evidence persisted before any parsing; quote fields NULL/BROKER_NOT_CONNECTED.
        # NewMessage (CREATED) here; EDITs captured by _edit_handler below (2026-07-21).
        # Deletion/backfill remain NOT wired (unsupported).
        # This is NOT the trading pipeline; the module_b handoff below remains DISABLED.
        try:
            _record_prospective(recorder, event, allowed_ids)
            _last["id"], _last["ts"] = mid, stamp       # ADD-2: latest capture for the heartbeat
            print("          [prospective] raw evidence recorded (quotes NULL / BROKER_NOT_CONNECTED)")
        except PermissionError:
            print(f"          [prospective] off-allowlist channel {event.chat_id} REJECTED — no row")
        except Exception as _e:
            # never echo raw content via an exception string — type name only
            print(f"          [prospective] record skipped (evidence not lost): {type(_e).__name__}")

        # GATE 1b (Phase 2B): supported Telegram IMAGE-byte preservation — ONLY AFTER the text
        # commit above. Fully guarded: any media error is contained and the text row is safe.
        if media_ctx is not None and getattr(event.message, "media", None) is not None:
            try:
                _st = await _preserve_media(event, media_ctx, allowed_ids)
                print(f"          [media] {_st}")
            except Exception as _me:
                print(f"          [media] skipped (text already safe): {type(_me).__name__}")

        # ===================================================================
        # HANDOFF TO THE PIPELINE  —  DISABLED (this is the line to enable).
        # When you go live, this single line hands the text to Module B, which
        # decides if it's a real signal and parses it. Then it flows into the
        # normal confirm -> size -> log path. DO NOT enable this on your own.
        # ===================================================================
        # parsed = module_b_parser.parse(text)  # <-- ENABLE LATER
        #
        # (For reference, the real function in this codebase is named
        #      parsed = module_b_parser.parse_signal(message_text)
        #  but leave it commented until activation is done deliberately.)

    @client.on(events.MessageEdited(chats=channels))
    async def _edit_handler(event):
        # LIVE_EDIT_EVENTS_NOT_CAPTURED fix (D-028): capture Telegram EDITS as append-only
        # EDITED revisions (listener_edit_capture.py holds all logic + tests). Same
        # containment rules as CREATED: allowlist fail-closed, content only to the DB,
        # never to terminal/logs. Interpretation stays downstream: the wire routes any
        # non-CREATED row to its fail-closed edit branch and alarms on touched campaigns.
        import hashlib as _hl
        stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        raw = event.raw_text
        safe_hash = _hl.sha256((raw or "").encode("utf-8")).hexdigest()[:12] if raw else "NONE"
        mid = getattr(event.message, "id", None)
        print(f"\n[PREVIEW] EDIT captured at {stamp}  channel={event.chat_id}  msg_id={mid}")
        print(f"          chars={len(raw) if raw else 0}  sha256[:12]={safe_hash}  (content -> evidence DB only)")
        try:
            import listener_edit_capture as _lec
            row = _lec.record_prospective_edit(recorder, event, allowed_ids)
            print(f"          [prospective] EDITED revision {row['message_revision_number']} recorded "
                  f"(supersedes {row['supersedes_evidence_id'] or 'NONE — orphan edit'})")
        except PermissionError:
            print(f"          [prospective] off-allowlist channel {event.chat_id} REJECTED — no row")
        except Exception as _e:
            print(f"          [prospective] edit record skipped (original evidence safe): {type(_e).__name__}")

    if _ll is not None:
        asyncio.create_task(_heartbeat_loop())      # ADD-2: writes an immediate heartbeat, then every 60s
    print("\n  Connected. Listening for new messages... (press Ctrl+C to stop)\n")
    try:
        await client.run_until_disconnected()
    finally:
        # Disconnect from inside the loop so the socket closes before asyncio.run
        # tears the loop down — this is what prevents the closed-loop error.
        await client.disconnect()


def list_dialogs():
    """
    Log in and print a numbered list of every channel/group this account is in,
    with each one's name and numeric ID. READ-ONLY — it fetches your chat list
    and prints it; it watches nothing, parses nothing, logs nothing.

    Handy for finding the ID of a PRIVATE channel that has no @username — copy the
    ID it prints into TELEGRAM_CHANNEL in config.py.
    """
    tele = _load_telethon()
    if not tele:
        return
    TelegramClient, _events = tele

    creds = _read_credentials()
    if not creds:
        return
    api_id, api_hash = creds

    print("=" * 64)
    print("   SIGNAL LISTENER (Telegram)   —   LIST CHANNELS (read-only)")
    print("=" * 64)
    print("   This only lists the chats you're in so you can find a channel ID.")
    print("   It watches nothing and changes nothing.")
    print("=" * 64)

    # Same supported pattern as the preview: one event loop, owned and closed by
    # asyncio.run, so nothing tries to use a loop after it's been torn down
    # (the Python 3.14 "Event loop is closed" crash).
    try:
        asyncio.run(_list_async(TelegramClient, api_id, api_hash))
    except KeyboardInterrupt:
        print("\n  Cancelled.")


async def _list_async(TelegramClient, api_id, api_hash):
    """Async core of --list: log in, fetch the chat list, print it, disconnect."""
    client = await _make_client_and_login(TelegramClient, api_id, api_hash)
    if client is None:
        return

    try:
        dialogs = await client.get_dialogs()

        rows = []
        for d in dialogs:
            # Channels and groups only — skip one-to-one private chats with people.
            if getattr(d, "is_channel", False) or getattr(d, "is_group", False):
                username = getattr(getattr(d, "entity", None), "username", None)
                rows.append((d.name or "(no name)", d.id, username))

        print("\n  Channels & groups your account is a member of:\n")
        if not rows:
            print("  (None found. Are you a member of any channels or groups?)")
        else:
            for i, (name, cid, username) in enumerate(rows, start=1):
                handle = f"  (@{username})" if username else ""
                print(f"  {i:>3}) {name}{handle}")
                print(f"       ID: {cid}")
            print("\n  To watch one, copy its ID into config.py, for example:")
            print('       TELEGRAM_CHANNEL = "-1001234567890"')
            print("  (A public channel can use its @username instead.)")
    except Exception as e:
        _friendly_stop(f"couldn't fetch your chat list: {e}")
    finally:
        # Disconnect inside the loop, before asyncio.run closes it.
        await client.disconnect()
    print()


# ============================================================================
# HISTORY BACK-LOG MODE (--history N)
# ============================================================================
# Pulls the last N messages from the configured channel, prints them, and shows
# what each WOULD be classified as (clean signal / commentary / REVIEW) by the
# existing parser + router + quality filter. It writes a reviewable CSV. It does
# NOT log anything to paper_log.csv — this is a read-only back-log aid you eyeball
# first. Telegram access is read-only; FloodWait is respected (see below).

# --- Cheap, LLM-free signal detection (so we don't parse 500 chatter messages) -
_DIR_RE = re.compile(r"\b(long|short|buy|sell)\b", re.I)
_SIGNAL_KW_RE = re.compile(r"\b(sl|stop[\s-]?loss|stop|tp\d?|take[\s-]?profit|target|entry|zone)\b", re.I)
_NUM_RE = re.compile(r"\d")
# Conservative number capture for the regex fallback (no API key / --no-parse).
_NUM = r"([0-9][0-9,]*\.?[0-9]*)"
_STOP_RE = re.compile(r"(?:sl|stop[\s-]?loss|stop)\s*[:=@\-]?\s*" + _NUM, re.I)
_TP_RE = re.compile(r"(?:tp|target)(?:[1-9])?\s*[:=@\-]?\s*" + _NUM, re.I)
_ENTRY_RE = re.compile(r"(?:entry|enter|zone|@)\s*[:=@\-]?\s*"
                       r"([0-9][0-9,]*\.?[0-9]*(?:\s*[-–]\s*[0-9][0-9,]*\.?[0-9]*)?)", re.I)
# A light ticker sniff: metals, X/USDT crypto, or a 6-letter FX pair / common words.
_TICKER_RE = re.compile(
    r"\b(XAUUSD|XAGUSD|XAU|XAG|GOLD|SILVER|US30|NAS100|US100|USOIL|WTI|"
    r"[A-Z]{2,6}/USDT?|[A-Z]{3,5}USDT|[A-Z]{6})\b")


# Some channels are AGGREGATORS that re-post several traders, prefixing each post
# with the original poster, e.g. "seascalperfarouk Posted in ...". When present,
# that poster is the real 'sender' to filter on (the Telegram sender is just the
# aggregator channel). Match it so --sender can isolate one trader's posts.
_POSTER_RE = re.compile(r"^\s*([A-Za-z0-9_.]{2,40})\s+(?:Posted in|posted in|:)\b")


def _extract_poster(text: str) -> str:
    m = _POSTER_RE.match(text or "")
    return m.group(1) if m else ""


# Named instruments, matched CASE-INSENSITIVELY (so "Gold"/"gold"/"GOLD" all
# count). The uppercase _TICKER_RE above catches symbols/pairs like XAUUSD.
_NAMED_TICKER_RE = re.compile(
    r"\b(xauusd|xagusd|xau|xag|gold|silver|us30|nas100|us100|usoil|wti|brent|"
    r"btc|eth|sol)\b", re.I)


def _looks_like_signal(text: str) -> bool:
    """A trade signal needs a direction, a number, and some signal vocabulary."""
    if not text:
        return False
    return bool(_DIR_RE.search(text)) and bool(_NUM_RE.search(text)) and \
        (bool(_SIGNAL_KW_RE.search(text)) or bool(_TICKER_RE.search(text))
         or bool(_NAMED_TICKER_RE.search(text)))


def _regex_fields(text: str) -> dict:
    """
    Best-effort field extraction WITHOUT the LLM, for the no-API-key / --no-parse
    path. It only fills a field when reasonably clear; otherwise it leaves it
    BLANK (we never guess). The LLM parser overrides this when available.
    """
    fields = {k: "" for k in ("asset", "direction", "entry", "stop", "tp1", "tp2", "tp3")}
    d = _DIR_RE.search(text)
    if d:
        w = d.group(1).lower()
        fields["direction"] = "LONG" if w in ("long", "buy") else "SHORT"
    t = _TICKER_RE.search(text)
    if t:
        fields["asset"] = t.group(1).upper()
    s = _STOP_RE.search(text)
    if s:
        fields["stop"] = s.group(1).replace(",", "")
    e = _ENTRY_RE.search(text)
    if e:
        fields["entry"] = re.sub(r"\s+", "", e.group(1)).replace(",", "")
    tps = [m.group(1).replace(",", "") for m in _TP_RE.finditer(text)]
    for i, val in enumerate(tps[:3], start=1):
        fields[f"tp{i}"] = val
    return fields


def _fields_from_signal(sig) -> dict:
    """Dedicated columns from a parsed Signal (the reliable path)."""
    lo, hi = sig.entry_low, sig.entry_high
    entry = str(lo) if lo == hi else f"{lo}-{hi}"
    tps = list(sig.targets or [])
    return {
        "asset": sig.ticker or "",
        "direction": sig.direction or "",
        "entry": entry,
        "stop": str(sig.stop_loss) if sig.stop_loss is not None else "",
        "tp1": str(tps[0]) if len(tps) > 0 else "",
        "tp2": str(tps[1]) if len(tps) > 1 else "",
        "tp3": str(tps[2]) if len(tps) > 2 else "",
    }


# ============================================================================
# OUTCOME-CUE DETECTION + matching follow-up messages to their entry signal
# ============================================================================
# Farouk posts management/result messages after an entry ("tp1 hit", "sl to
# entry", "stopped out", "+50 pips", "all tp hit"…). These detect the OUTCOME a
# follow-up message reports, and match it back to the entry it belongs to. It is
# an AID for review only — never auto-logged, and conservative: anything unclear
# stays "unclear" with no evidence rather than guessed.
#
# Each message is read as ONE of these EVENTS (precedence top-down):
#   win      a verifiable take-profit / "+X pips"  (scored by what's stated only)
#   missed   the ENTRY never filled (no trade)
#   be_stop  the breakeven stop was hit ("SL at entry hit", "stopped at entry") -> BE
#   move_be  a MANAGEMENT MOVE of the stop to entry/BE ("sl to entry", "moved to BE")
#   stop_hit a stop being hit ("sl hit", "stopped out", "-X pips")
#
# CHRONOLOGY (no retroactive breakeven): the stop sits at the ORIGINAL level until
# a move_be message. So a stop_hit BEFORE any move_be is a LOSS (original stop);
# a stop_hit AFTER a move_be is a BREAKEVEN (the BE stop). We can only approximate
# the timing from message ORDER — where we can't tell, we mark unclear, not guess.
#
# We do NOT model partial profit-taking or assume a % closed at TP1 — the messages
# don't verify partial sizes or the remaining stop, and assuming them would flatter
# the edge. We score the VERIFIABLE outcome only.

# --- Outcome categories (granular & honest) ---------------------------------
# Each clean signal is labelled with EXACTLY ONE of these, so the distribution
# RECONCILES to the total. R-scoring (in log_history.py) follows the category.
OUT_TARGET_HIT = "target_hit"                       # win  -> R to the stated target
OUT_MANAGED_PROFIT = "managed_profit_confirmed"     # win  -> R from the stated pips/level
OUT_PROFIT_RUNKNOWN = "profit_confirmed_r_unknown"  # win label, exit unknown -> 0R
OUT_MANUAL_LOSS = "manual_loss"                     # loss -> the ACTUAL stated loss (not -1R)
OUT_STOP_LOSS = "original_stop_loss"                # loss -> -1R (the stop was hit)
OUT_BREAKEVEN = "breakeven"                         # 0R
OUT_MISSED = "missed"                               # no fill (no trade)
OUT_INSTRUCTION = "instruction_only"               # only instructions/chatter -> not a result
OUT_UNCLEAR = "unclear"                             # nothing to go on

_WIN_CATEGORIES = {OUT_TARGET_HIT, OUT_MANAGED_PROFIT, OUT_PROFIT_RUNKNOWN}
_LOSS_CATEGORIES = {OUT_MANUAL_LOSS, OUT_STOP_LOSS}


def _stop_is_valid(direction, entry, stop):
    """
    True unless the stop is on the WRONG side of entry (a LONG stop at/above entry,
    or a SHORT stop at/below entry) — an invalid stop makes any R meaningless.
    Returns True when it can't tell (missing/garbled values) so it never downgrades
    a win on uncertain data.
    """
    enums = [n.replace(",", "") for n in re.findall(r"\d[\d,]*\.?\d*", entry or "")]
    snums = re.findall(r"\d[\d,]*\.?\d*", stop or "")
    if not enums or not snums:
        return True
    try:
        evals = [float(n) for n in enums]
        sval = float(snums[0].replace(",", ""))
    except ValueError:
        return True
    lo, hi = min(evals), max(evals)
    d = (direction or "").upper()
    if d.startswith("L") or d == "BUY":
        return sval < lo
    if d.startswith("S") or d == "SELL":
        return sval > hi
    return True


# GOLD pip convention: Farouk's "pips" on gold are $0.10 increments (10 pips = 1
# price point) — "300 pips" is a ~30-point run, not 300 points. This factor turns a
# stated pip count into a price-point move so it can be compared to target distances
# and scored to R. Other assets are left as-is (1 pip = 1 quoted unit).
def _pip_points(asset, pips):
    a = (asset or "").upper()
    if "XAU" in a or "GOLD" in a:
        return float(pips) * 0.1
    return float(pips)


def _refine_win_with_pips(outcome, evidence, row):
    """
    Refine a pip-based WIN against the signal's OWN targets (we have the prices
    here): if the confirmed pip move reaches (≈) the FURTHEST posted target, it's a
    `target_hit`; otherwise it's a `managed_profit_confirmed` partial. An EXPLICIT
    target hit is never downgraded. Never touches losses / breakevens / r-unknown
    with no pip figure, or trades with no posted targets.
    """
    if outcome not in _WIN_CATEGORIES:
        return outcome
    if _OUT_TARGET_HIT_CONFIRM_RE.search(evidence or ""):
        return outcome                                   # an explicit hit stays target_hit
    pips = _evidence_pips(evidence)
    if pips <= 0:
        return outcome                                   # no stated pips -> leave as-is
    tps = []
    for k in ("TP1", "TP2", "TP3"):
        m = re.findall(r"\d[\d,]*\.?\d*", row.get(k) or "")
        if m:
            tps.append(float(m[0].replace(",", "")))
    enums = [float(n.replace(",", ""))
             for n in re.findall(r"\d[\d,]*\.?\d*", row.get("Entry") or "")]
    if not tps or not enums:
        return outcome                                   # no targets to compare against
    mid = (min(enums) + max(enums)) / 2
    d = (row.get("Direction") or "").upper()
    furthest = max(tps) if (d.startswith("L") or d == "BUY") else min(tps)
    dist = abs(furthest - mid)
    move = _pip_points(row.get("Asset"), pips)
    if dist > 0 and move >= dist * 0.9:                   # reached (≈) the furthest target
        return OUT_TARGET_HIT
    return OUT_MANAGED_PROFIT


def outcome_group(category):
    """Coarse bucket for a granular category: win/loss/breakeven/missed/unclear."""
    if category in _WIN_CATEGORIES:
        return "win"
    if category in _LOSS_CATEGORIES:
        return "loss"
    if category in (OUT_BREAKEVEN, OUT_MISSED):
        return category
    return "unclear"   # instruction_only / unclear


# A WIN requires an EXPLICITLY STATED profit — a target reached / taken ("tp1 hit",
# "take tp 1", "tp 1 now", a bare "tp 1" in the result thread), stated pips of
# profit ("+40 pips", "we got 90 pips", "banked 80 pips"), or profit taken
# ("took profit", "secured tp1", "take 75%"). Deliberately STILL NOT a win:
# "secured at breakeven" (a scratch), "running 200 pips" (unrealised), and a TP
# LEVEL LISTING like "TP1 : 4,334" (a target being POSTED, not hit — guarded by the
# negative lookahead on the bare-tp cue). Hypothetical/educational "if price… you
# could…" messages are excluded separately (see _is_generic).
_OUT_WIN_RE = re.compile(r"""(?:
    # --- a target was reached / profit taken (result context) ----------------
    \btp\s*[1-9]?\s*(?:hit|done|reached|smashed|tagged|secured|now)\b |
    \bhit\s+tp\s*[1-9]?\b |
    \btp\s*[1-9]?\s*(?:at|@)\s*\d |                                 # "tp1 at 2350"
    \btake\s+(?:the\s+|some\s+|partial\s+)?(?:tp|tps|profits?)\b(?!\s+(?:levels?|targets?|zones?|area|range)) |  # "take tp 1" but NOT "take profit levels" (a listing)
    \btake\s+\d{1,3}\s*% |                                          # "take 75%"
    \btake\s+\d{1,3}\s*(?:pips?|off)\b |                            # "take 50 pips/off"
    \btake\s+some\s+(?:off|out|profit)\b |                          # "take some off"
    \b(?:small|more)\s+(?:tp|profits?)\b |                          # "small tp", "more tp/profit"
    \bofficial\s+tp\s*[1-9]?\b |                                    # "official tp1"
    \bsecur(?:e|ed|ing)\s+(?:tp|profits?)\s*[1-9]?\b |              # "securing tp 1"
    \bout\s+(?:of\s+the\s+trade\s+)?(?:after\s+)?(?:securing\s+)?tp\s*[1-9]?\b |
    \balmost\s+(?:reach(?:ed)?|hit|got\s+to)?\s*tp\b |              # "almost reached tp" (partial)
    \btp\s*[1-9]\b(?!\s*[:=]?\s*[\d,]{3,}) |                        # bare "tp 1" — NOT "TP1 : 4,334" (a listing)
    \ball\s+(?:tps?|targets?)\b |
    \b(?:target|targets)\s+(?:hit|reached|done|smashed)\b |
    \btook\s+(?:the\s+|some\s+|partial\s+)?profits?\b |
    \btake[\s-]?profit\s+(?:hit|done|reached)\b |
    # --- stated pips of profit ----------------------------------------------
    \+\s*\d+\s*pips? |
    \b\d+\s*\+\s*pips? |
    \b\d+\s*pips?\s+(?:tp|to\s+[1-9]|take|profit|banked|secured|gain|in\s+profit|done|closed|won)\b |
    \bwe\s+(?:got|have|made|bagged)\s+\+?\d+\s*pips?\b |            # "we got 90 pips"
    \b(?:banked|secured|bagged|grabbed|made|locked\s+in)\s+(?:the\s+|some\s+|partial\s+)?profits?\b |
    \b(?:banked|secured|bagged|grabbed|made)\s+\+?\d+\s*pips? |     # "banked 80 pips"
    \bclosed\s+in\s+profit\b
)""", re.I | re.X)

# --- Win SUB-type classifiers (which win category a profit message is) -------
# "almost reached tp1" = it did NOT reach the target -> profit confirmed but exit
# unknown (must NOT be credited TP1's R).
_OUT_ALMOST_RE = re.compile(r"\balmost\b\s*(?:reach(?:ed)?|hit|got\s+to|made\s+it\s+to|at|to)?\s*(?:tp|target)", re.I)
# Stated PIPS of profit -> managed_profit_confirmed (R from the stated pips).
# ("pi(?:p|sp)s?" also accepts Farouk's recurring "pisp"/"pisps" typo.)
_OUT_PROFIT_PIPS_RE = re.compile(r"""(?:
    \+\s*\d+\s*pi(?:p|sp)s? | \b\d+\s*\+\s*pi(?:p|sp)s? |
    \bwe\s+(?:got|have|made|bagged)\s+\+?\d+\s*pi(?:p|sp)s?\b |
    \b\d+\s*pi(?:p|sp)s?\s+(?:tp|to\s+[1-9]|take|profit|banked|secured|gain|in\s+profit|done|closed|won)\b |
    \b(?:banked|secured|bagged|grabbed|made)\s+\+?\d+\s*pi(?:p|sp)s?\b
)""", re.I | re.X)
# A NAMED target reached (a tp NUMBER, or "all tp") -> target_hit (R to target).
_OUT_TARGET_NAMED_RE = re.compile(r"""(?:
    \btp\s*[1-9]\s*(?:hit|done|reached|smashed|tagged|secured|now)\b |
    \bhit\s+tp\s*[1-9]\b |
    \btp\s*[1-9]\s*(?:at|@)\s*\d |
    \btake\s+(?:the\s+|some\s+|partial\s+)?tp\s*[1-9]\b |
    \bofficial\s+tp\s*[1-9]\b |
    \bsecur(?:e|ed|ing)\s+tp\s*[1-9]\b |
    \bout\s+(?:of\s+the\s+trade\s+)?(?:after\s+)?(?:securing\s+)?tp\s*[1-9]\b |
    \btp\s*[1-9]\b(?!\s*[:=]?\s*[\d,]{3,}) |
    \ball\s+(?:tps?|targets?)\b |
    \b(?:target|targets)\s+(?:hit|reached|done|smashed)\b
)""", re.I | re.X)

# An EXPLICIT target-HIT confirmation (the target was actually REACHED), as opposed
# to a bare "take tp"/"tp now" INSTRUCTION. Only an explicit hit gets full target R;
# a take-instruction accompanied by a smaller stated-pips figure is scored to the
# pips instead (don't over-credit a distant target that wasn't reached).
_OUT_TARGET_HIT_CONFIRM_RE = re.compile(r"""(?:
    \btp\s*[\d\s-]{0,6}hit\b |                                  # "tp1 hit", "tp 1 -2 hit"
    \btp\s*[1-9]?\s*(?:reached|smashed|tagged|done)\b |
    \bhit\s+tp\s*[1-9]?\b |
    \b(?:target|targets)\s+(?:hit|reached|done|smashed)\b |
    \ball\s+(?:tps?|targets?)\b |                               # "all tp (hit)"
    \bsecur(?:e|ed|ing)\s+tp\s*[1-9]?\b |
    \bout\s+(?:of\s+the\s+trade\s+)?(?:after\s+)?securing\s+tp\s*[1-9]?\b |
    \bofficial\s+tp\s*[1-9]?\s*hit\b
)""", re.I | re.X)


# A BARE pip figure that is a CONFIRMED result ("300 pips", "50 pips", "50-60
# pips") — counts as a stated-pips profit. Guarded against UNREALISED / non-result
# contexts ("running 200 pips", "still up 50-60 pips", "after a 130-pips", "missed
# by 1 pip", "almost 200 pips", forecasts) so an open or hypothetical move never
# reads as a banked result.
_BARE_PIPS_RE = re.compile(r"\b\d+\s*(?:[-–]\s*\d+)?\s*pi(?:p|sp)s?\b", re.I)
_PIPS_NONRESULT_RE = re.compile(
    r"\b(?:running|still|up|after|by|missed|almost|away|holding|open|expect|expecting|"
    r"target|targeting|aim|aiming|need|could|would|chance|if)\b", re.I)


def _bare_pips_result(text):
    """True if the text states a CONFIRMED pip result (not unrealised/hypothetical)."""
    t = text or ""
    if not _BARE_PIPS_RE.search(t):
        return False
    if _PIPS_NONRESULT_RE.search(t) or _OUT_ALMOST_RE.search(t):
        return False
    return True


# A "banked" pip figure carries a verb/level showing profit was TAKEN ("we got 90
# pips", "banked 80", "take tp"); a FLOATING figure is a bare "50 pips" with none of
# that — it may just be the open float, so if the trade then scratches at BE it's a
# breakeven, not a win.
_BANKING_VERB_RE = re.compile(
    r"\b(?:got|have|banked|secured|bagged|grabbed|made|locked|take|took|taking|"
    r"close|closed|closing|tp|profit)\b", re.I)


def _is_floating_pips(text):
    """A bare pip figure with no banking verb / win cue — an UNREALISED float."""
    t = text or ""
    if not _bare_pips_result(t):
        return False
    return not (_OUT_PROFIT_PIPS_RE.search(t) or _OUT_WIN_RE.search(t)
                or _OUT_TARGET_NAMED_RE.search(t) or _BANKING_VERB_RE.search(t))


def _profit_strength(text):
    """
    How strong a profit confirmation is, for ranking and sub-typing:
      3 = an explicit target HIT  ("tp1 hit", "all tp hit", "securing tp1")
      2 = a stated PIP figure     ("we got 90 pips", "50 pips tp 1", a bare "300 pips")
      1 = a bare take/now target  INSTRUCTION ("take tp 1", "tp 1 now")
      0 = profit confirmed, no quantity/level ("take profit", "more tp")
    A stated pip figure OUTRANKS a bare instruction so the confirmed (often smaller)
    result is scored, not a distant target that was only *instructed*, never hit.
    """
    t = text or ""
    if _OUT_TARGET_HIT_CONFIRM_RE.search(t):
        return 3
    if _OUT_PROFIT_PIPS_RE.search(t) or _bare_pips_result(t):
        return 2
    if _OUT_TARGET_NAMED_RE.search(t):
        return 1
    return 0


def _win_subtype(text):
    """
    Classify a profit message into target_hit / profit_pips / profit_runknown.
      * an explicit target HIT          -> target_hit (full R to that target)
      * a stated PIP figure (no hit)    -> profit_pips (scored to the confirmed pips)
      * a bare take/now INSTRUCTION     -> target_hit (a reached target, no pips stated)
      * "almost reached tp" / nothing   -> profit_runknown
    Pips OUTRANK a bare instruction so a confirmed (often smaller) result isn't
    over-credited to a distant target that was only instructed, never hit.
    """
    t = text or ""
    if _OUT_ALMOST_RE.search(t):
        return "profit_runknown"          # "almost reached tp" — did NOT hit it
    s = _profit_strength(t)
    if s == 3:
        return "target_hit"               # explicit hit -> full target R
    if s == 2:
        return "profit_pips"              # stated pips -> score to the confirmed pips
    if s == 1:
        return "target_hit"               # bare take/now instruction (no pips)
    return "profit_runknown"              # profit confirmed but no number/level/exit


# Extract the reconstructable magnitude of a profit message, for picking the
# STRONGEST/LATEST confirmation in a window (the evidence-link fix).
_TP_NUM_RE = re.compile(r"\btp\s*([1-9])\b", re.I)
_ALL_TP_RE = re.compile(r"\ball\s+(?:tps?|targets?)\b", re.I)
# "pisp" is Farouk's recurring typo for "pips" — accept both magnitude readers.
_EV_PIPS_RE = re.compile(r"([+-]?\d+(?:\.\d+)?)\s*pi(?:p|sp)s?\b", re.I)
_CONF_WORD_RE = re.compile(r"\b(?:hit|official|reached|smashed|done|secured|banked|got)\b", re.I)


def _evidence_target(text):
    """Highest named target in the text: 99 for 'all tp', 1..9 for 'tpN', else 0."""
    t = text or ""
    if _ALL_TP_RE.search(t):
        return 99
    nums = [int(m.group(1)) for m in _TP_NUM_RE.finditer(t)]
    return max(nums) if nums else 0


def _evidence_pips(text):
    """Largest stated pip magnitude in the text, or 0."""
    vals = []
    for m in _EV_PIPS_RE.finditer(text or ""):
        try:
            vals.append(abs(float(m.group(1))))
        except ValueError:
            pass
    return max(vals) if vals else 0


# A RE-ENTRY marker — Farouk re-entering the same idea as a NEW position.
_OUT_REENTRY_RE = re.compile(r"\bre-?\s*enter(?:ing)?\b|\bre-?entry\b|\breenter\b", re.I)


# A fresh-SIGNAL-shaped message inside a window (a new buy/sell with a price) — a
# new trade starts here, so a parent must not be credited with anything past it.
_NEW_SIGNAL_RE = re.compile(r"\b(?:buy|sell|long|short)\b[^.\n]{0,30}?\d{3,}", re.I)


def _truncate_at_reentry(texts):
    """
    Cut the window at the first RE-ENTRY or NEW SIGNAL that follows a resolved
    PARENT result, so a post-re-entry "tp3 170 pips" / a later trade's result can't
    leak backwards into the parent. The boundary cuts BOTH ways: a genuine result
    confirmed BEFORE the boundary is kept; anything from the boundary on is dropped.
    If no parent result precedes the boundary (the trade is simply continuing), the
    window is unchanged.
    """
    resolved = None
    for i, t in enumerate(texts):
        e = _detect_event(t)
        if resolved is None and e in (
                "net_loss_verdict", "manual_loss", "stop_hit", "be_stop",
                "target_hit", "profit_pips", "profit_runknown"):
            resolved = i                          # parent has a result from here
        if resolved is not None and i > resolved and (
                _OUT_REENTRY_RE.search(t or "") or _NEW_SIGNAL_RE.search(t or "")):
            return texts[:i]                      # drop everything from the boundary on
    return texts


def _profit_rank(text):
    """
    Sort key for choosing the strongest profit confirmation in a window:
    explicit HIT (3) > stated PIPS (2) > bare take/now instruction (1) > nothing (0),
    then the highest target, then the largest pips, then a confirmation word. So an
    explicit "tp1 hit" / "all tp hit" beats a pip figure, a pip figure beats a bare
    "take tp 1", and a later "almost hit TP1" recap never displaces a real hit.
    """
    return (_profit_strength(text), 0 if _OUT_ALMOST_RE.search(text or "") else 1,
            _evidence_target(text), _evidence_pips(text),
            1 if _CONF_WORD_RE.search(text or "") else 0)


# "missed" the ENTRY (no fill). Bare "missed" is excluded when it's clearly about
# something else ("missed my sl", "just missed our sl", "missed tp", "missed by a
# pip") — a near-miss of the STOP/target is not a missed entry. Conservative.
_OUT_MISSED_RE = re.compile(r"""(?:
    \bmissed\b(?!\s+(?:\w+\s+){0,2}?(?:sl\b|stop\b|tp\b|target))(?!\s+(?:my\b|by\b|it\b)) |
    \bdidn'?t\s+fill\b | \bdid\s+not\s+fill\b | \bno[\s-]?fill\b |
    \bnever\s+filled\b | \bnot\s+filled\b | \bdidn'?t\s+trigger\b | \bnever\s+triggered\b
)""", re.I | re.X)

# The breakeven STOP being hit (a scratch) — needs both an at-entry/BE reference
# AND a hit/stopped/closed. "scratch" is its own terminal-breakeven word.
_OUT_BE_STOP_RE = re.compile(r"""(?:
    \b(?:sl|stop)\s+(?:is\s+|now\s+)?at\s+(?:entry|be|break[\s-]?even)\b.{0,15}?\bhit\b |
    \bstopped?(?:\s+out)?\s+at\s+(?:entry|be|break[\s-]?even) |
    \b(?:be|breakeven|break\s*even)\s+(?:stop\s+)?hit\b |
    \bclosed\s+at\s+(?:entry|be|break[\s-]?even)\b |
    \bscratch(?:ed)?\b
)""", re.I | re.X)

# A MANAGEMENT MOVE of the stop to entry/breakeven (NOT itself a terminal outcome).
# "SL at entry" WITHOUT a hit is a move statement; with a hit it's caught above.
_OUT_MOVE_BE_RE = re.compile(r"""(?:
    \bsl\s+to\s+(?:entry|be|break[\s-]?even)\b | \bstop\s+to\s+(?:entry|be|break)\b |
    \bmoved?\s+(?:sl\s+|stop\s+)?to\s+(?:entry|be|break[\s-]?even)\b |
    \bmove\s+(?:sl|stop)\s+to\s+(?:entry|be|break)\b |
    \bset\s+(?:sl|stop)\s+(?:to|at)\s+(?:entry|be|break)\b |
    \b(?:sl|stop)\s+(?:is\s+|now\s+)?at\s+(?:entry|be|break[\s-]?even)\b |
    \bbreak[\s-]?even\b | \brisk[\s-]?free\b
)""", re.I | re.X)

# The ORIGINAL STOP being hit (the stop mechanism) -> -1R, unless a move_be
# preceded it (then it's the BE stop). NOTE: a stated-pips loss ("-40 pips") or a
# manual close is NOT here — that's a manual_loss (below), scored at its actual R.
_OUT_STOP_HIT_RE = re.compile(r"""(?:
    \bsl\s+(?:got\s+|was\s+|just\s+)?hit\b | \bhit\s+(?:my\s+|the\s+)?sl\b |
    \bstop[\s-]?loss\s+(?:got\s+|was\s+)?hit\b | \bstop\s+hit\b |
    \bstopped\s+out\b | \bstopped\b(?!\s+for) | \bsl\s+taken\b | \bstop\s+taken\b
)""", re.I | re.X)

# An EXPLICIT NET-LOSS VERDICT — Farouk's own final word on the trade/sequence.
# This OVERRIDES everything (even an earlier partial tp): count the whole thing a
# loss. Includes a manual CLOSURE-FOR-A-LOSS of this trade ("close it for a small
# loss") and an explicit per-trade win/loss tally ("1 win, 1 loss today"). NOTE:
# a multi-trade tally that uses "trades" not "wins" ("6 trades, 1 loss") is NOT a
# per-trade verdict and is deliberately excluded.
_OUT_NET_LOSS_VERDICT_RE = re.compile(r"""(?:
    \bcount\s+(?:this|it|that|the\s+\w+|the\s+sequence|everything|all)?\s*
        (?:as\s+)?an?\s*loss\b |
    \bcount\s+(?:the\s+)?sequence\s+as\s+an?\s*loss\b |
    \boverall\s+(?:a\s+)?loss\b | \bnet\s+loss\b | \bas\s+an?\s+loss\s+overall\b |
    \bcall\s+it\s+an?\s+loss\b |
    \bclos(?:e|ed|ing)\s+(?:it|the\s+trade|this|out)?\s*for\s+a\s+(?:\w+\s+)?loss\b |
    \b\d+\s+wins?\s*,?\s*(?:and\s+)?\d+\s+loss(?:es)?\b
)""", re.I | re.X)

# A MANUAL / NET loss that is NOT the original stop being hit — "cut for -40 pips",
# "closed for a loss", "manually closed", "took a loss", "stopped for -X", any
# "-X pips". Scored at the ACTUAL stated loss, never dropped, never relabelled BE.
_OUT_MANUAL_LOSS_RE = re.compile(r"""(?:
    \bcut\s+(?:the\s+trade|it|this|the\s+\w+)?\s*(?:for\s+)?-?\s*\d*\s*pips? |
    \bcut(?:ting)?\s+(?:the\s+)?(?:trade|loss|it|position)\b |
    \bclos(?:e|ed|ing)\s+(?:the\s+trade\s+|it\s+|this\s+)?(?:for\s+|in\s+|at\s+)?an?\s*loss\b |
    \bclosed\s+in\s+(?:loss|red)\b |
    \bmanually\s+clos(?:e|ed|ing)\b |
    \btook\s+(?:a\s+|the\s+|small\s+)?loss\b | \bsmall\s+loss\b | \btake\s+the\s+loss\b |
    \bstopped\s+for\s+-?\s*\d+\s*pips? |
    (?<![\d.,])-\s*\d+\s*pips?\b                # a genuine "-40 pips", NOT a range "50-60 pips"
)""", re.I | re.X)


# Educational / hypothetical / generic messages — NOT a result on this trade, so
# their tp/pips talk must not be read as a win. e.g. "if price breaks X you could
# see tp1", "would have hit tp", "for example", "in theory".
_GENERIC_RE = re.compile(r"""(?:
    \bif\s+(?:price|it|we|you|this|that|gold|market|the\s+\w+)\b[^.\n]{0,40}?
        \b(?:could|would|can|might|may|expect|looking|see|push|reach)\b |
    \b(?:when|once)\s+(?:we|price|it|gold|this|that)\b[^.\n]{0,30}?
        \b(?:go|goes|going|reach|reaches|break|breaks|hit|hits|get|gets|come|comes|move|moves)\b |
    \bwould\s+have\b | \bcould\s+have\b | \bwould'?ve\b |
    \bfor\s+example\b | \be\.?g\.? | \bhypothetical(?:ly)?\b | \bin\s+theory\b |
    \bimagine\b | \bsuppose\b | \blet'?s\s+say\b |
    \bif\s+you\s+(?:had|took|enter|entered|would)\b |
    # forecast / analysis (a PREDICTION, not a result)
    \bi\s+think\b | \bgood\s+chance\b | \bchance\s+of\b |
    \bexpect(?:ing|s)?\s+(?:to|a|the|price|it|gold|more)\b |
    \bshould\s+(?:reach|hit|go|see|run|push|drop)\b |
    \btargeting\b | \baiming\s+for\b | \blooking\s+(?:for|to)\s+\w
)""", re.I | re.X)


def _is_generic(text: str) -> bool:
    """True if the message is hypothetical/educational, not a real result."""
    return bool(_GENERIC_RE.search(text or ""))


def _detect_event(text):
    """
    One event per message (precedence top-down):
      net_loss_verdict | target_hit | profit_pips | profit_runknown | missed |
      manual_loss | be_stop | move_be | stop_hit | None
    """
    t = text or ""
    # An explicit "count it as a loss" verdict is the strongest signal.
    if _OUT_NET_LOSS_VERDICT_RE.search(t):
        return "net_loss_verdict"
    # A profit cue (unless it's a hypothetical/educational message) -> win subtype.
    if _OUT_WIN_RE.search(t) and not _is_generic(t):
        return _win_subtype(t)
    if _OUT_MISSED_RE.search(t):
        return "missed"
    # A manual / net loss (cut, closed for a loss, -X pips) BEFORE the stop check,
    # so a stated-pips loss is scored at its real R, not the stop's -1R.
    if _OUT_MANUAL_LOSS_RE.search(t):
        return "manual_loss"
    if _OUT_BE_STOP_RE.search(t):
        return "be_stop"
    if _OUT_MOVE_BE_RE.search(t):
        return "move_be"
    if _OUT_STOP_HIT_RE.search(t):
        return "stop_hit"
    # LAST: a standalone CONFIRMED pip result ("300 pips", "50 pips") with no other
    # cue -> a managed-profit win. Checked last so a "-40 pips" loss / "after 130
    # pips" stop / "running 200 pips" never reach here.
    if _bare_pips_result(t) and not _is_generic(t):
        return "profit_pips"
    return None


# Map an event to the coarse outcome label of a SINGLE message (used by callers /
# tests that look at one message in isolation; a move-to-BE reads as breakeven).
_EVENT_TO_OUTCOME = {
    "net_loss_verdict": "loss", "manual_loss": "loss", "stop_hit": "loss",
    "target_hit": "win", "profit_pips": "win", "profit_runknown": "win",
    "missed": "missed", "be_stop": "breakeven", "move_be": "breakeven",
}


def detect_outcome_cue(text):
    """
    The COARSE outcome a SINGLE message reports: 'win'/'loss'/'breakeven'/'missed'
    or None. (A move-to-BE reads breakeven in isolation; the loss-vs-breakeven
    chronology and the granular category are resolved in match_outcome_for_window.)
    """
    return _EVENT_TO_OUTCOME.get(_detect_event(text))


_EVENT_TO_CATEGORY = {
    "target_hit": OUT_TARGET_HIT,
    "profit_pips": OUT_MANAGED_PROFIT,
    "profit_runknown": OUT_PROFIT_RUNKNOWN,
}


def match_outcome_for_window(texts):
    """
    Resolve ONE trade's outcome category from the follow-up messages in its window,
    IN CHRONOLOGICAL ORDER (oldest-first). Returns (category, evidence).

    Category precedence:
      1. an explicit NET-LOSS verdict ("count it as a loss", "close it for a
         small loss", "1 win, 1 loss")                            -> manual_loss
      2. a confirmed PROFIT (money was made)                      -> target_hit /
         managed_profit_confirmed / profit_confirmed_r_unknown (the win sub-type).
         When several profit messages exist, the STRONGEST/LATEST confirmation
         (highest named target, then largest pips) is stored as the evidence —
         NOT the first "take tp1" instruction (the evidence-link fix).
      3. a no-fill                                                -> missed
      4. a MANUAL / net loss ("cut for -40 pips", "closed for a loss") -> manual_loss
         (NEVER dropped, never relabelled missed/breakeven)
      5. chronological stop: stop_hit BEFORE a move-to-BE -> original_stop_loss (-1R);
         AFTER it (or an explicit BE-stop) -> breakeven; lone move-to-BE -> breakeven
      6. nothing                                                  -> unclear
    """
    events = [(_detect_event(t), t) for t in texts]
    events = [(e, t) for e, t in events if e]
    if not events:
        return OUT_UNCLEAR, ""

    # 1. His explicit "count it as a loss" verdict overrides everything.
    for e, t in events:
        if e == "net_loss_verdict":
            return OUT_MANUAL_LOSS, t
    # 2. A confirmed profit means money was made. Across ALL profit messages, keep
    #    the STRONGEST/LATEST confirmation as evidence and classify from THAT — so
    #    "all tp hit 500 pips" wins over an earlier bare "take tp 1" instruction.
    profit = [(i, t) for i, (e, t) in enumerate(events) if e in _EVENT_TO_CATEGORY]
    if profit:
        _, best_t = max(profit, key=lambda it: (_profit_rank(it[1]), it[0]))
        # A FLOATING pip figure ("up to 50 pips") that then SCRATCHED at breakeven,
        # with NO banked partial, is a breakeven — not a win. (A genuinely banked
        # pip take has a banking verb / target, or the window was cut at a re-entry
        # before any BE-stop.)
        if all(_is_floating_pips(t) for _, t in profit):
            be = next((t for e, t in events if e == "be_stop"), None)
            if be is not None:
                return OUT_BREAKEVEN, be
        return _EVENT_TO_CATEGORY[_win_subtype(best_t)], best_t
    # 3. A missed entry means no trade was taken.
    for e, t in events:
        if e == "missed":
            return OUT_MISSED, t
    # 4. A manual / net loss must NEVER be dropped.
    for e, t in events:
        if e == "manual_loss":
            return OUT_MANUAL_LOSS, t
    # 5. Chronological stop resolution (message order approximates timestamps).
    moved_be = False
    move_evidence = ""
    for e, t in events:
        if e == "move_be":
            moved_be = True
            move_evidence = move_evidence or t
        elif e == "be_stop":
            return OUT_BREAKEVEN, t
        elif e == "stop_hit":
            return (OUT_BREAKEVEN, t) if moved_be else (OUT_STOP_LOSS, t)
    if moved_be:
        return OUT_BREAKEVEN, move_evidence
    return OUT_UNCLEAR, ""


def _outcome_asset_key(s: str) -> str:
    """Normalise a ticker for same-asset matching ('XAUUSD'/'gold' -> 'XAU')."""
    s = (s or "").upper().replace("/", "").strip()
    for suf in ("USDT", "USDC", "USD"):
        if s.endswith(suf) and len(s) > len(suf):
            return s[: -len(suf)]
    return s


# Unambiguous crypto tickers used ONLY to spot a cross-asset outcome message
# (e.g. a "BTC tp1 hit" leaking into a gold trade's window). Kept to clearly
# non-English symbols so we don't mis-tag a gold message that happens to contain
# an English word — being WRONG here would drop a real gold win.
_OUTCOME_CRYPTO_BASES = {
    "BTC", "ETH", "SOL", "BNB", "XRP", "ADA", "DOGE", "AVAX", "LINK", "MATIC",
    "DOT", "LTC", "BCH", "PEPE", "SHIB", "FET", "SUI", "APT", "INJ", "TIA", "SEI",
}

_THREAD_RE = re.compile(r"posted\s+in\s+(.+?)\s*(?:`|$)", re.I)


def _thread_of(text: str) -> str:
    """
    The channel SECTION/thread an aggregator message was posted in, normalised:
    "… Posted in 🐚・gold-trades `Whale` …" -> "gold-trades". '' if not present.
    Used to keep a gold-thread outcome from matching a different-thread trade.
    """
    m = _THREAD_RE.search(text or "")
    if not m:
        return ""
    return re.sub(r"[^a-z0-9]+", "-", m.group(1).lower()).strip("-")


def _outcome_msg_asset_key(text: str) -> str:
    """
    Best-effort asset key for an OUTCOME/management message — more aggressive than
    the parser's detector so a different-asset result is recognised and EXCLUDED.
    Returns '' when no asset is named (a same-thread context message).
    """
    import module_b_parser as parser
    a = parser._detect_instrument(text or "")[0]
    if a:
        return _outcome_asset_key(a)
    t = (text or "").upper()
    if re.search(r"\bGOLD\b|\bXAU\b", t):
        return "XAU"
    if re.search(r"\bSILVER\b|\bXAG\b", t):
        return "XAG"
    for base in _OUTCOME_CRYPTO_BASES:
        if re.search(r"\b" + re.escape(base) + r"\b", t):
            return base
    return ""


def assign_detected_outcomes(rows):
    """
    For each 'clean signal' row, look at the later messages on the SAME asset and
    SAME thread, after it and BEFORE the next entry on that asset, and fill
    DetectedOutcome / OutcomeEvidence by matching outcome cues. `rows` must be in
    chronological order. Mutates and returns `rows`. Read-only analysis.

    Accuracy guards:
      * ASSET CONSISTENCY — a window message that names a DIFFERENT asset (e.g. a
        "BTC tp1 hit" under a gold trade) is excluded; a no-asset message is only
        taken if it's in the SAME thread/section as the entry.
      * HYPOTHETICAL WIN CUES ARE SUPPRESSED, BUT THE MESSAGE IS KEPT — a generic
        "if price could hit tp" won't read as a win (that's handled in
        _detect_event), yet the message still enters the window so a concrete
        verdict buried in it ("…close it for a small loss") is NOT lost.
      * INVALID STOP — a confirmed win on a trade whose stop is on the wrong side
        of entry can't yield a target/pip R, so it's kept as a win but scored 0R.
    """
    import module_b_parser as parser

    meta = []
    for r in rows:
        txt = r.get("RawMessage", "") or ""
        asset = r.get("Asset") or parser._detect_instrument(txt)[0]
        is_entry = (r.get("Classification") == CLASS_CLEAN) or parser.has_fresh_entry(txt)
        meta.append({
            "key": _outcome_asset_key(asset),
            "msg_key": _outcome_msg_asset_key(txt),   # aggressive (catches bare BTC)
            "thread": _thread_of(txt),
            "is_entry": is_entry,
            "text": txt,
        })

    for p, r in enumerate(rows):
        if r.get("Classification") != CLASS_CLEAN:
            continue
        key = meta[p]["key"]
        entry_thread = meta[p]["thread"]
        # Window ends at the next ENTRY (clean or re-entry) on the SAME asset.
        end = len(rows)
        for q in range(p + 1, len(rows)):
            if meta[q]["is_entry"] and meta[q]["key"] == key:
                end = q
                break
        window = []
        candidates = 0          # same-asset/thread, non-entry messages seen (incl. generic)
        for q in range(p + 1, end):
            if meta[q]["is_entry"]:
                continue
            txt = meta[q]["text"]
            mk = meta[q]["msg_key"]
            if mk:
                if mk != key:
                    continue                          # different asset -> not this trade
            else:
                # No asset named: only take it if it's the SAME thread/section
                # (or threads are unknown). Stops cross-section leakage.
                mt = meta[q]["thread"]
                if entry_thread and mt and mt != entry_thread:
                    continue
            candidates += 1
            window.append(txt)        # generic win cues are suppressed downstream,
                                      # but the message is kept (verdicts survive)
        # RE-ENTRY ATTRIBUTION — once the PARENT has resolved (a profit/stop event),
        # a later re-entry starts a NEW position, so its target confirmations can't
        # be credited to the parent. Truncate the window at the first re-entry that
        # FOLLOWS a parent result. (A re-entry with no prior result is just the same
        # trade continuing and is left intact.)
        window = _truncate_at_reentry(window)
        outcome, evidence = match_outcome_for_window(window)
        # Refine a pip-based win against the signal's own targets: a confirmed pip
        # move that reaches the furthest target is target_hit; a smaller one is a
        # managed_profit partial (don't over-credit a distant unreached target).
        outcome = _refine_win_with_pips(outcome, evidence, r)
        # A confirmed win on a trade whose STOP is invalid (on the wrong side of
        # entry) can't be scored to a target/pip R -> keep the win, score it 0R.
        if outcome in _WIN_CATEGORIES and not _stop_is_valid(
                r.get("Direction"), r.get("Entry"), r.get("Stop")):
            outcome = OUT_PROFIT_RUNKNOWN
        # If there were same-context messages but none was a confirmed result,
        # label it instruction_only (chatter/instructions) rather than bare unclear.
        if outcome == OUT_UNCLEAR and candidates > 0:
            outcome = OUT_INSTRUCTION
        r["DetectedOutcome"] = outcome
        r["OutcomeEvidence"] = evidence
    return rows


def _classify_message(text, parse_ctx):
    """
    Classify one message. Returns (classification, fields, confidence).

    Chatter (no signal shape) -> 'commentary' with no API call. Signal-shaped
    messages get the quality-filter confidence and, when parsing is available,
    are run through the real parser + router: a cleanly routable signal is
    'clean signal'; anything the router flags (or that won't parse) is 'REVIEW'.
    Without a key (or --no-parse), signal-shaped messages are marked 'REVIEW'
    (needs a human/parse) and fields come from the conservative regex.
    """
    import signal_quality
    import module_b_parser as parser
    import module_router as router

    _blank = {k: "" for k in ("asset", "direction", "entry", "stop", "tp1", "tp2", "tp3")}

    # PRIORITY: a management / running-trade update is never auto-promoted to a
    # clean signal. Checked FIRST. BUT a RE-ENTRY (management language that ALSO
    # carries a complete fresh signal — direction + entry + stop) is surfaced as
    # REVIEW so a real re-entry isn't missed; pure management stays commentary.
    if parser.is_management(text):
        if parser.has_fresh_entry(text):
            sig = None
            try:
                sig = parser.parse_locally(text)
            except Exception:
                sig = None
            fields = _fields_from_signal(sig) if sig is not None else _regex_fields(text)
            return CLASS_REVIEW, fields, signal_quality.classify(text).level
        return CLASS_COMMENTARY, _blank, ""

    if not _looks_like_signal(text):
        return CLASS_COMMENTARY, _blank, ""

    confidence = signal_quality.classify(text).level

    # 1) Deterministic parse first (free, reliable, handles entry RANGES). It
    #    returns a Signal only when it confidently reads direction + instrument +
    #    entry zone — otherwise None.
    sig = None
    try:
        sig = parser.parse_locally(text)
    except Exception:
        sig = None

    # 2) For anything the deterministic parser couldn't read, fall back to the LLM
    #    (only if it's available and hasn't already failed this run).
    if sig is None and parse_ctx.get("ok"):
        try:
            sig = parser.parse_with_llm(text)
        except parser.ParserError:
            sig = None
        except Exception as e:
            parse_ctx["ok"] = False           # stop hammering a failing API
            parse_ctx["error"] = str(e)
            sig = None

    if sig is not None:
        # The ROUTER decides clean vs REVIEW — and it REQUIRES a valid stop (plus
        # asset + direction + entry). So a range with NO stop, or management
        # chatter, is sent to REVIEW, never promoted to a clean signal.
        decision = router.route(sig)
        return (CLASS_CLEAN if not decision.needs_review else CLASS_REVIEW), \
            _fields_from_signal(sig), decision.confidence

    # Signal-shaped but neither parser could read it confidently.
    return CLASS_REVIEW, _regex_fields(text), confidence


def _parsing_available(no_parse: bool):
    """Can we run the LLM parser? Returns (ok, reason_if_not)."""
    if no_parse:
        return False, "--no-parse was given"
    try:
        import anthropic  # noqa: F401
    except ImportError:
        return False, "the 'anthropic' library isn't installed"
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return False, "ANTHROPIC_API_KEY isn't set"
    return True, ""


async def _resolve_sender(message) -> str:
    """A human-readable sender: @username, else full name, else channel author/id."""
    author = getattr(message, "post_author", None)
    if author:
        return author
    try:
        sender = await message.get_sender()
    except Exception:
        sender = None
    if sender is not None:
        username = getattr(sender, "username", None)
        if username:
            return f"@{username}"
        name = " ".join(p for p in (getattr(sender, "first_name", "") or "",
                                    getattr(sender, "last_name", "") or "") if p).strip()
        if name:
            return name
    sid = getattr(message, "sender_id", None)
    return str(sid) if sid else "(channel)"


async def _fetch_history_async(TelegramClient, api_id, api_hash, channels, limit):
    """
    Log in and pull up to `limit` past messages from each configured channel.
    READ-ONLY: it only reads message history. Returns a dict with the collected
    messages and a 'flood' seconds value if Telegram asked us to stop early.
    """
    client = await _make_client_and_login(TelegramClient, api_id, api_hash)
    if client is None:
        return None

    try:
        from telethon.errors import FloodWaitError
    except Exception:  # pragma: no cover
        class FloodWaitError(Exception):
            seconds = 0

    # Match the built FloodWait policy: let Telethon auto-sleep SMALL waits
    # (<= our short threshold), and we catch + report + STOP on a big one.
    try:
        client.flood_sleep_threshold = _SHORT_WAIT_SECONDS
    except Exception:
        pass

    collected = []
    flood = None
    try:
        for ch in channels:
            try:
                async for msg in client.iter_messages(ch, limit=limit):
                    collected.append({
                        "date": msg.date,
                        "sender": await _resolve_sender(msg),
                        "channel": str(ch),
                        # IDs + edit time for the permanent archive (message_key =
                        # telegram:{channel_id}:{message_id}); harmless to run_history.
                        "channel_id": str(getattr(msg, "chat_id", None) or ch),
                        "message_id": getattr(msg, "id", None),
                        "edited": getattr(msg, "edit_date", None),
                        "text": (msg.message or getattr(msg, "raw_text", "") or ""),
                    })
            except FloodWaitError as e:
                flood = int(getattr(e, "seconds", 0) or 0)
                break   # one careful fetch — do NOT keep hammering
    finally:
        await client.disconnect()
    return {"messages": collected, "flood": flood}


def _write_history_csv(rows, path):
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=HISTORY_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def run_history(limit=None, sender_filter=None, no_parse=False, out_path=None):
    """
    Back-log mode: fetch past messages, classify them, print a reviewable list,
    and write history_review.csv. Touches paper_log.csv NOT AT ALL.
    """
    tele = _load_telethon()
    if not tele:
        return
    TelegramClient, _events = tele

    creds = _read_credentials()
    if not creds:
        return
    api_id, api_hash = creds

    raw = config.TELEGRAM_CHANNEL
    raw_items = raw if isinstance(raw, (list, tuple)) else [raw]
    channel_names = [str(c).strip() for c in raw_items if str(c).strip()]
    if not channel_names:
        return _friendly_stop(
            "no channel is set.\n"
            "  Open config.py and set TELEGRAM_CHANNEL to the channel's @username\n"
            "  or its numeric ID before fetching history."
        )
    channels = [int(c) if c.lstrip("-").isdigit() else c for c in channel_names]

    # Clamp the count so a typo can't ask for a huge, API-hammering fetch.
    limit = HISTORY_DEFAULT if not limit else int(limit)
    clamped = max(1, min(limit, HISTORY_MAX))
    out_path = out_path or HISTORY_REVIEW_FILE

    can_parse, why_not = _parsing_available(no_parse)

    print("=" * 64)
    print("   SIGNAL LISTENER (Telegram)   —   HISTORY BACK-LOG (read-only)")
    print("=" * 64)
    print(f"   Channel(s)   : {', '.join(channel_names)}")
    print(f"   Fetching     : last {clamped} message(s)"
          + (f"  (you asked for {limit}, capped at {HISTORY_MAX})" if clamped != limit else ""))
    if sender_filter:
        print(f"   Sender filter: only messages from '{sender_filter}'")
    print(f"   Classify     : deterministic parser + router + quality filter"
          + ("  (+ LLM fallback)" if can_parse else f"  (LLM off: {why_not})"))
    print("   It PRINTS and writes a review CSV. It logs NOTHING to paper_log.csv,")
    print("   places no trades, and only READS Telegram. (PAPER / preview.)")
    print("=" * 64)
    if not can_parse:
        print(f"\n  Note: the LLM fallback is off ({why_not}), but the deterministic parser")
        print("  still classifies clear one-line signals (incl. entry ranges). Only")
        print("  messages it can't read confidently are left as REVIEW.\n")

    # --- The one careful fetch (read-only, FloodWait-respecting) -------------
    try:
        result = asyncio.run(
            _fetch_history_async(TelegramClient, api_id, api_hash, channels, clamped))
    except KeyboardInterrupt:
        print("\n  Cancelled. Nothing was logged.")
        return
    if result is None:
        return   # login failed; _make_client_and_login already explained why

    messages = result["messages"]
    # Telegram returns newest-first; show oldest-first so history reads in order.
    messages.reverse()

    # Effective sender: prefer a poster embedded in the text (aggregator channels),
    # else the Telegram sender. Used for BOTH the --sender filter and the CSV.
    for m in messages:
        m["sender"] = _extract_poster(m["text"]) or m["sender"]

    if sender_filter:
        sf = sender_filter.lower().lstrip("@")
        messages = [m for m in messages if sf in (m["sender"] or "").lower().lstrip("@")]

    if not messages:
        print("\n  No messages matched. (Empty channel, or the sender filter excluded all.)")
        if result["flood"]:
            _report_flood_wait(result["flood"])
        return

    # --- Classify + build rows ---------------------------------------------
    parse_ctx = {"ok": can_parse, "error": ""}
    rows = []
    counts = {CLASS_CLEAN: 0, CLASS_COMMENTARY: 0, CLASS_REVIEW: 0}
    print(f"  Reviewing {len(messages)} message(s)"
          + ("  (parsing signal-shaped ones — this can take a moment)\n" if can_parse else "\n"))
    for i, m in enumerate(messages, start=1):
        text = m["text"]
        cls, fields, confidence = _classify_message(text, parse_ctx)
        counts[cls] = counts.get(cls, 0) + 1
        date_str = m["date"].strftime("%Y-%m-%d %H:%M") if m["date"] else ""
        rows.append({
            "Date": date_str,
            "Sender": m["sender"],
            "Asset": fields["asset"],
            "Direction": fields["direction"],
            "Entry": fields["entry"],
            "Stop": fields["stop"],
            "TP1": fields["tp1"],
            "TP2": fields["tp2"],
            "TP3": fields["tp3"],
            "Classification": cls,
            "Confidence": confidence,
            "DetectedOutcome": "",      # filled by the matching pass below
            "OutcomeEvidence": "",
            "RawMessage": text.replace("\n", " ").strip(),
        })
        # Console line: clear and skimmable (sanitised for the console; the CSV
        # keeps the original UTF-8 text).
        summary = " ".join(p for p in (fields["asset"], fields["direction"], fields["entry"]) if p)
        tag = f"[{cls}]"
        snippet = rows[-1]["RawMessage"]
        if len(snippet) > 80:
            snippet = snippet[:77] + "..."
        sender_disp = _console_safe(m["sender"])
        print(f"  {i:>3}) {date_str}  {sender_disp:<16} {tag:<15} {_console_safe(summary)}")
        print(f"        \"{_console_safe(snippet)}\"")

    if parse_ctx.get("error"):
        print(f"\n  Note: the parser stopped responding ({parse_ctx['error']}).")
        print("  Remaining messages were classified by heuristic only.")

    # --- Match later result/management messages back to each entry signal ----
    # (Read-only analysis; fills DetectedOutcome / OutcomeEvidence for clean
    # signals. Conservative: ambiguous -> 'unclear' with no evidence.)
    assign_detected_outcomes(rows)

    # --- Write the reviewable CSV (NOT the paper log) -----------------------
    try:
        _write_history_csv(rows, out_path)
    except OSError as e:
        print(f"\n  (Couldn't write {out_path}: {e})")
        out_path = None

    print("\n" + "-" * 64)
    print(f"  Reviewed {len(rows)} message(s):  "
          f"{counts.get(CLASS_CLEAN,0)} clean signal, "
          f"{counts.get(CLASS_COMMENTARY,0)} commentary, "
          f"{counts.get(CLASS_REVIEW,0)} REVIEW")

    # Detected-outcome distribution for the clean entry signals, RECONCILED so
    # every clean signal is accounted for (an AID — verify each).
    clean_rows = [r for r in rows if r["Classification"] == CLASS_CLEAN]
    if clean_rows:
        cats = {}
        for r in clean_rows:
            key = r["DetectedOutcome"] or OUT_UNCLEAR
            cats[key] = cats.get(key, 0) + 1
        order = [OUT_TARGET_HIT, OUT_MANAGED_PROFIT, OUT_PROFIT_RUNKNOWN,
                 OUT_MANUAL_LOSS, OUT_STOP_LOSS, OUT_BREAKEVEN, OUT_MISSED,
                 OUT_INSTRUCTION, OUT_UNCLEAR]
        print(f"  Outcome distribution (clean signals = {len(clean_rows)}):")
        for k in order:
            if cats.get(k):
                print(f"      {k:<28} {cats[k]}")
        for k in cats:                                   # any unexpected label
            if k not in order:
                print(f"      {k:<28} {cats[k]}  (UNEXPECTED)")
        # Coarse roll-up + reconciliation check.
        wins = sum(cats.get(c, 0) for c in (OUT_TARGET_HIT, OUT_MANAGED_PROFIT, OUT_PROFIT_RUNKNOWN))
        losses = sum(cats.get(c, 0) for c in (OUT_MANUAL_LOSS, OUT_STOP_LOSS))
        be = cats.get(OUT_BREAKEVEN, 0)
        miss = cats.get(OUT_MISSED, 0)
        unsure = cats.get(OUT_INSTRUCTION, 0) + cats.get(OUT_UNCLEAR, 0)
        total = wins + losses + be + miss + unsure
        print(f"  Roll-up: {wins} win / {losses} loss / {be} breakeven / "
              f"{miss} missed / {unsure} unclear-or-instruction")
        ok = "OK" if total == len(clean_rows) else f"MISMATCH (sum {total})"
        print(f"  Reconciliation: {total} categorised == {len(clean_rows)} clean signals  [{ok}]")
        print("  ** Detected outcomes are an AID — VERIFY the OutcomeEvidence column")
        print("     before trusting any of them. Nothing was auto-logged.")
    if out_path:
        print(f"  Review file written: {os.path.abspath(out_path)}")
        print("  Open it in Excel, sort/filter by Sender or Classification, and decide")
        print("  what (if anything) to log — nothing was added to paper_log.csv.")
    if result["flood"]:
        print("-" * 64)
        print("  NOTE: the fetch was cut short by a Telegram FloodWait —")
        _report_flood_wait(result["flood"])
        print(f"  The {len(rows)} message(s) fetched BEFORE that are saved above.")
    print("-" * 64)


def pull_for_archive(limit=None, sender_filter=None, no_parse=True, backfill=False):
    """
    READ-ONLY Telegram fetch for the permanent archive (archive.py). Returns a list
    of normalised message records (oldest-first), each:

        {channel_id, message_id, raw_text, sent_at_utc, edited_at_utc, sender,
         classification, asset, direction, entry, stop, tp1, tp2, tp3}

    backfill=True: this is a HISTORICAL back-fill of past messages we did NOT receive
    live, so the listener-received / parsed STAGE timestamps are left BLANK (not
    stamped to 'now'). That keeps these signals honestly POSTED-ONLY (T-C): we never
    fabricate a receipt time months after the fact, so nothing can mistake a back-fill
    for a real-time (T-A/T-B) capture.

    Does NOT write any CSV and touches paper_log.csv NOT AT ALL. Returns [] if
    Telethon/credentials/channel are unavailable (the caller decides what to do).
    """
    tele = _load_telethon()
    if not tele:
        return []
    TelegramClient, _events = tele
    creds = _read_credentials()
    if not creds:
        return []
    api_id, api_hash = creds

    raw = config.TELEGRAM_CHANNEL
    raw_items = raw if isinstance(raw, (list, tuple)) else [raw]
    channel_names = [str(c).strip() for c in raw_items if str(c).strip()]
    if not channel_names:
        return []
    channels = [int(c) if c.lstrip("-").isdigit() else c for c in channel_names]
    limit = HISTORY_DEFAULT if not limit else int(limit)
    clamped = max(1, min(limit, HISTORY_MAX))

    can_parse, _why = _parsing_available(no_parse)
    try:
        result = asyncio.run(
            _fetch_history_async(TelegramClient, api_id, api_hash, channels, clamped))
    except KeyboardInterrupt:
        return []
    if result is None:
        return []
    # Surface whether Telegram cut the fetch short with a FloodWait, so a caller can
    # report honestly that the accessible history may be capped (not silently partial).
    global _LAST_PULL_FLOOD
    _LAST_PULL_FLOOD = result.get("flood")
    messages = result["messages"]
    messages.reverse()                       # oldest-first
    for m in messages:
        m["sender"] = _extract_poster(m["text"]) or m["sender"]
    if sender_filter:
        sf = sender_filter.lower().lstrip("@")
        messages = [m for m in messages if sf in (m["sender"] or "").lower().lstrip("@")]

    parse_ctx = {"ok": can_parse, "error": ""}
    records = []
    for m in messages:
        text = m["text"] or ""
        # Stage timestamps for the archive's signal_timing (groundwork for shadow
        # mode): listener_received = when we took the message off the fetch;
        # parsed = the moment parsing/classification completed.
        received_at = _now_utc_iso()
        cls, fields, _conf = _classify_message(text, parse_ctx)
        parsed_at = _now_utc_iso()
        # For a historical back-fill we leave the stage timestamps BLANK — we did not
        # receive these messages live, so stamping 'now' would invent a months-long
        # "receipt latency" and risk implying a real receipt time. Posted-only = T-C.
        if backfill:
            received_at = ""
            parsed_at = ""
        records.append({
            "channel_id": str(m.get("channel_id") or m.get("channel") or ""),
            "message_id": m.get("message_id"),
            "raw_text": text,
            "sent_at_utc": _to_utc_iso(m.get("date")),     # telegram_posted_at
            "edited_at_utc": _to_utc_iso(m.get("edited")),
            "listener_received_at": received_at,
            "parsed_at": parsed_at,
            "sender": m.get("sender") or "",
            "classification": cls,
            "asset": fields.get("asset", ""),
            "direction": fields.get("direction", ""),
            "entry": fields.get("entry", ""),
            "stop": fields.get("stop", ""),
            "tp1": fields.get("tp1", ""),
            "tp2": fields.get("tp2", ""),
            "tp3": fields.get("tp3", ""),
        })
    return records


def _now_utc_iso():
    """The current instant as a UTC ISO-8601 string (stage-capture timestamps)."""
    from datetime import datetime as _dt, timezone as _tz
    return _dt.now(_tz.utc).isoformat()


def _to_utc_iso(dt):
    """A timezone-aware datetime -> UTC ISO-8601 string, or '' if missing."""
    if dt is None:
        return ""
    try:
        from datetime import timezone as _tz
        if dt.tzinfo is None:
            return dt.isoformat()
        return dt.astimezone(_tz.utc).isoformat()
    except Exception:
        return str(dt)


def _parse_cli(args):
    """Tiny arg parser for the listener's modes/flags."""
    opts = {"mode": "preview", "history": None, "sender": None,
            "no_parse": False, "out": None, "bad": None}
    i = 0
    while i < len(args):
        a = args[i]
        if a in ("--list", "-l", "list"):
            opts["mode"] = "list"
        elif a in ("--history", "-H", "history"):
            opts["mode"] = "history"
            # An optional number may follow.
            if i + 1 < len(args) and args[i + 1].lstrip("-").isdigit():
                opts["history"] = int(args[i + 1]); i += 1
        elif a == "--sender":
            i += 1
            opts["sender"] = args[i] if i < len(args) else None
        elif a == "--no-parse":
            opts["no_parse"] = True
        elif a == "--out":
            i += 1
            opts["out"] = args[i] if i < len(args) else None
        elif a in ("-h", "--help", "help"):
            opts["mode"] = "help"
        else:
            opts["bad"] = a
            break
        i += 1
    return opts


def _print_usage():
    print("  Usage:")
    print("    python module_a_telegram.py                 # watch the channel(s) in PREVIEW mode")
    print("    python module_a_telegram.py --list           # list your channels/groups and their IDs")
    print("    python module_a_telegram.py --history 500    # back-log the last 500 messages (review only)")
    print("    python module_a_telegram.py --history 500 --sender farouk   # only that sender")
    print("    python module_a_telegram.py --history 500 --no-parse        # skip the LLM (heuristic only)")
    print("    python module_a_telegram.py --history 500 --out myfile.csv   # choose the review file")


def main():
    import sys
    args = [a for a in sys.argv[1:] if a.strip()]
    opts = _parse_cli(args)

    if opts["bad"]:
        print(f"\n  Unknown option: {opts['bad']}")
        _print_usage()
        print()
        return
    if opts["mode"] == "help":
        _print_usage()
    elif opts["mode"] == "list":
        list_dialogs()
    elif opts["mode"] == "history":
        run_history(limit=opts["history"], sender_filter=opts["sender"],
                    no_parse=opts["no_parse"], out_path=opts["out"])
    else:
        run_preview()


if __name__ == "__main__":
    main()
