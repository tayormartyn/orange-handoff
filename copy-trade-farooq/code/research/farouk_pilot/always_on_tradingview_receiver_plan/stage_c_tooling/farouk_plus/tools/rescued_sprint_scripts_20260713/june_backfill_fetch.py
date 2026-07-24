"""
Sprint Day 3 — BOUNDED copied-session backward fetch of June gold-trades history.

Method (proven 2026-07-10, twice): copy whale_room.session to a temp file (live session file
untouched, listener PID 87988 undisturbed), one short-lived Telethon connection, bounded
iter_messages, disconnect, delete the temp session copy.

Hard bounds: date window 2026-06-01T00:00Z .. 2026-06-29T23:59Z; message cap 1600; photo
download cap 100 (gold-trades photos only); image-only, 10MiB streaming cap via the existing
media_capture store (sha256-addressed, append-only, dedup-indexed).

Storage: June message text -> NEW append-only DB june_history_backfill_v1.db (separate file, no
write contention with the live listener's evidence DB). Photos -> existing prospective_media_v1
dir + DB (same as the proven Jul-10 backfill). Observation-only; nothing is reprocessed as a
signal. No broker/execution surface.
"""
import asyncio, os, shutil, sqlite3, sys, io, json
from datetime import datetime, timezone

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = r"C:\Users\Marty\signal-terminal"
SCRATCH = r"C:\Users\Marty\AppData\Local\Temp\claude\C--Users-Marty\5fc06f59-5409-4db3-ac12-a901363ccb04\scratchpad"
sys.path.insert(0, os.path.join(ROOT, r"campaign_extractor\media_capture"))
import store as media_store
from media_db import MediaDB

CHANNEL_ID = -1001902136163
ALLOW_CHANNEL = "-1001902136163"
WINDOW_START = datetime(2026, 6, 1, 0, 0, 0, tzinfo=timezone.utc)
WINDOW_END = datetime(2026, 6, 30, 0, 0, 0, tzinfo=timezone.utc)   # exclusive; = Jun-29 23:59:59 inclusive
MSG_CAP = 1600
PHOTO_CAP = 100

LIVE_SESSION = os.path.join(ROOT, "whale_room.session")
TEMP_SESSION = os.path.join(SCRATCH, "june_backfill_copy.session")
JUNE_DB = os.path.join(ROOT, r"campaign_extractor\prospective\data\june_history_backfill_v1.db")
MEDIA_DB_PATH = os.path.join(ROOT, r"campaign_extractor\prospective\data\prospective_media_v1.db")
DUMP = os.path.join(SCRATCH, "june_gold_trades_dump.jsonl")

DDL = """
CREATE TABLE IF NOT EXISTS june_message_evidence (
    rowseq INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_channel_id TEXT NOT NULL,
    telegram_message_id TEXT NOT NULL UNIQUE,
    telegram_posted_at_utc TEXT NOT NULL,
    raw_text TEXT,
    media_reference_or_hash TEXT,
    grouped_media_id TEXT,
    fetch_method TEXT NOT NULL,
    fetched_at_utc TEXT NOT NULL)
"""
TRIGGERS = [
    "CREATE TRIGGER IF NOT EXISTS june_no_update BEFORE UPDATE ON june_message_evidence "
    "BEGIN SELECT RAISE(ABORT, 'append-only: UPDATE forbidden'); END",
    "CREATE TRIGGER IF NOT EXISTS june_no_delete BEFORE DELETE ON june_message_evidence "
    "BEGIN SELECT RAISE(ABORT, 'append-only: DELETE forbidden'); END",
]


def media_ref_of(msg):
    if msg.media is None:
        return None
    return f"media:{type(msg.media).__name__}:{msg.id}"


async def main():
    api_id = int(os.environ["TELEGRAM_API_ID"])
    api_hash = os.environ["TELEGRAM_API_HASH"]

    # copied-session method: live session file is only READ (copied); never written/locked
    shutil.copy2(LIVE_SESSION, TEMP_SESSION)
    from telethon import TelegramClient

    jcon = sqlite3.connect(JUNE_DB)
    jcon.execute(DDL)
    for t in TRIGGERS:
        jcon.execute(t)
    jcon.commit()

    mdb = MediaDB(MEDIA_DB_PATH)

    client = TelegramClient(TEMP_SESSION.replace(".session", ""), api_id, api_hash)
    await client.connect()
    if not await client.is_user_authorized():
        raise SystemExit("copied session not authorized — abort")

    entity = await client.get_entity(CHANNEL_ID)

    fetched = 0
    stored_new = 0
    dup_skipped = 0
    photo_targets = []
    gold_rows = []
    all_msgs = []          # in-memory buffer so the album scan needs NO second network pass
    now_iso = datetime.now(timezone.utc).isoformat()

    async for msg in client.iter_messages(entity, offset_date=WINDOW_END):
        if msg.date < WINDOW_START:
            break
        if fetched >= MSG_CAP:
            print(f"HARD CAP {MSG_CAP} reached — stopping (bounded by design)")
            break
        fetched += 1
        all_msgs.append(msg)
        text = msg.message or ""
        mref = media_ref_of(msg)
        gid = str(msg.grouped_id) if msg.grouped_id else None
        try:
            jcon.execute(
                "INSERT INTO june_message_evidence (telegram_channel_id, telegram_message_id, "
                "telegram_posted_at_utc, raw_text, media_reference_or_hash, grouped_media_id, "
                "fetch_method, fetched_at_utc) VALUES (?,?,?,?,?,?,?,?)",
                (ALLOW_CHANNEL, str(msg.id), msg.date.isoformat(), text, mref, gid,
                 "copied_session_bounded_june_backfill_v1", now_iso))
            jcon.commit()
            stored_new += 1
        except sqlite3.IntegrityError:
            dup_skipped += 1

        is_gold = "gold-trades" in text
        if is_gold:
            gold_rows.append({"message_id": msg.id, "posted_at": msg.date.isoformat(),
                              "text": text, "media_ref": mref, "grouped_id": gid})
        # photos: gold-trades authored posts, or photo-only album members right after a gold post
        if msg.photo is not None and is_gold:
            photo_targets.append(msg)

    # album continuation photos (empty text, grouped with a gold-trades caption message) — local scan
    gold_gids = {r["grouped_id"] for r in gold_rows if r["grouped_id"]}
    for msg in all_msgs:
        if msg.photo is not None and not (msg.message or "") and msg.grouped_id \
                and str(msg.grouped_id) in gold_gids \
                and all(m.id != msg.id for m in photo_targets):
            photo_targets.append(msg)

    photo_targets = sorted(photo_targets, key=lambda m: m.id)[:PHOTO_CAP]
    print(f"fetched={fetched} stored_new={stored_new} dup_skipped={dup_skipped} "
          f"gold_msgs={len(gold_rows)} photo_targets={len(photo_targets)}")

    captured = 0
    statuses = {}
    for msg in photo_targets:
        if msg.file and msg.file.size and msg.file.size > 10 * 1024 * 1024:
            statuses["SKIPPED_TOO_LARGE_PRECHECK"] = statuses.get("SKIPPED_TOO_LARGE_PRECHECK", 0) + 1
            continue
        dl_start = datetime.now(timezone.utc).isoformat()
        data = await client.download_media(msg, file=bytes)
        dl_end = datetime.now(timezone.utc).isoformat()
        if not data:
            statuses["EMPTY_DOWNLOAD"] = statuses.get("EMPTY_DOWNLOAD", 0) + 1
            continue
        mref = f"media:MessageMediaPhoto:{msg.id}"
        descriptor = {"media_type": "photo", "sizes": [{"bytes": len(data), "ref": mref}]}
        identity = ("TELEGRAM", ALLOW_CHANNEL, str(msg.id), 1,
                    str(msg.grouped_id) if msg.grouped_id else None, 0, mref)
        ts = {"posted_at": msg.date.isoformat(), "created_at": dl_end,
              "dl_start": dl_start, "dl_end": dl_end}
        status = media_store.preserve_bytes(data, descriptor, identity, mdb, timestamps=ts)
        statuses[status] = statuses.get(status, 0) + 1
        if status == "MEDIA_CAPTURED":
            captured += 1

    await client.disconnect()
    jcon.close()
    mdb.close()
    for suffix in (".session", ".session-journal"):
        p = TEMP_SESSION.replace(".session", "") + suffix
        if os.path.exists(p):
            os.remove(p)

    with open(DUMP, "w", encoding="utf-8") as fh:
        for r in sorted(gold_rows, key=lambda x: x["message_id"]):
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")

    print(f"photos captured={captured} statuses={statuses}")
    print(f"gold-trades dump: {DUMP}")
    print("DONE — temp session removed, live session untouched")


asyncio.run(main())
