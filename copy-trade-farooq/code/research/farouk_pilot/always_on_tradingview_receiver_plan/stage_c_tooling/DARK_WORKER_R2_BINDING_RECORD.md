# Dark Worker — R2 Binding Record

**Gate C-DEPLOY-DARK. 2026-07-07.**

## Binding

| Field | Value |
|---|---|
| Binding name (in Worker) | `EVIDENCE` |
| Bucket | `farouk-tv-webhook-evidence-v1` (private, created Gate C-R2B) |
| Declared in | `cloud_worker_dark/wrangler.toml` → `[[r2_buckets]]` |
| Confirmed at deploy | wrangler printed `env.EVIDENCE (farouk-tv-webhook-evidence-v1)  R2 Bucket` |
| Scope | **Least-privilege available**: the Worker is bound to **this one bucket only**; no other R2 bucket, no other cloud resource. |
| Usage in code | `env.EVIDENCE.put(key, body)` — write/put only. No public read, no delete path in code. |

## wrangler.toml binding block

```
[[r2_buckets]]
binding = "EVIDENCE"
bucket_name = "farouk-tv-webhook-evidence-v1"
```

## Object model (append-only)

- Key: `events/YYYY/MM/DD/<event_id>.jsonl` (one object per accepted POST; `event_id` unique → no
  overwrite).
- Body: single JSON record; `raw_payload` holds the byte-exact TradingView body; secret path redacted.
- Current objects: **0** (bucket empty; no accepted POST has occurred).

## Notes

- The binding grants the Worker access to this bucket; R2 Worker bindings are bucket-scoped by design
  (there is no other bucket or permission attached to this Worker).
- No public access / public domain is configured on the bucket → objects are reachable only via the
  authenticated account API, not publicly.
