# Constitutional Cybernetics

Constitutional CMS is a control system for the agentic web.

Traditional CMS software manages human-authored pages. Constitutional CMS
manages the feedback loops that decide whether an agent-built surface is
allowed to exist, make claims, expose structured data, appear in discovery
surfaces, or project state into downstream renderers.

The core question changes from:

> Who edited this page?

to:

> What does this system believe, where did that belief come from, which
> surfaces are allowed to act on it, and how will the system know when it is
> wrong?

That is a cybernetic problem.

## The Loop

Every governed publishing system has the same loop:

1. **Sensors** observe the world: logs, crawlers, probes, analytics, APIs,
   editorial inputs, human review, and synthetic audits.
2. **State** compresses those observations into materialized snapshots,
   registries, resolver decisions, and source-authority records.
3. **Comparators** apply invariants and contracts to observed state. Required
   inputs that are absent produce `UNMEASURED`, never PASS.
4. **Priority resolvers** select the next admissible intervention. Hard
   constitutional constraints filter first; Pareto allocates attention among
   what remains.
5. **Actuators** change the outside world: rendered HTML, structured data,
   sitemaps, cache writes, feeds, agent APIs, notifications, audio, light, and
   spatial interfaces.
6. **Dampers** prevent runaway behavior: suppression, hold, degrade, explicit
   uncertainty, rate limits, scoped mutation envelopes, and human ratification.
7. **Wire, receipts, and outcomes** close the loop: machine-readable evidence
   shows whether the actuator reflected governed state and whether the external
   objective changed.

If any part of that loop is implicit, an agent will eventually fill the gap
with a plausible story. Constitutional CMS exists to make the loop explicit.

## Sensors Are Not Truth

A cybernetic system can only respond to what it can sense, but sensor output is
not automatically world truth.

Logs can go stale. Crawlers can be blocked. Analytics can drop events. A probe
can time out. A dashboard can chart a derived count that looks authoritative but
is only a display limit.

The system must therefore model sensor health separately from observed values.
A broken or stale sensor is not evidence that the world is quiet. It is evidence
that the control loop has lost visibility.

This is why Constitutional CMS treats source authority and sensor integrity as
first-class contracts. "No observations" and "observation source failed" are
different states, and they must produce different public behavior.

## The Observer Is Inside The System

A probe can change the corpus it is trying to measure. A nominally passive page
census may trigger a read-through cache, self-heal missing state, or write an
access-derived artifact. The observation then becomes an intervention.

> A metric that responds to observation cannot certify convergence.

The minimum viable probe contract is one required field:

```yaml
mutation_class: pure_read | read_with_side_effect | active_perturbation
```

- `pure_read` is not expected to change measured state.
- `read_with_side_effect` may trigger cache fill, repair, logging, or another write.
- `active_perturbation` deliberately changes the system to test its response.

"GET request" is not a mutation class. A receipt must disclose the class, the
declared denominator, observation order, and known blind spots. Probe logic and
mutation policy stay pinned for the observation window: do not recalibrate the
instrument mid-measurement.

## Requisite Variety

A regulator cannot preserve distinctions that its contract has already erased.
Publishability, indexability, claim permission, schema permission,
materialization, fallback, stale, unknown, and unavailable are different states
because they require different responses. The signal may compress detail; it may
not erase a distinction that changes the lawful action.

This is why missing probe inputs produce `UNMEASURED` rather than a convenient
PASS, and why no-volume is not a true zero.

## Pareto Allocates Attention; Invariants Protect The Tail

The repair stack orders dependent layers within one publishing surface. Control
priority classes order unlike interventions after constitutional filtering.
Neither is a numeric score, and neither can waive a rare constitutional failure
because it affects a small denominator.

See [`PROTOCOL_MAP.md`](PROTOCOL_MAP.md) for the canonical routing between
contracts, invariants, conformance levels, release gates, repair layers, and
control priority classes.

## State Is The Compression Layer

Agentic systems cannot safely reason from raw noise on every request. They need
state that is:

- materialized before render time
- named by stable identifiers
- timestamped with source freshness
- derived by declared transforms
- inspectable by humans and machines

State is the compression layer between the world and the consuming layer. It
lets renderers, crawlers, APIs, and agents consume a governed belief instead of
inventing one from whichever raw input happened to be nearby.

## Controllers Are Contracts

In a conventional web stack, policy is scattered through route files, loaders,
helpers, templates, middleware, cron jobs, and human habit. In an agent-built
stack, that is not enough. Agents need a contract they can read before acting.

Controllers in Constitutional CMS are declarative contracts:

- page type contracts decide quality tiers
- claim decisions decide public fact emission
- page health resolvers decide body, schema, sitemap, and link eligibility
- cache materialization contracts decide whether an artifact may serve traffic
- sensor integrity contracts decide whether a chart can claim a real zero
- proof ledgers decide whether "done" has evidence

The contract is the controller. Code is the actuator that implements it.

## Actuators Must Not Invent Truth

An actuator is any surface that changes what another system can perceive:
HTML, response headers, JSON-LD, `llms.txt`, manifests, sitemaps, API payloads,
emails, dashboards, audio beds, AR overlays, or environmental displays.

The actuator may translate state into a form suited to its medium. It may not
upgrade uncertainty into certainty, turn stale state into current claims, or
derive policy from local renderer convenience.

This is the bridge to VIBEnet-style thinking: the same canonical state can be
rendered as text, schema, sound, light, motion, or spatial atmosphere. Those are
different renderers, not different truths.

## Dampers Make Autonomy Safe

Agentic systems need dampers because autonomy amplifies small errors.

A stale source should degrade output, not trigger deletion of a canonical URL.
A failed verifier should stop a batch, not rerun expensive ingestion. A scoped
agent should prepare and prove, not silently expand into production mutation.
A missing source should show limitation language, not a confident substitute.

Dampers are not pessimism. They are the difference between a system that adapts
and a system that thrashes.

## Proof Is Feedback

The loop is not closed when a PR merges. It is not closed when a deploy starts.
It is not closed when an agent says it is done.

The loop closes when evidence from the correct authority shows that the public
actuator reflects the governed state.

That is delivery proof, not automatically outcome proof. A merge, deployment,
promotion, or served-identity receipt can prove that the intended world reached
the wire. It cannot prove that the external objective changed. Implementations
capture those results separately using
[`outcome_record.yaml`](../contracts/outcome_record.yaml), including
`not_observed`, `unmeasured`, `blocked`, and `inconclusive` states. Missing
outcome evidence never becomes an actual value of zero.

That evidence should be machine-readable first and narrative second. Markdown
can explain a result, but JSON or equivalent structured evidence should govern
the result. If the narrative and the evidence disagree, the evidence wins.

## Why This Matters Now

Agentic search, agentic commerce, and agentic interfaces are all moving the web
from documents toward operating surfaces. A page is no longer only read by a
person. It is parsed by crawlers, summarized by models, transformed into answer
cards, invoked by agents, and re-rendered into interfaces the publisher may
never see.

A traditional CMS asks whether content exists. A constitutional, cybernetic CMS
asks whether the whole loop is governed:

- Can the system sense the right world?
- Does it know which source is authoritative?
- Can it compress observations into inspectable state?
- Do its renderers derive from that state?
- Does it damp uncertainty instead of hiding it?
- Can it prove what it did?

That is the operating layer websites need when agents become authors, readers,
and actors.
