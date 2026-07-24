# Batch 002 — Low-Noise Mirror Setup Checklist (for Martyn)

**Mode: BATCH 002 MIRROR SETUP PLAN ONLY — manual checklist for Martyn; Claude changes nothing.** No
TradingView alert touched by Claude, no Worker deploy, no R2, no broker/cTrader/QST, no permit/lease/order,
no gate change. **No webhook URL / secret path is printed anywhere in this doc.** `NOT_INTEGRATION_READY`
unchanged.

## Purpose

Create **capture-only duplicate mirror alerts** for the low-noise event types the detector needs, so the
next observation cycle can form sequence candidates:
`CHOCH_UP→A_LONG`, `CHOCH_DOWN→A_SHORT`, `SWEEP_LOW→CHOCH_UP→A_LONG`, `SWEEP_HIGH→CHOCH_DOWN→A_SHORT`
(and later `BPR_TAPPED→A_LONG/A_SHORT`).

## Golden rules (every mirror)

- **Duplicate-first**: use TradingView's **Duplicate/Clone** on the original, add the webhook to the
  **DUPLICATE only**. **Never open/edit/rename the original.**
- **Webhook target**: the existing logging-only Worker endpoint — copy it from your gitignored local file
  **`cloud_worker_dark/LOCAL_ONLY_GATE_F_WEBHOOK_URL.txt`** (the copy-proof bare URL) and paste it **into the
  TradingView webhook field ONLY**. **Do NOT paste it into chat, screenshots, or reports.**
- Alerts are **`alert()`-based** (indicator-defined message; not editable) → the webhook body is the
  indicator's raw text. That's expected: the Worker stores it as `INVALID_JSON` raw text. **No order /
  action / broker / lot / account field is possible or present** — it is plain text capture only.
- Keep **Notify-in-app ON**; tick **Webhook URL**; set expiry to **Open-ended** (or re-arm as needed).
- **Delete/disable the mirror after enough capture** (as done for H1/H2). Originals stay untouched.

## Source-condition confirmation (task 4)

Confirmed present in the local inventory (discrete Farouk per-type originals on **XAUUSD · Pepperstone ·
3m**):

| event | original alert (source to duplicate) | status |
|---|---|---|
| CHoCH up | `LIVE001_CHOCH_UP_XAUUSD_3M` | ✅ confirmed |
| CHoCH down | `LIVE001_CHOCH_DOWN_XAUUSD_3M` | ✅ confirmed (H2 mirrored it) |
| Sweep high | `LIVE001_SWEEP_HIGH_XAUUSD_3M` | ✅ confirmed |
| Sweep low | `LIVE001_SWEEP_LOW_XAUUSD_3M` | ✅ confirmed |
| **A LONG** | *(no discrete `LIVE001_A_LONG_*` in inventory)* | ⚠️ **UNCONFIRMED — confirm in TradingView first** |
| **A SHORT** | *(no discrete `LIVE001_A_SHORT_*` in inventory)* | ⚠️ **UNCONFIRMED — confirm in TradingView first** |

> ⚠️ **STOP / confirm before LIVE006 & LIVE007.** The `A LONG` / `A SHORT` raw texts were only ever captured
> via the `LIVE001_ANY_ALERT` flood; **no discrete A-directional original alert is recorded locally** (only
> `LIVE001_APLUS_XAUUSD_3M` exists on the A side). **Do not guess.** In TradingView, check whether the Farouk
> Playbook indicator exposes discrete **A LONG** and **A SHORT** conditions in the alert **Condition**
> dropdown:
> - **If yes** → create those two originals (or duplicate them if they already exist) and proceed with
>   LIVE006/LIVE007 below.
> - **If no** (A signals only fire via ANY_ALERT) → **tell Claude**; we will decide an alternative (e.g. a
>   single low-TTL A-only capture, or accept A via a filtered path) rather than re-introduce the noisy
>   ANY_ALERT. **These two are the sequence blocker, so resolving them is top priority.**

## Mirrors to create

For each: Duplicate the source → rename the COPY to the name below → add the webhook to the COPY → leave the
original untouched.

| # | duplicate name | source original | expected raw text (indicator-defined) | classifier event_type |
|---|---|---|---|---|
| LIVE006 | `LIVE006_A_LONG_MIRROR_BATCH002` | ⚠️ A LONG (confirm source first) | `Farouks Playbook: A LONG on XAUUSD 3` | `A_LONG` |
| LIVE007 | `LIVE007_A_SHORT_MIRROR_BATCH002` | ⚠️ A SHORT (confirm source first) | `Farouks Playbook: A SHORT on XAUUSD 3` | `A_SHORT` |
| LIVE008 | `LIVE008_CHOCH_UP_MIRROR_BATCH002` | `LIVE001_CHOCH_UP_XAUUSD_3M` | `Farouks Playbook: CHoCH UP on XAUUSD 3` | `CHOCH_UP` |
| LIVE009 | `LIVE009_CHOCH_DOWN_MIRROR_BATCH002` | `LIVE001_CHOCH_DOWN_XAUUSD_3M` | `Farouks Playbook: CHoCH DOWN on XAUUSD 3` | `CHOCH_DOWN` |
| LIVE010 | `LIVE010_SWEEP_HIGH_MIRROR_BATCH002` | `LIVE001_SWEEP_HIGH_XAUUSD_3M` | `Farouks Playbook: Sweep high (bearish) on XAUUSD` | `SWEEP_HIGH` |
| LIVE011 | `LIVE011_SWEEP_LOW_MIRROR_BATCH002` | `LIVE001_SWEEP_LOW_XAUUSD_3M` | `Farouks Playbook: Sweep low (bullish) on XAUUSD` | `SWEEP_LOW` |

Notes: Sweep raw texts carry `(bullish)`/`(bearish)` and **no trailing `3`** — that is expected (instrument
extracted, timeframe null). A / CHoCH texts end `on XAUUSD 3` (3-minute).

## Avoid

- **`LIVE001_ANY_ALERT_XAUUSD_3M`** — high-volume flood (~6.4 events/h; Engulfing + A noise). **Do not
  mirror.**
- **Engulfing (bull/bear)** — co-firing noise; the detector does not promote it. **Do not mirror.**

## Per-mirror completion checklist (tick each)

- [ ] Duplicated the correct source (original NOT edited/renamed).
- [ ] Renamed the COPY to the `LIVE00x_..._BATCH002` name.
- [ ] Webhook URL pasted from the local file **into TradingView only** (never chat).
- [ ] Notify-in-app ON; Webhook ticked; expiry open-ended.
- [ ] Fired once (or waited for a natural fire) → tell Claude to verify R2 (temp read branch → revert).
- [ ] Disable/delete the mirror after capture is confirmed.

## After creation → resume path (Claude, on your signal)

Verify R2 capture (read-only temp branch, then revert to pure logging-only) → import that session's XAUUSD
1m OHLC → run classifier → detector → outcome matcher → scorer → Farouk Campaign State Machine v0.1 → enqueue
any `WATCH_ONLY` / `SHADOW_CANDIDATE_*` into Batch 002. Observation-only.

## What still blocks demo / broker

Evidence bar **≥30 outcome-matched candidates across ≥5 sessions — NOT MET**; HTF-alignment gate; human
review; no auto broker path; `NOT_INTEGRATION_READY` held. Gates stay `PAPER/PREVIEW/False/False`.
