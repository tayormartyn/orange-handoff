"""Transcribe a video's audio with faster-whisper (local cached base.en model, int8 CPU)."""
import sys, io, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
from faster_whisper import WhisperModel

src, dst = sys.argv[1], sys.argv[2]
model = WhisperModel("base.en", device="cpu", compute_type="int8")
segments, info = model.transcribe(src, vad_filter=True, beam_size=1)
out = []
with open(dst, "w", encoding="utf-8") as fh:
    for s in segments:
        line = {"start": round(s.start, 1), "end": round(s.end, 1), "text": s.text.strip()}
        out.append(line)
        fh.write(json.dumps(line, ensure_ascii=False) + "\n")
print(f"segments={len(out)} duration={info.duration:.0f}s written={dst}")
