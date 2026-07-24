# Next Gate — H (small-set mirrored capture) Readiness

**Gate G PASSED.** Gate H is **UNBLOCKED but NOT started and NOT authorised.**

## Prerequisites

- [x] Gate D/E/F; **Gate G (one real Farouk alert mirrored, captured) PASSED**.
- [ ] Duplicate `LIVE003_FAROUK_MIRROR_GATE_G` disabled/deleted (Martyn) — recommended before Gate H so
  volume is controlled.
- [ ] Explicit **Gate H** approval.

## Key learning from Gate G to fold into Gate H

- The **ANY_ALERT composite is very high-volume** (69 captures in ~10h). For Gate H, prefer **lower-volume
  dedicated alerts** (APLUS, a CHoCH/Sweep) for a first small set, and **disable each duplicate after its
  proof** unless ongoing capture is explicitly wanted.
- Farouk alerts are **`alert()`-based → raw text / INVALID_JSON**. Plan for raw-text normalisation
  (offline, read-only) — `RAW_ALERT_NORMALISATION_PLAN.md`.

## What Gate H would do (per `GATE_H_SMALL_SET_CAPTURE_PLAN.md`)

- Duplicate-first, one-by-one, **max 3** mirrors first batch; originals never edited; disable-after-proof;
  full rollback (per-duplicate / batch / `ENABLED=0` / secret-rotation). Capture-only.

## Gate sequence

`… → F ✅ → G ✅ (real Farouk capture) → H (small set — next, not authorised) → I reports → J shadow`.

Nothing proceeds without explicit approval. NOT_INTEGRATION_READY unchanged; capture-only.
