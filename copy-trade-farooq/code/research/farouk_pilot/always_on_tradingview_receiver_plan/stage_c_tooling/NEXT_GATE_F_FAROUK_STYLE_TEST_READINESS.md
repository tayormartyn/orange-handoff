# Next Gate — F (Farouk-style duplicate test) Readiness

**Gate E PASSED.** Gate F is **UNBLOCKED but NOT started and NOT authorised.**

## Prerequisites

- [x] Stage B PASS; Gate C-* (install/login/R2A/R2B/deploy-dark/endpoint/hygiene); Gate D-MANUAL-POST.
- [x] **Gate E-TRADINGVIEW-TEST VERIFIED** — real TradingView alert → Worker → R2, placeholders
  resolved, UTC, secret-safe (2 captures).
- [ ] Explicit **Gate F** approval.

## What Gate F would do (later, only if approved)

- A **duplicate Farouk-STYLE** test alert (a NEW alert shaped like a Farouk signal, **NOT** a real
  Farouk production alert) → cloud receiver → verify capture + parsing of Farouk-shaped fields.
- Still **no** real Farouk production alert edited/mirrored (that is Gate G/H).

## Hard boundaries

- No real Farouk production alert edited/mirrored; keep app notification ON; no broker/QST/execution;
  no permit/lease/order; no gate change; no shadow engine; listener untouched; secret never exposed.
- Verification will again use the temporary secret-gated read-only list branch (added + reverted), or
  the tail method.

## Gate sequence

`… → D ✅ → E ✅ (verified) → F (next — unblocked, not authorised) → G/H (Farouk mirroring) → I → J`.

Nothing proceeds to Gate F without explicit approval. NOT_INTEGRATION_READY unchanged; capture-only.
