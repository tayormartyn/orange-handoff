# Output Schema — the JSON contract

> The engine returns **only** this JSON object. It is what makes the whole
> thing automatable: n8n validates against it, files it in Airtable, and
> hands clean fields to the voice/video tools (Step C).

```json
{
  "character": "nan_sybil | maeve | jesse",
  "format": "hero_dream_short | validation_moment | fireside_tale | dream_of_the_week | multi_character",
  "title": "internal working title (not shown publicly)",
  "hook": "the first 1–2 seconds, spoken",
  "beats": ["one short line per structural beat, in order"],
  "script_lines": [
    {
      "speaker": "nan_sybil | maeve | jesse",
      "text": "the exact spoken words, written for the breath (ellipses = pauses)",
      "delivery_note": "tone / pause / small action for the render"
    }
  ],
  "cta": "the closing invitation, spoken",
  "on_screen_caption": "short burned-in caption (muted-viewer hook)",
  "disclaimer_line": "e.g. 'a mirror, not a warning' where symbols are used, else null",
  "safety_flag": false,
  "safety_response": null,
  "hashtags": ["#dreammeaning", "..."],
  "notes_for_editor": "palette + mannerism + light cues for HeyGen/Higgsfield"
}
```

## Validation rules (enforced in n8n)

- `character` and `format` must be from the allowed enums above.
- If `safety_flag` is `true`: `script_lines` may be empty, `safety_response`
  must be non-null, and the item is routed away from video generation.
- `script_lines[].speaker` must match `character` — except in
  `multi_character`, where multiple speakers are allowed.
- Total spoken words should fit the format's target length (see each
  format module).
- Reject and regenerate if any banned word appears or the JSON is invalid.
