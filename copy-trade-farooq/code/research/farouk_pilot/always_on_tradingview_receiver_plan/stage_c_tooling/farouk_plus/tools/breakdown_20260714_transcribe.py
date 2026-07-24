"""FP-CAMPAIGN-BREAKDOWN-20260714 transcription (review-only). Same durable pattern as
explainer_005. READS the .mov from Downloads; WRITES ONLY under
farouk_plus/derived/transcripts/breakdown_20260714/. Original untouched. Offline, model cached."""
import hashlib, json, sys, time, traceback
from datetime import datetime, timezone
from pathlib import Path

SRC = Path(r"C:\Users\Marty\Downloads\Schermopname 2026-07-14 om 17.47.54.mov")
OUT = Path(__file__).resolve().parent.parent / "derived" / "transcripts" / "breakdown_20260714"
ITEM = "FP-CAMPAIGN-BREAKDOWN-20260714"
MODEL_NAME = "base.en"
KNOWN_SHA = "d871ca8474b197f8216a1cd9813cd1bc473d9ee2df67ffd3233e32993d07e023"


def utc():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    log = OUT / "_run.log"
    def w(m):
        open(log, "a", encoding="utf-8").write(f"[{utc()}] {m}\n")
    try:
        st = SRC.stat()
        h = hashlib.sha256()
        with open(SRC, "rb") as f:
            for c in iter(lambda: f.read(8 << 20), b""):
                h.update(c)
        sha = h.hexdigest()
        w(f"sha256={sha} match={sha == KNOWN_SHA}")
        (OUT / f"{ITEM}_source_meta.json").write_text(json.dumps({
            "item_id": ITEM, "source_path": str(SRC), "source_bytes": st.st_size, "sha256": sha,
            "sha256_matches_ingestion_hash": sha == KNOWN_SHA, "source_modified_local": "2026-07-14 21:20",
            "rights_provenance": "Discord .mov breakdown forwarded by Farouk (ref msg 45742); "
                                 "MANUAL_DISCORD_FORWARD; RIGHTS_PENDING_PRIVATE_REVIEW; private research only",
            "classification": "RETROSPECTIVE_EXPLANATION",
            "transcribed_at_utc": utc(), "tool": "faster-whisper", "model": MODEL_NAME,
            "compute": "cpu/int8", "vad_filter": True}, indent=1), encoding="utf-8")
        from faster_whisper import WhisperModel
        model = WhisperModel(MODEL_NAME, device="cpu", compute_type="int8")
        w("model loaded")
        t0 = time.time()
        segments, info = model.transcribe(str(SRC), vad_filter=True)
        rows, txt = [], []
        for i, s in enumerate(segments, 1):
            rows.append({"idx": i, "start": round(s.start, 2), "end": round(s.end, 2),
                         "text": s.text.strip(), "avg_logprob": round(getattr(s, "avg_logprob", 0), 3),
                         "no_speech_prob": round(getattr(s, "no_speech_prob", 0), 3)})
            txt.append(f"[{s.start:7.1f}s] {s.text.strip()}")
        (OUT / f"{ITEM}_transcript.txt").write_text("\n".join(txt) + "\n", encoding="utf-8")
        (OUT / f"{ITEM}_transcript.json").write_text(json.dumps({
            "schema_version": "1.0.0", "record_type": "transcript", "item_id": ITEM,
            "tool": "faster-whisper", "model": MODEL_NAME, "language": info.language,
            "duration_s": round(info.duration, 2), "segment_count": len(rows),
            "sha256": sha, "note": "LOCAL offline; verbatim; SMC terms preserved; no upload.",
            "segments": rows}, indent=1), encoding="utf-8")
        w(f"DONE {len(rows)} segments duration={info.duration:.1f}s elapsed={time.time()-t0:.0f}s")
        (OUT / "_progress.txt").write_text(f"DONE segments={len(rows)}\n", encoding="utf-8")
        return 0
    except Exception:
        w("FAILED\n" + traceback.format_exc())
        return 1


if __name__ == "__main__":
    sys.exit(main())
