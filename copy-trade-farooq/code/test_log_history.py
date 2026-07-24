"""
test_log_history.py — a WIN is scored at its real, STATED R (no +1R flat).

Covers the refinement: a "win to tp1 that then scratched" logs at the R from
entry to TP1 (small), a full win (all TP) keeps its full R, and where the stated
info can't yield an R it's marked for manual entry — never an assumed partial or
guessed price.

Deterministic, no API, read-only. Run:  python test_log_history.py
"""

from decimal import Decimal

import config
import module_c_risk as risk
import log_history as lh


def _gold_ticket():
    """A real LONG gold trade with TP1/TP2/TP3, sized through the engine."""
    row = {"Asset": "XAUUSD", "Direction": "LONG", "Entry": "4006-4016",
           "Stop": "3970", "TP1": "4022", "TP2": "4027", "TP3": "4040",
           "RawMessage": "XAUUSD buy 4016-4006 sl 3970 tp1 4022 tp2 4027 tp3 4040",
           "Sender": "farouk"}
    sig, _ = lh.build_signal(row)
    ticket = risk.size_signal(sig, Decimal(config.POT_SIZE))
    return sig, ticket


def _invalid_stop_long():
    """A LONG whose stop (4318) sits ABOVE entry (4231-4241) — an invalid stop."""
    from models import Signal
    return Signal(ticker="XAUUSD", pair="XAUUSD", direction="LONG", asset_class="METAL",
                  entry_low=Decimal("4231"), entry_high=Decimal("4241"),
                  stop_loss=Decimal("4318"), targets=[],
                  raw_text="XAUUSD buy 4241-4231 sl 4318", source="farouk")


# ----------------------------------------------------------------------------
# _target_from_evidence
# ----------------------------------------------------------------------------
def test_target_from_evidence():
    assert lh._target_from_evidence("tp1 hit") == 1
    assert lh._target_from_evidence("Tp 2 hit") == 2
    assert lh._target_from_evidence("tp1 hit then tp2 hit") == 2     # highest stated
    assert lh._target_from_evidence("all TP hit 500 pips") == "all"
    assert lh._target_from_evidence("all targets hit") == "all"
    assert lh._target_from_evidence("+50 pips") is None
    assert lh._target_from_evidence("took profit at 2350") is None


# ----------------------------------------------------------------------------
# _resolve_win_rr — auto-resolution from stated targets (no prompt needed)
# ----------------------------------------------------------------------------
def test_win_to_tp1_scores_R_to_tp1_not_flat():
    sig, ticket = _gold_ticket()
    rr, label = lh._resolve_win_rr(sig, ticket, {"OutcomeEvidence": "tp1 hit"})
    assert label == "TP1"
    assert rr == ticket.rr_targets[0].quantize(Decimal("0.01"))
    assert rr < Decimal("1")            # a small partial win, NOT +1R flat


def test_win_highest_stated_tp_used():
    sig, ticket = _gold_ticket()
    rr, label = lh._resolve_win_rr(sig, ticket, {"OutcomeEvidence": "tp1 hit, then tp2 hit"})
    assert label == "TP2"
    assert rr == ticket.rr_targets[1].quantize(Decimal("0.01"))


def test_full_win_keeps_full_R():
    sig, ticket = _gold_ticket()
    rr, label = lh._resolve_win_rr(sig, ticket, {"OutcomeEvidence": "all TP hit 500 pips"})
    assert label == "all targets"
    assert rr == ticket.rr_targets[-1].quantize(Decimal("0.01"))
    # full R is larger than the TP1 partial
    assert rr > ticket.rr_targets[0].quantize(Decimal("0.01"))


def test_stated_pips_now_scored_not_marked_manual():
    # NEW (P2): stated pips are no longer ambiguous — "+50 pips banked" is a
    # managed profit scored to a real R (capped at the furthest target), NOT punted
    # to manual and NOT zero.
    sig, ticket = _gold_ticket()
    rr, label = lh._resolve_win_rr(sig, ticket, {"OutcomeEvidence": "+50 pips banked"})
    furthest = ticket.rr_targets[-1].quantize(Decimal("0.01"))
    assert rr is not None and rr > Decimal("0")
    assert rr <= furthest                        # never over-credits past the targets


def test_out_of_range_named_target_scores_zero_R():
    # A named target with no price in the signal AND no pips -> no reconstructable
    # quantity -> 0R (confirmed win, never guessed).
    sig, ticket = _gold_ticket()                 # has TP1/2/3 only
    rr, label = lh._resolve_win_rr(sig, ticket, {"OutcomeEvidence": "tp5 hit"})
    assert rr == Decimal("0.00") and "unknown" in label.lower()


def test_named_tp_without_price_or_pips_scores_zero_R():
    # Signal has NO take-profit prices and the follow-up ("tp1 hit") states no pips
    # -> genuinely no reconstructable quantity -> 0R (a confirmed win, not guessed).
    row = {"Asset": "XAUUSD", "Direction": "LONG", "Entry": "4006-4016",
           "Stop": "3970", "TP1": "", "TP2": "", "TP3": "",
           "RawMessage": "XAUUSD buy 4016-4006 sl 3970", "Sender": "farouk"}
    sig, _ = lh.build_signal(row)
    ticket = risk.size_signal(sig, Decimal(config.POT_SIZE), require_targets=False)
    rr, label = lh._resolve_win_rr(sig, ticket, {"OutcomeEvidence": "tp1 hit"})
    assert rr == Decimal("0.00") and "unknown" in label.lower()


def test_named_tp_without_price_but_with_pips_uses_pips():
    # No TP price in the signal, but the follow-up states pips -> credit the pips R
    # (the audit's "named target with no reconstructable price -> fall back to pips").
    row = {"Asset": "XAUUSD", "Direction": "SHORT", "Entry": "4138-4155",
           "Stop": "4180", "TP1": "", "TP2": "", "TP3": "",
           "RawMessage": "XAUUSD sell 4138-4155 sl 4180", "Sender": "farouk"}
    sig, _ = lh.build_signal(row)
    ticket = risk.size_signal(sig, Decimal(config.POT_SIZE), require_targets=False)
    rr, label = lh._resolve_win_rr(sig, ticket, {"OutcomeEvidence": "take tp 3 170 pips"})
    risk_pts = Decimal(str(ticket.sl_dollar))
    move = Decimal(str(170 * 0.1))               # gold pips are $0.10 points
    assert rr == (move / risk_pts).quantize(Decimal("0.01"))
    assert "170" in label


# ----------------------------------------------------------------------------
# HONESTY FIX P2 — a WIN with no reconstructable exit is 0R, NOT an assumed TP1
# ----------------------------------------------------------------------------
def test_r_unknown_win_scores_zero_R_not_tp1():
    # "almost reached tp1" — money side unknown / target NOT reached -> 0R.
    sig, ticket = _gold_ticket()
    rr, label = lh._resolve_win_rr(sig, ticket, {"OutcomeEvidence": "almost reached tp1"})
    assert rr == Decimal("0.00")                 # 0R, NOT the TP1 partial R
    assert rr != ticket.rr_targets[0].quantize(Decimal("0.01"))
    assert "unknown" in label.lower()


def test_closed_in_profit_scores_zero_R():
    # "best layer closed in profit" — a confirmed win but no exit -> 0R.
    sig, ticket = _gold_ticket()
    rr, label = lh._resolve_win_rr(sig, ticket, {"OutcomeEvidence": "best layer closed in profit"})
    assert rr == Decimal("0.00")
    assert "unknown" in label.lower()


def test_invalid_stop_win_scores_zero_R():
    # A win on a trade whose stop is on the wrong side of entry -> 0R (R is
    # meaningless), even though the evidence names a target.
    sig = _invalid_stop_long()
    _, ticket = _gold_ticket()                   # any ticket with rr/sl_dollar
    assert lh._stop_is_valid(sig) is False
    rr, label = lh._resolve_win_rr(sig, ticket, {"OutcomeEvidence": "tp 1 hit"})
    assert rr == Decimal("0.00") and "invalid stop" in label.lower()


def test_exit_price_reached_scores_R_from_price():
    # A stated exit PRICE reached ("reached 4050") with no TP price/pips -> R from
    # that price vs the trade's risk.
    sig, ticket = _gold_ticket()                 # LONG 4006-4016, sl 3970
    rr, label = lh._resolve_win_rr(sig, ticket, {"OutcomeEvidence": "we reached 4050"})
    risk_pts = Decimal(str(ticket.sl_dollar))
    expected = ((Decimal("4050") - Decimal("4016")) / risk_pts).quantize(Decimal("0.01"))
    assert rr == expected and "4050" in label


def test_managed_profit_pips_scores_R_from_stated_pips():
    # Stated pips with NO named target -> R = pips / risk (|entry-stop|).
    # Use a no-target signal so there's no furthest-target cap in play.
    row = {"Asset": "XAUUSD", "Direction": "SHORT", "Entry": "4138-4155",
           "Stop": "4180", "TP1": "", "TP2": "", "TP3": "",
           "RawMessage": "XAUUSD sell 4138-4155 sl 4180", "Sender": "farouk"}
    sig, _ = lh.build_signal(row)
    ticket = risk.size_signal(sig, Decimal(config.POT_SIZE), require_targets=False)
    rr, label = lh._resolve_win_rr(sig, ticket, {"OutcomeEvidence": "we got 90 pips"})
    risk_pts = Decimal(str(ticket.sl_dollar))
    move = Decimal(str(90 * 0.1))                 # gold pips are $0.10 points
    assert rr == (move / risk_pts).quantize(Decimal("0.01"))
    assert "90" in label


def test_pips_smaller_than_target_scores_to_pips_not_distant_target():
    # PRINCIPLE: when stated pips (no explicit hit) are SMALLER than the named
    # target's R, score to the pips — don't over-credit the distant target.
    # Gold LONG 4090-4103, single target 4190 (distant); confirmed "70 pips".
    row = {"Asset": "XAUUSD", "Direction": "LONG", "Entry": "4090-4103",
           "Stop": "4080", "TP1": "4190", "TP2": "", "TP3": "",
           "RawMessage": "XAUUSD buy 4103-4090 sl 4080 tp1 4190", "Sender": "farouk"}
    sig, _ = lh.build_signal(row)
    ticket = risk.size_signal(sig, Decimal(config.POT_SIZE), require_targets=False)
    risk_pts = Decimal(str(ticket.sl_dollar))
    r_target = ticket.rr_targets[0].quantize(Decimal("0.01"))
    r_pips = (Decimal(str(70 * 0.1)) / risk_pts).quantize(Decimal("0.01"))   # gold $0.10 pips
    assert r_pips < r_target                              # pips fall short of the target
    rr, label = lh._resolve_win_rr(sig, ticket, {"OutcomeEvidence": "tp 1 we have 70 pips"})
    assert rr == r_pips and "70" in label                # scored to the confirmed pips


def test_explicit_hit_scores_full_target_even_with_smaller_pips():
    # An explicit HIT gets the full target R, not downgraded to a stray pip figure.
    sig, ticket = _gold_ticket()                         # tp1 4022
    rr, label = lh._resolve_win_rr(sig, ticket, {"OutcomeEvidence": "tp1 hit"})
    assert rr == ticket.rr_targets[0].quantize(Decimal("0.01"))
    assert "TP1" in label


def test_pip_R_is_capped_at_furthest_target():
    # Don't over-credit: a hyped pip figure (here 500 "pips" on a gold trade whose
    # furthest target is ~24 points away) is CAPPED at the furthest target's R, so
    # it can never exceed what the posted targets allow.
    sig, ticket = _gold_ticket()                 # tp3 4040, entry 4006-4016, sl 3970
    furthest = ticket.rr_targets[-1].quantize(Decimal("0.01"))
    risk_pts = Decimal(str(ticket.sl_dollar))
    assert (Decimal("500") / risk_pts) > furthest        # uncapped would over-credit
    rr, label = lh._resolve_win_rr(sig, ticket, {"OutcomeEvidence": "500 pips close more"})
    assert rr == furthest and "capped" in label.lower()


# ----------------------------------------------------------------------------
# HONESTY FIX P1 — a MANUAL loss is scored at its ACTUAL stated size, never -1R
# flat, never zero, never dropped. The original stop is -1R.
# ----------------------------------------------------------------------------
def test_manual_loss_scores_actual_stated_R():
    # "cut for -40 pips" -> -(40)/risk, NOT a flat -1R.
    sig, ticket = _gold_ticket()
    rr, label = lh._resolve_loss_rr(ticket, {"OutcomeEvidence": "cut for -40 pips"})
    risk_pts = Decimal(str(ticket.sl_dollar))
    move = Decimal(str(40 * 0.1))                 # gold pips are $0.10 points
    assert rr == (-(move) / risk_pts).quantize(Decimal("0.01"))
    assert rr < Decimal("0") and rr != Decimal("-1")     # a real, smaller loss
    assert "40" in label


def test_original_stop_loss_scores_minus_one_R():
    # The original stop being hit (no stated size) -> -1R.
    sig, ticket = _gold_ticket()
    rr, label = lh._resolve_loss_rr(ticket, {"OutcomeEvidence": "sl hit"})
    assert rr == Decimal("-1")
    assert "stop" in label.lower()


def test_manual_loss_with_stated_pips_is_negative_R():
    # A manual loss with a STATED size is a real negative R.
    sig, ticket = _gold_ticket()
    for ev in ("stopped for -25 pips", "cut the trade -50 pips"):
        rr, _ = lh._resolve_loss_rr(ticket, {"OutcomeEvidence": ev})
        assert rr is not None and rr < Decimal("0"), ev


def test_manual_loss_unknown_magnitude_awaits_manual_not_dropped():
    # A manual loss whose magnitude can't be stated ("closed for a loss", "count it
    # as a loss overall", "1 win, 1 loss") -> None (negative, enter R manually) —
    # still a loss, NEVER zero, NEVER a silent -1R, NEVER dropped.
    sig, ticket = _gold_ticket()
    for ev in ("closed for a loss", "I'll count it as a loss overall",
               "better to close it for a small loss; 1 win, 1 loss today"):
        rr, label = lh._resolve_loss_rr(ticket, {"OutcomeEvidence": ev})
        assert rr is None, ev
        assert "manual" in label.lower() and "unknown" in label.lower(), ev


def test_apply_choice_unknown_magnitude_loss_logged_as_loss():
    # The unknown-magnitude manual loss is still written as a LOSS (awaiting -R),
    # not skipped and not silently -1R (no tps_hit=SL).
    sig, _ = _gold_ticket()
    row = _blank_row()
    lh.apply_choice(row, "loss", sig, "2026-06-19T13:06:00+00:00",
                    loss_rr=None, loss_label="manual loss, magnitude unknown -> enter R")
    assert row["outcome"] == "LOSS"
    assert row["realised_rr"] == ""             # not fabricated
    assert row["tps_hit"] != "SL"              # not the -1R original-stop path
    assert "MANUAL" in row["notes"].upper()


# ----------------------------------------------------------------------------
# apply_choice — writes the computed R (or leaves awaiting for manual)
# ----------------------------------------------------------------------------
def _blank_row():
    import module_d_logger as logger
    return {k: "" for k in logger.FIELDNAMES}


def test_apply_choice_win_writes_real_r():
    sig, _ = _gold_ticket()
    row = _blank_row()
    lh.apply_choice(row, "win", sig, "2026-06-25T14:42:00+00:00",
                    win_rr=Decimal("0.12"), win_label="TP1")
    assert row["outcome"] == "WIN"
    assert row["realised_rr"] == "0.12"          # NOT "1"
    assert "TP1" in row["notes"]


def test_apply_choice_win_manual_left_awaiting():
    sig, _ = _gold_ticket()
    row = _blank_row()
    lh.apply_choice(row, "win", sig, "2026-06-25T14:42:00+00:00",
                    win_rr=None, win_label="manual")
    assert row["outcome"] == ""                  # awaiting, not scored/guessed
    assert "MANUAL" in row["notes"].upper()
    assert row["realised_rr"] == ""              # no fabricated R


def test_apply_choice_manual_loss_writes_real_negative_r():
    # A manual loss writes its ACTUAL -R into realised_rr (not the -1R stop path).
    sig, _ = _gold_ticket()
    row = _blank_row()
    lh.apply_choice(row, "loss", sig, "2026-06-25T14:42:00+00:00",
                    loss_rr=Decimal("-0.30"), loss_label="-40 pips")
    assert row["outcome"] == "LOSS"
    assert row["realised_rr"] == "-0.30"         # the stated size, not -1R
    assert row["tps_hit"] != "SL"               # not routed through the -1R stop path
    assert "40 pips" in row["notes"]


def test_apply_choice_original_stop_loss_is_minus_one_r():
    # The original stop (-1R) routes through tps_hit=SL (review -> -1R), no realised_rr.
    sig, _ = _gold_ticket()
    row = _blank_row()
    lh.apply_choice(row, "loss", sig, "2026-06-25T14:42:00+00:00",
                    loss_rr=Decimal("-1"), loss_label="original stop / full loss")
    assert row["outcome"] == "LOSS"
    assert row["tps_hit"] == "SL"
    assert row["realised_rr"] == ""             # -1R derived at review, not fabricated


# ----------------------------------------------------------------------------
# Minimal runner (no pytest needed)
# ----------------------------------------------------------------------------
def _run():
    tests = [v for k, v in sorted(globals().items())
             if k.startswith("test_") and callable(v)]
    passed = failed = 0
    print("=" * 64)
    print("  LOG-HISTORY WIN-SCORING TESTS")
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
