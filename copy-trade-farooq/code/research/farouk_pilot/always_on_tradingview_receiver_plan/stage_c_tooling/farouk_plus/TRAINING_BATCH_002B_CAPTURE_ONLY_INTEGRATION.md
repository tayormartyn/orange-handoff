# Training Batch 002B — Capture-Only Integration (audit R-lane + stop-width dataset)

**Mode: CAPTURE-ONLY INTEGRATION — SINGLE-SESSION.** Observation-only. Date 2026-07-11.
Extends (never edits) the Cycle-002 schema addendum, Batch-001B plan, and all prior artefacts.
**Detector v0.3 live labels are UNCHANGED for Cycle 004** — everything here is recorded alongside, never
scored. Machine-readable: `training_batch_002b_capture_only_integration.json`. Gates
`PAPER/PREVIEW/False/False`; `NOT_INTEGRATION_READY` unchanged.

## 1. New capture-only fields (per XAU-F record, Cycle 004+)

| field | definition |
|---|---|
| `audit_r_midpoint` / `audit_r_low` / `audit_r_high` | the claim-based R estimate per the FP-AUDIT-001/002 methodology (midpoint + sensitivity bounds), computed at outcome-review time from posted entry/SL/claims |
| `audit_source_id` | FP-AUDIT-002 (methodology lineage) |
| `audit_convention_notes` | which conventions applied (e.g. flats-excluded accounting; managed-credit vs target-hit; unknowns bracketed) |
| `stop_width_dataset_reference` | pointer into the stop-width calibration set (34 sprint setups + 6 May samples + spoken anchors) |
| `stop_width_anchor_class` | `MAY_SAMPLE` \| `VIDEO_SPOKEN_ANCHOR` \| `POSTED_SL` \| `STRUCTURAL_INVALIDATION` \| `UNKNOWN` |
| `stop_width_value_if_known` | $ width beyond the zone far edge (posted or structurally derived) |
| `stop_width_context` | `fresh_level` \| `mitigated_level` \| `strong_level` \| `weak_level` \| `HTF_supply_demand` \| `unknown` |

## 2. Hard constraints on the two additions

**`audit_r_midpoint` is capture-only:** useful for later triangulation analysis (the claim-lane
+0.27–0.35R estimate vs the deterministic lanes); **never a live entry score, never a risk-size or
position-size field, never an execution gate.** It carries no sizing semantics — R here is a
dimensionless outcome ratio computed from posted prices.

**`stop_width_dataset_extension` is capture-only:** it grows the `stop_width_by_level_type` v0.1 research
set (now: 32 sprint widths median ~$20 + 6 May samples $20–40 + spoken "$30–40" anchor + STRONG-class
$20–85). It **does not alter the follower lane after entry and does not permit stop widening after
entry** — the Batch-001B never-widen ratification stands in full; widths inform *pre-freeze* invalidation
hypotheses only.

## 3. Version discipline

- **Detector v0.3: unchanged.** Cycle 004 emits v0.3 (and v0.2 parallel) labels exactly as before.
- **Detector v0.4 backlog updated:** may consume these fields **only after offline replay**, and any
  scoring use of `audit_r_midpoint` (a claim-derived quantity) additionally requires **human
  ratification** (claim-derived inputs feeding scores is a policy question, not a technical one).

## 4. Cycle-004 readiness note

When XAU-F001 arrives: capture `audit_r_midpoint/low/high` if the setup is linkable to the audited
convention (posted entry/SL + claims suffice); capture the stop-width anchor class/value/context whenever
an SL is posted or a structural invalidation is visible; everything else per the 8C+8D+8F+001B spec.
**Not run in this step. No May-trade OHLC matching run in this step** (remains a batch-003 option).

## 5. Safety confirmation

Documentation only; targets pre-flight-checked; nothing overwritten; spreadsheet sizing/account/
compounding content remains redacted/excluded; no execution built; no permits/leases/orders; gates
unchanged; listener PID 87988 running; no TradingView/Worker/R2/secret action.
`NOT_INTEGRATION_READY` unchanged.

## Next step

Cycle 004 at the next market activity (gold reopens Sunday ~22:00Z) under the full capture spec including
these fields; detector v0.4 offline replay thereafter; batch 003 later.
