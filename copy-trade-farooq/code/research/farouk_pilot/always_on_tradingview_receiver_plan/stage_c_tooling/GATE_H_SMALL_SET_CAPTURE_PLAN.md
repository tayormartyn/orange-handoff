# Gate H — Small-Set Mirrored Farouk Capture — PLAN (NOT STARTED)

**Mode: PLAN ONLY (prepared during the Gate G wait).** No alert touched, no duplicate created, no
webhook attached, no Worker change. Gate H is **not started and not authorised** — it requires Gate G
to pass first, then explicit approval.

## Objective

After Gate G proves one real Farouk alert captures cleanly, extend to a **small set** of Farouk alerts
— **duplicate-first, one-by-one**, capture-only, with no edits to any original production alert.

## Principles

1. **Duplicate-first only.** Each mirrored alert is a **duplicate** of an original; originals are never
   edited and keep their app/CSV evidence lanes.
2. **One-by-one rollout.** Add one duplicate, confirm a capture, evaluate, then add the next — never a
   whole batch at once.
3. **Bounded first batch.** **Maximum 3 mirrored alerts** in the first Gate H batch (see selection).
4. **Disable-after-proof option.** Each duplicate may be disabled once its capture is confirmed (to
   avoid volume), or kept running if ongoing capture is wanted — Martyn decides per alert.
5. **Capture-only.** Logging-only; no broker/QST/execution; no permit/lease/order; gates stay False.

## Suggested first batch (max 3) — Martyn confirms at approval

| # | Original alert | Why | Volume |
|---|---|---|---|
| 1 | `LIVE001_ANY_ALERT_XAUUSD_3M` | composite — richest text, already proven in Gate G | high |
| 2 | `LIVE001_APLUS_XAUUSD_3M` | the grade trigger (A+) — high analytical value | ~4/day |
| 3 | `LIVE001_CHOCH_DOWN_XAUUSD_3M` (or SWEEP_HIGH) | a structure event — lower volume, breadth | low |

Rationale: one high-volume composite + one grade + one structure event gives representative coverage
without flooding. Dedicated names map cleanly to `event_type`.

## Naming convention for duplicates

`LIVE0xx_FAROUK_MIRROR_<SHORTNAME>_GATE_H` (e.g. `LIVE004_FAROUK_MIRROR_APLUS_GATE_H`). Never reuse or
rename an original.

## Rollout procedure (per alert, when approved)

1. Duplicate the chosen original (do not edit it). Rename the copy per convention.
2. On the duplicate only: condition unchanged, Notify-in-app ON, add the proven webhook URL (bare line
   from the gitignored local file), message per its type (JSON if editable, else raw `alert()` text).
3. Save; confirm the original is present + unchanged + armed.
4. Wait for one natural trigger; verify the R2 capture (temp read-only branch or tail, then revert to
   pure logging-only).
5. Decide: keep the duplicate running (ongoing capture) or disable it (proof-only).
6. Only then proceed to the next alert.

## Rollback procedure

- **Per duplicate:** disable or delete it → capture stops for that alert; original unaffected.
- **Whole batch:** delete all `*_GATE_H` duplicates → back to originals-only.
- **Endpoint-level:** `TV_WEBHOOK_ENABLED=0` (Worker returns 503) or rotate the secret path (old URL
  404s) → stops all capture instantly, no TradingView edits needed.
- **Evidence:** R2 objects are append-only and kept (legitimate evidence); rollback never deletes them.

## Exit criteria to consider Gate H "done" (first batch)

- Each of the ≤3 mirrors produced ≥1 verified capture (raw preserved, no secret stored).
- Originals confirmed untouched throughout.
- No disruption to app/CSV evidence lanes.
- Safety audit clean at each step.

## Hard guarantees

Originals never edited; duplicate-first; capture-only; no broker/QST/execution; no permit/lease/order;
no gate change; no risk change; Telegram listener untouched; secret never exposed;
`NOT_INTEGRATION_READY` unchanged. **NOT started — awaiting Gate G pass + explicit approval.**
