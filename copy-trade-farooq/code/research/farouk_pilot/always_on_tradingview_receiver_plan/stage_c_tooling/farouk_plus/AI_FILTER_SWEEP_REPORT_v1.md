# Farouk-Plus Shadow Engine Step 3 — AI Filter Sweep Report v1

**Mode: STEP 3 AI FILTER SWEEP ONLY.** Observation-only, review-only, offline. Date 2026-07-11.
Listener PID 87988 untouched; both evidence DBs opened read-only. Deterministic OHLC outcomes (Days 2/4/5)
remain the authority — this sweep only joins text features to those outcomes. **Every structured record
(34/34) passed the ai_review fail-closed validator** and carries the validator's
`review_only=True, executable=False, trade_ready=False` stamp. Negative check **PASSED**: a record with a
`low_lot_flag` key was rejected (`forbidden execution-surface field`) — feature keys containing
`lot`/`risk`/etc. are unwritable through the validator by design, so features use safe names
(`f2_small_size_language`, `f4_elevated_caution_label`). Gates unchanged; `NOT_INTEGRATION_READY` unchanged.

**Corpus:** all 34 XAU setups (33 matched + J24) × their full captured message threads (June backfill DB,
273 gold-trades msgs + July evidence DB). 12 features scanned at two scopes: full thread vs entry message
only (= entry-actionable). Data: `ai_filter_sweep_v1.json`.

## 1. Findings (present → W/L/P vs absent → W/L/P; L includes the 3 manual-cut losses)

| feature | present | absent | verdict |
|---|---|---|---|
| **f4 HIGH-RISK label** (entry-actionable) | **5W/0L/2P** | 15W/6L/5P | **PROMISING_SCORING_FEATURE** — his own caution label paradoxically marks zero-loss trades (heightened-alert days incl. the J26 859p monster) |
| **f2 size-caution language** (entry-actionable) | **5W/0L/3P** | 15W/6L/4P | **PROMISING_SCORING_FEATURE** — merged with f4 as one "caution-language" family (they co-occur). Recorded as TEXT only; the engine never derives sizing |
| **f7 explicit "Reason for the sell/buy"** (semi-actionable) | **5W/0L/1P** | 15W/6L/6P | **PROMISING (low weight)** — structured-thesis days win; applied as an upgrade when the reason arrives |
| f8 education/stream context | 0W/1L/2P | 20W/5L/5P | **WATCHLIST (negative tilt)** — teaching-mode threads produced no verified wins; n=3 |
| f5 BE-stop management language | 19W/2L/6P | **1W/4L/1P** | **WATCHLIST — outcome-side ONLY.** Dramatic split but reverse-caused: BE-stop talk happens only after profit exists. Entry-scope hits (2, both L) are just re-entry announcements = R2b again. Never scored at entry |
| f11 Friday entry | 1W/1L/2P | 19W/5L/5P | WATCHLIST (mild negative, n=4) |
| f1 news language | 2 hits (both W), 0 at entry | — | **NEEDS_FORWARD_EVIDENCE** — his text rarely flags news in advance; a real feature needs an external economic-calendar join |
| f6 layered-entry language | 3W/1L/4P | mixed | **REJECTED** (his universal method, narrated inconsistently) |
| f9 post-hoc commentary · f10 breakdown video · f12 late-entry confession | sparse / neutral | — | **REJECTED** (no signal) |

## 2. Predictive-value answers

- **Risk-language / size-caution / "don't risk profit":** yes, positive — the caution-language family
  (f2+f4, plus f3 protect-language at 3W/0L/2P) accompanied **zero losses** in this sample. Interpretation:
  the labels mark his highest-attention discretionary reads, not danger.
- **News/session:** no usable in-text news signal (needs calendar join, forward). Friday mildly negative
  (n=4). The already-adopted R4b (≥15:30Z) remains the only time feature with teeth.
- **Management language:** hugely correlated with outcomes but **reverse-caused** — adopted only as an
  outcome-side diagnostic (beside the MAE feature), never as an entry score.

## 3. Honesty caveats (do not skip)

With 33 trades / 6 losses, a zero-loss split on a 7-hit feature has ~15–25% probability **by pure chance**;
12 features were tested, so ~2 lucky splits are expected. f2/f4/f7 co-occur (one "conviction-day" family,
not three edges). All features parse the poster's own wording — fragile if his phrasing changes. Everything
above is provisional until the ≥15 forward-captured-trade sample exists (Day-6 thresholds).

## 4. Carry into detector v0_2 replay

1. **caution_language** (f2∪f4): +1 provisional, entry-actionable.
2. **reason_stated** (f7): +1 low weight, applied on arrival.
3. **education_context** (f8): flag, weight 0, watch.
4. **f5 + MAE**: outcome-side diagnostics only.
5. Existing ruleset features unchanged: R2/R2b, R4b, R6.

## 5. Safety confirmation

Read-only analysis; 34/34 validator-passed records; 1 deliberate forbidden-field rejection (PASS). No
broker/QST/cTrader/nano/copy/demo/live execution; no permits/leases/orders; gates `PAPER/PREVIEW/False/False`
unchanged; listener PID 87988 running (start 2026-07-10 21:54:45 unchanged); no TradingView/Worker/R2/secret
action; nothing promoted to trade-ready. `NOT_INTEGRATION_READY` unchanged.

## Next step

**Step 4 — shadow candidate detector v0_2 replay:** implement the ruleset-v0.1 scoring model plus the two
adopted sweep features (caution_language, reason_stated) as scoring inputs, replay over the 34 captured
setups, emit review labels (REJECT/WATCH/SHADOW_CANDIDATE_LOW/MEDIUM/HUMAN_REVIEW_REQUIRED) through the
ai_review validator, and diff label quality against the 33 known deterministic outcomes
(precision/recall per label tier).
