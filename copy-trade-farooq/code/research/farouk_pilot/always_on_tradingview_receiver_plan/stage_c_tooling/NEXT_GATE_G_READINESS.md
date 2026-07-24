# Next Gate — G (one REAL Farouk alert mirrored) Readiness

**Gate F PASSED.** Gate G is **UNBLOCKED but NOT started and NOT authorised.**

## Prerequisites

- [x] Stage B; Gate C-* ; Gate D (manual POST); Gate E (real TradingView capture); **Gate F
  (Farouk-STYLE capture) PASSED**.
- [ ] Explicit **Gate G** approval.

## What Gate G would do (later, only if approved) — FIRST production-touching step

- Mirror **ONE real Farouk production alert** to the cloud webhook, **app notification kept ON**,
  prefer **duplicate-first** (add the webhook to a duplicate, or add-webhook-only to one live alert
  without changing its condition/notifications). Verify capture; confirm the app/CSV evidence lane is
  unaffected. **Reversible** (remove the webhook to revert).
- Still logging-only; **no broker/QST/execution**; no permit/lease/order; no gate change.

## Hard boundaries / cautions for Gate G

- This is the first gate that touches a **real Farouk alert** — do it to ONE alert only, reversibly,
  with explicit sign-off; keep app notification ON; confirm no disruption before any batch (Gate H).
- Secret handling + verification (temp read branch / tail, then revert) as in Gate E/F.

## Gate sequence

`… → E ✅ → F ✅ → G (one real Farouk alert — next, not authorised) → H (full set, batches) → I reports
→ J shadow`.

Nothing proceeds without explicit approval. NOT_INTEGRATION_READY unchanged; capture-only.
