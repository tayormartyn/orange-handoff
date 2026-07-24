# H-FPL-06 — PRE-REGISTRATION: does the published weekly plan predict his own campaign zones?
Registered 2026-07-20 (reviewer-instructed). Predicate FROZEN NOW, before any further campaign exists. Distinct from H-FPL-05 (plan vs PRICE); this tests plan vs HIS OWN SUBSEQUENT CAMPAIGNS. Directly material to Lane C because the plan is published before the trades. Novelty-gate note: gate matched K-017 (related GENUINELY_NEW parent) — registered as a distinct child hypothesis, not a duplicate; K-017 cited as parent.

## Generating observation (NEVER confirming evidence)
XAU-F006-20260720 (msg 45935, BUY 4010–4000) sits directly adjacent to the Sunday-plan buy region 3984–4000 (H-FPL-05 zones, video-frozen). **F006 is excluded from scoring — it generated this hypothesis.**

## Frozen predicate (may not be tuned after registration)
For each FUTURE campaign C (F007 onward) posted in a week W for which a preserved pre-open weekly plan P(W) exists (source-controlled video or equivalent dated artifact):
1. Extract C's published entry zone [c_lo, c_hi] from the campaign's own message (as parsed by the wire — no reinterpretation).
2. For each named plan region R = [r_lo, r_hi] in P(W) *on the same side (buy/sell) as C's direction*:
   - **OVERLAP** if the intervals intersect;
   - **ADJACENT** if min gap between intervals ≤ height(R);
   - else **UNRELATED**.
3. C scores its best category across regions. Also record the gap distance in points.
4. Report = descriptive counts per week (OVERLAP / ADJACENT / UNRELATED, n) with the campaign and plan artifacts cited. **No significance claims, no null-model fitting, no rule promotion** until a governance-signed evaluation design exists; this register only accumulates prospectively-scored rows.
5. A week with no preserved pre-open plan → campaigns that week are NOT_SCORABLE (recorded, not skipped silently).

## Status
ACTIVE, prospective-only, zero rows scored. First scorable campaign: F007+ during a week with a preserved plan (current week qualifies via FP-LIVE-20260719).
