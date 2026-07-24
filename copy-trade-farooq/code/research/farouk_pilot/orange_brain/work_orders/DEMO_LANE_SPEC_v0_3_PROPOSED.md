# DEMO LANE SPECIFICATION v0.3.1 — PROPOSED FOR RATIFICATION

**Status: PROPOSED_FOR_RATIFICATION — NOT AUTHORISED, NOT BUILT, NOT EXECUTED.**
Second-reviewer verdict on v0.3: **SIGN_OFF_WITH_THREE_FINAL_CORRECTIONS** (concept approved; build still NOT authorised). v0.3.1 incorporates the three final corrections (see the v0.3.1 FINAL CORRECTIONS block below, which AMENDS the sections it touches). v0.3 had already incorporated all 13 required corrections from the v0.2 round.

## v0.3.1 FINAL CORRECTIONS (this round — take precedence where they amend an earlier section)

**F1 — Exact volume, no rounding EITHER way (amends correction 3 / §5).** Rounding DOWN is not safe: it makes the traded quantity differ from the ratified quantity, silently breaking the correction-4 approval binding — an INTERNAL-CONSISTENCY fix, not a tightening. Volume must satisfy **ALL of: >= minVolume; <= maxVolume; (volume % stepVolume) == 0; AND == the exact ratified nominal.** Any failure → **halt, no order.** No broker-minimum substitution unless that exact minimum was shown to Martyn and ratified as the nominal.

**F2 — LIMIT-only vs risk-reducing closure was a FLAT CONTRADICTION in our own spec (amends §6a/§12b).** "LIMIT only, no market fallback" + "partial fill without verified stop: close the filled quantity" is impossible — a position cannot be closed with a limit order. **Caught by the second reviewer as a contradiction, not a tightening.** Fix as written: **LIMIT-only governs OPENING placement.** `ProtoOAClosePositionReq` is permitted **solely to reduce or close a positively-identified Orange-owned position** — never to open, increase, reverse, exceed owned quantity, or touch anything unknown. All invariant wording and tests updated accordingly. Proof tests added (§10.5), verbatim as issued:
- partial fill without stop can be closed without opening/reversing;
- kill containment closes only known Orange-owned quantity;
- excessive close quantity is rejected;
- unknown position remains no-touch.

**F3 — Human approval authority separation (architectural, the most important).** As specified the executor could write `DEMO_APPROVED` itself — human approval enforced by convention, not architecture. Implement exactly:
- The executor may write `DEMO_APPROVAL_REQUEST` and must be **TECHNICALLY INCAPABLE of writing or modifying `DEMO_APPROVED`.**
- A **separate operator-approval tool** requiring explicit Martyn action writes `DEMO_APPROVED`.
- **Separate directories with Windows ACLs** — the executor's account has no write permission to the approval directory; the approval tool's account has no order-placement capability.
- Approval binds the **fourteen plan fields (correction 4) PLUS a single-use nonce, the approval-record hash, the approval-tool version, expiry, and an atomic consumed-state.**
- Lifecycle: **REQUESTED → MARTYN_APPROVED → ATOMICALLY_CONSUMED → EXPIRED/COMPLETED.**
- **Reused, modified, duplicated, expired, or partially-consumed approvals FAIL CLOSED.**
- Proof tests added (§10.5), verbatim as issued:
  - executor cannot create approval;
  - approval-tool creates correctly bound approval;
  - modified approval rejected;
  - replayed approval rejected;
  - expired approval rejected;
  - simultaneous consumption produces at most one successful consumer.

**OPERATIONAL IMPLICATION FOR MARTYN (F1):** the nominal quantity must convert **EXACTLY** to a valid protocol volume. **The nominal will be shown to you and ratified as an exact figure.** If a chosen nominal does not convert exactly (fails any of the four F1 conditions), **the lane HALTS — no trading until it is corrected.** This is deliberate friction, chosen over trading a quantity nobody approved.

**RECORD:** the second reviewer has now found **seven genuine errors across two rounds**, including **one flat internal contradiction** (F2). Kept on the record as continued vindication of the two-reviewer requirement.

---

*(v0.3 body below — the 13 corrections from the v0.2 round. F1/F2/F3 above amend §5, §6a/§12b, and §4 respectively.)*

---

## THE 13 REQUIRED CORRECTIONS — VERBATIM + INCORPORATION

**1. Account discriminator.** *"Replace accountType == DEMO. Required conjunction: endpoint == demo.ctraderapi.com; ProtoOACtidTraderAccount.isLive == false; ctidTraderAccountId == exact allowlisted demo account; broker/environment == expected Pepperstone demo; permissionScope == SCOPE_TRADE. ProtoOATrader.accountType is HEDGED/NETTED classification and must not be used as the live/demo test."*
INCORPORATED (§3): the executor arms only when ALL five hold, re-checked at startup and before every order call; any failure → NOT_ARMED + loud alarm + no order path. `accountType` is never used as the live/demo test. Refusal unit-tested against a mocked `isLive==true` and a wrong-`ctidTraderAccountId`.

**2. Credential handling.** *"Add secure OAuth/token handling: no secret/token in repository, env files, logs or ledgers; Windows-protected credential storage; one dedicated demo account only; redaction tests; documented revocation."*
INCORPORATED (§12a NEW): tokens/secrets never in repo, env files, logs, or ledgers; stored via Windows-protected credential storage (DPAPI/Credential Manager); one dedicated demo account only; redaction tests prove no token reaches any log/ledger; a documented revocation procedure. OAuth trade-scope grant is Martyn's own action, deferred to activation, never stored.

**3. Sizing conversion.** *"Replace blind '0.01 lots' encoding with a ratified symbol-metadata conversion: read symbolId, lotSize, minVolume and stepVolume; state exact protocol volume per leg; never round upward; halt on any mismatch; cap aggregate volume across the three legs."*
INCORPORATED (§5): read `symbolId`/`lotSize`/`minVolume`/`stepVolume`; compute exact protocol volume per leg quantised to a valid `stepVolume` multiple ≥ `minVolume`; **never round upward** (round down or halt); halt on any metadata mismatch; enforce an aggregate-volume cap across the (max three) legs.

**4. Approval binding.** *"Bind every single-use campaign approval to: campaign ID, T=0 freeze hash, approved account ID, symbol ID, direction, exact entries, stop, volume per leg, maximum aggregate volume, source message IDs, executor/version hash, approval timestamp, approval expiry, placement deadline. Any difference invalidates approval."*
INCORPORATED (§4): the DEMO_APPROVED token carries all fourteen bound fields; the executor re-verifies every field at placement time and **any difference invalidates the approval** (no order, alarm). Approval is single-use, per-campaign, non-rolling.

**5. Gate truth table.** *"Add a formal gate truth table. Prove DEMO_EXECUTION_ENABLED cannot create a path to any live endpoint or live account, and does not silently weaken the meaning of EXECUTION_ENABLED or CTRADER_EXECUTION_ENABLED."*
INCORPORATED (§2a NEW): a formal truth table over {`EXECUTION_ENABLED`, `CTRADER_EXECUTION_ENABLED`, `DEMO_EXECUTION_ENABLED`} × {endpoint, isLive} proving (a) no combination yields a live-endpoint/live-account path, (b) `DEMO_EXECUTION_ENABLED=True` requires demo-endpoint + isLive==false to do anything, (c) the two live gates retain their exact prior meaning (demo gate is AND-composed, never overrides). Encoded as an enforced test.

**6. LIMIT-only, protection-at-request.** *"Restrict v0.1 execution to resting LIMIT orders only. Every order must carry protection in the initial request. No market-order fallback. No place-then-protect path. Reconcile after acceptance/fill and verify broker-reported stop. Partial fill without verified stop: cancel remainder, close filled quantity, alarm, halt. A stop-widening instruction requires fresh human approval."*
INCORPORATED (§6a rewritten): **resting LIMIT orders only**; the protective stop is in the **initial order request** (no place-then-protect, no market fallback); after acceptance/fill the executor **reconciles and verifies the broker-reported stop**; a **partial fill without a verified stop → cancel remainder, close the filled quantity, alarm, halt**; a **stop-widening instruction requires fresh human approval** (narrowing/BE under a Lane-A instruction is allowed; widening/removal fails closed).

**7. Idempotency / outbox.** *"Do not treat clientOrderId as server-guaranteed exactly-once protection. Add a durable order-intent/outbox state machine. A lost response after sending must enter OUTCOME_UNKNOWN and reconcile before any retry."*
INCORPORATED (§7): durable order-intent/outbox (INTENT_WRITTEN → SENT → ACKED / **OUTCOME_UNKNOWN**), persisted before send, survives restart; a lost/timed-out response → OUTCOME_UNKNOWN → **reconcile against broker state before any retry**, never blind-resend. `clientOrderId` is a correlation aid only, not the exactly-once guarantee.

**8. Reconciliation policy + exclusive account.** *"Resolve reconciliation policy: known Orange-owned mismatch = cancel/flatten owned exposure + alarm + halt; unknown broker order/position = alarm + halt + NO TOUCH. Require an Orange-exclusive dedicated demo account with no manual trades or other bots."*
INCORPORATED (§7a NEW): **known Orange-owned mismatch → cancel/flatten owned exposure + alarm + halt; unknown broker order/position → alarm + halt + NO TOUCH.** Requires an **Orange-exclusive dedicated demo account** — see Operational Implication A.

**9. Disconnect semantics.** *"Correct disconnect semantics. A disconnected process cannot promise immediate flattening. It must halt locally, rely on broker-side stops, alarm, reconnect, reconcile first and remain NOT_ARMED until safe."*
INCORPORATED (§6 rewritten): on disconnect/fault — **halt locally, rely on broker-side stops, alarm, reconnect, reconcile FIRST, remain NOT_ARMED until proven safe.** The impossible "flatten on disconnect" is removed; broker-side stops (§6a) are the disconnect protection.

**10. Order expiry / stale-order protection.** *"Add order expiry and stale-order protection. Approval expiry prevents placement. Terminal campaign state cancels pending entries. Restart cannot revive expired/cancelled orders. No pending order may drift into another campaign without fresh approval."*
INCORPORATED (§10a NEW): approval expiry + placement deadline block late placement; a terminal campaign state (incl. the new XAU_F_TERMINAL_OUTCOME/adjudication marker) cancels its pending entries; restart reconciliation **cannot revive expired/cancelled orders**; no pending order may drift into another campaign without fresh approval.

**11. Domain-specific evidence eligibility.** *"Replace generic evidence exclusion with domain-specific eligibility: eligible_for_strategy_expectancy=false; eligible_for_model_training=false; eligible_for_candidate_ranking=false; eligible_for_freeze_evidence=false; eligible_for_execution_fidelity_analysis=true. Add negative tests proving existing research/dataset readers cannot ingest the demo ledger."*
INCORPORATED (§8 rewritten): every demo record carries the five explicit flags exactly as specified (expectancy=false, training=false, ranking=false, freeze=false, **execution_fidelity=true**); **negative tests** prove the existing expectancy/ranking/freeze/training readers reject/ignore the demo ledger.

**12. Immutable safety caps.** *"Add immutable safety caps: XAUUSD only; LIMIT only; one approved campaign at a time; maximum three entry orders; exact capped volume; no upward rounding; no pyramiding; no reverse trade; no quantity-increasing modification; no unprotected position."*
INCORPORATED (§12b NEW, immutable): XAUUSD only · LIMIT only · one approved campaign at a time · max three entry orders · exact capped volume · no upward rounding · no pyramiding · no reverse trade · no quantity-increasing modification · no unprotected position. Enforced as hard invariants, each with a test.

**13. Proof tests.** *"Include proof tests for: live endpoint refusal; isLive=true refusal; wrong account-id refusal; wrong OAuth scope refusal; unit-conversion mismatch; approval-hash mismatch; expired approval; response-lost-after-placement; partial fill without stop; hard process death with broker stop surviving; restart reconcile-before-action; unknown broker order no-touch; stale pending-order cancellation; demo-ledger exclusion from all strategy evidence."*
INCORPORATED (§10.5 — the fourteen required proof tests, each with a recorded proof run before `DEMO_EXECUTION_ENABLED` can flip):
1. live endpoint refusal
2. isLive=true refusal
3. wrong account-id refusal
4. wrong OAuth scope refusal
5. unit-conversion mismatch (symbol-metadata) → halt
6. approval-hash mismatch → approval invalidated
7. expired approval → placement blocked
8. response-lost-after-placement → OUTCOME_UNKNOWN + reconcile-before-retry
9. partial fill without stop → cancel remainder, close filled, alarm, halt
10. hard process death with broker stop surviving (and executing if the level trades)
11. restart reconcile-before-action (NOT_ARMED until reconciled)
12. unknown broker order → no-touch (alarm + halt)
13. stale pending-order cancellation (terminal state / expiry)
14. demo-ledger exclusion from all strategy evidence (negative tests on every research/dataset reader)
Each maps to a correction above (1→#1, 2→#1, 3→#1, 4→#1/#2, 5→#3, 6→#4, 7→#10, 8→#7, 9→#6, 10→#6a, 11→#9, 12→#8, 13→#10, 14→#11).

---

## OPERATIONAL IMPLICATIONS FOR MARTYN — STATED PLAINLY (corrections 8 + 12)

**A. Orange needs an EXCLUSIVE dedicated demo account.** Orange-only. **Martyn must not manually trade it, and no other bot may touch it.** Any position Orange did not place is an *unknown position* → §7a unknown-position halt (alarm, no touch, stop). Hard precondition: a fresh Pepperstone demo used for nothing else.

**B. ONE approved campaign at a time.** The demo lane accepts only one approved campaign concurrently; **if two Farouk campaigns overlap, it takes ONLY THE FIRST.** Realistic, not hypothetical — **F006→F007 were 17.6h apart.** Known limitation, not a surprise: during overlap the demo lane's coverage is a strict subset of Lane A's paper coverage, and the second campaign is demo-invisible until the first closes.

---

## UNCHANGED FROM v0.2 (still in force)
Purpose/scope (XAUUSD-only instrumentation lane, per-campaign human approval); the separate `DEMO_EXECUTION_ENABLED` gate (default False) with `EXECUTION_ENABLED`/`CTRADER_EXECUTION_ENABLED` hard False and untouched; separate executor process (seven live services never gain broker code); §8 separate non-evidential `demo_execution_ledger`; §10 prerequisites (incl. terminal-marker 4a and the host-death test suite); §11 out-of-scope. All await ratification.

## What is NOT authorised by this document
No executor build; no trading-scope OAuth; no gate flip; no order. Returns for second-reviewer sign-off once the remainder of correction 13 is received and incorporated verbatim.

---

# FINAL_SECOND_REVIEWER_ADDENDUM_001 (appended verbatim; TAKES PRECEDENCE where it conflicts with existing text — spec body NOT rewritten)

Second-reviewer verdict: SIGN_OFF_WITH_FINAL_MANDATORY_ADDENDUM. Spec text conditionally ratified; a BOUNDED implementation build is authorised once this addendum is appended. Live execution remains prohibited absolutely.

**Item 1 — approval immutability vs consumed-state (resolves a contradiction in F3).** F3 required the approval to be BOTH immutable AND to carry a consumed-state the executor must write — impossible. Resolution: the approval record is immutable and operator-tool-owned; CONSUMPTION is recorded in a SEPARATE executor-owned consumption RECEIPT (the executor never mutates the approval). Strict ordering, enforced: (a) validate the approval against the fourteen plan fields + nonce + approval-record hash + tool version + expiry; (b) atomically create the consumption receipt (single-winner); (c) write the durable order intent (outbox); (d) ONLY THEN send the broker request. **Failed receipt persistence MUST block the request** (no receipt → no order intent → no send).

**Item 2 — resting-order host-death protection (a genuine GAP, not a tightening).** section 6a protected FILLED positions against host death via broker-native stops, but nothing protected RESTING limit orders: a GTC limit at the broker is indefinitely fillable with nobody watching. Resolution: every resting entry order is placed **GOOD_TILL_DATE**, with the expiry **bound into the approval and the plan hash** (the same expiry that governs placement governs the order's broker-side lifetime). GTD is the resting-order counterpart to the broker-native stop for filled positions.

**Item 3 — silent normalization detection.** A broker may quietly adjust price to tick size or minimum stop distance and ACCEPT the order. Resolution: after acceptance, perform **exact-equality reconciliation on all seven fields** (symbol, side, type, volume, entry price, stop price, expiry) between the sent request and the broker-reported order; ANY inequality → treat as silent normalization → cancel/close as owned + alarm + halt. Acceptance alone is never trusted.

**Item 4 — remove the stale correction-13-outstanding statement.** Correction 13 is complete; any residual "AWAITING"/"truncated"/"outstanding" wording for item 13 is void.

RUNNING TALLY (for the record): TEN genuine corrections across three review rounds — including one flat internal contradiction (F2) and two gaps neither the primary reviewer nor the builder identified (addendum items 1-contradiction and 2-gap; item 3-silent-normalization). Standing justification for two-reviewer sign-off on any safety-critical document.

BOUNDED BUILD AUTHORISED (this round only): isolated executor code; immutable approval tool; durable consumption + outbox state; MOCK broker adapter; tests; read-only configuration; documentation.
STILL PROHIBITED: no OAuth trading-scope grant; no DEMO_EXECUTION_ENABLED flip; no connection capable of order placement; no demo or live order. Return the build + test report before requesting any OAuth scope, gate flip, or broker-connected proof run.
