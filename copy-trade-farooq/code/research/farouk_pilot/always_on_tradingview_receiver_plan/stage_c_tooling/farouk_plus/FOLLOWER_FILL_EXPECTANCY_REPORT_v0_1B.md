# Follower-Fill Expectancy Report v0.1B (conservative bar-walk model) + RECONCILIATION with v0.1

**Mode: STEP 8 CAPTURABILITY TABLE.** Observation-only. Date 2026-07-11.
**IMPORTANT PROCESS NOTE:** two sessions worked this step in parallel. The other session produced
`FOLLOWER_FILL_EXPECTANCY_REPORT_v0_1.md` + `follower_fill_expectancy_table_v0_1.json` (Model A) at
~13:00Z; this session's independently-built table (Model B) briefly overwrote that JSON at 13:12Z —
**restored** at 13:17Z by re-running the other session's generator script; Model B now lives at
`follower_fill_expectancy_table_v0_1b.json`. Both artefacts are preserved. **Recommend serialising future
work to one session at a time.**

## 1. Two models, two answers — the divergence IS the finding

| | **Model A (v0.1, parallel session)** | **Model B (v0.1b, this session)** |
|---|---|---|
| follower fill | posted-zone MEDIAN | NEAR-EDGE zone boundary (always fills when zone trades) |
| TP banking | 50% at the POSTED TP1 level; runner scratched only when "sl to entry" was actually posted; manual-close setups credited with last-claim achievable | 50% at +50p (his universal stated rule) + 25% at +100p; runner scratched at first BE-return after arming; full loss if hard SL trades pre-arm |
| exit quality | near best-achievable (optimistic bound) | worst-case literal automation (pessimistic bound) |
| result (raw) | 22W/7P/1S/2L · **mean +132.3p** · median +115.5p · total +4,234.5p (32 computable) | 13W/17P/4L · **mean +1.4p** · median +25p · total +48p (34 computable) |
| result (R2b+R4b filtered) | mean **+142.9p** (n=28) | mean **+25.6p** (n=24, total +614.4p) |

**Why they differ:** Model B's automatic BE-return scratch fires in 22 of 34 trades (price revisits the
fill after +50p in almost every trade — the MAE data from Step 1 said exactly this), truncating winners at
+25–50p. Model A scratches only where the instruction was actually posted and lets exits track posted TPs
/ achievable — crediting follower exits with near-Farouk quality. **His real instruction timing sits
between the two.** The honest joint statement:

> **Follower capturability from posted information is positive but lies in a wide model-dependent band:
> raw [+1.4 … +132.3] pips/trade; R2b+R4b-filtered [+25.6 … +142.9] pips/trade.
> Confidence: MODERATE for the sign under the filtered set; INSUFFICIENT_DATA for the magnitude until
> forward capture records ACTUAL instruction timestamps and resolves the scratch model.**

## 2. What BOTH models agree on (robust findings)

1. **Headline claims are not capturable:** Model A: +699p of claimed pips unreachable across 22
   claim-cases (6 setups with inflation_ratio > 1.25). Model B: capture ratio 16.4% (848.7p of 5,180p
   claimed). **R6 claim discount: STRONG, in both models.**
2. **R2b (first-attempt-only) is the binding protective rule** — Model A: +10.6 mean uplift; Model B:
   +452p of losses removed (+17.8 mean uplift). **R4b helps in both.**
3. **S2-type first-attempt losses are unavoidable in every lane** (−310 to −359p) — the irreducible
   entry risk.
4. **His private fills/management beat every follower lane** (J24 +170 vs 0; J30 240 vs ≤175; widgets
   prove his stops weren't at the literal instructed levels).
5. **J11-class evening runners** (MFE 1,369p in Model B's window — price ran to 4,219.94) show the market
   sometimes exceeded even his claims after his exit — headline inflation and under-capture co-exist.

## 3. Model-B-specific detail (see `follower_fill_expectancy_table_v0_1b.json`)

Biggest divergences: S1 follower +25 vs 922p available (BE-scratch 1 min after fill) · J26 +123 (best
follower trade) vs his 674 · S3 +25 vs 558p MFE · J10 **−427** (post-time fill + hard SL; Model A excluded
this row as unavailable — Model B's inclusion is more conservative and drags its mean) · J16 −200 (Model B
fills the zone edge that Model A's median never filled). Mid-zone sensitivity: mid fills **never trade** on
J20/J25/J26/S1 — deeper-limit strategies miss the best trades entirely.

## 4. Conclusion labels

- Raw literal automation ≈ zero expectancy: **MODERATE** (Model B, deterministic bar-walk).
- Follower edge positive under optimistic management: **MODERATE** (Model A).
- Sign positive under R2b+R4b in BOTH models: **MODERATE** (in-sample, circular-feature caveat).
- Magnitude: **INSUFFICIENT_DATA** — bounded, not pinned; forward instruction-timing capture resolves it.
- Claims inflated / not capturable: **STRONG** (both models, deterministic).

## 5. Safety confirmation

Offline computation only; overwrite incident detected, disclosed, and repaired (both artefacts preserved).
No broker/QST/cTrader/nano/copy/demo/live execution; no permits/leases/orders; gates
`PAPER/PREVIEW/False/False`; listener PID 87988 running/untouched; no TradingView/Worker/R2/secret action;
nothing trade-ready. `NOT_INTEGRATION_READY` unchanged.

## Next step

Forward Cycle 002+ must log **actual management-instruction timestamps** per XAU-F record so lane-4 can be
computed with the real scratch points (collapsing the Model-A/Model-B band), and both tables re-run on
≥15 forward trades. Lane 6 results: `ORANGE_PRE_MARK_RETROSPECTIVE_REPORT_v0_1.md`.
