# 🫸・limit-order-trades — READ-ONLY CHARACTERISATION (D-023, 2026-07-20)
Corpus: 141 archive messages in-channel (2025-06-11 → 2026-04-23), all seascalperfarouk-authored. Gate decision returns to Martyn; nothing widened.

## Channel history (from its own messages)
- **2025-06 → 2025-09: CRYPTO limit orders** (BTC/ETH/SOL/SUI/ENA/LTC/DOGE/HYPE/TAO/AAVE/XRP) — "SUI: 2.3-2.2 SL: 2.05" style. Then dormant.
- **2026-01-29 REVIVAL POST:** "I'm putting this channel back to use. The limit order channel… we used it mainly for crypto before… now I'm bringing it back to life" — for GOLD.
- **2026-02-10 → 2026-04-23: GOLD limit era** (the 15 old-extractor signals). Dormant since 04-23; zero posts in the live-capture window.

## The five questions
1. **Format:** RELATED BUT DISTINCT morphologies: single-price limits ("Limit gold 5022 / Sl 5007", "Sell limit at 4960"), comma prices ("Entry: 4,619 - 4,610"), zone forms ("Buy Zone: 4992–4980"), and **explicit 3-leg limit ladders ("Entry 1: 5,050 / Entry 2: 5,042 / Entry 3: 5,035")**. Some would parse under v2 (comma/single-price work generalises); the ladder form and "Limit gold <price>" label are new morphologies.
2. **Management:** SAME instruction vocabulary, in the SAME channel: `sl entry`, `tp 1..4`, `take 50% sl entry`, `close 100%`, break-even, partials — the interpreter's management taxonomy covers it.
3. **Entry mechanics: GENUINELY PENDING/LIMIT — a different lifecycle.** Orders placed ahead of price with heavy churn: "Adjustment sell limit…", "Last adjustment…", "missed by 30–40 pips", "Remove all limits", "Remove the limit — we just missed it", cancel-then-replace sequences. A pre-fill ADJUST/CANCEL/MISS lifecycle that the gold-trades zone model doesn't have. **Stated management protocol differs from the ratified constitution defaults:** "Every 30 pips we take partial profit; once profit reaches 50–70 pips, move SL to entry" (vs ratified take-some=25% / per-leg BE). The "3-point entry like we learned in Whaleschool" reference (2026-02-17) corroborates the 3-leg model itself.
4. **Outcomes:** same pips-claim/bragging style + a P&L result card ("28W / 10L, +$9,933.44").
5. **Overlap with captured campaigns:** none — the gold-limit era (Feb–Apr) predates live capture (29-Jun→) and F001–F006; no same-zone/same-day duplicates identified among the 15 vs gold-trades signals.

## RECOMMENDATION: **DIFFERENT_SPECIES_SEPARATE_LANE**
Rationale: pending-order lifecycle (adjust/cancel/miss churn) ≠ zone-entry model; explicitly different stated management cadence (30-pip partials, 50–70→BE) vs Constitution v0.1 defaults; every post framed "high-risk play"; and the channel carries historical CRYPTO contamination (K-047 scoping must be per-message, not per-channel). Folding into Lane A would pollute gold statistics with a different product — the crypto-leak failure class. The instruction VOCABULARY is shared, so a future separate lane could reuse the interpreter plus a limit-lifecycle extension (ADJUST_LIMIT / CANCEL_LIMIT / MISSED morphologies) and its own constitution addendum. **Decision returns to Martyn; must be settled before the demo lane goes live.**

## Two intelligence finds (recorded, no action)
- **2026-04-23: "Next week we'll connect the bot and you can go on holiday… I'll start with a small account first"** + back-office P&L screenshot — Farouk himself runs/planned a **copy-bot** for this lane. Directly relevant context for Orange's own demo-lane framing and for interpreting his result claims.
- The revival post explains the gate history: the channel was crypto-native; its gold use was an experiment (Feb–Apr) that he paused. Re-activation risk is real and the intake observer's out-of-gate quarantine class remains the live tripwire.
