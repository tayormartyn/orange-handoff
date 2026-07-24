# ORANGE Knowledge Register v1 — durable retention index (read with `orange_knowledge_register_v1.json`)

**As of 2026-07-13 (~02:55Z). REVIEW-ONLY. This register is an INDEX + rule register over the existing
durable files — it does not duplicate or replace them. Update discipline: extend with version bump;
no rule moves OBSERVED→PROMOTED directly (path: replay/forward states → HUMAN_REVIEW → the v0.4
promotion gate + ratification).**

## Retention verdict: DURABLY RETAINED (after this session's two rescues)
Everything material now lives in repo files. Two at-risk classes were rescued this session:
1. **Transcripts** for explainer-001/002/003/004, the Jul-5 indicator audio, and Live Jul-3 — were
   ephemeral-scratchpad-only → rescued to `derived/transcripts/rescued_20260712/` (manifest+hashes).
2. **Sprint generator scripts** (detector v0.3 replay, day-2/4/5 matchers, expectancy builders,
   cycle tools — 42 scripts + june_gold_trades_dump.jsonl) — were ephemeral-only → rescued to
   `tools/rescued_sprint_scripts_20260713/`. Results were always durable; now generators are too.
Remaining non-durable content: session terminal output and mining extracts — all derived/reproducible
from durable transcripts; no unique knowledge remains outside the repo.

## Where everything lives (Task-1 map)
Provenance+hashes → per-asset review/meta JSONs (explainer 001/002/005 reviews; batch 003/004
`_source_meta.json`s; price_data hashes in audit/validation docs) · Transcripts →
`derived/transcripts/{batch_003,batch_004,explainer_005,rescued_20260712}` +
`raw/live_with_farouk_2026-07-05/_analysis/` · Timestamped video evidence → the five explainer/batch
review MDs · Methodology → `FAROUK_PLUS_RULESET_v0_1.*`, ratification records, batch reports, this
register (B) · Level construction → `LANE6_PRE_MARK_BUILDER_SPEC_v0_1.*` + register (C) · Management →
8C/8D addenda + batch reports · Feature candidates → merge queues + register (D) · Replay candidates →
`DETECTOR_V0_4_PROMOTION_GATE.md` + backlog files · Pre-marks → `pre_mark_candidates_v0_1.jsonl`
(+frozen snapshot in register F) · Corroboration/contradiction → 15m match report, v0.4 feature
effects, indicator audit · Unknowns → indicator audit §6/§9 + register C UNKNOWNs.

## Level-construction spec (C, v0.2 candidate framework)
**unmitigated origin-of-move/liquidity object → confluence → Asia H/L break with 5m/15m close
confirmation → limit entry at zone or mitigation snipe → stop beyond structure, width by level
type/mitigation context.** Explicit UNKNOWNs: zone selection among candidates; boundary construction;
A-grade formula; hidden panel formula (13 engine parameters); repaint behaviour; personal stop/fill
values when unstated.

## Known vs unknown (headline table)
| KNOWN (with provenance) | UNKNOWN (explicitly preserved) |
|---|---|
| selection criterion = unmitigated objects (MR-001) | which qualifying zone he picks |
| confluence stack + graded posture (MR-002) | exact zone boundaries |
| session trigger mechanics (MR-003) | A+/A+++ formula |
| magnet doctrine (MR-004) | panel/engine parameters |
| limit-at-zone + snipe entries (MR-005, documentary) | repaint behaviour |
| stop-width drivers + median ~$20-21 (MR-006) | his actual fills/stops when unstated |
| anticipatory BE 50-60p + BE-scratch rent (MR-007) | true session-prior statistics (MR-015 claims) |
| layering/close-worst/hold-best (MR-008) | |
| R2b no-re-entry, his own rule (MR-009) | |
| posted ≠ his book, ~$5 SL gap documented (MR-010) | |
| claim conventions / lane-5 discount (MR-011) | |
| displacement-FVG artifact doctrine (MR-012) | numeric displacement threshold (none exists) |
| spent-level doctrine; literal filter REJECTED in replay (MR-013) | |
| pre-marking is his workflow (MR-014) | pre-mark match rate (forward test running) |

## Pre-marks (F — frozen, immutable)
PM-F001-SELL-4150-4184 (exp Jul-17) · PM-F002-SUPPLY-4430-4480 (exp Jul-31) ·
PM-F003-SELL-4250-4260 (exp Jul-19) · PM-F004-DEMAND-3850-3863 (exp Jul-31) — all PRE_MARK_OBSERVED /
post-match PENDING; ledger sha256 at registration recorded in the JSON; boundaries never edited
(video-005's 4160–4170 corroboration recorded as a note, zone untouched).

## Prohibited from v0.3 (standing)
Session priors (unverified) · mitigated-exclusion hard filter (ratification-gated) · A-grade-derived
weights (formula unknown) · repaint-dependent values (F5) · claim-derived quantities (002B policy) ·
any video-only observation without the ratified merge path. **v0.3's actual inputs remain exactly its
replayed definition** (base v0.2 scoring + F1..F6 per the ratified merge plan) — integrity-hashed in
the JSON and checked by `tools/test_knowledge_register_integrity.py`.
