"""Embed Day-5 adjudications + final combined June counts into the results JSON."""
import json, sys, io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
P = r"C:\Users\Marty\signal-terminal\research\farouk_pilot\always_on_tradingview_receiver_plan\stage_c_tooling\SPRINT_DAY5_JUNE_XAU_5M_FALLBACK_OUTCOME_MATCHING_v1.json"

ADJ = {
 "XAU-J01-20260602": ("PARTIAL", "SUPPORTED",
   "SL never touched; TP1 4535 missed by $0.80 (fav extreme 4534.20) — literally 'almost hit TP1'; early manual close consistent."),
 "XAU-J02-20260602": ("VERIFIED_WIN", "SUPPORTED",
   "TP1 4520 touched on the entry bar ('hit TP almost instantly' confirmed); SL never touched; MFE 199p."),
 "XAU-J03-20260602": ("PARTIAL", "SUPPORTED",
   "ADMITTED LOSS #1 tested: no SL touch, no TP touch; -40/50p manual cut consistent with mid-zone fills vs low 4486.16. A real (manual) loss, OHLC-consistent."),
 "XAU-J04-20260603": ("VERIFIED_WIN", "SUPPORTED",
   "TP 4430 hit 13:40Z (before 'Close here' 13:47); SL never touched; MFE 436p; waterfall milestones achievable."),
 "XAU-J05-20260603": ("VERIFIED_WIN", "SUPPORTED",
   "50p/100p supported (127p achievable); TP1 4440 hit 15:20Z; SL never touched; MFE 283p."),
 "XAU-J06-20260603": ("VERIFIED_WIN", "SUPPORTED",
   "TP1 4436 hit 18:10Z, 4 min before his 'Tp 1 hit'; SL never touched; small win as claimed."),
 "XAU-J07-20260604": ("VERIFIED_WIN", "SUPPORTED",
   "TP1 4461 hit 07:40Z (his msg 07:50); >50p claim supported (106p); SL never touched; MFE 266p."),
 "XAU-J08-20260604": ("PARTIAL", "SUPPORTED",
   "ADMITTED LOSS #2 tested: adverse extreme 4514.44 vs SL 4515 — 'just missed our sl' accurate to $0.56; manual small-loss close consistent. A real (manual) loss, OHLC-consistent. ('50 pips' at 11:12 predates 5m zone touch — fill tolerance.)"),
 "XAU-J09-20260611": ("VERIFIED_WIN", "SUPPORTED",
   "'tp1 70 pips' supported (95p achievable); SL 4080 never touched; BE exit after partials consistent."),
 "XAU-J10-20260611": ("VERIFIED_LOSS", "SUPPORTED",
   "IMPLIED LOSS resolved: stated SL 4060 TRADED 12:30Z, before the 13:58 recovery trade. Price never traded below 4060 between re-entry (08:22) and the touch, so ANY long from that period was above 4060 -> SL hit = loss, regardless of exact fills. His never-posted outcome was indeed a loss."),
 "XAU-J11-20260611": ("PARTIAL", "UNCLEAR_FILL_DEPENDENT",
   "Recovery win direction confirmed (SL 4035 never touched; +$66 from signal close). But no entry zone was posted: '500/800 pips' = 246/664p from a market-at-signal fill vs 546/964p from the best post-signal fill — supported only under favourable layered fills."),
 "XAU-J12-20260615": ("VERIFIED_WIN", "SUPPORTED",
   "'50 pips' supported (55p); SL never touched; BE exit 'still up 50-60' consistent (65p max)."),
 "XAU-J13-20260615": ("VERIFIED_WIN", "SUPPORTED",
   "TP1 4364 touched 14:05Z (his 'tp1 hit' 14:06); 100p claim supported (153p); SL never touched."),
 "XAU-J14-20260615": ("VERIFIED_WIN", "SUPPORTED",
   "'100p again' supported (123p achievable); SL never touched."),
 "XAU-J15-20260615": ("PARTIAL", "SUPPORTED",
   "Pure BE-scratch claim; 99p was achievable before the stop; consistent, not independently provable."),
 "XAU-J16-20260615": ("PARTIAL", "SUPPORTED",
   "BE-scratch claim; 129p achievable before; consistent."),
 "XAU-J17-20260615": ("VERIFIED_LOSS", "SUPPORTED",
   "ADMITTED LOSS #3 tested: SL 4318 TRADED 18:00Z (~2h before his 'SL was hit' message); MAE $19.50; full-SL loss deterministically confirmed."),
 "XAU-J18-20260616": ("VERIFIED_WIN", "SUPPORTED",
   "'50-60p' supported (78p achievable); SL never touched."),
 "XAU-J19-20260616": ("VERIFIED_WIN", "SUPPORTED",
   "100p/130p supported (108p/156p); SL never touched; MFE 209p."),
 "XAU-J20-20260617": ("VERIFIED_WIN", "SUPPORTED",
   "TP1 4328 (09:20Z) + TP2 4332 (09:25Z) touched before his 09:29 'tp 1-2 hit'; 100p supported; SL never touched."),
 "XAU-J21-20260618": ("VERIFIED_WIN", "SUPPORTED",
   "110p/200p supported (137p/229p); MFE 400p; hard SL 4300 never approached — his 10:52 'just missed my sl' referred to the ENTRY-level stop (SL moved to entry 10:23): the retrace peaked 4272.63, inside the zone. Resolves cleanly."),
 "XAU-J22-20260618": ("VERIFIED_WIN", "SUPPORTED",
   "tp1+BE consistent (80-103p achievable); posted SL 4318 impossible for a long (typo, tested 4218 — never touched); MFE 294p."),
 "XAU-J23-20260619": ("PARTIAL", "SUPPORTED",
   "ADMITTED LOSS #4 tested: SL 4135 never touched (low 4141.73); mixed manual closes 'count it as a loss' consistent with the -123p adverse chop; his regret note is OHLC-accurate — price rallied to +293p AFTER his exit. A real (manual) loss, OHLC-consistent."),
}

with open(P, encoding="utf-8") as fh:
    data = json.load(fh)

tally = {}
for r in data["results"]:
    sid = r["setup_id"]
    status, verdict, note = ADJ[sid]
    r["status"], r["claim_verdict"], r["adjudication_note"] = status, verdict, note
    tally[status] = tally.get(status, 0) + 1

data["day5_new_matches"] = tally
data["final_june_combined_counts"] = {
    "strict_setup_count": 30,
    "entry_executions": 33,
    "grouped_campaign_count": 24,
    "VERIFIED_WIN": 18, "VERIFIED_LOSS": 2, "PARTIAL": 9,
    "CONTRADICTED": 0, "AMBIGUOUS_INTRABAR": 0, "INSUFFICIENT_DATA": 1,
    "precision_split": {
        "1m_confirmed_day4": {"VERIFIED_WIN": ["J25","J26","J27","J29"], "PARTIAL": ["J28","J30(magnitude CONTRADICTED)"]},
        "5m_fallback_day5": {"VERIFIED_WIN": 14, "VERIFIED_LOSS": ["J10","J17"], "PARTIAL": 7},
        "insufficient": ["J24 (no entry message)"]},
    "june_losing_trades_total": {
        "verified_SL_losses": ["J10 (SL 4060 traded 06-11 12:30Z)", "J17 (SL 4318 traded 06-15 18:00Z)"],
        "manual_cut_losses_admitted_and_OHLC_consistent": ["J03 (-40/50p cut)", "J08 (missed SL by $0.56, small cut)", "J23 (mixed closes, counted as loss)"],
        "total_losing_trades": 5},
}
data["claim_22_trades_2_losers_reassessment"] = {
    "trade_count": "~24 grouped campaigns / 30 strict setups / 33 executions vs claimed 22 — approximately consistent under grouped counting only",
    "losers_SL_only_convention": "EXACTLY 2 verified full-SL losses (J10, J17) -> under this convention the claim is SUPPORTED",
    "losers_all_losing_trades": "5 total losing trades (2 SL + 3 manual cuts he himself posted) -> under this convention CONTRADICTED",
    "overall": "PARTIALLY SUPPORTED / CONVENTION-DEPENDENT: not fabricated — '2 losers' is exactly right for hard-SL stop-outs; it undercounts total losing trades (5); trade count fits grouped-campaign counting (~24 vs 22)."}
data["cumulative_sprint_sample"] = {
    "trades_matched": 33, "sessions": 18,
    "VERIFIED_WIN": 20, "VERIFIED_LOSS": 3, "PARTIAL": 10, "CONTRADICTED": 0,
    "magnitude_issues": ["J30 material (170/200/240p vs 128/128/175p)", "S1 mild (1000+p vs 922p)"]}

with open(P, "w", encoding="utf-8") as fh:
    json.dump(data, fh, indent=2)
print("day5 new-match tally:", tally)
print("final June:", json.dumps(data["final_june_combined_counts"], indent=1)[:400])
