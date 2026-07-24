# The Dream Book — commerce & AI architecture (FOR LATER)

> **Do not build this live yet.** This is the scaffold for the paid layer, kept
> in the drawer until Nana has a real, trusting audience (thousands, not
> dozens). When that day comes, hand this to a developer. It maps the routes
> and — importantly — bakes in the honest guardrails so the paid product stays
> safe and defensible. See the Revenue Funnel doc for the full economics.

## Golden rules for the paid layer (non-negotiable)

- **Reflection, not therapy.** Every product page and every generated reading
  is framed as comfort and reflection — never therapy, diagnosis, cure or
  prediction. The disclaimer sits on the checkout and inside every delivered PDF.
- **Care before commerce.** The dream-intake runs the SAFETY CLASSIFIER first
  (`prompts/w1-safety-classifier.md`). A distressed submission is **refunded /
  never charged**, is **not** run through the engine, and receives a warm
  signpost to real support — never an upsell.
- **Privacy.** Dreams are personal data. Encrypt at rest, minimal retention,
  a real privacy policy, explicit consent. This is a legal must.
- **VAT / refunds / terms** set up properly before a penny is taken.

## The flow (when live)

```
[Garden site · Dream Book]
   └─ user pays (Stripe) + submits ≤300-word dream
        └─ /api/dream-intake   → SAFETY CLASSIFIER
             ├─ FLAG → refund + warm signpost (NO engine, NO content)   ⛑
             └─ SAFE → queue job → your AI agent framework (Step B engine)
                  └─ agent writes the reflection → renders PDF (+ optional audio)
                       └─ /api/dream-webhook  (secure, signature-verified)
                            └─ store + email the reading to the user
```

## API route placeholders (Next.js style — commented stubs)

```js
// /api/dream-intake  — receives the paid dream submission
// 1. verify payment (Stripe) succeeded for this order
// 2. run w1-safety-classifier on dreamText  → if FLAG: refund + signpost, STOP
// 3. else: enqueue job for the AI agent framework; return {status:"received"}
export default async function handler(req, res){ /* TODO */ }

// /api/stripe-webhook  — Stripe events
// handle: checkout.session.completed (one-off £19), customer.subscription.* (Hearth-side Letter)
// verify signature with STRIPE_WEBHOOK_SECRET. Never trust unverified events.
export default async function handler(req, res){ /* TODO */ }

// /api/dream-webhook  — receiver for YOUR AI agent to return the finished reading
// verify a shared secret / signature. Store the PDF, email it to the user.
export default async function handler(req, res){ /* TODO */ }
```

## Stripe products (create when live)

- `Bespoke Dream Translation` — one-off £19 (Checkout, mode: payment).
- `Hearth-side Letter` — recurring (Checkout, mode: subscription).
- `Reading in Her Voice` — one-off £10 upsell (added as a line item at checkout).

## Env vars (on the server, never in the repo)

```
STRIPE_SECRET_KEY=        STRIPE_WEBHOOK_SECRET=
LLM_API_KEY=              AGENT_WEBHOOK_SECRET=
EMAIL_SERVICE_KEY=        DATABASE_URL=
```

## The honest reminder

The garden landing page (`index.html`) is what goes live **now** — beautiful,
free, email-capture only. This Dream Book stays a *preview* ("opening soon")
until the trust is real. Selling before then doesn't just underperform — it
spends the warmth you can't buy back. Build the audience; the shop waits.
