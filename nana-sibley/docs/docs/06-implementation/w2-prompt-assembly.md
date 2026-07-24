# W2 — Prompt-Assembly Pseudocode

> The deterministic logic that assembles the four layers, calls the model,
> validates the JSON, and files a script for review. Language-agnostic
> pseudocode — the agent implements it in the n8n runtime (JS). Zero ambiguity
> by design.

---

## Main flow

```
function generateScript(submission):
    # submission = { id, dreamText, character?, format?, variables }

    # 1 · Decide format + character (MVP rules)
    format = submission.format or "hero_dream_short"
    if format == "multi_character":
        character = "family"
    else:
        character = submission.character or rotateCharacter()   # nan/maeve/jesse

    # 2 · Load the four layers (cache the module files; refresh on change)
    systemPrompt  = loadCodeBlock("prompts/system-prompt.md")
    characterCard = loadCodeBlock("prompts/character-modules/{character}.md")
        # for nan_sybil, also append nan-sybil-presence-and-stillness.md
        # (and nan-sybil-voice-design.md is for rendering, not the prompt)
    formatModule  = loadCodeBlock("prompts/format-modules/{format}.md")
    outputSchema  = loadCodeBlock("prompts/output-schema.md")

    # 3 · Build the task block
    task = joinLines(
        "FORMAT: "        + format,
        "CHARACTER: "     + character,
        "DREAM/TOPIC: "   + submission.dreamText,
        "VARIABLES: "     + toJSON(submission.variables)
    )

    # 4 · Assemble the full prompt (order matters)
    fullPrompt = systemPrompt      + "\n\n"
               + characterCard     + "\n\n"
               + formatModule      + "\n\n"
               + "OUTPUT SCHEMA:\n" + outputSchema + "\n\n"
               + "TASK INPUT:\n"    + task

    # 5 · Call the model, validate, retry up to 3x
    for attempt in 1..3:
        raw    = LLM.call(prompt=fullPrompt, response_format="json",
                          temperature=0.5)
        result = tryParseJSON(raw)
        if result == null:            continue      # invalid JSON → retry
        if not validate(result, format, character): continue   # failed checks → retry
        goto ok
    # all attempts failed:
    writeScriptRow(submission, status="needs_review", flagForHuman=true,
                   reviewerNotes="engine failed validation 3x — human draft needed")
    return

    ok:
    # 6 · Safety double-check (defense in depth — engine may still raise it)
    if result.safety_flag == true:
        setSubmission(submission, status="care_queue", safetyFlag=true)
        notifyHuman(); return

    # 7 · File the script for Human Gate 1
    writeScriptRow(submission, character, format,
                   scriptJSON=result, status="needs_review", version=1)
    logCost(attempt, tokensUsed)
```

---

## Validation

```
function validate(result, format, character):
    # structural
    assert result is valid JSON matching output-schema.md
    assert result.character in ["nan_sybil","maeve","jesse"]  OR  == "family"
    assert result.format   in ["hero_dream_short","validation_moment",
                               "fireside_tale","dream_of_the_week","multi_character"]

    # voice integrity
    if format == "multi_character":
        assert every script_lines[].speaker in ["nan_sybil","maeve","jesse"]
    else:
        assert every script_lines[].speaker == character   # no wrong voice

    # brand rules
    assert no BANNED_WORDS in any script_lines[].text, hook, or cta
        # BANNED_WORDS from system-prompt (wellbeing, journey, subscribe, ...)
    assert hedged language present where a symbol/card/palm is used
        # look for "some say" / "the old" style; require disclaimer_line non-null
    assert script ends on the character's closing ritual + dream invitation
        (unless format == validation_moment, where invitation is optional)

    # length (soft)
    warn if spokenWordCount(result) outside the format's target range

    return all_hard_checks_pass
```

---

## Helpers & notes

```
rotateCharacter():
    # round-robin so no character dominates; store a counter in Airtable
    # or derive from submission index. nan → maeve → jesse → nan ...

loadCodeBlock(path):
    # read the fenced ``` block from the module .md; cache it; bust cache
    # when the file changes (so a prompt edit propagates on next run)

BANNED_WORDS = [ wellbeing, journey, self-care, "your energy", content,
                 subscribe, guys, hey, manifest, vibe ]
```

- **Temperature ~0.5:** enough warmth/variation to avoid robotic sameness,
  low enough to obey structure. Tune per model.
- **JSON mode / structured output:** use the model's native JSON mode so
  parsing is reliable; the schema is still validated in code (never trust the
  model blindly).
- **Idempotency:** key each generation to `submission.id + version` so a
  re-run never double-creates a Script row or double-charges the LLM.
- **Everything lands at `needs_review`** — Human Gate 1. Nothing auto-advances
  to voice until the Creative Director approves.
- **Cost + token logging** on every call, for margins and diligence.
```
