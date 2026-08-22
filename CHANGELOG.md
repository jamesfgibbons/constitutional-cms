# Changelog

All notable changes to Constitutional CMS are documented here. This project follows [Semantic Versioning](https://semver.org/).

## [Unreleased]

## [0.5.0] - 2026-08-22

**Run the Constitution.** This is the distribution release: one framework identity, a wheel that works outside the clone, and a receipt-first CLI.

### Added
- Packaged CLI as the developer conversion surface. `constitutional-cms audit --evidence` evaluates a normalized `EvidenceBundleV1` against the bundled catalog and writes a `ConformanceReceiptV1`. Optional `audit <url>` performs one read-only GET for public-static evidence only.
- `--version` and opt-in `--fail-on FAIL` / `--fail-on FAIL,UNMEASURED`. Default `audit` is receipt-first: it writes a valid receipt and exits 0. A catalog `FAIL` does not block a release unless CI asks it to.
- Catalog, JSON Schemas, evaluator, and contract validator ship inside `constitutional_cms/` via `importlib.resources`, so a clean wheel works from `/tmp`. `scripts/conformance_evaluator.py` and `scripts/validate_contracts.py` remain thin re-exports.
- `constitutional-cms validate` with no arguments checks bundled catalog/schema coherence (19 checks, catalog 1.0.2, framework `v0.5.0`). A local contracts directory is validated when present or when a path is passed.
- Synthetic `examples/hello-site/` fixture for the README quickstart.
- Clean-wheel smoke in CI: install the built wheel outside the repository and run `--help`, `validate`, and `audit`.
- **CheckCatalogV1 1.0.2** (already on `main`, now released under this framework identity): `search.structured_data.jsonld_rfc8259` (19 checks). Shared pass_all / unmeasured-state fixtures and public goldens recreate PASS, FAIL, NOT_APPLICABLE, and UNMEASURED for the new check.
- Authority references for RFC 8259 §7 and Google's JSON-LD single-unescape behavior in the standards registry.
- Documented VIBEnet Signal Contract as the adjacent renderer-facing awareness layer, not a fifth web-conformance profile.

### Changed
- Framework release, Python package, git tag, and catalog `framework_release` pin are all `v0.5.0` / `0.5.0`. Do not publish this tree as `0.4.2`: the existing `v0.4.2` tag points at `951b09d`, before the CLI package and the nineteenth check.
- README opening is the adoption screen (category, website/CLI distinction, install, fixture, sample receipt, non-goals, contribution ladder). Historical contract material stays below.

### Notes
- `EVALUATOR_VERSION` remains `constitutional-cms-reference/0.4.1`. Evaluation rules did not change; distribution and identity did.
- `certified` remains `false` on the public recreate-a-check path.
- Site diagnostics remain separately labeled from catalog verdicts.

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
