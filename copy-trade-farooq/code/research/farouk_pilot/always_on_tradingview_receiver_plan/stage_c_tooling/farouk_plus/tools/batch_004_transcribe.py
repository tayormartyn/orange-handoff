"""Batch 004 detached transcription runner (review-only tooling).

Transcribes the two unprocessed Sunday-Zoom recordings locally with faster-whisper.
Canonical audio (.m4a) only — the *_Recording_*x*.mp4 files and the "(1)" copies are
the SAME recordings (video/duplicate variants) and are intentionally excluded.
READS from Downloads; WRITES ONLY under farouk_plus/derived/transcripts/batch_004/.
Touches nothing else: no trading state, no listener, no DB, no gates, no alerts,
no Worker, no broker, no execution files. No network use (model cached locally).

Designed to run detached and survive the launching session:
    .venv-vision\\Scripts\\python.exe batch_004_transcribe.py
"""

import hashlib
import json
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

DOWNLOADS = Path(r"C:\Users\Marty\Downloads")
OUT_ROOT = Path(__file__).resolve().parent.parent / "derived" / "transcripts" / "batch_004"

ITEMS = [
    ("FP-B004-Z1", "Sunday Zoom 2025-10-12 (GMT20251012-140632)", DOWNLOADS / "GMT20251012-140632_Recording.m4a"),
    ("FP-B004-Z2", "Sunday Zoom 2025-12-21 (GMT20251221-181518)", DOWNLOADS / "GMT20251221-181518_Recording.m4a"),
]

MODEL_NAME = "base.en"


def utc_now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def sha256_of(path, log):
    h = hashlib.sha256()
    t0 = time.time()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8 * 1024 * 1024), b""):
            h.update(chunk)
    log(f"sha256 computed in {time.time() - t0:.1f}s")
    return h.hexdigest()


def main():
    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    master_log_path = OUT_ROOT / "_master.log"

    def mlog(msg):
        with open(master_log_path, "a", encoding="utf-8") as f:
            f.write(f"[{utc_now()}] {msg}\n")

    mlog(f"START batch_004 transcription pid={__import__('os').getpid()} model={MODEL_NAME} items={len(ITEMS)}")

    from faster_whisper import WhisperModel
    model = WhisperModel(MODEL_NAME, device="cpu", compute_type="int8")
    mlog("model loaded")

    ok, failed = [], []
    for item_id, label, src in ITEMS:
        out_dir = OUT_ROOT / item_id
        out_dir.mkdir(parents=True, exist_ok=True)
        run_log_path = out_dir / "_run.log"
        progress_path = out_dir / "_progress.txt"

        def rlog(msg):
            with open(run_log_path, "a", encoding="utf-8") as f:
                f.write(f"[{utc_now()}] {msg}\n")

        try:
            rlog(f"BEGIN {item_id} '{label}' source={src}")
            if not src.exists():
                raise FileNotFoundError(str(src))
            stat = src.stat()
            meta = {
                "item_id": item_id,
                "label": label,
                "source_path": str(src),
                "source_bytes": stat.st_size,
                "source_modified_utc": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(timespec="seconds"),
                "sha256": sha256_of(src, rlog),
                "evidence_id_placeholder": f"{item_id}-EVIDENCE-ID-TBD",
                "rights_provenance": "member-recorded WhaleRoom Zoom session; private research use only",
                "transcribed_at_utc": utc_now(),
                "tool": "faster-whisper", "model": MODEL_NAME, "compute": "cpu/int8", "vad_filter": True,
            }
            (out_dir / f"{item_id}_source_meta.json").write_text(json.dumps(meta, indent=1), encoding="utf-8")

            t0 = time.time()
            segments, info = model.transcribe(str(src), vad_filter=True)
            rlog(f"audio duration={info.duration:.1f}s language={info.language} p={info.language_probability:.2f}")

            seg_rows, txt_lines = [], []
            for i, seg in enumerate(segments, 1):
                seg_rows.append({"idx": i, "start": round(seg.start, 2), "end": round(seg.end, 2), "text": seg.text.strip()})
                txt_lines.append(f"[{seg.start:8.1f}s] {seg.text.strip()}")
                if i % 25 == 0:
                    progress_path.write_text(
                        f"RUNNING segments={i} audio_t={seg.end:.0f}/{info.duration:.0f}s elapsed={time.time() - t0:.0f}s\n",
                        encoding="utf-8")

            (out_dir / f"{item_id}_transcript.txt").write_text("\n".join(txt_lines) + "\n", encoding="utf-8")
            doc = {
                "schema_version": "1.0.0", "record_type": "transcript", "item_id": item_id, "label": label,
                "tool": "faster-whisper", "model": MODEL_NAME, "compute": "cpu/int8", "vad_filter": True,
                "language": info.language, "duration_s": round(info.duration, 2), "segment_count": len(seg_rows),
                "source_path": str(src), "sha256": meta["sha256"],
                "note": "LOCAL offline; verbatim; SMC terms (BOS/CHoCH/OB/FVG/BPR) preserved; no diarization; no upload.",
                "segments": seg_rows,
            }
            (out_dir / f"{item_id}_transcript.json").write_text(json.dumps(doc, indent=1), encoding="utf-8")
            progress_path.write_text(
                f"DONE segments={len(seg_rows)} audio={info.duration:.0f}s elapsed={time.time() - t0:.0f}s\n",
                encoding="utf-8")
            rlog(f"DONE {len(seg_rows)} segments in {time.time() - t0:.0f}s")
            ok.append(item_id)
            mlog(f"{item_id} DONE ({len(seg_rows)} segments)")
        except Exception:
            err = traceback.format_exc()
            rlog("FAILED\n" + err)
            try:
                progress_path.write_text("FAILED - see _run.log\n", encoding="utf-8")
            except OSError:
                pass
            failed.append(item_id)
            mlog(f"{item_id} FAILED")

    mlog(f"END ok={ok} failed={failed}")
    (OUT_ROOT / "_master_progress.txt").write_text(
        f"FINISHED ok={len(ok)}/{len(ITEMS)} failed={failed or 'none'} at {utc_now()}\n", encoding="utf-8")
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
