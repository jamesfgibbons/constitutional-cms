# Changelog

All notable changes to Constitutional CMS are documented here. This project follows [Semantic Versioning](https://semver.org/).

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
