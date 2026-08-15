# Public Adapter Boundary

An adapter translates an implementation's authority into a public normalized record. It does not publish the
authority itself.

For internal links, the portable evaluator consumes `LinkTargetV1`: canonical URL, existence, page family,
publication tier, indexability, inbound/outbound eligibility, observation time, and an opaque authority identifier.
The evaluator can therefore falsify phantom or ineligible links without knowing a product's tables, queries, route
registry, thresholds, deployment topology, or incident history.

## Included public adapters

- Sitemap collectors can declare the public URL universe.
- Static generators can emit normalized records from their build route manifest.
- The synthetic records in `examples/link-targets/` demonstrate eligible and ineligible targets.

## Private adapter contract

A private adapter:

1. reads the product's canonical route and readiness authority;
2. makes the product-specific eligibility decision privately;
3. emits only normalized `LinkTargetV1` records and optional SHA-256 artifact hashes;
4. never emits credentials, connection strings, queries, internal table names, or private thresholds; and
5. fails loud when its authority is unavailable, causing `UNMEASURED` rather than an empty successful corpus.

The public `ConstitutionalSiteManifestV1` names an adapter by opaque authority ID. It contains configuration choices,
not implementation details.
