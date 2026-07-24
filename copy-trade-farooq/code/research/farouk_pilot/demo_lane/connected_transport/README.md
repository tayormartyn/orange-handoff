# connected_transport (OFFLINE build — Chuck-authorised, TRANSPORT_BUILD_AUTHORISED)

The connected cTrader-**DEMO** transport. It owns **wire mechanics only** — connect, auth, frame,
heartbeat, correlate, reconcile, reconnect — and it **sends approved requests and returns broker
facts**. It never reinterprets: no sizing, price validation, approval, gate authority, reconciliation
equality, or campaign interpretation lives here (those single sources stay in `demo_lane` and the
follower interpreter).

## Module separation
- The **executor imports neither this package nor the mapper** (proven three ways: recursive import
  graph, clean-interpreter + socket booby-trap, and no edge in `sys.modules`).
- This package **may** import the approved `demo_lane.protobuf_mapper` (it does, for the deterministic
  client-order-id / request construction).

## Safety posture (all enforced + tested)
- Production composition is **NOT_ARMED** while the authoritative gates are False; test-enable binds
  to a **fake / 127.0.0.1-loopback** connector only. No CLI/env/caller override of destination or arming.
- **Fixed destination**: `demo.ctraderapi.com:5035` is the only dialable endpoint; no live host is
  nameable; no host/port override exists.
- **External-egress guard**: the whole test suite runs behind a process-wide guard that blocks every
  non-loopback `connect`/`connect_ex` and DNS lookup. `demo.ctraderapi.com` can be neither resolved
  nor dialled in tests.
- **Only** these outbound families exist (no generic console, no raw send): app-auth, account-auth,
  heartbeat, reconcile, LIMIT-open, cancel-pending, risk-reducing close, Lane-A stop-amend.
- Deterministic correlation; in-flight/resolved keys refused (**no blind resend**). **Send
  classification:** `DEFINITELY_NOT_SENT` ONLY when failure is provably before any transmit
  (state/gate refusal, encode/frame failure, not connected before send starts) — only that path
  releases the correlation; ANY error once `connector.send` begins is ambiguous →
  `OUTCOME_UNKNOWN` (correlation retained, no retry, READY invalidated, disconnect,
  reconcile-first after reconnect). Response timeout → atomic take-or-consume: a boundary
  response resolves exactly once; otherwise `OUTCOME_UNKNOWN` (retained permanently) + READY
  invalidated + session stopped — reconnect + full auth + reconcile before actions resume;
  reconnect → auth → **RECONCILE-before-action**; unknown order/position → **no-touch**;
  known-owned mismatch → **ratified containment**; unknown inbound event → **fail-closed**.
- **One always-on I/O owner:** a single reader thread is the only caller of `connector.recv`
  (routes responses by clientMsgId, consumes async fills/events even when idle); a single sender
  thread drains ONE outbound queue and emits heartbeats automatically (≤10s idle). Callers wait
  on futures and never touch the socket.
- **Broker identity:** the guard proves endpoint/ID/isLive/scope OFFLINE; `broker_environment` is a
  local-config self-comparison, NOT broker attestation — `PEPPERSTONE_ACCOUNT_BINDING =
  PENDING_READ_ONLY_PREFLIGHT` (`transport_config.BROKER_IDENTITY_CLAIMS`), validated later via
  `validate_preflight_binding()`.
- Credentials arrive only through a **provider interface**; this build ships a **fake provider** only.
  No token/secret in source/env/argv/logs; alarms + logs are sanitised.

## Run the tests
```
python -m demo_lane.connected_transport.tests_connected_transport      # 108 checks, loopback-only
.venv-ctrader/Scripts/python -m demo_lane.connected_transport.tests_proto_codec   # 27, real protobuf
.venv-ctrader/Scripts/python -m demo_lane.connected_transport.tests_tls_channel   # 17, TLS loopback
```

**Completion items (Chuck, 2026-07-24):** the REAL ProtoCodec (generated cTrader classes, mapper-
backed) and the TLS channel (fixed demo endpoint, required cert+hostname validation, loopback-tested
only) are BUILT — see `CHUCK_COMPLETION_PACK.txt`.

**NOT done (prohibited):** no external connection, no OAuth, no gate flip, no order to any venue.
The DPAPI credential provider + live-channel wiring are later, separately-reviewed steps.
