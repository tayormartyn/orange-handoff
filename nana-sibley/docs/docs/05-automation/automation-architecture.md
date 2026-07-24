# Document 4 — The Automation Architecture (Step C)

*Sybil's Hearth · the engine room · v1.0*

---

## What this is

This is the wiring that takes a dream (a submission or a topic) and carries
it all the way to a published, on-model video and a filed record — with the
scripting engine (Step B) at its heart and **two human gates** protecting the
soul and the safety of the brand.

The guiding principle is the opposite of "lights-out automation." We
automate the *labour* (rendering, filing, formatting, scheduling) and keep a
human on the *soul* (the "turn" beat) and the *safety* (distress). That
balance is what lets this scale without going hollow — and it's what a buyer
wants to see in due diligence.

---

## 1. The pipeline, end to end

```
  ┌────────────────┐
  │  DREAM INTAKE  │  submission form  ·  pinned-comment prompt
  └───────┬────────┘
          ▼
  [Airtable · Submissions]  status: new
          ▼
  ┌──────────────────────────────┐
  │ n8n W1 · SAFETY PRE-SCREEN    │  distress? ── yes ──► Care Queue (human)
  └───────┬──────────────────────┘                         (no video ever)
          ▼ no
  ┌──────────────────────────────┐
  │ n8n W2 · SCRIPT GENERATION    │  assemble  System + Character + Format
  │  (the Step B engine)          │  + Task  → LLM → validate JSON vs schema
  └───────┬──────────────────────┘
          ▼
  [Airtable · Scripts]  status: needs_review
          ▼
  ┌──────────────────────────────┐
  │ ★ HUMAN GATE 1 · SCRIPT       │  your ear on the "turn" beat
  └───────┬──────────────────────┘
          ▼ approved
  ┌──────────────────────────────┐
  │ n8n W3 · VOICE  (ElevenLabs)  │  one locked voice per speaker tag
  └───────┬──────────────────────┘
          ▼
  ┌──────────────────────────────┐
  │ n8n W4 · VIDEO  (route by     │  Nan ─► HeyGen (talking head)
  │  character)                   │  Twins ─► Higgsfield (cinematic)
  └───────┬──────────────────────┘  (async: submit → poll/webhook → store)
          ▼
  ┌──────────────────────────────┐
  │ n8n W5 · ASSEMBLE + CAPTION   │  stitch, burn captions, intro/outro
  └───────┬──────────────────────┘
          ▼
  ┌──────────────────────────────┐
  │ ★ HUMAN GATE 2 · FINAL VIDEO  │  quick tone + truth pass
  └───────┬──────────────────────┘
          ▼ approved
  ┌──────────────────────────────┐
  │ n8n W7 · SCHEDULE + PUBLISH   │  set AI-disclosure label · post
  └───────┬──────────────────────┘
          ▼
  [Airtable · Videos]  status: published  ──►  analytics loop back in
```

Everything hangs off Airtable as the single source of truth; n8n is the set
of workers that move an item from one status to the next.

---

## 2. The stack (and why each piece)

| Layer | Tool | Job |
|---|---|---|
| **Ledger / DB** | **Airtable** — the "Hearthside Ledger" | Single source of truth: every submission, script, asset, video, schedule row, and (later) subscriber. |
| **Orchestrator** | **n8n** | The workflows that move items between statuses and call every API. Self-hostable, visual, cheap. |
| **Brain** | **LLM API** (the Step B engine) | Assembles the 4-layer prompt and returns validated JSON scripts. |
| **Voice** | **ElevenLabs** | The three locked character voices, one per `speaker` tag. |
| **Nan video** | **HeyGen** | Long-form, continuous lip-synced talking head. |
| **Twins video** | **Higgsfield** (Cinema Studio) | Cinematic short-form + B-roll with character consistency. |
| **Assembly** | An assembly API (e.g. Creatomate / Shotstack) *or* a human editor at launch | Stitch clips, burn captions, add intro/outro. |
| **Publish** | Platform APIs or a scheduler (Metricool/Buffer) | Post + set the AI-disclosure label. Manual at launch. |
| **Funnel (later)** | **Stripe** + a print-on-demand mail API | Payments and physical fulfilment — wired only when the funnel goes live. |

---

## 3. The Airtable ledger (schema)

Six core tables (plus two that come online with the funnel):

**Submissions** — every dream that comes in.
`id · source · raw_dream_text · submitter_handle · consent (bool) · safety_flag (bool) · status (new / screened / scripted / care_queue) · created_at`

**Scripts** — one row per generated script.
`id · submission (link) · character · format · script_json · safety_flag · status (needs_review / approved / rejected) · reviewer_notes · version`

**Assets** — every audio/video artefact.
`id · script (link) · type (audio / video / final) · speaker · tool · file_url · render_cost · status`

**Videos** — the publishable unit.
`id · script (link) · final_asset (link) · platform · publish_at · published_url · ai_label_set (bool) · status (scheduled / published) · retention · comment_rate`

**Schedule** — a calendar *view* of Videos, so the content pipeline is visible at a glance.

**Ideas / Backlog** — every submitted dream doubles as a future topic; the running idea bank.

*(Later, with the funnel:* **Subscribers** *and* **Fulfilment** *— orders, binder status, monthly leaves, postage.)*

> The `status` field on each table is the backbone: n8n workflows trigger on
> status changes, and the two human gates are simply "move the card to
> Approved."

---

## 4. The n8n workflows

**W1 · Dream intake + safety pre-screen.** New submission lands (form
webhook, or a pulled/pinned-comment feed) → create Submissions row → run the
safety pre-screen (the `safety-layer` rules). If distress is detected, set
`safety_flag`, move to **Care Queue**, and stop — no script, no video, a
human handles a warm signpost. Otherwise mark `screened`.

**W2 · Script generation (the Step B engine).** Trigger on `screened` →
assemble `system-prompt + character-module + format-module + task input` →
call the LLM → validate the returned JSON against `output-schema` (reject &
retry on invalid or banned words) → write to Scripts as `needs_review`. The
engine re-checks safety and can still raise `safety_flag` here.

**★ Human Gate 1 · Script review.** You read the script — especially the
"turn" beat — in Airtable. Approve → `ready_for_voice`. This is the soul
check; keep it manual at launch.

**W3 · Voice.** Trigger on `approved` → for each `script_lines[].speaker`,
call ElevenLabs with that character's locked voice + settings → store audio
in Assets. (Keep the "warmest of three takes" rule as an optional
generate-3-pick-1 sub-step for hero lines.)

**W4 · Video (routed).** Route by character: **Nan → HeyGen**, **twins →
Higgsfield**. Both are **asynchronous** — submit the job, receive a job id,
then **poll or catch a webhook** until the render is ready, then store the
clip in Assets with its `render_cost`. Respect concurrency limits (HeyGen
allows ~10 concurrent renders) by queuing.

**W5 · Assemble + caption.** Combine audio + video, burn in captions (warm
serif/handwritten), add the shared intro glow and fire-crackle ambience,
export a clean master → Assets (`final`). Use an assembly API, or hand to a
human editor at launch.

**★ Human Gate 2 · Final video.** A quick tone-and-truth pass before
anything publishes. Approve → `scheduled`.

**W7 · Schedule + publish.** At `publish_at`, post to the platform (API or
scheduler) and **set the AI-disclosure label** (Rule Zero — and required by
YouTube/TikTok). Write back `published_url` and `ai_label_set: true`.

**W8 · Analytics loop.** Pull retention + comment-rate back into Videos so
the weekly review (Growth Engine doc, §7) and the idea backlog are
data-fed.

*(Later)* **W9 · Funnel + fulfilment.** Stripe event → generate the PDF /
parchment leaves → print-on-demand mail API → update Fulfilment. Wired only
when the funnel launches.

---

## 5. Safety routing (the highest-priority path)

Distress never reaches automation. W1 screens every submission *before* a
script exists; the engine re-checks in W2; either can set `safety_flag`,
which routes the item to a human **Care Queue** and blocks all voice/video
generation. A warm, non-clinical signpost is sent by a person, never
auto-generated as "content." This path is tested first and monitored
always.

---

## 6. The realities to design around (honest flags)

- **Don't fully automate publishing at launch.** A comfort-and-dreams brand
  lives or dies on feel and safety. Keep both human gates until the engine
  has a long track record; automate the labour, not the judgement.
- **Async renders + rate limits.** HeyGen/Higgsfield are not instant and are
  rate-limited. Build W4 as submit → poll/webhook → store, with a queue and
  a retry/backoff. Budget the ~10% re-render buffer from the Funnel doc —
  failed renders cost real money.
- **Dream intake: prefer a form or pinned-comment prompt over scraping.**
  Auto-scraping comments and mass auto-replying with AI readings can trip
  platform spam/automation limits and feels less human. Curate the
  *Dream of the Week* as crafted content instead of blasting auto-replies —
  it's safer, on-brand, and higher quality.
- **Platform API access takes lead time.** YouTube Data API has quotas;
  TikTok's content-posting API needs approval. Assume a manual/scheduler
  publish step first, and automate publishing later.
- **AI disclosure is a pipeline step, not an afterthought.** W7 must set the
  label every time; make `ai_label_set` a required field so nothing
  publishes without it.
- **Consent for featured dreams.** Only submissions with `consent: true` can
  be named/featured; the form captures this explicitly.
- **Idempotency + logging.** Every workflow writes status + cost + timestamps
  so a re-run never double-charges an API or double-posts, and every render
  cost is auditable (useful for both margins and diligence).

---

## 7. Build order — crawl, walk, run

Don't build all nine workflows on day one. Stage it so you're live fast and
automate under yourself as volume grows:

- **Phase 0 · Launch (mostly manual).** Airtable ledger + the Step B engine
  (call the LLM via a simple n8n flow) + render Nan/twins in the HeyGen and
  Higgsfield UIs by hand + caption/publish manually. Prove the soul with the
  first 20 Shorts. *This is enough to start.*
- **Phase 1 · Automate the desk work.** W2 script-gen + W3 voice + asset
  filing. Keep human render and publish.
- **Phase 2 · Automate the renders.** W4 API renders + W5 assembly. Keep both
  human gates.
- **Phase 3 · Automate the loop.** W7 publish + W8 analytics. Then, only when
  the funnel launches, W9 fulfilment.

Each phase is independently useful, so you're never blocked waiting on the
whole thing to be perfect.

---

## 8. How this closes the loop

The architecture makes every earlier document *operational*: the Bible's
Rule Zero is enforced at W2 and W7; the character playbooks are the voices
in W3 and the render routing in W4; the Growth Engine's formats are the
Format Modules W2 pulls in; the Funnel's economics ride W9; and the Step B
engine is the brain in the middle. Two human gates keep the soul and the
safety intact.

That's the whole machine: honest by construction, warm by design, and built
so a buyer's technician could read it top to bottom and understand exactly
how Sybil's Hearth runs.

---

*The build is now fully specified end to end. From here it's implementation —
stand up the Airtable base, wire W1–W3, and start drafting the first 20
Shorts through the engine.*
