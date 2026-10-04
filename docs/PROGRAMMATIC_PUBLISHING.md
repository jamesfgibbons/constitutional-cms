# Governed Programmatic Publishing

**Provenance mode: synthetic.** This guide is an application pack, not a new
protocol. It shows how a business can turn structured catalogue data into a
page family without installing VIBEnet, running High Command, or adopting any
preferred coding agent.

> Turn structured business data into useful, searchable pages—with controlled
> claims, consistent representations, and proof of what was published.

That is the promise. It is not “generate thousands of SEO pages.”

Passing the checks in this pack does **not** establish search-policy compliance
and does **not** guarantee rankings. Google’s scaled-content policy (and any
other search program) remains an external platform rule. A green receipt here
is publishing governance, not a ranking certificate.

```
Canonical question: how does an implementation apply the existing publishing
contract to a generated page family?
Governs: contract mappings, synthetic fixtures, acceptance tests, and
implementation guidance for programmatic page families
Must not be used as: a fifth web-conformance profile, a G0–G5 substitute, a
site compiler, or universal SEO law
```

## Distinction

| Layer | Owns | This pack |
| --- | --- | --- |
| Constitutional CMS | Portable contracts, schemas, validators, fixtures, public releases | Application mapping only |
| A programmatic-publishing application | Implementing the contract for a page family | The synthetic example and tests |
| High Command | Work that changes either layer | Out of scope |
| Future `governed-publishing-starter` | A runnable publisher that would pin a CMS release | Deferred — mentioned only as a future home |

Constitutional CMS defines the publishing contract. A programmatic-publishing
application implements it. This repository does not ship a site compiler. The CLI is not a site compiler.
The public CLI evaluates evidence and writes receipts
([`CLI.md`](CLI.md), [`MERGE_IS_NOT_SHIP.md`](MERGE_IS_NOT_SHIP.md)). It does
not compile pages, campaigns, or catalogues.

Three separate deliveries, only the first of which is this PR:

| | Delivery | Status |
| --- | --- | --- |
| A | Publish spec, synthetic fixtures, and tests | This pack |
| B | Release a runnable implementation | Deferred (`governed-publishing-starter`) |
| C | Deploy a public demo | Deferred |

A business can use (A) without (B) or (C). Copy the mappings, write fixtures
against the existing contracts, and enforce them in whatever publisher you
already run.

## What this pack is not

- Not a fifth web-conformance profile. The four profiles stay Foundation,
  Search, Answer and AI Retrieval, and Agentic Web
  ([`WEB_CONFORMANCE.md`](WEB_CONFORMANCE.md)).
- Not a sixth certification state. G0–G5 remains the only adoption sequence
  ([`contracts/page_family_certification_v1.yaml`](../contracts/page_family_certification_v1.yaml)).
- Not universal SEO law extracted from any private travel or publisher stack.
  Indexability follows an **explicit page-family policy**, not “every page
  missing a primary number must be `noindex`.”
- Not a requirement to adopt Root/Book/Fly, Cloudflare, React, Railway, or any
  other vendor topology. Shared claims retain meaning, evidence identity, and
  qualifications across projections — the surfaces themselves are the
  implementer’s choice.
- Not permission to treat source failure as entity retirement. A missing
  metric is not a delete. An unavailable feed is not a `404`.

Operational registries, private thresholds, customer records, production
identifiers, and High Command traces stay out of this repository
([`SOURCE_BOUNDARY.md`](SOURCE_BOUNDARY.md)).

## How to apply the existing schemes

Do not invent a new numbered scheme. Identify the question, then use the
scheme that already owns it ([`PROTOCOL_MAP.md`](PROTOCOL_MAP.md)).

| Question for a page family | Existing scheme | What an application does |
| --- | --- | --- |
| What part of publishing is governed? | Five contract families (`page_types`, `enrichment_stages`, `link_rules`, `snapshot_boundary`, sprint) | Declare product, collection, and comparison families; name write/read agents |
| What must remain true? | Incident-learned invariants | Keep quality ≠ indexability; timeouts ≠ absence; rendered truth beats resolver intent |
| How completely has the family adopted the framework? | G0–G5 | Register the family (G1) through corpus-certified monitoring (G5). A page tier is not a G-state |
| Which selectable evidence grouping applies? | Four web-conformance profiles | Attach Foundation / Search / Answer / Agentic checks to the evidence you actually collect. Profiles are not levels |
| What evidence must a candidate pass before it is current? | Eight release gates, read through [`promotion_protocol_v1.yaml`](../contracts/promotion_protocol_v1.yaml), [`proof_ledger.yaml`](../contracts/proof_ledger.yaml), and [`MERGE_IS_NOT_SHIP.md`](MERGE_IS_NOT_SHIP.md) | Publish artifacts, evaluate the cohort, move one pointer, probe the wire. Merged ≠ served ≠ accepted |
| Which dependent layer on one surface is repaired first? | Four-layer repair stack | Data truth → content truth → depth → experience. A broken inventory feed is Level 1; a comparison narrative is Level 3 |
| Which unlike intervention deserves attention next? | Seven control priority classes | Use them across unlike work. Do not score a page family with them |
| Does the subject still exist? | [`entity_lifecycle.yaml`](../contracts/entity_lifecycle.yaml) | Gone requires terminal authority. Source failure is a forbidden trigger |
| What may we currently say? | [`claim_decision.yaml`](../contracts/claim_decision.yaml), Claim Gate v0.1 (DRAFT) | Admitted sources with scope, units, dates, rights. Integrity ≠ truth |
| Did delivery change an external objective? | [`outcome_record.yaml`](../contracts/outcome_record.yaml) | Impressions, conversions, and revenue stay off the delivery receipt |

Work priority is not a publication tier. A release gate is not a conformance
profile. Maturity (G0–G5) is not a check-catalog score.

## Precedence for this synthetic domain

`page_types.yaml` (including word-count floors and “suppress when a source is
unavailable”) and `entity_lifecycle.yaml` answer different questions. Leaving
adopters to invent the interaction is how source failure becomes a `410`.

For the Northline Desk Co. catalogue in
[`examples/programmatic-publishing/`](../examples/programmatic-publishing/):

| Decision | Winning authority | Losing authority may only |
| --- | --- | --- |
| Does the product still exist? May we emit `410 Gone`? | `entity_lifecycle.yaml` | `page_types.yaml` may degrade or withhold. It may not retire |
| What quality tier is this URL at? | Family `page_types` in `domain-example.yaml` | Lifecycle state does not pick FULL / BASIC / SHELL |
| May this claim appear in HTML, JSON-LD, or a table? | `claim_decision.yaml` | A renderer may suppress further, never upgrade |
| May crawlers index this URL? | Family `indexability_policy` + `page_health_resolver.yaml` | Missing a primary number does not imply `noindex` |
| Is the served body the accepted candidate? | `promotion_protocol_v1.yaml` + proof ledger | A green pre-merge audit does not prove the wire |
| Did anyone buy or rank? | `outcome_record.yaml` | Delivery evidence cannot fill `actual` |

**Rule, portable form:** source failure cannot alone establish permanent
entity retirement. `page_types` degradation and family-declared `SUPPRESS`
control *emission and discovery*. Terminal artifacts require
`lifecycle_authority`, `evidence_reference`, `reason_code`, `effective_at`,
and `terminal: true`.

The reference `contracts/page_types.yaml` example still says `SUPPRESS`
returns `404` when a “data source [is] permanently unavailable.” That wording
collapses two courts. Until the owning contract is amended, **this pack
declares the opposite for the synthetic domain** and records the gap below
rather than hiding it.

## Lifecycle (each row is demonstrated)

The synthetic catalogue and `tests/test_programmatic_publishing.py` exercise
every row.

| # | Requirement | Existing contract | Synthetic demonstration |
| --- | --- | --- | --- |
| 1 | **Page-family purpose** — which user question; required evidence | `page_family_certification_v1.yaml` family registration; `page_types.yaml` required fields | Product / collection / comparison each name a question and the evidence that answers it |
| 2 | **Entity and relationship lifecycle** — missing metric ≠ auto-delete | `entity_lifecycle.yaml`; `page_health_resolver.yaml` `unknown_is_not_unsupported` | Inventory feed fails; the product stays `active`; artifact stays `publish` / `degraded` |
| 3 | **Claim authority** — admitted sources with scope, units, dates, rights | `claim_decision.yaml`; Claim Gate v0.1 (integrity only); `sensor_integrity.yaml` | List price is sourced from `canonical_snapshot` with unit `USD` and `observed_at` |
| 4 | **Cross-surface consistency** — shared claims consistent; page-specific permissions may differ | `signal_projection.yaml` `one_state_many_renderers`; `claim_decision.yaml` `schema_matches_visible_claims`; certification `P0-3_state_divergence` | HTML / JSON-LD / comparison cell / collection card must agree on the same `claim_id` when they publish it. A comparison page may omit inventory while the product page publishes it |
| 5 | **Presentation** — static answer, chart, table, machine-readable from the same approved inputs | `signal_projection.yaml`; `snapshot_boundary.yaml`; consuming-layer law | Projections copy the snapshot. They do not recompute price at render time |
| 6 | **Discovery policy** — canonical / robots / sitemap / internal-link follow declared family policy | `page_health_resolver.yaml`; `link_rules.yaml`; publishing heuristics (`children_require_hub` is `soft_warn`) | Indexability is an explicit family policy. SHELL is not automatically `noindex` |
| 7 | **Release and acceptance** — tested candidate connected to the artifact actually served | `promotion_protocol_v1.yaml`; `cache_materialization.yaml`; `proof_ledger.yaml`; `MERGE_IS_NOT_SHIP.md` | Wrong generation on the wire → acceptance `failed`, not `live_verified` |
| 8 | **Outcome measurement** — delivery evidence separate from impressions / conversions / revenue | `outcome_record.yaml` `delivery_is_not_outcome` | A matching served hash does not write impression `actual`s |

## Portable extraction rules

Correct framing, with the private-law form this pack refuses:

| Portable rule | Not a portable rule |
| --- | --- |
| Indexability follows explicit page-family policy | “Every page missing a primary number must be `noindex`” |
| A shared claim retains meaning, evidence identity, and qualifications across projections | “Every site needs Root / Book / Fly” |
| Source failure cannot alone establish permanent entity retirement | “Unavailable source → `404`” |
| Quality tier decides schema, links, and narrative depth | Quality tier *is* lifecycle |
| Merged / built / promoted / served / accepted are distinct relations | A green CLI audit means the page is live |
| Delivery proof is not an outcome | Impressions may be inferred from a deploy |

## Synthetic domain

[`examples/programmatic-publishing/`](../examples/programmatic-publishing/) is
a fabricated desk-goods catalogue (Northline Desk Co.). It is ecommerce, not
travel. Records are synthetic and non-sensitive.

| Family | User question | Required evidence |
| --- | --- | --- |
| Product | What is this product, what does it cost, and what is its availability? | Identity; list price or typed withhold; inventory or typed withhold |
| Collection | Which products are in this set, and what do they cost? | Collection identity; child product refs that still exist |
| Comparison | How do these two products differ on governed specs and price? | Both product snapshots at BASIC or above; spec table from the same claims |

Three controlled failures live under `fixtures/` with matching `expected/`:

1. **Price changed in one channel.** HTML shows a different list price than
   the governed snapshot. The parity test records `price_parity_contradiction`.
   The entity stays `active`.
2. **Inventory feed failed.** The product remains a legitimate entity. The
   inventory claim is withheld. The evaluator refuses an invented zero and
   refuses retirement.
3. **Deployment served the wrong version.** Candidate generation and content
   hash do not match the served artifact. Acceptance is `failed`.

## Implementation guidance

1. **Register the family** in the operating CMS
   (`page_family_certification_v1.yaml` `family_registration`). Name the
   question, fact authority, allowed and forbidden claims, and indexability
   rules *before* generating URLs.
2. **Keep a snapshot boundary.** Write agents materialize product state. Read
   agents project it. If the renderer needs a field, the write agent adds it
   to the snapshot ([`snapshot_boundary.yaml`](../contracts/snapshot_boundary.yaml)).
3. **Decide claims before copy.** A fact is not a public claim until
   `claim_decision` assigns `publish` / `suppress` / `hold` with source class,
   scope, units, dates, and rights.
4. **Project, do not recompute.** HTML, JSON-LD, comparison tables, collection
   cards, and any later chart or agent payload read the same approved inputs
   ([`CONSUMING_LAYER.md`](CONSUMING_LAYER.md)).
5. **Degrade on the claim axis, not the existence axis.** Unavailable inventory
   withholds the inventory claim and may drop FULL → BASIC. It does not
   unpublish the product.
6. **Discover from policy plus rendered truth.** Sitemap and internal links
   follow the family policy *and* what the wire actually returned
   (`rendered_truth_authority`).
7. **Accept on the served artifact.** Record `candidate_generation_id` and
   `content_hash`. Probe the wire. `proof_ledger` status `live_verified`
   requires that match in the same packet.
8. **Store outcomes separately.** Do not backfill revenue or impressions from
   a promotion receipt.

Repair order on one surface: fix the feed (Level 1) before rewriting
comparison prose (Level 3). Across unlike work, use control priority classes —
do not invent a programmatic-SEO backlog scheme.

## Public CLI and the future starter

```bash
constitutional-cms audit \
  --evidence examples/hello-site/evidence.yaml \
  --out receipt.json
```

That command judges a normalized `EvidenceBundleV1`. It is not a compiler, not
a catalogue generator, and not proof that a candidate was served. Use it to
evaluate evidence you already collected.

A future `governed-publishing-starter` would pin a Constitutional CMS release
and ship a runnable publisher. This pack is not that starter. Do not treat
anything in this repository as a substitute for it.

Optional adjacent work, not required to use this pack: Evidence Harness,
targeted-impressions-skills, and Open Demand OS remain separate repositories.

## Proposed contract amendments (TODOs, not landed)

Where the existing wording contradicts the portable rule, the gap is named
here. This PR does **not** silently rewrite the owning contracts.

### TODO-PP-1 — `contracts/page_types.yaml` SUPPRESS / source-unavailable

**Owning contract:** `page_types.yaml` (propose v1.1.0; keep v1.0.0 readable).

**Gap:** The example `SUPPRESS` trigger is “Entity deprecated or data source
permanently unavailable” and the header says SUPPRESS “Returns 404.” That
lets a missing source authorize a terminal-looking artifact, which
`entity_lifecycle.yaml` `forbidden_triggers` (`evidence_source_timeout`,
`evidence_source_error`, `no_recent_observation`, …) forbids.

**Proposed amendment:** State that `SUPPRESS` is a *discovery and emission*
decision (sitemap, schema, links, optional `noindex`). `404` / `410` / hard
delete require an `entity_lifecycle` terminal transition. “Source unavailable”
is a degradation or claim-withhold trigger, not a terminal trigger. Word-count
floors remain quality-tier rules.

### TODO-PP-2 — `examples/ecommerce-catalog/page_types.yaml` teaching copy

**Owning example:** `examples/ecommerce-catalog/` (after TODO-PP-1).

**Gap:** `SUPPRESS` is “Product discontinued AND no pricing in 90+ days”;
null `price_usd` degrades to SHELL. Fine as a quality rule, easy to misread
as “no price → disappear.”

**Proposed amendment:** Adopt this pack’s precedence note: discontinue only
with terminal authority; missing price withholds the price claim and degrades
tier.

### TODO-PP-3 — `contracts/claim_decision.yaml` shared-claim projections

**Owning contract:** `claim_decision.yaml` (propose a new `decision_rules` id).

**Gap:** `schema_matches_visible_claims` and `agent_api_matches_public_claim_state`
cover two surfaces. Collection cards and comparison cells are also projections
of the same `claim_id`. Certification `P0-3_state_divergence` already forbids
the contradiction, but the claim-decision contract is the natural owner.

**Proposed amendment:** Add `shared_claim_projections_must_agree`: when two
surfaces publish the same `claim_id`, they must retain meaning, evidence
identity, units, dates, and qualifications. Page-specific *permissions* may
still differ (comparison may omit inventory while the product page publishes
it). Do not add a fifth web-conformance profile for this.

These three TODOs are the only contract-amendment proposals opened by this
pack. Nothing in the guide is a silent fifth profile.

## See also

- Worked files: [`examples/programmatic-publishing/`](../examples/programmatic-publishing/)
- Tests: [`tests/test_programmatic_publishing.py`](../tests/test_programmatic_publishing.py)
- [`PROTOCOL_MAP.md`](PROTOCOL_MAP.md) · [`CONSUMING_LAYER.md`](CONSUMING_LAYER.md)
- [`WEB_CONFORMANCE.md`](WEB_CONFORMANCE.md) · [`CLAIM_GATE.md`](CLAIM_GATE.md)
- [`MARTECH_CONTROL_LOOP.md`](MARTECH_CONTROL_LOOP.md) (resolver ≠ compiler ≠ channel)
