**SYBIL’S HEARTH**

**THE REVENUE FUNNEL**

*Honest unit economics · the three tiers · what breaks the model · defensible pricing*

Document 3 of the build · Foundation Draft · 16 July 2026

*Every figure is a real 2026 quote (sources at the back). FX used: \$1 ≈ £0.79.*

**1. The funnel, and the one rule for this document**

The model is a value ladder: free content earns attention, a tiny paid “tripwire” converts a viewer into a buyer, a subscription turns a buyer into recurring revenue, and a premium tier turns your most engaged fans into high-margin cash. Each rung makes the next one easier to climb.

**The rule for this document:** no wishful thinking. Every cost below is a real, current 2026 figure, and every margin is shown AFTER payment fees and fulfilment — not before. Where a number in the original brief was optimistic, I say so plainly and show the corrected figure. This is the document that decides whether the business makes money or quietly loses it on every order.

**The headline finding, up front:** The funnel works — but two of the original numbers don’t survive a shipping invoice. (1) The “free premium binder” is a large hidden acquisition cost that only pays back if subscribers stay ~3+ months. (2) The “£24 for a 30-minute video / £220 profit” holds only on HeyGen’s cheapest engine; a premium Nan render is 3–5× that. Both are fixable, and the fixes actually make the product better. Details below.

**2. Tier 1 — The Tripwire (£1.50 instant reading)**

A fast, low-cost personalised dream reading delivered instantly as a beautiful PDF. Its job is NOT to make money — it is to convert a free viewer into a paying customer, because the second purchase from an existing buyer is many times easier than the first.

**The honest economics of a £1.50 sale**

| **Per £1.50 instant reading**    | **Amount** | **Note**         |
|----------------------------------|------------|------------------|
| Price charged                    | £1.50      | impulse buy      |
| Stripe fee (1.5% + 20p, UK card) | −£0.22     | ~15% of the sale |
| AI generation + PDF hosting      | −£0.08     | pennies          |
| **Net kept**                     | **£1.20**  | **per order**    |

**The catch nobody mentions:** on a £1.50 sale, the fixed 20p part of the Stripe fee alone is ~13%. Sub-£2 card payments are structurally fee-heavy. That’s fine — this is marketing, not margin — but do not fool yourself that the tripwire is a profit centre. Its only KPI is conversion rate to the subscription.

**Recommendation:** Keep the tripwire cheap and impulsive, but consider £2.50–£3.00 rather than £1.50. It’s still an easy yes, it halves the proportional fee drag, and it slightly better qualifies buyers who’ll go on to subscribe. Test £1.50 vs £2.99 head-to-head.

**3. Tier 2 — The Subscription (the riskiest number in the plan)**

This is the recurring-revenue engine: a monthly subscription where members receive physical “dream leaves” — calligraphy-style parchment readings — to collect in a keepsake binder (the Dream Codex). The retention idea is sound. The economics of the original “free binder” version are not, and this is the most important page in the document.

**First: what a monthly parcel actually costs to send**

| **Monthly fulfilment (per member)**          | **Cost**       | **Source basis**  |
|----------------------------------------------|----------------|-------------------|
| Parchment print (3–4 specialty sheets)       | £1.20          | specialty print   |
| Envelope + wax-effect seal                   | £0.40          | see note on wax   |
| Postage — Royal Mail Large Letter, 2nd class | £1.55–1.90     | 2026 rate         |
| Pick / pack / handling labour                | £0.60          | realistic         |
| **Total to serve one member / month**        | **£3.75–4.10** | **before Stripe** |

**The “automated wax seal” problem:** Real molten-wax sealing is manual, slow work — it cannot be “automated by a print API” as the original brief assumed. You have two honest choices: (a) wax-EFFECT self-adhesive seals, which look great and can be machine-applied cheaply (recommended), or (b) genuine wax, which becomes a real per-parcel labour cost (~30–60p+ of hand-labour) that must be priced in. Don’t promise automated real wax — it doesn’t exist.

**The hidden killer: the “free” binder is a big acquisition cost**

A custom-embossed leather (or quality faux-leather) binder costs roughly £15–25 wholesale, plus ~£3.50 to ship it. Giving it away free at signup means every new subscriber starts ~£20–28 in the hole. Here’s what that does to the two possible models:

**Model A — Free binder, £14.99/month**

| **Free-binder model**               | **Month 1** | **Each later month** |
|-------------------------------------|-------------|----------------------|
| Subscription revenue                | £14.99      | £14.99               |
| Stripe fee (1.5% + 20p)             | −£0.42      | −£0.42               |
| Monthly fulfilment                  | −£4.00      | −£4.00               |
| Free binder + its postage (one-off) | −£25.50     | —                    |
| **Net contribution**                | **−£14.93** | **+£10.57**          |

**Read that carefully:** you LOSE ~£15 on every subscriber in month one, and you don’t claw the binder cost back until roughly the end of month 3. Any member who cancels before then is a guaranteed loss. This model bets the whole business on retention you haven’t proven yet.

**Model B — Paid “Starter Codex” £34.99 one-off, then £9.99/month (recommended)**

| **Paid-starter model**                | **At signup** | **Each month** |
|---------------------------------------|---------------|----------------|
| Charge                                | £34.99        | £9.99          |
| Stripe fee                            | −£0.72        | −£0.35         |
| Binder + postage / monthly fulfilment | −£25.50       | −£4.00         |
| **Net contribution**                  | **+£8.77**    | **+£5.64**     |

**Why Model B wins:** You’re cash-positive from the very first transaction, the binder is framed as a premium “welcome kit” (higher perceived value than “free”), and you’re no longer betting the business on month-3 retention. Same beautiful product, same super-glue “complete the annual journal” psychology — but the maths can’t sink you. Strongly recommend launching on Model B.

**The Moon’s Reflection leaf:** your monthly 30-day synopsis idea is excellent retention design and costs almost nothing extra (it’s one more parchment sheet in the same envelope). Keep it — it’s the single strongest anti-churn feature and it makes the annual binder feel incomplete without every month.

**4. Tier 3 — The VIP Video (£250 personalised reading)**

A premium, personalised video of Nan Sybil reading a customer’s dream by the fire, addressing them by name. High-margin, zero physical logistics. The concept is strong; two assumptions in the original brief need correcting.

**Correction 1 — the render cost depends entirely on which engine**

**HeyGen API pricing is roughly “\$1 = 1 minute of video” on its standard (Avatar III) engine, but its premium photorealistic engines (Studio / Avatar IV) run \$4–5 per minute.** So the “£24 for 30 minutes” figure is real — but only on the cheapest engine. For the flawless, premium Nan the brand promises, 30 minutes would cost roughly £95–£120 in render alone. That’s the gap between the brief and reality.

**Correction 2 — 30 minutes is the wrong length (and it’s costing you)**

A 30-minute talking-head is worse on every axis: more expensive to render, more likely to hit length limits or errors (a failed render means paying to re-render), slower to deliver, and — bluntly — few people watch a 30-minute AI monologue to the end, which drives refund risk on a £250 product. A tight, beautifully-scripted 10–12 minute video is cheaper, more reliable, more likely to be watched fully, and feels MORE premium, not less.

| **£250 VIP video — margin by spec** | **Premium 12-min (recommended)** | **Premium 30-min (brief)** |
|-------------------------------------|----------------------------------|----------------------------|
| Price                               | £250.00                          | £250.00                    |
| Stripe fee (1.5% + 20p)             | −£3.95                           | −£3.95                     |
| HeyGen render (premium engine)      | −£38                             | −£110                      |
| Voice / audio                       | −£3                              | −£6                        |
| Re-render buffer (10%)              | −£4                              | −£11                       |
| **Net cash margin**                 | **≈ £201**                       | **≈ £119**                 |

**The counter-intuitive win:** Switching the flagship from 30 minutes to a tight 12 minutes nearly DOUBLES your margin (~£201 vs ~£119), speeds delivery, cuts failure risk, and improves the customer experience. This is the clearest example of honest math making the product better, not smaller. (Note: figures exclude your scripting time and VAT — see Section 5.)

**5. What breaks the model (read before scaling)**

These are the five things that quietly turn a profitable-looking funnel into a loss-maker. Price and plan for them now, not after.

- **Churn.** The whole subscription rests on it. Model B protects you, but track monthly churn from day one; anything above ~8–10%/month means the retention “super-glue” isn’t working and needs a product fix before you scale ad spend.

- **Refunds & chargebacks.** Highest on the £250 tier. A shorter, watched-to-the-end video is your best defence. Set a clear delivery-time and quality promise, and budget ~3–5% of VIP revenue for refunds.

- **VAT.** Once UK turnover passes the £90k registration threshold, you must add 20% VAT — which comes out of your margin unless prices are set VAT-inclusive from the start. At scale this is the single biggest silent margin hit. Build pricing VAT-aware now.

- **International physical shipping.** The binder and leaves are cheap to post inside the UK and expensive everywhere else (plus customs). Recommend: physical subscription UK-only at launch; offer overseas fans a digital-only tier until volumes justify regional fulfilment.

- **Re-render / failure rate.** AI video generation fails sometimes. Every failed premium render is real money. Keep videos short, QA before sending, and hold the 10% buffer shown above.

**6. An illustrative monthly picture**

A rough, deliberately conservative snapshot once the channel has traction — to show the shape, not to promise the result. Assume 500 active subscribers on Model B and a modest premium/tripwire flow:

| **Illustrative month (500 subscribers)** | **Revenue** | **Net after costs** |
|------------------------------------------|-------------|---------------------|
| Subscriptions: 500 × £9.99               | £4,995      | ≈ £2,820            |
| New-member Starter Codex: 60 × £34.99    | £2,099      | ≈ £525              |
| Tripwire readings: 400 × £2.99           | £1,196      | ≈ £900              |
| VIP videos: 8 × £250 (12-min)            | £2,000      | ≈ £1,610            |
| **Indicative monthly total**             | **£10,290** | **≈ £5,855**        |

**What this says:** even at a modest 500 subscribers, the model throws off meaningful monthly profit — and the subscription base is the flywheel that makes it compound. But notice the profit is real only because the costs above are honest. On the original free-binder + 30-min-video assumptions, that same month would be thousands of pounds thinner, and possibly negative on a bad churn month.

**Not included here (on purpose):** your own time/labour, software subscriptions (HeyGen/Higgsfield/ElevenLabs base plans, n8n, Airtable), any ad spend, and VAT. Fold these in before treating any month as “profit in the bank.”

**7. The recommended pricing architecture**

| **Tier**                       | **Price**      | **Role in the funnel**            |
|--------------------------------|----------------|-----------------------------------|
| Free content                   | £0             | Attention → dream submissions     |
| Tripwire instant reading       | £2.99          | Convert viewer → first-time buyer |
| Starter Codex (welcome kit)    | £34.99 one-off | Cover binder cost, cash-positive  |
| Dream Codex subscription       | £9.99 / month  | Recurring-revenue flywheel        |
| VIP fireside video (10–12 min) | £250           | High-margin fan monetisation      |

This ladder is cash-positive at every step, defensible under scrutiny, and — critically for your exit goal — built on real numbers a buyer’s accountant can verify. It keeps every product you designed. It just prices them so a shipping invoice can never turn a “sale” into a loss.

**Sources for every figure in this document**

*HeyGen API pricing (≈\$1/min standard, \$4–5/min premium engines, TTS \$0.04/min):* help.heygen.com/en/articles/10060327.

*Royal Mail 2026 Large Letter rates (2nd class 100g £1.55, 250g £1.90):* royalmail.com/prices2026 (via mymailingroom.com/rm-prices).

*Stripe UK card fees (1.5% + 20p, standard UK cards):* stripe.com/gb/pricing. Binder wholesale and specialty-print figures are typical 2026 trade quotes and should be confirmed with your chosen supplier before launch.

**Where we are:** brand locked (Doc 1), a month of content and a growth flywheel (Doc 2), and a funnel now priced on rock rather than hope (Doc 3). Same three tiers you designed — tripwire, physical subscription, VIP video — every one kept, every one now cash-positive.

*Next up is Document 4 — the Automation Architecture: the n8n + Airtable backend, the script-generation pipeline, and the print-on-demand fulfilment wiring that makes all of the above run without you touching each order. Say the word.*
