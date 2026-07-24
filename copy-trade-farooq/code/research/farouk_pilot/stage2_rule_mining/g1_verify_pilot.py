"""G1 AUDIO VERIFICATION — PILOT RUN (D-043/D-049; method registered in register_builder).
Machine-corroboration leg: re-transcribe the cited segment with medium.en (larger than the
batch small.en) and compare the critical token. Disagreement/inaudible -> stays pending.
Run under .venv-vision python."""
import json
import os

from faster_whisper import WhisperModel

CORPUS = r"C:\Users\Marty\signal-terminal\research\farouk_pilot\corpus"
SEGS = [
    # (label, stored_path, start_s, end_s, question)
    ("ORB-definition-1", r"store\c5\c5508175ec0d635b__GMT20251221-181518_Recording (1).m4a",
     3648, 3700, "ORB window: '50 minutes' vs 15 minutes (context: London 9:00-9:15)"),
    ("ORB-definition-2", r"store\c5\c5508175ec0d635b__GMT20251221-181518_Recording (1).m4a",
     5300, 5330, "'works really good on the 50 minutes' vs 15"),
    ("close-stack-sun", r"store\43\4328a875cb55d147__Live with Farouk, Sunday, 5 July 2026.mp4",
     478, 510, "'50 minute candle close' in the 5m/15m/1h stack"),
    ("close-stack-fri", r"store\94\944789f92a8092cc__Live with Farouk, Friday, 3 July 2026.mp4",
     1470, 1500, "'50 minutes candle close' three-confirmation list"),
    ("choch-timeframe", r"store\43\4328a875cb55d147__Live with Farouk, Sunday, 5 July 2026.mp4",
     685, 710, "CHoCH 'under three and one minutes' - which timeframes?"),
    ("range-mgmt-pips", r"store\94\944789f92a8092cc__Live with Farouk, Friday, 3 July 2026.mp4",
     4165, 4185, "'50, 160, 60, 70 pips' digit garble"),
    ("sizing-negation", r"store\43\4328a875cb55d147__Live with Farouk, Sunday, 5 July 2026.mp4",
     7530, 7560, "'$1,000 account, do more than that' - is it 'do NO more'?"),
]

model = WhisperModel("medium.en", device="cpu", compute_type="int8")
out = []
for label, rel, start, end, q in SEGS:
    path = os.path.join(CORPUS, rel)
    if not os.path.exists(path):
        out.append({"label": label, "error": "MEDIA_MISSING", "path": rel})
        print(f"== {label}: MEDIA_MISSING {rel}")
        continue
    try:
        segments, _ = model.transcribe(path, beam_size=5, vad_filter=False,
                                       clip_timestamps=f"{start},{end}")
        text = " ".join(s.text.strip() for s in segments)
    except TypeError:
        segments, _ = model.transcribe(path, beam_size=5)
        text = " ".join(s.text.strip() for s in segments if start - 2 <= s.start <= end + 2)
    out.append({"label": label, "window_s": [start, end], "question": q, "medium_en": text})
    print(f"== {label} [{start}-{end}s] Q: {q}")
    print(f"   medium.en: {text}")
json.dump(out, open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                 "g1_pilot_raw_v0_1.json"), "w", encoding="utf-8"), indent=1)
print("done")
