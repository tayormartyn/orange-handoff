# NANA SYBIL'S HEARTH — Master Brief

*The single "read this first" handover. Everything the project is, wants to be,
and where it stands right now. Give this to any model or collaborator to bring
them fully up to speed. · v1.0*

---

## 1. What this is, in one paragraph

**Nana Sybil's Hearth** is a warm, AI-crafted storytelling brand: a wise
grandmother, Nana Sybil, who sits by a crackling fire, reads people's dreams,
tells old folklore, and offers a moment of comfort before sleep. She's rooted
in a **real family tradition of dream-lore** (the founder Martyn's Romani
Traveller grandparents, and his Irish mother's gift for reading dreams), brought
to life with AI — with a real person behind every reading. The brand publishes
short daily videos across YouTube, TikTok, Instagram and Facebook, built around
one engine: **make a stranger feel deeply seen, and invite them to leave a dream.**

## 2. The vision & the goal

- **Near-term:** grow a warm, trusting audience with short-form dream/comfort
  videos. Build the community first.
- **Long-term (the endgame):** an honest, high-margin business selling
  **personalised dream reflections** (see §9) — but only *after* trust is built.
  We never sell early. Ambition: a channel doing millions of views across
  platforms, and a sellable IP asset that doesn't depend on a real person's face.
- **The through-line:** everything is measured against one standard —
  *"does this give a stranger what a good nan gave her grandchild?"* (comfort,
  insight, a bit of strength). See `THE-HEART.md`.

## 3. RULE ZERO (the two hard rules — never broken)

1. **Honest-AI.** The characters are openly AI-crafted; we never claim they're
   real living people. AI-content disclosure is ON for every upload on every
   platform. (Required by the platforms, and it's what makes the brand saleable.)
2. **Reflection, not therapy.** Everything is comfort and reflective
   entertainment — never therapy, counselling, diagnosis, treatment, or
   fortune-telling. Dreams are framed as *mirrors* ("some say…"), never verdicts.
   A distressed submission is never used as content — it's routed to a warm
   signpost toward real support. **Care before content, always.**

These two rules protect vulnerable viewers AND keep the brand legally
defensible and buyable. They are non-negotiable.

## 4. The characters

- **Nana Sybil** — the heart. A warm, weathered, dignified Romani Traveller
  grandmother by the fire. Kind because she's known hard winters, not because
  she's naïve. Three layers always present: **warmth + quiet wisdom + a little
  dry mischief.** Her face and voice are **locked** (a fixed reference image;
  a designed ElevenLabs voice tuned for stillness). Full profile:
  `docs/01-characters/nan-sybil-playbook.md`.
- **Maeve & Jesse** — the twins (grandchildren), designed but **held back** for
  now. Maeve = intuitive/emotional; Jesse = grounded/practical. She'll introduce
  them once she's established. `docs/01-characters/maeve-and-jesse-twins-playbook.md`.
- **Consistency is sacred:** the face is locked (re-use the reference image in
  the image tool every time); the voice is locked (fixed ElevenLabs settings).

## 5. The content engine

- **Format:** vertical short (~35–45s), Nan by the fire, one dream/topic.
- **The beat sheet:** Hook (name the dream in the first 2s) → the old meaning
  ("some say…", hedged) → the turn (one gentle reflective question) → comfort
  (a warm gravity-point line) → the invite (the CTA).
- **The locked CTA:** *"Drop your dream in the comments, my darling — I read
  them here, by the fire. The kettle's on. …I'll be here."*
- **Voice/breath:** scripts are written *for the breath* — ellipses = held
  pauses, line breaks = landings, silence *before* the key word, 2–3 "gravity
  points" per script. ElevenLabs settings: stability ~68, style ~18, speed ~0.93.
- **Portable "Nan lock" prompt** (paste into any AI to write on-voice):
  `prompts/nan-sybil-master-prompt.md`.

## 6. Distribution — hard-won lessons

- **Post from the PHONE app** (esp. TikTok). Desktop/web uploads got throttled
  to zero; the same clip from the phone got views. This was the key unlock.
- **No VPN** when posting — a VPN throttled the fresh TikTok account to zero.
- **Same clean clip → all platforms** (YouTube Shorts, TikTok, Instagram Reels,
  Facebook Reels). AI label on each. TikTok = fastest cold-start; **Facebook's
  older audience may be a strong fit** for grandmother content.
- **Niche hashtags, not generic** (skip #fyp/#viral). Full copy + hashtag bank:
  `publishing-pack.md`.

## 7. WHERE WE ARE RIGHT NOW (status + data)

- **Live** on YouTube, TikTok, Instagram, Facebook as *Nana Sybil's Hearth /
  @NanaSybil*. Several short episodes published; more voiced and rendering.
- **First data (days 1–4):** the loved-one/grief dream video pulled ~**150 →
  350 views on TikTok**; **first followers and first comments** across TikTok,
  Facebook, Instagram. Numbers are small but **trending up**, and real humans are
  engaging. This is a normal, healthy early start.
- **Honest read:** the 350 is confounded (topic vs the phone-upload fix), so we
  don't yet know the winning topic. We're in the **discovery phase** — testing
  different dream topics, all phone-uploaded, reading which pull best.
- **Founder context:** solo operator, doing this alongside other work and life
  stress. Cadence must stay **sustainable** — daily if possible, ~5/week if not.

## 8. The growth plan — 3 phases with triggers

- **Phase 1 (NOW → next few weeks): the discovery grind.** Daily shorts, all
  platforms, phone-upload, test topics, reply to every comment, find the 2–3
  winning topics. *Advance when: comments flowing + a few hundred–1k followers.*
- **Phase 2: add Dream of the Week.** Weekly, read a real submitted dream (needs
  real comments to exist first). Keep daily shorts as the engine underneath.
  *Advance when: a few thousand followers, consistent views.*
- **Phase 3: long-form + the funnel.** 10–30 min "fall asleep to Nan" videos on
  YouTube (better watch-time + monetisation), and switch on the website/email
  list and gentle products. *Move up on DATA, never on boredom.*

## 9. The monetization endgame (FOR LATER — kept dark)

A value ladder, opened only once trust is real (see `docs/03-business/`):
- Free content → a small tripwire reading → a **£19 "Bespoke Dream Translation"**
  → a monthly "Hearth-side Letter" subscription → a premium video tier.
- Stress-tested economics and honest guardrails are already documented. The
  website has the shop as an *"opening soon"* preview only; the Stripe/AI
  architecture is scaffolded but dark (`website/DREAM-BOOK-architecture.md`).
- **The rule:** every paid reading carries the safety net (distress → refund +
  support, never upsold) and the reflection-not-therapy framing.

## 10. The tech / pipeline (built, mostly for later scale)

- **Scripting engine** (modular, layered): system prompt + character module +
  format module + task → validated JSON script. Safety classifier runs first.
  `docs/04-engine/`, `prompts/`.
- **Self-contained pipeline & voice worker** (Python, no server needed):
  `build/hearth_pipeline.py`, `build/hearth_voice_worker.py`.
- **Automation blueprint** (n8n + Airtable) + importable scaffolds for scale:
  `docs/05-automation/`, `build/`.
- **Website:** bright cottage-garden landing page with email capture, ready to
  host: `website/nana-sybil-hearth.html`.
- *Current reality:* videos are made semi-manually (ElevenLabs → HeyGen →
  CapCut → post). The heavy automation is for when volume justifies it.

## 11. Repo index — the full map

```
THE-HEART.md ............... read first: who she really is (the soul)
README.md ................. repo guide + Rule Zero
MASTER-BRIEF.md ........... this file (the onboarding brief)
publishing-pack.md ........ titles/descriptions/captions/pinned/hashtags (per platform)

docs/
  00-foundation/brand-and-character-bible.md
  01-characters/nan-sybil-playbook.md
  01-characters/maeve-and-jesse-twins-playbook.md
  02-growth/channel-growth-engine.md
  03-business/revenue-funnel.md ............ the money plan (honest math)
  04-engine/scripting-prompt-engine-brief.md
  05-automation/automation-architecture.md
  06-implementation/  ...... launch plan, first-video playbook, agent build brief, episode-01
  examples/  ............... 3 worked multi-character scripts (light/dark/grief)

prompts/  .................. the working engine
  system-prompt.md · safety-layer.md · w1-safety-classifier.md · output-schema.md
  review-checklist.md · nan-sybil-master-prompt.md  (portable "Nan lock")
  character-modules/  ...... nan-sybil (+ presence-and-stillness, voice-design), maeve, jesse
  format-modules/  ......... hero-dream-short, validation-moment, fireside-tale,
                             dream-of-the-week, multi-character

build/  .................... runnable code + scaffolds
  hearth_pipeline.py · hearth_voice.py · hearth_voice_worker.py · setup_airtable.py
  n8n-w1-dream-intake.json · n8n-w2-script-generation.json
  dry-run-01.md · live-test-kit.md · RUN.md · README-import.md

website/  .................. nana-sybil-hearth.html (live-ready) · index.html (template)
                             DREAM-BOOK-architecture.md (shop, for later)
```

## 12. How to use this pack (for another model)

If you're a model being handed this: **read `THE-HEART.md` and this brief
first.** Hold **Rule Zero** above everything. The immediate job is **Phase 1** —
help write sharper hooks and on-voice scripts (use `nan-sybil-master-prompt.md`),
propose dream topics to test, and help read the platform data to find the
winning topics. Do **not** push monetisation or long-form yet — those are gated
on trust and audience. Keep her warm, keep her honest, and keep the founder's
pace sustainable.

*The whole thing in one line: a real family's dream-lore, carried by an
honestly-AI grandmother, grown patiently on short-form, to one day sell comfort
the right way.*
