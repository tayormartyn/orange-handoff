# Stage C — Cloudflare Resource Requirements

**Mode: PREFLIGHT ONLY.** Lists what a *future* dark deployment would require. **No resource is
created here.** No account access, no login, no bucket, no Worker.

## Account & access

- **Cloudflare account** that Martyn owns/controls (free tier is sufficient at this volume).
- Auth for deploys: either `wrangler login` (OAuth, **Gate C-LOGIN**) or an API token scoped to
  Workers + R2 only. **Not done in preflight.**

## Compute — Cloudflare Worker

- One Worker running the logging-only receiver (LOGGING_ONLY) — POST-only, exact secret path,
  body cap, raw-first, UTC stamp, safe-header whitelist, parser-only, event_id, append-only R2 write,
  `ENABLED` flag, cold-start import firewall.
- **No** broker/cTrader/QST/execution capability; **no** outbound calls except the R2 write.
- Free-tier request limits are far above a few events/day.

## Storage — R2 bucket

- One **private** R2 bucket (no public access) for append-only event objects.
- **Least-privilege binding:** the Worker binding may `put`/write to this one bucket only — no list on
  other buckets, no delete-by-default, no other cloud permission.
- **Append-only object naming:** `events/YYYY/MM/DD/<event_id>.jsonl` — key on the unique `event_id`
  so `put` never overwrites an existing object (append-only guarantee on object storage). One object
  per event. Optional daily manifest (rebuildable, never source of truth).
- R2 has no egress fees; storage cost at this volume is negligible.

## Configuration (Worker secrets/vars — never committed)

| Name | Type | Purpose |
|---|---|---|
| `TV_WEBHOOK_SECRET_PATH` | secret | long random path segment — PRIMARY auth (`/tv/<value>`) |
| `TV_WEBHOOK_ENABLED` | var | kill switch (`"1"` on / `"0"` → 503) |
| `TV_WEBHOOK_MAX_BODY` | var (optional) | body cap in bytes (default 65536 / 64 KB) |
| R2 binding (e.g. `EVENTS`) | binding | append-only write to the one bucket |

Explicitly **absent by design:** no broker/cTrader API key, no QST credential, no account id, no
execution/permit config. There is nothing of that kind in this lane to store.

## Networking / exposure

- The Worker gets an HTTPS URL (e.g. `*.workers.dev` or a route). In Stage C it stays **dark** — the
  URL exists but **no TradingView alert points at it**, so it receives no real traffic.
- HTTPS only; any non-POST → 405; any wrong path → 404; oversize → 413.

## Cost summary

- Worker + R2 at a few events/day: **effectively free** (well within free tiers).

## Not required (and must never be added)

- No public bucket access. No execution runtime. No broker/QST/cTrader connectivity. No queue/worker
  that could forward to a trading system. No secret in code or repo.
