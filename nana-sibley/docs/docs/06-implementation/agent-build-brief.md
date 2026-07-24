# Agent Build Brief — Phase 0/1 (hand this to the coding agent)

*Sybil's Hearth · the exact construction instructions · v1.0*

This is the brief the **human operator** pastes to the coding agent (Claude
Code / dev agent) to build the first working slice of the machine. It is
deliberately scoped: **Airtable base + workflows W1–W3 only**, with hard stops
before anything paid or live. Prove the core loop, then expand.

---

## 0. Copy-paste kickoff (give this to the agent verbatim)

> You are building the backend for "Sybil's Hearth". The full spec is in this
> repository — read `README.md`, `THE-HEART.md`, `docs/05-automation/`, and the
> entire `prompts/` folder before writing anything. Build **only** the Airtable
> base and n8n workflows **W1, W2, and W3** described in
> `docs/06-implementation/agent-build-brief.md`. Obey Rule Zero and the safety
> layer as hard requirements. **Do not** hardcode any secret, and **do not**
> wire any live paid render API or any publishing/posting step — stop and ask
> the human operator at every point marked ⛔. Deliver importable n8n workflow
> JSON, an Airtable setup script, a `.env.example`, a README, and a test log.
> Work one component at a time and stop for review after the Airtable base.

---

## 1. The Airtable base — "Hearthside Ledger"

Create these tables, fields, and views.

**Submissions**
- `Submission ID` (autonumber) · `Raw Dream Text` (long text) · `Source`
  (select: form / pinned_comment / manual) · `Submitter Handle` (text) ·
  `Consent to Feature` (checkbox) · `Safety Flag` (checkbox) · `Status`
  (select: new / screened / care_queue / scripted) · `Created At` (created
  time) · link → **Scripts**

**Scripts**
- `Script ID` (autonumber) · `Submission` (link) · `Character` (select:
  nan_sybil / maeve / jesse / family) · `Format` (select: hero_dream_short /
  validation_moment / fireside_tale / dream_of_the_week / multi_character) ·
  `Script JSON` (long text) · `Safety Flag` (checkbox) · `Status` (select:
  needs_review / approved / rejected) · `Reviewer Notes` (long text) ·
  `Version` (number) · link → **Assets**, **Videos**

**Assets**
- `Asset ID` (autonumber) · `Script` (link) · `Type` (select: audio / video /
  final) · `Speaker` (select: nan_sybil / maeve / jesse) · `Tool` (select:
  elevenlabs / heygen / higgsfield / runway / assembly) · `File` (attachment
  or URL) · `Render Cost` (number) · `Status` (select: queued / rendering /
  ready / failed)

**Videos**
- `Video ID` (autonumber) · `Script` (link) · `Final Asset` (link) ·
  `Platform` (select: youtube / tiktok / reels) · `Publish At` (date) ·
  `Published URL` (URL) · `AI Label Set` (checkbox, **required true before
  published**) · `Status` (select: scheduled / published) · `Retention %`
  (number) · `Comment Rate` (number)

**Ideas / Backlog**
- `Idea ID` (autonumber) · `Source Dream` (link → Submissions) · `Theme`
  (multi-select) · `Notes` (long text) · `Status` (select: backlog / queued /
  used)

**Views:** `Needs Review` (Scripts where Status = needs_review) · `Care Queue`
(Submissions where Safety Flag = true) · `Render Queue` (Assets where Status =
rendering) · `Schedule` (calendar on Videos.`Publish At`).

⛔ **STOP after the base is built. Human reviews before workflows begin.**

---

## 2. Workflow W1 — Intake + Safety Pre-screen

- Trigger: a webhook (submission form) — for now also accept manual test
  inputs.
- Create a **Submissions** row (Status = `new`).
- Run the **safety pre-screen** per `prompts/safety-layer.md`: an LLM
  classification pass (plus a keyword guard) over `Raw Dream Text`.
- If distress/crisis is detected → set `Safety Flag = true`, Status =
  `care_queue`, notify the human operator, and **STOP** (no downstream
  processing).
- Otherwise → Status = `screened`.

**This workflow is built and tested first, before W2.** It is the most
important one in the system.

---

## 3. Workflow W2 — Script Generation (the Step B engine)

- Trigger: Submissions where Status = `screened`.
- Assemble the prompt by concatenating, in order:
  `prompts/system-prompt.md` + the chosen `prompts/character-modules/<x>.md`
  + the chosen `prompts/format-modules/<y>.md` + the task input (the dream +
  variables). For MVP, default Format = `hero_dream_short` and rotate Character,
  unless a field specifies otherwise.
- Call the LLM (low temperature) and require JSON output.
- **Validate** the JSON against `prompts/output-schema.md`: valid JSON, allowed
  enums, no banned words, `safety_flag` re-checked. On failure, retry up to 3×,
  then flag for human — never crash, never publish invalid output.
- Write a **Scripts** row (Status = `needs_review`).

⛔ **Human Gate 1 lives here** — scripts wait at `needs_review` for the
Creative Director to approve. Do not auto-advance.

---

## 4. Workflow W3 — Voice (ElevenLabs) — build, but gate the live call

- Trigger: Scripts where Status = `approved`.
- For each `script_lines[].speaker`, call ElevenLabs with that character's
  **locked voice ID** and settings, and store the audio in **Assets**.
- ⛔ **Do not connect the live, paid ElevenLabs API until the human operator
  has added credentials and approved.** Build and test against a sandbox / free
  tier / mock first.

---

## 5. Secrets & safety of build

- All API keys and tokens go in the n8n credential store or environment
  variables the human operator sets. **Never hardcode secrets.** Provide a
  `.env.example` listing what's needed.
- Everything the agent writes is committed to this repo (version-controlled).

---

## 6. Acceptance tests (the agent must pass these before "done")

1. **Happy path:** a benign dummy dream → Submissions row → `screened` → W2 →
   a **valid** Script JSON at `needs_review`.
2. **Safety path (critical):** a dummy input mentioning self-harm → `Safety
   Flag = true`, Status = `care_queue`, and **no script generated**. This test
   must pass before anything else is considered working.
3. **Robustness:** a forced invalid LLM output → retried, then flagged; the
   workflow does not crash and nothing invalid moves downstream.

---

## 7. Explicit STOP points (⛔) — human decisions only

- After the Airtable base is created (review before workflows).
- Before connecting any **live paid** render/voice/video API.
- Before wiring **any** publishing/posting to a real platform (that's a later
  phase, needs API approval + the AI-disclosure label).

Build to here, prove the loop on dummy dreams, and hand back for review. Phase
2 (renders + assembly) and Phase 3 (publish + analytics) come only after this
slice is solid.
