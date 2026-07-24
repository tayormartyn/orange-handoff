# Farouk Session Policy v0.1

**Offline, observation-only.** What the local corpus actually supports about session windows and
timezone — and, critically, what it does **not**. **No invented rules.** `NOT_INTEGRATION_READY`
unchanged.

## Overall confidence: ⚠️ UNCONFIRMED (timezone deliberately unresolved in corpus)

The corpus **deliberately does NOT choose a canonical timezone** and BLOCKS every timezone-dependent
transition. Therefore all session labels this policy produces are **PROXIES** (`*_UTC_PROXY`) carrying
`SESSION_UNCONFIRMED` / `TIMEZONE_POLICY_UNCONFIRMED`. They must not be treated as confirmed sessions.

## Per-item findings (verbatim corpus references)

| Item | Verdict | What the corpus says | Source |
|---|---|---|---|
| **Asia window** | ❌ **UNSUPPORTED** | "Asia 00:00–07:00 UTC" is **not stated anywhere**. Asia is a **liquidity level** (Asia High/Low), not a clock window. Exact session window flagged `[OPEN]`. | `specifications/FAROUK_LEVEL_CONSTRUCTION_SPEC_v0.2.md:22`; `..._v0.1.md:25`; `FAROUK_METHODOLOGY_SPEC_v0.2.1.md:29` |
| **London** | ⚠️ **PARTIAL** | "London open (08:00 UTC)" documented in the Playbook; **no close time**; TZ "not yet reconciled with the UTC+2 chart or unknown Discord TZ". | `derived/doc_text/FP-EDU-002_playbook_text.txt:101`; `FAROUK_LEVEL_CONSTRUCTION_SPEC_v0.2.md:23` |
| **New York** | ✅ **SUPPORTED (family-scoped)** | "NY open = 13:30 UTC; NY window 13:30–15:00 UTC" — but "**NOT a system-wide timezone authority**" (NY-model-specific). | `synthesis_v0.3/FAROUK_METHODOLOGY_RULE_LEDGER_v0.3.jsonl:10` (R-NY-1330); `FP-EDU-002_playbook_text.txt:102` |
| **Timezone policy** | ❌ **UNRESOLVED (deliberate)** | "A canonical 'Farouk timezone' is **deliberately NOT chosen** (evidence conflicts…)"; `G_TZ_UNRESOLVED` = BLOCKED. Chart observed UTC+1 (video) / UTC+2 (edu); indicator field = Europe/Berlin; Discord unknown. Internal storage = UTC. | `state_machine/FAROUK_STATE_MACHINE_SPEC_v0.1.md:52-57`; `FAROUK_GUARD_CATALOG_v0.1.json` (G_TZ_UNRESOLVED, G_SESSION_WINDOW_KNOWN) |
| **DST** | ⚠️ **ACKNOWLEDGED, no rule** | Retained as `dst_context`; test TM-05 (DST boundary) = **BLOCKED**; no adjustment logic. | `state_machine/FAROUK_STATE_MACHINE_SPEC_v0.1.md:54`; `..._TEST_MATRIX_v0.1.csv:6` |

## Policy windows used by `session_context_resolver_v0_1` (ALL proxies)

| Proxy label | UTC window | Corpus support | Confidence (even if TZ confirmed) |
|---|---|---|---|
| `ASIA_UTC_PROXY` | 00:00–08:00 | **unsupported** (no corpus window) | NONE |
| `LONDON_UTC_PROXY` | 08:00–13:30 | open-only (08:00Z) | LOW |
| `NEW_YORK_UTC_PROXY` | 13:30–21:00 | window (13:30–15:00Z documented) | MEDIUM |
| `OFF_SESSION_UTC_PROXY` | 21:00–24:00 | none | NONE |

Config default: `confirmed=False`, `dst_handled=False` → **every** live label is `SESSION_UNCONFIRMED`.

## Is "Asia 00:00–07:00 UTC" supported?

**No — unsupported.** It is not in any Farouk-authored file. The only Asia UTC hours anywhere are a
tentative proxy (`00:00–07:59`), explicitly *not* a Farouk definition. Do not treat Asia as a confirmed
session window.

## Unresolved points (do not invent)

- Canonical chart/Discord timezone (conflicting evidence; BLOCKED).
- London close; full London window.
- Whether NY 13:30–15:00Z generalises beyond the NY family.
- DST adjustment across boundaries (TM-05 BLOCKED).

## Status

Policy v0.1 — proxy only, TIMEZONE_POLICY_UNCONFIRMED. Cannot satisfy the methodology scorer's
`session_context` factor until the timezone is validated (a separate, approved step). Enables no execution.
