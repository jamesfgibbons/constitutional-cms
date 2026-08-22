# Changelog

All notable changes to Constitutional CMS are documented here. This project follows [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added
- Documented VIBEnet Signal Contract as the adjacent renderer-facing awareness layer, not a fifth web-conformance profile.
- **CheckCatalogV1 1.0.2**: Added `search.structured_data.jsonld_rfc8259` (19 checks). Catalog `framework_release` is `v0.4.2`. Shared pass_all / unmeasured-state fixtures and public goldens recreate PASS, FAIL, NOT_APPLICABLE, and UNMEASURED for the new check.
- Authority references for RFC 8259 §7 and Google's JSON-LD single-unescape behavior in standards registry.
- Test fixtures and golden receipts covering PASS, FAIL, NOT_APPLICABLE, and UNMEASURED verdict states for the new check.

## [0.4.2] - 2026-08-16

### Added
- Public recreate-a-check path: catalog → EvidenceBundle → evaluator → golden receipt.
- Explicit LinkTarget / private-adapter boundary so product route registries stay out of the public protocol.

### Notes
- No new catalog checks. Site diagnostics remain uncertified.

## [0.4.1] - 2026-08-15

### Fixed
- Applicability is evaluated before check evidence, so a valid false declaration returns `NOT_APPLICABLE` even when check evidence is absent.
- Missing, stale, invalid, and unavailable evidence now return `UNMEASURED` with stable reason codes; wrong-typed evidence can no longer become a policy `FAIL`.
- Receipt time and identity are deterministic from an explicit `--as-of` value or the bundle's `collected_at`, with canonical catalog, evidence, context, and result digests.
- Public golden receipts make the Python/JavaScript parity boundary independently reproducible.
- The internal-link boundary now validates versioned `LinkGraphEvidenceV1` and `LinkTargetV1` records, canonical-origin membership, freshness, source/target eligibility, redirects, and conflicting duplicates.

### Notes
- This patch adds no checks and does not change the four profiles. It corrects the existing `ConformanceReceiptV1` semantics.

## [0.4.0] - 2026-08-15

### Added
- One web-conformance standard with Web Foundation, Search, Answer and AI Retrieval, and Agentic Web profiles.
- Versioned standards registry, check catalog, evidence bundle, public-safe site manifest, and conformance receipt contracts.
- JSON Schemas, offline Python reference evaluator, deterministic synthetic verdict fixtures, and private-adapter boundary.
- Reproducible internal-link evidence through normalized `LinkTargetV1` records.

### Changed
- G0-G5 is now explicitly the sole adoption and certification sequence; profiles and publication tiers are not maturity levels.
- The protocol map now admits new taxonomies only when their canonical question, governed object, role, and retirement relationship are declared.
- Lab performance, field Core Web Vitals, platform eligibility, and experimental agent interfaces use distinct evidence and claim language.

### Notes
- The evaluator performs no network access and does not certify a page family. Private implementations collect evidence and retain their route authorities, schemas, thresholds, and credentials.

## [0.3.2] - 2026-08-15

### Added
- Canonical protocol map declaring which taxonomy answers which question.
- Public/private release and source boundary.
- Explicit synthetic provenance documentation for examples and test fixtures.
- Probe `mutation_class` vocabulary: `pure_read`, `read_with_side_effect`, and `active_perturbation`.
- `UNMEASURED` output when page-health probe inputs are absent.
- Portable `outcome_record.yaml` for append-only external results, with delivery proof kept distinct from outcome proof.

### Changed
- Contract validation and unit tests are blocking on pull requests and `main`.
- The sample page-health report runs as a separate non-blocking observer job.
- GitHub Actions dependencies are pinned to immutable commit SHAs.
- Public language no longer relies on private incident detail or unsourced implementation outcomes.

### Notes
- Portable contracts remain authoritative in this repository. Private mappings, thresholds, incidents, and operating receipts remain outside the public release.

## [0.3.1] - 2026-08-14

### Added
- `contracts/deploy_cadence.yaml` — time-indexes scheduled enrichment windows and promoted generations. Empty days are `not_observed`, never a zero.
- Calendar projection surface on `contracts/signal_projection.yaml` (v1.1.0). Daily multi-level deploys project through the same canonical state as HTML, APIs, and audio.

### Changed
- Signal projection principle now names calendar as a first-class renderer. The calendar cannot invent deploys, advance the relation ladder, or treat a scheduled stage as a promotion.

### Notes
- Docs/contract release. Promotion protocol core invariant is unchanged: one authoritative `promoted_generation_id`.

## [0.3.0] - 2026-08-14

### Changed
- Rewrote the public README as a scannable constitution: table of contents, five-contract index, grammar fixes, and a homepage link to [constitutionalcms.com](https://constitutionalcms.com).
- Clarified that SERP Radio is modeled after this repo.

### Added
- CONTRIBUTING.md encoding the human-review boundary, contract-as-test cadence, and what belongs in the public repo.

### Notes
- Docs-only release. No contract schema changes.

## [0.2.0] - 2026-05-04

### Added
- `docs/V0_2_REFERENCE_PATTERNS.md` documenting four public-safe reference patterns: contract-as-test, page-family render tiers, cache write authority, and the readiness invariant ladder.

### Changed
- Clarified in the README that Constitutional CMS is the act of making implicit contracts explicit, not a bolt-on product feature.
- Linked the new v0.2 reference-pattern layer from the main public entrypoint.

### Notes
- This is a docs-only release. It publishes abstractions and methodology, not private contract details from any single implementation.

## [0.1.2] - 2026-05-02

### Added
- Sanitized incident-learned invariants for page health, rendered truth, cache warming, registry authority, and public claim suppression.
- Generic contracts for page health resolution, cache materialization, claim decisions, and mobile table/card layouts.
- Observe-only page health validator with fixture tests and a sample GitHub Actions workflow.

### Changed
- Clarified that `SHELL` quality tier does not automatically imply `noindex`.
- Replaced public README examples with domain-neutral entity examples.

## [0.1.1] — 2026-04-16

### Added
- `runtime/SPEC.md` — runtime specification defining the container isolation contract for constitutional workstreams. Three MUST-level invariants: contracts mount read-only, working directories are ephemeral, publish gates run in the build.
- README section introducing runtime governance as a peer concept to contract governance.

### Notes
- This is a docs-only release. No changes to existing contracts. Fully backward compatible with v0.1.0.
- Reference implementation of the runtime specification (Dockerfile, compose example, validation hooks) planned for v0.2.0.

## [0.1.0] — 2026-04-15

### Added
- Initial public release.
- Contract system: `page_types.yaml`, `enrichment_stages.yaml`, `link_rules.yaml`, `snapshot_boundary.yaml`, and supporting example contracts.
- README, NOVELTY, and PRIOR_ART documentation.
- Apache 2.0 license.
