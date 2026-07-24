"""
Farouk-Plus Shadow Engine Step 4 — detector v0.2 REPLAY (review-only, offline).

Scores every captured June+July XAU setup with ruleset v0.1 + Step-3 adopted features using ONLY
entry-time-knowable inputs. Emits ONLY the five allowed review labels. Every record passes the
ai_review fail-closed validator PLUS an extended forbidden-token guard (copy_trade/nano/live/
demo_execute added). Outcome comparison uses the deterministic matchers (authority). No execution.
"""
import json, os, sys, io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
ROOT = r"C:\Users\Marty\signal-terminal"
BASE = ROOT + r"\research\farouk_pilot\always_on_tradingview_receiver_plan\stage_c_tooling"
sys.path.insert(0, os.path.join(ROOT, "ai_review"))
import schema

cmp_ = json.load(open(BASE + r"\farouk_plus\winner_loss_comparison_v1.json", encoding="utf-8"))
sweep = json.load(open(BASE + r"\farouk_plus\ai_filter_sweep_v1.json", encoding="utf-8"))
OUT = BASE + r"\farouk_plus\detector_v0_2_replay_results.json"

ALLOWED_LABELS = ("REJECT", "WATCH", "SHADOW_CANDIDATE_LOW", "SHADOW_CANDIDATE_MEDIUM", "HUMAN_REVIEW_REQUIRED")
EXTRA_FORBIDDEN = ("trade_ready", "execute", "order", "lot_size", "broker_route", "account_id",
                   "risk_size", "copy_trade", "nano", "live", "demo_execute")

# the ai_review validator ITSELF stamps these keys with safe values on every accepted record;
# they are the safety mechanism, exempt at top level ONLY and only with the safe values
STAMP_EXEMPT = {"review_only": True, "executable": False, "trade_ready": False, "observation_only": True}

def extended_guard(rec):
    """Local guard on top of ai_review: extended forbidden tokens in ANY nested key (except the
    validator's own top-level safety stamp, whose values are asserted safe); label whitelist."""
    for k, safe_val in STAMP_EXEMPT.items():
        if k in rec and rec[k] != safe_val:
            raise ValueError(f"safety stamp '{k}' has unsafe value {rec[k]!r}")
    def walk(o, path="", top=False):
        if isinstance(o, dict):
            for k, v in o.items():
                if top and k in STAMP_EXEMPT:
                    continue
                kp = f"{path}.{k}" if path else str(k)
                leaf = k.lower()
                for bad in EXTRA_FORBIDDEN:
                    if bad in leaf:
                        raise ValueError(f"extended forbidden token in key: '{kp}'")
                walk(v, kp)
        elif isinstance(o, list):
            for i, v in enumerate(o):
                walk(v, f"{path}[{i}]")
    walk(rec, top=True)
    if rec.get("review_label") not in ALLOWED_LABELS:
        raise ValueError(f"label '{rec.get('review_label')}' not in allowed set")
    return rec

CMP = {r["setup_id"]: r for r in cmp_["setups"]}
SWEEP = {r["setup_id"]: r for r in sweep["records"]}

def outcome_group(sid):
    s = CMP.get(sid, {}).get("outcome_status")
    if s == "VERIFIED_WIN": return "W"
    if s in ("VERIFIED_LOSS", "PARTIAL_LOSS"): return "L"
    if s == "PARTIAL": return "P"
    return "I"

def after_1530(r):
    h = r.get("entry_hour_utc") or (r.get("signal_utc", "")[-5:] if r.get("signal_utc") else None)
    if not h or ":" not in h:
        return None
    hh, mm = map(int, h.split(":"))
    return (hh, mm) >= (15, 30)

results = []
validated = 0
for sid in sorted(set(list(CMP) + list(SWEEP))):
    c = CMP.get(sid, {})
    s = SWEEP.get(sid, {})
    feats_entry = s.get("sweep_features_entry_msg", {})
    feats_thread = s.get("sweep_features_thread", {})

    attempt = c.get("idea_attempt")
    a1530 = after_1530(c) if c else None
    caution = bool(feats_entry.get("f2_small_size_language") or feats_entry.get("f4_elevated_caution_label"))
    reason = bool(feats_thread.get("f7_reason_stated"))   # applied on arrival (minutes after entry)

    missing = []
    if not c or c.get("entry_zone") in (None, "None"):
        missing.append("no numeric entry zone")
    if attempt is None:
        missing.append("attempt number unknown")
    if a1530 is None:
        missing.append("entry time unknown")

    score = 0
    flags = {"first_attempt_flag": None, "re_entry_flag": None, "attempt_ge_3": None,
             "after_1530z_flag": a1530, "caution_language": caution, "reason_stated_on_arrival": reason,
             "be_stop_language_EXCLUDED_outcome_side": True, "mae_feature_EXCLUDED_outcome_side": True,
             "claim_quality_R6": "retrospective-only in this replay (no prior inflation history at most entries)"}
    if attempt is not None:
        flags["first_attempt_flag"] = attempt == 1
        flags["re_entry_flag"] = attempt >= 2
        flags["attempt_ge_3"] = attempt >= 3
        score += 1 if attempt == 1 else -1
        if attempt >= 3:
            score -= 2
    if a1530 is not None:
        score += -1 if a1530 else 1
    if caution:
        score += 1
    if reason:
        score += 1

    if missing:
        label = "HUMAN_REVIEW_REQUIRED"
    elif score <= -2:
        label = "REJECT"
    elif score <= 0:
        label = "WATCH"
    elif score == 1:
        label = "SHADOW_CANDIDATE_LOW"
    else:
        label = "SHADOW_CANDIDATE_MEDIUM"

    rec = {"pack_id": sid, "extracted_instrument": "XAUUSD", "direction": c.get("direction"),
           "entry_zone": c.get("entry_zone"), "sl": str(c.get("sl")) if c.get("sl") is not None else None,
           "tp_levels": [], "result_claim": None,
           "evidence_used": [], "confidence": 0.7, "contradictions": [],
           "missing_evidence": missing, "ohlc_required": False, "verdict": "EXTRACTED",
           "detector_version": "v0_2_replay", "score": score, "flags": flags,
           "review_label": label, "outcome_group_retrospective": outcome_group(sid)}
    rec = schema.validate_reviewer_output(rec)  # fail-closed + review-only stamp
    rec = extended_guard(rec)
    validated += 1
    results.append(rec)

# negative checks
neg = []
try:
    bad = dict(results[0]); bad["copy_trade_flag"] = True
    extended_guard(bad); neg.append("FAIL copy_trade accepted")
except ValueError as e:
    neg.append(f"PASS extended guard: {e}")
try:
    bad2 = dict(results[0]); bad2["review_label"] = "TRADE_READY"
    extended_guard(bad2); neg.append("FAIL label accepted")
except ValueError as e:
    neg.append(f"PASS label whitelist: {e}")
try:
    bad3 = dict(results[0]); bad3["lot_size"] = 0.5
    schema.validate_reviewer_output(bad3); neg.append("FAIL ai_review accepted lot_size")
except schema.ReviewerOutputRejected as e:
    neg.append(f"PASS ai_review: {e}")
try:
    bad4 = dict(results[0]); bad4["trade_ready"] = True
    extended_guard(bad4); neg.append("FAIL trade_ready=True accepted")
except ValueError as e:
    neg.append(f"PASS stamp-value guard: {e}")

# label x outcome matrix
matrix = {}
for r in results:
    lab = r["review_label"]
    g = r["outcome_group_retrospective"]
    matrix.setdefault(lab, {"n": 0, "W": 0, "L": 0, "P": 0, "I": 0})
    matrix[lab]["n"] += 1
    matrix[lab][g] += 1

promoted = [r for r in results if r["review_label"] in ("SHADOW_CANDIDATE_LOW", "SHADOW_CANDIDATE_MEDIUM")]
prom_w = sum(1 for r in promoted if r["outcome_group_retrospective"] == "W")
prom_l = [r["pack_id"] for r in promoted if r["outcome_group_retrospective"] == "L"]
rej = [r for r in results if r["review_label"] == "REJECT"]
rej_w = [r["pack_id"] for r in rej if r["outcome_group_retrospective"] == "W"]
rej_l = [r["pack_id"] for r in rej if r["outcome_group_retrospective"] == "L"]
watch_l = [r["pack_id"] for r in results if r["review_label"] == "WATCH" and r["outcome_group_retrospective"] == "L"]

out = {"replay_id": "detector_v0_2_replay", "generated_on": "2026-07-11",
       "mode": "OBSERVATION_ONLY / REVIEW_ONLY / OFFLINE_REPLAY",
       "scoring_inputs": "attempt number (R2/R2b), after-15:30Z (R4b), caution_language (f2∪f4, entry msg), reason_stated (f7, on arrival). EXCLUDED from scoring: BE-stop language, MAE (outcome-side); R6 claim-quality retrospective-only.",
       "allowed_labels": list(ALLOWED_LABELS),
       "forbidden_tokens_enforced": list(EXTRA_FORBIDDEN),
       "validator": {"records_validated": validated, "negative_checks": neg},
       "records": results,
       "label_outcome_matrix": matrix,
       "headline": {
           "promoted_candidates": {"n": len(promoted), "wins": prom_w, "losses": prom_l},
           "reject_bucket": {"n": len(rej), "winners_wrongly_rejected": rej_w, "losses_correctly_rejected": rej_l},
           "losses_left_in_watch": watch_l}}
with open(OUT, "w", encoding="utf-8") as fh:
    json.dump(out, fh, indent=2, ensure_ascii=False)

print(f"replayed={len(results)} validated={validated}")
for n in neg:
    print(" ", n)
print("\nlabel x outcome matrix:")
for lab, m in sorted(matrix.items()):
    print(f"  {lab:26s} n={m['n']:2d}  W={m['W']:2d} L={m['L']} P={m['P']} I={m['I']}")
print("\npromoted:", len(promoted), "wins:", prom_w, "losses promoted:", prom_l)
print("REJECT bucket:", [r['pack_id'] for r in rej], "| winners wrongly rejected:", rej_w, "| losses rejected:", rej_l)
print("losses left in WATCH:", watch_l)
print("written:", OUT)
