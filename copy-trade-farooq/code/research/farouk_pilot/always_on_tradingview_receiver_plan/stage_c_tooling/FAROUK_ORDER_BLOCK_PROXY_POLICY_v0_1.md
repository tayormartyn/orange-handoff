# Farouk Order-Block Proxy Policy v0.1

**Offline, observation-only.** Defines what the OB proxy detector may and may not do. **It never claims a
confirmed Farouk order block.** `NOT_INTEGRATION_READY` unchanged.

## What the corpus says about order blocks

- **Definition:** an OB is the **last opposing candle before a strong impulsive (displacement) move**;
  the **retest** of the OB is the entry; SL beyond the OB body; target the prior swing.
  (`specifications/FAROUK_LEVEL_CONSTRUCTION_SPEC_v0.2.md` §C.)
- **Strong OB (quality model):** sweep → **displacement** → leaves an **FVG**, **first/fresh tap**, aligned
  with the **Trend EMA / HTF bias**, **BPR overlap** = bonus.
  (`specifications/FAROUK_METHODOLOGY_SPEC_v0.2.1.md` — ORDER BLOCK QUALITY MODEL.)
- **Weak OB:** lazy impulse / no FVG / **mitigated or multiply-tapped** (spent) / against-trend or chop /
  isolated. First tap strongest; prior taps degrade.
- **Support:** OB retest is Farouk's **highest-supported entry family** (C001/C003 wins).

## What is CONFIRMED vs BLOCKED/UNKNOWN

| Aspect | Status |
|---|---|
| OB = last opposing candle before displacement | ✅ documented (qualitative) |
| Retest/first-tap strongest; mitigated degrades | ✅ documented (qualitative) |
| **Displacement magnitude threshold** | ❌ UNKNOWN ("do NOT invent") |
| **Mitigation / tap-count numeric rule** | ❌ UNKNOWN |
| **FVG size/fill for "strong OB"** | ❌ UNKNOWN |
| **Trend-EMA / HTF bias definition** | ❌ UNKNOWN (no SMC rule) |
| **BPR overlap tolerance** | ❌ UNKNOWN |

## What v0.1 is ALLOWED to detect (proxy only)

- The **last opposite-colour candle immediately before a displacement PROXY** (displacement proxy =
  range ≥ 2.0× rolling ATR, the documented default from the chart extractor).
  - LONG context → last **bearish** candle before an upward displacement proxy.
  - SHORT context → last **bullish** candle before a downward displacement proxy.
- Descriptive **zone bounds** = the OB proxy candle **body** (max/min of open/close).
- Whether price later **re-entered** the zone (mitigation proxy).
- Distance (minutes) from the candidate anchor.

## What v0.1 MUST NOT do

- ❌ Claim a **confirmed Farouk order block** (output is `order_block_proxy_found`, never a real OB).
- ❌ Emit an **entry zone for trading**, SL/TP, size, or any actionable instruction. Zone bounds are
  **descriptive evidence only**.
- ❌ Assign confidence above **LOW**.
- ❌ Invent the UNKNOWN thresholds (mitigation count, displacement size, FVG fill).
- ❌ Assert strong-vs-weak OB grading (needs FVG + first-tap + HTF, all proxy/blocked).

## Human-review requirement

Every OB proxy record carries `requires_human_review=true` and `NEEDS_HUMAN_REVIEW`. No OB proxy may
inform any decision beyond the shadow journal without a human confirming it against the chart.

## Status

Policy v0.1 — proxy only. Feeds the methodology scorer **only as low-confidence proxy evidence** and
enables no execution. `NOT_INTEGRATION_READY` unchanged.
