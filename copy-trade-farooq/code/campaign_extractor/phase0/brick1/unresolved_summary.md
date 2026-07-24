# BRICK 1 — Unresolved Campaign Census + Evidence-Bounded Materiality

READ-ONLY diagnostic. No event, association, campaign state, expectancy, or baseline was
modified. Deterministic: identical inputs reproduce identical output hashes.

## Corpus (and its limitation)
Censused: the 4 campaigns that exist through the extraction pipeline —
the fixtures June 17 / 24 / 25 / 26. **This is NOT the full archive.** An archive-wide
materiality read would require full-archive LLM extraction, which is NOT built. Treat
these numbers as a pipeline-behaviour census on the available campaigns, not a
population-level edge estimate.

## Census
- Total campaigns: 4
- Fully resolved: 2
- Partially resolved: 2
- Unresolved: 0
- Total ambiguous (NEEDS_REVIEW leg-targeting) events: 11

### Ambiguity categories (every event has a NAMED reason; no generic bucket)
- move-stop target unknown (multiple open legs, no disambiguating price): 3
- partial-TP target unknown (multiple open legs, no disambiguating price): 3
- partial-TP target unknown (worst/best/highest/lowest ranking): 1
- partial-close target unknown (multiple open legs, no disambiguating price): 1
- partial-close target unknown (worst/best/highest/lowest ranking): 2
- stop-hit leg unknown (price belongs to a co-declared new leg): 1

### By month
- 2026-06: 4 campaigns, 2 not fully resolved

### By campaign style
- single-leg: 3
- multi-leg: 1

All ambiguous events resolve to a single multi-leg campaign (June 26). The single-leg
campaigns (June 17 / 24 / 25) fully resolve via the deterministic single-open-leg rule.

## MATERIALITY (evidence-bounded)

### KNOWN-EVIDENCE-ONLY SCENARIO (a SCENARIO — not a floor, not truth; bias direction UNKNOWN)
This is NOT a conservative floor. Excluding the unresolved campaigns can bias the result
UP or DOWN, and the direction is unknown, because the excluded set is not a random sample —
it is specifically the COMPLEX (multi-leg) campaigns. Reported strictly as a scenario:
- campaigns INCLUDED (known realised R): 0
- campaigns EXCLUDED (unresolved / no known R): 4
- total known realised R (sum over included): 0.0000R
- mean R over INCLUDED only: UNDEFINED (denominator = 0)
- denominator used: 0 (campaign-level, = number of included campaigns)

With 0 included campaigns the scenario is UNCOMPUTABLE (denominator 0): there are
no fully-supported realised-R campaigns at all. This is BY DESIGN — the extractor
fail-closes on entry-fill price, exit price, size and fractions, so it emits auditable
campaign STRUCTURE (legs, events, terminal status) but no realised R. It does NOT yet emit
an edge number.

### LIKE-FOR-LIKE with +0.17R: NOT directly comparable (reconcile first)
The +0.17R baseline and this scenario differ on every axis of analysis:
| axis | +0.17R baseline | this scenario |
|------|-----------------|---------------|
| unit of analysis | per SIGNAL | per CAMPAIGN |
| population | signal-level history (price-aware system) | 4 extracted fixtures |
| denominator | signals scored | campaigns with known R (0) |
| scoring | all-in, price-derived R | fail-closed; R not computed |
Because population, denominator AND unit differ and cannot be reconciled here, the two are
**NOT directly comparable**. We therefore do NOT claim the edge moved or held. Any future
comparison MUST first reconcile population, denominator and unit (same population, same
unit, same scoring) before any number is set beside +0.17R.

### Materiality to the +0.17R signal-level baseline: **0R (structural)**
Separate from the comparability question: this campaign-extractor is PAPER / advisory and
never writes to the signal-level scoring path that produces +0.17R (EXECUTION_ENABLED=False).
The maximum defensible shift to +0.17R from ANY resolution of these unresolved campaigns is
**0R** — they cannot move that baseline at all, by architecture.

### Bounds for the 0 unresolved (multi-leg) campaign
- lower bound: INDETERMINATE — affected leg / size / outcome unknown; no defensible lower
  numeric bound exists. (The known-evidence-only number is NOT substituted as a bound.)
- upper bound: INDETERMINATE — same; no defensible upper numeric bound exists.
- zero-for-unknown (SCENARIO ONLY, not truth, not a bound): treating every unknown as 0R
  contributes exactly 0R — an accounting convention, not a measured or bounded outcome.
- genuinely INDETERMINATE campaigns (no defensible numerical bound — unknown size /
  affected leg / outcome): 4 (2026-06-17:gold, 2026-06-24:gold, 2026-06-25:gold, 2026-06-26:gold).

NOTE: no false worst-case or best-case is manufactured. Where size, affected leg, or
outcome is unknown, the value is reported as INDETERMINATE, never as a number, and the
known-evidence-only scenario is never presented as a bound.

## Determinism / integrity
- unresolved_campaign_census.csv sha256: b304d47cccfd96161ab497ce3f6db96c95552525fa200d5e0f580500658c0732
- unresolved_event_census.csv sha256: 427614fb9770f010e48aa508c44682d5eda64666f7ec2a7c0160fb15cb6a40de
- No source DB, archive, shadow DB, expectancy, baseline, locked truth, or prompt was
  changed by this diagnostic.
