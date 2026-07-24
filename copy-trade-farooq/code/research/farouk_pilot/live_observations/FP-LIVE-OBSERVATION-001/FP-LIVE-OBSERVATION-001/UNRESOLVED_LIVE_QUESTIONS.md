# FP-LIVE-OBSERVATION-001 — UNRESOLVED LIVE QUESTIONS (after first set)

## Resolved / narrowed by this set
- **Any alert() runtime payload** — captured verbatim (plain text `Farouks Playbook: <event> on XAUUSD 3`). ✔
- **Named vs Any alert() payloads** — named = "Sweep low"; Any alert() = richer with direction/symbol. ✔
- **Bar-close vs intrabar timing** — all firings on 3-minute boundaries (bar close). ✔ (low sample)
- **Duplicate behaviour** — no per-bar repeats; named+Any echo is dedupable. ✔ (low sample)
- **Config tuple / timezone** — captured; timezone field = Europe/Berlin (current config, not a default). ✔

## Still unresolved
- **A / A+ / A+++ grade formula & meaning** — "A LONG"/"A SHORT" observed, but what "A" encodes, and whether an
  A+++ ever fires, is unknown. No grade change observed (insufficient sample).
- **Intrabar repaint at the firing instant** — post-alert state is stable, but no at-firing capture exists to
  prove markers don't repaint before close.
- **Full config-tuple parameter identities** — only ~7 tokens map to known settings; the rest are UNMAPPED
  (e.g. is 9/17/15/22 the London/US session hours? unproven).
- **Sweep-high / CHoCH up / CHoCH down / A+++ / A+ named conditions** — none fired in this window (no evidence).
- **Webhook payload** — not tested (no webhook configured, by design).
- **Cross-session consistency** — a single ~40-minute window; timing/dedup/repaint need repetition.
- **Whether "A LONG" == the named-condition set** — the composite's relationship to the individual named
  conditions (does A LONG require sweep-low + engulfing together?) is inferred, not confirmed.

## Recommended next captures (to close the above)
1. A **continuous screen recording** spanning several candle closes (prove no intrabar repaint; confirm timing).
2. Sessions that produce **Sweep high, CHoCH up/down, and A+ / A+++** firings.
3. An at-firing capture where a **grade** appears, then +1/+5 re-checks (C7).
4. A settings capture scrolled to the ORDER BLOCK/LIQUIDITY + SESSIONS inputs to map the remaining tuple tokens.


---
# AFTER CONTINUATION SET 002
## Advanced this round
- **Bar-close timing** now has DIRECT VIDEO proof (toast at 06:24:00 exactly). ✔
- **Payload format** confirmed stable across two sets + a new event type (BPR tapped). ✔
- **Chart clock = UTC+1** confirmed on video (vs indicator field Europe/Berlin). ✔

## Still unresolved / newly noted
- **A+ / A+++** — STILL never observed (only A LONG / A SHORT composites). C7 blocked.
- **Sweep high, CHoCH up/down** — still never fired in any capture.
- **Intrabar marker repaint at firing** — recordings were alert-SETUP focused; no clean single-candle
  formation-to-close capture → C4 still partial.
- **Cross-session repetition** — all evidence is one trading day; timing/dedup need other days.
- **BPR tapped semantics** — new primitive; relationship to BPR-formed / mitigation not established.
- **"A LONG" without a paired same-bar primitive** (07:45) — how the composite is triggered standalone is unclear.
- **Config-tuple parameter identities** — still only ~7 of ~30 tokens mapped.

## Best next captures
1. A recording that **watches one candle form and close with the chart unobstructed** (settle C4).
2. Sessions producing **Sweep high, CHoCH, and especially A+ / A+++** (settle C7).
3. Multi-day repetition of the timing/dedup behaviour.


---
# AFTER CONTINUATION SET 003 (+ set 004 nil-return)
## Advanced by set 003
- **A+ now observed** (named "A+ or better" + composite "A+ SHORT", 08:24/08:27). ✔
- **CHoCH up now observed** (named "CHoCH up" + composite "CHoCH UP", 08:42). ✔
- Composite grade token is explicit ("A" vs "A+"); format `Farouks Playbook: <grade> <dir> on XAUUSD 3` stable.

## Still unresolved
- **A+++** — never observed (condition armed, not met).
- **Sweep high, CHoCH down, BPR formed** — never fired.
- **Grade formula/threshold** — what distinguishes A vs A+ (vs A+++) is unknown; no numeric basis captured.
- **Grade stability over time** — no +1/+5 re-check of whether an A+ downgrades/changes after the bar.
- **Intrabar marker repaint at firing** — still no unobstructed single-candle formation-to-close capture (C4).
- **Cross-session/multi-day repetition** — all 22 events are one trading day.
- **Config-tuple identities** — still only ~7 of ~30 tokens mapped.

## Set 004 status
No files were added after set 003 (nil-return); nothing to append. See CONTINUATION_CAPTURE_004_ADDENDUM.md.

## Best next captures
1. Unobstructed recording across candle closes (settle C4).
2. Sessions producing A+++, Sweep high, CHoCH down, BPR formed.
3. A grade that is then re-checked at +1/+5 (grade stability, C7).
