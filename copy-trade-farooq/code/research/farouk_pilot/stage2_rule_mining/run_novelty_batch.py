"""Batch novelty gating for the DEDUPLICATED canonical rule set (reviewer order:
dedup FIRST, then gate the deduplicated set against the pre-existing claim register).
Writes novelty_verdicts_v0_1.json keyed by rule_id. Read-only against the brain."""
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ST = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
GATE = os.path.join(ST, r"research\farouk_pilot\orange_brain\novelty_gate.py")
DRAFT = os.path.join(HERE, "canonical_rules_draft_v0_1.json")
OUT = os.path.join(HERE, "novelty_verdicts_v0_1.json")

rules = json.load(open(DRAFT, encoding="utf-8"))
env = dict(os.environ, PYTHONIOENCODING="utf-8")
verdicts = {}
for i, r in enumerate(rules, 1):
    p = subprocess.run([sys.executable, GATE, "--claim", r["statement"]],
                       capture_output=True, text=True, encoding="utf-8", env=env)
    out = p.stdout
    try:
        j = json.loads(out[out.index("{"):])
        verdicts[r["rule_id"]] = {"verdict": j.get("classification", "GATE_ERROR"),
                                  "reason": (j.get("reason") or "")[:200]}
    except Exception as e:
        verdicts[r["rule_id"]] = {"verdict": "GATE_ERROR", "reason": f"{type(e).__name__}: {out[-120:]}"}
    if i % 10 == 0:
        print(f"{i}/{len(rules)} gated")
json.dump(verdicts, open(OUT, "w", encoding="utf-8"), indent=1)
from collections import Counter
print("verdict counts:", dict(Counter(v["verdict"] for v in verdicts.values())))
print("wrote", OUT)
