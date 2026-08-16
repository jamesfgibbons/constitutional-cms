# Public Adapter Boundary

An adapter translates an implementation's authority into a public normalized record. It does not publish the
authority itself.

For internal links, the portable evaluator consumes a `LinkGraphEvidenceV1` containing versioned adapter identity,
a source record, and target `LinkTargetV1` records. Each target carries canonical URL, existence, page family,
publication tier, indexability, inbound/outbound eligibility, observation time, and an opaque authority identifier.
The evaluator can therefore falsify phantom or ineligible links without knowing a product's tables, queries, route
registry, thresholds, deployment topology, or incident history.

## Included public adapters

- Sitemap collectors can declare the public URL universe.
- Static generators can emit normalized records from their build route manifest.
- The synthetic records in `examples/link-targets/` demonstrate eligible and ineligible targets.
- `schemas/link_target_v1.schema.json` and `schemas/link_graph_evidence_v1.schema.json` define the public wire shapes.

## Private adapter contract

A private adapter:

1. reads the product's canonical route and readiness authority;
2. makes the product-specific eligibility decision privately;
3. emits a normalized `LinkGraphEvidenceV1`, including separate source-outbound and target-inbound decisions;
4. never emits credentials, connection strings, queries, internal table names, or private thresholds; and
5. fails loud when its authority is unavailable, causing `UNMEASURED` rather than an empty successful corpus.

The public `ConstitutionalSiteManifestV1` names an adapter by opaque authority ID. It contains configuration choices,
not implementation details.

The evaluator requires every internal URL and redirect to remain on the declared canonical origin. Identical target
records are deduplicated deterministically. Conflicting duplicates, stale records, malformed redirects, or invalid
authority records produce `UNMEASURED`; ineligible but valid source or target decisions produce `FAIL`.
