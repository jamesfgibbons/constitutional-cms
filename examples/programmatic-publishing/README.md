# Governed Programmatic Publishing (synthetic)

**Provenance mode: synthetic**

Northline Desk Co. is a fabricated desk-goods catalogue. It is not a customer,
a production deployment, or a measured outcome. It exists so the
[application pack](../../docs/PROGRAMMATIC_PUBLISHING.md) can show product,
collection, and comparison pages answering to the existing Constitutional CMS
contracts.

The public CLI is not a site compiler. These files are fixtures for
`tests/test_programmatic_publishing.py`. They do not generate a website.

## Promise

Turn structured business data into useful, searchable pages—with controlled
claims, consistent representations, and proof of what was published.

Passing the pack tests does not establish search-policy compliance or
guarantee rankings.

## Layout

| Path | Role |
| --- | --- |
| [`provenance.md`](provenance.md) | Public-safe origin statement |
| [`domain-example.yaml`](domain-example.yaml) | Domain constitution: families, claims, precedence |
| [`fixtures/`](fixtures/) | Baseline plus three controlled failures |
| [`expected/`](expected/) | Acceptance verdicts the tests compare against |

## Page families

| Family | Question | URL pattern |
| --- | --- | --- |
| Product | What is this product, what does it cost, and what is its availability? | `/products/{slug}` |
| Collection | Which products are in this set, and what do they cost? | `/collections/{slug}` |
| Comparison | How do these two products differ on governed specs and price? | `/compare/{a}-vs-{b}` |

## Controlled failures

1. `fixtures/price_parity_contradiction.yaml` — HTML list price changed without
   changing the governed snapshot. Expected: parity failure; entity remains
   active.
2. `fixtures/inventory_feed_failed.yaml` — inventory feed is `failed`. Expected:
   inventory claim withheld, no invented zero, no retirement.
3. `fixtures/served_artifact_mismatch.yaml` — wire serves a different
   generation than the accepted candidate. Expected: acceptance `failed`.

## Precedence (this domain)

`entity_lifecycle.yaml` owns existence and `410 Gone`.
`page_types` in `domain-example.yaml` owns quality tier, word-count, and
claim-emission floors. Family `indexability_policy` owns robots/sitemap.
Source failure is not a terminal trigger. See the guide for the full table.

## What this is not

- Not `governed-publishing-starter` (deferred runnable publisher).
- Not a fifth web-conformance profile.
- Not travel-domain SEO law.
- Not a replacement for `examples/ecommerce-catalog/`, which remains a thinner
  page-type sketch. This pack is the contract-mapping application.
