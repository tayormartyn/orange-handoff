# Running the self-contained pipeline

`hearth_pipeline.py` is the whole W1→W2 flow in one program — no n8n, no
server. Two ways to run it.

## Dry mode (no keys, no network — see the logic work)
```bash
python3 hearth_pipeline.py --dry --dream "your dream text here"
```
- A distress dream → 🛑 Care Queue, no script.
- A normal dream → ✅ script drafted at needs_review.
This is safe to run anywhere and proves the flow before you plug anything in.

## Live mode (on YOUR machine — keys stay with you)
1. Run `setup_airtable.py` once to build the ledger.
2. Set env vars **in your own terminal** (never paste keys into a chat):
   ```bash
   export ANTHROPIC_API_KEY="sk-ant-..."
   export AIRTABLE_PAT="pat..."
   export AIRTABLE_BASE_ID="app..."
   ```
   *(`pip install requests` if you don't have it.)*
3. Run:
   ```bash
   python3 hearth_pipeline.py --dream "I was swimming in a rising sea..."
   ```
   → real safety check, real script, written to your Airtable at needs_review.

## Voicing an approved script (`hearth_voice.py`)
After you approve a drafted script, turn it into Nan's (and the twins') actual
audio:
```bash
python3 hearth_voice.py --demo --dry          # see the render plan, no key
python3 hearth_voice.py --script approved.json # live, on your machine
```
Live mode needs, set in your own terminal:
```bash
export ELEVEN_API_KEY="..."
export ELEVEN_VOICE_NAN="voiceId"    # your locked Nan voice
export ELEVEN_VOICE_MAEVE="voiceId"
export ELEVEN_VOICE_JESSE="voiceId"
```
It renders one clip per line in the right voice + settings, and automatically
adds a held breath at every gravity point (any line whose delivery_note says
breath/gravity/slow). `pip install pydub` + ffmpeg to auto-stitch into one track.

## Notes
- Prompt layers are read live from `../prompts/`, so editing a module changes
  every future script — no code changes needed.
- The safety layer runs first, every time. A flagged dream never reaches the
  engine. That behaviour is the point; don't remove it.
- ⛔ Still no paid voice/video/publish here — this is the intake+draft core.
  Add those only after you trust this, one step at a time.
- This can run as a one-off, on a schedule (cron), or behind a tiny web form.
  It does not need to be "always on" to work.
