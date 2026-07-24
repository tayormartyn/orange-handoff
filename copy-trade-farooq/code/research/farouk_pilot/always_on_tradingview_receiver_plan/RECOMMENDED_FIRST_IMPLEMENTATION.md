# Recommended First Always-On Implementation (§2)

**DESIGN ONLY.** No build, no deploy.

## Recommendation

**Option A — a serverless function endpoint + managed append-only storage**, running the exact
Stage-2-proven logging-only contract.

## Why it is the fastest safe option

- **24/7 capture** with no laptop dependency — closes the only Stage 2 limitation.
- **Smallest standing attack surface** — no long-lived server/OS to patch or monitor.
- **~Zero cost** at a few events/day.
- **Trivial rollback** — delete/disable the function; nothing lingers.
- **Reuses what's already proven** — PATH_ONLY secret-path auth, raw-first append-only storage, UTC
  timestamps, ~1s latency. The receiver logic is the same shape as `stage1_local_receiver/receiver.py`
  (stdlib-level, no framework needed for one endpoint).
- **Provider-agnostic** — the design does not depend on a specific vendor; pick the one Martyn already
  trusts (see `ALWAYS_ON_NEXT_DECISION.md`).

## Mandatory receiver invariants (identical to Stage 2, enforced in code)

The always-on receiver MUST be:

- **logging-only** — capture and store; never act.
- **append-only** — inserts only; no update/delete path.
- **path-secret authenticated** — a single long random secret path is the auth (no header needed, per
  Stage 2). Wrong path → 404.
- **POST-only** — any other method → 405.
- **raw-payload preserving** — store the body byte-exact before parsing.
- **UTC timestamped** — `received_at_utc` from the server clock, ISO-8601 `Z`.
- **parser-only** — classification is read-only metadata; it never decides or forwards anything.
- **no execution path** — no engine, no order, no sizing.
- **no broker/cTrader/QST imports** — enforced by an import allowlist that fails closed at start.
- **no permits/leases/orders** — never created or written.
- **no outbound trading requests** — the function only receives + writes to its own store.

## What is explicitly out of scope for the first build

- No parsing *decision* that acts (parser is metadata-only).
- No connection to the Telegram lane at runtime (alignment is a later, offline, read-only study).
- No mirroring of real Farouk alerts yet (that is a later, gated stage — see
  `TRADINGVIEW_ALERT_MIRRORING_PLAN.md`).
- No shadow integration (much later, separate authorisation).

## Fallback

Keep the local `receiver.py` + cloudflared as the **manual fallback** for ad-hoc tests. The always-on
serverless endpoint becomes the primary 24/7 capture path once validated.
