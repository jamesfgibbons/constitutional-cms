# Story Bible — A Frame for the Agentic Web

This document is the master narrative frame that underlies the contracts, invariants, and reference patterns in this repository. It is published so that adopters can place individual rules in a coherent worldview rather than treating governance as a checklist.

Version: 0.2
Last updated: 2026-06-19

---

## The universe law

> **Do not let the consuming layer invent truth.**

Every rule in this repository ladders into this single principle:

- If an AI answer needs a fact, the fact comes from substrate, not inference at retrieval time.
- If a programmatic page needs a claim, the claim comes from a governed registry, not from a fallback heuristic.
- If an agent needs a boundary, the boundary comes from a declared contract, not from a model's best guess.
- If a renderer needs state, the state comes from a defined signal payload, not from re-derivation against raw inputs.
- If a brand wants to be cited by machines, its proof must exist upstream of the machine layer that cites it.

Consuming layers — language models, retrieval systems, agent runtimes, downstream renderers — can compose, summarize, present, and adapt. They must not be permitted to manufacture upstream truth, because that truth is what the rest of the system depends on.

This is not a stylistic preference. It is a structural requirement for any system whose output will be re-consumed by machines that have no way to verify it after the fact.

---

## The scarce-asset thesis

AI makes downstream output abundant. Articles, summaries, code, briefs, dashboards, synthetic media — the cost of generating any one of them is collapsing.

What becomes scarce is the material that exists *before* the machine acts:

- Structured meaning that retrieval can compress without losing the load-bearing fact.
- Source-backed claims a citation system can trust.
- Governed context an agent can act on without inferring policy.
- Provenance an auditor can follow back to a person or process.
- Human-origin signal that has not been flattened into machine-time uniformity.

The agentic economy does not commoditize authorship. It raises the value of authored input that survives mediation.

---

## The compression doctrine

> **Compress meaning for machines. Preserve timing for bodies. The right compression at the right layer.**

Machines now mediate between human intent and the world in two directions:

- **Outbound** — machines read the world for users through search, agents, comparison, booking, commerce, and citation.
- **Inbound** — machines render the world back to users through ambient audio, wearable displays, spatial interfaces, lighting, haptics, and persistent environments.

Both directions need authored upstream input. Both will fail without it. But the *kind* of input they need is different:

- **Outbound failure mode is under-compression.** Business meaning is scattered across vague prose, PDFs, dashboards, and tribal knowledge. The agent has to infer what the entity is, what it proves, what it sells, whether it is trustworthy. Inference burns token, latency, confidence, and governance budgets. A competitor can win simply by being cheaper to read. The remedy is *compression*: chunks, entities, schemas, APIs, proof points, materialized state, structured claims.
- **Inbound failure mode is over-compression.** Signal that started human gets flattened into grid time: generic loops, quantized cadence, uniform rhythms, synthetic sameness. Ambient systems become indistinguishable from machine output. The remedy is *preservation*: rubato, compound meter, phrasing, breath, performance provenance, human-origin timing.

Different surfaces, same structural law: protect the load-bearing signal at the layer it lives in.

---

## The cybernetic doctrine

> **Govern the loop, not just the artifact.**

The agentic web is not only a publishing surface. It is a feedback system.
Machines observe public state, compress it, reason over it, act on it, and feed
their outputs back into the next cycle of discovery and decision.

That makes Constitutional CMS a cybernetic layer:

- **Sensors** collect logs, crawls, probes, analytics, user feedback, and agent traces.
- **State** compresses observations into snapshots, registries, resolver decisions, and proof artifacts.
- **Controllers** apply contracts, gates, source authority, and claim policy.
- **Actuators** emit HTML, schema, sitemaps, APIs, manifests, cache artifacts, dashboards, sound, light, or spatial renderings.
- **Dampers** hold, suppress, degrade, rate-limit, or require human ratification when the loop loses confidence.
- **Proof** closes the loop by showing whether the actuator matched the governed state.

This frame connects Constitutional CMS to VIBEnet-style sensory thinking without
making any one sensory surface mandatory. The same governed state can become a
page, an API payload, an agent-readable manifest, an audio cue, or an ambient
interface. Those are renderers. The truth still lives upstream.

---

## The four realms

Every published essay, invariant, contract, and product surface in our work maps to one of four realms:

| Realm | Concern | Hero essay |
|-------|---------|------------|
| R1 Outbound Surface | Can machines understand, retrieve, cite, compare, and act on your business without guessing? | *Geometries of Discoverability* |
| R2 Inbound Surface | Can machines render the world back to the human nervous system without flattening it? | *The Two Clocks* |
| R3 The Bridge | What upstream material must humans author because the agentic layer cannot safely invent it? | *Authored Upstream* |
| R4 The Operating System | How do we keep downstream agents, pages, renderers, and interfaces from inventing truth? | *Do Not Let the Consuming Layer Invent Truth* |

The repository's contracts, invariants, and reference patterns are predominantly Realm 4 artifacts. The other realms produce the public narrative; Realm 4 produces the executable governance.

---

## The hero essays

Each realm has one canonical essay that states the realm's core argument.

### Geometries of Discoverability (R1)
> *A competitor can beat you simply by being cheaper for an agent to read.*

Discovery becomes geometric. Brand becomes a compression token — the entity the system converges on when it reasons about a category. The old question was "do we rank for this query?" The new question is "when the model thinks about this problem, are we the entity it converges on?"

### The Two Clocks (R2)
> *Ambient interfaces need body-time the way AI search needs substrate.*

Machines do not only read the world. They render it back. Ambient systems flatten authored timing into machine-time unless designers preserve cadence, phrasing, and provenance explicitly. The same scarce-input law applies in reverse: the body needs upstream timing the machine layer cannot synthesize from nothing.

### Authored Upstream (R3)
> *AI does not commoditize authored input. It raises the value of authored input that survives mediation.*

The bridge essay. Unifies the outbound and inbound arguments under one frame: the agentic economy rewards whoever authors the upstream material the machine layer cannot safely invent. Future model releases reinforce this rather than weakening it, because every increment of agentic capability raises the value of the substrate the agent depends on.

### Do Not Let the Consuming Layer Invent Truth (R4)
> *Prompt-based AI says "tell the model not to hallucinate." Architecture-based AI says "do not ask the model to supply truth the system never emitted."*

The operating-system essay. Full body: [`docs/CONSUMING_LAYER.md`](CONSUMING_LAYER.md). Companion: [`docs/ENTITY_LIFECYCLE.md`](ENTITY_LIFECYCLE.md) — do not let one truth domain revoke another; 410 is a verdict. The contracts, invariants, and reference patterns in this repository are the executable form of this argument: governance before runtime, materialized state, derived (not asserted) headers, single-resolver public facts, cross-surface consistency. It reduces unauthorized certainty (the load-bearing kind of AI slop). It does not ban generation.

---

## How this repository serves the frame

This repository is the Realm 4 surface. It publishes:

- **Contracts** in `contracts/` — declarative YAML defining what a renderer, gate, or surface must guarantee before serving public output.
- **Invariants** in `docs/INCIDENT_LEARNED_INVARIANTS.md` — governance rules clarified by live failures, rewritten as portable patterns.
- **Reference patterns** in `docs/V0_2_REFERENCE_PATTERNS.md` — implementation guidance for adopting the contracts.
- **Cybernetic framing** in `docs/CONSTITUTIONAL_CYBERNETICS.md` — a control-system model for sensors, state, controllers, actuators, dampers, and proof.
- **Examples** in `examples/` — domain-specific applications of the framework.

Each artifact ties back to one of the four realms. The contracts and invariants exist because the consuming layer cannot be allowed to invent the truth the rest of the system depends on. The reference patterns exist because operators need a path from "we agree with this principle" to "we have it running in production."

---

## What this document is not

- It is not a marketing positioning document. The audience is operators and architects deciding how their own agent-mediated systems should be governed.
- It is not exhaustive. The repository's contracts and invariants are the executable detail; this document is the frame those details ladder into.
- It is not stable in its current form. Version 0.1 is a working canon. The structure is expected to survive; specific essays and invariants will be added, refined, and superseded as the operating model matures.

---

## Cross-references within this repository

- Universe law, full essay: [`docs/CONSUMING_LAYER.md`](CONSUMING_LAYER.md).
- Universe law in action: [`docs/INCIDENT_LEARNED_INVARIANTS.md`](INCIDENT_LEARNED_INVARIANTS.md) — every invariant is an application of "do not let the consuming layer invent truth."
- Implementation patterns: [`docs/V0_2_REFERENCE_PATTERNS.md`](V0_2_REFERENCE_PATTERNS.md).
- Cybernetic frame: [`docs/CONSTITUTIONAL_CYBERNETICS.md`](CONSTITUTIONAL_CYBERNETICS.md).
- Agent coordination boundary: [`docs/AGENT_COORDINATION.md`](AGENT_COORDINATION.md).
- Novelty and prior-art context: [`docs/NOVELTY.md`](NOVELTY.md), [`docs/PRIOR_ART.md`](PRIOR_ART.md).
