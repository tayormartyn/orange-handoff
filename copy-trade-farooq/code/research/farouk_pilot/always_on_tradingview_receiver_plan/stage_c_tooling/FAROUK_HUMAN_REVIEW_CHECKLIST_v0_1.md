# Farouk Human Review Checklist v0.1

For each shadow candidate, open the chart at the anchor and answer every item. **This validates
EVIDENCE, not trades.** No item asks "should I trade" — the ceiling is observation-only.
`NOT_INTEGRATION_READY` unchanged.

## Checklist (per candidate)

1. **OB proxy visually credible?** Is the machine's order-block zone a real last-opposing-candle-before-
   impulse, or an artefact? → `order_block_review = CONFIRMED_FRESH / CONFIRMED_MITIGATED / DENIED / UNSURE`.
2. **OB already mitigated / spent?** Has price already returned into the zone (tapped/mitigated)? A spent
   OB is a *weak* signal. → note under order_block_review.
3. **FVG proxy meaningful or tiny/noisy?** Is the 3-candle gap a real imbalance or micro-noise?
   → `fvg_review = CONFIRMED / DENIED / UNSURE`.
4. **Displacement obvious or just volatility?** Was there a genuine impulsive move, or ordinary chop that
   happened to exceed the ATR proxy? → `displacement_review`.
5. **Sweep / CHoCH in meaningful structure?** Did the liquidity sweep / structure shift occur at a real
   level (Asia H/L, PDH/PDL, swing), or mid-range? → `liquidity_review`, `structure_review`.
6. **Direction aligned or contradicted?** Do the pieces point the same way as the alert's direction, or
   fight it (e.g. HTF against the hint)? → `htf_bias_review`, `structure_review`.
7. **Just ANY_ALERT noise?** Is this candidate really only high-frequency composite churn (Engulfing/A
   spam) rather than a setup? → if yes, lean `CONTEXT_ONLY` / `REJECT`.
8. **Telegram / Discord confirmation?** Did the Farouk channel actually flag this? (Integrity check —
   NOT a methodology confluence factor.) → `telegram_discord_context_review = CONFIRMED / NONE / NOT_CHECKED`.
9. **Session context known or unresolved?** Given the unresolved timezone, can you even place this in a
   real session? → `session_review = CONFIRMED / UNRESOLVED / UNSURE`.
10. **Hard disqualifiers?** Contradictory cluster, invalidation (close beyond OB/against structure),
    inside-range chop, body-close-beyond (not a sweep), mitigated OB relied upon? → `disqualifiers[]`.

## Scoring guidance (labels only — none trade-ready)

- Any hard disqualifier (item 10) → `REJECT`.
- Only noise / lone primitive (item 7) → `CONTEXT_ONLY`.
- Some real evidence but thin / unconfirmed → `WATCH` or `SHADOW_CANDIDATE_LOW`.
- Multiple CONFIRMED factors (real OB + FVG + displacement + aligned) but session/HTF/grade or outcome
  still weak → up to `SHADOW_CANDIDATE_MEDIUM`.
- `METHODOLOGY_ALIGNED_SHADOW` only if session CONFIRMED **and** a fresh CONFIRMED OB **and** aligned
  HTF **and** a favourable outcome — **still observation-only, still not permission to trade.**

## Reminder

Unfavourable outcome stays a strong negative. Missing Telegram/Discord stays missing evidence. A single
confirmed proxy can only *improve a shadow score* — it can never make a candidate trade-ready.
