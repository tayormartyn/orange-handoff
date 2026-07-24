# Claude's Answers — Orange Handoff (for Kimi)

I'm the strategy/review side. I'll answer fully where it's my domain, and mark **[FABLE]** (needs the builder's repo/live truth) or **[MARTYN]** (external fact I don't hold) where I shouldn't guess. I will not invent specifics — a wrong "fact" here is worse than an honest "confirm this."

---

## 1. TradingView integration
Based on the repo structure (`always_on_tradingview_receiver_plan/…`) and my notes, TV interaction is **alert/webhook-based**, not REST polling: a PineScript indicator fires `alert()` payloads that a receiver ingests (the corpus holds "alert() payload captures" and "webhook logs"). There is a **PineScript component** (one `.pine` file shipped), so it's not pure-Python — TV-side Pine emits, Python receives.
- Data pulled: indicator *signal events* (Sweep / Engulfing / CHoCH / A / A+ / A+++ style conditions) via alert payloads, plus price at alert. **Price semantics from TV are explicitly UNVERIFIED** (flag `TRADINGVIEW_PRICE_SEMANTICS_UNVERIFIED`) — do not assume TV price == broker price.
- Priority indicator: Farouk's Playbook **"Smart Money Suite"** (catalogued as **FP-INDICATOR-005 / FP-INDICATOR-006**, with a 13-condition alert-condition audit). Data is accessed through its `alert()` webhook payloads, not a public API.
- **[FABLE]** confirm the exact current wiring: webhook endpoint, whether the receiver is live, and which `.pine` version is authoritative.

## 2. Post-trade videos & training material
- Videos are **stored locally** on Martyn's machine (they show up in Downloads). Raw video was excluded from the repo as large media. **[MARTYN]** for where the master copies live / cloud backup.
- Transcription **has** been run on a good chunk — the repo carries transcripts (indicator transcripts, live-session transcripts) and there's an `ocr_trial/` pipeline, so OCR has been trialled too. Whether **every** video is transcribed is a corpus-completeness question — **[FABLE]** check against the Orange Brain corpus manifest and flag any un-transcribed items.
- Educational batches (FP-EDU-007/008/016), dossiers: the Orange Brain (`orange_brain/brain_build_v0_1.py`) was built to index the corpus with a novelty gate; how *complete* the ingest is — **[FABLE]**.
- Total corpus size — **[MARTYN]/[FABLE]**. I don't have a number; videos are the heavy part.

## 3. Current live state
- **F008** — at my last verified check it was captured clean (LIVE_AT_ARRIVAL, prospective freeze) and had taken management to **revision 3 (msg 46098)**. Whether it's now still open or closed I can't assert from here — **[FABLE]** pull its current ledger status.
- **Four services** — restarted cleanly this morning after the reboot (single listener, correct banners, gates False). Current-moment health — **[FABLE]** confirm PIDs still alive / no alarms.
- **LIVE_EDIT fix** — my understanding: **built and proven but still HELD**, waiting for a quiet F008 window to deploy. Not deployed as of my last knowledge — **[FABLE]** confirm.

## 4. Pepperstone & demo account
- The read-only preflight **previously connected to the Pepperstone demo and confirmed view-only** — that was a success (it proved `scope=accounts`, no trading). 
- Demo account still active / account ID — **[MARTYN]/[FABLE]**. I don't hold the ID, and it shouldn't be pasted around anyway; it belongs in the sanitised preflight binding, not in chat.
- DPAPI: there is **existing DPAPI/Credential-Manager infrastructure** for secret storage (that's where the cTrader + Telegram creds live). The **production DPAPI credential *provider* for the connected transport is still to be built** — it's one of Chuck's authorised offline next-work items. So: foundation exists, the transport-side provider does not yet. **[FABLE]** for specifics.

## 5. Nana-Sibley
Honest answer: **not my area.** I didn't build it and I only know it's social-media automation (IG/FB/YT/TikTok) run by Hermes, with `code/build + prompts` in the repo. Official-API vs browser-automation, and its fragile parts — **[MARTYN]/[FABLE]/Hermes**. Don't take a guess from me here.

## 6. Strategy & edge
- **Biggest thing the system doesn't yet capture:** Farouk's **personal, discretionary method** — his *real* invalidation level (not the posted follower stop, which is logged as `personal stop UNKNOWN`), and his real-time management judgment (when he moves to BE, adds, or bails). The published signals + Constitution rules capture the *follower-visible* behaviour; the discretion in his post-trade commentary/videos is the `PERSONAL_LIVE_METHOD_UNCONFIRMED` tier, and it's the highest-value gap. Re-entry / pyramiding behaviour is a second under-captured area.
- **K-064 / P-EP-1 since F007:** F008 is the new data point. It has **not** been formally scored against P-EP-1 yet — and it must be scored under pre-registration discipline (no retuning to fit it; recall the 0.40-leg fill-rate is a *recorded characteristic*, not a knob). So: new data exists, assessment unchanged until scored honestly.
- **Highest-value insight from post-trade videos:** his *decision rationale* — why he entered where he did, where he considers the trade actually invalidated, and what makes him scale vs hold. That's the personal edge the follower signals don't reveal. Capture it as UNCONFIRMED-tier, never merged into follower method.

## 7. Transport & connectivity
- **Connect sequence (correct):** real view-only preflight + immutable account/symbol binding → DPAPI credential provider → production composition (all offline, gates False) → **signed CONNECT_APPROVAL block in MIGRATION.md §0.5** (both reviewers + Martyn's explicit go) → *only then* a real connection, and DEMO-only. Live gates stay False.
- **What loopback can't prove (watch these in a real environment):** actual cTrader server quirks and real reject/error codes vs the mock's; real TLS cert chain / hostname behaviour against `demo.ctraderapi.com`; heartbeat/timeout tuning under real latency; partial/fragmented frames under real network conditions; and the **broker-identity binding**, which is deliberately deferred to the real preflight (§0.5) — the offline build only proved the *guard shape*, not the real broker's identity. No known *defect* in the codec/TLS — but "no defect offline" ≠ "no surprises live," which is exactly why CONNECT_APPROVAL is gated.

## 8. If I were taking over
- **First improvement:** close the observability gap on his *personal* method — get his post-trade rationale and real invalidation levels captured as tiered UNCONFIRMED evidence — while continuing clean prospective captures (F009+). That's where the real edge signal is. I would **not** rush toward connection; the transport being done is not a reason to connect.
- **Biggest blind spot to watch:** the **"demo looks brilliant" trap** — treating a good demo run, or retrospective screening, as *confirmation* of edge. It isn't. Confirmation only ever comes from a genuine prospective sample with positive expectancy after costs. Second: the **silent-absence** failure class (a dead listener, a missed parse, an un-scored campaign) — always prefer a loud alarm over a quiet nothing.
- **What in MIGRATION.md I'd revise now:** (a) the launcher reference `ORANGE_START_SERVICES.ps1` is unconfirmed — we couldn't find it by that name; treat §4a's launcher line as *to-verify* until Fable confirms the real launch command. (b) F008's status line is a snapshot and will drift — always re-read the live ledger, don't trust the doc's snapshot.

## 9. Practical next steps
- **Fastest path to TV data correlation:** resolve `TRADINGVIEW_PRICE_SEMANTICS_UNVERIFIED` first — line up TV alert prices against broker prices on the same events to learn the offset/semantics. You can't correlate reliably on an unverified price basis.
- **Research vs demo lane:** do **both, in the right order** — prioritise *research capture* (clean prospective campaigns = the evidence that actually matters), and build out the demo lane **offline in parallel** (Chuck's authorised items 1–4). Connection is last and gated. Don't let demo-lane progress become pressure to connect.
- **Known stale/misleading to ignore:** **F001 / F002 are non-analytical backfill — never fit them as training** (this is a hard rule, easy to trip over). Also treat the launcher reference as unverified until Fable confirms. **[FABLE]** for any other configs known to be stale.

---

*Compiled by Claude (strategy/review). Items marked [FABLE] or [MARTYN] are deliberately deferred rather than guessed. Recommend adding this file to the repo alongside MIGRATION.md so it travels with the project.*
