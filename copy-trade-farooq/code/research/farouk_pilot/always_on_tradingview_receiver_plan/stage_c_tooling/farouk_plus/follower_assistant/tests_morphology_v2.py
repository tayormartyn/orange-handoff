"""MORPHOLOGY_EXTENSION_v2 tests (D-020). Written FAILING-FIRST against the current
interpreter, then must pass against interpreter_v2. Run:
  python tests_morphology_v2.py           -> tests interpreter_v2 (target GREEN)
  python tests_morphology_v2.py --v1      -> tests live interpreter (expected RED pre-fix)
"""
import sys

USE_V1 = "--v1" in sys.argv
if USE_V1:
    import interpreter as I
else:
    import interpreter_v2 as I

H = "seascalperfarouk Posted in 🪙・gold-trades\n\n"
checks = []


def ck(name, cond, detail=""):
    checks.append((name, bool(cond), detail))


def kinds(text):
    return I.classify(H + text)


def itypes(c):
    return [i["instruction_type"] for i in c.get("instructions", [])]


# ---- HARD ASSERTION (operator condition B1): entry NEVER read as stop-move ----
c = kinds("`Whale` gold long sl 5090 high risk trade\n\nTp zone 5120-5125-5130-5135-5140")
ck("HARD: 'gold long sl 5090' is ENTRY", c["kind"] == "ENTRY", c)
ck("HARD: never MANAGEMENT/REVISED_STOP", c["kind"] != "MANAGEMENT")
if c["kind"] == "ENTRY":
    ck("HARD: no zone synthesised (tp-zone numbers NOT stolen)",
       c.get("zone_low") is None and c.get("zone_high") is None, c)
    ck("HARD: flagged AT_MARKET_UNPRICED", c.get("entry_pricing") == "AT_MARKET_UNPRICED")
    ck("HARD: direction LONG", c.get("direction") == "LONG")
    ck("HARD: sl preserved 5090", c.get("sl") == "5090")

# ---- A1 single-price entry family ----
c = kinds("`Whale` XAUUSD SELL 4635\n\nSL @ 4670")
ck("A1: 'XAUUSD SELL 4635 / SL @ 4670' ENTRY", c["kind"] == "ENTRY", c)
if c["kind"] == "ENTRY":
    ck("A1: degenerate zone = price", c.get("zone_low") == "4635" and c.get("zone_high") == "4635")
    ck("A1: SHORT + sl 4670", c.get("direction") == "SHORT" and c.get("sl") == "4670")
    ck("A1: pricing SINGLE_PRICE", c.get("entry_pricing") == "SINGLE_PRICE")

c = kinds("`Whale` High-risk short on gold. (farouk entry 4740.2)\nStop loss at 4762\nUse a small position size.")
ck("A1: 'entry 4740.2 / Stop loss at 4762' ENTRY", c["kind"] == "ENTRY", c)
if c["kind"] == "ENTRY":
    ck("A1: price 4740.2 sl 4762 SHORT", c.get("zone_low") == "4740.2" and c.get("sl") == "4762"
       and c.get("direction") == "SHORT")

c = kinds("`Whale` Gold buy sl 4710 take tp every 30 pips\n\nEntry 4732")
ck("A1: separate Entry-line form ENTRY", c["kind"] == "ENTRY", c)
if c["kind"] == "ENTRY":
    ck("A1: 4732/4710 LONG", c.get("zone_low") == "4732" and c.get("sl") == "4710"
       and c.get("direction") == "LONG")

c = kinds("`Whale` I opened a 0.1 long position on gold.\nIt's Monday, and I'll open another long later today.\nStop loss: 4060")
ck("A1: first-person position ENTRY", c["kind"] == "ENTRY", c)
if c["kind"] == "ENTRY":
    ck("A1: AT_MARKET_UNPRICED (no entry price given)", c.get("entry_pricing") == "AT_MARKET_UNPRICED")
    ck("A1: no sizing derived", "0.1" not in str(c.get("zone_low")) and c.get("no_sizing_note"))

c = kinds("`Whale` gold long 5015 sl")
ck("A1: trailing bare 'sl' (no stop price) stays fail-closed review", c["kind"] == "NEEDS_HUMAN_REVIEW", c)

# stop-side sanity on priced single-price entries
c = kinds("`Whale` XAUUSD BUY 4635\n\nSL @ 4670")
ck("A1: LONG with stop ABOVE price fails closed", c["kind"] == "NEEDS_HUMAN_REVIEW", c)

# ---- A2 SL-variant family ----
c = kinds("`Whale` Tp 4 hit stop loss to entry")
ck("A2: 'stop loss to entry' -> SL_TO_ENTRY", "SL_TO_ENTRY" in itypes(c), c)
c = kinds("`Whale` Move stoploss to entry")
ck("A2: one-word 'stoploss to entry'", "SL_TO_ENTRY" in itypes(c), c)
c = kinds("`Whale` we keep selling today (MOVE SL ENTRY)")
ck("A2: 'sl entry' (no to/at) -> SL_TO_ENTRY not entry", c["kind"] == "MANAGEMENT" and "SL_TO_ENTRY" in itypes(c), c)
c = kinds("`Whale` tp 4 hit move sl to enty")
ck("A2: typo 'enty' -> SL_TO_ENTRY", "SL_TO_ENTRY" in itypes(c), c)
c = kinds("`Whale` At 4497, you can move your stop loss to entry. Put your stop loss now at 4465")
ck("A2: 'stop loss now at 4465' recognized", c["kind"] == "MANAGEMENT"
   and ("REVISED_STOP" in itypes(c) or "SL_TO_ENTRY" in itypes(c)), c)
c = kinds("`Whale` last tp hit set stoploss at 3985 please")
ck("A2: 'set stoploss at 3985' -> REVISED_STOP 3985", "REVISED_STOP" in itypes(c), c)
c = kinds("`Whale` Set your stop-loss at 4040 please")
ck("A2: 'set your stop-loss at 4040' -> REVISED_STOP", "REVISED_STOP" in itypes(c), c)
c = kinds("`Whale` MAKET CLOSE in 3 min guys!!!!! take 90% sl entry!!!")
ck("A2: 'take 90% sl entry' -> TAKE_PCT + SL_TO_ENTRY", "SL_TO_ENTRY" in itypes(c)
   and "TAKE_PCT_OFF" in itypes(c), c)

# ---- B3: pips/result cards still never terminal, mgmt never becomes entry ----
for txt in ("we made 700 pips on this one!", "140-150 pips locked in so far",
            "0.5 lots banked +250 pips, screenshot attached"):
    c = kinds("`Whale` " + txt)
    ck(f"B3: '{txt[:24]}' never ENTRY/terminal",
       c["kind"] != "ENTRY" and not any(t in ("EXPLICIT_FULL_EXIT", "FINAL_CLOSE") for t in itypes(c)), c)

# ---- follow-ups (operator, post-acceptance): degenerate flag + comma prices ----
c = kinds("`Whale` XAUUSD SELL 4635\n\nSL @ 4670")
ck("F1: single-price entry carries zone_degenerate flag", c.get("zone_degenerate") is True, c)
c = kinds("`Whale` XAUUSD BUY 4010-4000 SL 3992")
ck("F1: normal zone entry has NO degenerate flag", "zone_degenerate" not in c, c)
c = kinds("`Whale` Direction : long Entry Price : 4,915\nStop loss at 4,890 gold")
ck("F2: comma prices '4,915'/'4,890' parse as ENTRY", c["kind"] == "ENTRY", c)
if c["kind"] == "ENTRY":
    ck("F2: comma normalised 4915/4890 LONG", c.get("zone_low") == "4915" and c.get("sl") == "4890"
       and c.get("direction") == "LONG", c)
c = kinds("`Whale` set stoploss at 4,940 please")
ck("F2: comma price in SL variant -> REVISED_STOP 4940",
   any(i["instruction_type"] == "REVISED_STOP" and i.get("new_sl") == "4940" for i in c.get("instructions", [])), c)

# ---- EXTENDED v2.1 (D-028 defects; failing-first) --------------------------------
c = kinds("`Whale` tp 1 sl entry")
ck("X1: 'tp 1 sl entry' parses BOTH clauses (TP1 + SL_TO_ENTRY)",
   c["kind"] == "MANAGEMENT" and "TP1_TAKE" in itypes(c) and "SL_TO_ENTRY" in itypes(c), c)
c = kinds("`Whale` Hold the lowest entry. If we go higher, the next TP is 4032.")
ck("X2: hold-lowest is a typed leg-selective instruction (not commentary)",
   c["kind"] == "MANAGEMENT" and "HOLD_LEG_SELECTIVE" in itypes(c), c)
if c["kind"] == "MANAGEMENT":
    sel = [i for i in c["instructions"] if i["instruction_type"] == "HOLD_LEG_SELECTIVE"]
    ck("X2: selector LOWEST", sel and sel[0].get("selector") == "LOWEST", sel)
    notes = [i for i in c["instructions"] if i.get("informational")]
    ck("X2: TP 4032 captured as informational note (never an engine instruction)",
       any(i.get("instruction_type") == "TP_LEVEL_NOTE" and str(i.get("level")) == "4032" for i in notes), c)
# per-clause completeness: residual indicative token with no matching instruction fails the WHOLE message
c = kinds("`Whale` tp 1 now, then trail your stop tightly into the close")
ck("X3: residual un-typed 'stop' clause fails the ENTIRE message closed",
   c["kind"] == "NEEDS_HUMAN_REVIEW", c)
c = kinds("`Whale` close worst hold best entry and cancel the leftover order thing")
ck("X3b: cancel clause typed alongside close/hold (fully covered -> MANAGEMENT)",
   c["kind"] == "MANAGEMENT" and "CANCEL" in itypes(c), c)
c = kinds("`Whale` Tp 4 hit stop loss to entry")
ck("X4: 'tp 4 hit' covered as informational TP_HIT_NOTE + SL_TO_ENTRY actionable",
   c["kind"] == "MANAGEMENT" and "SL_TO_ENTRY" in itypes(c)
   and any(i.get("instruction_type") == "TP_HIT_NOTE" for i in c.get("instructions", [])), c)
# 45719 phantom guard must survive the compound extension
c = kinds("`Whale` I'm still in. If your SL entry got hit, I'll send another trade in a bit.")
ck("X5: retrospective 'SL entry got hit' still NOT an instruction (45719 guard)",
   "SL_TO_ENTRY" not in itypes(c), c)

# current-era zone entry unchanged
c = kinds("`Whale` XAUUSD BUY 4010-4000 SL 3992 Use a small size on this trade.")
ck("current era: F006 form still ENTRY LONG 4000-4010/3992",
   c["kind"] == "ENTRY" and c.get("zone_low") == "4000" and c.get("zone_high") == "4010"
   and c.get("sl") == "3992" and c.get("direction") == "LONG", c)

fails = [(n, d) for n, ok_, d in checks if not ok_]
for n, ok_, d in checks:
    print(("PASS " if ok_ else "FAIL ") + n + ("" if ok_ else f"  <- {d}"))
print(f"\n{'V1(expect RED)' if USE_V1 else 'V2'}: {len(checks) - len(fails)}/{len(checks)} pass")
sys.exit(0 if not fails else 1)
