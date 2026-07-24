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
Four separate processes, each with a "NO BROKER / NO ORDER SUBMISSION" banner. They are launched by `ORANGE_START_SERVICES.ps1` and must never be touched by build work:

| Service   | Role                                                                 |
|-----------|----------------------------------------------------------------------|
| listener  | Connects to Telegram, receives Farouk's messages live.               |
| wire      | Watches (30s), interprets messages -> shadow campaign proposals (review-only). |
| watcher   | Evidence layer: router sweep, freezes campaigns prospectively.       |
| observer  | Read-only re-classifier of the historical archive.                   |

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

**F008 (live at time of writing):** BUY XAUUSD, entry zone 4040–4050, SL 4015, captured **LIVE_AT_ARRIVAL** with a clean prospective freeze (verified against Farouk's actual screenshot — parse was exact). It has since taken management updates (now at revision 3, msg 46098). This is a genuine clean prospective capture — one of the "count these" wins.

---

## 7. KNOWN ISSUES / FRAGILE PARTS

- **Entry-model divergence (K-064):** Lane A places legs at zone edges (worst price); Farouk fills shallow (~0.24 depth). Entry price sets break-even, which determines runner survival. P-EP-1 (legs at depth 0.15 / 0.40, no far leg) is the frozen enhanced profile. Its 0.40 leg fills only ~25% of the time and would have missed F007 — recorded as a *known characteristic*, deliberately NOT retuned (avoiding the double-dipping / fit-on-the-fitting-sample trap).
- **LIVE_EDIT deploy pending:** the fix for "edit completes a signal but the edit path never creates a campaign" is built and proven but its deploy was being held for a clean window (jumps the queue when F008 is quiet).
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
- When F008 is quiet, deploy the LIVE_EDIT fix in a clean window via the launcher.
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
