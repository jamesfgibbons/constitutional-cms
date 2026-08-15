# Incident-Learned Invariants

**Provenance mode: synthetic**

This document expresses portable governance rules through generalized failure scenarios. It does not publish private
incident details or claim that a listed outcome was independently certified on a production system.

The point is to share portable implementation patterns, not the private operating details behind any one deployment.

---

## Publishability And Indexability Are Separate

**Statement:** Content quality and search inclusion are separate policy decisions. A page can be degraded, missing enrichment, or operating in fallback mode and still represent a legitimate public URL that should remain indexable.

**Failure mode prevented:** If quality tiers and robots directives are collapsed into one flag, temporary fallback states can emit `noindex`. Crawlers may cache that directive after the page recovers, causing legitimate URLs to disappear from search even though browser testing looks fine.

**Public implementation guidance:** Let quality tiers decide what a page may render: schema, links, visible claims, and narrative depth. Derive robots directives only from explicit indexability policy. A degraded but legitimate URL should generally remain indexable while withholding richer output until it qualifies again.

---

## Timeouts Are Not Entity Absence

**Statement:** Slow dependencies, aborted requests, and ambiguous upstream failures are not proof that a canonical entity does not exist.

**Failure mode prevented:** If an existence check times out and the system treats that as "unsupported," public URLs can flip to `404` or `410` under load. That turns an infrastructure latency problem into an index-shrinking policy decision.

**Public implementation guidance:** Model request-time support as at least three states: `supported`, `unsupported`, and `unknown`. Only explicit canonical evidence should produce permanent absence responses. Unknown states should degrade safely, remain observable, and be tracked separately from entity lifecycle policy.

---

## Rendered Truth Beats Resolver Intent

**Statement:** When a resolver, registry, sitemap, or policy layer disagrees with the actual rendered response, the rendered response is authoritative because that is what users and crawlers receive.

**Failure mode prevented:** A URL can be considered ready by an internal resolver while returning a non-200 status, rendering placeholder content, emitting `noindex`, or exposing different crawler/browser semantics. Discovery surfaces then advertise pages that production output does not actually support.

**Public implementation guidance:** Validate sitemap and link eligibility against rendered output, not only against registry membership. Every sitemap URL should render with the expected status, robots policy, canonical intent, and non-empty body. Resolver state should encode render-parity exclusions with reasons instead of hiding them in sitemap-only filters.

---

## Cache Freshness Must Exceed Warm Cadence

**Statement:** Any system that combines scheduled warm jobs with freshness-based cache reads must set freshness windows longer than the warm cadence with margin.

**Failure mode prevented:** If freshness expires before the next warm cycle completes, cold gaps are guaranteed. Requests in that gap fall back to slower or degraded paths even when the warm job is technically healthy.

**Public implementation guidance:** Treat warm cadence and freshness TTL as paired governance values. Validate that freshness exceeds the schedule plus expected run time and recovery margin. Alert when production freshness approaches the edge of that margin.

---

## Warm Paths Must Populate Every Production Cache

**Statement:** A warm job is complete only if it populates every cache layer that production requests read.

**Failure mode prevented:** Systems with partially warmed cache trees produce surface-specific cold behavior: one path serves fresh materialized output while another misses, recomputes, or falls back because its dependent cache was never populated.

**Public implementation guidance:** Maintain a registry of production-serving caches and their warm producers. Review new cache layers against that registry. Warm jobs should report which dependent caches were populated, skipped, or rejected.

---

## Request-Time Gates Must Use Canonical Registry State

**Statement:** A request-time gate that accepts or rejects a canonical public entity must derive from the declared registry, materialized readiness state, or another explicit source of record.

**Failure mode prevented:** Static metadata maps are useful for display copy, aliases, colors, labels, or fallback presentation, but they drift. If stale enrichment maps become accept/reject authorities, real entities can be rejected because a non-authoritative list forgot them.

**Public implementation guidance:** Separate scope authority from enrichment. Registry or readiness state decides whether an entity is in scope; display metadata only decorates entities that are already in scope. Add drift tests that compare request-time gate coverage to the canonical source of record.

---

## Visible Claims Need A Validated Source Or Suppression

**Statement:** Any visible public claim about a price, score, rating, availability, metric, or recommendation must either come from a validated source or be replaced by explicit suppression language.

**Failure mode prevented:** Fallback values, stale extracts, enriched guesses, and mismatched APIs can produce pages that look substantive while contradicting the system of record. Schema and agent-facing APIs may then amplify the wrong claim.

**Public implementation guidance:** Use a claim decision object before rendering public facts. The decision should name the source, validation state, confidence, and whether the claim is allowed in visible text, structured data, and agent-facing APIs. If the claim is not publishable, render a visible limitation or suppression block instead of silently omitting context or substituting a weaker value.

---

## A Single Rendered Page Must Not Disagree With Itself

**Statement:** When a single rendered URL contains a suppression block ("no public claim is currently published") and a concrete claim block ("from $199") for the same data domain, the page is broken even if both blocks are individually valid.

**Failure mode prevented:** A renderer applies suppression to one module while leaving adjacent modules — FAQ generators, structured-data emitters, summary blocks, or derivative tables — to read a separate upstream and emit confident claims. The page passes a partial gate while presenting a contradiction. The consuming layer has invented truth from an unauthorized substrate.

**Public implementation guidance:** Route every claim-emitting module on the page — body paragraphs, FAQ, structured data, agent-facing payloads, derivative metrics — through one resolver. Treat suppression as a property of the page, not of individual modules. If the resolver says suppress, every speaker is silent. Add a pre-deploy contradiction probe that fails the build when suppression copy and concrete claim tokens coexist on the same rendered URL.

---

## Partial Guards Are False Signal

**Statement:** A guard that covers N of M emission surfaces is not a guard. It is a misleading reassurance that the rest of the system is governed when it is not.

**Failure mode prevented:** A new claim-suppression policy is enforced at the body-paragraph layer. Pre-deploy probes that sample a small basket of routes show green. The policy ships. In production, headers, structured data, agent-facing protocols, sitemap entries, and other rendering paths continue to emit the very claim the policy was meant to suppress — sometimes for weeks — because no surface-wide audit ran. The team has a false sense of compliance; the public experience shows a contradiction. The root cause is not the policy; it is the assumption that a per-surface guard is a per-page guarantee.

**Public implementation guidance:** New policy boundaries require three things before they can be considered shipped: (1) a corpus-wide audit, not a basket-scoped sample, that fails the build when any URL violates the policy; (2) write-time refusal at the data layer that prevents non-compliant emissions from being persisted in the first place; and (3) derived headers and metadata rather than asserted headers, so the rendering surface and the upstream policy cannot drift apart. Treat any partial implementation as un-shipped, regardless of how many surfaces it covers.

---

## One Decision, Many Surfaces

**Statement:** Every public fact has one resolver and N derivation functions. Consumers never copy the decision; they never re-derive it from raw inputs.

**Failure mode prevented:** Body copy reads one publishability source. Headers read another. JSON-LD reads a third. Agent-facing protocol payloads read a fourth. Sitemap inclusion reads a fifth. Over time the rules drift — a threshold tightens here, a defensive fallback is added there, a legacy code path is forgotten — and the same public fact is represented differently across surfaces. Different agents indexing the same URL form different beliefs. Cross-surface consistency is no longer guaranteed because no surface is canonical.

**Public implementation guidance:** Establish one resolver per public fact (publishability, freshness, indexability, claim allowability). Each surface — HTML body, response headers, structured data, agent-protocol payloads, sitemap, llms.txt, well-known files — derives from that resolver via a deterministic function. The function is pure, versioned, and tested. Add cross-surface consistency CI that compares all surfaces on a representative URL set before deploy. Make the cross-surface drift detector a required gate, not an advisory check.
