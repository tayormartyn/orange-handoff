# Webhook Deployment Options

**DESIGN ONLY.** Comparison of where the logging-only receiver could run. TradingView must POST to a
**public HTTPS URL**, so a local-only receiver needs a tunnel.

> Note on TradingView reachability: TradingView's webhook sender posts to a public endpoint. A plain
> laptop on hotel Wi-Fi is not publicly reachable, hence Option A needs a tunnel. **TO_VERIFY:**
> whether the current TradingView plan tier permits webhook alerts at all — webhooks are a paid-plan
> feature; confirm before Stage 2.

## Option A — Local receiver + secure tunnel

A small local HTTP receiver on the laptop, exposed via a secure tunnel (e.g. an authenticated tunnel
service) that gives a public HTTPS URL forwarding to localhost.

- **Setup speed:** Fastest. Runs from `C:\Users\Marty\signal-terminal` like the other tools; no cloud
  account/build pipeline.
- **Reliability:** Good while laptop is awake/online; depends on the tunnel staying up.
- **Laptop-off behaviour:** **Captures nothing when the laptop sleeps/offline** — same limitation as
  the Telegram PREVIEW listener. Firings during downtime are missed by this lane (TradingView app/CSV
  still exist as backstop).
- **Hotel/Wi-Fi risk:** Captive portals, NAT, and flaky Wi-Fi can drop the tunnel; public URL changes
  on reconnect unless a reserved domain is used.
- **Security risk:** The tunnel exposes a local port publicly — mitigated by random secret path +
  shared-secret header + POST-only + body cap. Keep the URL private.
- **Cost:** Free / low (tunnel free tier likely sufficient).
- **Recommended use case:** **The fastest safe FIRST implementation** and all of Stages 1–4.

## Option B — Small cloud server (always-on VM)

A minimal always-on VM running the same receiver.

- **Setup speed:** Moderate (provision, harden, deploy, TLS).
- **Reliability:** High; independent of the laptop.
- **Laptop-off behaviour:** **Captures 24/7** — solves the downtime gap.
- **Hotel/Wi-Fi risk:** None for capture (server is remote); Martyn only needs connectivity to read
  the logs later.
- **Security risk:** A standing public host to patch/harden; larger attack surface than serverless.
  Same app-level controls apply.
- **Cost:** Low but ongoing (small monthly VM).
- **Recommended use case:** Stage-5 upgrade for laptop-off capture once the lane is proven.

## Option C — Serverless endpoint (function + managed store)

A serverless HTTPS function that validates and appends to a managed append-only store.

- **Setup speed:** Moderate (function + storage + secret config).
- **Reliability:** High; auto-scales; no server to keep alive.
- **Laptop-off behaviour:** **Captures 24/7.**
- **Hotel/Wi-Fi risk:** None for capture.
- **Security risk:** Smallest standing surface (no long-lived host), but adds a cloud provider to the
  trust boundary; must ensure the function has **no** broker/execution capability and least-privilege
  storage access.
- **Cost:** Effectively free at this volume (a handful of events/day).
- **Recommended use case:** The **preferred always-on** option long-term (cheap, low-maintenance,
  small surface) — after Option A proves the format and safety.

## Comparison at a glance

| | A: Local + tunnel | B: Cloud VM | C: Serverless |
|---|---|---|---|
| Setup speed | ★★★ fastest | ★★ | ★★ |
| Reliability | ★★ (laptop-bound) | ★★★ | ★★★ |
| Laptop-off capture | ✗ | ✓ | ✓ |
| Hotel/Wi-Fi resilience | ✗ | ✓ | ✓ |
| Standing security surface | medium (open port via tunnel) | larger (host) | smallest |
| Cost | free/low | low ongoing | ~free |
| Best for | **first build, Stages 1–4** | laptop-off upgrade | **always-on long-term** |

## Recommendation

1. **Start with Option A** (local + tunnel, LOGGING_ONLY, JSONL) — fastest safe path to stop missing
   firings while the laptop is up, fully under Martyn's control.
2. **Then move the always-on lane to Option C (serverless)** for cheap 24/7 capture, once the payload
   format and safety controls are validated on Option A.
3. Option B only if a full VM is wanted for other reasons; otherwise C is lighter.

**All three run the identical receiver in LOGGING_ONLY mode with the same safety spec and hard
vetoes.** The deployment target changes reachability, not behaviour: none of them may ever import a
broker/QST/execution module or create a permit/lease/order.
