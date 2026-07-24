# Cost-Model Application — cost_assumptions_v0_1 (HYPOTHETICAL until measured broker data)

Every figure below is an **explicit hypothesis**, not a measured cost. It stays hypothetical
until real Pepperstone fill data exists. No cost view alters the raw authoritative outcome; each
is a derived research view.

## Pip convention
**XAUUSD: 1 pip = $0.10** (pips = USD price distance × 10). Project-wide, unchanged.

## Per-event application

| Event | BASE_COST | STRESSED_COST | Rationale |
|---|---|---|---|
| Each **entry fill** (per filled leg) | spread 1.5p + slippage 0.5p = **2.0p** | spread 3.0p + slippage 1.5p = **4.5p** | crossing the spread on entry + modest fill slippage |
| Each **partial exit** | spread 1.5p + slippage 0.5p = **2.0p** | 3.0p + 1.5p = **4.5p** | crossing the spread again on each scale-out |
| **Final exit** | counted as a partial exit (2.0p) | 4.5p | same spread crossing |
| **Break-even scratch** | counted as an exit (2.0p) | 4.5p | a scratch is still a market exit that crosses the spread |
| **Stopped leg** | counted as an exit (2.0p) | 4.5p | stop-out crosses the spread (worse in STRESSED) |
| **Unfilled leg** | **0** | **0** | never entered → no cost |
| **Runner still open** | **0 realized** (cost applies only when it eventually exits) | 0 realized | unrealized is shown pre-cost; cost accrues at the future exit |

Charge model (deterministic): `cost_pips = (spread + slippage) × (n_fills + n_exits)`, where
`n_exits` = partial exits + final/scratch/stop closes. Feed sensitivity is separate (a ±$3 / 30-pip
level shift, not a spread), applied only to touch/graze outcomes and reported alongside the
second-feed divergence records.

## Worked example — 3-leg LONG campaign, one partial close, one scratch

Setup: zone 4007–4019, 3 equal legs (⅓ unit each). Suppose **2 legs fill** (near 4019, mid 4013;
far 4007 never trades). Management: "tp 1 now" banks 50% of open; later "sl to entry" → the
runner scratches at breakeven. Raw strict result (illustrative): **realized = +9.95 pips/unit**,
runner scratched (0 further), far leg unfilled.

Event count for costing:
- entry fills = **2** (near, mid); far leg unfilled → 0 cost.
- exits = **2** (one TP1 partial close + one BE scratch of the runner).

**BASE_COST:** cost = (1.5 + 0.5) × (2 fills + 2 exits) = 2.0 × 4 = **8.0 pips**.
→ realized_after_cost = 9.95 − 8.0 = **+1.95 pips/unit**.

**STRESSED_COST:** cost = (3.0 + 1.5) × 4 = 4.5 × 4 = **18.0 pips**.
→ realized_after_cost = 9.95 − 18.0 = **−8.05 pips/unit**.

**RAW_SHADOW:** **+9.95 pips/unit** (untouched authoritative outcome).

**FEED_SENSITIVITY:** raw +9.95 retained; flags that the TP1 touch and the BE scratch each sat
within the $3 cross-feed band, so on another feed the scratch could have missed or the fills
differed — see the SECOND_FEED_DIVERGENCE record.

Interpretation (honest): this single campaign spans **+9.95 → +1.95 → −8.05 pips/unit** across the
cost brackets — the spread of subscriber reality that only real fills at n≥15 can collapse. The
brackets are held fixed (no tuning) unless a mathematical/unit inconsistency is found; they remain
hypothetical until measured broker data exists.
