# FILL-PLACEMENT DISTRIBUTION (D-046 round)

**Survivorship-limited (posted cards only). Mechanical comparison only. NEVER expectancy.**

Matched fills: 18 | unmatched (no ledger zone within 48h, incl. pre-F001 era): 37

## Distribution across zone thirds
{
 "bottom": 10,
 "middle": 2,
 "top": 6
}

## Per-fill rows
- XAU-F002-20260714 msg 45728: fill 4085.33 in [4084.0, 4094.0] rel 0.133 (bottom); nearest leg 4084.0 delta 1.33
- XAU-F002-20260714 msg 45729: fill 4085.33 in [4084.0, 4094.0] rel 0.133 (bottom); nearest leg 4084.0 delta 1.33
- XAU-F003-20260716 msg 45803: fill 4023.08 in [4025.0, 4035.0] rel 0.0 (bottom); nearest leg 4025.0 delta -1.92
- XAU-F004-20260716 msg 45809: fill 4006.11 in [4003.0, 4014.0] rel 0.283 (bottom); nearest leg 4008.5 delta -2.39
- XAU-F004-20260716 msg 45811: fill 4004.23 in [4003.0, 4014.0] rel 0.112 (bottom); nearest leg 4003.0 delta 1.23
- XAU-F004-20260716 msg 45812: fill 4006.11 in [4003.0, 4014.0] rel 0.283 (bottom); nearest leg 4008.5 delta -2.39
- XAU-F004-20260716 msg 45816: fill 4006.11 in [4003.0, 4014.0] rel 0.283 (bottom); nearest leg 4008.5 delta -2.39
- XAU-F005-20260717 msg 45879: fill 3997.52 in [3998.0, 4008.0] rel 0.0 (bottom); nearest leg 3998.0 delta -0.48
- XAU-F005-20260717 msg 45885: fill 3997.52 in [3998.0, 4008.0] rel 0.0 (bottom); nearest leg 3998.0 delta -0.48
- XAU-F005-20260717 msg 45885: fill 3997.01 in [3998.0, 4008.0] rel 0.0 (bottom); nearest leg 3998.0 delta -0.99
- XAU-F006-20260720 msg 45939: fill 4009.64 in [4000.0, 4010.0] rel 0.964 (top); nearest leg 4010.0 delta -0.36
- XAU-F006-20260720 msg 45939: fill 4007.68 in [4000.0, 4010.0] rel 0.768 (top); nearest leg 4010.0 delta -2.32
- XAU-F006-20260720 msg 45939: fill 4005.72 in [4000.0, 4010.0] rel 0.572 (middle); nearest leg 4005.0 delta 0.72
- XAU-F006-20260720 msg 45941: fill 4005.72 in [4000.0, 4010.0] rel 0.572 (middle); nearest leg 4005.0 delta 0.72
- XAU-F007-20260721 msg 45974: fill 4060.55 in [4053.0, 4063.0] rel 0.755 (top); nearest leg 4063.0 delta -2.45
- XAU-F007-20260721 msg 45974: fill 4059.71 in [4053.0, 4063.0] rel 0.671 (top); nearest leg 4058.0 delta 1.71
- XAU-F007-20260721 msg 45978: fill 4060.55 in [4053.0, 4063.0] rel 0.755 (top); nearest leg 4063.0 delta -2.45
- XAU-F007-20260721 msg 45978: fill 4059.71 in [4053.0, 4063.0] rel 0.671 (top); nearest leg 4058.0 delta 1.71

---
## DIRECTION-NORMALIZED DEPTH (the mechanism-relevant view; appended same run)
Depth = distance INTO the zone from the ARRIVAL (first-touched) edge: LONG arrival edge = zone top, SHORT = zone bottom. The three-leg model places legs at depths 0 / 0.5 / 1.0.

**Distribution across 18 matched fills (6 campaigns F002-F007, both directions): shallow third 16 · middle third 2 · deep third 0.** Depth range 0.00-0.43, median ~0.24. Distinct-fill view (deduplicating repeat card rows): 11 distinct fills — 9 shallow, 2 middle, 0 deep — same shape.

Mechanical consequences (no expectancy, survivorship-limited):
1. **The model's far leg (depth 1.0) has never filled in the observed record** — consistent with F006 (far never filled) and F007 (mid/far cancelled).
2. On shallow-penetration campaigns the model fills ONLY its arrival-edge leg (depth 0 = the worst price in the zone) while his fills sit slightly deeper (0.2-0.4) — the exact F007 mechanism (model 4063=depth 0 vs his ~4060.1 at depth ~0.29), now visible across every observed campaign.
3. "Lowest/best entry" instructions therefore resolve systematically worse in the model than in his account.

DISCLOSURES: 37 rows unmatched (no in-ledger zone within 48h — mostly pre-F001 era; extension to archive-era zones is a named follow-up). F006's above-zone fill 4013.02 fell 0.02 outside the +/-3 match tolerance and is EXCLUDED from the 18 (the exclusion is conservative: including it would add one more shallow/outside-edge fill). Repeat card rows of the same position counted in the 18; distinct-fill view given above.

---
## ARCHIVE-ERA EXTENSION (D-048; run immediately after ratification per operator follow-up 1)
Join source: data\signal_archive.db (240 Farouk XAU signals with zones, old extractor). 21 of the 37 previously-unmatched rows matched a June-era archive zone within 48h -> **+9 distinct fills** (34 rows remain unmatched: mostly commentary-adjacent cards with no zone in either source within the window — reported, not dropped).

June-era distinct fills: 8 shallow, 0 middle, **1 DEEP (0.81 — 2026-06-25 LONG 4007.94 in [4006,4016]) — the first deep-third observation in the record.** Note: 4 of the 9 sit at-or-marginally-outside the arrival edge (matched within the ±3 tolerance; depth clamped to 0).

**COMBINED SAMPLE (n=20 distinct fills, ~13 campaigns, Jun-03 → Jul-21): shallow 17 (85%) · middle 2 · deep 1.** Median depth ~0.2. Shape CONFIRMED on the enlarged sample; the single deep outlier softens "never deep" to "rarely deep (1/20)". K-050's far-leg statement stands as written (no observed fill at the far-edge leg placement itself; deepest observed = 0.81).

P-EP-1 (0.15/0.40, no far leg) remains supported by the enlarged sample — values unchanged, sample basis updated n=11 -> n=20. Recorded as a sample-basis amendment, NOT a retune (parameter values untouched); operator acknowledgement requested per the no-quiet-retuning rule.
