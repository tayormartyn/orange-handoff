# FP-LIVE-OBSERVATION-001 — PAYLOAD OBSERVATIONS (first set)

## Exact runtime messages (verbatim, from tooltips + log)
**Named condition** (LIVE001_SWEEP_LOW_XAUUSD_3M):
- Tooltip message: **"Sweep low"** (plain — the alertcondition title). Log-list label: **"Liquidity Sweep low"**
  (the alert's NAME). No direction, no symbol in the payload text.

**Any alert() function call** (LIVE001_ANY_ALERT_XAUUSD_3M) — script-generated, richer:
- "Farouks Playbook: **Sweep low (bullish)** on XAUUSD"
- "Farouks Playbook: **A LONG** on XAUUSD 3"
- "Farouks Playbook: **Bullish Engulfing** on XAUUSD 3"
- "Farouks Playbook: **Bearish Engulfing** on XAUUSD 3"
- "Farouks Playbook: **A SHORT** on XAUUSD 3"

### Payload shape
Any alert() = `Farouks Playbook: <EVENT[ (direction)]> on XAUUSD[ 3]` — plain text, prefixed with the indicator
name, includes the event, sometimes a direction, the symbol, and (mostly) the timeframe "3". **No JSON, no
`{{placeholders}}`** — but deterministic and easily parseable by a fixed prefix + event vocabulary.

## Named vs Any alert() (same event, two mechanisms)
For the 06:33 sweep low: named payload = "Sweep low"; Any alert() payload = "Farouks Playbook: Sweep low
(bullish) on XAUUSD". → The Any alert() carries **more** (direction + symbol); the named carries only the
condition title. Both are attributable to the same bar close.

## Configuration tuple (shown in Any alert() tooltips — item 11)
`Farouk's Playbook — Smart Money Suite (Small, 50, 0.15, 0.1, 0.5, 0.3, 5, 50, 0.3, 0.2, 15, 1.5, 2.5, 20,
Default, 2, 6, Europe/Berlin, 1, Solid, 9, 17, 15, 22, 2, 50, 5, 30, bottom_right, 10, 0.1): Any alert() function call`
(identical on the Sweep-low and A-LONG tooltips.)

### Tokens that MATCH known named settings (FP-INDICATOR-005/006 registers)
- `Small` → **Chart label size** (note: 005/006 showed *Tiny*; here *Small* — a CURRENT_VISIBLE_CONFIG difference, NOT a default).
- `50` → **FVG lookback (bars)**; `0.15` → **TZ/ST level tolerance (xATR)**; `0.5` → **Min FVG size (xATR)**;
  `5` → **CHoCH pivot length**; `0.2` → **Min BPR overlap (xATR)**; `10` → **Max zones kept per type**.
- `Europe/Berlin` → **timezone field** (see item 12 below).
- `Default` → a mode value (e.g. OB-display "Default"), **NOT** evidence of a factory reset.
- `bottom_right` → panel position; `Solid` → a line style.

### Tokens NOT identifiable (positional inference unsafe)
`0.1, 0.3, 15, 1.5, 2.5, 20, 2, 6, 1, 9, 17, 15, 22, 2, 50, 5, 30, 0.1` — recorded verbatim; their parameter
identity is **UNMAPPED** (WEAK_INFERENCE only; some of 9/17/15/22 could be session hours but this is not proven).

## Item 12 — Europe/Berlin mapping (not a factory default)
`Europe/Berlin` is the indicator's **timezone input** = the current on-screen value. In July it is UTC+2 (DST),
consistent with the FP-INDICATOR-005/006 chart-TZ observations (UTC+1/UTC+2, user-local). It is recorded as
**CURRENT_VISIBLE_CONFIG**; **no reset-to-default was demonstrated**, so it is NOT treated as a factory default.
The separate `Default` token in the tuple is a parameter value, not proof of a defaults state.


---
# CONTINUATION SET 002 — payload consistency
- New payloads confirm the format `Farouks Playbook: <event[ (direction)]> on XAUUSD[ 3]`:
  "A LONG on XAUUSD 3", "Sweep low (bullish) on XAUUSD" (no trailing 3, as in set 1), and the NEW
  "**BPR tapped** on XAUUSD 3".
- Config tuple UNCHANGED on all continuation tooltips (…Small, 50, 0.15, 0.1, 0.5, 0.3, 5, 50, 0.3, 0.2, 15,
  1.5, 2.5, 20, Default, 2, 6, **Europe/Berlin**, 1, Solid, 9, 17, 15, 22, 2, 50, 5, 30, bottom_right, 10, 0.1).
- No truncation observed; where a message would truncate it is recorded verbatim. No wording inferred from prior
  examples — each payload read from its own tooltip.


---
# CONTINUATION SET 003 — grade + CHoCH payloads (verbatim)
- Named: "A+ or better" (list "A+ or better setup"); "CHoCH up" (list "CHoCH up (bullish)").
- Any alert(): "Farouks Playbook: A+ SHORT on XAUUSD 3"; "Farouks Playbook: CHoCH UP on XAUUSD 3";
  "Farouks Playbook: Bearish Engulfing on XAUUSD 3".
- Composite grade token now explicit: set-1 "A LONG"/"A SHORT" -> set-3 "A+ SHORT". Format =
  `Farouks Playbook: <GRADE?> <DIRECTION> on XAUUSD 3`. Grade values seen: {A, A+}. A+++ NOT seen.
- Config tuple UNCHANGED; no truncation; each payload read from its own tooltip.
