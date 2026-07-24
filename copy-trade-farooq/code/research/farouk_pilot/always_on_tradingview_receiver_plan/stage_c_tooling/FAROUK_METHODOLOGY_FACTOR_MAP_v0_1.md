# Farouk Methodology Factor Map v0.1

**Offline, observation-only.** Maps the documented Farouk decision factors to what our pipeline can
currently see. Sourced from the repo methodology corpus (paths cited). **Descriptive; authorises
nothing.** `NOT_INTEGRATION_READY` unchanged.

> Corpus caveat: nearly every geometric/numeric threshold (displacement magnitude, FVG size/fill, BPR
> tolerance, OB tap-count, **grade formula**, confluence count, session timezone) is explicitly
> **BLOCKED/UNKNOWN** in the corpus and marked *"do NOT invent."* The scorer therefore treats these as
> missing evidence, never as satisfied.

| Factor | Source / training basis | Required evidence | Positive signal | Negative signal | Missing-evidence handling | Available from our pipeline now? |
|---|---|---|---|---|---|---|
| **Session context** | `FAROUK_METHODOLOGY_SPEC_v0.2.1.md` §2; `FAROUK_LEVEL_CONSTRUCTION_SPEC_v0.2.md` §B; rule ledger R-NY-1330; `FAROUK_GUARD_CATALOG` G_SESSION_WINDOW_KNOWN / G_TZ_UNRESOLVED | Candle time in a known session (London 08:00Z, NY 13:30–15:00Z); Asia H/L as liquidity | In-session, aligned with session narrative | Timezone unresolved → guard BLOCKED | **null** → missing (we lack a validated TZ mapping) | ❌ no (TZ unresolved) |
| **Liquidity sweep** | `FAROUK_LEVEL_CONSTRUCTION_SPEC_v0.2.md` §B; `SETUP_FAMILY_SPECIFICATIONS` POI_SWEEP_REVERSAL; guards G_WICK_BREACH/G_CLOSE_BACK_INSIDE/G_BODY_CLOSE_BEYOND | Wick breaks a level then closes back inside | Sweep-into-POI then reversal | Body close beyond = a break, **veto** (not a sweep) | Alert gives SWEEP_HIGH/LOW type but not the wick/close geometry | ⚠️ partial (event type only, not geometry) |
| **Market structure (BOS/CHoCH)** | rule ledger R-BOS-CANDLECLOSE / R-CHOCH-NONUNIVERSAL / R-CONFLUENCE-ORDER; `SPEC` §6; `LEVEL_CONSTRUCTION` §E | BOS = close beyond level; CHoCH is *a* confirmation, not universally required | Aligned BOS/CHoCH on the right TF | CHoCH absent where required; wick-only "break" | CHoCH type captured; BOS/displacement close not captured | ⚠️ partial (CHoCH type only) |
| **Displacement** | rule ledger R-DISPLACEMENT; `SPEC` OB Quality Model (`displacement_strength`) | Strong impulsive close breaking levels | Big impulse → strong OB | Lazy move → weak OB | **BLOCKED_BY_THRESHOLD** (no numeric size); not observable | ❌ no |
| **Order block (OB)** | `LEVEL_CONSTRUCTION` §C; `SPEC` OB Quality Model; `SETUP_FAMILY_SPECIFICATIONS` STRONG_OB_REVERSAL/SCOB | Last opposing candle before impulse; first-tap; trend-aligned | Fresh, sweep→displacement→FVG, BPR overlap | Mitigated/"spent"/multiply-tapped; against-trend | Not captured by current alerts | ❌ no |
| **FVG** | `LEVEL_CONSTRUCTION` §D; `SETUP_FAMILY_SPECIFICATIONS` TREND_CONTINUATION; `SPEC` §1,§3 | 3-candle gap geometry; unfilled | HTF FVG unfilled, gating continuation | Filled FVG = invalid | Gap size/fill threshold UNKNOWN; not captured | ❌ no |
| **BPR** | `LEVEL_CONSTRUCTION` §D; `SPEC` §4 + OB Quality (`bpr_overlap`); STRONG_OB_REVERSAL bonus | Bullish+bearish FVG overlap at same price | Overlap zone ("A+ setup") | — (bonus, not required) | We capture BPR **tapped/formed** event type only; overlap geometry unknown | ⚠️ partial (event type only) |
| **Grade A / A+ / A+++** | `SPEC` §6; rule ledger R-AGRADES; FP-INDICATOR-005 ALERT_INTERFACE_REGISTER; FP-INDICATOR-006 blockers | Indicator emits "A+++ setup" / "A+ or better" | Higher grade = more confluence (per indicator) | — | **Grade formula NOT exposed** ("do NOT invent"; A+++ ≠ executable). Literal-only if present in raw | ⚠️ literal-only (0 seen so far) |
| **Direction alignment / HTF bias** | `SPEC` §1 + OB Quality (`trend_alignment`); `LEVEL_CONSTRUCTION` §C; guards G_BIAS_ALIGNED/G_BIAS_FLIP | HTF (4H/Daily) bias; trend-EMA alignment | LTF aligned with HTF & trend-EMA | Bias flip against setup (degrade) | We can check *internal* sequence bias alignment only; no HTF/EMA feed | ⚠️ partial (intra-sequence only) |
| **Contradictory signals / invalidation** | `SETUP_FAMILY_SPECIFICATIONS` invalidation fields; `SPEC` §8; R-STRONGWEAK; CONTRADICTION_ADJUDICATION | Close beyond OB/against structure; reclaim of swept extreme | — | Opposite-direction cluster; invalidation close | We detect contradictory clusters / opposite-A → **disqualifier** | ✅ yes (cluster/opposite detection) |
| **Telegram / Discord confirmation** | `ALERT_INTEGRATION_BOUNDARY_v0.1.md`; FP-INDICATOR-005 INTEGRATION_BOUNDARY | — | — | — | **Not a methodology confluence factor in the corpus** — Discord is the teaching source; TG/Discord are alert *delivery* targets only. Tracked but unweighted | ❌ n/a (delivery, not decision) |
| **Outcome evidence** | our `outcome_matcher_v0_1` / shadow journal | Price excursion vs direction_hint | Favourable follow-through | Unfavourable / adverse-heat | From matcher (or null if unmatched) | ✅ yes (when OHLC imported) |

## Summary of availability

- **Available:** contradiction detection, outcome evidence; **partial:** liquidity/structure/BPR (event
  type but not geometry), direction alignment (intra-sequence only), grade (literal-only, none seen).
- **Missing entirely:** session context (TZ unresolved), displacement, FVG, order block — the four
  `REQUIRED_CONTEXT` factors. Because these are absent, the scorer **cannot** award the top label; it
  caps at `SHADOW_CANDIDATE_MEDIUM` and lists them in `missing_evidence`.

This map is why nothing is trade-ready: our alert-only pipeline sees a small slice of the documented
methodology, and the highest-weight confluence factors (OB/FVG/displacement/session) are exactly the ones
we cannot yet observe.
