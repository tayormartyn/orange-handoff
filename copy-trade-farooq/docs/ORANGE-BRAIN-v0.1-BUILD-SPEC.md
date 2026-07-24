# ORANGE BRAIN v0.1 — BUILD SPEC (hand this to Fable / Claude Code)

**Purpose:** stop rediscovery permanently. Give every future session immediate access to everything the project already knows — every video, every Telegram message, every training document, every indicator capture — plus a gate that refuses to let known facts be reported as new, and a loop that keeps the project moving without Martyn driving it.

**Bounded build. One outcome. Do not widen it.**

---

## HARD CONSTRAINTS (unchanged, non-negotiable)

```
MODE=PAPER
LISTENER_MODE=PREVIEW
EXECUTION_ENABLED=False
CTRADER_EXECUTION_ENABLED=False
NOT_INTEGRATION_READY
```

No broker, demo or live execution. No credentials, account fields, sizing, orders, permits, leases or Smart Entry. No model fitting or promotion. No autonomous strategy change.

Do not restart the seven live research processes. Do not modify Constitution v0.1, frozen freezes, ledgers or campaign outcomes. Everything the Brain writes is **append-only**.

---

## LAYER 1 — CORPUS (the missing piece)

Ingest **once**, retrievable forever. This is the layer that ends "I've given him this twice."

**Ingest these source classes:**

1. **Telegram archive** — all historical captured messages (raw + normalised), including signals, management, result cards, commentary, and non-XAU (tagged, isolated).
2. **Video material** — every training video and live-breakdown video Martyn has supplied. Transcribe once to text with timestamps; store transcript + source metadata. Never re-transcribe an already-ingested video.
3. **Training documents** — Farouk's Playbook (Smart Money & Candlesticks), Whaleroom Candlestick Patterns, Order Blocks Strong vs Weak, Daily Gold Traders Signals Guide, Farouk Education, and any later additions.
4. **Indicator material** — FP-INDICATOR-005, FP-INDICATOR-006, ORANGE_INDICATOR_KNOWLEDGE_AUDIT, FP-LIVE-OBSERVATION-001, the 13-condition alert-condition audit, alert() payload captures, live Sweep / Engulfing / CHoCH / A LONG / A SHORT / A+ / A+++ captures, webhook logs, panel screenshots and continuity frames.
5. **Chart screenshots and result cards.**

**Every corpus item must carry:**

```
source_id            (stable, unique)
source_class         (telegram | video | document | indicator | screenshot)
source_tier          (PUBLISHED_FOLLOWER_METHOD | ADVANCED_EDUCATION_METHOD | PERSONAL_LIVE_METHOD_UNCONFIRMED)
ingested_at
content_hash
provenance           (where it came from, who supplied it, original filename/URL)
supersedes           (optional — for version drift, e.g. indicator updates)
```

**Requirements:**
- **Idempotent ingestion.** Re-supplying the same video/document must NOT create a duplicate — match on content hash and return `ALREADY_INGESTED` with the existing `source_id`.
- **Retrievable.** A local search index over transcripts and text so any session can answer "what do we already know about X?" without re-reading everything.
- **Tier-preserving.** Retrieval results always return the source tier. Tiers must never be merged or silently promoted.
- **Version-drift aware.** The indicator is actively developed; newer captures `supersede` older ones without deleting them.

---

## LAYER 2 — STATE (registries + novelty gate)

Machine-readable, append-only.

**Artifacts to create:**
- `START_HERE` — plain-English current project state for a fresh session.
- `project_state.json` — machine-readable state.
- **Knowledge claim register** — every extracted claim with `claim_id`, statement, `source_id`(s), source tier, evidence strength, status (`ACTIVE | SUPERSEDED | REJECTED | CONTRADICTED`), first-recorded date.
- **Campaign registry** — F001–F005+, **read from authoritative repository artifacts, not reconstructed from conversation summaries.** Flag any conflict rather than choosing a version.
- **Hypothesis registry** — including H-FPL-05, `IMPLICIT_PROFIT_MILESTONE_EXIT_CUE_v0.1`, `PROFIT_MILESTONE_PROGRESS_OR_SCALE_OUT_CUE_v0.1`, each with status, source tier and scoring state.
- **Decision log**, **rejected/superseded register**, **open-question register**, **known-defect register**.

**NOVELTY GATE — the point of the whole build.**

Before any finding is recorded or reported as new, it must pass through the gate:

```
INPUT:  candidate claim
CHECK:  match against knowledge claim register + corpus index
OUTPUT: ALREADY_KNOWN (+ claim_id, source_id, date first recorded)
        | INCREMENTAL (+ what exactly is new, against what prior art)
        | GENUINELY_NEW
        | CONTRADICTS_PRIOR (+ the conflicting claim_id)
```

Nothing may be described as a discovery without passing the gate.

**Mandatory acceptance test:** submit the claim *"Farouk's Playbook — Smart Money Suite indicator exists and is a major new structural discovery."* The gate MUST return `ALREADY_KNOWN` citing FP-INDICATOR-005 / FP-INDICATOR-006 and the alert-condition audit. If it does not, the build has failed.

---

## LAYER 3 — LOOP (the agent cadence)

Runs on a schedule and on new-campaign-close. Each cycle:

1. **Load Brain** — mandatory pre-flight. No analysis or build may start before this.
2. **Detect new material** — new Telegram messages, new campaigns, new videos/documents supplied by Martyn.
3. **Ingest** new material into the corpus (idempotent).
4. **Extract candidate claims** → run every one through the **novelty gate** → register only what is genuinely new or incremental.
5. **Score** any pre-registered hypothesis that has become scoreable (e.g. H-FPL-05), with no hindsight.
6. **Update** registries, contradictions and open questions (append-only).
7. **Produce Martyn's operator brief** — one page, plain English, no jargon: what changed, what it means, what's blocked.
8. **Recommend exactly three bounded next actions.**
9. **STOP** and wait for Martyn's approval. Execute nothing further.

---

## PERMISSIONS

**The Brain MAY autonomously:** read and index; reconcile evidence; refresh summaries; run the novelty gate; detect contradictions; score pre-registered hypotheses; write the operator brief; recommend three actions.

**The Brain MAY NOT, ever:** alter strategy rules or Constitution v0.1; rewrite or delete freezes, ledgers or campaign outcomes; mutate campaign state; fit or promote a model; touch risk, sizing or execution; change the hard gates; run a proposed build without Martyn's explicit approval.

---

## PROOF OF COMPLETION (all must pass)

1. Novelty gate returns `ALREADY_KNOWN` for the Playbook-indicator claim, citing prior art.
2. "What do we know about the indicator?" returns accumulated prior art from the corpus — not a fresh analysis.
3. "What videos and documents do we hold?" lists every ingested item with `source_id` and tier.
4. Re-supplying an already-ingested video returns `ALREADY_INGESTED`, creates no duplicate.
5. A fresh session demonstrably loads the Brain before doing anything else.
6. Campaign registry matches authoritative repo artifacts; every brief-vs-repo conflict is explicitly flagged, none silently resolved.
7. Operator brief generates with exactly three recommended actions.
8. Hard gates verified unchanged; no live process restarted; no frozen artifact modified.

---

## EXPLICIT NON-GOALS

No model fitting. No new setup families. No router widening. No broker, demo or execution work. No TradingView UI automation. No re-analysis of already-known indicator facts. No rewriting of F001–F005. This build adds **memory and retrieval only**.

---

## REPORT BACK

Files created/modified; corpus item counts by class and tier; registry counts; novelty-gate acceptance-test result; campaign-registry conflicts found; tests and counts; confirmation gates unchanged and no live process touched; what is now deterministic; what remains UNKNOWN.
