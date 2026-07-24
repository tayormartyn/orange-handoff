# Batch 002 — Option A (no-Worker-change) Tracking + Post-Setup Verification Checklist

**Mode: OPTION A CONFIRMATION / SETUP TRACKING ONLY.** Claude changes nothing here. No TradingView alert
touched, no Worker deploy, no R2, no broker/cTrader/QST, no permit/lease/order, no gate change. **No webhook
URL / secret path printed.** `NOT_INTEGRATION_READY` unchanged.

## Selection recorded

**Martyn selected Option A (2026-07-10):** no Worker change; existing **pure logging-only** Worker path
only; **local offline whitelist filtering** for `A LONG` / `A SHORT`; **time-boxed** ANY_ALERT duplicate
only. Reference: `BATCH_002_DIRECTIONAL_A_FALLBACK_PLAN.md`, `BATCH_002_LOW_NOISE_MIRROR_SETUP_CHECKLIST.md`.

**Martyn will manually create (duplicate-first, webhook into TradingView only):**
- `LIVE008_CHOCH_UP_MIRROR_BATCH002`  → discrete, main pure path
- `LIVE009_CHOCH_DOWN_MIRROR_BATCH002` → discrete, main pure path
- `LIVE010_SWEEP_HIGH_MIRROR_BATCH002` → discrete, main pure path
- `LIVE011_SWEEP_LOW_MIRROR_BATCH002`  → discrete, main pure path
- `LIVE012_ANY_ALERT_TIMEBOX_A_ONLY_BATCH002` → time-boxed, main pure path, A-only via local filter

**Will NOT create:** `LIVE006_A_LONG_MIRROR_BATCH002`, `LIVE007_A_SHORT_MIRROR_BATCH002`, any permanent
ANY_ALERT mirror, Engulfing mirrors, any broker/order/execution alert.

**Status: AWAITING SETUP.** Claude will run the verification below **after** Martyn confirms creation.

---

## Post-setup verification checklist (Claude runs this when notified)

### 1. Confirm the five mirror names
- [ ] Exactly these five exist as **duplicates**: LIVE008 / LIVE009 / LIVE010 / LIVE011 / LIVE012 (names
      matching above). No LIVE006 / LIVE007; no permanent ANY_ALERT; no Engulfing/broker mirrors.

### 2. Confirm originals remain untouched
- [ ] Sources `LIVE001_CHOCH_UP_XAUUSD_3M`, `LIVE001_CHOCH_DOWN_XAUUSD_3M`, `LIVE001_SWEEP_HIGH_XAUUSD_3M`,
      `LIVE001_SWEEP_LOW_XAUUSD_3M`, `LIVE001_ANY_ALERT_XAUUSD_3M` **not edited/renamed** (duplicate-first).
      Claude never touches TradingView; this is Martyn-attested.

### 3. Confirm LIVE012 is time-boxed
- [ ] LIVE012 is armed **only for a short, agreed observation window** (hours, not days) and will be
      **disabled/deleted immediately after**. It is **not** left running as a permanent flood.

### 4. Confirm A LONG / A SHORT are extracted LOCALLY only
- [ ] The A-directional signal is obtained **only** by an **offline whitelist filter** over the window's
      captured objects — a pure `is_directional_A(raw_text)` accepting only `"A LONG"` / `"A SHORT"`. No
      Worker-side filtering; the Worker stays pure logging-only and lossless.

### 5. Confirm ANY_ALERT noise is NOT promoted to candidates
- [ ] During processing, everything from LIVE012 that is **not** `A LONG` / `A SHORT` (Engulfing, BPR, and
      any CHoCH/Sweep echoes) is **ignored** — never fed to the detector, never journalled, never enqueued.
      Structure/sweep events come only from the clean discrete mirrors (LIVE008–LIVE011).

### 6. Confirm Worker remains pure logging-only
- [ ] Worker src sha256 == baseline `30bdc54d…`; `__verify_list__` / any filter branch **absent**; no deploy
      performed for Batch 002 setup. (Checked read-only, locally.)

### 7. Confirm no broker/execution path exists
- [ ] No broker/cTrader/QST connection; no permit/lease/order; gates `MODE=PAPER`, `LISTENER_MODE=PREVIEW`,
      `EXECUTION_ENABLED=False`, `CTRADER_EXECUTION_ENABLED=False`; no order/route/lot/account/risk field
      anywhere in the pipeline outputs.

### After the window (only when LIVE012 is disabled)
- [ ] Read-only R2 verification (temporary token-gated read branch → **revert to pure logging-only**),
      then local A-only filter → import that session's XAUUSD 1m OHLC → classifier → detector → outcome
      matcher → scorer → Farouk Campaign State Machine v0.1 → enqueue any `WATCH_ONLY` / `SHADOW_CANDIDATE_*`
      into Batch 002. Observation-only.

---

## 8. Exact phrase to send when LIVE012 is ARMED

```
LIVE012 ARMED — Batch 002 A-only time-box OPEN
```
(Optionally add the UTC start time, e.g. `— open 2026-07-10T14:00Z`.) On this, Claude notes the window start;
**Claude does not check R2 while the window is open** unless you ask.

## 9. Exact phrase to send when LIVE012 is DISABLED

```
LIVE012 DISABLED — Batch 002 A-only time-box CLOSED
```
(Optionally add the UTC end time.) On this, Claude runs the read-only R2 verification + local A-only filter +
the offline pipeline.

---

## Guardrails (unchanged)

Capture/observation-only; duplicate-first; originals untouched; Worker stays pure logging-only (no deploy);
R2 read only after the window (temp branch → revert); local A-only filter; no broker/order/execution/route/
account/risk/lot field; no permit/lease/order; webhook secret never printed; gates
`PAPER/PREVIEW/False/False`; Telegram PREVIEW listener PID 16608 left running; `NOT_INTEGRATION_READY`
unchanged. **Nothing here is trade-ready.**
