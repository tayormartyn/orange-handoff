# PAIRED LANE A / LANE B SHADOW SCORING — SPEC + PRE-REGISTRATION (D-062, 2026-07-21)

**Reviewer directive. Effective F008 onward. Automatic, no manual step. This is the primary evidence stream for the project's core question.**

## Objective ceiling (stated so it is never quietly restated)
The goal is **parity with a PERFECT FOLLOWER OF HIS PUBLISHED SIGNALS.** Parity with his PERSONAL ACCOUNT is **not achievable and not the objective** — private fills, unposted outcomes (K-018) and relay failures (K-053) place his personal trade set permanently beyond observation. The objective must never be restated as "match Farouk". (Registered as claim K-054.)

## Per-campaign paired output (from F008, every genuine prospective campaign, automatic)
Three columns:
1. **LANE A** — Constitution v0.1 UNCHANGED: legs at zone edges + midpoint, explicit-instruction management only. The baseline; NEVER modified.
2. **LANE B** — P-EP-1 entry placement (depth 0.15 / 0.40 from arrival edge, no far leg) PLUS documented default-management P-DM-1 (partial + SL-to-BE at +50 pips, per the frozen FP-EDU-003 citations).
3. **SOURCE-OBSERVED** — where his actual fills exist in the OCR dataset (result_card_capture / OQ-10): what a follower matching HIS fill placement would have obtained.

For each: fill prices · fill count · realised result (pips/unit) · terminal type + cause · and the **delta** (Lane B − Lane A; and each lane's entry-distance to source-observed).

## Binding conditions
- **Lane B NEVER writes** to Lane A records, the freeze ledger, or the learning dataset. Shadow output goes only to `paired_scores_v0_1.jsonl` (review_only / eligible_for_prospective_evidence=false / eligible_for_training=false).
- The **P-EP-1 pre-registered abandon/revise predicate governs** the entry model; **no quiet retuning** (a mid-series parameter change is a new registered version, forward-only).
- **Report BOTH lanes every campaign, win or lose.** A Lane B that underperforms IS the finding, not a failure to adjust away.
- Lane B management uses P-DM-1 defaults ONLY where Lane A has no explicit instruction covering the same action; an explicit Farouk instruction always takes precedence in both lanes (Lane B is not a different strategy, it is Lane A + documented defaults + fill placement).

## PRE-REGISTERED JUDGMENT — declared BEFORE any scoring (never tuned after)
Evaluated over the **first 5 fill-achieving paired campaigns from F008** (uncaptured-card campaigns are NOT_SCORABLE, recorded not skipped):

**LANE B IS JUDGED *NOT AN IMPROVEMENT* if ANY of:**
1. **No result edge** — Lane B realised result ≤ Lane A in ≥3 of the 5 campaigns (i.e. median per-campaign delta ≤ 0).
2. **No placement edge** — Lane B's mean entry-distance to source-observed fills is NOT smaller than Lane A's (the 0.15/0.40 depths fail to actually sit closer to where he fills).
3. **Worse terminals** — Lane B suffers ≥2 terminal outcomes strictly worse than Lane A on the same campaign attributable to the entry/mgmt change (e.g. Lane B's deeper/earlier config stopped out where Lane A survived, or a P-DM-1 default exit forfeited a runner Lane A kept).

If none of (1)–(3): Lane B is a **candidate improvement, pending continued series** (never "proven" at n=5 — descriptive, no promotion, no fitting; D-009 stands).
Note the asymmetry: (1) and (2) can BOTH be near-neutral and Lane B still fails on (3) — a placement that matches his fills but whose default management forfeits runners is not an improvement. This is deliberately a hard bar: the burden is on Lane B to demonstrate edge, not on Lane A to defend the baseline.

## Trigger
Auto-fires when a new genuine prospective campaign reaches a terminal state (OUTCOME_FROZEN / adjudicated). Reads: fwd ledger (zones/legs/instructions), tracker Lane A slices, OCR source-observed fills. Writes only `paired_scores_v0_1.jsonl`.


## AMENDMENT (D-077, 2026-07-21) — ENTRY-DETERMINED MANAGEMENT DIVERGENCE
Ratified from the fill-modelling diagnostic (K-064). The entry model and management are **not independent contributors** — they are **causally coupled through the break-even level**: entry price sets the BE, the BE decides runner survival, survival decides the terminal. F007 proved it: Lane A entered 4063 (BE 4063, struck by the ~4061.8 post-instruction retrace, runner dead at +5.38); Farouk entered 4059.71 (BE cleared by ~2 pts, runner survived to +121 / +943 USD). A ~3.3-pt entry difference determined the **entire** runner outcome.

**Binding consequences for this design:**
1. **P-EP-1 is judged on TERMINAL OUTCOMES, not entry-price improvement.** Predicate (1) result-edge and (3) worse-terminals are the decision basis; predicate (2) entry-distance is **context/diagnostic only** and MUST NOT be read as P-EP-1's value — scoring on entry pips alone would measure ~33 and miss the +121 it can preserve.
2. **Report BOTH per campaign, plus the coupling:** for each lane record the entry price, the resulting BE level, the post-instruction retrace extreme, and a boolean `entry_flipped_terminal` (did the retrace fall between the two lanes' BE levels, so the entry difference alone decided runner survival). This makes the non-linear entry→BE→terminal effect visible rather than hidden inside a realised-pips delta.
3. **General law (K-064):** small entry differences produce large outcome differences non-linearly, via the BE level, whenever a retrace falls between the two entry prices. Any future "entry effect is small" statement must be checked against this before it is made.

No parameters changed by this amendment; P-EP-1 depths (0.15/0.40) untouched; scoring remains F008-guarded.
