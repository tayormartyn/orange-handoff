# FAROUK METHODOLOGY SPECIFICATION — v0.1

**Status: DRAFT / EVIDENCE-GRADED. Not a strategy, not a rule set, not executable.**
Synthesised from FP-EDU-001 (educational livestream, local transcript) and three reconstructed campaigns
(FP-CAMPAIGN-001 win, FP-CAMPAIGN-002 net-unknown/loss, FP-CAMPAIGN-003 win). No market data has been
downloaded; both campaign videos and the edu video are **retrospective / bar-replay**; some spoken claims
are **unverified**. Two campaigns + one video (now three campaigns + one video) is **not** enough to
declare a strategy. Every item is tagged:

- **[STRONG]** strongly evidenced (teaching + ≥1 directly-visible campaign, consistent)
- **[PARTIAL]** partially supported (stated in one source; mixed/limited across campaigns)
- **[HYP]** untested hypothesis
- **[CONTRA]** contradicted / discrepant across sources
- **[OPEN]** unresolved

> This document does not contain executable detector code and must not be treated as one.

---

## 1. Higher-timeframe context
- **[STRONG]** "The higher timeframe is stronger" / "high-timeframe OB is king"; layer order blocks across
  5m/15m/1h/4H/weekly and weight the higher TF more (EDU-C-004). Winners C001 (entered near an HTF supply
  that held) and C003 (OB rebound targeting the **Daily FVG**) entered **at** an HTF level; the loss C002
  entered **far** from its HTF bearish zones.
- **[PARTIAL]** A **Daily FVG** / daily high is used as an HTF magnet and continuation gate (C003 spoken:
  "we need at least one 1h candle close above the daily bearish FVG"; single instance).
- **[OPEN]** Exact weekly/daily zone construction and how HTF confluence is scored.

## 2. Session liquidity
- **[STRONG]** The **Asia session High/Low** is the core daily framing; a "Asia break HIGH/LOW" state is
  shown by the indicator panel in all three campaigns and taught extensively (EDU-C-012). Liquidity
  "rests" at session extremes ("trend liquidity", "$$$").
- **[PARTIAL]** **London high** liquidity is used alongside Asia (C003 spoken: "liquidity in London high
  and Asian high, tap it and then go down"). The **A+ long** = *break Asia High → wait retest* ("78% up",
  EDU-C-001) — **stated in teaching but NOT exemplified** by these three campaigns (C001/C002 were sells,
  C003 bought an Asia-**Low** sweep).
- **[HYP]** A session-extreme break that only grabs liquidity (no follow-through) is a **trap** to be faded
  (EDU-C-007; worked in C003's Asia-low sweep-then-reverse). The stronger "missing displacement/FVG ⇒ trap"
  form is **NOT promoted** (only C002's unverified external review asserts it).

## 3. Level construction
See the companion `FAROUK_LEVEL_CONSTRUCTION_SPEC_v0.1.md`. In brief: **[STRONG]** Asia High/Low, Order
Blocks (multi-TF), FVG/Daily FVG, CHoCH/BOS, and a **custom indicator panel** (TF · CHoCH · Asia break ·
OB retest · Current OB · Fresh OB) generate the traded levels.

## 4. Setup families
- **[STRONG]** **OB retest** after a break of structure (EDU-C-003; C001 win OB-retest inside entry zone;
  C003 win OB near the deeper entry).
- **[STRONG]** **OB + FVG confluence** (C003: the executed BUY and the missed 4000 long were both explicitly
  "OB + FVG"; EDU-C-006 "big FVG / BPR → look for a long").
- **[PARTIAL]** **Session-sweep reversal**: sweep an Asia extreme then reverse to the opposing liquidity /
  FVG (C003 win: Asia-low sweep → rebound toward Daily FVG).
- **[PARTIAL]** **A+ Asia-High-break long** (EDU-C-001) — taught but unexemplified here.

## 5. Entry triggers
- **[STRONG]** Enter on the **retest of the OB** (in the break direction) rather than the break itself
  (EDU-C-003; "wait for retest").
- **[PARTIAL]** **Layered / averaging** entries: an in-zone entry plus a deeper "best" entry, then "close the
  worst entry, hold the best entry" (C003 explicit; C001 Discord). *(C003's deeper 4027.37 entry provenance
  is [OPEN] — see §12.)*

## 6. Confirmation
- **[PARTIAL]** **CHoCH ("change of character")** is cited as *a* confirmation (EDU-C-005), but is **not**
  consistently required across wins (C003's winning BUY showed panel **CHoCH ×**).
- **[PARTIAL]** **Continuation gate**: a **1h candle close above the daily bearish FVG / daily high** is
  required for extension higher (C003 spoken; single instance; not price-verified).
- **[PARTIAL]** **FVG/BPR** presence supports a directional entry (EDU-C-006; C003).

## 7. Vetoes
- **[HYP] H-VETO-001** — an Asia-extreme break without bearish displacement / downside FVG / bearish CHoCH /
  valid OB-retest confirmation may be a liquidity trap rather than continuation (from C002; **unverified**).
- **[PARTIAL]** No trade if the required session break is absent (EDU-C-002: "we didn't break Asia High …
  because we didn't break Asia High").
- **[PARTIAL]** Do **not** re-enter a **mitigated** OB (C003 spoken: "don't enter another long here at this
  OB, already mitigated").

## 8. Structural invalidation
- **[STRONG]** Stop placed **beyond the structural extreme** (EDU-C-009: "my stop loss is above the Asia
  High"); published stops sit beyond the zone (C001 SL 4140 at supply top; C003 SL 4010 below the buy zone).
- **[PARTIAL]** Wider stops as a **beginning-of-month risk protocol** (C002 explicit; **[HYP] H-RISK-001**:
  a protocol, not reduced setup confidence).

## 9. Target selection
- **[STRONG]** Targets anchored to **structural / opposing liquidity** (EDU-C-011; all three campaigns'
  TP ladders). C003 targeted up toward the **Daily FVG** and named the opposing **4070–4080 sell zone** at
  swept highs; C001/C002 targeted structural levels on the profit side.

## 10. Campaign management
- **[STRONG]** **TP1 → move stop to breakeven** ("SL to entry") is consistent across the teaching and all
  three campaigns (EDU-C-008; C001, C002-LEG-A, C003).
- **[STRONG]** **Partial / scale-out** exits (C003: buy 1 → 0.5 → 0.25, "50% off", "75% out, risk free";
  EDU-C-011). A final runner is left and may stop at breakeven (C003 "SL entry hit").
- **[PARTIAL]** "Normally move stop to entry at 50–60 pips" (C003) — a stated threshold; one instance was
  disrupted by "my phone overheated and shut down".

## 11. Recovery / re-entry
- **[PARTIAL]** A **recovery trade** is a defined response to a stop-out (EDU-C-010; C002-LEG-B was a
  re-entry after LEG A stopped). This is a **contingency/management sub-protocol**, distinct from…
- **[PARTIAL]** …**layering/add-on** management within a live trade ("close worst, hold best"; C003). The
  two are different behaviours and should not be conflated. **[HYP] H-MGMT-001**: a fast TP1 may bias toward
  aggressive re-entry (C002).

## 12. Data gaps
- **[OPEN]** **Timezones** for all Discord timestamps (the edu platform shows **UTC+2**; Discord TZ unknown).
- **[OPEN]** **Provenance of C003's 4027.37 deeper entry** (add-on / recovery / re-entry / averaging /
  unposted) — a material evidence gap.
- **[OPEN]** **Currency** of the blue result-card values (no symbol shown; math is consistent with
  price × 100 × lot-size, but the unit is unrecorded). **Blue values must not be summed as realised P/L.**
- **[OPEN]** No **market data** downloaded → session levels, OB/FVG placement, MFE/MAE, and continuation
  claims are not price-verified.
- **[OPEN]** Transcripts are `base.en` (some SMC terms phonetic); "**displacement**" is never spoken in the
  edu video.
- **[CONTRA]** External-review discrepancies (C002 Gemini): feed "Pepperstone" vs actual Vantage/Bybit;
  "Binance" vs Bybit; spoken "3990 sell area" vs Discord "3970–3980". Held separately, not canonical.
