"""FP-LIVE-VIDEO-EXPLAINER-005 detached transcription runner (review-only tooling).

Transcribes 'Live with Farouk, Sunday, 12 July 2026.mp4' locally with faster-whisper.
READS the source from Downloads; WRITES ONLY under
farouk_plus/derived/transcripts/explainer_005/. Original file untouched. No network
(model cached). Durable output by design (the batch-004 rescue lesson applied).
"""

import hashlib
import json
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

SRC = Path(r"C:\Users\Marty\Downloads\Live with Farouk, Sunday, 12 July 2026.mp4")
OUT = Path(__file__).resolve().parent.parent / "derived" / "transcripts" / "explainer_005"
ITEM = "FP-LIVE-VIDEO-EXPLAINER-005"
MODEL_NAME = "base.en"
KNOWN_SHA256 = "942DC4AF6F74504BD0FFEB80D37153943696C6DC51E42467E083707EDE85CB5D".lower()


def utc_now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    log_path = OUT / "_run.log"
    progress = OUT / "_progress.txt"

    def log(msg):
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(f"[{utc_now()}] {msg}\n")

    try:
        log(f"BEGIN {ITEM} source={SRC}")
        stat = SRC.stat()
        h = hashlib.sha256()
        with open(SRC, "rb") as f:
            for chunk in iter(lambda: f.read(8 * 1024 * 1024), b""):
                h.update(chunk)
        sha = h.hexdigest()
        log(f"sha256={sha} match_known={sha == KNOWN_SHA256}")
        meta = {
            "item_id": ITEM, "source_path": str(SRC), "source_bytes": stat.st_size,
            "source_modified_local": "2026-07-12 22:19:41", "sha256": sha,
            "sha256_matches_ingestion_hash": sha == KNOWN_SHA256,
            "rights_provenance": "his own YouTube live (linked by him in msg 45650); RIGHTS_PENDING_PRIVATE_REVIEW; private research only; no redistribution",
            "transcribed_at_utc": utc_now(), "tool": "faster-whisper", "model": MODEL_NAME,
            "compute": "cpu/int8", "vad_filter": True,
        }
        (OUT / f"{ITEM}_source_meta.json").write_text(json.dumps(meta, indent=1), encoding="utf-8")

        from faster_whisper import WhisperModel
        model = WhisperModel(MODEL_NAME, device="cpu", compute_type="int8")
        log("model loaded")
        t0 = time.time()
        segments, info = model.transcribe(str(SRC), vad_filter=True)
        log(f"audio duration={info.duration:.1f}s language={info.language}")
        seg_rows, txt = [], []
        for i, seg in enumerate(segments, 1):
            seg_rows.append({"idx": i, "start": round(seg.start, 2), "end": round(seg.end, 2), "text": seg.text.strip()})
            txt.append(f"[{seg.start:8.1f}s] {seg.text.strip()}")
            if i % 50 == 0:
                progress.write_text(f"RUNNING segments={i} audio_t={seg.end:.0f}/{info.duration:.0f}s elapsed={time.time()-t0:.0f}s\n", encoding="utf-8")
        (OUT / f"{ITEM}_transcript.txt").write_text("\n".join(txt) + "\n", encoding="utf-8")
        (OUT / f"{ITEM}_transcript.json").write_text(json.dumps({
            "schema_version": "1.0.0", "record_type": "transcript", "item_id": ITEM,
            "tool": "faster-whisper", "model": MODEL_NAME, "compute": "cpu/int8", "vad_filter": True,
            "language": info.language, "duration_s": round(info.duration, 2),
            "segment_count": len(seg_rows), "source_path": str(SRC), "sha256": sha,
            "note": "LOCAL offline; verbatim; SMC terms preserved; no diarization; no upload.",
            "segments": seg_rows}, indent=1), encoding="utf-8")
        progress.write_text(f"DONE segments={len(seg_rows)} audio={info.duration:.0f}s elapsed={time.time()-t0:.0f}s\n", encoding="utf-8")
        log(f"DONE {len(seg_rows)} segments in {time.time()-t0:.0f}s")
        return 0
    except Exception:
        log("FAILED\n" + traceback.format_exc())
        try:
            progress.write_text("FAILED - see _run.log\n", encoding="utf-8")
        except OSError:
            pass
        return 1


if __name__ == "__main__":
    sys.exit(main())
