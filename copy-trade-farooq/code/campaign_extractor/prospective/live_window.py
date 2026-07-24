"""
Gate 1 — bounded live observation window. Connects to Telegram (read-only, PREVIEW),
attaches the approved prospective recorder, listens for a SHORT bounded time, disconnects,
and writes a result JSON. Observational only: no broker, no OAuth, no order code, no trading
pipeline. Quote fields stay NULL/BROKER_NOT_CONNECTED.

Usage: python live_window.py [seconds]
"""
import asyncio
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ST = os.path.dirname(os.path.dirname(HERE))          # signal-terminal
sys.path.insert(0, ST)

RESULT = os.path.join(HERE, "data", "live_window_result.json")


async def _run(seconds):
    import module_a_telegram as mat
    import config
    tele = mat._load_telethon()
    if not tele:
        return {"status": "no_telethon"}
    TelegramClient, events = tele
    creds = mat._read_credentials()
    if not creds:
        return {"status": "no_credentials"}
    api_id, api_hash = creds
    raw = config.TELEGRAM_CHANNEL
    raw_items = raw if isinstance(raw, (list, tuple)) else [raw]
    channels = [int(c) if c.lstrip("-").isdigit() else c
                for c in (str(x).strip() for x in raw_items) if c]

    client = await mat._make_client_and_login(TelegramClient, api_id, api_hash)
    if client is None:
        return {"status": "login_failed"}

    recorder = mat._prospective_recorder()
    before = recorder.db.count("prospective_message_evidence")
    captured = {"n": 0}

    @client.on(events.NewMessage(chats=channels))
    async def _h(event):
        mat._record_prospective(recorder, event)
        captured["n"] += 1

    await asyncio.sleep(seconds)
    await client.disconnect()

    after = recorder.db.count("prospective_message_evidence")
    # quote-context integrity: every row NULL / BROKER_NOT_CONNECTED
    bad = recorder.db.con.execute(
        "SELECT COUNT(*) FROM prospective_quote_context "
        "WHERE bid IS NOT NULL OR ask IS NOT NULL OR context_status NOT IN "
        "('BROKER_NOT_CONNECTED','AUTH_NOT_AVAILABLE')").fetchone()[0]
    return {"status": "ok", "window_seconds": seconds, "channels": channels,
            "captured_in_window": captured["n"], "db_rows_before": before,
            "db_rows_after": after, "quote_context_violations": bad,
            "db_path": os.path.relpath(recorder.db.db_path, ST)}


def main():
    secs = int(sys.argv[1]) if len(sys.argv) > 1 else 75
    try:
        res = asyncio.run(_run(secs))
    except Exception as e:
        res = {"status": "error", "error": repr(e)}
    os.makedirs(os.path.dirname(RESULT), exist_ok=True)
    with open(RESULT, "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=2)
    print(json.dumps(res, ensure_ascii=False))


if __name__ == "__main__":
    main()
