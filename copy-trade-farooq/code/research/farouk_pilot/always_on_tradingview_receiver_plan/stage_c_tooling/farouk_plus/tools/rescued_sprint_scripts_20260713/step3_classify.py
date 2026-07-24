"""Embed feature classifications + caveats into ai_filter_sweep_v1.json."""
import json, sys, io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
P = r"C:\Users\Marty\signal-terminal\research\farouk_pilot\always_on_tradingview_receiver_plan\stage_c_tooling\farouk_plus\ai_filter_sweep_v1.json"
data = json.load(open(P, encoding="utf-8"))

data["classifications"] = {
 "f4_elevated_caution_label": {"class": "PROMISING_SCORING_FEATURE",
   "timing": "ENTRY-ACTIONABLE (label is in the entry message)",
   "finding": "present 5W/0L/2P vs absent 15W/6L/5P — his own HIGH RISK label paradoxically marks zero-loss trades (heightened-alert days: J09, J13, J26 monster, J28 campaign, S1-era). Suggested weight +1 (provisional).",
   "caveat": "n=7; correlates with f2; ~20% chance any single feature this common shows 0/6 losses by luck"},
 "f2_small_size_language": {"class": "PROMISING_SCORING_FEATURE",
   "timing": "ENTRY-ACTIONABLE",
   "finding": "present 5W/0L/3P (entry-scope 4W/0L/3P) vs absent 15W/6L/4P — size-caution language accompanies no losses. NOTE: recorded as a TEXT feature; the shadow engine records the language, it NEVER derives sizing (no risk sizing in scope).",
   "caveat": "overlaps f4 heavily; same multiple-comparisons caveat"},
 "f7_reason_stated": {"class": "PROMISING_SCORING_FEATURE (low weight)",
   "timing": "SEMI-ACTIONABLE (reason usually posted within minutes of entry)",
   "finding": "present 5W/0L/1P — explicit 'Reason for the sell/buy' posts correlate with wins (structured-thesis days).",
   "caveat": "n=6; timing lag means a live scorer may only apply it as an upgrade after the reason arrives"},
 "f8_education_context": {"class": "WATCHLIST_FEATURE (negative tilt)",
   "timing": "thread-scope",
   "finding": "present 0W/1L/2P vs absent 20W/5L/5P — teaching-mode threads produced no verified wins.",
   "caveat": "n=3 — far too small; watch forward"},
 "f5_be_stop_management": {"class": "WATCHLIST_FEATURE (outcome-side only)",
   "timing": "NOT entry-actionable (mid-trade consequence)",
   "finding": "thread present 19W/2L/6P vs absent 1W/4L/1P — dramatic but OUTCOME-CONFOUNDED: BE-stop talk only happens after the trade reaches profit. Entry-scope presence (2 records, both L) is just the re-entry signal again (entry messages that OPEN by reporting a prior BE-stop are re-entries J10/J17) — already covered by R2b.",
   "caveat": "do not score; keep as management diagnostic beside the MAE feature"},
 "f1_news_event_language": {"class": "NEEDS_FORWARD_EVIDENCE",
   "finding": "only 2 thread hits (both W), zero entry-scope hits — his text rarely flags news in advance. A real news feature needs an external economic-calendar join, not his language.",
   "caveat": "insufficient data by construction"},
 "f11_friday_entry": {"class": "WATCHLIST_FEATURE (mild negative tilt)",
   "finding": "Friday entries 1W/1L/2P vs rest 19W/5L/5P.",
   "caveat": "n=4"},
 "f6_layered_entry_management": {"class": "REJECTED (no discrimination)",
   "finding": "present 3W/1L/4P — mixed; it is his universal method narrated inconsistently."},
 "f9_post_hoc_commentary": {"class": "REJECTED (sparse, no signal)", "finding": "1 hit"},
 "f10_breakdown_video": {"class": "REJECTED (no signal)", "finding": "3W/1L/0P — video posting is outcome-neutral"},
 "f12_late_entry_confession": {"class": "REJECTED (sparse)", "finding": "2 hits, both W"},
}
data["carry_to_detector_v0_2"] = [
 "f4_elevated_caution_label (+1 provisional)",
 "f2_small_size_language (+1 provisional, merged with f4 as one 'caution-language' feature to avoid double counting)",
 "f7_reason_stated (+1 low weight, applied on arrival)",
 "f8_education_context (flag, weight 0, watch)",
 "f5 + MAE (outcome-side diagnostics only)",
]
data["honesty_caveats"] = [
 "n=33 matched trades, only 6 losses — every zero-loss split has ~15-25% probability by chance for features of this prevalence; with 12 features tested, ~2 such splits are EXPECTED by luck. Nothing here is confirmed; everything is provisional until the >=15 forward-captured-trade sample exists.",
 "f2/f4/f7 co-occur (conviction-day cluster) — they are one signal family, not three independent edges.",
 "f5 thread-scope is outcome-caused (reverse causality) and must never be scored at entry.",
 "All features derive from the poster's own language — adversarially fragile if he changes phrasing; forward TV-alert alignment remains the robust path.",
]

with open(P, "w", encoding="utf-8") as fh:
    json.dump(data, fh, indent=2, ensure_ascii=False)
print("classifications embedded")
