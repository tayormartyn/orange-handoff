# DEMO LANE — BOUNDED BUILD (v0.3.1 + FINAL_SECOND_REVIEWER_ADDENDUM_001)

**Authorised scope only: isolated executor code, immutable approval tool, durable consumption + outbox state, MOCK broker adapter, tests, read-only config, docs.**
**STILL PROHIBITED (enforced by absence, not just policy):** no OAuth trading-scope grant, no `DEMO_EXECUTION_ENABLED` flip (default False in config), no connection capable of order placement (only `mock_broker.MockBroker` exists — there is no real cTrader socket in this package), no demo or live order.

## Modules
- `config.py` — read-only; all three gates hard False; immutable safety caps (corr 12); the five ledger eligibility flags (corr 11); account allowlist (corr 1). No credentials.
- `gate.py` — five-field account guard (corr 1; `accountType` never used) + `can_arm` + `truth_table` (corr 5; proves no armed row touches a live target).
- `sizing.py` — exact volume, no rounding either way (F1); halt on any mismatch.
- `approval_tool.py` — OPERATOR tool; writes immutable `DEMO_APPROVED` (write-once O_EXCL); requires explicit Martyn action; binds 14 plan fields + nonce + approval-record hash + tool version + expiry (corr 4, F3). No broker import → no order capability.
- `executor.py` — writes `DEMO_APPROVAL_REQUEST`; `write_approval` raises (F3: technically incapable of approving). Ordering (addendum 1): validate → atomic consumption receipt → outbox intent → send; failed receipt blocks the request. LIMIT-only opening with SL + GOOD_TILL_DATE (addendum 2) in the initial request; exact-equality 7-field reconciliation (addendum 3); OUTCOME_UNKNOWN on lost response (corr 7).
- `mock_broker.py` — in-memory MOCK adapter; configurable for every proof scenario.
- `reconcile.py` — reconciliation policy (corr 8) + F2 close-only-reduces-owned.
- `tests_demo_lane.py` — 28 proof tests (corr-13 fourteen + F2 four + F3 six + addendum 1/2/3 + corr-11 negatives). All pass.

## Architectural safety notes
- **Approval authority separation (F3):** the executor has no method that writes `DEMO_APPROVED`; the only path (`write_approval`) raises `PermissionError`. In deploy, the approvals directory additionally carries a Windows ACL the executor's OS account cannot write.
- **Receipt-before-send (addendum 1):** no receipt → no outbox intent → no send; proven by the failed-receipt test placing zero orders.
- **No real connection:** the package imports no cTrader client. Activation (a real adapter, OAuth, gate flip) is a SEPARATE, unauthorised step requiring sign-off.

## To run tests
`python research/farouk_pilot/demo_lane/tests_demo_lane.py`  → 28/28 pass.
