"""FR-076 re-cut v3 from the STRONGEST real-quote source that has local media:
gmt20251221 ~[02:26:12] 'not only gold, also BTC, but gold respects a little bit more'.
Cut a wide window, ASR-transcribe it (no VAD => real positions), and ONLY keep the clip if the
transcription actually contains the instrument-focus content. Read-only toward everything else."""
import os, subprocess, sys, tempfile

ROOT = r"C:\Users\Marty\signal-terminal"
FF = os.path.join(ROOT, ".venv-vision", "Lib", "site-packages", "imageio_ffmpeg",
                  "binaries", "ffmpeg-win-x86_64-v7.1.exe")
SRC = os.path.join(ROOT, "research", "farouk_pilot", "corpus", "store", "c5",
                   "c5508175ec0d635b__GMT20251221-181518_Recording (1).m4a")
OUT = os.path.join(ROOT, "research", "farouk_pilot", "stage2_rule_mining", "operator_clips_g1")
START = 2*3600 + 25*60 + 30      # 02:25:30
DUR = 100                        # 100s window (guards against drift)

if not os.path.exists(SRC):
    print("SRC_MISSING", SRC); sys.exit(2)
tmp = tempfile.mkdtemp()
wav = os.path.join(tmp, "clip.wav")
subprocess.run([FF, "-y", "-ss", str(START), "-t", str(DUR), "-i", SRC, "-vn", "-ac", "1",
                "-ar", "16000", wav], check=True, capture_output=True)
from faster_whisper import WhisperModel
model = WhisperModel("small.en", device="cpu", compute_type="int8")
segs, _ = model.transcribe(wav, vad_filter=False, beam_size=5)
text = ""
hit_at = None
for s in segs:
    text += s.text
    low = s.text.lower()
    if hit_at is None and ("gold" in low and ("btc" in low or "respect" in low or "focus" in low or "personally" in low)):
        hit_at = START + s.start
print("ASR_TRANSCRIPT:")
print(text.strip()[:600])
low = text.lower()
verified = ("gold" in low) and ("btc" in low or "respect" in low or "focus" in low)
print("\nINSTRUMENT_FOCUS_CONTENT_PRESENT:", verified)
print("REAL_HIT_AT:", None if hit_at is None else f"{int(hit_at//3600):02d}:{int((hit_at%3600)//60):02d}:{int(hit_at%60):02d}")
if verified:
    mp3 = os.path.join(OUT, "FR-076_ear_v3.mp3")
    subprocess.run([FF, "-y", "-ss", str(START), "-t", str(DUR), "-i", SRC, "-vn", "-ac", "1", mp3],
                   check=True, capture_output=True)
    print("WROTE:", mp3)
else:
    print("NOT_VERIFIED - no clip written (do not hand a mis-cut clip)")
