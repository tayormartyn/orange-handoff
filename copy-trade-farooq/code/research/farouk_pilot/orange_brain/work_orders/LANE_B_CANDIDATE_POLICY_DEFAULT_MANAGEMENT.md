# LANE B CANDIDATE POLICY — DOCUMENTED DEFAULT MANAGEMENT (registered 2026-07-21, D-043)

**Status: REGISTERED CANDIDATE POLICY — SHADOW-ONLY, NOT SCORED YET, NOT BUILT INTO ANY LANE.**
Operator-directed. Lane A and Constitution v0.1 DO NOT change — Lane A is the strict explicit-instruction follower by definition; that is its identity, not a bug.

## The hypothesis this encodes
Per the training material, a trained subscriber applies **default management without being told**: partial-take and SL-to-breakeven around +50 pips. Farouk often does not state it because the rules are assumed known ("make sure to put sl entry guys!" on F007 arrived AFTER his own fills were already managed). Consequence: Lane A, acting only on explicit instructions, may **systematically under-manage** versus a trained subscriber — a structural (not random) gap, sitting alongside LANE_A_ENTRY_MODEL_ADVERSE_DIVERGENCE as the second structural difference between Lane A and lived-follower results.

## Frozen parameters (from the source documents — cited, not tuned)
- **P-DM-1 (Whaleroom Trading Guide, FP-EDU-003, 12pp, recovery index `raw/documents/`):** at **+50 pips** move SL to entry; take **50% at TP1**. (Guide also documents the 3-point entry, corroborating the leg model.)
- **P-DM-2 (limit-order channel characterisation, LIMIT_ORDER_CHANNEL_CHARACTERISATION.md):** "Every 30 pips we take partial profit; once profit reaches **50–70 pips**, move SL to entry" — DIFFERENT product/lane (D-023 DIFFERENT_SPECIES); recorded as the cadence variant, **never merged with P-DM-1**; gold-lane shadow uses P-DM-1 only.
- Parameter freeze: P-DM-1 = {be_trigger_pips: 50, tp1_fraction: 0.50}. No other parameters. Any change = new policy version, re-registered.

## Pre-registered conditions (stated BEFORE any scoring)
- **Confirm:** across the next 5 fill-achieving campaigns, Farouk's observed/stated management (result cards + explicit messages + video) is consistent with P-DM-1 defaults in ≥4 — i.e. partials/BE occur near +50 pips WITHOUT an explicit instruction preceding them.
- **Kill:** ≥2 of the next 5 fill-achieving campaigns show management that contradicts the defaults (no partial by +80 pips without a stated reason, or BE not moved after +70 pips, or an explicit instruction that overrides the default in the opposite direction) — then the "assumed defaults" model is wrong or unstable and the policy is rejected.

## Application rules
- **Shadow-only**: a Lane B policy-sensitivity variant computes what P-DM-1 management WOULD have done; never a headline number, never Lane A, never executable.
- **Retrospective rows permitted for F004 / F005 / F007 ONLY as explicitly-labelled RETROSPECTIVE** (policy registered after their outcomes were known); prospective scoring starts F008.
- Novelty-gate verdict recorded below before first use.
- No promotion, no fitting, D-009 unchanged.

## ENTRY-PLACEMENT PARAMETERS — RATIFIED AND FROZEN (2026-07-21, D-047)
**P-EP-1 = {leg_depths_from_arrival_edge: [0.15, 0.40], far_leg: NONE}.** Source: FILL_DISTRIBUTION_ANALYSIS.md (operator-verified OCR dataset; direction-normalized depth). Shadow-only; prospective from F008; retrospective rows explicitly labelled.

**SAMPLE BASIS — PROMINENT, PER OPERATOR AMENDMENT: these parameters are FITTED to 11 distinct observed fills across six campaigns (F002-F007), survivorship-limited to posted cards. That is an OVERFITTING RISK regardless of how clean the distribution looks.**

**PRE-REGISTERED REVISION/ABANDONMENT PREDICATE (defined BEFORE any scoring; never quietly retuned — any change is a NEW registered version):**
Evaluate over the first 5 fill-achieving forward campaigns from F008 with captured cards (distinct fills, direction-normalized depth):
- **ABANDON** if ≥2 of the 5 campaigns place their deepest distinct fill in the DEEP third (depth > 0.66), OR the pooled shallow-third share falls below 40% — the shallow-clustering model is then wrong, not mistuned.
- **REVISE** (new version, enlarged sample cited) if pooled median depth falls outside [0.10, 0.45] while the shallow-clustering shape holds.
- **STAND** otherwise.
A campaign whose cards are not captured is NOT_SCORABLE for this predicate (recorded, never skipped silently — result-card capture task D-041 feeds this).

**Structural fact recorded alongside (K-050): the model's far leg has NEVER filled across six campaigns in both directions — a fact about the model, not a run of luck.** (Enlarged-sample precision, D-048/D-049: deepest observed fill 0.81 < far-leg placement 1.0 — statement stands; companion claim softened from "never deep" to "rarely deep, 1 of 20".)

**SAMPLE-BASIS AMENDMENT — REVIEWER-ACKNOWLEDGED (D-049):** cited basis amended n=11 distinct fills / 6 campaigns → **n=20 distinct fills / ~13 campaigns / 7 weeks (2026-06-03→07-21)**; parameter VALUES untouched. Standing practice recorded: **any change to a frozen record's cited basis requires explicit reviewer acknowledgement, even when values are unchanged.**

**CANDIDATE DIRECTION ON THE EVIDENCE TRAIL (recorded 2026-07-21, NOT acted on):** on the enlarged sample (shallow 17 / middle 2 / deep 1, median ~0.2) the second leg at depth 0.40 sits in sparse territory — only 2 of 20 observed fills fall in the middle third; both legs may belong shallower. **DO NOT RETUNE:** the revise predicate is keyed to F008+ FORWARD campaigns, not retrospective sample growth; this note exists so any legitimately-triggered future revision finds the direction already on the trail rather than discovering it conveniently later.

**STANDING DISCLOSURE (keep visible):** 4 of the 9 June fills sit at-or-marginally-outside the arrival edge within the ±3 match tolerance — bears on how arrival-edge depth 0 is interpreted (some "depth 0" fills are chases just beyond the published edge, not edge-limit fills).

## Companion candidate registered same day — ENTRY-PLACEMENT policy (direct evidence attached)
The F007 mechanism proof (D-044) is direct evidence for a SECOND Lane B candidate: **entries modelled where he actually fills (mid-zone) rather than at published zone edges.** On F007, edge placement resolved "lowest entry" to 4063 (premature scratch); his actual mid-zone fills resolved it to 4059.71 (runner survived, +943 USD open at ~09:54Z, price never came within 1.36 points of his stop). Parameters for this candidate must be frozen from observed fill data (result cards / OQ-10 output) before any scoring — same discipline as this policy; registration of frozen parameters pending that dataset.

## Novelty gate
Run at registration (2026-07-21): **ALREADY_KNOWN — matches K-001** (master source-of-truth records the guide's defaults). Correct and expected: the default-management RULES are documented prior art (which is precisely why their parameters could be frozen from source documents rather than fitted); the new machinery is only the Lane B shadow application of them. No novelty claim is made.
