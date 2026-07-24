# FAROUK_HIERARCHICAL_STRATEGY_ROUTER_v0_1 (readable)

**RESEARCH_ONLY / NON_AUTHORITATIVE / NO_EXECUTION_CONSEQUENCE.** Authoritative form = the companion
JSON. The router is an **evidence + annotation layer**: it RECORDS, FREEZES and AUDITS Farouk's
*possible* decision hierarchy from causal market data. It never chooses a trade, never touches the
live follower, never fits weights, never activates Smart Entry, never routes an order.

## The 14-node hierarchy
`SOURCE_TIER → OBJECTIVE_LANE → TRADING_HORIZON → HTF_CONTEXT → MARKET_REGIME → SESSION_MODEL →
LIQUIDITY_NARRATIVE → POI_FAMILY → STRUCTURAL_CONFIRMATION → EXECUTION_CANDLE_CONFIRMATION →
ENTRY_MODEL → STOP_INVALIDATION → TARGET_MODEL → REJECTION_NO_TRADE`

Every node stores: **status, causal_timestamp, source_bar_cutoff, candidate_values, selected_value
(only if genuinely predetermined), alternatives, unknown_fields, rule_ids, provenance, confidence,
and activity (ACTIVE | REPLAY_ONLY | INACTIVE).**

## What it MAY do (Part 5)
Freeze causal market context; preserve all plausible regime labels, session models, liquidity /
inducement candidates, POI candidates, structural-trigger states, execution-candle states; enumerate
entry-model candidates; generate a research-only blind hypothesis; record UNKNOWN.

## What it MAY NOT do
Change the live follower; determine authoritative entries; alter stop/management; activate Smart
Entry; select whichever route later wins; fit weights; optimise parameters; create live proposals;
mutate outcome ledgers; emit execution instructions.

## Two confirmation layers kept separate
- **STRUCTURAL_CONFIRMATION** (ranked p1): BOS ▸ FVG-inversion ▸ Level-reclaim ▸ SFP/Burj-Khalifa.
- **EXECUTION_CANDLE_CONFIRMATION**: engulfing / hammer / shooting-star / rejection candle.
The structural priority *ranks* structural methods; it does **not** replace the execution candle. The
router records the strongest causally-available structural trigger **and** every lower-priority
alternative. It never requires all four.

## Causality (Part 9)
Every feature obeys `bar_close_time ≤ decision_timestamp`. A bar that has opened but not closed at the
decision timestamp is forbidden. Each frozen feature records decision_timestamp,
latest_source_bar_open/close_time, causal_cutoff, feature_version, source_hashes. A metamorphic test
proves appending arbitrary future bars changes no previously-frozen pre-decision feature.

## Companion contracts
source-tier · objective-lane · advanced setup families (all DECLARED_INACTIVE) · structural-trigger
priority · valid-BOS · execution profiles (primary UNKNOWN) · OTE (DISABLED shadow) · volume-profile
(DATA_UNAVAILABLE) · ranking-model boundary (interface only). Only `FVG_CONTINUATION_5M` and
`ASIA_SESSION_FAKEOUT` execute, OFFLINE_REPLAY_ONLY, disabled from the live follower.

## Scope isolation
Crypto/weekend material (PO3 weekend claim, BTC/ETH examples) is scope-gated and **must not** enter
XAU. Volume Profile stays UNKNOWN until direct volume-at-price data exists.
