"""ORANGE BRAIN — deterministic prior-art / novelty gate (v0.1).

Checks a proposed claim against knowledge_claims_v0_1.jsonl and
rejected_and_superseded_v0_1.jsonl BEFORE any report may call it new.
Pure deterministic token matching — no LLM, no network, read-only.

Usage:
  python novelty_gate.py --claim "..." [--domain D] [--sources p1 p2 ...]
  python novelty_gate.py --selftest
"""
import argparse
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
THRESHOLD = 0.35
GRAY = 0.20


def tokens(text):
    return set(t for t in re.split(r"[^a-z0-9%+]+", text.lower()) if t and t not in STOP)


STOP = {"the", "a", "an", "is", "was", "are", "were", "of", "and", "or", "to", "in",
        "on", "for", "it", "its", "this", "that", "with", "as", "by", "be", "has",
        "have", "had", "at", "from", "s", "we", "his", "he", "our"}


def load_jsonl(name):
    p = os.path.join(HERE, name)
    return [json.loads(l) for l in open(p, encoding="utf-8") if l.strip()]


def kw_hits(keywords, prop_toks):
    hits = 0
    for kw in keywords:
        kt = tokens(kw)
        if kt and kt <= prop_toks:
            hits += 1
    return hits


def score(entry, prop_toks):
    stmt = entry.get("precise_statement") or entry.get("statement") or ""
    st = tokens(stmt)
    jac = len(st & prop_toks) / max(1, len(st | prop_toks))
    kws = entry.get("keywords", [])
    kscore = kw_hits(kws, prop_toks) / max(3, len(kws)) if kws else 0.0
    return round(2.0 * kscore + jac, 4)


def check(claim_text, domain=None, sources=None):
    prop = tokens(claim_text)
    claims = load_jsonl("knowledge_claims_v0_1.jsonl")
    rejected = load_jsonl("rejected_and_superseded_v0_1.jsonl")

    scored_c = sorted(((score(c, prop), c) for c in claims),
                      key=lambda x: (-x[0], x[1]["claim_id"]))
    scored_r = sorted(((score(r, prop), r) for r in rejected),
                      key=lambda x: (-x[0], x[1]["rej_id"]))
    best_c_score, best_c = scored_c[0] if scored_c else (0, None)
    best_r_score, best_r = scored_r[0] if scored_r else (0, None)

    result = {"proposed_claim": claim_text, "domain": domain,
              "supporting_sources": sources or [],
              "best_claim_match": None, "best_rejected_match": None,
              "matching_prior_claim_ids": [], "matching_artifact_paths": [],
              "classification": None, "reason": None, "human_review_required": False}

    top_ids = [c["claim_id"] for s, c in scored_c[:3] if s >= GRAY]
    result["matching_prior_claim_ids"] = top_ids
    if best_c is not None and best_c_score >= GRAY:
        result["best_claim_match"] = {"id": best_c["claim_id"], "score": best_c_score,
                                      "status": best_c["status"],
                                      "statement": best_c["precise_statement"][:180]}
        result["matching_artifact_paths"] = best_c.get("source_paths", [])
    if best_r is not None and best_r_score >= GRAY:
        result["best_rejected_match"] = {"id": best_r["rej_id"], "score": best_r_score,
                                         "kind": best_r["kind"],
                                         "statement": best_r["statement"][:180]}

    # 1) rejected/superseded register wins when it is the strongest signal
    if best_r is not None and best_r_score >= THRESHOLD and best_r_score > best_c_score:
        kind = best_r["kind"]
        result["classification"] = ("CONTRADICTS_PRIOR_EVIDENCE" if kind == "REJECTED"
                                    else "SUPERSEDES_PRIOR_INTERPRETATION")
        result["reason"] = (f"Matches {kind.lower()} record {best_r['rej_id']}: "
                            f"{best_r.get('rejected_because') or best_r.get('superseded_by')}")
        result["matching_artifact_paths"] = [best_r.get("source", {}).get("path", "")]
        result["human_review_required"] = True
        return result

    # 2) knowledge register match
    if best_c is not None and best_c_score >= THRESHOLD:
        status = best_c["status"]
        new_sources = [s for s in (sources or []) if s not in best_c.get("source_paths", [])]
        if status in ("GENUINELY_NEW", "HYPOTHESIS_ONLY", "UNKNOWN",
                      "SUPERSEDES_PRIOR_INTERPRETATION"):
            result["classification"] = status
            prov = " Provenance recorded (prospectively_proven=True)." if best_c.get(
                "prospectively_proven") else ""
            result["reason"] = (f"Restates registered claim {best_c['claim_id']} "
                                f"(status {status}).{prov} Not a fresh discovery — cite the claim.")
        elif new_sources:
            result["classification"] = "STRONGER_EVIDENCE_FOR_KNOWN_FACT"
            result["reason"] = (f"Known fact {best_c['claim_id']}; proposal adds new sources "
                                f"{new_sources} — append evidence to the claim, do not call it new.")
        else:
            result["classification"] = "ALREADY_KNOWN"
            result["reason"] = (f"Matches {best_c['claim_id']} "
                                f"({best_c['source_paths'][0] if best_c.get('source_paths') else ''}). "
                                f"Prior art — must not be reported as new/first/discovery.")
        return result

    # 3) no adequate match
    if max(best_c_score, best_r_score) >= GRAY:
        result["classification"] = "NOT_EVIDENCED"
        result["reason"] = ("Weak partial match only (gray zone) — insufficient register evidence "
                            "either way. Human review required before any novelty wording.")
    else:
        result["classification"] = "NOT_EVIDENCED"
        result["reason"] = ("No register match. Either genuinely novel or the registers are "
                            "incomplete — REQUIRES human review + explicit prior-art file search "
                            "(indicator audit, observatory, live observations) before publication.")
    result["human_review_required"] = True
    return result


SELFTESTS = [
    ("Farouk's Playbook exists and makes the process partly algorithmic.",
     {"ALREADY_KNOWN"}),
    ("The Sunday frames add a continuity dataset for panel-to-bar analysis.",
     {"GENUINELY_NEW", "STRONGER_EVIDENCE_FOR_KNOWN_FACT"}),
    ("The 140-150 pips message was the final exit.",
     {"CONTRADICTS_PRIOR_EVIDENCE", "SUPERSEDES_PRIOR_INTERPRETATION"}),
    ("H-FPL-05 was recorded before the week's market outcome.",
     {"GENUINELY_NEW"}),
    ("The indicator panel shows ChoCH, Asia break, OB retest, Current OB and Fresh OB fields.",
     {"ALREADY_KNOWN"}),
    ("SL to entry does not cancel unfilled legs.",
     {"CONTRADICTS_PRIOR_EVIDENCE"}),
    ("Genuine prospective campaign count is two: F004 and F005.",
     {"ALREADY_KNOWN"}),
]


def selftest():
    ok = True
    for text, expect in SELFTESTS:
        r = check(text)
        verdict = "PASS" if r["classification"] in expect else "FAIL"
        if verdict == "FAIL":
            ok = False
        print(f"[{verdict}] {r['classification']:<34} <- {text}")
        print(f"        match={r.get('best_claim_match') or r.get('best_rejected_match')}")
    print("SELFTEST", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--claim")
    ap.add_argument("--domain")
    ap.add_argument("--sources", nargs="*")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        sys.exit(selftest())
    if not a.claim:
        ap.error("--claim required (or --selftest)")
    print(json.dumps(check(a.claim, a.domain, a.sources), indent=1))
