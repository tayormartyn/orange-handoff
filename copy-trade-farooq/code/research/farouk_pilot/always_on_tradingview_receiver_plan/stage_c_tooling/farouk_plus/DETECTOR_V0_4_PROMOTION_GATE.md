# Detector v0.4 — Promotion Gate (standing conditions; nothing here authorises promotion)

**As of 2026-07-12. This file defines what must ALL be true before detector v0.4 (or any v0.4 feature)
may replace or join v0.3 in live forward scoring. Until every condition is met AND governance signs
off, v0.4 is offline-only. No automatic promotion exists anywhere in the stack.**

## Gate conditions (all required)

1. **Forward evidence base:** ≥15 forward XAU-F records across ≥5 sessions, captured with TRUE zone
   formation times (not the 24h proxy), per the standing demo-readiness blocker list.
2. **Out-of-sample replay:** v0.4 variants re-run on those forward records only. In-sample results
   (this replay) carry zero promotional weight — V4-SP/SPX's 0-promoted-loss figures are
   threshold-selection artefacts until reproduced out-of-sample.
3. **No stratification regression:** out-of-sample, the candidate must not add promoted-tier loss
   leakage vs v0.3, and promoted-winner retention vs v0.3 must be reviewed explicitly (the in-sample
   cost was 10–11 demoted winners — a human judgement call, never an automatic trade-off).
4. **Ratification records required BEFORE any scoring use:**
   - `mitigated_level_exclusion` — doubly gated: (a) the standing Batch-003 ratification requirement,
     (b) it is a GATE-type feature, so adopting it revisits ratification #2 (graded stack, no
     all-boxes veto). Its literal form (V4-LIT) is REJECTED outright under the proxy.
   - `audit_r`/claim-derived inputs (incl. anything built on `claim_convention_notes`) — the 002B
     policy ratification (claim-derived quantities feeding scores is a policy question).
   - Any weight upgrade of a ZERO_WEIGHT flag (F1 rule applies to new features identically).
5. **Displacement test precondition:** `displacement_fvg_artifact_test` may only be scored after a
   deterministic FVG-presence implementation runs on captured formation-leg OHLC with frozen,
   hash-logged windows (leak-free), and its replay is reviewed. No proxy substitutes.
6. **TF-hierarchy precondition:** ≥5 forward records carrying explicit candle-close evidence
   (in-sample density was 2/34 — unevaluable). Remains +confidence-only per ratification #1.
7. **Validator enforcement unchanged:** all v0.4 outputs pass the ai_review fail-closed validator +
   extended forbidden-token guard; labels confined to the allowed five; stamp from the validator only.
8. **Governance sign-off:** explicit human approval recorded in a ratification record naming the exact
   v0.4 configuration promoted. Gates (`PAPER/PREVIEW/False/False`) and `NOT_INTEGRATION_READY` are
   untouched by any detector promotion — a detector version change is a REVIEW-lane change only and
   never an execution-surface change.

## Explicitly out of scope for promotion

Capture-only fields stay capture-only regardless of v0.4's fate: limit-at-zone evidence,
posted-vs-actual SL gap, indicator semantics, claim-convention notes, audit-R fields, stop-width
dataset references. They inform research and human review, never labels, unless individually ratified.

## Current status

- v0.3 live (with v0.2 parallel A/B). v0.4 offline candidate.
- In-sample replay done 2026-07-12 (`DETECTOR_V0_4_OFFLINE_REPLAY_REPORT.md`): V4-LIT rejected;
  V4-SP/SPX mixed, not recommended; V4-TF neutral; displacement untestable in-sample.
- Conditions 1–3: NOT met (0 forward XAU-F records exist). Condition 4: no ratifications requested.
- **Nothing is pending promotion.**
