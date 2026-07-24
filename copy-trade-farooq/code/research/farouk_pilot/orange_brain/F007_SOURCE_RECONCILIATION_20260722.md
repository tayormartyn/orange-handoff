# F007 SOURCE RESULT-CARDS + SOURCE CHART — INGEST & RECONCILIATION
Date: 2026-07-22 | Operator-supplied full F007 image set | Derived record (authority = ledgers/cards)

**Tier:** SOURCE_REPORTED_OUTCOME · `eligible_for_prospective_evidence=false` · `eligible_for_training=false`
· `survivorship_limited=true` · usage = **MECHANICAL ENTRY-DIVERGENCE COMPARISON ONLY, NEVER expectancy.**
**Frozen record untouched:** F007 Lane A realised **+5.38 pips/unit** stands unaltered (card `strict_follower_lane`, D-045/K).

## 1. Ingest — idempotent

### ALREADY_INGESTED (no duplication) — the two result cards, hash-verified on 2026-07-21
These are already in `ocr_trial/source_reported_outcome_v0_1.jsonl` from the 2026-07-21 OCR pass, with real `image_sha256`:

| msg | posted (UTC) | fills (entry) | carded exit (second_price) | result_usd | image_sha256 (first 16) |
|-----|-------------|---------------|-----------------------------|------------|--------------------------|
| 45974 | 2026-07-21T09:02:48 | 4060.55 / 4059.71 | 4063.72 | 317 / 401 | 6d1fb395827fff83 |
| 45978 | 2026-07-21T09:10:37 | 4060.55 / 4059.71 | 4066.59 | 604 / 688 | fa1e15c394335b1e |

Operator's supplied fills (4060.55, 4059.71) and exit progression (4063.72 → 4066.59) match these rows exactly → **ALREADY_INGESTED, not re-written.**

### NEW source material — operator-transcribed 2026-07-22, image NOT hashed by Orange
Orange never reads media (OQ-10); these values are **operator-transcribed**, so they carry no `image_sha256` and are recorded here (derived layer), NOT appended to the hash-verified OCR ledger, to keep that ledger's provenance clean:

- **Intermediate partial exit 4065.15** — referenced between the two carded exits (4063.72 → **4065.15** → 4066.59). Not separately carded; recorded as a referenced waypoint only.
- **His M5 chart (his own platform):** drawn stop-loss line **SL 4059.71** (= his lowest entry), open-position marker **BUY 1, +943.00 USD** (unrealized, open). The +943 USD open was already noted in K-060/K-064 from the 09:54Z chart; the **drawn SL at 4059.71** is newly captured.

## 2. Reconciliation vs K-060 / K-064 (ENTRY-DETERMINED MANAGEMENT DIVERGENCE)

The now-captured source values **confirm the recorded mechanism** — and upgrade one link from *inferred* to *source-drawn*:

| | Lane A (frozen) | Farouk (source) |
|---|---|---|
| entry used | near leg **4063** (mid 4058 / far 4053 cancelled) | fills **4060.55 / 4059.71** |
| break-even | BE **4063** | BE **4059.71** — now **drawn on his own chart as SL 4059.71** |
| post-instruction retrace low | 4061.78 @09:31Z fell **between** the two BEs | |
| runner | BE **struck** → runner dies, **+5.38** | BE **cleared** → runner survives, **+943 USD open** |

- **First SOURCE-DRAWN (not inferred) confirmation that his break-even = his entry.** Prior to this, BE=4059.71 was inferred from the "SL to entry on lowest entry" instruction; his chart now literally draws SL at 4059.71. The ~3.3-pt entry difference, *through the BE level it set*, determined the entire runner outcome — exactly K-064.
- **Two K-060 caveats still travel with any gap figure** (mandatory, not footnotes): (a) NOT like-for-like — his narrative peak-capture vs Lane A's modelled realised; (b) source unreliable in detail — his chart/video entry-count narrative differs from his posted two cards. **May NOT be quoted as "Lane A captured X% of what Farouk made."**
- No contradiction surfaced. F007 **+5.38 untouched.**

## 3. Entry-model evidence (P-EP-1) — feature-capture only, NO parameter change
His chart shows **multiple entry arrows spread ~4059.7–4063.6** — several fills across the shallow zone, **not two clean legs**. Recorded as evidence bearing on **P-EP-1 leg placement and count**. P-EP-1 values (0.15 / 0.40) **UNCHANGED**; scoring remains F008-guarded (nothing runs now).

## 4. FR-058 corroboration — NOT upgraded
Management "close worst / hold best" and "tp1, SL to entry on lowest entry" are further leg-selective **close-worst/hold-best** instances. Noted as additional support; **FR-058 remains at its existing G1-confirmed status**, not upgraded (it already stands on triple corroboration: doctrine + F006 45938 + F007 45973).

## Result
Ingest = idempotent (2 cards ALREADY_INGESTED; new chart/waypoint recorded, operator-transcribed, unhashed). Reconciliation = mechanism **CONFIRMED** from source, BE=entry now source-drawn. No frozen record changed. Gates unchanged.
