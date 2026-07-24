"""PROOF (D-080): the old operator-brief contradiction can no longer render, and a
deliberately stale literal claiming recency is rejected by the general consistency guard."""
import importlib.util, os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("br", os.path.join(HERE, "brain_refresh.py"))
br = importlib.util.module_from_spec(spec)
spec.loader.exec_module(br)

_p = _f = 0
def check(name, cond):
    global _p, _f
    print(("  ok  " if cond else "FAIL  ") + name)
    _p += bool(cond); _f += (not cond)

# 1. the REAL brief renders and is DERIVED (no frozen F005 literal; both numbers present)
out = subprocess.run([sys.executable, os.path.join(HERE, "brain_refresh.py"), "--status"],
                     capture_output=True, text=True, encoding="utf-8", errors="replace").stdout
check("real brief renders", "OPERATOR BRIEF" in out)
check("item3 DERIVES latest = F007 (no 'since F005' literal)",
      "XAU-F007-20260721" in out and "No new campaign since F005" not in out)
check("item4 renders BOTH numbers", "genuine prospective captures" in out and "expectancy rows" in out)
check("item4 names F006 exclusion + reason", "F006" in out and "PARTIAL_INSTRUCTION_SILENT_LOSS" in out)

# 2. a deliberately stale LITERAL claiming recency -> guard REJECTS
try:
    br.consistency_guard([{"id": "item3", "kind": "LITERAL",
                           "text": "No new campaign since F005 (2026-07-17).", "asserts": {}}])
    check("stale literal claiming recency is REJECTED", False)
except br.BriefConsistencyError as e:
    check("stale literal claiming recency is REJECTED", "recency" in str(e).lower())

# 3. the OLD contradiction (item3 latest=F005 vs item4 latest=F007) -> guard REJECTS
try:
    br.consistency_guard([
        {"id": "item3", "kind": "DERIVED", "text": "latest F005",
         "asserts": {"latest_campaign": "XAU-F005-20260717"}},
        {"id": "item4", "kind": "DERIVED", "text": "...F007...",
         "asserts": {"latest_campaign": "XAU-F007-20260721"}},
    ])
    check("old item3-vs-item4 contradiction is REJECTED", False)
except br.BriefConsistencyError as e:
    check("old item3-vs-item4 contradiction is REJECTED", "disagreement" in str(e).lower())

# 4. a correct, consistent, all-DERIVED field set PASSES
check("consistent derived set passes", br.consistency_guard([
    {"id": "a", "kind": "DERIVED", "text": "latest F007", "asserts": {"latest_campaign": "XAU-F007-20260721"}},
    {"id": "b", "kind": "DERIVED", "text": "captures 4", "asserts": {"latest_campaign": "XAU-F007-20260721"}},
]) is True)

print(f"\n{_p} passed, {_f} failed")
sys.exit(1 if _f else 0)
