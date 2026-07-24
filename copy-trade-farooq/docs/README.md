# copy-trade-farooq (ORANGE) — sanitized handoff package

Assembled 2026-07-24, LOCAL ONLY (no remote, not a git repo push). Source:
`C:\Users\Marty\signal-terminal` on Marty's PC.

ORANGE is a **read-only** research stack that observes and reverse-engineers
Farouk's XAUUSD signalling. It is NOT a copy-trader: there is no broker order
path anywhere, enforced by hard gates (see below).

## Package layout
- `code/` — all project source (`*.py`, `*.ps1`, `*.pine`, `*.md`, `*.json`,
  `*.txt`), directory structure preserved. Excluded: venvs, node_modules,
  `data/` (evidence DBs), corpus media, derived media, logs, `*.jsonl` ledgers,
  `*.db`. One file sanitized: `campaign_extractor/ctrader_a1/tests/test_ctrader_a1.py`
  (real cTrader client id replaced with a placeholder).
- `configs/` — the main config modules + `env.template`. **Every secret has
  been stripped**; each stripped value is marked
  `# set in Windows Credential Manager / DPAPI`.
- `docs/` — this README + the repo's own key docs (`CLAUDE.md`,
  `ORANGE_MASTER_SOURCE_OF_TRUTH_vNEXT.md`, orange_brain `START_HERE.md`,
  `operator_brief.md`, original project README).
- `training-data/` — manifest only (`corpus_index_v1.jsonl`); no large media.
- `logs/` — three secret-free sample service logs from the 2026-07-24 restart.
- `requirements.txt` — pip freeze of both venvs; the main service stack is
  stdlib-only on CPython 3.14.

## What is deliberately NOT here (quarantined secrets)
- `.env` (real cTrader CLIENT_ID/CLIENT_SECRET) — receiving operator must
  provision their own via Windows Credential Manager / DPAPI.
- `whale_room.session` (Telegram auth session) — account-sensitive.
- `data/ctrader_auth_url.txt` (embeds the client id).
- All evidence/ledger databases and `data/` content.
- TELEGRAM_API_ID / TELEGRAM_API_HASH (User-scope env vars, never in files).

## Hard gates (verified 2026-07-24, ALL safe)
`MODE="PAPER"` · `LISTENER_MODE="PREVIEW"` · `EXECUTION_ENABLED=False` ·
`CTRADER_EXECUTION_ENABLED=False` · NOT_INTEGRATION_READY · no broker
connection, no order code, fail-closed on ambiguity. The connected cTrader-DEMO
transport is offline/loopback-tested only: NOT_ARMED, fixed demo endpoint,
fake credential provider, egress-guarded tests.

## Services, launcher, scheduling
Seven detached read-only services: listener, tracker, wire, watcher, companion,
shadow, observer. Launcher: `code/ORANGE_START_SERVICES.ps1` (single-instance
guarded; dry-run mode; per-service dated logs). Helpers: `ORANGE_STATUS.ps1`,
`ORANGE_BRAIN_REFRESH.ps1`, `ORANGE_START_FABLE.ps1`.

**Scheduled tasks: NONE.** A Windows Task Scheduler query (2026-07-24) found no
ORANGE/nana/signal-related scheduled tasks — all services are started manually
via the launcher after boot. Instance locks store PIDs with NO stale detection:
delete a lock only after proving its PID dead.

## Operating rules for the receiving agent
Read `docs/START_HERE.md` and `docs/CLAUDE.md` first. Never start a second
listener. Never flip a gate. The forward/freeze ledgers on the source machine
are authoritative; this package contains code and docs, not evidence.
