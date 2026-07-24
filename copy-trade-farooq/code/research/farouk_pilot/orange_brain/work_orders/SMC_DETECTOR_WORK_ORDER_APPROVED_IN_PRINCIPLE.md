# SMC FEATURE DETECTORS — APPROVED IN PRINCIPLE, BINDING CONDITION (2026-07-21)

**Status: APPROVED_IN_PRINCIPLE — NOT BUILDABLE YET.** Operator approval granted subject to one binding condition; final build approval happens when the frozen definitions are brought back.

## Governance precedent (record prominently; standing rule)
**Detector definitions must never be constructed after observing the rationale they will be tested against.** Origin: F007 msg 45976 (2026-07-21 09:07:27Z) published an itemised rationale ("1h Bullish FVG tapped / 1h Low Sweep / 1/3m Bullish CHoCH"); Orange had no registered FVG/sweep/CHoCH detector, and building one at that moment — with the target rationale already in view — was **refused as post-hoc fitting** (D-039) and the refusal ratified by the operator (this order). This is the same discipline family as pre-registered predicates (H-FPL-05/06/07) and the adjudication preconditions: the definition must exist, frozen, before the comparison it will be scored on.

## Binding condition
SMC detector definitions (FVG formation + tap, session-low sweep, CHoCH, and any others) must be:
1. **Derived from the Stage 2 mined-rule register** (documented-method provenance: each definitional choice cites the mined rule(s) and their transcript provenance — e.g. candle-close requirements, timeframe hierarchy, fresh/mitigated distinctions — not reverse-engineered from any campaign's rationale or outcome);
2. **Pre-registered with frozen parameters** (sha-pinned) BEFORE any campaign comparison is run;
3. Applied **prospectively from registration forward**; rationale statements (45976-class) become label sources only AFTER the definitions are frozen.

## Sequencing
Do not build until the Stage 2 candidate-rule register exists (in progress) and the definitions are frozen from it. Then bring the frozen definitions to the operator for build approval. Retro-application to F007's rationale is permitted only as an explicitly-labelled retrospective row (the definitions post-date the rationale) — never mixed with prospective rows.

## ADDED 2026-07-21 (D-067) — timestamp hygiene
Stored transcript timestamps are VAD-COMPRESSED (vad_filter=True) and drift from real audio with recording length (K-056/K-057). If detector derivation ever maps a rule back to a recording moment, it MUST re-locate the utterance by real-audio position (search the token, no-VAD), NEVER seek by the stored transcript timestamp. This is part of the binding condition.
