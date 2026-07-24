# FAROUK METHODOLOGY SPECIFICATION — v0.2

**Status: DRAFT / EVIDENCE-GRADED. Not a strategy, not a rule set, not executable.** (v0.1 preserved separately.)
v0.2 adds the three **official documents** — FP-EDU-002 *Farouk's Playbook* (`sa-4cb77d9d6b13478a`),
FP-EDU-003 *Whale Room Trading Guide* (`sa-8b0a95608f41b5e4`), FP-EDU-004 *Strong vs Weak Order Blocks*
(`sa-c005bffefcc3a90e`) — as explicit **teaching claims**, kept distinct from **observed campaign
evidence** (C001 win, C002 loss, C003 win) and from the FP-EDU-001 livestream. Tags:

- **[DOC]** explicit documented teaching (a SourceClaim — *not* proof it is followed/true)
- **[OBS]** observed in ≥1 campaign · **[STRONG]** = [DOC]+[OBS] consistent
- **[PARTIAL]** · **[HYP]** untested hypothesis · **[CONTRA]** contradicted/inconsistent · **[OPEN]** unresolved

A documented teaching statement is a **SourceClaim**; it is **not** promoted to a confirmed rule unless
campaign evidence supports it. No detector code. Provenance screenshot for the docs is **[OPEN]** (pending).

---

## 1. Higher-timeframe context
- **[DOC]** HTF FVGs/zones outrank LTF ("4H/Daily > 5m/15m", Playbook p3); a **Daily FVG** and daily-high
  gate continuation ("1h close above the daily bearish FVG", FP-EDU-001/C003). **[OBS]** wins (C001, C003)
  entered at an HTF level; the loss (C002) entered far from one → **[STRONG]** directionally.

## 2. Session liquidity
- **[DOC]** Liquidity sits at Asia High/Low, PDH/PDL, equal highs/lows, swing points, round numbers
  (Playbook p6). **[DOC]** **Asia-session fakeout** (Playbook p9): a failed close beyond the Asia high +
  a first lower low = bearish trap → short; the reverse (Asia-low fakeout → bullish trap) also holds.
  **[OBS]** C003 = Asia-**low** fakeout → bullish rebound (win); panels show `Asia break HIGH/LOW` in all
  three. **[HYP]** "break without displacement ⇒ trap" is **not promoted** (only C002's unverified review).

## 3. Level construction
See `FAROUK_LEVEL_CONSTRUCTION_SPEC_v0.2.md`. **[DOC]** precise definitions now exist for FVG (3-candle
imbalance), **BPR** (overlap of opposing FVGs), **OB** (last opposing candle before displacement), and
liquidity sweep (**wick through a level then close back inside**).

## 4. Setup families
- **[STRONG]** **OB retest** after a break (Playbook p6; C001/C003 wins).
- **[DOC]/[PARTIAL]** **OB + FVG** confluence and **BPR** setups (Playbook p5; C003 uses OB+FVG explicitly;
  BPR itself **[OPEN]** in campaigns).
- **[DOC]/[PARTIAL]** **FVG continuation** state machine: bottom → FVG → **close above** → retrace/fill →
  continue to the next OB (Playbook p4; matches C003's path toward the Daily FVG).
- **[DOC]** A+ **Asia-High-break long** (FP-EDU-001) — taught, unexemplified in these campaigns.

## 5. Entry triggers
- **[DOC]** Enter on the **OB/FVG/BPR retest**, on the **CLOSE** of the trigger candle ("never enter live",
  Playbook p11). **[DOC]** Top-down **5m structure → 3m MSS/BOS → 1m trigger** (Playbook p10-11).
- **[DOC]/[OBS]** **Layered entries** ("3-Point Entry": Entry1/2/3, one **shared stop**, **average** entry;
  WR p10). **[OBS]** C003 shows an initial + deeper entry with "close worst, hold best"; a full 3-entry /
  shared-stop / average-BE is **[PARTIAL]** (not all visible). **[DOC]** hard cap: **max 3 entries — "never
  add a 4th entry to a loser"**.

## 6. Confirmation
- **[DOC]** A named **reversal candle** (hammer/shooting-star/doji/star/tweezer) or **engulfing** (body
  **≥2×** prior, Playbook p7-8) at the level; strongest **after a liquidity sweep**.
- **[DOC]** **CHoCH / MSS / BOS** as structure confirmation. **[OBS]** CHoCH is *a* confirmation but **not**
  consistently required (C003 win had panel `CHoCH ×`) → **[PARTIAL]**.
- **[CONTRA]** The Playbook's own scoring is **internally inconsistent**: a **6/6** top-down stack rule
  (p11) coexists with a **7-item** pre-trade checklist (p13) and the **A+++…C** letter grades (p12) — three
  non-reconciled frameworks. *(Task's "6/6 vs 6/8": actually 6/6 vs a 7-item checklist vs letter grades.)*

## 7. Vetoes
- **[DOC]** No trade if the required session break/fakeout is absent (FP-EDU-001 EDU-C-002; Playbook Asia
  setup). **[DOC]/[OBS]** Avoid a **mitigated OB** ("already tapped", "spent"; C003 spoken: "don't enter
  another long here at this OB, already mitigated"). **[DOC]** Skip **weak OBs** (see §OB Quality Model).
- **[HYP]** H-VETO-001 (Asia break without displacement/FVG/CHoCH/OB-retest = trap) — C002, **unverified**.

## 8. Structural invalidation
- **[DOC]/[STRONG]** Stop **beyond structure** (below swing low for buys / above swing high for sells;
  above the failed Asia high for the fakeout short); **never move the stop further away** (WR p9).
  **[OBS]** C001 SL 4140 at supply top; C003 SL 4010 below the buy zone.

## 9. Target selection
- **[DOC]/[STRONG]** Targets at **opposing/structural liquidity** and staged **TP1/TP2/TP3** (WR p4/p8;
  Playbook targets = "next liquidity"). **[OBS]** C003 → Daily FVG + opposing 4070–80 sell zone; C001/C002
  TP ladders at structural levels.

## 10. Campaign management
- **[STRONG]** **TP1 → move stop to breakeven** — taught (**BE at +50 pips**, WR p3/p10) and observed in
  all three campaigns; C003 spoken "**normally I move my stoploss to entry at 50–60 pips**" matches the
  +50-pip rule.
- **[DOC]/[PARTIAL]** Partial-exit schedules: **Conservative 50/30/20** vs **Advanced 30/30 + runner**
  (WR p8). **[OBS]** C003 scaled 50% then 75% out with a runner (closer to the Advanced style).
- **[DOC]** BE at **+50 pips from the average** for layered entries (WR p10).

## 11. Recovery / re-entry
- **[DOC]/[OBS]** **Layering to manage drawdown** ("add a 2nd BUY … both break even at the average", WR p3;
  "3-Point Entry", p10) — a *planned* averaging protocol (C003). Distinct from a **recovery trade after a
  stop-out** (FP-EDU-001 EDU-C-010; C002-LEG-B). **[DOC]** guardrail: **max 3, never add to a loser**.
- **[HYP]** H-MGMT-001 (fast TP1 biases re-entry) — C002.

## 12. Data gaps
- **[OPEN]** No **market data** → FVG/OB/displacement/sweep/R:R claims not price-verified.
- **[OPEN]** **Timezones** (edu platform UTC+2; Discord unknown); **C003 4027.37 provenance**; **currency**
  of blue result values.
- **[CONTRA]** **Risk figures**: docs teach **1–2% per trade** / "max 2% lot" (WR p7/p10; Playbook p13).
  The project's **LOCKED 1.0% campaign-wide cap is retained and NOT replaced** by any document figure.
- **[OPEN]** **Provenance screenshot** (Farouk-as-publisher) not supplied — authorship rests on document
  branding/footers only (suggestive, not proven). Provenance ≠ redistribution permission.
- **[OPEN]** "displacement" absent from the FP-EDU-001 transcript; external-review discrepancies (C002).

---

## ORDER BLOCK QUALITY MODEL
Separates, per feature, the **official teaching claim**, **observed campaign evidence**, the **current
inference**, the **unresolved threshold**, and the **required future evidence**. **No numerical thresholds
are assigned.** Full machine-readable version in
`comparisons/FP-OFFICIAL-DOCS-vs-CAMPAIGNS-001-002-003.json → order_block_quality_model`.

| Feature | Official teaching (FP-EDU-004) | Observed campaign evidence | Current inference | Unresolved threshold | Required future evidence |
|---|---|---|---|---|---|
| `sweep_present` | strong OB sweeps liquidity first | C003 Asia-low sweep before OB (supports) | strong marker | how definitively swept | tick data: wick-through + close-back-inside |
| `displacement_strength` | big impulse (strong) vs lazy (weak) | NOT_OBSERVABLE; "displacement" never spoken | central to quality | what magnitude qualifies | impulse vs ATR/range on ticks |
| `fvg_created` | strong OB leaves an FVG | C003 references FVG/Daily FVG (partial) | separates strong/weak | FVG size that counts | detect 3-candle gap after OB |
| `ob_touch_count` | first tap strongest; tapped = weak | C003 "already mitigated" veto (supports) | prior taps degrade OB | taps = "spent" | count retests from history |
| `ob_fresh` | unmitigated = strong | C003 mitigated-veto (supports) | freshness ~ strength | definition of "mitigated" | price-return check |
| `trend_alignment` | above Trend EMA (long)/below (short) | C001/C003 in-context wins; C002 far-off loss | alignment favours quality | which EMA/bias | define + compute Trend EMA |
| `bpr_overlap` | OB∈BPR = strongest confluence (bonus) | NOT_OBSERVABLE in campaigns | bonus, not required | overlap tolerance | detect BPR + overlap |
| `market_chop_state` | weak OB forms in chop/range | NOT_OBSERVABLE | chop degrades quality | chop vs trend classifier | regime classifier on price |

**Official teaching** (strong): *sweep → displacement → leaves an FVG*, fresh/first-tap, aligned with the
Trend EMA, BPR overlap = bonus. **Observed evidence** so far only corroborates *sweep + fresh/mitigated +
FVG-presence + trend-context*; **displacement, BPR overlap, and chop-state are not yet observable**.
**Required future evidence:** tick/OHLC for all campaigns to measure displacement, FVG geometry, tap
counts and regime — **before any threshold is set**.
