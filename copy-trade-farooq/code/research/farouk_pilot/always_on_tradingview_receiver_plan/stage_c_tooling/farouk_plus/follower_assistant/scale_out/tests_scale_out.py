"""Scale-out + runner lifecycle test sequence A-J (RESEARCH-ONLY, isolated logic; no ledgers touched)."""
from __future__ import annotations

import io
import os
import sys
from fractions import Fraction

HERE = os.path.dirname(os.path.abspath(__file__))
FA = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, FA)
import interpreter as I                                           # noqa: E402
import scale_out_classifier as S                                 # noqa: E402

PASS = 0
FAIL = 0
H = "seascalperfarouk Posted in gold-trades\n\n"
OPEN = {"instrument": "XAUUSD", "direction": "SELL", "entry": "4062.47"}


def ok(name, cond):
    global PASS, FAIL
    if cond:
        PASS += 1
    else:
        FAIL += 1
        print(f"FAIL: {name}")


def _instr_types(text):
    c = I.classify(text)
    return c["kind"], [i["instruction_type"] for i in c.get("instructions", [])]


# A. initial SELL signal -> exactly one campaign (ENTRY)
def test_A_initial_signal():
    c = I.classify(H + "@Whale XAUUSD Sell Zone: 4059–4069\nStop Loss: 4090\nhigh Risk: Low lot size")
    ok("A: initial SELL parses to ENTRY (one campaign)", c["kind"] == "ENTRY" and c["direction"] == "SHORT")


# B. tp1 -> management
def test_B_tp1():
    kind, types = _instr_types(H + "tp 1 now")
    ok("B: tp1 -> MANAGEMENT/TP1_TAKE", kind == "MANAGEMENT" and "TP1_TAKE" in types)


# C. first result card -> same-campaign scale-out, no new campaign, reconciles
def test_C_first_card():
    card = {"instrument": "XAUUSD", "direction": "SELL", "entry": "4062.47", "exit": "4054.34",
            "volume_label": "1", "result": "813", "timestamp": "2026-07-15T14:46:23Z", "provenance": "msg45757"}
    r = S.classify_result_card(card, OPEN)
    ok("C: first card SAME_CAMPAIGN_SCALE_OUT_EVIDENCE", r["classification"] == "SAME_CAMPAIGN_SCALE_OUT_EVIDENCE")
    ok("C: card does NOT create new campaign", r["creates_new_campaign"] is False)
    rec = S.reconcile_card(4062.47, 4054.34, 1, 813)
    ok("C: card reconciles (8.13*100*1=813)", rec["reconciles"] is True)
    ok("C: original size NOT inferred", "original_position_size" in r["not_inferred"])


# D. sl to entry -> per-leg BE, NO cancel of unfilled (regression)
def test_D_be_no_cancel():
    kind, types = _instr_types(H + "put sl to entry")
    ok("D: SL_TO_ENTRY present", "SL_TO_ENTRY" in types)
    ok("D: BE does NOT produce CANCEL_UNFILLED", not any("CANCEL" in t for t in types))
    # explicit risk-off IS a separate cancel
    _, rtypes = _instr_types(H + "cancel the limits")
    ok("D: explicit cancel produces a cancel instruction", any("CANCEL" in t for t in rtypes))


# E. pips commentary -> commentary, no closure
def test_E_commentary():
    kind, types = _instr_types(H + "140-150 pips if you're still holding.")
    ok("E: pips commentary -> not MANAGEMENT (no state transition)", kind in ("OTHER",))
    pc = S.profit_commentary("140-150 pips if you're still holding.", claimed_pips="140-150")
    ok("E: PROFIT_PROGRESS_COMMENTARY / no transition / UNVERIFIED", pc["automatic_state_transition"] == "NONE" and pc["pip_convention"] == "UNVERIFIED" and pc["is_implicit_close"] is False)


# F. second result card -> scale-out, campaign remains open
def test_F_second_card():
    card = {"instrument": "XAUUSD", "direction": "SELL", "entry": "4062.47", "exit": "4047.18",
            "volume_label": "1", "result": "1529", "timestamp": "2026-07-15T15:35:58Z", "provenance": "msg45764"}
    r = S.classify_result_card(card, OPEN)
    ok("F: second card scale-out, no new campaign", r["classification"] == "SAME_CAMPAIGN_SCALE_OUT_EVIDENCE" and not r["creates_new_campaign"])
    ok("F: reconciles 15.29*100*1=1529", S.reconcile_card(4062.47, 4047.18, 1, 1529)["reconciles"])
    lc = S.runner_transition("PARTIALS_BANKED_RUNNER_ACTIVE", "RESULT_CARD", residual_after="1/10")
    ok("F: result card does NOT close the campaign", lc == "PARTIALS_BANKED_RUNNER_ACTIVE")


# G. "350 pips close 90% leave 10%" -> explicit partial, 90% of remaining, retain 10%, runner active, open
def test_G_explicit_partial():
    c = I.classify(H + "350 pips close 90% leave 10%")
    e = [i for i in c.get("instructions", []) if i["instruction_type"] == "EXPLICIT_PERCENTAGE_PARTIAL_CLOSE"]
    ok("G: EXPLICIT_PERCENTAGE_PARTIAL_CLOSE", len(e) == 1)
    if e:
        ok("G: close 90 retain 10 sum 100", e[0]["close_percentage"] == 90 and e[0]["retain_percentage"] == 10 and e[0]["percentage_sum"] == 100)
        ok("G: quantity base = currently remaining open filled", e[0]["quantity_base"] == "CURRENTLY_REMAINING_OPEN_FILLED_QUANTITY")
        ok("G: runner requested", e[0]["runner_requested"] is True)
    # apply to a remaining open of 1/3 -> close 90% of 1/3, retain 10% of 1/3
    ap = S.apply_scale_out(Fraction(1, 3), 90)
    ok("G: closes 90% of REMAINING (0.90*1/3)", ap["closed"] == str(Fraction(9, 10) * Fraction(1, 3)))
    ok("G: residual after = 10% of remaining", ap["remaining_after"] == str(Fraction(1, 10) * Fraction(1, 3)))
    lc = S.runner_transition("OPEN", "EXPLICIT_PERCENTAGE_PARTIAL_CLOSE", residual_after=ap["remaining_after"])
    ok("G: -> PARTIALS_BANKED_RUNNER_ACTIVE (campaign open)", lc == "PARTIALS_BANKED_RUNNER_ACTIVE")


# H. third result card -> scale-out, no new campaign
def test_H_third_card():
    card = {"instrument": "XAUUSD", "direction": "SELL", "entry": "4062.47", "exit": "4030.77",
            "volume_label": "0.5", "result": "1585", "timestamp": "2026-07-15T16:00:00Z", "provenance": "card3"}
    r = S.classify_result_card(card, OPEN)
    ok("H: third card scale-out, no new campaign", r["classification"] == "SAME_CAMPAIGN_SCALE_OUT_EVIDENCE" and not r["creates_new_campaign"])
    ok("H: reconciles 31.70*100*0.5=1585", S.reconcile_card(4062.47, 4030.77, "0.5", 1585)["reconciles"])


# I. duplicate cards/messages -> idempotent (deterministic; same input same output, no extra transition)
def test_I_duplicate_idempotent():
    card = {"instrument": "XAUUSD", "direction": "SELL", "entry": "4062.47", "exit": "4054.34",
            "volume_label": "1", "result": "813", "timestamp": "t", "provenance": "p"}
    r1 = S.classify_result_card(card, OPEN)
    r2 = S.classify_result_card(card, OPEN)
    ok("I: duplicate card classification identical (idempotent)", r1 == r2)
    # a result card never triggers a lifecycle transition, so a duplicate cannot double-transition
    ok("I: duplicate card no lifecycle transition", S.runner_transition("PARTIALS_BANKED_RUNNER_ACTIVE", "RESULT_CARD", "1/10") == "PARTIALS_BANKED_RUNNER_ACTIVE")


# J. invalid percentages -> fail closed
def test_J_invalid_pct():
    for m in ("close 90 leave 20", "close 110 leave -10", "close 50 leave 60"):
        c = I.classify(H + m)
        ok(f"J: '{m}' -> NEEDS_HUMAN_REVIEW (fail closed)", c["kind"] == "NEEDS_HUMAN_REVIEW")
    # never silently normalised: no EXPLICIT_PERCENTAGE_PARTIAL_CLOSE emitted for invalid
    c = I.classify(H + "close 90 leave 20")
    ok("J: invalid never emits a valid partial", "instructions" not in c)


# runner lifecycle: only terminal events close
def test_runner_terminal_only():
    ok("runner: FINAL_CLOSE closes", S.runner_transition("PARTIALS_BANKED_RUNNER_ACTIVE", "FINAL_CLOSE", "0") == "CLOSED")
    ok("runner: big profit does NOT close", S.runner_transition("PARTIALS_BANKED_RUNNER_ACTIVE", "PROFIT_PROGRESS_COMMENTARY", "1/10") == "PARTIALS_BANKED_RUNNER_ACTIVE")
    ok("runner: 90% partial does NOT close (residual remains)", S.runner_transition("OPEN", "EXPLICIT_PERCENTAGE_PARTIAL_CLOSE", "1/30") == "PARTIALS_BANKED_RUNNER_ACTIVE")
    ok("runner: runner stop-hit closes", S.runner_transition("PARTIALS_BANKED_RUNNER_ACTIVE", "RUNNER_STOP_HIT", "0") == "CLOSED")


if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    for fn in [test_A_initial_signal, test_B_tp1, test_C_first_card, test_D_be_no_cancel, test_E_commentary,
               test_F_second_card, test_G_explicit_partial, test_H_third_card, test_I_duplicate_idempotent,
               test_J_invalid_pct, test_runner_terminal_only]:
        fn()
    print(f"\n{PASS} passed, {FAIL} failed")
    print("TRADINGVIEW_PRICE_SEMANTICS_UNVERIFIED | BROKER_EXECUTION_EQUIVALENCE_UNPROVEN | SIMULATION_ONLY")
    sys.exit(1 if FAIL else 0)
