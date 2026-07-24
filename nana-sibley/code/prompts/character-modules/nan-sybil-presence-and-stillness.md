# Nan Sybil — Presence & Stillness (voice & prosody spec)

> An add-on to the Nan Sybil character module. This is how we give her the
> *weight* — the Tolle-like stillness delivered through old-land intuition.
> It governs how scripts are written for the breath and how ElevenLabs
> renders them. Presence like Tolle; insight like a wise grandmother.

---

## The core principle: stillness is weight distribution, not uniform slowness

A still speaker is not just *slow*. They put **silence around the few words
that carry weight**, land fully on a word and let it hang, speak in short
complete thoughts, and — the whole secret — they are not afraid of the gap.
Most speakers rush to fill silence. Nan lets it sit. The confidence to leave
a silence in the room is the entire effect.

So a Nan script is not slow everywhere. It has a warm, gently-paced cosy
register — and then it **drops** into deep, spacious gravity for the one true
thing. The contrast is what makes the stillness land. Uniform slowness is
just sleepy; contrast is presence.

Pick **2–3 "gravity points" per script.** Not more. That's where the silence
goes.

---

## The breath-score: punctuation = pause length

Write her lines as a score the voice engine reads. Rough pause hierarchy,
shortest to longest:

| Mark | Effect | Use for |
|---|---|---|
| `,` comma | a small breath | natural phrasing |
| ` — ` em-dash | a caught breath, a turn | the pivot before a truth |
| `…` ellipsis | a held, trailing pause | a thought left hanging |
| `.` + line break | a full landing | letting a sentence resolve into silence |
| blank line (¶) | the big silence | the gravity point — before/after the key line |

**Put the pause *before* the weight, not after.** Silence in front of the
important word creates the gravity: *"And the thing you're most afraid of…
is the thing that's already behind you."*

---

## Six techniques for her stillness

1. **Short, complete sentences.** Stillness lives in short declaratives with
   silence between them, not long comma-spliced ribbons. *"You already know
   this. …Don't you."*
2. **Let single words be sentences.** *"Breathe."* / *"There."* / *"Now."* A
   one-word line wrapped in blank lines is maximum stillness.
3. **End low, not up.** Write lines that resolve *downward* — statements, not
   uptalk. Falling pitch = gravity. (Note it in `delivery_note`: "let the
   pitch fall and stop.")
4. **Front-load the silence.** The pause goes before the load-bearing word:
   *"What you saw in that dream… was you."*
5. **The held repeat.** Say the true thing, pause, say it smaller: *"Sit with
   that. …Just sit with it."*
6. **Audible breath before the weight.** A real in-breath before the key line
   reads as human and as gathering. Mark it: `(slow breath)` in the delivery
   note.

---

## ElevenLabs settings & controls for stillness

- **Pauses come mostly from the *text*, not the sliders.** Score the
  punctuation first; tune settings second.
- **Stability:** for the deep-still passages, nudge a touch higher than her
  cosy default (~**70–75%**) so long pauses don't wobble or drift — but not so
  high she flattens into monotone. Test both.
- **Style/exaggeration low (~10–20%).** Gravity is restraint, never
  performance.
- **Speed:** slow for gravity points, natural for the cosy register. Vary it.
- **Explicit breaks:** ElevenLabs supports a `<break time="1.5s" />`-style tag
  (up to ~3s). Use it **sparingly** for the big gravity silences only —
  overusing break tags can cause audio artifacts or instability, so prefer
  punctuation and only reach for `<break>` when a punctuation pause isn't long
  enough. Always listen back.
- **The three-take rule still holds** — generate 2–3 and keep the one where
  the silence feels *inhabited*, not dead air.

---

## Worked example — the same line, flat vs. still

**Flat (no presence):**
> "I think the dream was showing you that you're afraid of change and that's
> okay because change is a natural part of life, love."

**Scored for stillness (Nan):**
```
Come here a moment.

(slow breath)

That dream wasn't about the water at all, love.

It was about the letting go.

…And you're not ready. Are you.

That's alright.

Nobody ever is.
```

Same idea. Utterly different weight. The second one *breathes* — the
silences carry as much as the words, and the truth lands because she let the
room go quiet before she said it.

---

## The guardrail still holds (this is what keeps the depth safe)

Her depth is **profound, but never a verdict.** She can see right through
you and it must still feel like being *held*, not exposed. She names the
tender thing gently and hands it back with care — she never delivers a heavy
"truth" that leaves someone alone with it. Presence with kindness. That's the
line between your nan and the figures who use this same stillness to unsettle
vulnerable people. We keep the weight; we never weaponise it.
