"""Route-level provider authorisation — advisory, FAIL CLOSED (16 proofs). Transport != provider route.
Deterministic; fake/offline; no broker action; gates false; no permit/lease."""
from __future__ import annotations
import os
import sqlite3
import sys
import tempfile
import time as _time

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DE = os.path.join(_ROOT, "campaign_extractor", "demo_executor")
_CON = os.path.join(_ROOT, "campaign_extractor", "paper_loop", "console")
for p in (_ROOT, _DE, _CON):
    if p not in sys.path:
        sys.path.insert(0, p)

import provider_route_authorisation as PRA
import symbol_schedule as SS
import advisory_bridge as AB
import operator_alerts as OA
import config as CFG

T = -1001937743421                                        # Whale Room transport
FAROUK = "terrilyn Posted in 🐚・sea-scalper-farouk\n\nhttps://youtube.com/x\n\nLive"
GOLD = "seascalperfarouk Posted in 🪙・gold-trades\n\n`Whale` GOLD BUY LIMIT 4116-4118 SL 4110 TP 4130"
JOSH = "navigatorjosh Posted in ⛵・josh-the-navigator\n\ngoing live"
SIGNAL_FAROUK = "somebody Posted in 🐚・sea-scalper-farouk\n\nGOLD BUY LIMIT 4116-4118 SL 4110 TP 4130"
NOW = 1_800_000_000_000
ACT = NOW - 120_000
FRESH_ISO = _time.strftime("%Y-%m-%dT%H:%M:%S", _time.gmtime((NOW - 60_000) / 1000))


def A(**kw):
    base = dict(sender_id=T, fwd_present=True, posted_ms=NOW - 60_000, activation_ms=ACT)
    base.update(kw)
    return PRA.authorise_route(**base)


# 1 transport alone never authorises (recognised transport + a NON-authorised room => not eligible)
def test_transport_alone_never_authorises():
    r = A(raw_text=GOLD)                                  # transport ok but gold-trades room not authorised
    assert r["transport_authorised"] is True
    assert r["provider_route_authorised"] is False and r["execution_eligible"] is False


# 2 exact confirmed Farouk route (post-activation) passes the route gate
def test_exact_route_authorised():
    r = A(raw_text=FAROUK, posted_ms=PRA.ROUTE_ACTIVATION_TS_MS + 60_000, activation_ms=0)
    assert r["route_status"] == "PROVIDER_ROUTE_AUTHORISED" and r["provider_route_authorised"] is True
    assert r["source_room_normalized"] == "sea-scalper-farouk" and r["personal_sender_verified"] is False
    assert r["provider_authorisation_type"] == "ROUTE_LEVEL"


# 2b prospective only: the confirmed route does NOT authorise a message older than route activation
def test_pre_activation_route_not_authorised():
    r = A(raw_text=FAROUK, posted_ms=PRA.ROUTE_ACTIVATION_TS_MS - 60_000, activation_ms=0)
    assert r["provider_route_authorised"] is False and "BEFORE_ROUTE_ACTIVATION" in r["authorisation_reason_codes"]


# 3 other source rooms blocked
def test_other_rooms_blocked():
    for txt in (GOLD, JOSH):
        r = A(raw_text=txt)
        assert r["route_status"] == "UNAUTHORISED_PROVIDER_ROUTE" and r["provider_route_authorised"] is False


# 4 spoofed farouk-room text from another sender blocks
def test_spoof_wrong_sender_blocks():
    r = A(sender_id=999888, raw_text=FAROUK)
    assert r["transport_authorised"] is False and "UNRECOGNISED_TRANSPORT" in r["authorisation_reason_codes"]
    assert r["provider_route_authorised"] is False


# 5 missing fwd metadata blocks
def test_missing_fwd_blocks():
    r = A(fwd_present=False, raw_text=FAROUK)
    assert "FWD_METADATA_MISSING" in r["authorisation_reason_codes"] and r["provider_route_authorised"] is False


# 6 malformed wrapper blocks (typed, no machine middot)
def test_malformed_wrapper_blocks():
    r = A(raw_text="randomuser Posted in sea-scalper-farouk\n\nGOLD BUY 4116 SL 4110")
    assert r["wrapper_valid"] is False and "FORWARD_WRAPPER_INVALID" in r["authorisation_reason_codes"]


# 7 partial route-name match blocks (loose 'farouk' substring must not authorise)
def test_partial_route_match_blocks():
    r = A(raw_text="x Posted in 🐚・farouk-vip-scalper\n\nGOLD BUY 4116 SL 4110")
    assert r["source_room_normalized"] == "farouk-vip-scalper"       # not the exact route
    assert r["route_status"] == "UNAUTHORISED_PROVIDER_ROUTE"


# 8 / 9 exact route with chat / video stays non-actionable (needs full advisory run)
def _seed(rows):
    d = tempfile.mkdtemp()
    AB.STATE_FILE = os.path.join(d, "b.json"); AB.RESULTS_LOG = os.path.join(d, "r.jsonl")
    OA.ALERT_LOG = os.path.join(d, "a.jsonl"); OA.STATE_FILE = os.path.join(d, "as.json")
    db = os.path.join(d, "p.db"); c = sqlite3.connect(db)
    c.execute("CREATE TABLE prospective_message_evidence (rowseq INTEGER PRIMARY KEY AUTOINCREMENT, "
              "telegram_message_id TEXT, telegram_channel_id TEXT, telegram_posted_at_utc TEXT, raw_text TEXT, "
              "media_reference_or_hash TEXT, telegram_sender_id TEXT, telegram_sender_username TEXT, "
              "telegram_sender_display TEXT, telegram_is_forwarded INTEGER, telegram_fwd_origin TEXT)")
    for mid, raw, sid, fwd in rows:
        c.execute("INSERT INTO prospective_message_evidence (telegram_message_id, telegram_channel_id, "
                  "telegram_posted_at_utc, raw_text, media_reference_or_hash, telegram_sender_id, "
                  "telegram_sender_username, telegram_sender_display, telegram_is_forwarded, telegram_fwd_origin) "
                  "VALUES (?,?,?,?,?,?,?,?,?,?)",
                  (mid, "-1001902136163", FRESH_ISO, raw, None, sid, None, "The Whale Room", fwd, "origin"))
    c.commit(); c.close()
    return d, db


def _qctx():
    q = type("Q", (), {"bid": 4124.0, "ask": 4124.2, "ts_ms": NOW - 2000})()
    path = [{"bid": 4125.0, "ask": 4125.2, "ts_ms": NOW - 40000}, {"bid": 4124.0, "ask": 4124.2, "ts_ms": NOW - 2000}]
    return q, "QUOTES_ACTIVE", path


def test_exact_route_chat_stays_unknown():
    d, db = _seed([("910", "someone Posted in 🐚・sea-scalper-farouk\n\nWhale, hi guys, lets go.", str(T), 1)])
    AB.enable(ACT)
    r = AB.process(NOW, db_path=db, quote_ctx=_qctx())[0]
    assert r["source_room_normalized"] == "sea-scalper-farouk" and r["intent"] == "UNKNOWN"
    assert r["may_create_proposal"] is False and r["no_campaign"] is True


def test_exact_route_video_non_actionable():
    d, db = _seed([("911", FAROUK, str(T), 1)])
    AB.enable(ACT)
    r = AB.process(NOW, db_path=db, quote_ctx=_qctx())[0]
    # a video/greeting from the exact route is NON-ACTIONABLE (no eligibility / proposal / campaign),
    # regardless of whether the contract tags it UNKNOWN or a non-signal update.
    assert r["intent"] != "NEW_SIGNAL"
    assert r["execution_eligible"] is False and r["may_create_proposal"] is False and r["no_campaign"] is True


# 10 authorised route + valid signal still BLOCKS when quotes are not QUOTES_ACTIVE
def test_authorised_route_signal_blocked_when_quotes_not_active():
    d, db = _seed([("912", SIGNAL_FAROUK, str(T), 1)])
    AB.enable(ACT)
    # QUOTES_STALE context: route passes, but the interpretation/quote gate still blocks eligibility
    r = AB.process(NOW, db_path=db, quote_ctx=(None, "QUOTES_STALE", []))[0]
    assert r["intent"] == "NEW_SIGNAL" and r["source_room_normalized"] == "sea-scalper-farouk"
    assert r["route_status"] == "PROVIDER_ROUTE_AUTHORISED"      # route gate passes...
    assert r["execution_eligible"] is False and r["no_campaign"] is True   # ...but quotes not active -> blocked


# 11 after TEMP route confirmation, signal still requires all normal safety checks
def test_temp_confirmation_still_requires_safety():
    # confirmed route + stale quotes -> still not eligible (quote/interpretation gates remain)
    r_stale = PRA.authorise_route(sender_id=T, fwd_present=True, raw_text=SIGNAL_FAROUK,
                                  posted_ms=NOW - 60_000, activation_ms=ACT, confirmed_routes=("sea-scalper-farouk",))
    assert r_stale["provider_route_authorised"] is True     # route authorised...
    # ...but the advisory bridge still ANDs it with interpretation eligibility (quote gate etc.)
    import farouk_contract as FC
    d = FC.interpret(raw_text=SIGNAL_FAROUK, provider_ts_ms=NOW - 60_000, now_ms=NOW,
                     quote=None, quote_path=[], quote_health_state="QUOTES_STALE")
    assert bool(d["execution_eligible"] and r_stale["provider_route_authorised"]) is False


# 12 poster label never trusted as identity
def test_poster_label_not_identity():
    r = A(raw_text=FAROUK)
    assert r["personal_sender_verified"] is False and r["source_poster_label"] == "terrilyn"


# 13 historical rows (pre-activation) not replayed
def test_historical_not_replayed():
    old = _time.strftime("%Y-%m-%dT%H:%M:%S", _time.gmtime((NOW - 10_000_000) / 1000))
    d, db = _seed([("1", SIGNAL_FAROUK, str(T), 1)])
    # overwrite posted time to pre-activation
    c = sqlite3.connect(db); c.execute("UPDATE prospective_message_evidence SET telegram_posted_at_utc=?", (old,)); c.commit(); c.close()
    AB.enable(ACT)
    assert AB.process(NOW, db_path=db, quote_ctx=_qctx()) == []


# 14 / 15 / 16 safety
def test_locks_no_broker_no_transport_in_module():
    de = open(os.path.join(_DE, "config.py"), encoding="utf-8").read()
    cfg = open(os.path.join(_ROOT, "config.py"), encoding="utf-8").read()
    cc = open(os.path.join(_ROOT, "ctrader_config.py"), encoding="utf-8").read()
    assert "ORDER_SENDING_ENABLED = False" in de and "ORDER_MANAGEMENT_ENABLED = False" in de
    assert "EXECUTION_ENABLED = False" in cfg and "CTRADER_EXECUTION_ENABLED = False" in cc
    src = open(os.path.join(_DE, "provider_route_authorisation.py"), encoding="utf-8").read()
    for bad in ("ProtoOA", "SerializeToString", "network_send", "make_permit", "make_lease"):
        assert bad not in src
    assert A(raw_text=FAROUK)["no_broker_action"] is True


# schedule: never assume closure from calendar; broker metadata authoritative; non-active blocks
def test_schedule_unknown_without_broker_metadata():
    state, reason = SS.market_state(now_ms=NOW, schedule=None, holidays=None)
    assert state == "SCHEDULE_UNKNOWN" and reason == "NO_BROKER_SCHEDULE"
    closed, st, _ = SS.market_closed_flag(now_ms=NOW, schedule=None)
    assert closed is False                                # unknown -> not fabricated as closed


def test_schedule_broker_holiday_closes():
    today = _time.strftime("%Y-%m-%d", _time.gmtime(NOW / 1000))
    closed, st, reason = SS.market_closed_flag(now_ms=NOW, holidays=[{"date": today, "name": "Independence Day", "is_open": False}])
    assert closed is True and st == "MARKET_CLOSED" and reason.startswith("BROKER_HOLIDAY")


def test_route_confirmed_sender_allowlist_empty():
    import provider_authorisation as PA
    assert PA.FAROUK_AUTHORISED_SENDER_IDS == ()          # personal identity NEVER allowlisted
    assert PRA.AUTHORISED_PROVIDER_ROUTES == ("sea-scalper-farouk",)   # exact route confirmed
    assert PRA.AUTHORISED_FORWARD_TRANSPORT_IDS == {-1001937743421}    # transport-only
    assert PRA.PROVIDER_AUTHORISATION_TYPE == "ROUTE_LEVEL"
    assert -1001937743421 not in PRA.AUTHORISED_PROVIDER_ROUTES        # transport never a route
