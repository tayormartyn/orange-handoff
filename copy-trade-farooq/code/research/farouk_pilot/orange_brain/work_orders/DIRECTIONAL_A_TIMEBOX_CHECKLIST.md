# DIRECTIONAL-A TIME-BOXED CAPTURE — OPERATOR CHECKLIST (PREPARED, NOT RUN)
Status: AWAITING MARTYN'S DECISION. Prepared 2026-07-20 per reviewer instruction. Fable executes none of this — every step is Martyn's, per D-011 (Fable never touches the TradingView alert dialog).

**Why:** no discrete A LONG / A SHORT condition exists (catalogue proven complete at 13, D-012) — the catch-all `alert()` is the ONLY source of directional-A payloads, and the A-grade formula is one of the project's biggest unknowns. One controlled noisy window captures what nothing else can. Basis: `BATCH_002_DIRECTIONAL_A_FALLBACK_PLAN.md` (this checklist instantiates its recommendation).

## Steps (all Martyn, ~3 minutes setup + one disable at the end)
1. **Create (duplicate-first, never edit an original):** new alert on XAUUSD **3m**, indicator "Farouk's Playbook — Smart Money Suite", condition **"Any alert() function call"**.
   Name: `LIVE013_ANY_ALERT_TIMEBOX_A_ONLY_20260721` (next free LIVE number; date-stamp it).
2. **Settings:** Webhook URL = the exact bare line from the gitignored `LOCAL_ONLY_*_WEBHOOK_URL.txt` (starts `https://farouk-tv-webhook-logger-v1.taylormartyn70.workers.dev/tv/`); **notifications OFF** (untick app/popup/email/sound — webhook-only, so no dinging); expiration = set to the window end if the dialog offers it.
3. **Window:** ONE active session, **2–4 hours maximum**, ideally London or NY open on a weekday (highest A-grade density). Note the arm time.
4. **Expected volume:** ~6.4 events/hour average, peaks ~14/hour (Batch-002 measurement) → roughly **15–60 R2 objects** for the window. All append-only, harmless; Engulfing/BPR noise is filtered OFFLINE afterwards (whitelist: `A LONG` / `A SHORT` raw texts only) — the Worker is never modified.
5. **Disable step (MANDATORY):** at window end, **stop or delete `LIVE013_…` immediately**. It must never run overnight or unattended. If you forget, the only cost is extra harmless R2 noise — but stop it when remembered and note the actual window.
6. Tell Fable the armed window (start/end) — the offline whitelist extraction + analysis is a read-only follow-up task against `events/` objects in that window.

## What this may buy
Directional-A events time-stamped to 3m bar closes, alignable with panel state and bar data → first structured dataset for the A-grade formula question (currently UNKNOWN, weight-0 record-only). No promotion of anything from one window; capture-only.

## Explicitly not done
No Worker change, no permanent catch-all (rejected in Batch-002), no A+ / originals touched, no Fable interaction with TradingView.

---
## SESSION LOG (append-only)
**2026-07-21 ARMED:** `LIVE013_ANY_ALERT_TIMEBOX_A_ONLY_20260721`, XAUUSD 3m, webhook-only, notifications off — operator-armed, confirmed ≤06:29Z (pre-London-open). **Mandatory stop 12:00 UTC.** Purpose on record: test whether directional-A fires PRECEDE a Farouk post (Lane C question), not merely route delivery. Baseline marker at arm-confirmation: 06:27:01Z 'Liquidity Sweep high' (named-mirror plain payload). LIVE013's fires are distinguishable by the catch-all payload grammar `Farouks Playbook: <event> on XAUUSD 3`. Offline A-LONG/A-SHORT whitelist analysis after the window = Fable, per the pre-registered H-FPL-07 per-fire fields.
**2026-07-21 in-window evidence (append-only, EVIDENCE NOT CONCLUSION):** F007 (XAU-F007-20260721, msg 45970, LONG 4053-4063) posted 08:26:42Z inside the armed window. Fires visible WITHOUT enumeration: first fire 06:39:00Z "Bullish Engulfing" (catch-all grammar); latest-fire marker 08:09:01Z "Bearish Engulfing" — **17.7 minutes before a LONG post, opposite direction → no precede-a-post signal from the visible fires**. Neither visible fire is A LONG / A SHORT. Intermediate fires are invisible until the authorised post-stop enumeration (D-013 method, operator-authorised ONCE, to run only AFTER the 12:00Z stop); full H-FPL-07 per-fire rows then.
**2026-07-21 STOPPED:** operator-confirmed LIVE013 stopped at the 12:00Z mandatory ceiling (confirmation received 12:02Z). Window: 06:29Z arm -> 12:00Z stop. One-time enumeration (D-013 discipline) authorised and executed post-stop; results appended below.

## ENUMERATION RESULT (2026-07-21, D-013 discipline, one-time)
**Worker shas: baseline `2045cdb140604750` -> temp branch (2 deploys: list, then bodies) -> REVERTED byte-exact `2045cdb140604750`.** GET `/__verify_list__` probe post-revert = **405** (branch gone, both with and without token); temp token + baseline backup DESTROYED; bar feed ALIVE post-revert (fresh accepted bar 12:07:00Z close 4059.86). No webhook secret used or printed. R2 evidence untouched (append-only reads only).

**Window enumerated: 785 objects on 2026-07-21; 380 events inside 06:29-12:00Z.**

### PRIMARY QUESTION — directional-A DID fire. 11 directional-A fires in the window:
06:51:02Z A SHORT · 07:00:09Z A SHORT · 07:33:00Z A LONG · 07:45:04Z A SHORT · 08:09:01Z A SHORT · 09:09:02Z A LONG · 09:27:02Z A SHORT · 09:51:01Z A SHORT · 10:12:00Z A LONG · 11:42:01Z A SHORT · 12:00:05Z A SHORT. (8 A SHORT, 3 A LONG.) Full non-A tally: Sweep low/high, Liquidity Sweep low/high, Bearish/Bullish Engulfing, BPR tapped, CHoCH DOWN — see live013_window_fires.json.

### LANE C TEST — did a directional-A fire PRECEDE F007 (LONG @08:26:42Z) in a consistent direction?
5 directional-A fires preceded the post: **4 A SHORT (06:51, 07:00, 07:45, 08:09Z) and 1 A LONG (07:33:00Z, 53.7 min before).** So a same-direction (A LONG) fire DID precede the LONG post — but it was outnumbered 4:1 by opposite-direction A SHORT fires in the same pre-post window, the nearest fire before the post was A SHORT (08:09Z, opposite), and the whole-window mix is 8 SHORT / 3 LONG. **VERDICT: NO CLEAN PRECEDE SIGNAL — a consistent A LONG existed but is indistinguishable from noise; directional-A fires in BOTH directions repeatedly through the window regardless of the eventual single LONG post. n=1 campaign; recorded as evidence, not conclusion.**

### SESSION OUTCOME (honest): NOT a null window — the catch-all captured a rich directional-A stream (11 A-fires + dozens of structure events over 5.5h) that the named-mirror alerts never expose. The precede-hypothesis is NOT supported at n=1, but the session succeeded at its capture purpose: it proved directional-A fires exist, are frequent (~2/hour), fire both directions continuously, and do NOT cleanly anticipate his single post. This is real evidence about their behaviour, not a failed session.
