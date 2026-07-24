# Step 8D-A — Deterministic S3 Hold-Best Leg Check: **ESTIMATE REFUTED, +50p not +300–500p**

**Mode: S3 LEG CHECK ONLY — SINGLE-SESSION.** Observation-only. Date 2026-07-11.
1m Pepperstone data (deterministic authority). Listener PID 87988 untouched; Model A/B artefacts
untouched; no volume/lot/account/ticket fields recorded. Gates `PAPER/PREVIEW/False/False`;
`NOT_INTEGRATION_READY` unchanged. Data: `s3_hold_best_leg_check_v0_1.json`.

## 1. The deterministic facts (S3 = SHORT 4072–4083, SL 4125, posted 12:14:29Z)

| check | result |
|---|---|
| far-edge 4083 fill | **CONFIRMED** — 12:47Z (bar high 4083.31) |
| BE-returns to ≥4083 after the fill bar | **9 occurrences** — first 12:49Z (pre-instruction), **first post-instruction 13:05Z** (4 min after the 13:01:19Z "close worst hold best sl entry") |
| hard SL 4125 | never touched |
| leg MFE / MAE | **613p / 36p** |
| TP1 (+50p) / TP2 (+100p) | reached 12:56Z / 12:59Z |
| runner | **BE-stopped 13:05Z at 4083 → 0p** |
| **leg supported pips (literal playbook)** | **+50.0** (TP1+TP2 tranches banked; runner dead before the move) |

**The Step-8D premise was wrong.** The audit reasoned from "post-fill high ≈ 4086.6" that the retrace
might not have tagged 4083 — in fact price crossed 4083 nine times after the fill, including 4 minutes
after the SL-to-entry instruction. The hold-best leg died exactly like the near-edge leg, just 37 minutes
later and +25p richer.

## 2. Leg-resolved S3 vs the models

| lane | S3 result |
|---|---|
| Model A (posted-TP/achievable exits) | large positive (~+220–500p class) |
| Model B single near-edge leg | +25p |
| **leg-resolved (near +25, far +50, 50/50 blend)** | **+37.5p** |
| no-BE counterfactual | runner marked at window end (18:14, close 4075.06) = only **+79p** — price came all the way back; capturing the 613p MFE required exiting near the 15:32 "full tp" moment. **Exit timing, not leg choice, is the value.** |

## 3. Materiality — the honest answer is IMMATERIAL

- Model B raw: total +48 → **+60.5**; mean +1.4 → **+1.8p/trade**.
- Model B filtered (R2b+R4b): +614.4 → **+626.9**; mean +25.6 → **+26.1p/trade**.
- The Step-8D materiality estimate ("leg-resolved Model B ≈ +10–16p/trade") is **withdrawn**: the one
  HIGH-sensitivity case contributes ~+12.5p to the 34-trade *total*, ~+0.4p to the mean.
- **Overall capturability conclusion unchanged — and sharpened:** the literal SL-to-entry instruction
  destroys follower runners regardless of which leg is held. Leg reconstruction does NOT collapse the
  Model-A/B band; only real instruction-timing capture (Step-8C) can — plus the widget-proven fact that
  his own stops were not at the literal instructed levels.

## 4. Safety confirmation

Offline deterministic computation on already-imported 1m data; Step-8 artefacts preserved (files checked
before write; new filenames only). No broker/QST/cTrader/nano/copy/demo/live execution; no
permits/leases/orders; gates unchanged; listener PID 87988 running; no TradingView/Worker/R2/secret
action; nothing trade-ready. `NOT_INTEGRATION_READY` unchanged.

## Next step

Leg-reconstruction research is now closed as a materiality lever (audit + this check both filed). Await
gold-trades activity → **Cycle 002** under the 8C+8D capture spec; instruction-timestamp capture is the
single highest-value data item going forward.
