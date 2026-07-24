# MIGRATION.md — Handoff Notes

Prepared for a new agent (Captain / Kimi / OpenClaw) taking over. Written by the strategy/review side (Claude), which holds the project *knowledge* and the strategy docs. The *source code* lives in a separate builder's repo on Martyn's machine (`C:\Users\Marty\signal-terminal\...`) and must be packaged from there by that builder ("Fable" / Claude Code) — see the last section for the exact instruction. A complete handoff = this knowledge + the sanitized source, assembled together.

**Two projects are referenced by the handoff spec: `copy-trade-farooq` (a.k.a. "Orange", detailed below) and `nana-sibley`. This document covers Orange in full. Nana-Sibley was not built on the strategy/review side — its material must come from the builder repo / Martyn.** A third venture ("AI Websites for tradesmen" B2B, master template `the-gutterman-master-template.html`) was deliberately kept separate and should get its own repo, not folded in here.

---

## 0. THE ONE RULE THAT OVERRIDES EVERYTHING

This is a **read-only research system** whose eventual, human-gated goal is a **demo** (paper) copy-trader. It has **never** placed a real order and must not until an explicit, reviewed decision is made. These gates are hard and must stay exactly as written:

```
EXECUTION_ENABLED            = False   (live)
CTRADER_EXECUTION_ENABLED    = False   (live)
DEMO_EXECUTION_ENABLED       = False   (demo — flip only after sign-off)
MODE                         = PAPER
LISTENER_MODE                = PREVIEW
NOT_INTEGRATION_READY
```

No broker connection, no OAuth *trading* grant, no gate flip, no order — none of these happen without Martyn's explicit go, and safety-critical changes are reviewed by two independent reviewers before that. **Secrets never enter code, `.env`, args, shell history, stdout/stderr, logs, ledgers, reports, or git.** They live only in Windows Credential Manager / DPAPI.

---

## 0.5 INTEGRATION STATUS — CLEAR-TO-CONNECT PROTOCOL (read before touching the transport)

```
TRANSPORT_STATUS      = OFFLINE_VERIFIED — BOTH REVIEWERS PASS; offline prerequisite CLOSED (2026-07-24)
CLEAR_TO_CONNECT      = FALSE
CONNECT_APPROVAL      = (none — this block is empty and unsigned)
```

**A reviewer PASS on the connected transport means it is offline-correct. It does NOT mean clear to connect, integrate, or flip any gate.** Even after Chuck's final PASS, the transport is verified against fakes/loopback only and has never touched a broker.

You (the incoming agent) may **read, audit, and propose or build OFFLINE improvements** to the transport. You may **not** wire it toward any live or demo connection until this section carries a signed `CONNECT_APPROVAL` block. There is no implicit "clear to integrate" flag anywhere else — this is the only place it can be granted, and right now it is empty.

Before `CLEAR_TO_CONNECT` can become TRUE, **all** of the following must be separately completed and independently reviewed (see §9): real ProtoCodec wired to the live channel; DPAPI credential provider; live-channel composition wiring; the immutable read-only Pepperstone preflight binding; elevated ACL apply; reboot/uptime evidence. Then, and only then:
1. Both reviewers (Claude + Chuck) sign off in writing.
2. Martyn gives explicit authorization in chat.
3. A dated `CONNECT_APPROVAL` block is written here recording who signed, what prerequisite set was completed, and that it is **DEMO only** (`DEMO_EXECUTION_ENABLED` flips to True; the live gates `EXECUTION_ENABLED` / `CTRADER_EXECUTION_ENABLED` stay False **forever** at this stage).

Until that block exists and is signed, treat the transport as audit-only. Gates stay ALL_FALSE regardless of any test result.

---

## 1. WHAT THE PROJECT IS

Reverse-engineers a trader ("Farouk", XAUUSD / gold) copy-trading method from his published signals, education material, and live campaigns, in order to (a) learn his real entry & management method, and (b) eventually run it safely on a **Pepperstone demo** account with a human approval gate — never confusing a good demo run with a real edge.

**The people/agents in the loop:**
- **Martyn** — owner/operator. Not a developer; needs plain, step-by-step guidance. Is the human approval gate.
- **Claude (this side)** — strategist + adversarial reviewer. Writes specs, reviews builds, holds the knowledge.
- **Chuck (ChatGPT)** — second independent reviewer. Safety-critical work passes both reviewers.
- **Fable (Claude Code)** — the engineer, works directly in the repo.
- **New agent (Kimi/OpenClaw)** — incoming; this handoff is for them.

---

## 2. NON-NEGOTIABLE SAFETY CONCEPTS (do not violate)

**Source tiers — never merge or promote between them:**
```
PUBLISHED_FOLLOWER_METHOD          (what free followers see)
ADVANCED_EDUCATION_METHOD          (paid education)
PERSONAL_LIVE_METHOD_UNCONFIRMED   (inferred from his live trades — unconfirmed)
```

**Objective lanes — never cross-contaminate:**
- **Lane A** — strict follower method (Constitution v0.1). Shadow-tracked, unchanged, in parallel.
- **Lane B** — "Farouk-Plus" enhanced (entry profile P-EP-1).
- **Lane C** — independent detector.

**Prospective capture discipline:** a campaign's decision must be **frozen at T=0 (arrival) before any outcome is known**. No backdating, ever. Retrospective data may *screen/reject* hypotheses but may **never confirm** one or be used to fit a model. Confirmation comes only from live prospective campaigns.

**Fail-closed / silent-absence:** the recurring bug class. A parser miss, a dead listener, an ambiguous send, a timeout, an edit that completes but creates no campaign — anything that could *silently do nothing* — must instead alarm loudly and hold state. Ambiguity never guesses; it stops and reconciles.

**Two-reviewer rule:** safety-critical work (anything touching execution, transport, credentials) is reviewed independently by Claude and Chuck before it is accepted.

---

## 3. CONSTITUTION v0.1 (Lane A management rules)

- Three legs per entry zone: near / mid / far.
- Unscoped "SL to entry" = per-leg break-even; it does **not** cancel unfilled legs.
- "take some" = 25%.
- Explicit "close X% leave Y%" uses the stated percentages.
- Ambiguous instructions fail closed → raise for human review, never guess.

---

## 4. ARCHITECTURE

### 4a. Live research services (always-on, read-only)
Four separate processes, each with a "NO BROKER / NO ORDER SUBMISSION" banner. They are launched by `ORANGE_START_SERVICES.ps1` (confirmed at `copy-trade-farooq/code/ORANGE_START_SERVICES.ps1` — note it **hard-codes machine paths** `$PY=C:\Python314\python.exe` and `$ROOT=C:\Users\Marty\signal-terminal`; adjust both for any other checkout). They must never be touched by build work. (`FA` below = `copy-trade-farooq/code/research/farouk_pilot/always_on_tradingview_receiver_plan/stage_c_tooling/farouk_plus/follower_assistant`.)

| Service   | Repo file / launch command | Role                                                     |
|-----------|----------------------------|----------------------------------------------------------|
| listener  | `code/module_a_telegram.py` — `python -u module_a_telegram.py` (from `code/`, no lock) | Connects to Telegram, receives Farouk's messages live. |
| wire      | `FA/live_wire.py` — `python -u live_wire.py --watch` (from `FA/`, lock `live_wire.instance.lock`) | Watches (30s), interprets -> shadow proposals (review-only). |
| watcher   | `FA/evidence_layer/evidence_watcher.py` — `--watch` (from its dir) | Evidence layer: router sweep, prospective freeze. |
| observer  | `FA/intake_reliability/intake_observer.py` — `--watch` (from its dir) | Read-only re-classifier of the archive. |

Each service resolves its instance lock and cursor **from its own working directory** — run each from its own folder. `live_wire_v2.py` / `interpreter_v2.py` are the staged morphology-v2 variants; the launcher does **not** run them.

**Lock discipline:** each service holds an instance lock with its PID. On restart, if a lock holds a *dead* PID, you must **prove the PID is gone AND no matching python process is running** before cleaning the lock — otherwise you risk two listeners fighting over Telegram.

**Silent-death mitigation:** an independent heartbeat/liveness monitor (`listener_liveness.py`) alarms on *absence* of activity. This exists because the listener once died overnight (ConnectionError) and was only noticed hours later. Recovery rule after a death: **recover forward, never backfill** into the prospective store.

### 4b. Interpretation / routing
- `interpreter.py` — `is_farouk_gold` gate (filters to XAUUSD only; a BTC post is correctly ignored), plus classification.
- `strategy_router.py` — `freeze_router`, prospective freeze.
- `_emit_campaign(...)` — single source for campaign creation (refactored to close the "edit-completion creates no campaign" hole).
- `edit_completion_guard.py` — guards the edit path.

### 4c. Demo execution lane (built, gated OFF)
`demo_lane/` package: `executor.py`, `order_adapter.py`, `protobuf_mapper.py`, `mock_broker.py`, `sizing.py` (fixed 0.01 lot, no dynamic sizing), `gate.py`, `reconcile.py`. **The executor is deliberately network-incapable** (proven by a socket "booby-trap" test — importing the executor with a booby-trapped socket must not connect). Evidence separation is strict: demo results write to their own ledger tagged `record_class=DEMO_EXECUTION`, `eligible_for_prospective_evidence=false`, `eligible_for_training=false`. Demo activity must never alter the Lane A shadow ledger.

### 4d. Connected transport (`demo_lane/connected_transport/`) — just completed, offline only
The cTrader OpenAPI transport, built and verified **entirely offline** (loopback/fakes, no real connection) across several adversarial review rounds with Chuck. As of this writing it passes **152/152** transport-suite tests plus proto-codec (27) and TLS-channel (17). Components:
- **Real protobuf codec** — canonical request -> ProtoMessage envelope (payloadType + clientMsgId) -> serialized protobuf -> 4-byte TCP length prefix; inbound reverse. Uses the accepted offline mapper.
- **TLS channel** — loopback-tested; production policy is fixed host `demo.ctraderapi.com:5035`, cert + hostname validation required, no insecure mode, no override.
- **Auth + account guard** — state sequence `CONNECTED -> APPLICATION_AUTHENTICATED -> ACCOUNT_LIST_RECEIVED -> ACCOUNT_VALIDATED -> ACCOUNT_AUTHENTICATED -> RECONCILE_ONLY -> READY`. Will not authenticate an account until the account-list proves: one allowlisted account, exact ID, `isLive==false`, expected demo environment, expected scope. Anything off -> sanitised alarm + `NOT_ARMED`.
- **Ambiguous-send safety** — a send exception does NOT prove zero bytes sent. Only pre-transmit failures = `DEFINITELY_NOT_SENT` (may forget the correlation); anything during/after transmit = `OUTCOME_UNKNOWN` (retain correlation, no auto-retry, invalidate READY, disconnect, reconcile before any resend).
- **Single I/O owner** — one thread owns the socket: continuously reads, deframes, routes by clientMsgId, consumes async fills/events even when idle, auto-heartbeats <=10s, one outbound queue, deterministic reconnect. Callers submit work and await a future; they never call recv.
- **Response-timeout fail-closed** — a timeout never leaves the transport READY; it resolves atomically (exactly once, never both a response and OUTCOME_UNKNOWN), holds the correlation, and forces reconnect + full auth + reconciliation before any further action.
- **Broker-identity honesty** — `PEPPERSTONE_ACCOUNT_BINDING = PENDING_READ_ONLY_PREFLIGHT`; the code must not claim broker identity is proven when it only compared a config value with itself. The real read-only preflight creates the immutable sanitised binding the connected system later validates.

---

## 5. SERVICES / APIs USED

- **Telegram** — live signal source (listener). Uses a Telegram session/API credential (stored locally, NOT in repo).
- **cTrader OpenAPI** — target broker API. **View-only scope (`accounts`) only** for research; a *trading* scope would only ever be for the eventual gated demo-exec and does not exist yet. Endpoint `demo.ctraderapi.com:5035`. Not connected.
- **Pepperstone demo** — the demo account the copy-trader would eventually run on. A read-only preflight has previously connected to confirm the account is view-only; no trading.

**Credentials needed by a future operator (names only — values live in Windows Credential Manager / DPAPI):** Telegram API id/hash + session; cTrader OpenAPI client_id/secret (view-only app; the earlier accidental *trading*-scope app was revoked); cTrader access token (view-only).

---

## 6. CAMPAIGN LEDGER & CURRENT STATE

Campaigns are `XAU-Fnnn-YYYYMMDD`. Recent: F002 (0714), F004 (0716), F007 (0721), **F008 (0724)**. Terminal outcomes so far are mostly BE-scratch. F001/F002 are non-analytical backfill and must never be fit as training.

**Where the records live (authority order matters):** the per-campaign *cards* (JSON + markdown, F001–F008) are in the repo at `FA/cards/XAU-Fnnn-YYYYMMDD.json`. The **authoritative append-only ledgers are NOT in the repo** (deliberately excluded; source machine only): the forward ledger (`…/farouk_plus/forward_validation_ledger_v0_2.jsonl`), the genuine prospective freeze ledger (`FA/evidence_layer/router_freeze_v0_1.jsonl`), plus `follower_ledger_v0_1.jsonl`, `evidence_layer/entry_refusals_v0_1.jsonl`, `pre_mark_candidates_v0_1.jsonl`. **On any disagreement the ledgers win over the cards** — the cards are for reading; the ledgers are the evidence of record.

**F008 — OPEN (as of 2026-07-24):** LONG XAUUSD, entry zone 4040–4050, posted SL 4015, captured **LIVE_AT_ARRIVAL** (08:34:31Z) with a clean prospective freeze (verified against Farouk's actual screenshot — parse was exact). Forward ledger holds 4 `XAU_F_SETUP` records, latest **revision 4, no terminal yet**. Management applied: **TP1_TAKE** (msg 46097, 08:44Z) then **SL_TO_ENTRY** (msg 46098, 09:02Z) — so it is **break-even-protected and awaiting a terminal**. A genuine clean prospective capture — one of the "count these" wins.

---

## 7. KNOWN ISSUES / FRAGILE PARTS

- **SECURITY INCIDENT (2026-07-24) — TradingView webhook path leak:** the first repo push accidentally included 5 `cloud_worker_dark/` files holding the live TradingView webhook **secret path** (`LOCAL_SECRET_webhook_path.txt` + 4 related). Both secret scans missed them — the secret is a URL *path*, not a key shape, and the filename check missed the uppercase `LOCAL_ONLY_*` names. Repo history was rebuilt to a clean commit (`08a0627`, force-pushed); token no longer retrievable from the repo. **But Kimi's first zip contains it → treat the webhook path as exposed and ROTATE it** (new secret path on the Cloudflare Worker + manually update the TradingView alerts). Impact is contained: the worker is write-only logging (no read branch), gives no money/broker/account access — worst case is fake-data injection into the research feed. **Scan-hardening lesson:** the secret scan must also flag URL-path secrets and uppercase `LOCAL_SECRET`/`LOCAL_ONLY` filenames, not just credential-shaped tokens.
- **Entry-model divergence (K-064):** Lane A places legs at zone edges (worst price); Farouk fills shallow (~0.24 depth). Entry price sets break-even, which determines runner survival. P-EP-1 (legs at depth 0.15 / 0.40, no far leg) is the frozen enhanced profile. Its 0.40 leg fills only ~25% of the time and would have missed F007 — recorded as a *known characteristic*, deliberately NOT retuned (avoiding the double-dipping / fit-on-the-fitting-sample trap).
- **LIVE_EDIT fix — NOW LIVE (2026-07-24), deployed by the reboot ahead of plan:** the fix for "edit completes a signal but the edit path never creates a campaign" is committed and proven (fixed `live_wire.py`, sha `a8cc4706…`, evidence pack D-106; tests D-108). It was *held* for a planned Phase-B deploy (F008 closed → clean window → review), but this morning's post-reboot restart loaded the fixed on-disk `live_wire.py`, so it has been **running live since the 2026-07-24 restart** — the reboot executed the deploy early. Files in repo: `FA/live_wire.py`, `…/parser_replay/edit_completion_guard.py` (+ tests), `FA/tests_edit_completion_lookup.py`, `FA/tests_live_wire.py`, evidence `FA/LIVE_EDIT_COMPLETION_FIX_PACK.txt`. **Process note (for reviewers):** the build was already proven and the wire behaved correctly under it (F008 captured + managed today), so this is not dangerous — but it is an *unplanned deploy* and both reviewers (Claude + Chuck) should formally acknowledge/record it rather than let it be discovered later.
- **Fragile-token rules to re-verify:** FR-027, FR-056, FR-008, FR-051, FR-058 need re-validation with fixed-pipeline audio clips (an earlier transcript-timestamp -> real-audio misalignment was root-caused and fixed; re-validation was queued).
- **Operator-ear discipline:** some rules require a human to *actually listen* to clips; AI-transcribing then AI-checking defeats the independent-ear purpose. Keep the human in that loop.

---

## 8. WHAT I WAS WORKING ON WHEN INTERRUPTED

1. **Transport final sign-off:** the connected transport's last two-gap corrections passed (152/152); the review bundle was being sent to Chuck for what should be the final PASS. When Chuck signs off, the transport is engineering-complete.
2. **GitHub consolidation:** preparing to push everything (code + docs + distilled knowledge) into a **private** repo, with a mandatory secret-scan before the first push. (Raw chat transcripts must NOT be pushed — they contain a credential Martyn pasted earlier; distill the knowledge instead, which is what this document does.)

---

## 9. TODO / NEXT STEPS

**Transport: DONE.** Both reviewers PASS; offline transport prerequisite CLOSED (2026-07-24). Do NOT reopen the offline transport architecture or add further mock transport work unless a concrete defect appears in real-environment testing. (Housekeeping only: update README connected-transport count 71 -> 108.)

**Authorized next work — may proceed in PARALLEL, all OFFLINE / view-only, all gates stay False:**
1. Complete the real view-only Pepperstone preflight and the immutable account/symbol binding.
2. Perform the previously approved elevated ACL Apply + Verify using the corrected inbox/sealed-store and DPAPI-bootstrap design.
3. Build the DPAPI credential provider and final production composition OFFLINE — all gates False, no external connection.
4. Continue OQ-7 reboot/autostart evidence.
Return next with whichever of these produces genuine real-world evidence first. Do not produce another transport design review.

**Still prohibited (unchanged):** real trade-capable cTrader connection; OAuth `scope=trading`; `DEMO_EXECUTION_ENABLED=True`; any demo order; any live order. None of these happen without the signed CONNECT_APPROVAL block in §0.5, two-reviewer sign-off, and Martyn's explicit go.

**Other standing items:**
- LIVE_EDIT fix is now DEPLOYED (loaded on the 2026-07-24 reboot restart, ahead of the planned Phase-B sequence). Reviewers to acknowledge/record the unplanned deploy; confirm the wire keeps behaving correctly under the fixed build.
- Re-verify the five fragile-token rules (FR-027 / FR-056 / FR-008 / FR-051 / FR-058) with fixed-pipeline clips.
- Never flip to real money until a genuine prospective sample shows positive expectancy after costs. The dangerous moment is when the demo looks brilliant.

---

## 10. DEPENDENCIES

Python (two interpreters used for repeat-stable test runs; one under a `venv-ctrader`). Protobuf (cTrader OpenAPI generated classes). Telethon or equivalent for Telegram. PowerShell launcher + Windows DPAPI / Credential Manager for secrets and ACL provisioning. Fable should emit the exact `requirements.txt` when it packages the code (see below).

---

## 11. FABLE CODE-PACKAGING INSTRUCTION (run this in the builder repo to complete the handoff)

> Package the Orange source into a handoff, SANITIZED. Do NOT push anywhere and do NOT include secrets.
> 1. Assemble `handoff/copy-trade-farooq/` with: `code/` (all source), `configs/` (config files with EVERY key/token/secret/password stripped and replaced by `# set in Windows Credential Manager / DPAPI`), `docs/` (existing docs + a repo README), `training-data/` (a manifest, not large media), `logs/` (a few secret-free sample logs).
> 2. Run a full-tree SECRET SCAN first: grep for client_id/secret shapes, access tokens, "secret", "password", private-key headers, the known cTrader credential string, and any `.session`/`.env`. Report every hit; quarantine anything sensitive; do NOT include it.
> 3. Emit `requirements.txt` (and any package manifest). List cron/scheduled tasks and the service launcher.
> 4. Report: files staged, the full secret-scan result, and confirmation that gates remain ALL_FALSE and no live service was touched.
> STOP there — no push, no remote, no gate flip, no order. Delivery method (private GitHub repo URL, or a zip) will be provided separately.

Merge Fable's `handoff/copy-trade-farooq/{code,configs,training-data,logs}` output into the same tree as this document's `docs/` and MIGRATION.md, and that is the complete Orange package.
