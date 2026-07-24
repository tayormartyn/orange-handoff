"""STAGE 2 candidate-rule register builder v0.1 — ENFORCED guardrails (D-016 + reviewer
directive 2026-07-21). This script is the only writer of candidate_rules_v0_1.jsonl.

Pipeline order (reviewer-mandated):
  1. LOAD all miners' raw outputs (raw_miner_outputs/*.json — frozen as delivered).
  2. CROSS-AGENT DEDUP FIRST: merge duplicates/phrasing variants across miners into one
     canonical statement (merge map is explicit, human-authored, recorded in the file).
  3. NOVELTY GATE the DEDUPLICATED set against the pre-existing claim register.
  4. STATUS ENFORCEMENT (in code, not intention):
       - audio_verification_required and no verification record in
         g1_verifications_v0_1.jsonl  -> status FORCED to CANDIDATE_G1_PENDING_AUDIO
         (can never be CANDIDATE; attempting to pass status=CANDIDATE raises).
       - kill_condition empty         -> status FORCED to OBSERVATION (not a candidate).
       - instrument_scope crypto      -> status FORCED to CRYPTO_SCOPED_EXCLUDED (K-047)
         and the rule may never feed XAUUSD hypotheses.
       - novelty gate verdict KNOWN   -> status DUPLICATE_OF_KNOWN (register cites claim id).
  5. Every surviving rule carries: source_id(s), source_tier (weakest of evidence, G3),
     timestamps, quotes, G1 status, confirm_condition, kill_condition.

G1 VERIFICATION METHOD (process, recorded per verification in g1_verifications_v0_1.jsonl):
  locate the cited timestamp -> extract the audio segment from the SOURCE media file
  (ffmpeg, ±10s pad) -> verify by (a) machine corroboration: re-transcribe the segment
  with a LARGER model than the batch small.en and require agreement on the critical
  number/term, AND/OR (b) operator listening. Disagreement or inaudibility -> the rule
  STAYS CANDIDATE_G1_PENDING_AUDIO (never resolved by transcript text alone). Each
  verification record: {rule_id, source_id, timestamp, method, heard, resolved_value,
  verifier, verified_at_utc}.

Everything here is HYPOTHESIS_ONLY. Nothing is promoted to strategy, weights, or wire
behaviour. Statistical testing of any rule is a separate governed step (D-009 applies).
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
RAW_DIR = os.path.join(HERE, "raw_miner_outputs")
MERGES = os.path.join(HERE, "dedup_merge_map_v0_1.json")
G1_VERIFICATIONS = os.path.join(HERE, "g1_verifications_v0_1.jsonl")
REGISTER = os.path.join(HERE, "candidate_rules_v0_1.jsonl")
NOVELTY = os.path.join(HERE, "novelty_verdicts_v0_1.json")

VALID_STATUS = ("CANDIDATE", "CANDIDATE_G1_PENDING_AUDIO", "OBSERVATION",
                "DUPLICATE_OF_KNOWN", "CRYPTO_SCOPED_EXCLUDED")


def load_g1_verifications():
    out = {}
    if os.path.exists(G1_VERIFICATIONS):
        for l in open(G1_VERIFICATIONS, encoding="utf-8"):
            if l.strip():
                r = json.loads(l)
                out.setdefault(r["rule_id"], []).append(r)
    return out


def enforce_status(rule, g1_map, novelty_map):
    """Returns the FORCED status — caller intent cannot override the gates."""
    if rule.get("instrument_scope") == "crypto":
        return "CRYPTO_SCOPED_EXCLUDED"
    nv = novelty_map.get(rule["rule_id"], {}).get("verdict", "")
    if nv.startswith("KNOWN") or nv.startswith("STRONGER_EVIDENCE_FOR_KNOWN"):
        return "DUPLICATE_OF_KNOWN"
    if not (rule.get("kill_condition") or "").strip():
        return "OBSERVATION"
    if rule.get("audio_verification_required") and not g1_map.get(rule["rule_id"]):
        return "CANDIDATE_G1_PENDING_AUDIO"
    return "CANDIDATE"


def build(rules):
    """rules: list of synthesised dicts (post cross-agent dedup). Writes the register."""
    g1_map = load_g1_verifications()
    novelty_map = json.load(open(NOVELTY, encoding="utf-8")) if os.path.exists(NOVELTY) else {}
    seen_ids = set()
    with open(REGISTER, "w", encoding="utf-8") as f:
        for r in rules:
            required = ("rule_id", "statement", "category", "sources", "source_tier",
                        "confirm_condition", "kill_condition")
            missing = [k for k in required if k not in r]
            if missing:
                raise ValueError(f"{r.get('rule_id', '?')}: missing fields {missing}")
            if r["rule_id"] in seen_ids:
                raise ValueError(f"duplicate rule_id {r['rule_id']}")
            seen_ids.add(r["rule_id"])
            forced = enforce_status(r, g1_map, novelty_map)
            if r.get("status") and r["status"] != forced:
                raise ValueError(f"{r['rule_id']}: declared status {r['status']} "
                                 f"but gates force {forced} — declaration refused")
            r["status"] = forced
            r["g1_verifications"] = g1_map.get(r["rule_id"], [])
            r["novelty_verdict"] = novelty_map.get(r["rule_id"], {}).get("verdict", "UNCHECKED")
            r["hypothesis_only"] = True
            r["never_promoted_without_governance"] = True
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    return len(seen_ids)


if __name__ == "__main__":
    print("This module is imported by the synthesis script; it does not run standalone.")
    sys.exit(0)
