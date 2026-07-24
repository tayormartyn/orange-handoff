# Session Context Resolver v0.1 — Report

**Mode:** OFFLINE SESSION CONTEXT. Maps a UTC timestamp to a session label using an explicit policy.
**Observation-only; proxy labels only.** No broker/QST, no deploy. `NOT_INTEGRATION_READY` unchanged.

## Files

- `session_context_resolver_v0_1.py` — the resolver (pure function).
- `test_session_context_resolver_v0_1.py` — tests.
- `FAROUK_SESSION_POLICY_v0_1.md` — the corpus-grounded policy (proxy, unconfirmed).

## Output

`session_label`, `session_window`, `session_confidence` (UNCONFIRMED default; NONE/LOW/MEDIUM under a
hypothetical confirmed policy per corpus support), `policy_version`, `warnings`, and the hard-wired safety
block (candidate_only=true; execution/broker/qst/order_intent/risk_sizing=false).

## Behaviour

- Default policy `confirmed=False` (timezone deliberately unresolved in corpus) → every live label carries
  `SESSION_UNCONFIRMED` and confidence `UNCONFIRMED`.
- Asia has **no corpus clock window** → `support=unsupported_proxy` → confidence `NONE` even if a policy
  were marked confirmed. London = open-only (LOW); NY = documented window (MEDIUM).
- Unparseable timestamp → `SESSION_UNRESOLVED` + warning (no fabrication). DST unhandled → warning.

## Test results — ✅ PASS

`python test_session_context_resolver_v0_1.py` → **5 tests, OK.** Covers: inside-Asia maps to
`ASIA_UTC_PROXY` (confidence NONE under confirmed policy — Asia window unsupported); NY maps correctly;
unconfirmed policy → `SESSION_UNCONFIRMED`; unparseable timestamp; all safety flags false.

## Applied to Gate G (see replay report)

All 3 candidate anchors (00:03Z, 04:12Z, 05:42Z) fall in 00–08Z → `ASIA_UTC_PROXY`, all
`SESSION_UNCONFIRMED`. Because Asia is unsupported and the policy is unconfirmed, this cannot satisfy the
scorer's `session_context` factor — it remains `missing_evidence`.

## Safety confirmations

- Candidate-only; no execution / order / broker / lot / account / risk / permit / lease.
- Offline; no broker/cTrader/QST; no deploy.
- **`NOT_INTEGRATION_READY` unchanged.**

## Status

v0.1 — implemented, tested (5/5). Session remains a proxy; the confirmed-session factor stays blocked on
the unresolved timezone.
