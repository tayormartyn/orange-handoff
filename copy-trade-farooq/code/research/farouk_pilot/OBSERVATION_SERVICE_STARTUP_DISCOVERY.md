# Observation-Only Service Startup — Discovery Report

**Mode:** READ-ONLY DISCOVERY. No service started/restarted/modified. No code executed or imported.
No alerts/webhook/QST/broker/permit/lease/risk/execution change. Evidence is from documentation and
file inspection only (`README.md`, `config.py`, `ctrader_config.py`, module docstrings).

**Confirmed global safety flags (read from `config.py` / `ctrader_config.py`):**
`MODE = "PAPER"` · `EXECUTION_ENABLED = False` · `LISTENER_MODE = "PREVIEW"` ·
`CTRADER_EXECUTION_ENABLED = False` (hard lock). All execution gates **False**.

---

## Candidate 1 — Telegram listener (also the Farouk/WhaleRoom provider listener)

- **Service name:** Signal listener, Module A (Telegram) — this *is* the WhaleRoom/Farouk provider
  listener (`TELEGRAM_CHANNEL = "-1001902136163"`, the private WhaleRoom channel).
- **Exact command found:**
  - `python module_a_telegram.py` (live **PREVIEW** — prints caught messages)
  - `python module_a_telegram.py --list` (read-only: list channel names/IDs, then exits)
  - `python module_a_telegram.py --history 500` / `--history 500 --sender farouk` (read-only back-log
    of past messages → `history_review.csv`; logs nothing)
- **Source:** `README.md` §"The signal listener (Module A) — PREVIEW ONLY" (lines ~837–981, 983–1247);
  `config.py:363 LISTENER_MODE="PREVIEW"`, `config.py:376 TELEGRAM_CHANNEL`; Files table line ~1660.
- **Clearly observation-only?** YES per docs — "**preview only**, prints caught messages, not
  connected"; "does **not** parse, size, log, or trade"; "read-only to Telegram." Going live is a
  separate deliberate edit (`ENABLE TO GO LIVE` + `LISTENER_MODE="LIVE"`).
- **Touches Telegram?** YES — connects to Telegram and **reads** channel messages (network read).
- **Touches quotes?** No.
- **Touches shadow records?** No.
- **Touches broker/execution/QST?** No.
- **Required env / config:** `TELEGRAM_API_ID`, `TELEGRAM_API_HASH` (env); `telethon` installed;
  `TELEGRAM_CHANNEL` set (it is). A Telethon session file `whale_room.session` exists, so the
  one-time login may already be done; if not, first run prompts for an **interactive Telegram login
  code** (blocking).
- **Safety classification:** **SAFE_CANDIDATE** (observation-only by documentation) — with the caveat
  that it opens a live network read to Telegram and may require an interactive login. The read-only
  `--list` / `--history` sub-commands are the lowest-risk way to exercise it.

## Candidate 2 — Quote watcher / supervisor

- **Service name:** (persistent quote watcher / supervisor daemon)
- **Exact command found:** none. The quote/price tooling is **one-shot, read-only historical lookups**,
  not a running watcher:
  - `python quote_lookup.py 2026-06-25T14:42 T-C` (before/after tick + grades for one instant)
  - `python dukascopy_adapter.py 2026-06-25T14` (fetch+decode one hour)
  - `python price_cache.py 2026-06-25T14` (cache+verify one hour)
  - `python shadow_price_runner.py` (Phase 1a coverage over the 28 timestamps + GO/NO-GO)
- **Source:** `README.md` §"Shadow mode — Phase 1a" (lines ~1462–1563); Files table lines ~1662–1667.
- **Clearly observation-only?** The one-shot tools are read-only (Dukascopy HTTPS fetch of historical
  ticks; immutable hashed cache). But there is **no documented persistent "watcher" or "supervisor"
  service** to start.
- **Touches Telegram?** No. **Touches quotes?** Yes (historical, read-only).
  **Touches shadow records?** `shadow_price_runner.py` writes `data/shadow_phase1a_report.json` (a
  report, not the archive). **Touches broker/execution/QST?** No.
- **Required env / config:** none required (optional `OANDA_API_TOKEN` for the secondary cross-check;
  absent → reports "unavailable").
- **Safety classification:** **NOT_FOUND** (no persistent quote-watcher/supervisor service exists).
  The individual lookups are read-only but are batch tools, not a monitoring daemon.

## Candidate 3 — Shadow engine (observation-only mode)

- **Service name:** Shadow mode engine (Phase 1a coverage / Phase 1b executable-edge)
- **Exact command found:**
  - `python shadow_run.py --no-persist` (**report only — writes nothing**)
  - `python shadow_run.py` (full run, **persists to `data/shadow.db`**)
  - `python shadow_config.py` (print + hash the frozen assumption set)
  - `python shadow_price_runner.py` (Phase 1a coverage; writes report JSON)
- **Source:** `README.md` §"Shadow mode — Phase 1b" (lines ~1570–1643) and §"Phase 1a"; Files table
  lines ~1667–1674.
- **Clearly observation-only?** YES per docs — "PAPER mode, read-only, `EXECUTION_ENABLED` stays
  `False`, the LIVE stub is untouched." It is a **batch computation** over archived signals + cached
  price files, not a persistent engine/daemon.
- **Touches Telegram?** No. **Touches quotes?** Reads immutable Phase-1a price cache.
  **Touches shadow records?** YES — `shadow_run.py` writes `data/shadow.db`; `--no-persist` does not.
  **Touches broker/execution/QST?** No.
- **Required env / config:** none (uses the frozen `shadow_config.py` + archived data).
- **Safety classification:** **SAFE_CANDIDATE** for `shadow_run.py --no-persist` (report-only, no
  writes). The persisting `shadow_run.py` is still read-only w.r.t. broker/execution but **mutates
  `shadow.db`** (shadow records), so it is not "observation-only" in the strict no-writes sense →
  treat the plain form as **UNCLEAR_DO_NOT_START** unless a shadow-DB write is explicitly intended.

## Candidate 4 — Farouk / WhaleRoom provider listener

- **Service name:** Farouk/WhaleRoom provider listener + Farouk cohort tracker.
- **Exact command found:**
  - Provider listener = **Candidate 1** (`module_a_telegram.py`; channel is WhaleRoom). Farouk-scoped
    read-only back-log: `python module_a_telegram.py --history 500 --sender farouk`.
  - `python farouk_cohort_monitor.py` — read-only cohort tracker.
- **Source:** `README.md` listener section; `farouk_cohort_monitor.py` module docstring (inspected):
  *"READ-ONLY tracker … writes only `data/reports/farouk_cohort_one_status.{json,md}` and modifies NO
  evidence database … No recomputation of outcomes, no order/execution path."* No telegram/telethon
  or broker/execution imports.
- **Clearly observation-only?** YES for both (listener PREVIEW; cohort monitor read-only reporter).
- **Touches Telegram?** Listener: yes (read). Cohort monitor: **no**. **Touches quotes?** No.
  **Touches shadow records?** No (cohort monitor reads intake manifests + paper-observation DBs, writes
  only its two report files). **Touches broker/execution/QST?** No.
- **Required env / config:** listener as Candidate 1; `farouk_cohort_monitor.py` needs none (reads
  local `data/` stores; safely rerunnable).
- **Safety classification:** **SAFE_CANDIDATE** — `farouk_cohort_monitor.py` is the lowest-risk (no
  network, writes only report files). The provider listener inherits Candidate 1's caveats.

## Candidate 5 — Local monitoring console

- **Service name:** Status dashboard / read-only consoles.
- **Exact command found:**
  - `python status.py` (read-only dashboard: mode, risk, breaker headroom, edge, per-trader breakdown,
    execution status)
  - Supporting read-only viewers: `python review.py`, `python audit.py`, `python limits.py`
- **Source:** `README.md` §"The status dashboard" (lines ~459–489); Files table line ~1656.
- **Clearly observation-only?** YES — "**read-only** dashboard — it reads `paper_log.csv` and
  `config.py` and prints; it changes nothing, logs nothing, and places nothing." Prints
  `EXECUTION_ENABLED = False` / `LIVE TRADING DISABLED — paper only`.
- **Touches Telegram?** No. **Touches quotes?** No. **Touches shadow records?** No.
  **Touches broker/execution/QST?** No.
- **Required env / config:** none.
- **Safety classification:** **SAFE_CANDIDATE** (zero external footprint; pure read + print).

---

## Cross-checked as UNSAFE / execution-related (do NOT start)

| Command | File | Why |
|---|---|---|
| `python module_execution.py` | module_execution.py | Execution scaffold (disabled). Builds/previews a would-be order. Do not run in observation mode. **UNSAFE_OR_EXECUTION_RELATED** |
| `python ctrader_auth.py url/token/...` | ctrader_auth.py | Broker (Pepperstone DEMO) OAuth. Read-only build, but it is a **broker connection/auth** step and needs an interactive browser login → out of scope. **UNSAFE_OR_EXECUTION_RELATED** |
| `python run.py` / `pipeline.py` | run.py / pipeline.py | Interactive paper-trade logging (writes `paper_log.csv`). Not observation-only. **UNSAFE_OR_EXECUTION_RELATED** (writes trade log) |
| `python module_a_discord.py` | module_a_discord.py | Deliberately disabled stub (self-botting warning). Nothing to start. **UNSAFE_OR_EXECUTION_RELATED / disabled** |
| `python archive.py import …` | archive.py | Writes the archive DB (append). Read-only to Telegram but **mutates `signal_archive.db`** → not pure observation. **UNCLEAR_DO_NOT_START** |

No QST service/command was found anywhere in the docs or file inspection → **QST: NOT_FOUND** (nothing
to connect; consistent with prior audits).

---

## Final assessment

**1. Which observation-only service can be safely started first, if any?**
Two tiers:
- **Zero-footprint, safe to run now (read-only, no network, no writes to evidence):**
  `python status.py` and `python farouk_cohort_monitor.py`. These are consoles/reports, not
  continuous monitors.
- **The actual continuous "monitoring/evidence-capture" service:** the **Telegram PREVIEW listener**
  (`python module_a_telegram.py`) — documented observation-only, but it opens a live Telegram read and
  may need an interactive login, so it should not be started without confirmation.

**2. Exact command proposed.**
- Immediate, safe, no confirmation strictly needed (pure read): `python status.py`
  (and/or `python farouk_cohort_monitor.py`).
- For live monitoring (needs confirmation): `python module_a_telegram.py`
  (lowest-risk exercise first: `python module_a_telegram.py --list`).

**3. Why it is safe / why not confirmed.**
- `status.py` / `farouk_cohort_monitor.py`: documented + docstring-verified read-only; touch no
  Telegram/quotes/shadow/broker; no execution path; write at most local report files. **Safe.**
- `module_a_telegram.py`: documented preview-only (`LISTENER_MODE="PREVIEW"`, prints only, not
  connected to the pipeline) — but it makes a **live Telegram network read** and its first run may
  block on an interactive login code, and it depends on `TELEGRAM_API_ID` / `TELEGRAM_API_HASH` being
  present. Because it touches an external service and may need interaction, it is **not auto-started**;
  it needs your explicit go-ahead.

**4. What explicit confirmation Martyn must give before starting the listener.**
Confirm all of:
- "Start the Telegram **PREVIEW** listener only" (observation, no going live).
- `TELEGRAM_API_ID` and `TELEGRAM_API_HASH` are set in this environment (or you'll complete the login
  prompt interactively).
- You accept it will open a live read to the WhaleRoom channel and print messages (no parse/size/log).
- You understand nothing else is enabled — no webhook, no QST, no broker, `EXECUTION_ENABLED` stays
  False, `LISTENER_MODE` stays `PREVIEW`.

**5. What remains NOT_RUNNING (unchanged by this discovery).**
- Telegram listener — **NOT_RUNNING** (not started).
- Quote watcher / supervisor — **NOT_RUNNING / NOT_FOUND** (no such daemon exists).
- Shadow engine — **NOT_RUNNING** (batch tool; not started).
- Farouk cohort monitor / status console — **NOT_RUNNING** (not started).
- Broker (cTrader) / QST / execution — **NOT_RUNNING**, gates **False**.
- No webhook, no permit, no lease, no order. Risk cap unchanged.

_No service was started. This report is discovery only._
