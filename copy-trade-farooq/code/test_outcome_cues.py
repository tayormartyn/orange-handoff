"""
test_outcome_cues.py — outcome-cue detection + matching for the history puller.

Proves the management/result cues are read correctly:
  * win  — "tp1 hit", "all tp hit", "+50 pips"
  * loss — "sl hit", "stopped out"  (the ACTUAL stop being hit)
  * breakeven — "sl to entry", "moved to breakeven"  (NOT a loss)
  * missed — "no fill", "didn't fill"
  * the critical "sl to entry  !=  loss" distinction
  * conservative matching: no cue OR conflicting cues -> 'unclear' (no evidence),
    and a win-then-runner-to-breakeven still reads 'win'.

All deterministic — no API key, read-only.  Run:  python test_outcome_cues.py
"""

import module_a_telegram as t


# ----------------------------------------------------------------------------
# detect_outcome_cue — single message -> win / loss / breakeven / missed / None
# ----------------------------------------------------------------------------
def test_win_cues():
    for msg in ("tp1 hit", "TP1 HIT", "tp hit", "all tp hit", "all targets hit",
                "target hit", "tp2 hit", "tp3 hit", "hit tp1",
                "+50 pips", "+ 120 pips", "100+ pips!!!!!",
                "banked 80 pips", "closed in profit"):
        assert t.detect_outcome_cue(msg) == "win", msg


def test_loss_cues():
    for msg in ("sl hit", "SL HIT", "stop loss hit", "stopped out", "stopped",
                "hit my sl", "stop hit", "-40 pips", "took the loss",
                "closed in loss"):
        assert t.detect_outcome_cue(msg) == "loss", msg


def test_breakeven_cues():
    for msg in ("sl to entry", "SL to entry", "moved to breakeven", "move sl to entry",
                "breakeven", "break even", "scratch", "closed at entry",
                "stopped at entry", "moved to be"):
        assert t.detect_outcome_cue(msg) == "breakeven", msg


def test_missed_cues():
    for msg in ("missed", "no fill", "didn't fill", "did not fill",
                "never filled", "missed entry"):
        assert t.detect_outcome_cue(msg) == "missed", msg


def test_no_cue_returns_none():
    for msg in ("good morning team", "gold looking bullish", "watch this level",
                "XAUUSD buy 4016-4006 sl 3970 tp1 4022 tp2 4027", ""):
        assert t.detect_outcome_cue(msg) is None, msg


def test_sl_to_entry_is_not_a_loss():
    # The critical distinction: a moved-to-breakeven stop is NOT a loss.
    assert t.detect_outcome_cue("sl to entry") == "breakeven"
    assert t.detect_outcome_cue("moved sl to entry") == "breakeven"
    assert t.detect_outcome_cue("sl to entry, risk free now") == "breakeven"
    # …whereas the stop actually being hit IS a loss.
    assert t.detect_outcome_cue("sl hit") == "loss"
    assert t.detect_outcome_cue("stopped out") == "loss"


def test_win_beats_breakeven_in_one_message():
    # "tp1 hit, move sl to entry" -> won TP1 (then runner to BE) -> win.
    assert t.detect_outcome_cue("tp1 hit, move sl to entry") == "win"


def test_breakeven_stop_being_hit_is_not_a_loss():
    # The moved-to-entry (breakeven) stop being hit is a SCRATCH, not a loss.
    assert t.detect_outcome_cue("SL at entry hit, we're insured") == "breakeven"
    assert t.detect_outcome_cue("stop at entry hit") == "breakeven"


def test_missed_does_not_fire_on_missed_my_sl():
    # "just missed my sl" = price nearly hit the stop — NOT a missed entry.
    assert t.detect_outcome_cue("just missed my sl") != "missed"
    assert t.detect_outcome_cue("missed by a pip") != "missed"


def test_missed_does_not_fire_on_missed_tp():
    # "missed tp3" is not a missed ENTRY; with a win cue present it's a win.
    assert t.detect_outcome_cue("missed tp3 but tp1 and tp2 hit") == "win"


# ----------------------------------------------------------------------------
# match_outcome_for_window — resolve a trade's window of follow-up messages.
# It now returns a GRANULAR category; outcome_group() rolls it up to the coarse
# win/loss/breakeven/missed/unclear bucket the chronology tests care about.
# ----------------------------------------------------------------------------
def test_match_single_outcomes():
    assert t.match_outcome_for_window(["tp1 hit"])[0] == t.OUT_TARGET_HIT
    assert t.match_outcome_for_window(["sl hit"])[0] == t.OUT_STOP_LOSS
    assert t.match_outcome_for_window(["sl to entry"])[0] == t.OUT_BREAKEVEN
    assert t.match_outcome_for_window(["no fill"])[0] == t.OUT_MISSED
    # …and the coarse roll-up of each is what callers used to read.
    assert t.outcome_group(t.match_outcome_for_window(["tp1 hit"])[0]) == "win"
    assert t.outcome_group(t.match_outcome_for_window(["sl hit"])[0]) == "loss"
    assert t.outcome_group(t.match_outcome_for_window(["sl to entry"])[0]) == "breakeven"
    assert t.outcome_group(t.match_outcome_for_window(["no fill"])[0]) == "missed"


def test_match_empty_window_is_unclear_no_evidence():
    outcome, evidence = t.match_outcome_for_window([])
    assert outcome == t.OUT_UNCLEAR and evidence == ""
    # chatter-only window with no cue is also unclear
    outcome, evidence = t.match_outcome_for_window(["nice move", "watching"])
    assert outcome == t.OUT_UNCLEAR and evidence == ""


def test_match_win_then_breakeven_is_win_with_evidence():
    outcome, evidence = t.match_outcome_for_window(["tp1 hit guys", "now move sl to entry"])
    assert t.outcome_group(outcome) == "win"
    assert "tp1 hit" in evidence.lower()


def test_win_to_tp1_dominates_even_if_runner_later_stops():
    # "tp1 hit" is a VERIFIABLE win to tp1; a later stop on the runner doesn't
    # erase it. Scored as a win (no partial sizes assumed).
    outcome, evidence = t.match_outcome_for_window(["tp1 hit", "then sl hit"])
    assert outcome == t.OUT_TARGET_HIT
    assert "tp1 hit" in evidence.lower()


# ----------------------------------------------------------------------------
# CHRONOLOGICAL MANAGEMENT — no retroactive breakeven
# ----------------------------------------------------------------------------
def test_original_stop_before_be_move_is_loss():
    # Stop hit BEFORE the move-to-BE message -> the ORIGINAL stop -> LOSS,
    # NOT a (retroactive) breakeven, even though a move-to-BE appears later.
    outcome, evidence = t.match_outcome_for_window(["stopped out", "ok sl to entry now"])
    assert outcome == t.OUT_STOP_LOSS                # the original stop, -1R
    assert "stopped out" in evidence.lower()


def test_breakeven_stop_after_be_move_is_breakeven():
    # Stop hit AFTER the move-to-BE -> the breakeven stop -> BREAKEVEN.
    outcome, evidence = t.match_outcome_for_window(["moved sl to entry", "sl hit"])
    assert outcome == t.OUT_BREAKEVEN
    assert "sl hit" in evidence.lower()


def test_lone_move_to_be_is_breakeven_scratch():
    assert t.match_outcome_for_window(["sl to entry"])[0] == t.OUT_BREAKEVEN
    assert t.match_outcome_for_window(["risk free now"])[0] == t.OUT_BREAKEVEN


def test_lone_stop_is_loss():
    # A bare stop is the ORIGINAL stop (-1R); a stated-pips stop is a MANUAL loss
    # (scored at its actual size) — both roll up to a loss, neither is dropped.
    assert t.match_outcome_for_window(["sl hit"])[0] == t.OUT_STOP_LOSS
    assert t.match_outcome_for_window(["stopped out, -30 pips"])[0] == t.OUT_MANUAL_LOSS
    assert t.outcome_group(t.match_outcome_for_window(["stopped out, -30 pips"])[0]) == "loss"


def test_explicit_breakeven_stop_hit_is_breakeven():
    assert t.match_outcome_for_window(["SL at entry hit"])[0] == t.OUT_BREAKEVEN


# ----------------------------------------------------------------------------
# STATED partial profit -> small win; UNSTATED -> stays breakeven (no assuming)
# ----------------------------------------------------------------------------
def test_stated_partial_before_scratch_is_win():
    # tp1 hit, then the runner scratches at BE -> a small WIN to the STATED tp1.
    outcome, evidence = t.match_outcome_for_window(["tp1 hit", "moved sl to entry", "sl hit"])
    assert outcome == t.OUT_TARGET_HIT
    assert "tp1 hit" in evidence.lower()


def test_stated_pips_profit_before_scratch_is_win():
    outcome, ev = t.match_outcome_for_window(["secured +40 pips", "sl to entry", "sl hit"])
    assert outcome == t.OUT_MANAGED_PROFIT and "40" in ev


def test_took_profit_at_price_is_win():
    # "took profit" with no reconstructable exit -> a win, scored 0R (r-unknown).
    assert t.match_outcome_for_window(["took profit at 2350", "sl to entry"])[0] == t.OUT_PROFIT_RUNKNOWN


def test_move_to_be_no_stated_profit_then_be_stop_is_breakeven():
    # "moved to BE / sl to entry" with NO stated profit, then the BE stop -> BREAKEVEN.
    # We must NOT credit an unverifiable partial here.
    assert t.match_outcome_for_window(["moved to BE", "sl hit"])[0] == t.OUT_BREAKEVEN
    assert t.match_outcome_for_window(["sl to entry", "sl hit"])[0] == t.OUT_BREAKEVEN


def test_unrealised_running_pips_is_not_a_win():
    # "running 200 pips" is UNREALISED; he then moved to BE -> scratch, not a win.
    assert t.match_outcome_for_window(["running 200 pips, sl to entry", "sl hit"])[0] == t.OUT_BREAKEVEN


def test_secured_at_breakeven_is_not_a_win():
    # "secured at breakeven" = protected at BE, NOT a profit -> breakeven, never win.
    assert t.detect_outcome_cue("secured at breakeven") == "breakeven"
    assert t.match_outcome_for_window(["secured at breakeven", "sl hit"])[0] == t.OUT_BREAKEVEN


# ----------------------------------------------------------------------------
# AUDIT ROUND 2 — evidence-link, net-loss verdicts, pip-range, near-miss, target>pips
# ----------------------------------------------------------------------------
def test_win_subtype_three_tier_hit_pips_instruction():
    # Explicit HIT -> target_hit (full target R).
    assert t._win_subtype("all TP hit 500 pips") == "target_hit"
    assert t._win_subtype("tp1 hit") == "target_hit"
    assert t._win_subtype("out of the trade after securing tp 1") == "target_hit"
    # Stated PIPS without an explicit hit -> profit_pips (score to the confirmed
    # pips, NOT a distant target that was only instructed).
    assert t._win_subtype("100 pips take tp 2") == "profit_pips"
    assert t._win_subtype("tp 1 we have 70 pips") == "profit_pips"
    assert t._win_subtype("we got 90 pips") == "profit_pips"
    # A bare take/now INSTRUCTION (no pips, no hit) -> target_hit (a reached target).
    assert t._win_subtype("tp 1 now") == "target_hit"
    assert t._win_subtype("take tp 1") == "target_hit"
    # Nothing quantifiable -> r-unknown.
    assert t._win_subtype("closed in profit") == "profit_runknown"
    assert t._win_subtype("more profit") == "profit_runknown"


def test_evidence_link_stores_strongest_confirmation_not_first_instruction():
    # The first message is a bare instruction; the real confirmation comes later.
    cat, ev = t.match_outcome_for_window(
        ["take tp 1", "more tp", "all TP hit 500 pips"])
    assert cat == t.OUT_TARGET_HIT
    assert "all tp hit" in ev.lower()           # the STRONG/LATE confirmation, not "take tp 1"

    # pips-only window: the stated-pips result outranks bare "take some off".
    cat, ev = t.match_outcome_for_window(["take some off", "we got 90 pips sl entry"])
    assert cat == t.OUT_MANAGED_PROFIT and "90" in ev


def test_confirmed_hit_outranks_later_almost_recap():
    # This trade's own "tp1 hit" must not be displaced by a later multi-trade recap
    # that merely says "almost hit tp1".
    cat, ev = t.match_outcome_for_window(
        ["tp1 hit", "Difficult day: the first trade almost hit TP1, took partials"])
    assert cat == t.OUT_TARGET_HIT
    assert "tp1 hit" in ev.lower()


def test_net_loss_verdict_close_for_small_loss_overrides_partial():
    # A bare partial ("small tp") followed by an explicit closure-for-a-loss /
    # "1 win, 1 loss" verdict -> the whole trade is a manual loss (fix 1).
    cat, ev = t.match_outcome_for_window(
        ["50 pips small tp", "take profit on best entry",
         "better to close it for a small loss than a huge one; 1 win, 1 loss today"])
    assert cat == t.OUT_MANUAL_LOSS


def test_net_loss_verdict_some_profit_some_loss_counts_as_loss():
    # "some in profit, some in a loss ... count it as a loss overall" -> manual loss
    # overriding the earlier "take some profit" (fix 3).
    cat, ev = t.match_outcome_for_window(
        ["take some profit on best entry",
         "I closed some positions in profit and some in a loss, but I'll count it as a loss overall"])
    assert cat == t.OUT_MANUAL_LOSS


def test_multi_trade_tally_is_not_a_per_trade_verdict():
    # "6 trades, 1 loss" is a DAY tally, not THIS trade's verdict -> a real tp win
    # is NOT flipped to a loss.
    cat, _ = t.match_outcome_for_window(["tp1 hit", "Result: 6 trades, 1 loss"])
    assert cat == t.OUT_TARGET_HIT


def test_pip_range_is_not_a_manual_loss_breakeven_be_stop():
    # "SL at entry hit ... still up 50-60 pips" — the "-60" in the RANGE "50-60"
    # must NOT read as a -60 pip manual loss; the BE-stop -> breakeven (fix 2).
    cat, ev = t.match_outcome_for_window(
        ["50 pips", "sl enty TP1 4334 TP2 4329",
         "SL at entry hit, choppy here. Still up 50-60 pips though. Wait for next setup"])
    assert cat == t.OUT_BREAKEVEN
    # a genuine "-40 pips" is still a manual loss
    assert t.match_outcome_for_window(["cut for -40 pips"])[0] == t.OUT_MANUAL_LOSS


def test_near_miss_of_stop_is_not_a_missed_entry():
    # "just missed our sl" is a near-miss of the STOP, not a missed entry.
    assert t._detect_event("just missed our sl") != "missed"
    assert t._detect_event("missed our sl by a pip") != "missed"
    # a real no-fill is still missed
    assert t._detect_event("missed this entry, no fill") == "missed"


def test_assign_invalid_stop_win_downgraded_to_r_unknown():
    # A confirmed target hit on a trade whose stop is on the WRONG side of entry
    # (LONG, sl 4318 ABOVE entry 4231-4241) -> kept a win, but profit_confirmed_r_unknown.
    rows = [
        _row("clean signal", "XAUUSD", "XAUUSD buy 4241-4231 sl 4318",
             "LONG", "4241-4231", "4318"),
        _row("commentary", "", "tp 1"),
        _row("commentary", "", "sl entry tp 1"),
    ]
    t.assign_detected_outcomes(rows)
    assert rows[0]["DetectedOutcome"] == t.OUT_PROFIT_RUNKNOWN
    assert t.outcome_group(rows[0]["DetectedOutcome"]) == "win"


def test_assign_valid_stop_win_keeps_target_hit():
    # Control: the same shape with a VALID stop stays target_hit.
    rows = [
        _row("clean signal", "XAUUSD", "XAUUSD buy 4231-4241 sl 4200",
             "LONG", "4231-4241", "4200"),
        _row("commentary", "", "tp 1 hit"),
    ]
    t.assign_detected_outcomes(rows)
    assert rows[0]["DetectedOutcome"] == t.OUT_TARGET_HIT


# ----------------------------------------------------------------------------
# AUDIT ROUND 3 — re-entry attribution + confirmed-pips-over-distant-target
# ----------------------------------------------------------------------------
def test_reentry_after_parent_result_is_not_credited_to_parent():
    # Parent took a small unspecified profit, then BE; the "tp 1" comes AFTER an
    # explicit re-entry -> it belongs to the re-entry, not the parent -> r-unknown.
    cat, ev = t.match_outcome_for_window(
        t._truncate_at_reentry(["small tp", "sl entry hit", "re-enter", "tp 1 now", "tp 1"]))
    assert cat == t.OUT_PROFIT_RUNKNOWN
    assert "tp 1" not in ev.lower() or "small" in ev.lower()


def test_reentry_without_prior_result_does_not_truncate():
    # A re-entry with NO resolved parent result before it is the same trade
    # continuing — the window is NOT truncated and the later confirmation counts.
    w = t._truncate_at_reentry(["re-enter playing it out", "take tp 3 170 pips"])
    assert "take tp 3 170 pips" in w and len(w) == 2
    assert t.outcome_group(t.match_outcome_for_window(w)[0]) == "win"


def test_pip_take_outranks_bare_target_instruction():
    # "50 pips tp 1" is a take-instruction WITH a stated pip figure -> managed_profit
    # (scored to the confirmed pips), NOT target_hit to a distant tp1.
    assert t.match_outcome_for_window(["50 pips tp 1"])[0] == t.OUT_MANAGED_PROFIT
    assert t.match_outcome_for_window(["tp 1 we have 70 pips"])[0] == t.OUT_MANAGED_PROFIT


def test_explicit_hit_keeps_target_hit_even_with_pips():
    # An explicit HIT outranks a pip figure -> target_hit (full target R).
    cat, ev = t.match_outcome_for_window(["100 pips take tp 2", "tp 1 -2 hit show profit"])
    assert cat == t.OUT_TARGET_HIT
    assert "hit" in ev.lower()
    # "all tp hit" stays target_hit despite the hyped pips.
    assert t.match_outcome_for_window(["we got 150 pips", "all TP hit 500 pips"])[0] == t.OUT_TARGET_HIT


def test_bare_instruction_no_pips_stays_target_hit():
    # No pips, no explicit hit, just "tp 1 now" -> still a reached target.
    assert t.match_outcome_for_window(["tp 1 now"])[0] == t.OUT_TARGET_HIT
    assert t.match_outcome_for_window(["take tp 1", "more tp"])[0] == t.OUT_TARGET_HIT


def test_profit_strength_ordering():
    assert t._profit_strength("tp1 hit") == 3
    assert t._profit_strength("all tp hit") == 3
    assert t._profit_strength("we got 90 pips") == 2
    assert t._profit_strength("50 pips tp 1") == 2          # pips present -> tier 2
    assert t._profit_strength("tp 1 now") == 1
    assert t._profit_strength("more profit") == 0


# ----------------------------------------------------------------------------
# AUDIT ROUND 4 — the RE-ENTRY BOUNDARY cuts both ways
# ----------------------------------------------------------------------------
def test_post_reentry_result_does_not_leak_to_parent():
    # Parent took 50 pips, then "re-enter", then a 170-pip result AFTER the
    # re-entry. The parent is scored to the PRE-re-entry 50 pips ONLY; the 170 pips
    # belongs to the re-entry and must NOT leak backwards.
    w = t._truncate_at_reentry(
        ["50 pips", "Re-enter playing it out", "100 pisp", "take tp 3 170 pips"])
    assert w == ["50 pips"]                               # everything from re-entry on is dropped
    cat, ev = t.match_outcome_for_window(w)
    assert cat == t.OUT_MANAGED_PROFIT and "50" in ev and "170" not in ev


def test_post_newsignal_result_does_not_leak_to_parent():
    # A NEW signal (not just a re-entry) also bounds the parent.
    w = t._truncate_at_reentry(
        ["300 pips", "XAUUSD SELL 4078-4092 SL 4120", "90 pips take 2 tp's"])
    assert w == ["300 pips"]
    assert "90" not in t.match_outcome_for_window(w)[1]


def test_pre_reentry_confirmed_result_IS_credited():
    # The boundary also credits a genuine pre-re-entry result: a bare "300 pips"
    # confirmed before any re-entry is a managed profit (becomes target_hit only
    # after the price/target refinement in assign).
    assert t.match_outcome_for_window(["300 pips"])[0] == t.OUT_MANAGED_PROFIT
    assert t.match_outcome_for_window(["300 pips 💙💙💙"])[0] == t.OUT_MANAGED_PROFIT


def test_bare_pips_recognised_but_unrealised_excluded():
    assert t._bare_pips_result("300 pips") is True
    assert t._bare_pips_result("50 pips") is True
    assert t._bare_pips_result("running 200 pips") is False     # unrealised
    assert t._bare_pips_result("still up 50-60 pips") is False  # unrealised float
    assert t._bare_pips_result("after a 130-pips") is False     # stop description
    assert t._bare_pips_result("almost 200 pips") is False      # did not reach


def test_floating_pips_then_be_scratch_is_breakeven():
    # A floating "50 pips" that then scratches at the BE stop (no banked partial)
    # is a BREAKEVEN, not a win — the float was never realised.
    assert t.match_outcome_for_window(
        ["50 pips", "sl to entry", "SL at entry hit, still up 50-60 pips"])[0] == t.OUT_BREAKEVEN
    # …but a banked pip take (or one cut at a re-entry before any BE) IS a win.
    assert t.match_outcome_for_window(["we got 90 pips"])[0] == t.OUT_MANAGED_PROFIT


def test_gold_pip_points_conversion():
    # Gold "pips" are $0.10 increments; other assets are left as-is.
    assert t._pip_points("XAUUSD", 300) == 30.0
    assert t._pip_points("GOLD", 50) == 5.0
    assert t._pip_points("EURUSD", 50) == 50.0


def test_refine_bare_pips_to_target_when_reaching_furthest():
    # 300 gold pips (≈30 pts) reaches TP3 (~4040 from ~4011 entry) -> target_hit.
    row = _row("clean signal", "XAUUSD", "XAUUSD buy 4006-4016 sl 3970 tp1 4022 tp2 4027 tp3 4040",
               "LONG", "4006-4016", "3970")
    row["TP1"], row["TP2"], row["TP3"] = "4022", "4027", "4040"
    assert t._refine_win_with_pips(t.OUT_MANAGED_PROFIT, "300 pips", row) == t.OUT_TARGET_HIT
    # 90 gold pips (≈9 pts) falls short of TP3 -> stays a managed partial.
    assert t._refine_win_with_pips(t.OUT_MANAGED_PROFIT, "we got 90 pips", row) == t.OUT_MANAGED_PROFIT
    # an explicit hit is never downgraded.
    assert t._refine_win_with_pips(t.OUT_TARGET_HIT, "all tp hit", row) == t.OUT_TARGET_HIT


def test_stop_is_valid_helper():
    assert t._stop_is_valid("LONG", "4231-4241", "4318") is False   # stop above a long entry
    assert t._stop_is_valid("LONG", "4231-4241", "4200") is True
    assert t._stop_is_valid("SHORT", "4339-4345", "4360") is True   # stop above a short entry
    assert t._stop_is_valid("SHORT", "4339-4345", "4330") is False
    assert t._stop_is_valid("LONG", "", "") is True                 # can't tell -> valid


# ----------------------------------------------------------------------------
# HONESTY FIXES — granular categories (manual_loss never dropped; r-unknown win
# scored 0R, never credited TP1; every clean row reconciles to one category)
# ----------------------------------------------------------------------------
def test_manual_loss_never_dropped():
    # A trade cut for a stated loss is a MANUAL loss (scored at its real size),
    # NOT missed, NOT breakeven, NOT dropped.
    for msg in ("cut for -40 pips", "closed for a loss", "closed in loss",
                "manually closed", "cut the trade", "took a small loss",
                "stopped for -30 pips"):
        cat = t.match_outcome_for_window([msg])[0]
        assert cat == t.OUT_MANUAL_LOSS, (msg, cat)
        assert t.outcome_group(cat) == "loss", (msg, cat)


def test_net_loss_verdict_counts_whole_sequence_as_loss():
    # His own final word "count this as a loss overall" OVERRIDES an earlier
    # partial tp -> the whole sequence is a (manual) loss, never a win.
    for msg in ("count this as a loss overall", "count the sequence as a loss",
                "overall a loss", "net loss", "call it a loss"):
        cat = t.match_outcome_for_window([msg])[0]
        assert cat == t.OUT_MANUAL_LOSS, (msg, cat)
    # even after a stated tp1 partial earlier in the window
    cat, _ = t.match_outcome_for_window(["tp1 hit", "but count this as a loss overall"])
    assert cat == t.OUT_MANUAL_LOSS


def test_almost_reached_tp1_is_not_credited_tp1():
    # "almost reached tp1" means it did NOT reach the target -> r-unknown win
    # (0R), NEVER target_hit (which would credit TP1's R).
    for msg in ("almost reached tp1", "almost tp1", "almost hit tp1",
                "we almost got to tp1"):
        cat = t.match_outcome_for_window([msg])[0]
        assert cat == t.OUT_PROFIT_RUNKNOWN, (msg, cat)
        assert cat != t.OUT_TARGET_HIT, (msg, cat)
        assert t.outcome_group(cat) == "win", (msg, cat)   # still a win label


def test_r_unknown_win_for_unreconstructable_exit():
    # "best layer closed in profit" — money made, but no reconstructable exit
    # -> profit_confirmed_r_unknown (win label, 0R), not an assumed TP1.
    for msg in ("best layer closed in profit", "closed in profit",
                "took profit", "secured profits"):
        cat = t.match_outcome_for_window([msg])[0]
        assert cat == t.OUT_PROFIT_RUNKNOWN, (msg, cat)
        assert t.outcome_group(cat) == "win", (msg, cat)


def test_named_target_is_target_hit_not_r_unknown():
    # A NAMED target reached is target_hit (R to that target), distinct from the
    # r-unknown bucket above.
    assert t.match_outcome_for_window(["tp1 hit"])[0] == t.OUT_TARGET_HIT
    assert t.match_outcome_for_window(["tp2 reached"])[0] == t.OUT_TARGET_HIT
    assert t.match_outcome_for_window(["all tp hit"])[0] == t.OUT_TARGET_HIT


def test_original_stop_vs_manual_loss_distinction():
    # The original stop being hit is -1R (original_stop_loss); a stated-size cut
    # is a manual_loss (its actual R). Both are losses, but DIFFERENT categories.
    assert t.match_outcome_for_window(["sl hit"])[0] == t.OUT_STOP_LOSS
    assert t.match_outcome_for_window(["stopped out"])[0] == t.OUT_STOP_LOSS
    assert t.match_outcome_for_window(["cut for -40 pips"])[0] == t.OUT_MANUAL_LOSS


def test_every_window_resolves_to_exactly_one_known_category():
    # Reconciliation invariant: match_outcome_for_window always returns ONE of the
    # known categories — there is no silent "fell through to nothing".
    known = {t.OUT_TARGET_HIT, t.OUT_MANAGED_PROFIT, t.OUT_PROFIT_RUNKNOWN,
             t.OUT_MANUAL_LOSS, t.OUT_STOP_LOSS, t.OUT_BREAKEVEN,
             t.OUT_MISSED, t.OUT_UNCLEAR}
    windows = [
        ["tp1 hit"], ["secured +40 pips"], ["closed in profit"],
        ["cut for -40 pips"], ["sl hit"], ["sl to entry"], ["no fill"],
        ["count this as a loss overall"], ["good morning"], [],
    ]
    for w in windows:
        cat = t.match_outcome_for_window(w)[0]
        assert cat in known, (w, cat)


# ----------------------------------------------------------------------------
# assign_detected_outcomes — end-to-end over a chronological row list
# ----------------------------------------------------------------------------
def _row(cls, asset="", raw="", direction="", entry="", stop=""):
    return {"Date": "", "Sender": "", "Asset": asset, "Direction": direction,
            "Entry": entry, "Stop": stop, "TP1": "", "TP2": "", "TP3": "",
            "Classification": cls, "Confidence": "", "DetectedOutcome": "",
            "OutcomeEvidence": "", "RawMessage": raw}


def test_assign_matches_outcome_to_entry():
    rows = [
        _row("clean signal", "XAUUSD", "XAUUSD buy 4016-4006 sl 3970", "LONG", "4006-4016", "3970"),
        _row("commentary", "", "tp1 hit, smashing it"),
        _row("commentary", "", "move sl to entry"),
    ]
    t.assign_detected_outcomes(rows)
    assert rows[0]["DetectedOutcome"] == t.OUT_TARGET_HIT
    assert t.outcome_group(rows[0]["DetectedOutcome"]) == "win"
    assert "tp1 hit" in rows[0]["OutcomeEvidence"].lower()
    # the management rows themselves are not entries -> left blank
    assert rows[1]["DetectedOutcome"] == ""


def test_assign_window_stops_at_next_same_asset_entry():
    # Entry A, then a re-entry on the same asset BEFORE any outcome -> A is unclear
    # (its window is empty); the loss after the re-entry belongs to the re-entry.
    rows = [
        _row("clean signal", "XAUUSD", "XAUUSD buy 4016-4006 sl 3970", "LONG", "4006-4016", "3970"),
        _row("clean signal", "XAUUSD", "XAUUSD buy 4000-3990 sl 3960", "LONG", "3990-4000", "3960"),
        _row("commentary", "", "sl hit"),
    ]
    t.assign_detected_outcomes(rows)
    assert rows[0]["DetectedOutcome"] == t.OUT_UNCLEAR  # no outcome before the re-entry
    assert rows[0]["OutcomeEvidence"] == ""
    assert rows[1]["DetectedOutcome"] == t.OUT_STOP_LOSS  # the stop belongs to the re-entry
    assert t.outcome_group(rows[1]["DetectedOutcome"]) == "loss"


def test_assign_other_asset_outcome_not_matched():
    rows = [
        _row("clean signal", "XAUUSD", "XAUUSD buy 4016 sl 3970", "LONG", "4016", "3970"),
        _row("commentary", "", "BTCUSD tp1 hit"),        # different asset
    ]
    t.assign_detected_outcomes(rows)
    assert rows[0]["DetectedOutcome"] == t.OUT_UNCLEAR   # the BTC win isn't ours


def test_assign_chronology_original_stop_before_move_is_loss():
    # Entry, then the stop is hit, THEN (later) a move-to-BE message: the stop
    # came first, at the original level -> LOSS (no retroactive breakeven).
    rows = [
        _row("clean signal", "XAUUSD", "XAUUSD buy 4016-4006 sl 3970", "LONG", "4006-4016", "3970"),
        _row("commentary", "", "stopped out"),
        _row("commentary", "", "we were moving sl to entry"),
    ]
    t.assign_detected_outcomes(rows)
    assert rows[0]["DetectedOutcome"] == t.OUT_STOP_LOSS
    assert t.outcome_group(rows[0]["DetectedOutcome"]) == "loss"


def test_assign_chronology_be_stop_after_move_is_breakeven():
    # Entry, move-to-BE, THEN the stop is hit: that's the breakeven stop -> BE.
    rows = [
        _row("clean signal", "XAUUSD", "XAUUSD buy 4016-4006 sl 3970", "LONG", "4006-4016", "3970"),
        _row("commentary", "", "running nicely, sl to entry"),
        _row("commentary", "", "sl hit"),
    ]
    t.assign_detected_outcomes(rows)
    assert rows[0]["DetectedOutcome"] == t.OUT_BREAKEVEN


def test_assign_manual_loss_matched_and_not_dropped():
    # A trade Farouk cut for a stated loss must be matched as a MANUAL loss on the
    # entry row — never left unclear/missed/breakeven.
    rows = [
        _row("clean signal", "XAUUSD", "XAUUSD buy 4016-4006 sl 3970", "LONG", "4006-4016", "3970"),
        _row("commentary", "", "cut the trade for -45 pips, not our day"),
    ]
    t.assign_detected_outcomes(rows)
    assert rows[0]["DetectedOutcome"] == t.OUT_MANUAL_LOSS
    assert t.outcome_group(rows[0]["DetectedOutcome"]) == "loss"


def test_assign_instruction_only_when_chatter_but_no_result():
    # Same-asset/thread follow-up exists but states no result -> instruction_only,
    # distinct from a bare 'unclear' (no candidate messages at all).
    rows = [
        _row("clean signal", "XAUUSD", "XAUUSD buy 4016-4006 sl 3970", "LONG", "4006-4016", "3970"),
        _row("commentary", "", "XAUUSD hold your best entry and be patient"),
    ]
    t.assign_detected_outcomes(rows)
    assert rows[0]["DetectedOutcome"] == t.OUT_INSTRUCTION
    assert t.outcome_group(rows[0]["DetectedOutcome"]) == "unclear"   # not a confirmed result


def test_assign_every_clean_row_reconciles_to_one_category():
    # Reconciliation: EVERY clean-signal row ends with exactly one known category
    # (win/loss/breakeven/missed/instruction/unclear) — nothing dropped.
    rows = [
        _row("clean signal", "XAUUSD", "XAUUSD buy 4016-4006 sl 3970 tp1 4022", "LONG", "4006-4016", "3970"),
        _row("commentary", "", "tp1 hit"),
        _row("clean signal", "EURUSD", "EURUSD sell 1.0850-1.0840 sl 1.0900", "SHORT", "1.0850-1.0840", "1.0900"),
        _row("commentary", "", "cut for -30 pips"),
        _row("clean signal", "GBPUSD", "GBPUSD buy 1.2700-1.2690 sl 1.2650", "LONG", "1.2700-1.2690", "1.2650"),
        _row("commentary", "", "sl hit"),
        _row("clean signal", "USDJPY", "USDJPY buy 156.00-155.80 sl 155.40", "LONG", "156.00-155.80", "155.40"),
        _row("commentary", "", "sl to entry, risk free"),
    ]
    t.assign_detected_outcomes(rows)
    clean = [r for r in rows if r["Classification"] == "clean signal"]
    known = {t.OUT_TARGET_HIT, t.OUT_MANAGED_PROFIT, t.OUT_PROFIT_RUNKNOWN,
             t.OUT_MANUAL_LOSS, t.OUT_STOP_LOSS, t.OUT_BREAKEVEN,
             t.OUT_MISSED, t.OUT_INSTRUCTION, t.OUT_UNCLEAR}
    # every clean row carries exactly one known category, and they reconcile:
    assert all(r["DetectedOutcome"] in known for r in clean)
    assert len([r for r in clean if r["DetectedOutcome"] in known]) == len(clean)
    groups = [t.outcome_group(r["DetectedOutcome"]) for r in clean]
    assert groups.count("win") == 1 and groups.count("loss") == 2
    assert groups.count("breakeven") == 1


# ----------------------------------------------------------------------------
# Accuracy improvements: catch more STATED wins; reject mismatches & generics
# ----------------------------------------------------------------------------
def test_catch_more_stated_wins_imperative_phrasing():
    # Real Farouk phrasings that were being MISSED (-> unclear/breakeven).
    for s in ("tp 1 now", "take tp 1", "take tp", "more tp", "small tp",
              "we got 90 pips sl entry", "securing tp 1", "take 75% sl to entry",
              "50 pips tp 1", "100 pips take tp 2", "official tp1", "tp 3"):
        assert t.detect_outcome_cue(s) == "win", s


def test_tp_level_listing_is_not_a_win():
    # Him POSTING the TP levels (not hitting them) must not read as a win.
    assert t.detect_outcome_cue("TP1 : 4,334   TP2 : 4,329   TP3 : 4,319") is None
    assert t.detect_outcome_cue("tp1 4022 tp2 4027 tp3 4040") is None


def test_assign_previously_unclear_tp2_reached_is_win():
    # A row that used to score "unclear" but the follow-up says "tp2 reached".
    rows = [
        _row("clean signal", "XAUUSD",
             "XAUUSD buy 4016-4006 sl 3970 tp1 4022 tp2 4027 tp3 4040",
             "LONG", "4006-4016", "3970"),
        _row("commentary", "", "hold best entry"),
        _row("commentary", "", "tp2 reached, banking it"),
    ]
    t.assign_detected_outcomes(rows)
    assert t.outcome_group(rows[0]["DetectedOutcome"]) == "win"
    assert "tp2" in rows[0]["OutcomeEvidence"].lower()


def test_assign_asset_mismatch_rejected():
    # A gold signal must NOT be matched to a BTC outcome message.
    rows = [
        _row("clean signal", "XAUUSD", "XAUUSD buy 4016 sl 3970", "LONG", "4016", "3970"),
        _row("commentary", "", "BTC tp1 hit, smashed it"),
    ]
    t.assign_detected_outcomes(rows)
    assert rows[0]["DetectedOutcome"] == "unclear"      # the BTC win isn't ours


def test_assign_generic_message_not_matched():
    # A hypothetical/educational message is NOT a confirmed result — its tp/pips
    # talk must never be read as a win. (It's in-context chatter -> instruction_only,
    # which rolls up to 'unclear', never to a win/loss.)
    rows = [
        _row("clean signal", "XAUUSD", "XAUUSD buy 4016 sl 3970", "LONG", "4016", "3970"),
        _row("commentary", "", "if price breaks 4020 you could see tp1 and +50 pips"),
    ]
    t.assign_detected_outcomes(rows)
    assert rows[0]["DetectedOutcome"] in (t.OUT_UNCLEAR, t.OUT_INSTRUCTION)
    assert t.outcome_group(rows[0]["DetectedOutcome"]) == "unclear"   # never a win


def test_assign_thread_consistency():
    # A no-asset "tp1 hit" in a DIFFERENT thread/section is not matched...
    rows = [
        _row("clean signal", "XAUUSD",
             "farouk Posted in gold-trades `Whale` XAUUSD buy 4016 sl 3970",
             "LONG", "4016", "3970"),
        _row("commentary", "", "kyle Posted in institutional-charts `Whale` tp1 hit"),
    ]
    t.assign_detected_outcomes(rows)
    assert rows[0]["DetectedOutcome"] == t.OUT_UNCLEAR
    # ...but the SAME thread is matched.
    rows = [
        _row("clean signal", "XAUUSD",
             "farouk Posted in gold-trades `Whale` XAUUSD buy 4016 sl 3970",
             "LONG", "4016", "3970"),
        _row("commentary", "", "farouk Posted in gold-trades `Whale` tp1 hit"),
    ]
    t.assign_detected_outcomes(rows)
    assert t.outcome_group(rows[0]["DetectedOutcome"]) == "win"


# ----------------------------------------------------------------------------
# Minimal runner (no pytest needed)
# ----------------------------------------------------------------------------
def _run():
    tests = [v for k, v in sorted(globals().items())
             if k.startswith("test_") and callable(v)]
    passed = failed = 0
    print("=" * 64)
    print("  OUTCOME-CUE DETECTION TESTS")
    print("=" * 64)
    for fn in tests:
        try:
            fn()
            print(f"  PASS  {fn.__name__}")
            passed += 1
        except AssertionError as e:
            print(f"  FAIL  {fn.__name__}: {e}")
            failed += 1
        except Exception as e:                       # noqa: BLE001
            print(f"  ERROR {fn.__name__}: {type(e).__name__}: {e}")
            failed += 1
    print("-" * 64)
    print(f"  {passed} passed, {failed} failed, {len(tests)} total")
    print("=" * 64)
    return failed == 0


if __name__ == "__main__":
    import sys
    sys.exit(0 if _run() else 1)
