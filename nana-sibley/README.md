# nana-sibley (Nana Sybil's Hearth) — sanitized handoff package

Assembled 2026-07-24, LOCAL ONLY (no remote). Source of truth:
`C:\Users\Marty\Downloads\Sybils_Hearth_Repo.zip` (repo snapshot; spelling on
disk varies: Sybil / Sybal / cybal / "Sibley").

Nana Sybil's Hearth is a character-driven storytelling/YouTube project: an AI
"Nan Sybil" grandmother character (plus twins Maeve and Jesse) who turns
viewer-submitted dreams into fireside stories, with an automated
script-generation and voice pipeline.

## Package layout
- `code/build/` — the pipeline: `hearth_pipeline.py` (Anthropic script
  generation), `hearth_voice.py` + `hearth_voice_worker.py` (ElevenLabs voice),
  `setup_airtable.py` (dream-intake base), two n8n workflow exports
  (`n8n-w1-dream-intake.json`, `n8n-w2-script-generation.json`), RUN.md,
  README-import.md, live-test-kit.md, dry-run-01.md.
- `code/prompts/` — the prompt engine: master prompt, system prompt, safety
  layer + W1 safety classifier, output schema, character modules (Nan Sybil,
  voice design, presence-and-stillness, Maeve, Jesse), format modules
  (fireside tale, dream-of-the-week, hero-dream-short, validation moment,
  multi-character), review checklist.
- `configs/env.template` — every env var the pipeline expects, values stripped
  (`# set in Windows Credential Manager / DPAPI`). The secret scan found NO
  real secrets in the repo: all code reads env vars; docs contain only
  placeholders like "sk-ant-...".
- `docs/` — MASTER-BRIEF, THE-HEART (character soul document), publishing
  pack, DREAM-BOOK website architecture, plus the full `docs/` tree
  (brand/character bible, character playbooks, growth engine, revenue funnel,
  automation architecture, implementation plans).
- `sample-content/` — three example stories (`story-examples/`), the finished
  `episode-01-final.md`, and the two website HTML files (`index.html`,
  `nana-sybil-hearth.html`).

## Published/asset media (NOT staged — large media)
Episode videos, voice MP3s, character images and banners live in
`C:\Users\Marty\Downloads\` (e.g. "Nana episode 1.mp4", ElevenLabs episode
MP3s, "Nana v3 final.jpg"). They are finished renders, not code — pull them
from Downloads if the receiving agent needs them.

## Notes for the receiving agent
- No scheduled tasks, no running services, no live infrastructure on the
  source machine for this project (pipeline runs on demand; n8n workflows are
  import files, not a deployed instance).
- Secrets policy matches the ORANGE package: provision keys via Windows
  Credential Manager / DPAPI, never commit them.
