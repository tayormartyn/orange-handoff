# FP-INDICATOR-006 — EVIDENCE REPORT

## Source
**"Live with Farouk, Sunday 5 July 2026.mp4"** — a 2h08m live TradingView session. Classification:
**FP-INDICATOR-006, MIXED_SOURCE (indicator-primary)** — one physical source, three separated evidence sections
(INDICATOR_WALKTHROUGH / METHODOLOGY_TEACHING / MARKET_UPDATE). Same indicator as FP-INDICATOR-005: **Farouk's
Playbook — Smart Money Suite**. FP-LIVE-OBSERVATION-001 is NOT used (reserved for the forward alert test).

## 1. File & hash
- Original: `C:\Users\Marty\Downloads\Live with Farouk, Sunday, 5 July 2026.mp4`
- Staged: `research/farouk_pilot/raw/live_with_farouk_2026-07-05/…` (copied, no re-encode)
- **SHA256 (both) = `4328a875cb55d147a524a1b817209159ccdc734f972521b35718a8f4439e12d8` — VERIFIED IDENTICAL.**
- 614,053,015 bytes. Both files preserved unmodified. Asset `sa-4328a875cb55d147`.

## 2. Technical metadata
02:08:27.82 · 1920×1080 · h264 (High) · 30 fps · aac LC 44.1 kHz **stereo** · 637 kb/s · encoder Lavf63.3.100.
No reliable embedded creation_time; filesystem mtime = download time (NOT publication).

## 3. Context
XAUUSD 5m Pepperstone (+ BTCUSDT.P / HYPEUSDT.P tabs; Daily replay used). Chart TZ **UTC+2** (user-local).
Hidden co-loaded indicators: [kyle] v1/v2, BGS Liquidity Inefficiency, SeaScalper Bias Levels v2 (kept separate).

## 4. Main topics (see VISUAL_TIMELINE.md + AUDIO_TRANSCRIPT.md)
Indicator update recap (London/US high-low), **settings walkthrough incl. the detection engine**, alarms Q&A,
mitigation/OB/FVG/BPR/CHoCH teaching, extensive live XAUUSD/BTC analysis, Asia/London/US session logic, and an
on-screen "22-year gold edge" note.

## 5. New indicator features / settings (NEW_FEATURES_AND_CHANGES.md, SETTINGS_AND_FEATURE_REGISTER.*)
**Newly VISIBLE detection settings** (unknown in FP-INDICATOR-005): CHoCH pivot **5** · FVG lookback **50** ·
Min FVG **0.5 ATR** · Min BPR overlap **0.2 ATR** · Auto-remove filled FVG/BPR **ON** · Max zones **10** · Show
CHoCH ON. Reconfirmed (same as 005): label Tiny, box 50, TZ/ST 0.15/0.08/0.6/0.3, Only-show-TZ/ST ON, DISPLAY
toggles. **A "Defaults" dropdown is visible but was NEVER clicked → none are proven factory defaults; all are
CURRENT_VISIBLE_CONFIG.** Still not shown: OB-impulse thresholds, equal-high/low lookback, session-hours/timezone
fields, HTF-OB selector, alert settings.

## 6. New methodology findings (METHODOLOGY_CLAIMS_LEDGER.jsonl)
Candle-close required for entries (5m/15m/hourly); "CHoCH is the strongest form of confirmation"; mitigation =
valid-if-unmitigated (timeframe-relative); weekly session reset; auto zone-management. Asia range 00-07 UTC
(methodology note). A+/A+++ still qualitative.

## 7. Existing findings corroborated
FP-INDICATOR-005 London/US high-low + panel + IFVG + extend-box; FP-EDU-016 candle-close; FP-EDU-008 mitigation;
the CHoCH/OB panel attribution.

## 8. Contradictions (CONTRADICTION_IMPACT.md)
No new contradictions. BOS candle-close (016 vs 021) **narrowed toward "required for entries"** (retained at spec
level). #3 (FVG/IFVG) and #4 (mitigation/spent) corroborated as classified. #6 unchanged.

## 9. Blockers (BLOCKER_IMPACT.md — 27 questions)
**Resolved (current-config):** CHoCH pivot (5), FVG lookback (50), Min FVG (0.5 ATR), Min BPR overlap (0.2 ATR),
+ panel demonstrated (Q27). **Narrowed:** FVG-fill/expiry mechanics (auto-remove, max 10), Asia 00-07 UTC,
timezone user-local, candle-close practice. **Unchanged (17):** A+/A+++, confluence count, all-boxes-vs-graded,
OB-impulse thresholds, equal-high/low lookback, mitigation numeric, IFVG conversion, POC-T/VP window, nBOS,
session hours, and **all alert timing/repaint/payload/duplicate**.

## 10. Campaign cross-reference (CAMPAIGN_CROSS_REFERENCE.json)
Panel attribution **CONFIRMED** (this indicator produces the Campaigns 001-004 panel). Instrument match
(XAUUSD) confirmed; **no specific campaign-trade re-shown** (current Jul-2026 levels). Frozen dossiers untouched.

## 11. Synthesis impact (SYNTHESIS_IMPACT.md)
Methodology Candidate v0.3: FVG/BPR/CHoCH detection params now concrete (proposal note only). State-Machine
Candidate v0.2: ALERT_INTAKE unchanged (still BLOCKED_BY_LIVE_VALIDATION); auto-remove supports the dedup/stale
basis. No candidate files modified.

## 12. Recommended next action
Run **FP-LIVE-OBSERVATION-001** (already prepared) to close the alert timing/repaint/payload/duplicate blockers —
the only ones this rich session could not touch. Opportunistically, a future settings capture should scroll to
the **ORDER BLOCK / LIQUIDITY** + **SESSIONS** sections (OB-impulse thresholds, equal-high/low lookback, session
hours) and, if ever offered, observe a genuine reset-to-default to establish factory defaults.

## 13. Governance confirmation
No detector code; nothing connected to QST; no TradingView alert/webhook created or activated; no permit/lease;
no order sent/amended/cancelled/managed; the **1.0% campaign risk cap** and all **execution gates (False)**
unchanged. `FAROUK_METHODOLOGY_SPEC_v0.2.1`, `FAROUK_STATE_MACHINE_SPEC_v0.1`, `FAROUK_METHODOLOGY_CANDIDATE_v0.3`,
`FAROUK_STATE_MACHINE_CANDIDATE_v0.2`, frozen campaign dossiers, the Education corpus, FP-INDICATOR-005 evidence,
and the FP-LIVE-OBSERVATION-001 protocol were **not modified**. Both video copies preserved unmodified.
