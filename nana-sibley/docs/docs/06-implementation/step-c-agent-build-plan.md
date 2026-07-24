# Step C — Implementation & Agent Build Plan

*Sybil's Hearth · how the machine gets built (and who builds it) · v1.0*

---

## The honest principle up front

You want to do zero technical work and let AI agents build and run the
machine. Here's the truthful version of that, because it's the one that
actually gets you to launch:

**AI agents can do the heavy lifting of *building* — but a human has to hold
the keys, the card, and the judgement.** An agent can write an n8n workflow;
it cannot sign up for HeyGen with your bank card, pass YouTube's API review,
give legal consent to clone a voice, or decide whether a grieving person's
dream is safe to publish. Those are human acts by design.

So the real split is:

- **You** = Creative Director & the soul. You never debug. You keep the taste
  and the heart gate. (That's not "technical work" — it's the one job only you
  can do.)
- **A coding agent** (Claude Code, or a specialised dev agent) = the builder.
  It writes ~80–90% of the config and glue from this repo as its spec.
- **One human operator** (your co-founder with the infra track record, or a
  contract dev for a week or two) = holds credentials, money, and platform
  approvals; supervises the agent; does first-render QA.

That's not a failure of the dream — it's what "bulletproof" actually requires.
A pipeline that handles vulnerable people's words and real money should never
be fully unsupervised. Build it so *you* touch only the soul, and a trusted
human owns the plumbing.

---

## Part 1 — The Agent Labour Force

### What the coding agent can genuinely do (the ~85%)

Hand it this repository as the spec, and a capable agent will:

- **Configure the Airtable ledger** — create the base, all six tables, fields,
  views, and the `status` state-machine, from the schema in
  `docs/05-automation`. (Via the Airtable API or scripted setup.)
- **Write the n8n workflows** — scaffold W1–W8 as importable JSON: the intake
  webhook, the prompt-assembly node (System + Character + Format + Task), the
  LLM call, JSON-schema validation, the ElevenLabs / HeyGen / Higgsfield API
  calls, the poll/webhook loops, and the Airtable writes.
- **Write the glue code** — the prompt assembler, the output-schema validator,
  banned-word and safety pre-screens, retry/backoff, idempotency guards, cost
  logging.
- **Write tests and docs** — so the pipeline is verifiable and handover-ready.

### What still needs the human operator (the ~15% that can't be skipped)

- Creating accounts and entering billing for every tool.
- Generating and safely storing API keys and secrets.
- OAuth / app approval for publishing (YouTube Data API, TikTok content API —
  these need real applications and review time).
- **Voice consent** (see Part 2 — a legal act no agent can perform).
- First-render QA and the taste calibration of the aesthetic.
- Owning the monthly cost and the safety/moderation decisions.

### How to actually run the agent build

1. Give the agent the repo and this instruction: *"Build the Sybil's Hearth
   pipeline exactly to this spec. Start with the Airtable base and workflows
   W1–W3 only. Stop for review before anything touches a paid API."*
2. The human operator plugs in credentials in a sandbox and tests W1–W3 on
   one dummy dream.
3. Iterate workflow by workflow. Never let the agent wire live publishing or
   live billing without a human approving that step.
4. Keep every workflow the agent writes in the repo (version-controlled), so
   the "brain" stays legible for the eventual buyer.

> **Reality check on "it builds itself":** agents will compress weeks of dev
> into days, and that's genuinely powerful. But budget for a human operator
> across the build and for ongoing supervision. "90% automated" is true for
> the *code*; it is not true for *accountability*.

---

## Part 2 — The Aesthetic Stack (no slop, second-to-none)

The difference between "premium" and "AI-slop" is not the tool. It's
**consistency + restraint + a human taste gate.** The stack:

### Nan Sybil — the face
- **HeyGen** for her realistic, continuous lip-synced talking head. Lock one
  approved avatar and never regenerate the face. Keep videos tight (10–12 min
  max for premium, seconds for shorts — not 30 min; see the Funnel doc).
- Warm firelight, soft focus, the same framing every time. The cosiness hides
  the "AI sheen"; harsh flat light exposes it.

### The twins — the cinematic vibe
- **Higgsfield (Cinema Studio)** for atmospheric, character-driven motion and
  camera movement, and/or **Runway (Gen-4)** for its world/character
  consistency features. Test both on the twins and pick per-shot.
- **The hard part is consistency across shots** — all these tools drift. The
  fix is process, not hope: locked reference images per twin, fixed seeds
  where supported, a written "look doc" (wardrobe, palette, light) pasted into
  every generation, and a human eye rejecting any off-model frame.

### The voices — and an important legal correction
You asked about cloning Nan's voice to capture her breathing and stillness.
Here's the current rule, because it changes the plan:

- **ElevenLabs only lets you make a Professional Voice Clone of *your own*
  verified voice.** You cannot clone someone else's voice — *even with their
  consent* — directly. If another person wants their voice used, *they* must
  create and verify their own clone on their own account and share it with
  you.
- **So Nan's voice should be either:** (a) a designed/library voice tuned to
  her character, or (b) a **cast voice actor** who records her, creates and
  verifies *their own* clone, and shares it to your account under a clear
  written agreement. Do not plan on cloning a real person's voice (a late
  relative, a celebrity) — it's both against the tool's rules and ethically
  fraught.
- **Crucially: the stillness does not come from cloning.** Cloning captures
  *timbre*. Her heavy pauses and breath come from the **prosody scripting** in
  `prompts/character-modules/nan-sybil-presence-and-stillness.md` + the
  settings there (stability ~70–75% for the still passages, punctuation as the
  breath-score, `<break>` tags sparingly). Whatever voice you choose, that
  spec is what makes it *her*.

### The anti-slop checklist (the human gate enforces this)
Locked faces · warm light + soft focus · the three-take rule for voice · warm
serif / handwritten captions · minimal cuts and real stillness · consistent
intro glow + fire-crackle ambience · and a human rejecting anything that
feels "off." Restraint is the aesthetic.

---

## Part 3 — Your Zero-Friction Daily Workflow

The honest reframe: you do **zero technical work** — no code, no pipes, no
debugging, ever. But you stay the **taste-and-heart gate**, because that is
the creative-director role you want, and it's the moat. It takes minutes, not
hours.

**A typical day, once built:**

1. Open Airtable (or a phone-friendly interface the agent builds on top).
2. See the queue of **draft scripts** the engine generated overnight.
3. Read them — your ear on the "turn" beat. Approve, or tweak a line, or
   reject. *(This is the whole job. 10–20 minutes.)*
4. Glance at the **finished videos** waiting in the second queue; approve to
   schedule. The automation renders, captions, and posts the rest.
5. Once a week, pick the **Dream of the Week** to feature.

Everything else — assembly, captioning, posting, filing, analytics — runs
without you. Anything with a `safety_flag` is pulled out of the automation and
put in front of a human, never auto-published.

> **At launch, lean in a little more** (review every script) — that's how the
> engine earns your trust and how the soul stays pure. As it proves itself,
> move to spot-checking. But never go fully hands-off on the safety queue.
> That one stays human forever.

---

## Part 4 — The Viral Flywheel (toward 100k → 1M)

### The honest truth about the numbers
100k and 1M are earned, not engineered, and most channels — AI or human —
never get there. No one can promise it. What we *can* do is stack the levers
that give you the best odds and let the audience decide. Here they are.

### The flywheel

```
   great hook  ─►  high retention + comments  ─►  algorithm expands reach
        ▲                                                     │
        │                                                     ▼
  more dream submissions  ◄──  "leave your dream / Dream of the Week"  ◄─┘
        │
        ▼
   more content ideas + a returning weekly audience  ─►  (loop tightens)
```

The **Dream of the Week comment loop** is the engine: every video asks for a
dream, comments spike, the algorithm expands reach, more dreams come in, one
is featured, people return to see if it's theirs — and every submission is a
pre-validated future topic. It feeds itself.

### The levers that scale it

1. **One hero format, obsessively consistent** until the algorithm knows
   exactly who to show you (Growth Engine doc). Variety comes *after* traction.
2. **Win the first 3 seconds** every time; run the weekly best/worst hook
   review. Hooks are 80% of reach.
3. **Curate the Dream of the Week — don't mass auto-reply.** Auto-scraping
   comments and blasting AI replies trips spam detection and feels less human.
   Curate a few, beautifully. Quality of the loop > volume of the loop.
4. **Cross-post one clean asset** to YouTube Shorts, TikTok, Reels. TikTok for
   cold-start discovery; YouTube for durable search and the money.
5. **Double down on winners** — when a topic/character over-performs, make
   more like it immediately.
6. **The twins' contrast reveal** (Nan introduces them) as a growth event once
   Nan has a loyal core.
7. **The audience makes your content** — every submitted dream is fuel, so
   growth and content-supply rise together.

### Milestone gates (prove before you spend)
- **First 1k:** does the format hold retention? Is the comment loop alive?
- **10k:** which 2–3 topics/characters win? Is weekly return happening?
- **100k:** is the funnel converting *without* hurting trust? Only now
  consider paid amplification.

Don't buy scale before the organic loop is proven. A flywheel that isn't
spinning on its own won't spin faster with money poured on it.

---

## The bottom line

Agents build the machine; a trusted human owns the credentials, the money, and
the safety; you stay the soul and never touch the code; and the audience — not
the plan — decides the numbers. Build the MVP semi-manually, prove the loop
with real videos, then let the agents automate under you, one workflow at a
time.

That's how this gets to bulletproof: not by removing the humans from the
loop, but by putting each human exactly where only a human can stand.

---

*Sources for the tooling facts: ElevenLabs Help — Professional Voice Cloning
(own-voice-only rule); Runway Gen-4 (world/character consistency); Higgsfield
(cinematic motion). Confirm current pricing/limits with each vendor before you
commit spend.*
