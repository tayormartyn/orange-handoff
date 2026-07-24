"""FIXED audio-clip re-cutter (K-056 defect fix, 2026-07-22).

Root cause of the drift: clips were cut with INPUT seek ('-ss'/'-to' BEFORE '-i') on MP4, which
snaps to video keyframes and lands off-position. FIX: ACCURATE OUTPUT seek ('-i' then '-ss'/'-t'),
which is sample-accurate, PLUS a CLOSED-LOOP verify - ASR the cut clip and confirm the cited token
is actually in it before the clip is kept. A clip that fails verification is NOT written.
Read-only toward everything else.
"""
import os, re, subprocess, tempfile
ROOT = r"C:\Users\Marty\signal-terminal"
FF = os.path.join(ROOT, ".venv-vision", "Lib", "site-packages", "imageio_ffmpeg", "binaries", "ffmpeg-win-x86_64-v7.1.exe")
STORE = os.path.join(ROOT, "research", "farouk_pilot", "corpus", "store")
OUT = os.path.join(ROOT, "research", "farouk_pilot", "stage2_rule_mining", "operator_clips_g1")
FRI3 = os.path.join(STORE, "94", "944789f92a8092cc__Live with Farouk, Friday, 3 July 2026.mp4")
SUN12 = os.path.join(STORE, "94", "942dc4af6f74504b__Live with Farouk, Sunday, 12 July 2026.mp4")
FRI10 = os.path.join(STORE, "f1", "f1200fed0ebc5832__Live with Farouk, Friday, 10 July 2026.mp4")
GMT = os.path.join(STORE, "c5", "c5508175ec0d635b__GMT20251221-181518_Recording (1).m4a")

from faster_whisper import WhisperModel
model = WhisperModel("small.en", device="cpu", compute_type="int8")

def _extract(media, start, dur, out, mp3=False):
    args = [FF, "-y", "-i", media, "-ss", str(start), "-t", str(dur), "-vn", "-ac", "1"]
    if not mp3:
        args += ["-ar", "16000"]
    args += [out]
    subprocess.run(args, check=True, capture_output=True)   # ACCURATE output seek

def _asr(wav):
    segs, _ = model.transcribe(wav, vad_filter=False, beam_size=5)
    return "".join(s.text for s in segs).strip()

# (rule, [candidate (media,start,dur,required DISTINCTIVE-PHRASE groups) ...]) - first verified wins.
# Verify uses distinctive PHRASES, not loose keywords (loose 'gold' matched structural gold-talk).
TARGETS = {
 "FR-076": [
   (SUN12, 31*60+50,        40, [["gold"], ["personally"], ["silver", "doing"]]),
   (FRI10, 1*3600+18*60+38, 30, [["btc and gold", "only btc and gold"]]),
   (FRI3,  29*60+52,        40, [["focus on one"], ["asset", "chart"]]),
 ],
 "FR-063": [
   (FRI3,  40*60+40,        40, [["checklist"], ["probabilit"]]),
 ],
}

for rid, cands in TARGETS.items():
    stale = os.path.join(OUT, f"{rid}_ear_v3.mp3")   # never leave a stale/false-positive v3
    if os.path.exists(stale):
        os.remove(stale)
    done = False
    for media, start, dur, groups in cands:
        if not os.path.exists(media):
            continue
        tmp = tempfile.mkdtemp(); wav = os.path.join(tmp, "c.wav")
        _extract(media, start, dur, wav)
        txt = _asr(wav); low = re.sub(r"[^a-z0-9 ]+", " ", txt.lower())
        ok = all(any(t in low for t in grp) for grp in groups)
        src = os.path.basename(media).split("__")[-1]
        print(f"{rid}: [{src} @ {start//60:02d}:{start%60:02d}] verified={ok}")
        print(f"   ASR: {txt[:240]}")
        if ok:
            mp3 = os.path.join(OUT, f"{rid}_ear_v3.mp3")
            _extract(media, start, dur, mp3, mp3=True)
            print(f"   WROTE (token verified in clip): {os.path.basename(mp3)}")
            done = True
            break
    if not done:
        print(f"{rid}: NO candidate verified -> no clip written")
