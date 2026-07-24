"""Regressions for the red-team MATERIAL findings on the 07-14 retrospective-video analysis.

These are deterministic guards over the DURABLE analysis artifacts (transcript + review doc),
proving the over-read that the red-team caught cannot silently recur:
  RT-8.1: an HTF-bias claim must not be labeled CONTRADICTED solely from LTF 'look for longs'.
  RT-8.2: a reached-price argument must not refute 'HTF sell zones not reached' unless the price
          actually reaches the HTF zone (>= 4160); and no 'top-down' gold trace may be asserted
          when the transcript contains no HTF gold chart reference.
  Provenance: the review must classify the video RETROSPECTIVE_EXPLANATION and never backdate.
"""
from __future__ import annotations

import io
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
FP = os.path.dirname(os.path.dirname(HERE))          # farouk_plus
REVIEW = os.path.join(FP, "FP_CAMPAIGN_BREAKDOWN_20260714_REVIEW.md")
TXT = os.path.join(FP, "derived", "transcripts", "breakdown_20260714",
                   "FP-CAMPAIGN-BREAKDOWN-20260714_transcript.txt")
PASS = 0


def ok(c, name):
    global PASS
    assert c, f"FAIL: {name}"
    PASS += 1


review = open(REVIEW, encoding="utf-8").read()
transcript = open(TXT, encoding="utf-8").read().lower()

# --- provenance / firewall ---------------------------------------------------------------------
ok("RETROSPECTIVE_EXPLANATION" in review, "video classified RETROSPECTIVE_EXPLANATION")
ok("cannot create/backdate a blind hypothesis" in review.lower()
   or "cannot create" in review.lower(), "review states it cannot backdate a blind hypothesis")

# --- RT-8.1: no bare 'CONTRADICTED' on the HTF-bias row (must be softened) ----------------------
# find ambiguity #1 line
m1 = re.search(r'1\.\s*"bearish HTF directional bias".*', review)
ok(m1 is not None, "ambiguity #1 present")
line1 = m1.group(0)
ok("PARTLY_CONTRADICTED" in line1 and "does NOT logically refute" in line1
   or "does NOT logically refute an" in review, "RT-8.1: #1 softened to PARTLY_CONTRADICTED w/ reasoning")
ok("CONTRADICTED**" not in line1.replace("PARTLY_CONTRADICTED", ""),
   "RT-8.1: #1 not a bare CONTRADICTED verdict")

# --- RT-8.2: #6 must not use 4105 to refute un-reached 4160-4260 zones --------------------------
m6 = re.search(r'6\.\s*"Sunday HTF sell zones not reached.*', review)
ok(m6 is not None, "ambiguity #6 present")
line6 = m6.group(0)
ok("STILL_UNKNOWN" in line6, "RT-8.2: #6 downgraded to STILL_UNKNOWN")
ok("4160" in line6 and "4105" in line6, "RT-8.2: #6 explicitly notes 4105 < HTF sell zones 4160-4260")

# --- no HTF gold chart in the transcript -> no 'top-down' gold trace may be claimed as shown ----
ok("1 hour" in transcript or "1-hour" in transcript or "hour candle" in transcript,
   "transcript contains the '1-hour candle close' phrase (H1 spoken, not charted)")
ok("daily" not in transcript and "4 hour" not in transcript and "4h" not in transcript.replace("for our", ""),
   "transcript has NO daily/H4 gold reference (guards against invented top-down tiers)")
ok("no HTF gold chart" in review or "no HTF gold chart" in review.replace("**", ""),
   "review states there is NO HTF gold chart (Tasks 6-7 5m-only)")

# --- gold bias is LONG and stated; F002 not mentioned ------------------------------------------
ok("look for longs" in transcript, "transcript: gold bias 'look for longs' is real")
ok("sell 4084" not in transcript and "short" not in transcript, "F002 short genuinely unmentioned in video")

# --- no invented numeric gold rule / engine delta ----------------------------------------------
ok("NONE justified" in review, "engine delta = NONE justified (fail closed)")
ok("OBSERVED_ONCE" in review and "not a live rule" in review,
   "any new rule is OBSERVED_ONCE, not promoted to live")

if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    print(f"PASS {PASS} retro-video-guard checks")
