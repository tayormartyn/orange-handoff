# PARSER COVERAGE REPLAY — REPORT (D-015 step 3)
**Tag: RETROSPECTIVE_NOT_PROSPECTIVE.** Run 2026-07-20, interpreter sha16 `f27a90345118a116` (current live). Read-only: no campaign, freeze, ledger or cursor touched; outputs only in this directory (`parser_coverage_replay_results.json` = machine copy).

## Coverage: ZERO SILENT DROPS — proven by count reconciliation
| Source | Rows in | Dispositioned | Drops |
|---|---|---|---|
| signal_archive.db (raw_message_versions, ALL revisions, Nov-2025→) | 43,404 | 43,404 | **0** |
| prospective_evidence_v1.db (live capture 29-Jun→F006 era) | 565 | 565 | **0** |

## Disposition census (archive / prospective)
- NOT_FAROUK_GOLD_OTHER: 25,089 / 182 · NOT_FAROUK_GOLD_CRYPTO: 13,891 / 188 (scope-tagged per K-047)
- EXPLICITLY_REJECTED_EMPTY: 2,234 / 85 (text-less rows; media-only in prospective — correct)
- PARSED_COMMENTARY: 1,282 / 58 · PARSED_MANAGEMENT: 567 / 35 · PARSED_ENTRY: 16 / 11
- QUARANTINED_REVIEW: 325 / 6 — all LOUD, all reason-classed (below)

Management instruction census (archive): TP1 256 · TP2 141 · REVISED_STOP 107 · SL_TO_ENTRY 74 · TAKE_PCT_OFF 43 · FINAL_CLOSE 8 · EXPLICIT_FULL_EXIT 2 · CLOSE_WORST 2 · HOLD_BEST 3 · HOLD_RUNNER 3 · CANCEL 2 · INVALIDATION 2. (Prospective adds EXPLICIT_PERCENTAGE_PARTIAL_CLOSE ×2 — the F002/F005-era morphologies.)

## Quarantining morphologies (spec item 6 — every distinct class, fail-closed and loud)
| Reason class | archive | prospective |
|---|---|---|
| stop-related wording with no recognized instruction pattern (red-team safety net) | 274 | 4 |
| missing stop (entry-shaped, no SL) | 29 | 2 |
| N zone ranges found (need exactly 1) | 19 | 0 |
| ambiguous direction [BUY, SELL] | 2 | 0 |
| LONG stop not below zone | 1 | 0 |
These are CORRECT fail-closed outcomes, not silent gaps. The 274-row stop-wording class is the natural review corpus for any future morphology extension (Stage-2-adjacent; not fixed here because nothing is broken — every one quarantines loudly).

## Regression fixtures: 12/12 PASS
labelled-field form (`XAUUSD Sell Zone: 4050-4060 / Stop Loss: 4075`) → **ENTRY** ✓ · plain form → ENTRY ✓ · `full exit` → EXPLICIT_FULL_EXIT ✓ · `close 90% leave 10%` → EPPC ✓ · `close 100%` → EXPLICIT_FULL_EXIT ✓ · `tp 1 now` → TP1 ✓ · `put sl to entry` → SL_TO_ENTRY ✓ · claimed-pips (`700 pips`, `140-150 pips`) → NOT terminal ✓ · lot-fraction result card → NOT entry/terminal ✓ · crypto-in-gold-channel → NEEDS_HUMAN_REVIEW (refused as XAU entry) ✓ · crypto channel → NOT_FAROUK_GOLD ✓.
Note on the crypto-in-gold-channel fixture: it quarantines via the stop-side check rather than the no-XAU-word check (the header's "gold-trades" satisfies the instrument regex, and 5-digit crypto prices confuse the 4-digit gold-shaped zone regex). The OUTCOME is the required one (loud quarantine, never an XAU campaign) — recorded as a quirk, not a gap.

## Cross-instrument leak checks — CLEAN across 43,969 rows
- Crypto-content messages parsed as gold ENTRY: **0** (both DBs).
- Pips-mention messages producing a terminal instruction without genuine close morphology: **0** — the R-003 doctrine holds corpus-wide.

## Verdict
**PARSER COVERAGE: PROVEN.** Zero silent drops; every message parsed, quarantined loudly, or explicitly rejected; all named historical failure morphologies parse correctly under the current interpreter; no crypto leakage. **No gaps requiring fixes were found** — the demo-lane prerequisite on parser coverage is SATISFIED as of interpreter f27a9034.

---
# AMENDMENT (D-018, 2026-07-20, appended after operator checks — original above unmodified)
The §Verdict line "demo-lane prerequisite SATISFIED" is **AMENDED to CONDITIONAL**. Checks:
- **CHECK 1 (classification accuracy):** the archive's old-extractor signals table records **240 seascalperfarouk XAUUSD signals**; the current interpreter detects 16 entries (14 of them Jun-2026). Sept-25→May-26 gold-header months show 48–95 mgmt instructions each with ~0 detected entries (117 days have ≥2 mgmt + 0 entries). Cause: the pre-June era used **single-price entry morphologies** ("gold long sl 5090", "XAUUSD SELL 4635 / SL @ 4670", "High-risk short... (entry 4740.2) Stop loss at 4762") which the zone-based entry regexes do not match. Worst class: "gold long sl 5090" classifies as MANAGEMENT/REVISED_STOP — an entry read as a stop-move (wire orphan-handling fails it closed today; for a copy trader = order never placed).
- **CHECK 2 (stop-quarantine sample, seed 7, n=30 of 274):** 3 image-only/indeterminate; of 27 assessable, **~13–15 (~50%) are genuinely actionable** instructions in unrecognised variants: `stoploss to entry` (one-word), `sl entry` (no to/at), `stop loss now at 4465` / `set stop-loss at 4040`, typo `enty`, `take 90% sl entry`, plus old-style single-price entries. Mostly old-era, but these phrasing variants are timeless.
- **Consequence:** demo lane remains **GATED** until a morphology extension (single-price entry family + SL-variant family) is designed, approved, built and re-proven by full replay. Current-era live capture (F001–F006) is unaffected.
- **Minor (recorded):** the 4-digit gold-shaped `\d{4}` zone/SL regexes are a hardcoded assumption — brittle against future 5-digit gold prints.

---
## D-036 AMENDMENT (2026-07-21) — PREREQUISITE SATISFIED
The morphology-extension prerequisite recorded in the D-018 amendment above is **SATISFIED**: v2.1 (single-price entry family, SL-variant family, compound tp-N-sl-entry, HOLD_LEG_SELECTIVE, informational notes, per-clause completeness fail-closed) was fully proven (44/44 fixtures; battery 357 checks; full-replay ENTRY→non-ENTRY = 0; v2.0→v2.1 byte-identity changes exactly [45937, 45940]) and **DEPLOYED LIVE 2026-07-21T07:04:31Z** with operator approval. Before shas: interpreter f27a90345118a116 / live_wire c0027c56b2527593 → after: 7602755342a6748a / 7a8a4c4f1281fdb9. F006-scoped verification PASS; fwd/freeze/backfill/guards/constitution byte-identical. See D-036.
