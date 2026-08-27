# The MarTech stack is becoming a control system

This is a **translation**, not a new scheme. The jobs below already exist in
[`CONSTITUTIONAL_CYBERNETICS.md`](CONSTITUTIONAL_CYBERNETICS.md),
[`page_health_resolver.yaml`](../contracts/page_health_resolver.yaml), and
[`page_family_certification_v1.yaml`](../contracts/page_family_certification_v1.yaml).
This file names them in MarTech English so a CMO, RevOps, or growth engineer
can see what the conventional stack is missing.

It does **not** add a `compile` command to the public CLI. See [Honest product
boundary](#honest-product-boundary).

```
Canonical question: who is allowed to settle a marketing fact before a channel speaks?
Governs: how MarTech roles map onto the publish loop
Must not be used as: a maturity score, a fifth web-conformance profile, or a claim that today's CLI compiles campaigns
```

## Open with the failure, not the jargon

Most MarTech diagrams end at activation. That is where the governance problem begins.

Your data platform knows the product. Your decisioning system chooses the offer.
Your content system assembles the message. Your channel sends it. Your analytics
tells you whether somebody responded.

But **who decides which facts are allowed to cross from one layer to the next?**
And how does the system prove every channel used the same approved version?

```
The resolver is the permission engine.
The compiler is the build step.
The channels are renderers.
The receipt is the proof.
The loop connecting them is the control system.
```

Do not open with “cybernetic resolvers compile marketing actuators.”

## The central reframing

> **The MarTech stack is no longer just a stack of tools. It is a control system that senses the market, decides what may happen, compiles an artifact, activates channels, and learns from the result.**

A broken sensor is not evidence that nothing happened.
Delivery proof is not automatically outcome proof.

## Translate the jobs

| Job | Plain-English meaning | MarTech manifestation |
|---|---|---|
| **Sensor** | Something that observes the world | CRM events, CDP feeds, analytics, Search Console, inventory, campaign results |
| **Source authority** | The system allowed to settle a disagreement | Product catalog, pricing, consent ledger, CRM, finance, approved claims library |
| **State** | A timestamped picture of what the system currently believes | Customer profile, offer state, campaign state, content graph, page snapshot |
| **Resolver** | The permission engine | What may be said, to whom, in which channel, under which conditions |
| **Compiler** | The deterministic build step | Turns approved claims into one versioned page, email, ad, offer, or answer |
| **Renderer / actuator** | What the outside world actually receives | CMS, ESP, ad platform, personalization, chatbot, JSON-LD, API |
| **Damper** | Prevents runaway behavior | Consent, suppression, frequency caps, budgets, holdouts, degradation, human approval |
| **Receipt** | Machine-readable proof of what shipped | Campaign generation id, served-page identity, delivery record |
| **Outcome record** | Whether the external goal changed | Conversion, revenue, ranking, retention, pipeline |

Many platforms currently **combine several of those jobs inside one opaque product**.

A personalization system observes behavior, decides what it means, selects a
message, rewrites the copy, publishes it, and reports success.

That is **authority collapse** — the same error as a page renderer inventing a
price, or a child 404 retiring a parent entity. See
[`CONSUMING_LAYER.md`](CONSUMING_LAYER.md) and
[`entity_lifecycle.yaml`](../contracts/entity_lifecycle.yaml).

## Resolver and compiler must be distinct

This is the distinction worth teaching.

### The resolver asks: are we allowed to say or do this?

Examples:

- Is this product actually available?
- Is the price current enough to publish?
- Is this customer eligible for the offer?
- Do we have consent for this channel?
- May this claim appear in an ad but not in structured data?
- Is this landing page indexable?
- May an AI agent recommend the product?
- Should the campaign publish, hold, degrade, or suppress?

Those decisions can differ without contradicting one another. A promotion may
be valid in a private email and invalid as a public search claim. A product may
stay indexable while a stale price is withheld. A customer may qualify for an
offer and still be ineligible for another send because of frequency caps.

The page-health resolver already refuses to compress this into one
`publishable` flag. Marketing inherits the same split:

```
offer_publishable
email_eligible
paid_media_eligible
personalization_eligible
agent_recommendation_eligible
structured_data_eligible
human_approval_required
```

### The compiler asks: given what has been approved, what exact artifact do we build?

The compiler does **not** decide whether a fact is true. It receives approved
claims from the resolver.

```
approved claim IDs
+ audience context
+ channel contract
+ locale
+ template version
+ experiment assignment
+ expiration
        ↓
one versioned generation
```

The generation carries identities: `generation_id`, approved and suppressed
claim ids, source timestamps, template version, content hash, evidence hash,
expiration, fallback policy.

Page-family certification already says: semantic facts → claim decisions →
compiled utility document → projections. Downstream surfaces may render that
document. They may not create new claims.

MarTech English:

> **The resolver decides what the campaign is allowed to say. The compiler builds the exact campaign artifact. The channel is only allowed to render it.**

Most cross-channel inconsistency is a **compiler-governance problem disguised as a copy problem**.

## The loop

```
MARKET + CUSTOMER + BUSINESS SYSTEMS
                  │
                  ▼
              SENSORS
CRM · CDP · analytics · inventory · search · revenue
                  │
                  ▼
          GOVERNED MARKETING STATE
customer · product · offer · content · campaign · evidence
                  │
                  ▼
               RESOLVER
What may be claimed, offered, recommended, indexed, or sent?
                  │
                  ▼
               COMPILER
Build one versioned, evidence-bound generation
                  │
                  ▼
              ACTUATORS
web · email · ads · agents · schema · APIs
                  │
                  ▼
                 WIRE
What did customers, crawlers, models, and platforms receive?
          ┌───────┴────────┐
          ▼                ▼
       RECEIPT          OUTCOME
What shipped?       Did it actually work?
```

Dampers sit around resolver, compiler, and actuators: consent, frequency caps,
budgets, suppression, holdouts, expiration, human approval, safe degradation.

A campaign can be **delivered correctly and perform badly**. It can **perform
well while being governed badly**. Outcomes must not rewrite the delivery
receipt.

## Worked example: a seasonal offer

**Sensors.** Catalog: product exists. Pricing: `$79`. Inventory observed 20
minutes ago. CRM: customer in segment. Consent: email yes, SMS no. Calendar:
offer ends 31 August.

**Resolver.** Website claim: publish. Email offer: publish. SMS: suppress.
Structured offer schema: publish. Agent recommendation: publish. Paid ad: hold.
Each decision has a reason code and evidence reference.

**Compiler.** One generation, e.g. `fall_offer_017`, carrying product identity,
price, end date, availability qualification, and the allowed channels.

**Actuators.** Website, email, JSON-LD, and the assistant all project that
generation. SMS emits nothing because the resolver denied it.

**Receipt.** Participating surfaces used `fall_offer_017`.

**Outcome.** Impressions, clicks, conversion, revenue, unsubscribes, organic
visibility — a separate question.

## Where VIBEnet sits

VIBEnet begins **after** a valid state or decision exists.

> Constitutional CMS governs the campaign’s **right to speak**.
> VIBEnet governs the event’s **right to interrupt**.

It may warn that inventory went stale while a campaign is live. It may not
change `hold` to `publish`. Signal Contract v1 is unchanged.

## How to talk about the familiar tools

> Your CDP is a sensor and state store. It is not automatically the source of truth.

> Your journey engine is a priority resolver. It should not invent offer eligibility.

> Your generative AI is a compiler assistant. It is not the claim authority.

> Your CMS, email platform, and ad network are actuators. They should render approved claims, not reconstruct them.

> Your analytics platform is an outcome sensor. It cannot certify what was actually deployed by itself.

> An A/B test is an active perturbation, not passive observation.

Reading a dashboard is observation. Triggering personalization may have side
effects. Running an experiment deliberately perturbs the system. A test result
must disclose denominator, exposure logic, assignment policy, and blind spots.
See `mutation_class` in [`sensor_integrity.yaml`](../contracts/sensor_integrity.yaml):
`pure_read`, `read_with_side_effect`, `active_perturbation`.

## Honest product boundary

Talk about resolver and compiler as **architecture today**. Do not imply the
current CLI compiles campaigns.

Public CLI (this release):

```
constitutional-cms audit
constitutional-cms validate
```

It evaluates normalized evidence and validates contracts. Authority-collapse
detection lives in `tests/test_entity_lifecycle_contract.py` against
`contracts/entity_lifecycle.yaml`. It does **not** expose a generic `compile`
command.

Until a portable contract for `approved claims → compiled artifact → manifest →
projections` is ratified and shipped:

> **Constitutional CMS defines and verifies the contracts around the resolver and compiler. Private implementations may supply both.**

That is a larger frame without turning today’s CLI into something it does not do.

## Future: MarTech Control Loop Map (not shipped)

After the Public Truth Audit is established, a lightweight map could take named
authorities (product, customer state, decisioning, assembly, channels, consent,
delivery evidence, outcomes) and emit an architecture **receipt** — not a
maturity score — showing implicit decisions, renderer-owned claims, missing
evidence boundaries, unowned fallbacks, and delivery/outcome conflation.

CTA remains the Claim Gate Pilot: one governed boundary between the decision
layer and the channels that speak for the company. Do not advertise this map
as live.

## Essay series (Chair publishes)

Anchor: **The MarTech Stack Is Becoming a Control System**
Subhead: Your CDP senses. Your resolver decides. Your compiler builds. Your channels actuate. Your receipts prove.

Follow-ons, when Chair writes them:

1. Where Is the Resolver in Your MarTech Stack?
2. Generative AI Is a Compiler, Not a Source of Truth
3. Cross-Channel Consistency Is a Generation Problem
4. Your A/B Test Is an Intervention
5. Delivery Proof Is Not Outcome Proof
6. The Right to Publish Is Not the Right to Interrupt
