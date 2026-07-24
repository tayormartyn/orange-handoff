# Sprint Day 1 — Fable-assisted XAUUSD Backward Ledger + OHLC Export Requirements

**Mode: COMPRESSED VALIDATION SPRINT DAY 1 — LEDGER + OHLC PREP ONLY.** Observation-only. Date 2026-07-11.
Session model: **Fable 5** (`claude-fable-5`, 1M context) — the Day-0 model pin took effect. Listener **PID
87988 running/untouched** (verified before and after; read-only `Get-Process`/`Get-CimInstance` only). All DB
access **read-only** (`sqlite3 file:...?mode=ro`). No second listener; no TradingView/Worker/R2/secret action;
no broker/cTrader/QST; no permit/lease/order; gates `PAPER/PREVIEW/False/False`; `NOT_INTEGRATION_READY`
unchanged. SOL/BTC excluded from this ledger (side lanes). **All result figures are Farouk's own claims
(RESULT_CLAIM_ONLY) — none independently verified.** No scoring/outcome-matching run (no OHLC covers any
window). AI output is review-only, never an executable signal.

## 1. Ledger

**Machine-readable ledger:** `stage_c_tooling/SPRINT_DAY1_XAU_LEDGER_v1.json` — 4 setups, each with full
evidence pack (message ids, UTC timestamps, raw text), captured/uncaptured media, validated stub + Fable
review outputs, and OHLC export requirements.

Source: Telegram channel **-1001902136163** (Whale Discord mirror), sub-channel **🪙・gold-trades**, author
**seascalperfarouk**. Local capture window: msgs 45285–45642, 2026-06-29T13:21Z → 2026-07-10T16:52Z (269
records).

### Setup 1 — XAU-S1-20260630 (WIN claim)

| field | value |
|---|---|
| entry msg | **45331**, 2026-06-30T14:25:23Z |
| direction / entry / SL | SELL, **4060–4075**, SL **4100** |
| TP | no fixed ladder — progressive pip calls |
| management | HIGH RISK; **SUPER LOW LOT** (45331/45332); 60 pips tp1 (45333); sl to entry (45334); closing 0.5 at 150 pips (45340); 200 pips take 50% off (45345); take more, leave 10% sl to entry (45347) |
| follow-ups / result | 60→100→150→180→200 pips (45333/45338/45340/45343/45345); reason-for-sell (45336); breakdown video (45342); **"we got 1000+ pips I close fully now!" 45369, 2026-07-01T02:35:07Z** |
| message ids | 45331 45332 45333 45334 45335 45336 45338 45339 45340 45341 45342 45343 45344 45345 45347 45369 |
| media | photos referenced at 45334/45339/45340/45344/45345/45347/45369/45370 — **binaries NOT captured** (pre-fix era; backfillable via copied session) |
| status | **RESULT_CLAIM_ONLY** |

### Setup 2 — XAU-S2-20260707 (LOSS claim — upgraded from Day-0 "UNCLEAR")

| field | value |
|---|---|
| entry msg | **45499**, 2026-07-07T11:29:34Z |
| direction / entry / SL | SELL, **4144–4154**, SL **4180** |
| TP ladder | 4135–4130–4120–4115–4110–4105 (45500, 11:33Z) |
| result | **"Trade failed unfortunately" (45502, 2026-07-07T13:43:47Z)** — explicit same-day loss claim Day 0 had missed; + "Got stopped out by 0.60 cents and I knew we were going to dump hard" (45559, 07-08 14:18Z) |
| message ids | 45499 45500 **45502** 45559 |
| media | none for this setup |
| status | **RESULT_CLAIM_ONLY** (LOSS claim; stop-out time between 11:33 and 13:43Z, unverified) |

### Setup 3 — XAU-S3-20260708 (WIN claim)

| field | value |
|---|---|
| entry msg | **45552**, 2026-07-08T12:14:29Z |
| direction / entry / SL | SELL, **4072–4083**, SL **4125** |
| TP | TP1 never numerically stated; residual target **4020** for last 10% (45561) |
| management | **low lot please** (45552); close worst hold best sl entry (45553); take tp1 (45554); take 50% off (45555); take more off (45556); close 90% leave 10% for 4020 (45561) |
| follow-ups / result | "200+ pips" (45556, 14:16Z); breakdown video (45560); "Lets go 500 pips" (45562, 14:46Z); **"full tp hit now we wait for fomc" (45567, 15:32:31Z)** |
| message ids | 45552 45553 45554 45555 45556 45557 45558 45560 45561 45562 45566 45567 |
| media | photos referenced at 45554/45555/45556/45557/45558/45561/45567 + document 45566 — **binaries NOT captured** (pre-fix era; backfillable) |
| status | **RESULT_CLAIM_ONLY** |

### Setup 4 — XAU-S4-20260710 (WIN claim, PARTIAL — no close message captured)

| field | value |
|---|---|
| entry msg | **45625**, 2026-07-10T12:43:32Z |
| direction / entry / SL | SELL, **4102–4115**, SL **4152** |
| TP | conditional **TP2 4077 / TP3 4055** (45635, 13:38Z) |
| management | **LOW LOT** (45625); low risk, may push into 4125–4135 (45626); take tp1 close worst hold best sl to entry (45627); take 50% off sl to entry (45634) |
| follow-ups / result | **"100 pips" (45629, 13:25Z)**, **"200 pips" (45632, 13:30Z)**; reason-for-sell (45633); **no full-close message in capture** (window ends 45642, 16:52Z) |
| message ids | 45625 45626 45627 45628 45629 45630 45631 45632 45633 45634 45635 |
| media (CAPTURED, sha256-addressed under `campaign_extractor/prospective/data/prospective_media_v1/`) | 45628 `5643fb10…a51b12b.jpg` (37,058B) · 45629 `92fe92b7…c0ec5f.jpg` (18,601B, rev-2 backfill) · 45630 `359caa89…79aa1c.jpg` (20,499B) · 45632 `9c5c50f0…8474e.jpg` (20,162B) |
| status | **RESULT_CLAIM_ONLY** (partial win claims; final outcome unknown → OHLC window extended to Friday close) |

## 2. AI Evidence Reviewer lane usage

- Built 4 evidence packs directly from the read-only evidence DB; every pack passed
  `schema.validate_evidence_pack`.
- **Stub reviewer** (`stub_reviewer.review(provider="stub")`) run on all 4 packs — outputs validated +
  review-only stamped by the fail-closed validator.
- **Fable 5 extraction** for each setup was passed through the **same** `schema.validate_reviewer_output`
  validator — all 4 accepted, all stamped `review_only=True, executable=False, trade_ready=False`.
- **Cross-check:** stub vs Fable agree on direction + SL for all 4 setups. Divergences (both stub
  limitations, resolved by Fable review, recorded in the JSON): stub called S1 "CONTRADICTORY" because
  Farouk's commentary mentions his untouched *buy zone 4000–3980* (commentary, not a signal conflict);
  stub missed entry zones for S1/S3 (its regex needs an "Entry" keyword; those posts use "XAUUSD SELL
  4060-4075" form).
- **Negative check PASSED:** a crafted output containing `lot_size` was rejected by the validator
  (`ReviewerOutputRejected: forbidden execution-surface field ... 'lot_size'`). No AI output containing
  forbidden execution fields was accepted anywhere.
- No external AI API call was made; the "Fable" extractions are this session's own review, subordinated to
  the deterministic validator, which remains the authority.

## 3. OHLC export requirements (for independent outcome matching)

**Format** (same as `XAUUSD_OHLC_IMPORT_SCHEMA_v0_1.md` / existing imports): CSV header
`timestamp_utc,open,high,low,close,source,timeframe`, ISO-8601 UTC (`...Z`), `source=PEPPERSTONE_TradingView_export`,
`timeframe=1m`. Symbol **XAUUSD (Pepperstone feed on TradingView)**. Drop them in
`stage_c_tooling/price_data/`.

### Existing local coverage — checked, covers NONE of the 4 windows

| existing file | coverage (UTC) | verdict |
|---|---|---|
| `XAUUSD_1M_2026-07-08_2026-07-09_IMPORT_HERE.csv` | Jul-08 16:12 → Jul-09 12:18 (1,145 bars) | starts 40 min AFTER S3's 15:32 full-tp claim → misses S3 entirely |
| `XAUUSD_1M_2026-07-10_IMPORT_HERE.csv` | Jul-09 18:01 → Jul-10 08:09 (787 bars) | ends 4.5h BEFORE S4's 12:43 entry → misses S4 entirely |

### Required exports (4 files Martyn needs to produce)

| # | setup | window (UTC) | why this window | suggested filename |
|---|---|---|---|---|
| 1 | XAU-S1-20260630 | **2026-06-30 13:00 → 2026-07-01 04:00** | entry 14:25Z Jun-30 (−85 min buffer); final "1000+ pips close fully" claim 02:35Z Jul-01 (+85 min) — spans overnight/Asia | `XAUUSD_1M_2026-06-30_1300_2026-07-01_0400_UTC.csv` |
| 2 | XAU-S2-20260707 | **2026-07-07 10:00 → 16:00** | entry 11:29Z (−89 min); "Trade failed" 13:43Z (+137 min); must show whether/when 4180 traded (stop-out + the "0.60c" overshoot claim) | `XAUUSD_1M_2026-07-07_1000_1600_UTC.csv` |
| 3 | XAU-S3-20260708 | **2026-07-08 11:00 → 16:30** | entry 12:14Z (−74 min); "full tp hit" 15:32Z (+58 min); joins the existing file starting 16:12Z | `XAUUSD_1M_2026-07-08_1100_1630_UTC.csv` |
| 4 | XAU-S4-20260710 | **2026-07-10 11:30 → 22:00** | entry 12:43Z (−73 min); last claim 13:38Z but **no close message** → run to Friday close (~21:59Z) to adjudicate TP2 4077 / TP3 4055 / SL-to-entry | `XAUUSD_1M_2026-07-10_1130_2200_UTC.csv` |

**TradingView export steps (per window):** XAUUSD Pepperstone chart → 1m timeframe → set chart timezone to
**UTC** → scroll to the window → Export chart data… (CSV) → trim to the window rows → ensure the header/columns
above (add `source`/`timeframe` columns as constants if the raw export lacks them, as done for the two
existing files). One file per window; ~900 / ~360 / ~330 / ~630 rows respectively.

## 4. Backward Telegram history fetch (pre-2026-06-29) — feasibility

**FEASIBLE, not performed.** The copied-session method is already proven live twice (msg-45629 one-message
backfill and the 8-photo Jul-10 backfill — both ran while PID 87988 stayed connected, zero disruption).
Telegram server-side history for the mirror channel extends before Jun-29, so a **bounded**
`iter_messages(offset_date≈2026-06-01 → 2026-06-29)` text+photo fetch can reconstruct the June ledger (the
"22 trades, 2 losers" June claim). Recommendation: run it as its own authorised sprint task with an explicit
message-count cap and the same append-only revision-tagged writes; **do not** run unbounded. Not executed
today per the hard rules.

## 5. Safety confirmation

Listener PID 87988 checked running before work began and after the ledger was written — never
stopped/restarted/signalled; no second listener created. Evidence + media DBs opened `mode=ro` only. No
broker/QST/cTrader/execution code touched or imported; no permits/leases/orders (none created); gates
untouched (`MODE=PAPER`, `LISTENER_MODE=PREVIEW`, `EXECUTION_ENABLED=False`, `CTRADER_EXECUTION_ENABLED=False`);
no TradingView/Worker/R2/secret action; webhook secret not rotated. No methodology scoring, no
outcome-matching, no shadow/demo execution. All AI outputs review-only + validator-stamped.
`NOT_INTEGRATION_READY` unchanged.

## Next step

Martyn exports the **4 XAUUSD 1m OHLC windows** above into `stage_c_tooling/price_data/`. Then Sprint Day 2:
independent outcome-matching of the 4 ledger setups against those files (claimed vs actual), and — if
authorised — the bounded copied-session backward fetch of June gold-trades history to extend the ledger
toward the ≥10-trade evidence threshold.
