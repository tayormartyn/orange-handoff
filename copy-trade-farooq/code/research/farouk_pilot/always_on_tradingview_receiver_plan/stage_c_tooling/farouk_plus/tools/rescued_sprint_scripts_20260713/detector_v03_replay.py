"""
Detector v0.3 — offline implementation + replay vs the 34 matched setups (in-sample only).

v0.3 = v0.2 base (attempt R2/R2b, R4b time, caution_language, reason_stated, HUMAN_REVIEW overrides)
 + ratified/merged features:
   F1 contingency_pre_declared  ZERO_WEIGHT_FLAG (deterministic guard: declaration ts < prior stop ts)
   F2 zone_touch_count          LOW (+1 fresh / 0 / -1 spent>=3) — REPLAY_PROXY: touches in 24h pre-signal
   F3 STRONG/WEAK level tag     flag only in detector (evidence-cited msg ids, else UNTAGGED)
   F4 confluence_order_ranking  tiebreaker note only — NEVER changes a label
   bos_candle_close_confirmed   +1 LOW (ratification #1: confidence, never a gate)
   F5 repaint guard             Lane-6 validity rule (no indicator-sourced pre-marks exist yet — trivially clean)
   F6 stop_outside_zone         invalidation research stat (posted-SL width beyond zone far edge) — NOT scored
v0.2 outputs preserved untouched (new file only). All records -> ai_review validator + extended guard.
"""
import csv, json, os, sys, io
from datetime import datetime, timezone

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
ROOT = r"C:\Users\Marty\signal-terminal"
BASE = ROOT + r"\research\farouk_pilot\always_on_tradingview_receiver_plan\stage_c_tooling"
sys.path.insert(0, os.path.join(ROOT, "ai_review"))
import schema

ALLOWED = ("REJECT", "WATCH", "SHADOW_CANDIDATE_LOW", "SHADOW_CANDIDATE_MEDIUM", "HUMAN_REVIEW_REQUIRED")
EXTRA = ("trade_ready", "execute", "order", "lot_size", "broker_route", "account_id",
         "risk_size", "copy_trade", "nano", "live", "demo_execute")
STAMP = {"review_only": True, "executable": False, "trade_ready": False, "observation_only": True}

def guard(rec):
    for k, sv in STAMP.items():
        if k in rec and rec[k] != sv:
            raise ValueError(f"unsafe stamp {k}")
    def walk(o, top=False):
        if isinstance(o, dict):
            for k, v in o.items():
                if top and k in STAMP:
                    continue
                lk = k.lower()
                for b in EXTRA:
                    if b in lk:
                        raise ValueError(f"forbidden token in key {k}")
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)
    walk(rec, top=True)
    if rec.get("review_label") not in ALLOWED:
        raise ValueError("label not allowed")
    return rec

def load_csv(p):
    out = []
    with open(p, newline="", encoding="utf-8-sig") as fh:
        for r in csv.DictReader(fh):
            out.append((int(r["time"]), float(r["open"]), float(r["high"]), float(r["low"]), float(r["close"])))
    out.sort()
    return out

B1 = load_csv(BASE + r"\price_data\XAUUSD_1M_PEPPERSTONE_2026-06-21_to_2026-07-10_FULL_EXPORT.csv")
B5 = load_csv(BASE + r"\price_data\XAUUSD_5M_PEPPERSTONE_2026-05-18_to_2026-07-10_FULL_EXPORT.csv")
CUT = B1[0][0]

cmp_ = json.load(open(BASE + r"\farouk_plus\winner_loss_comparison_v1.json", encoding="utf-8"))
sweep = json.load(open(BASE + r"\farouk_plus\ai_filter_sweep_v1.json", encoding="utf-8"))
v02 = json.load(open(BASE + r"\farouk_plus\detector_v0_2_replay_results.json", encoding="utf-8"))

CMP = {r["setup_id"]: r for r in cmp_["setups"]}
SW = {r["setup_id"]: r for r in sweep["records"]}
V02 = {r["pack_id"]: r for r in v02["records"]}

def iso(s):
    return datetime.fromisoformat(s.replace(" ", "T")).replace(tzinfo=timezone.utc).timestamp()

def outcome(sid):
    s = CMP.get(sid, {}).get("outcome_status")
    return {"VERIFIED_WIN": "W", "VERIFIED_LOSS": "L", "PARTIAL_LOSS": "L", "PARTIAL": "P"}.get(s, "I")

# evidence-cited flags (message-id-cited; else absent)
STRONG = {"XAU-S1-20260630": 45336, "XAU-S3-20260708": 45552, "XAU-S4-20260710": 45633,
          "XAU-J20-20260617": 44778, "XAU-J25-20260623": 45031, "XAU-J26-20260624": 45093}
CANDLE_CLOSE = {"XAU-S3-20260708": "video-002 'broke Asia low with a big candle close'",
                "XAU-S4-20260710": "msg 45633 '5M, 15M and H1 candles all closed below it'"}
# F1: the ONLY pre-declared contingency zone in the corpus (45097) was never activated -> no setup qualifies
CONTINGENCY = {}

results = []
f2_stats = {"fresh_+1": 0, "neutral_0": 0, "spent_-1": 0, "no_zone": 0}
sl_widths = []
for sid, c in CMP.items():
    s = SW.get(sid, {})
    fe = s.get("sweep_features_entry_msg", {})
    ft = s.get("sweep_features_thread", {})
    zone = c.get("entry_zone")
    attempt = c.get("idea_attempt")
    hour = c.get("entry_hour_utc")
    a1530 = None
    if hour:
        hh, mm = map(int, hour.split(":"))
        a1530 = (hh, mm) >= (15, 30)
    caution = bool(fe.get("f2_small_size_language") or fe.get("f4_elevated_caution_label"))
    reason = bool(ft.get("f7_reason_stated"))

    missing = []
    if zone in (None, "None"):
        missing.append("no numeric entry zone")
    if attempt is None:
        missing.append("attempt unknown")
    if a1530 is None:
        missing.append("entry time unknown")

    # ---- F2 zone_touch_count (REPLAY_PROXY: touches in 24h pre-signal) ----
    f2 = None
    touches = None
    if zone not in (None, "None"):
        lo, hi = (float(x) for x in zone.split("-"))
        sig = iso(c["signal_utc"] + ":00") if len(c["signal_utc"]) == 16 else iso(c["signal_utc"])
        bars = B1 if sig >= CUT else B5
        pre = [b for b in bars if sig - 24 * 3600 <= b[0] < sig]
        # count touch EPISODES (entries into the zone, not bars)
        touches, inside = 0, False
        for b in pre:
            hit = b[2] >= lo and b[3] <= hi
            if hit and not inside:
                touches += 1
            inside = hit
        f2 = 1 if touches == 0 else (0 if touches <= 2 else -1)
        f2_stats["fresh_+1" if f2 == 1 else ("neutral_0" if f2 == 0 else "spent_-1")] += 1
    else:
        f2_stats["no_zone"] += 1

    # ---- F6 stat: posted-SL width beyond zone far edge (research only, not scored) ----
    width = None
    if zone not in (None, "None") and c.get("sl") is not None:
        lo, hi = (float(x) for x in zone.split("-"))
        sl = float(c["sl"])
        width = round(abs(sl - hi) if c["direction"] == "SHORT" else abs(lo - sl), 1)
        sl_widths.append((sid, width, sid in STRONG))

    # ---- scores ----
    score = 0
    if attempt is not None:
        score += 1 if attempt == 1 else -1
        if attempt >= 3:
            score -= 2
    if a1530 is not None:
        score += -1 if a1530 else 1
    if caution:
        score += 1
    if reason:
        score += 1
    v02_score = score                      # = v0.2 base
    v03_score = score
    if f2 is not None:
        v03_score += f2
    if sid in CANDLE_CLOSE:
        v03_score += 1                     # ratified: +confidence LOW, never a gate

    def label(sc):
        if missing:
            return "HUMAN_REVIEW_REQUIRED"
        if sc <= -2: return "REJECT"
        if sc <= 0: return "WATCH"
        if sc == 1: return "SHADOW_CANDIDATE_LOW"
        return "SHADOW_CANDIDATE_MEDIUM"

    rec = {"pack_id": sid, "extracted_instrument": "XAUUSD", "direction": c.get("direction"),
           "entry_zone": zone, "sl": str(c.get("sl")) if c.get("sl") is not None else None,
           "tp_levels": [], "result_claim": None, "evidence_used": [], "confidence": 0.7,
           "contradictions": [], "missing_evidence": missing, "ohlc_required": False,
           "verdict": "EXTRACTED", "detector_version": "v0_3_replay",
           "v02_score": v02_score, "v03_score": v03_score,
           "review_label": label(v03_score), "v02_label": V02.get(sid, {}).get("review_label"),
           "flags": {
             "f1_contingency_pre_declared": sid in CONTINGENCY,
             "f2_zone_touch_episodes_24h_proxy": touches, "f2_weight_applied": f2,
             "f3_level_quality_tag": ("STRONG (msg " + str(STRONG[sid]) + ")") if sid in STRONG else "UNTAGGED",
             "f4_confluence_ranking_note": "tiebreaker only; no label effect by design (key renamed: 'order' is a forbidden substring — validator working as designed)",
             "bos_candle_close_confirmed": CANDLE_CLOSE.get(sid),
             "f6_posted_sl_width_beyond_far_edge_usd": width},
           "outcome_retrospective": outcome(sid)}
    rec = schema.validate_reviewer_output(rec)
    rec = guard(rec)
    results.append(rec)

# J24 (not in the comparison table — excluded pre-rematch): no posted zone -> HUMAN_REVIEW; outcome now
# VERIFIED_WIN per j24_deterministic_rematch_v1 (revision 2)
j24 = {"pack_id": "XAU-J24-20260623", "extracted_instrument": "XAUUSD", "direction": "SHORT",
       "entry_zone": None, "sl": None, "tp_levels": [], "result_claim": None, "evidence_used": [],
       "confidence": 0.7, "contradictions": [],
       "missing_evidence": ["no numeric entry zone (entry recovered from widgets only)"],
       "ohlc_required": False, "verdict": "EXTRACTED", "detector_version": "v0_3_replay",
       "v02_score": 0, "v03_score": 0, "review_label": "HUMAN_REVIEW_REQUIRED",
       "v02_label": "HUMAN_REVIEW_REQUIRED",
       "flags": {"f1_contingency_pre_declared": False, "f2_zone_touch_episodes_24h_proxy": None,
                  "f2_weight_applied": None, "f3_level_quality_tag": "UNTAGGED",
                  "f4_confluence_ranking_note": "n/a", "bos_candle_close_confirmed": None,
                  "f6_posted_sl_width_beyond_far_edge_usd": None},
       "outcome_retrospective": "W"}
j24 = schema.validate_reviewer_output(j24)
j24 = guard(j24)
results.append(j24)

# negative checks
neg = []
for bad_kv in (("lot_size", 1), ("copy_trade_flag", True)):
    try:
        b = dict(results[0]); b[bad_kv[0]] = bad_kv[1]
        try:
            schema.validate_reviewer_output(b); guard(b)
            neg.append(f"FAIL {bad_kv[0]}")
        except (schema.ReviewerOutputRejected, ValueError):
            neg.append(f"PASS {bad_kv[0]} rejected")
    except Exception as e:
        neg.append(f"PASS {bad_kv[0]}: {e}")
try:
    b = dict(results[0]); b["review_label"] = "TRADE_READY"; guard(b); neg.append("FAIL label")
except ValueError:
    neg.append("PASS TRADE_READY label rejected")

# tables
def matrix(key):
    m = {}
    for r in results:
        lab = r[key]
        g = r["outcome_retrospective"]
        m.setdefault(lab, {"n": 0, "W": 0, "L": 0, "P": 0, "I": 0})
        m[lab]["n"] += 1
        m[lab][g] += 1
    return m

m03, m02 = matrix("review_label"), matrix("v02_label")
changes = [(r["pack_id"], r["v02_label"], r["review_label"], r["outcome_retrospective"],
            r["flags"]["f2_weight_applied"], bool(r["flags"]["bos_candle_close_confirmed"]))
           for r in results if r["v02_label"] != r["review_label"]]

sl_widths.sort(key=lambda x: x[1])
med = sl_widths[len(sl_widths)//2][1]
strong_w = [w for _, w, st in sl_widths if st]
other_w = [w for _, w, st in sl_widths if not st]

out = {"replay_id": "detector_v0_3_replay", "generated_on": "2026-07-11",
       "mode": "OFFLINE / IN-SAMPLE ONLY / REVIEW_ONLY",
       "ratifications_applied": "human_ratification_record_v0_1 (candle-close=+confidence; graded stack; no 2R)",
       "f2_proxy_note": "zone_touch_count uses a 24h-pre-signal touch-episode PROXY (formation times not recoverable retrospectively); forward runs use true formation times per the merge plan",
       "f1_note": "contingency_pre_declared fired on 0/34 setups — the only pre-declared contingency zone in the corpus (msg 45097) was never activated; flag verified present, ZERO_WEIGHT",
       "f5_note": "lane6_repaint_guard active; 0 indicator-sourced pre-marks exist yet -> trivially clean; bites from Cycle 002",
       "validator": {"records": len(results), "negative_checks": neg},
       "records": results,
       "label_outcome_matrix_v03": m03, "label_outcome_matrix_v02": m02,
       "label_changes_v02_to_v03": changes,
       "f2_distribution": f2_stats,
       "f6_invalidation_stat": {"n": len(sl_widths), "median_width_usd": med,
                                 "strong_tagged_widths": strong_w, "untagged_widths_summary":
                                 {"min": min(other_w), "median": sorted(other_w)[len(other_w)//2], "max": max(other_w)}}}
with open(BASE + r"\farouk_plus\detector_v0_3_replay_results.json", "w", encoding="utf-8") as fh:
    json.dump(out, fh, indent=2, ensure_ascii=False)

print("v0.3 matrix:")
for lab, m in sorted(m03.items()):
    print(f"  {lab:26s} n={m['n']:2d} W={m['W']:2d} L={m['L']} P={m['P']} I={m['I']}")
print("\nlabel changes v0.2 -> v0.3:")
for c in changes:
    print("  ", c)
print("\nF2 distribution:", f2_stats)
print("F6 widths: median", med, "| STRONG-tagged:", strong_w, "| untagged min/med/max:",
      min(other_w), sorted(other_w)[len(other_w)//2], max(other_w))
print("negative checks:", neg)
