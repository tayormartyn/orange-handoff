"""Embed adjudicated statuses + claim verdicts into the Day-4 results JSON."""
import json, sys, io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
P = r"C:\Users\Marty\signal-terminal\research\farouk_pilot\always_on_tradingview_receiver_plan\stage_c_tooling\SPRINT_DAY4_JUNE_XAU_OUTCOME_MATCHING_v1.json"

ADJ = {
    "XAU-J25-20260623": ("VERIFIED_WIN", "SUPPORTED",
        "SL 4180 never touched; TP 4130 hit 14:27Z; MFE 320p; all post-entry pip claims supported. "
        "'50 pips' at 13:57 predates zone touch (13:59) but matches a market fill at post time (price 4131-4137)."),
    "XAU-J26-20260624": ("VERIFIED_WIN", "SUPPORTED",
        "SL 4130 never touched; MAE none beyond zone; MFE 859p; every claim incl. '650 pips' supported "
        "(755p achievable at that moment)."),
    "XAU-J27-20260625": ("VERIFIED_WIN", "SUPPORTED",
        "SL 3970 never touched (MAE $0.91); TP1/2/3 hit; '300 pips' supported (345p achievable)."),
    "XAU-J28-20260626": ("PARTIAL", "SUPPORTED_WITHIN_FILL_TOLERANCE",
        "Hard SL never touched; MFE 206p. '100 pips' at 14:01 predates zone touch (14:04) but matches a "
        "market fill at the zone's bottom edge (~96p to the 14:01 low). Outcome was his own BE-stop scratch "
        "— consistent with price action, not independently provable."),
    "XAU-J29-20260626": ("VERIFIED_WIN", "SUPPORTED",
        "SL never touched; MFE 184p; 90/100/150-pip claims all supported; his in-profit exit before the "
        "retrace to entry ('missed by 1 pip') matches the 4096.04 adverse extreme."),
    "XAU-J30-20260629": ("PARTIAL", "CONTRADICTED_MAGNITUDE",
        "Win direction real: 'tp1 hit' 09:04 true for a market fill (high 4050.52); trade never lost from "
        "announced fills before profits. BUT 170/200/240-pip claims are contradicted — max achievable was "
        "128p (12:03, high 4047.83), 128p (12:04), 175p (12:12, high 4052.53): overstated 33-56%. BE stop "
        "on runner ~13:59 (price crossed zone bottom); hard SL 4010 touched 14:11-14:15 (low 4000.66) "
        "after his exit — holders of the original SL were stopped."),
    "XAU-J24-20260623": ("INSUFFICIENT_DATA", "UNCLEAR",
        "Entry message never captured — no numeric zone/SL to test although OHLC covers the day. The "
        "70/100/170-pip claims reference a ~4140 sellzone; price fell 4140->~4123 area that morning, "
        "directionally consistent but unverifiable without the entry post."),
}

with open(P, encoding="utf-8") as fh:
    data = json.load(fh)

tally = {}
for r in data["results"]:
    sid = r["setup_id"]
    if sid in ADJ:
        status, verdict, note = ADJ[sid]
        r["status"] = status
        r["claim_verdict"] = verdict
        r["adjudication_note"] = note
    else:
        r.setdefault("status", "INSUFFICIENT_DATA")
        r["claim_verdict"] = "UNVERIFIED_NO_OHLC"
    tally[r["status"]] = tally.get(r["status"], 0) + 1

data["adjudication_summary"] = {
    "statuses": tally,
    "covered_window_utc": "2026-06-21 22:01 .. 2026-06-30 (June portion)",
    "uncovered": "June 1-21 (23 setups) — TradingView export contains only loaded chart bars (~20k cap)",
    "cumulative_sprint_sample": "Day2 (4) + Day4 (6) = 10 outcome-matched XAU trades across 9 sessions "
                                "(Jun 23,24,25,26,29 + Jun 30, Jul 7,8,10) — >=10 trades / >=5 sessions threshold MET",
    "cumulative_results": "6 VERIFIED_WIN, 1 VERIFIED_LOSS, 3 PARTIAL, 0 CONTRADICTED (setup-level); "
                          "1 magnitude contradiction (J30) + 1 mild overstatement (S1 1000+p vs 922p)",
}

with open(P, "w", encoding="utf-8") as fh:
    json.dump(data, fh, indent=2)
print("statuses:", tally)
print("updated:", P)
