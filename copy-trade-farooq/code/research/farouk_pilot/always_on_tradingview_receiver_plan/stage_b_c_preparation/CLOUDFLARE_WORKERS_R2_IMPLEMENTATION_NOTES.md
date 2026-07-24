# Cloudflare Workers + R2 — Implementation Notes

**Mode: PREPARATION / DESIGN ONLY.** Notes for a *future* implementation. No Worker authored, no R2
bucket created, no deploy. Provider names are the approved direction (Cloudflare Workers + R2); an
equivalent serverless/edge + object store would follow the same shape.

## Feasibility: YES

A logging-only TradingView receiver is a **strong fit** for Cloudflare Workers + R2:

- **Workers** give an always-on HTTPS endpoint (24/7, global edge, no server to patch) — closes the
  laptop-off gap.
- **R2** is S3-compatible object storage with **no egress fees** — ideal for append-only raw event
  objects (JSONL/object-style), matching the raw-first design.
- At a few events/day this sits comfortably in **free/near-free** tiers.
- The receiver logic is tiny and pure — the Stage-2 Python receiver is the behavioural oracle; the
  Worker reproduces the same decisions.

## Shape of the Worker (LOGGING_ONLY)

Request handler (pseudocode — **not** committed code, illustration only):

```
export default {
  async fetch(request, env) {
    if (env.TV_WEBHOOK_ENABLED !== "1") return json(503, {ok:false,error:"disabled"});
    if (request.method !== "POST") return json(405, {ok:false,error:"method_not_allowed"});
    const url = new URL(request.url);
    if (!timingSafeEqual(url.pathname, "/tv/" + env.TV_WEBHOOK_SECRET_PATH))
      return json(404, {ok:false,error:"not_found"});
    const len = Number(request.headers.get("content-length") || 0);
    if (len <= 0 || len > MAX_BODY) return json(413, {ok:false,error:"bad_body_size"});
    const raw = await request.text();                 // raw-first
    const rec = buildRecord(raw, safeHeaders(request), nowUtc());  // parse = read-only metadata
    await env.EVENTS.put(objectKey(rec.event_id), toJsonl(rec));   // append-only: key on event_id
    return json(200, {ok:true, event_id: rec.event_id, validation_status: rec.validation_status});
  }
}
```

Key points:
- **PATH_ONLY auth** (Stage-2 proven; TradingView sends no custom header). Constant-time path compare.
- **Raw-first**: `request.text()` stored byte-exact; parsing is read-only metadata over a copy.
- **UTC**: `nowUtc()` = `new Date().toISOString()` (ends in `Z`).
- **Append-only R2**: `env.EVENTS.put(objectKey, ...)` keyed on **unique `event_id`** so nothing is
  overwritten. One object per event (or a per-day append object). No `delete`/overwrite path in code.
- **No outbound calls** except the R2 write. **No** `fetch()` to any broker/QST/trading host.

## R2 layout

- Bucket: private (no public access).
- Object key: `events/YYYY/MM/DD/<event_id>.jsonl` (one event per object) — immutable once written.
- Body: the single JSON record (the `raw_payload` field holds the byte-exact TradingView body).
- Optional daily manifest object listing event_ids (rebuildable; never the source of truth).

## Import firewall in a Worker context

- Workers can't import the Python engine anyway, but the discipline still holds: the Worker's code
  imports **nothing** related to broker/cTrader/QST/execution/permit; a review + grep gate confirms
  it before deploy. No `fetch()` to any trading endpoint. Bindings limited to the one R2 bucket.

## Health check

- A `GET /health` may return a static `200 {"ok":true}` with **no** secret and **no** data; it does
  not accept bodies and does not reveal the secret path.

## What is deliberately NOT in the Worker

- No decision that acts (parser is metadata-only).
- No connection to the Telegram lane.
- No broker/account credential, no order path, no sizing.

## Toolchain note (only if authorised later)

- Local dev: `wrangler dev` / miniflare bound to localhost with a local R2 for **Stage B Approach 2**
  (no deploy). Deploy: `wrangler deploy` — **Stage C, only if separately authorised.** Installing the
  toolchain is itself a step Martyn approves; Stage B Approach 1 (Python oracle) needs no install.
