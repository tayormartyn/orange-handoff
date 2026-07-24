#!/usr/bin/env python3
"""
Sybil's Hearth — Voice step (ElevenLabs).

Takes an APPROVED script (the JSON from the pipeline) and renders each line to
audio in the right character's locked voice, with the stillness settings from
nan-sybil-voice-design.md — and automatically adds a breath-pause at every
'gravity point' (any line whose delivery_note mentions breath/gravity/slow).

Runs AFTER Human Gate 1 (you approve the script first). Never before.

MODES
  --dry   : no key, no network. Writes a render-plan .txt per line so you see
            exactly what would be spoken, with which voice + settings + breaths.
  (live)  : real ElevenLabs calls. Set on YOUR machine (never in chat):
              ELEVEN_API_KEY
              ELEVEN_VOICE_NAN, ELEVEN_VOICE_MAEVE, ELEVEN_VOICE_JESSE  (voice IDs)
            Then:  python3 hearth_voice.py --script approved.json

USAGE
  python3 hearth_voice.py --demo --dry
  python3 hearth_voice.py --script path/to/approved_script.json [--dry] [--breaks]
"""
import os, sys, json, argparse

MODEL = os.environ.get("ELEVEN_MODEL", "eleven_multilingual_v2")
OUT = os.environ.get("HEARTH_AUDIO_DIR", "audio_out")

# Per-character voice settings (from nan-sybil-voice-design.md + twin cards)
SETTINGS = {
    "nan_sybil": {"stability": 0.72, "similarity_boost": 0.85, "style": 0.15},
    "maeve":     {"stability": 0.58, "similarity_boost": 0.85, "style": 0.25},
    "jesse":     {"stability": 0.64, "similarity_boost": 0.85, "style": 0.22},
}
VOICE_ENV = {"nan_sybil": "ELEVEN_VOICE_NAN",
             "maeve": "ELEVEN_VOICE_MAEVE",
             "jesse": "ELEVEN_VOICE_JESSE"}

def is_gravity(note):
    note = (note or "").lower()
    return any(k in note for k in ("gravity", "breath", "slow", "still"))

def score_text(text, note, add_breaks):
    """Punctuation already carries the breath. At gravity points, prepend a
    held silence so her stillness lands (ElevenLabs <break> tag)."""
    if add_breaks and is_gravity(note):
        return '<break time="1.0s" /> ' + text
    return text

def render_line(i, line, dry, add_breaks):
    spk = line["speaker"]
    text = score_text(line["text"], line.get("delivery_note", ""), add_breaks)
    settings = SETTINGS.get(spk, SETTINGS["nan_sybil"])
    os.makedirs(OUT, exist_ok=True)
    base = f"{OUT}/line_{i:02d}_{spk}"
    if dry:
        with open(base + ".plan.txt", "w") as f:
            f.write(f"voice   : {spk} (env {VOICE_ENV[spk]})\n")
            f.write(f"model   : {MODEL}\n")
            f.write(f"settings: {json.dumps(settings)}\n")
            f.write(f"gravity : {is_gravity(line.get('delivery_note',''))}\n")
            f.write(f"text    : {text}\n")
        print(f"  ♪ line {i:02d} [{spk}] {'· breath' if is_gravity(line.get('delivery_note','')) else ''}")
        print(f"     “{text[:76]}{'…' if len(text)>76 else ''}”")
        return base + ".plan.txt"
    import requests
    vid = os.environ[VOICE_ENV[spk]]
    r = requests.post(f"https://api.elevenlabs.io/v1/text-to-speech/{vid}",
        headers={"xi-api-key": os.environ["ELEVEN_API_KEY"],
                 "accept": "audio/mpeg", "content-type": "application/json"},
        json={"text": text, "model_id": MODEL,
              "voice_settings": {**settings, "use_speaker_boost": True}})
    r.raise_for_status()
    with open(base + ".mp3", "wb") as f:
        f.write(r.content)
    print(f"  ✔ line {i:02d} [{spk}] → {base}.mp3")
    return base + ".mp3"

def try_stitch(files, dry):
    """Optional: join the per-line clips into one track with gentle gaps."""
    if dry: return
    try:
        from pydub import AudioSegment
        gap = AudioSegment.silent(duration=450)
        track = AudioSegment.empty()
        for fpath in files:
            track += AudioSegment.from_mp3(fpath) + gap
        track.export(f"{OUT}/full.mp3", format="mp3")
        print(f"\n  ✔ stitched → {OUT}/full.mp3")
    except Exception as e:
        print(f"\n  · per-line clips ready; stitch skipped ({e}). "
              f"pip install pydub + ffmpeg to auto-join, or assemble in your editor.")

DEMO = {  # the locked Rising Tide script (abridged), for --demo
  "character": "family", "format": "multi_character",
  "script_lines": [
    {"speaker": "nan_sybil", "text": "Oh… there you are. Come in, love — sit down by the fire.", "delivery_note": "cosy open"},
    {"speaker": "nan_sybil", "text": "You weren't drowning. …You were floating. That matters more than you know.", "delivery_note": "gravity point — silence before the weight"},
    {"speaker": "maeve", "text": "Some of the old stories say water is feeling, sweet thing — all of it.", "delivery_note": "intimate, close"},
    {"speaker": "jesse", "text": "You don't find the shore by treading water and waiting. One stroke at a time.", "delivery_note": "grounded, lands"},
    {"speaker": "nan_sybil", "text": "You're not lost, love. You're just between shores for a little while.", "delivery_note": "warm close, slow"},
  ]}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--script"); ap.add_argument("--demo", action="store_true")
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("--breaks", action="store_true", default=True)
    a = ap.parse_args()
    if a.demo: script = DEMO
    elif a.script: script = json.load(open(a.script))
    else: sys.exit("Pass --script <file> or --demo")

    print(f"\n=== Voicing: {script.get('title', script.get('format'))} "
          f"({len(script['script_lines'])} lines) ===")
    files = [render_line(i+1, ln, a.dry, a.breaks) for i, ln in enumerate(script["script_lines"])]
    try_stitch(files, a.dry)
    print(f"\n{'[dry run — render plans written]' if a.dry else 'audio ready in ' + OUT}/\n")

if __name__ == "__main__":
    main()
