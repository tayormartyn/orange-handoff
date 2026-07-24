"""K-056 re-cut: locate the ACTUAL tokens for FR-076 (instrument-focus) and FR-063
(react-don't-predict) in friday_3 by REAL audio (no VAD), correcting VAD drift, then
cut tight operator-ear clips. Read-only toward everything else."""
import json, os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
FF = os.path.join(ROOT, ".venv-vision", "Lib", "site-packages", "imageio_ffmpeg",
                  "binaries", "ffmpeg-win-x86_64-v7.1.exe")
MEDIA = os.path.join(HERE, "..", "corpus", "store", "94",
                     "944789f92a8092cc__Live with Farouk, Friday, 3 July 2026.mp4")
OUT = os.path.join(HERE, "operator_clips_g1")
WIN_START, WIN_END = 30 * 60, 50 * 60          # real 00:30:00-00:50:00 (drift is LATER than transcript)
WORK = os.path.join(HERE, "_recut_window.wav")

TOKENS = {
    "FR-076": ["focus on one", "one asset", "one chart"],
    "FR-063": ["playing the probabilit", "having a checklist", "the probabilities"],
}


def main():
    subprocess.run([FF, "-y", "-ss", str(WIN_START), "-to", str(WIN_END),
                    "-i", MEDIA, "-ac", "1", "-ar", "16000", WORK],
                   check=True, capture_output=True)
    from faster_whisper import WhisperModel
    model = WhisperModel("small.en", device="cpu", compute_type="int8")
    segs, _ = model.transcribe(WORK, vad_filter=False, beam_size=5)   # NO VAD => real positions
    segs = list(segs)
    hits = {}
    for s in segs:
        tl = s.text.lower()
        for rid, toks in TOKENS.items():
            if rid in hits:
                continue
            if any(t in tl for t in toks):
                real = WIN_START + s.start
                hits[rid] = (real, s.text.strip())
    for rid, (real, text) in hits.items():
        c0, c1 = max(0, real - 8), real + 16
        clip = os.path.join(OUT, f"{rid}_ear_v2.mp3")
        subprocess.run([FF, "-y", "-ss", str(c0), "-to", str(c1), "-i", MEDIA,
                        "-vn", "-ac", "1", clip], check=True, capture_output=True)
        print(f"{rid}: real {int(real//60):02d}:{int(real%60):02d}  clip=[{int(c0//60):02d}:{int(c0%60):02d}-{int(c1//60):02d}:{int(c1%60):02d}]  '{text[:80]}'")
    for rid in TOKENS:
        if rid not in hits:
            print(f"{rid}: TOKEN NOT FOUND in window (widen window)")
    os.remove(WORK)


if __name__ == "__main__":
    main()
