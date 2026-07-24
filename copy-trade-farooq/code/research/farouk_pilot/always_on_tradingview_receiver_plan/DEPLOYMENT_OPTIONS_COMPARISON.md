# Always-On Deployment Options — Comparison (§1)

**DESIGN ONLY.** Four options for hosting the always-on logging-only receiver. All run the **same**
logging-only contract (POST to secret path → append-only store); only reachability/ops differ. None
may ever import a broker/QST/execution module or create a permit/lease/order.

## A. Serverless function endpoint (+ managed store)

An HTTPS function (e.g. a cloud "function"/"worker" with a URL) that validates the secret path and
appends the event to a managed append-only store.

- **Reliability:** High — provider-managed, auto-scales, no host to keep alive.
- **Cost category:** ~Free at this volume (a few events/day).
- **Complexity:** Low–moderate (function + storage + one secret).
- **Setup risk:** Low — no OS to harden.
- **Security risk:** **Smallest standing surface** (no long-lived host); trust boundary = the cloud
  provider; enforce least-privilege storage + no execution capability.
- **Laptop-off behaviour:** **Captures 24/7.** ✅
- **Logging/storage fit:** Excellent — pair with append-only object storage or a managed table.
- **Rollback ease:** Trivial — delete/disable the function.
- **Best use case:** **The always-on default.** Recommended first implementation.

## B. Small cloud VPS (always-on VM)

A minimal always-on VM running the receiver as a service behind HTTPS.

- **Reliability:** High; independent of the laptop.
- **Cost category:** Low but **ongoing** (small monthly VM).
- **Complexity:** Moderate (provision, TLS, service manager, patching).
- **Setup risk:** Moderate — you own the OS hardening.
- **Security risk:** **Largest** — a standing public host to patch/monitor.
- **Laptop-off behaviour:** Captures 24/7. ✅
- **Logging/storage fit:** Good — local SQLite/JSONL on the VM, or a managed DB.
- **Rollback ease:** Moderate — stop the service / destroy the VM.
- **Best use case:** Only if a full VM is wanted for other reasons; otherwise heavier than needed.

## C. Managed worker/function endpoint (edge worker + managed KV/DB)

Similar to A but on an edge-worker platform with an integrated managed key-value/table store.

- **Reliability:** High; global edge, auto-scales.
- **Cost category:** ~Free at this volume.
- **Complexity:** Low–moderate.
- **Setup risk:** Low.
- **Security risk:** Small standing surface; watch storage access scope + retention.
- **Laptop-off behaviour:** Captures 24/7. ✅
- **Logging/storage fit:** Good — managed KV/table; ensure append-only discipline in code (KV can
  overwrite by key, so key on `event_id`).
- **Rollback ease:** Trivial — delete the worker.
- **Best use case:** Strong alternative to A; pick by which provider Martyn already trusts/uses.

## D. Keep local receiver + manual tunnel only (status quo)

The Stage-2 approach: local `receiver.py` + cloudflared quick tunnel, started by hand.

- **Reliability:** Laptop-bound; tunnel can drop.
- **Cost category:** Free.
- **Complexity:** Low (already built + proven).
- **Setup risk:** Low.
- **Security risk:** Medium — public tunnel to a local port while running; mitigated by secret path.
- **Laptop-off behaviour:** **Captures nothing when laptop off/asleep.** ❌ (the gap we're closing)
- **Logging/storage fit:** Local JSONL (already implemented).
- **Rollback ease:** Trivial — stop both processes.
- **Best use case:** Ad-hoc tests and as a **fallback**; not a 24/7 solution.

## At a glance

| | A: Serverless | B: VPS | C: Edge worker | D: Local+tunnel |
|---|---|---|---|---|
| Laptop-off capture | ✅ | ✅ | ✅ | ❌ |
| Reliability | ★★★ | ★★★ | ★★★ | ★★ |
| Standing security surface | smallest | largest | small | medium |
| Cost | ~free | low ongoing | ~free | free |
| Complexity | low–mod | moderate | low–mod | low (done) |
| Rollback | trivial | moderate | trivial | trivial |
| Best for | **always-on default** | full-VM needs | strong A alt | tests/fallback |

## Recommendation

**Option A (serverless function + managed append-only store)** for the first always-on build, with
**Option C** as an equal-footing alternative chosen by provider preference. Keep **Option D** as the
local fallback. Details: `RECOMMENDED_FIRST_IMPLEMENTATION.md`.
