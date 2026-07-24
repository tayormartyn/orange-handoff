# Next Sequence Capture Plan v0.1

**Mode: NEXT SEQUENCE CAPTURE PLAN ONLY — design/observation, no execution.** No TradingView alert touched,
no Worker deploy, no R2, no broker/cTrader/QST, no permit/lease/order, no gate change, no trade instruction.
`NOT_INTEGRATION_READY` unchanged. This document is a **recommendation for Martyn to set up capture-only
mirrors** later; it changes nothing itself.

## Why Jul-10 produced 0 candidates

The detector (`shadow_candidate_detector_v0_1`) only forms a candidate when a **directional A** closes a
sequence. Jul-10 captured 3× `CHOCH_DOWN` + 1× `A_PLUS_OR_BETTER` — **no `A_SHORT`/`A_LONG`, no sweeps** — so
no pattern could complete. Lone CHoCH and a grade-only A+ never form a sequence.

## What the detector actually needs (ground truth from the code)

| Pattern | Requires | Window |
|---|---|---|
| `ALIGNED_CHOCH_TO_A` | `CHOCH_UP → A_LONG` **or** `CHOCH_DOWN → A_SHORT` (same instrument/TF, no opposite-A inside) | ≤ 15 min |
| `SWEEP_TO_CHOCH_CONTEXT` | `SWEEP_LOW → CHOCH_UP` **or** `SWEEP_HIGH → CHOCH_DOWN` | ≤ 30 min |
| `BPR_TO_A_CONTEXT` | `BPR_TAPPED → A_LONG`/`A_SHORT` | ≤ 15 min |
| `CONTRADICTORY_CLUSTER` (disqualifier) | opposite direction hints clustered | ≤ 15 min |

**Event types consumed:** `A_LONG`, `A_SHORT`, `CHOCH_UP`, `CHOCH_DOWN`, `SWEEP_LOW`, `SWEEP_HIGH`,
`BPR_TAPPED`. `A_PLUS` / `A_TRIPLE_PLUS` are **grade context only** — no pattern uses them as the terminal A.

## 1–2. Alert types still needed / to mirror next

**Missing and essential — capture next:**
- **`A LONG` and `A SHORT`** (directional A) — **the blocker.** Every candidate pattern ends in one. Without
  them nothing forms, no matter how many CHoCH/Sweep fire.
- **`Sweep high` and `Sweep low`** — the lead for `SWEEP_TO_CHOCH_CONTEXT` and the textbook
  Sweep→CHoCH→A chain (never captured cleanly yet).

**Already proven capturable, keep:**
- **`CHoCH up` and `CHoCH down`** — the lead for `ALIGNED_CHOCH_TO_A` and the terminal for
  `SWEEP_TO_CHOCH`. (H2 already showed CHoCH-down captures fine.)

**Optional / lower priority:**
- **`BPR tapped`** — enables `BPR_TO_A_CONTEXT` (but BPR is directionless proximity, LOW confidence).

**Grade context only (low volume):**
- **`A+ / A+++`** — capture to annotate a nearby directional A's grade; **not** a sequence trigger on its own.

## 3. Proposed low-noise capture set (next cycle)

Capture-only duplicate mirrors (same pattern as H1/H2: duplicate the original alert, webhook the DUPLICATE
to the logging-only Worker, original untouched, delete the mirror after enough capture):

- **Core (6):** `A LONG`, `A SHORT`, `CHoCH up`, `CHoCH down`, `Sweep high`, `Sweep low`.
- **Optional (2):** `BPR tapped`; `A+ / A+++` (grade context).
- Each on **XAUUSD · Pepperstone · 3m** (the Farouk production chart), copy-proof bare webhook URL pasted
  **into TradingView only** (never chat).

## 4. ANY_ALERT — avoid

**Yes, keep ANY_ALERT avoided.** Gate G showed `LIVE001_ANY_ALERT` is a very high-volume flood
(~6.4 events/h, peak 14/h; Engulfing + A dominate as noise). It buries the sequence structure and inflates
R2 with context/noise. Prefer the specific low-volume mirrors above.

Also avoid **Engulfing (bull/bear)** mirrors — co-firing noise the detector deliberately does not promote.

## 5. Are A LONG / A SHORT essential?

**Yes — essential.** They provide the campaign **direction** and are the terminal of every candidate
pattern. This is the single highest-priority gap.

## 6. CHoCH up/down and Sweep high/low?

**Yes — include both.** CHoCH up/down = the structure lead (`ALIGNED_CHOCH_TO_A`) and the Sweep terminal.
Sweep high/low = the liquidity lead (`SWEEP_TO_CHOCH_CONTEXT`) and the start of the textbook chain.

## 7. A+ / A+++?

**Include as grade context only.** A+ alone is **insufficient** — it carries no direction and no pattern uses
it as the terminal A. Capture it to enrich a nearby `A_LONG`/`A_SHORT` with grade, nothing more.

## 8. What counts as a valid sequence candidate

A candidate exists only when the detector forms one of:
- `ALIGNED_CHOCH_TO_A`: `CHOCH_UP→A_LONG` or `CHOCH_DOWN→A_SHORT` within 15m (same instrument/TF, no
  opposite-A in window) — **MEDIUM** only if same instrument+TF and no contradiction, else LOW.
- `SWEEP_TO_CHOCH_CONTEXT`: `SWEEP_LOW→CHOCH_UP` or `SWEEP_HIGH→CHOCH_DOWN` within 30m — LOW.
- `BPR_TO_A_CONTEXT`: `BPR_TAPPED→A_LONG/A_SHORT` within 15m — LOW.
- **Priority — textbook chain:** `SWEEP_LOW→CHOCH_UP→A_LONG` (or high/down/short) — combines the sweep and
  aligned patterns; never captured cleanly yet, so it is the top capture target.

Each formed candidate is then outcome-matched (needs same-session OHLC), scored, run through the Farouk
Campaign State Machine v0.1, and enqueued to Batch 002 if it resolves to `WATCH_ONLY` / `SHADOW_CANDIDATE_*`.

## 9. What still blocks demo / broker discussion

- **Evidence bar: ≥30 outcome-matched candidates across ≥5 sessions — NOT MET** (Batch 001 = 3 in 1 session;
  Jul-10 added 0). A REJECT does not count.
- **HTF-alignment gate** (Batch 001 lesson): counter-HTF candidates cap low; a confirmed HTF-supportive
  setup is still unseen.
- **Human review** of each candidate; **no auto broker path**; **`NOT_INTEGRATION_READY`** held by governance
  until explicitly lifted. Gates stay `PAPER/PREVIEW/False/False`.

## Guardrails (unchanged)

Observation/capture-only; each mirror is duplicate-first and deleted after capture; original alerts never
touched; Worker stays pure logging-only; R2 read only on a mirror fire (then revert); Telegram PREVIEW
listener PID 16608 left running; no broker/cTrader/QST; no permit/lease/order; gates unchanged;
`NOT_INTEGRATION_READY` unchanged.
