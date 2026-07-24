# MIS-CUT CLIPS - DO NOT USE FOR OPERATOR-EAR VERIFICATION (2026-07-22)

Martyn's ear + a citation spot-check found these two v2 clips contain the WRONG rule's content
(a transcript-timestamp -> real-audio DRIFT in the clip-cutting pipeline, not a bad transcript):

- **FR-076_ear_v2.mp3** -> contains FR-056 pip-target content ("200/100 pips, scalps, small moves"),
  NOT the instrument-focus rule. UNCONFIRMED. Do not use.
- **FR-063_ear_v2.mp3** -> contains the K-066 statistical claim ("22-year data, 80%/78% chance"),
  NOT the react-don't-predict / play-the-probabilities-with-a-checklist doctrine. UNCONFIRMED. Do not use.

FR-076_ear_v3.mp3 was NOT written: a verified re-cut from gmt20251221 failed the same way (the audio
at the cited transcript position is unrelated content). Transcript-timestamp -> real-audio mapping is
UNRELIABLE for these sources; audio operator-ear verification is ON HOLD until it is fixed.

The underlying TRANSCRIPT citations are sound (spot-check: 10/10 quotes present in-transcript); the
defect is the audio clip-cutting alignment. See brain D-103.

## FIXED 2026-07-22 (D-104): use the v3 clips, not v2
Root cause: clips were cut with INPUT seek (-ss/-to BEFORE -i) on MP4 -> keyframe-imprecise ->
off-position. FIX: accurate OUTPUT seek (-i then -ss/-t) + closed-loop ASR verify (recut_verified.py).
- **FR-076_ear_v3.mp3** (sunday_12 ~00:31:50) - ASR-verified: "Silver is also good... but I'm doing
  gold, personally" (gold-primary). LISTEN: gold as primary/personal, BTC only conditional/secondary.
- **FR-063_ear_v3.mp3** (friday_3 ~00:40:40) - ASR-verified: "playing the probabilities and having a
  checklist". LISTEN: react-don't-predict / play-the-probabilities-with-a-checklist doctrine.
The v2 clips remain DO-NOT-USE.
