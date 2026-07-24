#!/usr/bin/env python3
"""
Sybil's Hearth — Voice Worker (W3, automated).

Closes the loop: watches Airtable for scripts YOU approved, and for each one
automatically renders every line to audio in the right voice (with the
gravity-point breaths), files the audio as an Asset, and flips the script to
'voiced'. Run it on a timer (cron) or by hand after you approve.

    approved script  ──►  ElevenLabs  ──►  audio file  ──►  Status: voiced

MODES
  --dry   : no keys, no network. Uses a demo 'approved' script so you can watch
            the whole flow run. Safe anywhere.
  (live)  : set on YOUR machine (never in chat):
              ELEVEN_API_KEY, ELEVEN_VOICE_NAN/MAEVE/JESSE,
              AIRTABLE_PAT, AIRTABLE_BASE_ID
            then:  python3 hearth_voice_worker.py

Requires hearth_voice.py in the same folder (it reuses the voice settings +
breath-scoring so nothing is duplicated).
"""
import os, json, argparse
from hearth_voice import SETTINGS, VOICE_ENV, MODEL, score_text   # single source of truth

AUDIO_ROOT = os.environ.get("HEARTH_AUDIO_DIR", "audio_out")

DEMO = {"id": "recDEMO", "title": "A blessing for a hard day", "character": "nan_sybil",
        "script_lines": [
          {"speaker": "nan_sybil", "text": "Oh, love. You've had one of those days, haven't you.",
           "delivery_note": "warm, notices you"},
          {"speaker": "nan_sybil", "text": "You've done ever so well to get this far. Truly.",
           "delivery_note": "gravity — let it land"},
          {"speaker": "nan_sybil", "text": "Now. Drink your tea while it's warm.",
           "delivery_note": "soft close, slow breath"}]}

# ---------- ElevenLabs render (one line) ------------------------------------
def render_line(text, speaker, outdir, idx, dry):
    settings = SETTINGS.get(speaker, SETTINGS["nan_sybil"])
    os.makedirs(outdir, exist_ok=True)
    base = f"{outdir}/line_{idx:02d}_{speaker}"
    if dry:
        print(f"    ♪ line {idx:02d} [{speaker}]  “{text[:64]}{'…' if len(text)>64 else ''}”")
        open(base + ".plan.txt", "w").write(f"{speaker} {json.dumps(settings)}\n{text}\n")
        return base + ".plan.txt"
    import requests
    r = requests.post(f"https://api.elevenlabs.io/v1/text-to-speech/{os.environ[VOICE_ENV[speaker]]}",
        headers={"xi-api-key": os.environ["ELEVEN_API_KEY"], "accept": "audio/mpeg",
                 "content-type": "application/json"},
        json={"text": text, "model_id": MODEL,
              "voice_settings": {**settings, "use_speaker_boost": True}})
    r.raise_for_status()
    open(base + ".mp3", "wb").write(r.content)
    print(f"    ✔ line {idx:02d} [{speaker}] → {base}.mp3")
    return base + ".mp3"

def render_script(script, dry):
    outdir = f"{AUDIO_ROOT}/{script['id']}"
    files = []
    for i, ln in enumerate(script["script_lines"], 1):
        text = score_text(ln["text"], ln.get("delivery_note", ""), True)  # adds breath at gravity pts
        files.append(render_line(text, ln["speaker"], outdir, i, dry))
    return outdir, files

# ---------- Airtable --------------------------------------------------------
def at(path, dry, method="GET", body=None):
    if dry: return {"records": [DEMO]} if method == "GET" else {"id": "recDEMO"}
    import requests
    base, pat = os.environ["AIRTABLE_BASE_ID"], os.environ["AIRTABLE_PAT"]
    url = f"https://api.airtable.com/v0/{base}/{path}"
    hdr = {"Authorization": f"Bearer {pat}", "Content-Type": "application/json"}
    r = requests.request(method, url, headers=hdr, json=body)
    r.raise_for_status(); return r.json()

def get_approved(dry):
    if dry: return [DEMO]
    from urllib.parse import quote
    recs = at("Scripts?filterByFormula=" + quote("{Status}='approved'"), dry)
    out = []
    for rec in recs.get("records", []):
        f = rec.get("fields", {})
        try:
            script = json.loads(f["Script JSON"]); script["id"] = rec["id"]
            out.append(script)
        except Exception:
            print(f"  ! {rec['id']}: bad Script JSON — skipping")
    return out

def mark_voiced(script_id, outdir, dry):
    # file the audio as an Asset, then flip the script to 'voiced'
    at("Assets", dry, "POST", {"fields": {
        "Type": "audio", "Speaker": "nan_sybil", "Tool": "elevenlabs",
        "File URL": outdir, "Status": "ready"}})
    at(f"Scripts/{script_id}", dry, "PATCH", {"fields": {"Status": "voiced"}})

# ---------- main ------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--dry", action="store_true")
    dry = ap.parse_args().dry
    print("=== Voice Worker: looking for approved scripts ===")
    scripts = get_approved(dry)
    if not scripts:
        print("  (none approved right now)"); return
    for s in scripts:
        print(f"\n  → voicing: {s.get('title', s['id'])}  ({len(s['script_lines'])} lines)")
        outdir, files = render_script(s, dry)
        mark_voiced(s["id"], outdir, dry)
        print(f"  ✅ audio ready in {outdir}/  →  Script status: voiced")
    print(f"\nDone. {len(scripts)} script(s) voiced.\n")

if __name__ == "__main__":
    main()
