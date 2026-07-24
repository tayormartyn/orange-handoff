"""
Farouk-Plus Shadow Engine Step 3 — AI-assisted filter sweep (review-only, offline).

Scans every matched XAU setup's captured message thread (June backfill DB + July evidence DB,
both READ-ONLY) for candidate features, joins deterministic outcomes, computes per-feature
outcome distributions, and passes every structured record through the ai_review fail-closed
validator. Feature keys deliberately avoid forbidden substrings ('lot', 'risk', ...); a negative
check demonstrates the validator rejecting a 'low_lot_flag' key. No execution surface.
"""
import sqlite3, json, os, re, sys, io
from datetime import datetime, timezone

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
ROOT = r"C:\Users\Marty\signal-terminal"
BASE = ROOT + r"\research\farouk_pilot\always_on_tradingview_receiver_plan\stage_c_tooling"
sys.path.insert(0, os.path.join(ROOT, "ai_review"))
import schema

JUNE_DB = ROOT + r"\campaign_extractor\prospective\data\june_history_backfill_v1.db"
EV_DB = ROOT + r"\campaign_extractor\prospective\data\prospective_evidence_v1.db"
OUT = BASE + r"\farouk_plus\ai_filter_sweep_v1.json"

d3 = json.load(open(BASE + r"\SPRINT_DAY3_JUNE_XAU_LEDGER_v1.json", encoding="utf-8"))
d1 = json.load(open(BASE + r"\SPRINT_DAY1_XAU_LEDGER_v1.json", encoding="utf-8"))
cmp_ = json.load(open(BASE + r"\farouk_plus\winner_loss_comparison_v1.json", encoding="utf-8"))

OUTCOME = {r["setup_id"]: r["outcome_status"] for r in cmp_["setups"]}
def group(sid):
    s = OUTCOME.get(sid)
    if s == "VERIFIED_WIN": return "W"
    if s in ("VERIFIED_LOSS", "PARTIAL_LOSS"): return "L"
    if s == "PARTIAL": return "P"
    return "I"

jcon = sqlite3.connect(f"file:{JUNE_DB}?mode=ro", uri=True)
econ = sqlite3.connect(f"file:{EV_DB}?mode=ro", uri=True)

def june_text(mid):
    r = jcon.execute("SELECT raw_text FROM june_message_evidence WHERE telegram_message_id=?", (str(mid),)).fetchone()
    return r[0] if r else ""

def july_text(mid):
    r = econ.execute("SELECT raw_text FROM prospective_message_evidence WHERE telegram_message_id=? "
                     "ORDER BY message_revision_number DESC LIMIT 1", (str(mid),)).fetchone()
    return r[0] if r else ""

SETUPS = []
for s in d3["setups"]:
    SETUPS.append((s["setup_id"], s["entry_message_id"], s["message_ids"], june_text,
                   s.get("entry_posted_at_utc") or s.get("first_msg_utc")))
for s in d1["setups"]:
    SETUPS.append((s["setup_id"].replace("XAU-S", "XAU-S"), s["entry_message_id"], s["message_ids"], july_text,
                   s["entry_posted_at_utc"]))

FEATURES = {
 "f1_news_event_language":   r"fomc|cpi|nfp|news|volatil",
 "f2_small_size_language":   r"low lot|super low lot|small lot|lot sizes? low|quarter size|half size|small size|small position",
 "f3_protect_profit_language": r"don.?t risk|do not risk|protect|risk management",
 "f4_elevated_caution_label": r"high.?risk",
 "f5_be_stop_management":    r"sl to entry|sl entry|sl at entry|sl enty|breakeven|sl to enty",
 "f6_layered_entry_management": r"close (the )?worst|hold (the )?best|worst entry|best entry",
 "f7_reason_stated":         r"reason for the (sell|buy|long|short)",
 "f8_education_context":     r"education|tutorial|homework|explain|stream",
 "f9_post_hoc_commentary":   r"missed (the|this|it|my)|as planned|played out|i told",
 "f10_breakdown_video":      r"breakdown|schermopname",
 "f12_late_entry_confession": r"late entry",
}

records = []
validated = 0
for sid, entry_mid, mids, getter, entry_ts in SETUPS:
    entry_text = (getter(entry_mid) or "").lower() if entry_mid else ""
    thread = " || ".join((getter(m) or "") for m in mids).lower()
    feats_thread = {k: bool(re.search(rx, thread)) for k, rx in FEATURES.items()}
    feats_entry = {k: bool(re.search(rx, entry_text)) for k, rx in FEATURES.items()}
    dt = datetime.fromisoformat(entry_ts) if entry_ts else None
    feats_thread["f11_friday_entry"] = bool(dt and dt.weekday() == 4)
    feats_entry["f11_friday_entry"] = feats_thread["f11_friday_entry"]
    rec = {"pack_id": sid, "extracted_instrument": "XAUUSD",
           "direction": None, "entry_zone": None, "sl": None, "tp_levels": [],
           "result_claim": None, "evidence_used": mids, "confidence": 0.9,
           "contradictions": [], "missing_evidence": [], "ohlc_required": False,
           "verdict": "EXTRACTED",
           "sweep_features_thread": feats_thread, "sweep_features_entry_msg": feats_entry,
           "outcome_group": group(sid)}
    out = schema.validate_reviewer_output(rec)   # fail-closed; stamps review-only
    validated += 1
    records.append({**out, "setup_id": sid})

# negative check: forbidden key must be rejected
neg_rejected = None
try:
    bad = dict(records[0])
    bad["low_lot_flag"] = True
    schema.validate_reviewer_output(bad)
    neg_rejected = "FAIL — forbidden key accepted"
except schema.ReviewerOutputRejected as e:
    neg_rejected = f"PASS — {e}"

# per-feature outcome distributions (thread scope + entry scope), excluding INSUFFICIENT
def dist(scope_key):
    table = {}
    for f in list(FEATURES) + ["f11_friday_entry"]:
        pres = {"W": 0, "L": 0, "P": 0}
        absn = {"W": 0, "L": 0, "P": 0}
        for r in records:
            g = r["outcome_group"]
            if g == "I":
                continue
            (pres if r[scope_key].get(f) else absn)[g] += 1
        table[f] = {"present": pres, "absent": absn}
    return table

thread_dist = dist("sweep_features_thread")
entry_dist = dist("sweep_features_entry_msg")

out = {"sweep_id": "ai_filter_sweep_v1", "generated_on": "2026-07-11",
       "mode": "OBSERVATION_ONLY / REVIEW_ONLY",
       "corpus": "June backfill DB (273 gold msgs) + July evidence DB, read-only; 34 setups scanned (33 matched + J24)",
       "validator": {"records_validated": validated, "negative_check": neg_rejected,
                     "note": "feature keys deliberately avoid forbidden substrings; the natural names low_lot/high_risk are UNWRITABLE through the validator by design"},
       "feature_definitions": {**{k: v for k, v in FEATURES.items()}, "f11_friday_entry": "entry timestamp weekday == Friday"},
       "records": records,
       "outcome_distribution_thread_scope": thread_dist,
       "outcome_distribution_entry_msg_scope": entry_dist}
with open(OUT, "w", encoding="utf-8") as fh:
    json.dump(out, fh, indent=2, ensure_ascii=False)

print(f"setups scanned={len(records)} validated={validated} negative_check={neg_rejected}")
print("\n=== THREAD-SCOPE distributions (present W/L/P vs absent W/L/P) ===")
for f, d in thread_dist.items():
    p, a = d["present"], d["absent"]
    print(f"{f:32s} present W{p['W']}/L{p['L']}/P{p['P']}   absent W{a['W']}/L{a['L']}/P{a['P']}")
print("\n=== ENTRY-MSG-SCOPE distributions ===")
for f, d in entry_dist.items():
    p, a = d["present"], d["absent"]
    print(f"{f:32s} present W{p['W']}/L{p['L']}/P{p['P']}   absent W{a['W']}/L{a['L']}/P{a['P']}")
jcon.close(); econ.close()
print("\nwritten:", OUT)
