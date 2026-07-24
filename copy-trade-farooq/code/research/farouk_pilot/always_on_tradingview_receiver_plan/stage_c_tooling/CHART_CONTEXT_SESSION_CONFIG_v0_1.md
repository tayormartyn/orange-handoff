# Chart Context — Session Config v0.1

**TENTATIVE UTC session buckets used by `chart_context_extractor_v0_1`.** These are **PROXIES**, not
confirmed Farouk session definitions. `TIMEZONE_POLICY_UNCONFIRMED`. Observation-only.

## Assumed UTC buckets

| Proxy label | UTC hours |
|---|---|
| `ASIA_UTC_PROXY` | 00:00–07:59 |
| `LONDON_UTC_PROXY` | 08:00–12:59 |
| `NEW_YORK_UTC_PROXY` | 13:00–20:59 |
| `OFF_SESSION_UTC_PROXY` | 21:00–23:59 |

## Corpus basis (and why it's still a proxy)

- The Farouk corpus cites **London open 08:00 UTC** and **NY open 13:30 UTC / window 13:30–15:00 UTC**
  (`specifications/FAROUK_METHODOLOGY_SPEC_v0.2.1.md` §2;
  `specifications/FAROUK_LEVEL_CONSTRUCTION_SPEC_v0.2.md` §B;
  `synthesis_v0.3/FAROUK_METHODOLOGY_RULE_LEDGER_v0.3.jsonl` R-NY-1330).
- **But** the chart/Discord timezone is **UNRESOLVED** (platform observed UTC+2, Discord TZ unknown), so
  the session guard fail-closes (`state_machine/FAROUK_GUARD_CATALOG_v0.1.json` G_TZ_UNRESOLVED =
  BLOCKED). We therefore do **not** claim a confirmed session — only a UTC-hour proxy bucket, always
  emitted with `TIMEZONE_POLICY_UNCONFIRMED`, and `session_context confirmed` stays in `missing_evidence`.

## Rules

- Never treat a `*_UTC_PROXY` label as a confirmed session. It cannot satisfy the scorer's
  `session_context` factor (which stays `None`/missing until the timezone policy is validated).
- Resolving this requires establishing and validating the real chart-to-UTC mapping — a separate,
  approved step (see `NEXT_CHART_CONTEXT_COLLECTION_PLAN.md`). Do **not** invent an offset.

## Status

Proxy config only. TIMEZONE_POLICY_UNCONFIRMED. Enables no execution.
