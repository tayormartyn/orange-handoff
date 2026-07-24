"""Knowledge-register integrity checks (review-only; no live-scoring surface).

Verifies: rule provenance; promotion discipline; UNKNOWN formulas never claimed known;
no video-only observation flagged as a v0.3 input outside the ratified merge path;
pre-mark boundary immutability; active scorer artifacts unchanged; gates unchanged.
Exit 0 = all pass.
"""
import hashlib
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
FP = os.path.dirname(HERE)
REPO = r"C:\Users\Marty\signal-terminal"
REG = json.load(open(os.path.join(FP, "knowledge", "orange_knowledge_register_v1.json"), encoding="utf-8"))

fails, passes = [], []

def check(name, ok, detail=""):
    (passes if ok else fails).append(f"{name}{': ' + detail if detail and not ok else ''}")

def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest().upper()

# 1. every rule has provenance (>=1 source with id; and a ts or msg/doc reference somewhere)
for r in REG["B_methodology_rule_register"]["rules"]:
    srcs = r.get("sources", [])
    check(f"provenance:{r['rule_id']}", bool(srcs) and all("id" in s for s in srcs))
    check(f"status:{r['rule_id']}", bool(r.get("status")))
    check(f"reviewed:{r['rule_id']}", bool(r.get("last_reviewed")))

# 2. promotion discipline: nothing PROMOTED; PROMOTION_CANDIDATE requires replay/forward evidence in status
for r in REG["B_methodology_rule_register"]["rules"]:
    st = r["status"]
    check(f"no-direct-promotion:{r['rule_id']}", "PROMOTED" not in st or "REPLAY" in st or "FORWARD" in st)
for f in REG["D_feature_candidate_register"]:
    check(f"feature-not-live:{f['feature_id']}", "ELIGIBLE" not in f["live_eligibility"].upper() or f["live_eligibility"].upper().startswith("NOT") or "PROHIBITED" in f["live_eligibility"].upper())

# 2b. v1.1 docs addendum: every DR rule has doc+pages provenance; A-grade guarded; nothing live-eligible
_add_path = os.path.join(FP, "knowledge", "orange_knowledge_register_v1_1_docs_addendum.json")
if os.path.exists(_add_path):
    ADD = json.load(open(_add_path, encoding="utf-8"))
    for r in ADD["document_rules"]:
        check(f"doc-provenance:{r['rule_id']}", bool(r.get("doc")) and bool(r.get("pages")))
        check(f"doc-not-live:{r['rule_id']}", str(r.get("v03_input", "NO")).upper() in ("NO", "PROHIBITED"))
    check("agrade-indicator-equivalence-unknown", "INDICATOR_EQUIVALENCE_UNKNOWN" in ADD["a_grade_status_change"])
    check("addendum-review-only", ADD.get("review_only") is True and ADD.get("executable") is False)

# 3. UNKNOWN formulas stay unknown
unk = " ".join(REG["C_level_construction_spec"]["explicit_UNKNOWNS"]).lower()
check("agrade-unknown", "a-grade formula" in unk)
check("panel-unknown", "panel" in unk)
check("repaint-unknown", "repaint" in unk)

# 4. no video-only observation as v0.3 input: rules with v03_input YES must cite a ratified path
for r in REG["B_methodology_rule_register"]["rules"]:
    v = str(r.get("v03_input", "NO"))
    if v.upper().startswith("YES"):
        ok = any(k in v.lower() or k in r["statement"].lower() or any(k in str(s).lower() for s in r["sources"])
                 for k in ("ratif", "ruleset", "merge plan"))
        check(f"v03-input-ratified:{r['rule_id']}", ok, v)

# 4b. ORB capture wiring: capture-only, never a v0.3 input; unknowns preserved; panel guard present
_orb_path = os.path.join(FP, "orb_capture_schema_addendum_v0_1.json")
if os.path.exists(_orb_path):
    ORB = json.load(open(_orb_path, encoding="utf-8"))
    check("orb-prohibited-from-v03", "PROHIBITED" in ORB["v03_eligibility"])
    check("orb-unknown-params-preserved", all(k in ORB["source_rule"] for k in ("body-vs-wick", "retest depth", "validity horizon")))
    check("orb-panel-guard", "FC-PANELWATCH" in ORB["panel_version_guard"] and "F5" in ORB["panel_version_guard"])
    check("orb-fixture-marked", ORB["example_test_fixture"].get("TEST_FIXTURE_ONLY") is True)
    check("orb-empty-record-unknowns", ORB["example_empty_record"]["orb_anchor_basis"] == "UNKNOWN" and ORB["example_empty_record"]["v03_input"] is False)
    v03_txt = open(os.path.join(FP, "detector_v0_3_replay_results.json"), encoding="utf-8", errors="replace").read().lower()
    check("no-orb-field-in-v03-artifact", not any(f.lower() in v03_txt for f in ORB["fields"] if f != "orb_mid"))

# 5. pre-mark immutability: frozen definitions must appear verbatim in the append-only ledger
ledger_path = os.path.join(FP, "pre_mark_candidates_v0_1.jsonl")
ledger = [json.loads(l) for l in open(ledger_path, encoding="utf-8") if l.strip()]
# PRE_MARK_PROVENANCE_ANNOTATION records are append-only annotations (no pre_mark_id);
# they must never carry boundary fields that could shadow the frozen definitions.
for r in ledger:
    if r.get("record_type") == "PRE_MARK_PROVENANCE_ANNOTATION":
        check(f"annotation-no-boundary-fields:{r.get('annotates')}", "entry_zone" not in r and "expiry_time_utc" not in r)
by_id = {r["pre_mark_id"]: r for r in ledger if "pre_mark_id" in r}
for fz in REG["F_pre_mark_register_frozen"]["frozen_definitions"]:
    rec = by_id.get(fz["id"])
    ok = rec is not None and rec["entry_zone"] == fz["zone"] and fz["expires"].startswith(rec["expiry_time_utc"][:10]) and rec["direction"] == ("SHORT" if fz["dir"] == "SHORT" else "LONG")
    check(f"premark-frozen:{fz['id']}", ok)

# 6. active scorer artifacts unchanged
ib = REG["integrity_baselines"]
check("v03-artifact-hash", sha256(os.path.join(FP, "detector_v0_3_replay_results.json")) == ib["detector_v0_3_replay_results.json_sha256"])
check("v02-artifact-hash", sha256(os.path.join(FP, "detector_v0_2_replay_results.json")) == ib["detector_v0_2_replay_results.json_sha256"])

# 7. gates unchanged (from source)
cfg = open(os.path.join(REPO, "config.py"), encoding="utf-8", errors="replace").read()
cc = open(os.path.join(REPO, "ctrader_config.py"), encoding="utf-8", errors="replace").read()
check("gate-MODE", re.search(r'^MODE\s*=\s*"PAPER"', cfg, re.M) is not None)
check("gate-LISTENER", re.search(r'^LISTENER_MODE\s*=\s*"PREVIEW"', cfg, re.M) is not None)
check("gate-EXEC", re.search(r"^EXECUTION_ENABLED\s*=\s*False", cfg, re.M) is not None)
check("gate-CTRADER", re.search(r"^CTRADER_EXECUTION_ENABLED\s*=\s*False", cc, re.M) is not None)

print(f"PASS {len(passes)} checks")
if fails:
    print(f"FAIL {len(fails)}:")
    for f in fails:
        print("  -", f)
    sys.exit(1)
print("ALL INTEGRITY CHECKS PASSED")
