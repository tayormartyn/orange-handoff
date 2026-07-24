# ORANGE CONTROLLED TRAVEL SHUTDOWN CHECKPOINT

- shutdown_at_utc: 2026-07-13T10:55Z (2026-07-13 ~11:55 UK); expected resume ~21:00 UK
- listener_pid_stopped: 30268 (graceful stop verified EXITED; no other python processes; no watchdog/scheduled-task/auto-restart found)
- final_committed_cursor: 45674
- channel_store_max: 45674 (store max == cursor; zero unprocessed rows at shutdown)
- last_ledger_marker: CYCLE_006_SCAN_04_TRAVEL_SHUTDOWN (scanned 45660-45674, 15 msgs, all NON_XAU)
- cycle_006_status: OPEN - no genuine prospective XAU/Gold post yet; XAU-F001 NOT TRIGGERED (capture contract armed: 8C/8D/8F + 001B-004B + ORB block, frozen v0.2/v0.3 A/B, 4 pre-mark comparison)
- pre_marks (ALL FROZEN):
  - PM-F001-SELL-4150-4184 - expiry 2026-07-17 (4 days)
  - PM-F002-SUPPLY-4430-4480 - expiry 2026-07-31 (SEED_PROVENANCE_WEAK / HUMAN_REVIEW)
  - PM-F003-SELL-4250-4260 - expiry 2026-07-19 (strong provenance, zone visible on chart)
  - PM-F004-DEMAND-3850-3863 - expiry 2026-07-31
- scorer_hash_baselines (verbatim from knowledge register; integrity suite re-verifies):
  - A_source_evidence_index.assets.0.sha256_prefix: f1200fed
  - A_source_evidence_index.assets.1.sha256_prefix: f061b23c
  - A_source_evidence_index.assets.3.sha256_prefix: 942dc4af
  - F_pre_mark_register_frozen.ledger_sha256_at_registration: E5B3F0D622311348845FB4E46B2E71A5AED3D92FA53D2A4A5791F926279A357A
  - integrity_baselines.detector_v0_3_replay_results.json_sha256: DD1A5A1A7A1BE917856176857FDF7D148C8F17BB19C34CA594AA37CC0A24ED88
  - integrity_baselines.detector_v0_2_replay_results.json_sha256: F602E2FDBD2819C97123B8FEE9FB50B144E7D9CED1EB4156DC840D66E23989DB
- v0_4_offline_file_hashes:
  - detector_v0_4_offline_replay.py: a2984641e8f4a6c0c9bb6a41801129d3b83980609ab35764adad579521ad3c1d
- gates: MODE=PAPER | LISTENER_MODE=PREVIEW | EXECUTION_ENABLED=False | CTRADER_EXECUTION_ENABLED=False
- NOT_INTEGRATION_READY: unchanged
- no scorer / pre-mark / capture-schema / knowledge record was changed by this shutdown

## RESTART + GAP-BACKFILL INSTRUCTIONS
1. Listener script: module_a_telegram.py (locate under signal-terminal/campaign_extractor)
2. BEFORE starting the listener, backfill the offline gap with the copied-session method:
   copy whale_room.session to a temp copy (never run two clients on the same session file),
   fetch channel -1001902136163 messages with id > 45674, append-only insert into
   prospective_message_evidence exactly once (dedup on telegram_message_id + revision).
3. Then start the listener: python -u module_a_telegram.py (PREVIEW mode); record the new PID;
   verify single instance.
4. Run a sequential scan from cursor 45674 to the new store max; classify each message once;
   append a CYCLE_006 scan marker; commit cursor. If a genuine prospective XAU/Gold post exists,
   execute Cycle 006 / XAU-F001 capture FIRST before any other task.
5. Verify integrity suite passes and gates remain PAPER/PREVIEW/False/False.
6. Watch PM-F001 (exp Jul-17) and PM-F003 (exp Jul-19) for expiry resolution.
