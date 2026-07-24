# FAROUK STATE-MACHINE INVARIANTS — v0.1

Hard rules the Alpha detector must satisfy at all times. Any design/implementation that can violate one of
these is rejected. These are checkable properties, not guidelines.

## Structural / ordering
- **I-1 — Registration precedes qualification.** `QUALIFIED_CANDIDATE` cannot occur before a zone or event
  has been registered (`ZONE_REGISTERED` / a confirmed context event). No qualification from thin air.
- **I-2 — No confirmation on an unclosed candle.** `BREAKOUT_CONFIRMED` (and any *_CONFIRMED state) cannot
  occur on an intrabar/unclosed candle **unless future evidence explicitly permits intrabar confirmation**.
  Until then, `G_INTRABAR_ONLY` vetoes and the transition waits for `BAR_CLOSED`.
- **I-3 — One setup, immutable origin.** Each setup instance has a single, immutable `origin_evidence`
  (creating event, bar_close_time, source_indicator, level). Origin is never rewritten.
- **I-4 — No resurrection without new identity.** An `EXPIRED`, `VETOED`, `STRUCTURE_INVALIDATED`, or
  `SWEEP_INVALIDATED` setup cannot return to `ARMED`/`QUALIFIED_CANDIDATE`; a fresh setup with a new
  `setup_id` and new origin evidence is required.
- **I-5 — Terminal Alpha state.** `QUALIFIED_CANDIDATE` is the last state the Alpha detector may reach. It
  emits an **observation only**; region 7 is reference-only and downstream.

## Timezone / data integrity
- **I-6 — Unknown timezone cannot qualify.** A session-dependent setup (ORB / session-range families)
  cannot reach `QUALIFIED_CANDIDATE` while the canonical timezone is unresolved; `G_TZ_UNRESOLVED` blocks.
- **I-7 — UTC internal, provenance retained.** Every timestamp is stored in UTC with original chart TZ,
  indicator TZ, session-definition TZ and DST context retained. No lossy TZ coercion.
- **I-8 — Unknown never silently passes.** Any UNKNOWN required input trips `G_ANY_UNKNOWN_GUARD` and
  blocks (fail-closed). Confidence may degrade but a guard is never treated as "true by default".
- **I-9 — No guessed ownership.** `source_indicator` is one of the supported set or `UNKNOWN`; unverified
  objects are never attributed to Smart Zones / POC / POC Prototype or to a specific [kyle] version.

## Safety / separation (non-negotiable)
- **I-10 — No risk/size/order from Alpha.** No Alpha state transition may create risk, position size, or
  broker/order instructions. `G_ANY_EXECUTION` is a hard veto everywhere in the detector.
- **I-11 — Campaign risk is external.** Campaign risk (the locked 1.0% campaign-wide policy) lives entirely
  OUTSIDE this state machine and is never read, written, or influenced by it.
- **I-12 — Execution gates are irrelevant to detector progression.** Detector states advance purely on
  market/indicator evidence; the value of any execution gate must not change any Alpha transition, and no
  Alpha transition may change any gate.
- **I-13 — Reference region is inert.** `CAMPAIGN_LIFECYCLE_REFERENCE_ONLY` never emits orders, sizes, or
  broker calls; it is documentation of downstream lifecycle only.

## Consistency
- **I-14 — Deterministic replay.** Given the same ordered event stream + same `rule_version`, the machine
  produces identical states/transitions (no randomness, no wall-clock reads inside guards).
- **I-15 — No probability in v0.1.** No win-rate/ML score participates in any guard or transition; only
  Boolean/veto/data/confidence/family-class inputs (I-8 style).
- **I-16 — Monotonic setup age.** A setup's age only increases; `SETUP_EXPIRED` is irreversible for that
  `setup_id` (ties to I-4).
