"""G1 AUDIO VERIFICATION — FAST PATH (registered method, D-042/D-016: ffmpeg-extract the
segment with a +/-10s pad FIRST, then transcribe the clip). Seconds per segment instead of
a full-file decode. Run under .venv-vision python:
  .venv-vision\\Scripts\\python.exe g1_verify_fast.py segments.json
segments.json = [{"label","stored_path","start_s","end_s","question"}, ...]
Output: g1_fast_results_<basename>.json alongside the input.
"""
import json
import os
import subprocess
import sys
import tempfile

import imageio_ffmpeg
from faster_whisper import WhisperModel

CORPUS = r"C:\Users\Marty\signal-terminal\research\farouk_pilot\corpus"
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
PAD = 10


def clip(src, start, end, dst):
    a = max(0, start - PAD)
    subprocess.run([FFMPEG, "-y", "-loglevel", "error", "-ss", str(a),
                    "-i", src, "-t", str(end - a + PAD), "-vn",
                    "-ac", "1", "-ar", "16000", dst], check=True, timeout=120)


def main():
    segs = json.load(open(sys.argv[1], encoding="utf-8"))
    model = WhisperModel("medium.en", device="cpu", compute_type="int8")
    out, tmp = [], tempfile.mkdtemp(prefix="g1_clips_")
    for s in segs:
        src = os.path.join(CORPUS, s["stored_path"])
        row = dict(s)
        if not os.path.exists(src):
            row["error"] = "MEDIA_MISSING"
        else:
            wav = os.path.join(tmp, s["label"] + ".wav")
            try:
                clip(src, s["start_s"], s["end_s"], wav)
                segments, _ = model.transcribe(wav, beam_size=5)
                row["medium_en"] = " ".join(x.text.strip() for x in segments)
            except Exception as e:                                # noqa: BLE001
                row["error"] = f"{type(e).__name__}: {e}"[:120]
        out.append(row)
        print(f"== {row['label']}: {row.get('medium_en', row.get('error'))[:160]}")
    dst = os.path.join(os.path.dirname(os.path.abspath(sys.argv[1])),
                       "g1_fast_results_" + os.path.basename(sys.argv[1]))
    json.dump(out, open(dst, "w", encoding="utf-8"), indent=1)
    print("wrote", dst)


if __name__ == "__main__":
    main()
