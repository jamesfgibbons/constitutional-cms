# Do not let the consuming layer invent truth

This is the Realm 4 essay named in [`STORY_BIBLE.md`](STORY_BIBLE.md). Contracts and invariants in this repository are the executable form of this law. It is not a new scheme, not a CheckCatalog check, and not a style guide.

```
Canonical question: may this actuator emit a fact the producer never wrote?
Governs: every consuming layer — SSR, schema, FAQ, agent API, sitemap, CLI, checker, ambient renderer
Must not be used as: a ban on LLMs, a G0–G5 substitute, or a FAIL for UNMEASURED
```

## The law (three forms)

**Canon**

> Do not let the consuming layer invent truth.

**Architecture**

> Prompt-based AI says “tell the model not to hallucinate.” Architecture-based AI says “do not ask the model to supply truth the system never emitted.”

**Operator**

> Write agents write. Read agents read. Background jobs materialize. APIs read. Producers emit. Renderers render. If the consuming layer needs data that does not exist, **fix the producer.**

A consuming layer is any actuator another machine or person will treat as a fact: HTML, JSON-LD, FAQ, sitemaps, headers, CLI stdout, conformance receipts, ambient renderers, LLM answers over your page. It may **compose, translate, suppress, degrade, or hold**. It may not **upgrade uncertainty into a fact**.

Companion (already on `main` as [`contracts/entity_lifecycle.yaml`](../contracts/entity_lifecycle.yaml)): **do not let one truth domain revoke another’s existence.** Absence is scoped. Terminality is explicit. `410 Gone` is a verdict, not a missing-fact fallback.

## Does this reduce AI slop?

**Yes — the kind that matters. No — not all “slop.”**

“AI slop” in the viral sense is abundant downstream generation with no authored upstream. This law does not starve generation. It forbids generation from **standing in** for missing state. The precise name is **unauthorized certainty**: output that looks like knowledge without substrate.

| It cuts | It does not |
|---|---|
| Hallucinated numbers, fallback prices, silent zeros | Make prose beautiful |
| Schema or FAQ that contradict a suppression block | Ban LLMs from writing a sourced `narrative_block` |
| Composite scores, `certified: true` on a public recreate path, scoring a login wall as the page | Fill a missing collection hub at GET time |
| Advertising `uvx` while the package 404s | Cure generic cadence (that is inbound / Two Clocks, not this law) |
| A leaf URL implying a collection the system never authored | Make SHELL pages “feel rich” |

Thin-but-honest is not slop: SHELL, `UNMEASURED`, typed absence, a quiet CLI that writes `certified: false`. Confident filler is slop. A page that looks full while the producer never wrote the field is the failure.

## What else it is for

1. **Cross-surface consistency.** Body, FAQ, JSON-LD, agent API, sitemap, and headers share one resolver. A guard on N of M surfaces is not a guard ([Partial Guards Are False Signal](INCIDENT_LEARNED_INVARIANTS.md)).
2. **Multi-agent contract drift.** The snapshot is the handshake. Read agents do not compute primary data. If the field is missing, degrade — do not invent it in the loader ([`snapshot_boundary.yaml`](../contracts/snapshot_boundary.yaml)).
3. **Publish vs notice.** Constitutional CMS governs the right to publish. VIBEnet Signal Contract governs the right to notice. Neither mints the other’s truth ([`signal_projection.yaml`](../contracts/signal_projection.yaml), [`PROTOCOL_MAP.md`](PROTOCOL_MAP.md)).
4. **Receipts.** A `ConformanceReceiptV1` on the public recreate path stays `certified: false`. A Claim Gate receipt (when ratified) attests integrity and policy, not world-truth.
5. **Index and crawl integrity.** Quality tier is not indexability. A timeout is not entity absence. Rendered response beats resolver intent.
6. **Cost.** Do not spend tokens inventing a field the producer never wrote. Fix the producer; do not re-prompt the renderer.
7. **Trust that survives the next hop.** Machines re-consume your page as substrate. A prompt that says “don’t hallucinate” does not travel with the JSON-LD.
8. **Dampers.** Degrade, suppress, hold, `UNMEASURED`, `BLOCKED_BY_TARGET`. Autonomy without dampers thrashes ([`CONSTITUTIONAL_CYBERNETICS.md`](CONSTITUTIONAL_CYBERNETICS.md)).
9. **Heuristics sit under the law, not beside it.** If children exist, a collection hub should exist ([`PUBLISHING_HEURISTICS.md`](PUBLISHING_HEURISTICS.md) H1). The **leaf renderer must not invent** the index at request time. A **write agent** authors the collection. A 404 parent next to 200 children is a missing producer, not permission to synthesize a hub.
10. **Scarce-asset thesis.** AI makes downstream output cheap. Value moves to authored upstream the machine cannot safely invent (Realm 3). This law is how Realm 4 keeps that upstream from being overwritten downstream.

## Executable form (already in this repo)

| When the producer did not write it | The consuming layer does |
|---|---|
| No validated metric | SHELL / suppress the claim — no schema, no fallback price |
| Sensor failed | Not a quiet zero — sensor integrity, not “no demand” |
| Challenge / bouncer page | `BLOCKED_BY_TARGET` — do not score the wall as the document |
| Evidence missing | `UNMEASURED`, never FAIL-by-silence |
| Public recreate-a-check | `certified: false` |
| Canonical state exists | Project it (HTML, schema, audio, API). Do not mint a second truth per medium |

Every incident-learned invariant in this repository is an application of the same sentence.

## Worked example: children without a hub

Provenance: `public_live_source`, 2026-08-25.

A family of entity URLs `/collection/{slug}` can return 200 while `/collection` returns 404, even while a family sitemap is public. Sibling families on the same site may already have index hubs.

**Wrong fix (inventing truth):** the child template, at GET time, synthesizes a parent index from whatever slugs it can see.

**Right fix (law + heuristic):** the leaf keeps telling the truth it has. A write agent authors the collection hub (or Chair documents typed absence / `SUPPRESS` and removes the public sitemap). `children_require_hub` stays `soft_warn` until a founder ratifies `hard_block`.

## What this law is not

- Not anti-AI. Agents may write; they may not mint substrate.
- Not “no LLM copy.” Narrative is allowed when it is sourced from the snapshot.
- Not a category phrase. The product category stays *open-source publishing governance for AI-built websites.*
- Not VIBEnet’s law. VIBEnet is a renderer of awareness. This law is the publish OS.
- Not a CheckCatalog check and not a G0–G5 substitute.
- Not a reason to fail UNMEASURED.

## How to say it

Do not mint a second slogan. Gloss by audience; keep the title.

| Audience | Gloss |
|---|---|
| First screen / About | Govern what agents publish. Prove it with a receipt. |
| Architects | Consuming layer cannot invent truth. |
| Prompt vs architecture | Do not ask the model for truth the system never emitted. |
| Operators | Write/read split. Fix the producer. |
| SEO / publishing | No fallback claims. SHELL emits neither schema nor invented parents. |
| AI-search / answers | `UNMEASURED` is a public state. `certified: false` is correct. |
| Anti-slop discourse | Unauthorized certainty — not “stop generating.” |
| VIBEnet-adjacent | Renderers project; they do not create. |
| MarTech | Resolver decides what may be said. Compiler builds one generation. Channels only render. CDP is not automatically source of truth. Generative AI is a compiler assistant, not claim authority. See [`MARTECH_CONTROL_LOOP.md`](MARTECH_CONTROL_LOOP.md). |

If a sentence sounds like a second product (“web conformance framework,” “cybernetics for agents,” “anti-AI CMS”), it is the wrong description.
