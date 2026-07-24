#!/usr/bin/env python3
"""
Sybil's Hearth — self-contained pipeline (W1 + W2, no n8n needed).

Runs the whole flow in one program:
  intake → SAFETY classifier → (if safe) assemble 4 layers → generate script
  → validate → write to Airtable at needs_review.
  If flagged: route to Care Queue, generate NOTHING.

MODES
  --dry    : no network, no keys. Mocks the LLM + Airtable so you can see the
             logic run end-to-end. Safe to run anywhere.
  (live)   : real calls. Set env vars ON YOUR OWN MACHINE (never in chat):
               ANTHROPIC_API_KEY, AIRTABLE_PAT, AIRTABLE_BASE_ID
             Then:  python3 hearth_pipeline.py --dream "your dream text"

The prompt layers are read from the repo's prompts/ folder, so edits there
flow straight through. Care comes before content, always.
"""
import os, re, sys, json, argparse

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # sybils-hearth/
P = os.path.join(REPO, "prompts")

BANNED = ["wellbeing", "journey", "self-care", "your energy", "content",
          "subscribe", " guys", "manifest", "vibe"]
HARD_FLAG = ["kill myself", "end my life", "don't want to be here",
             "want to die", "suicidal", "hurt myself", "self harm", "self-harm"]

# ---------- helpers ----------------------------------------------------------
def code_block(path):
    """Return the first ``` fenced block from a markdown file (or whole file)."""
    txt = open(path, encoding="utf-8").read()
    m = re.search(r"```[a-zA-Z]*\n(.*?)```", txt, re.S)
    return m.group(1).strip() if m else txt.strip()

def log(tag, msg): print(f"  [{tag}] {msg}")

# ---------- W1: safety -------------------------------------------------------
def safety_classify(dream, dry):
    if dry:
        flagged = any(k in dream.lower() for k in HARD_FLAG)
        return {"classification": "FLAG" if flagged else "SAFE",
                "category": "self_harm_suicide" if flagged else "none",
                "confidence": "high",
                "reason": "keyword mock (dry mode)"}
    import requests
    prompt = code_block(os.path.join(P, "w1-safety-classifier.md"))
    r = requests.post("https://api.anthropic.com/v1/messages",
        headers={"x-api-key": os.environ["ANTHROPIC_API_KEY"],
                 "anthropic-version": "2023-06-01", "content-type": "application/json"},
        json={"model": "claude-sonnet-4-latest", "max_tokens": 300,
              "system": prompt, "messages": [{"role": "user", "content": dream}]})
    r.raise_for_status()
    try:
        return json.loads(r.json()["content"][0]["text"])
    except Exception:
        return {"classification": "FLAG", "category": "ambiguous",
                "confidence": "low", "reason": "unparseable — routing to human"}

# ---------- W2: assemble + generate -----------------------------------------
def assemble_prompt(dream, character, fmt):
    system = code_block(os.path.join(P, "system-prompt.md"))
    if character == "family":
        cards = "\n\n".join(code_block(os.path.join(P, "character-modules", f"{c}.md"))
                            for c in ("nan-sybil", "maeve", "jesse"))
    else:
        cards = code_block(os.path.join(P, "character-modules", f"{character}.md"))
    fmt_mod = code_block(os.path.join(P, "format-modules", f"{fmt.replace('_','-')}.md"))
    schema = code_block(os.path.join(P, "output-schema.md"))
    task = (f"FORMAT: {fmt}\nCHARACTER: {character}\n"
            f"DREAM/TOPIC: {dream}\nVARIABLES: {{}}")
    return "\n\n".join([system, cards, fmt_mod, "OUTPUT SCHEMA:\n"+schema,
                        "TASK INPUT:\n"+task])

def generate_script(dream, character, fmt, dry):
    if dry:
        # canned, schema-valid mock so validation exercises the real path
        return {"character": character, "format": fmt, "title": "(dry-mode draft)",
                "hook": "Some say water in a dream is never just water…",
                "beats": ["validate", "lore as mirror", "gentle question", "close"],
                "script_lines": [{"speaker": ("nan_sybil" if character=="family" else character),
                    "text": "Come and sit by the fire, love — some say the old dreams "
                            "are just the heart, talking while you sleep.",
                    "delivery_note": "warm, slow"}],
                "cta": "Leave your dream below — I read one every week. The kettle's on.",
                "on_screen_caption": "a dream by the fire", "disclaimer_line": "a mirror, not a warning",
                "safety_flag": False, "safety_response": None,
                "hashtags": ["#dreammeaning"], "notes_for_editor": "dry-mode placeholder"}
    import requests
    full = assemble_prompt(dream, character, fmt)
    for _ in range(3):
        r = requests.post("https://api.anthropic.com/v1/messages",
            headers={"x-api-key": os.environ["ANTHROPIC_API_KEY"],
                     "anthropic-version": "2023-06-01", "content-type": "application/json"},
            json={"model": "claude-sonnet-4-latest", "max_tokens": 1500,
                  "temperature": 0.5, "system": full,
                  "messages": [{"role": "user", "content": "Return the script JSON now."}]})
        r.raise_for_status()
        try:
            out = json.loads(r.json()["content"][0]["text"])
            if validate(out): return out
        except Exception:
            continue
    return None

def validate(out):
    try:
        assert out["character"] in ("nan_sybil", "maeve", "jesse", "family")
        assert out["format"] in ("hero_dream_short", "validation_moment",
                                 "fireside_tale", "dream_of_the_week", "multi_character")
        blob = json.dumps(out.get("script_lines", [])).lower()
        assert not any(w.strip() in blob for w in BANNED)
        if out["format"] != "multi_character":
            assert all(l["speaker"] == out["character"] for l in out["script_lines"])
        return True
    except Exception as e:
        log("VALIDATE", f"failed: {e}"); return False

# ---------- Airtable ---------------------------------------------------------
def airtable(table, fields, dry, op="create", rec_id=None):
    if dry:
        log("AIRTABLE", f"[dry] {op} {table}: {json.dumps(fields)[:90]}…"); return {"id": "recDRY"}
    import requests
    base = os.environ["AIRTABLE_BASE_ID"]; pat = os.environ["AIRTABLE_PAT"]
    url = f"https://api.airtable.com/v0/{base}/{table}"
    hdr = {"Authorization": f"Bearer {pat}", "Content-Type": "application/json"}
    if op == "create":
        r = requests.post(url, headers=hdr, json={"fields": fields})
    else:
        r = requests.patch(f"{url}/{rec_id}", headers=hdr, json={"fields": fields})
    r.raise_for_status(); return r.json()

# ---------- the flow ---------------------------------------------------------
def run(dream, character, fmt, dry):
    print("\n=== Sybil's Hearth pipeline ===")
    log("INTAKE", dream[:70] + ("…" if len(dream) > 70 else ""))
    sub = airtable("Submissions", {"Raw Dream Text": dream, "Status": "new"}, dry)

    verdict = safety_classify(dream, dry)
    log("W1", json.dumps(verdict))
    forced = any(k in dream.lower() for k in HARD_FLAG)
    if verdict["classification"] == "FLAG" or forced:
        airtable("Submissions", {"Safety Flag": True, "Status": "care_queue"},
                 dry, op="update", rec_id=sub["id"])
        print("\n🛑 ROUTED TO CARE QUEUE — no script generated. A human will reply with care.\n")
        return
    airtable("Submissions", {"Status": "screened"}, dry, op="update", rec_id=sub["id"])

    script = generate_script(dream, character, fmt, dry)
    if not script:
        log("W2", "engine failed validation 3x — flagged for human draft"); return
    if script.get("safety_flag"):
        airtable("Submissions", {"Safety Flag": True, "Status": "care_queue"},
                 dry, op="update", rec_id=sub["id"]); return
    airtable("Scripts", {"Character": script["character"], "Format": script["format"],
                         "Script JSON": json.dumps(script), "Status": "needs_review",
                         "Version": 1}, dry)
    print("\n✅ SCRIPT DRAFTED → Status: needs_review (waiting for your approval).")
    print(json.dumps(script, indent=2)[:600] + "…\n")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dream", required=True)
    ap.add_argument("--character", default="family")
    ap.add_argument("--format", default="multi_character")
    ap.add_argument("--dry", action="store_true")
    a = ap.parse_args()
    run(a.dream, a.character, a.format, a.dry)
