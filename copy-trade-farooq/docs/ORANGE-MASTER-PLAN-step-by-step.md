# ORANGE — MASTER PLAN, STEP BY STEP

Plain English. Five stages, in order. Each stage has: what it gives you, what Fable does, what you do, and how you know it's finished. Do not start a stage before the one above it is signed off — that's what caused the circling.

---

## STAGE 1 — THE BRAIN (start now)

**What it gives you:** Orange stops forgetting. Every video, document, Telegram message and indicator capture goes in once and is retrievable forever. A novelty gate blocks anything already known from being reported as new.

**Fable does:** builds `ORANGE-BRAIN-v0.1-BUILD-SPEC.md` — corpus layer, state/registries layer, novelty gate, operator brief, next-three director.

**You do:** paste the spec to Fable. Then supply, one final time, the full list of videos/documents you want ingested. After this you never supply them again.

**Done when:** you submit *"the Smart Money Suite indicator is a major new discovery"* and it returns **ALREADY_KNOWN** citing FP-INDICATOR-005/006. Plus: asking "what videos do we hold?" lists them all, and re-supplying one returns ALREADY_INGESTED.

**Rough effort:** small–medium build. This is the foundation — do not skip or rush it.

---

## STAGE 2 — RULE MINING (right after Stage 1)

**What it gives you:** Farouk's method turned from videos into a *registered library of testable rules*. This is "learning the strategy" in the real sense.

**Fable does:** systematically works through the whole corpus (Playbook, Education PDF, Order Blocks, Candlesticks, Signals Guide, every breakdown video) and extracts each rule as a candidate hypothesis with: statement, source_id, source tier, whether it's computable from bars, and what would confirm or kill it. Everything runs through the novelty gate so nothing is re-found.

**You do:** approve. Read the resulting hypothesis list.

**Done when:** a hypothesis register exists covering the documented method, every entry tied to a source and a tier, with a stated test for each. No rule invented, no threshold guessed — unknowns stay UNKNOWN.

**Why this matters:** you can't test what you haven't written down precisely. This is the step that converts "loads of videos" into something Orange can actually work with.

---

## STAGE 3 — DEMO COPY TRADING (the one you want)

**What it gives you:** Farouk posts → Orange builds the order plan → your phone/screen asks you to approve → orders go to your Pepperstone **demo** account → Orange manages them off Farouk's messages using the Constitution rules → everything reconciled and recorded.

**Fable does:** builds `ORANGE-DEMO-COPY-TRADE-SPEC.md`.

**You do:** approve each campaign entry. That tap is the safety control.

**Done when:** one full Farouk campaign runs end to end on demo — entry approved, orders placed, TP1 and break-even handled, scale-out handled, closed and reconciled — with zero duplicate orders and the kill switch tested.

**What it proves:** the plumbing, the timing, real spread, real fills, real latency. **What it does not prove:** profitability, or how live fills would behave (demo servers are kinder than live ones). Do not confuse a good demo run with an edge.

---

## STAGE 4 — RETROSPECTIVE SCREENING (runs in parallel with Stage 3)

**What it gives you:** speed. This is how you learn faster without waiting on Farouk.

**Fable does:** replays your historical Telegram archive through the Lane A follower logic to (a) prove parser coverage across every past message morphology, and (b) cheaply screen the Stage 2 hypotheses — kill the ones that clearly fail, shortlist the ones that survive.

**You do:** approve; review what survived.

**Done when:** every historical signal parses or quarantines (zero silent drops), and the hypothesis register is split into KILLED / SURVIVING / UNTESTABLE.

**The rule that keeps this honest:** retrospective results may **screen and reject** hypotheses. They may **never** confirm one, and they may never be used to fit a model. Confirmation only ever comes from live prospective campaigns. This is what stops you fooling yourself.

---

## STAGE 5 — THE LOOP (ongoing, forever)

**What it gives you:** the agent that keeps going without you.

**On a schedule and whenever a campaign closes, Orange:** loads the Brain → ingests anything new → extracts claims → runs the novelty gate → scores any hypothesis that has become scoreable → updates the registries → writes you a one-page brief → recommends exactly three actions → stops and waits for you.

**You do:** two minutes a day. Read the brief, approve or reject the three actions.

**Done when:** it runs unattended and you've stopped being the one who remembers.

---

## WHAT PROGRESS LOOKS LIKE FROM NOW ON

Stop counting features and reports. Count these:

1. Genuine prospective campaigns captured cleanly, end to end.
2. Demo campaigns executed and reconciled without error.
3. Hypotheses killed or promoted, with the evidence written down.
4. Rediscoveries: **must be zero.**
5. Named blockers removed.

---

## THE RULE YOU SET NOW, WHILE YOU'RE CALM

**No real money until there is a genuine prospective sample showing positive expectancy after costs.** Demo can run as long as you like. Write this down and have Chuck hold you to it — the dangerous moment is when the demo looks brilliant.
