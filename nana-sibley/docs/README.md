# Sybil's Hearth — Master Repository

The single source of truth for the Sybil's Hearth brand: an **openly
AI-crafted** storytelling world of folklore, dreams and reflection, with a
real person behind every reading. Modular by design, so any part can be
updated, tested, or handed over cleanly.

> **Read [`THE-HEART.md`](THE-HEART.md) first.** Before any strategy or code —
> it's who Nan Sybil really is and where she came from. Everything else is
> just craft in service of that page.

## Rule Zero (the foundation everything rests on)

1. **Honest-AI.** The characters are openly AI-crafted; we never claim they
   are real living people. (Required by YouTube/TikTok disclosure rules and
   what makes the brand a saleable asset.)
2. **Reflection, not therapy.** Everything is reflective entertainment and
   self-insight — never diagnosis, treatment, or a claim to replace a
   professional. Distress is always routed to real support.

## Repository map

```
sybils-hearth/
├── README.md                         ← you are here
├── docs/                             ← the reference playbooks (human-facing)
│   ├── 00-foundation/
│   │   └── brand-and-character-bible.md
│   ├── 01-characters/
│   │   ├── nan-sybil-playbook.md
│   │   └── maeve-and-jesse-twins-playbook.md
│   ├── 02-growth/
│   │   └── channel-growth-engine.md
│   ├── 03-business/
│   │   └── revenue-funnel.md
│   ├── 04-engine/
│   │   └── scripting-prompt-engine-brief.md   ← Step B (how the engine works)
│   └── 05-automation/
│       └── automation-architecture.md         ← Step C · Doc 4 (the engine room)
└── prompts/                          ← the working engine (machine-facing)
    ├── system-prompt.md              ← Layer 1 · the constitution
    ├── safety-layer.md               ← the distress protocol (care first)
    ├── output-schema.md              ← the JSON contract
    ├── review-checklist.md           ← the human quality gate
    ├── character-modules/            ← Layer 2 · one injected per job
    │   ├── nan-sybil.md
    │   ├── maeve.md
    │   └── jesse.md
    └── format-modules/               ← Layer 3 · one injected per job
        ├── hero-dream-short.md
        ├── validation-moment.md
        ├── fireside-tale.md
        ├── dream-of-the-week.md
        └── multi-character.md
```

## How a script gets made (the four layers)

`system-prompt` + one `character-module` + one `format-module` + the task
input (a dream/topic) → the model returns JSON matching `output-schema` →
n8n validates it, files it in Airtable, and (Step C) splits the fields out
to ElevenLabs / HeyGen / Higgsfield.

Read `docs/04-engine/scripting-prompt-engine-brief.md` for the full picture.

## Build order (roadmap)

- [x] Doc 1 — Brand & Character Bible
- [x] Doc 2 — Channel Growth Engine (+ first 20 Shorts)
- [x] Doc 3 — Revenue Funnel (stress-tested)
- [x] Nan Sybil playbook · Maeve & Jesse playbook
- [x] **Step B — Scripting Prompt Engine** (this repo's `prompts/`)
- [x] **Step C — Document 4: Automation Architecture** (`docs/05-automation/`)

The blueprint is now complete end to end. From here it's implementation:
stand up the Airtable base, wire workflows W1–W3, and draft the first 20
Shorts through the engine (build in phases — see the architecture doc §7).

## Notes

- `docs/` files are converted from the master Word documents for reference;
  the `prompts/` files are hand-authored working modules — treat those as
  canonical for generation.
- Folklore stays generic old-country; never tied to real Traveller/Roma
  ethnicity.
- Version each prompt module deliberately — a change propagates to every
  future script.
