# Changelog

All notable changes to Constitutional CMS are documented here. This project follows [Semantic Versioning](https://semver.org/).

## [Unreleased] — v0.6.0-dev (pre-ratification)

### Added — Claim Gate v0.1 (DRAFT: not ratified until the founder tags a release)
- **ClaimBundleV0_1** (`schemas/claim_bundle_v0_1.schema.json`): frozen, hashed, Ed25519-signed claim core. Volatile facts forbidden inside; `bundle_hash` and the signature cover the same canonical bytes (house `docs/CANONICAL_JSON.md` procedure, one code path). Bundle `valid_until` MUST equal the earliest claim `valid_until` — earliest-expiry-governs is verifier-enforced.
- **ClaimReceiptV0_1** (`schemas/claim_receipt_v0_1.schema.json`): volatile verification record quoting `bundle_hash`. Verifies integrity + policy conformance, never truth. Deterministic `receipt_id` (`cr_…`); supersession annotations live outside `receipt_hash` so superseding never mutates the old receipt's hashed core.
- `constitutional_cms.claims`: `build_bundle`, `sign_bundle`, `verify_bundle`, `verify_receipt`, plus `generate_keypair` and `supersede_receipt`. Ed25519 via the new optional extra `constitutional-cms[claims]` (base install stays PyYAML + jsonschema); a clear import-guard error names the extra.
- CLI verbs `claim-bundle`, `claim-sign`, `claim-verify` — fully offline against a local keys file; exit 0 verified, 1 refused (typed reason), 2 operational error. Private keys are file paths (or `CONSTITUTIONAL_CMS_CLAIM_KEY`); key material is never printed.
- `docs/CLAIM_GATE.md`: five-minute boundary spec — canonicalization, signing, expiry, supersession, `/.well-known/constitutional-cms/keys.json` convention (spec only), the minimal HTTP surface as normative-future, and the strict-consumer contract (verify → use, else reject).
- Technical-constitution test suite (`tests/test_claim_gate.py`) with byte-stable golden pairs in `tests/golden-claims/` (verified / tampered / expired / unmeasured / unknown-key / expiry-mismatch / superseded), TEST ONLY fixture keys, and an independent-reproduction test that re-derives hash + signature through a separate minimal code path.
- New reason codes (documented in the spec): `bundle_verified`, `bundle_malformed`, `hash_mismatch`, `signature_invalid`, `key_unknown`, `issuer_mismatch`, `bundle_expired`, `expiry_mismatch`, `claims_unmeasured`.
- **ClaimKeysV0_1** (`schemas/claim_keys_v0_1.schema.json`): the keys document is now a validated artifact. It MUST declare the `issuer` it publishes keys for; a key entry carries exactly `key_id`, `alg`, `public_key`.

### Fixed — adversarial review round 1 (three independent reviewers, live exploits)
- **Earliest-expiry-governs compared strings, not instants.** `min()` and `!=` ran over RFC 3339 text; `.` sorts before `Z`, so a bundle outliving its earliest claim VERIFIED (`…12:00:00Z` + `…12:00:00.999999Z`), while a law-correct bundle spelling one instant two ways (`…12:00:00Z` vs `…12:00:00.000Z`) was REFUSED. All comparisons are now on parsed instants, in `build_bundle` and `verify_bundle` alike; the spec says so normatively.
- **The issuer was never bound to the signing key.** A bundle claiming `issuer: victim-bank.example`, signed with example.com's key, verified green against example.com's own keys.json. The keys document now declares its `issuer` and a mismatch is refused with the new code `issuer_mismatch` (normative order step 4, right after key lookup).
- **Duplicate `key_id` let document ORDER pick the verdict.** First-match lookup meant an appended impostor entry could flip every legitimate bundle. A keys document containing a duplicate `key_id` is now refused fail-closed (operational, exit 2).
- **Duplicate/contradictory `claim_id` verified green.** One `claim_id` carrying both `PASS` and `FAIL` passed; consumers key by `claim_id` and got last-wins. Now `bundle_malformed`.
- **Uncaught exceptions escaped as exit 1 — the documented code for a typed refusal — with tracebacks.** `verify_bundle` and `verify_receipt` are now TOTAL over artifacts: a malformed keys entry, a bare JSON string, an uppercase-hex `bundle_hash`, an unhashable claim `value`, and impossible or leap-second timestamps (`format: date-time` is not enforced here) all become typed refusals. The bare `assert` is gone, `horizon_seconds` is bounded to 10 years, and the CLI exits 2 with one line for anything unexpected — never a traceback.

### Changed — honesty (v0.1 design limits, now stated instead of implied)
- **Receipt-only verification no longer prints `VERIFIED`.** A v0.1 receipt is UNAUTHENTICATED — anyone can mint a green-looking one. The CLI prints `RECEIPT INTEGRITY OK (unauthenticated — supply --bundle and --keys to verify the claim)`; a new spec section, "What a v0.1 receipt does NOT prove", says it plainly.
- **Supersession is an issuer-side assertion, not revocation.** `superseded`/`superseded_by` sit outside the hash by design, so a holder can strip them and the receipt still verifies. A consumer needing current state MUST consult the issuer's receipt endpoint. Authenticated supersession/revocation is deferred until earned.
- **Key `status` removed.** The field shipped in the fixture and was ignored by the code — a retired key signed fresh long-lived bundles fine. v0.1 defines no lifecycle semantics, so nothing advertises the control: a keys entry carrying `status` is refused rather than silently ignored. Revocation in v0.1 is removal from the document.
- **Portability MUST-rejects.** Duplicate JSON object members (undefined in RFC 8259, resolved differently by different parsers) are refused at parse time; JSON floats and integers beyond `2^53-1` are refused because canonicalization collapses `1.0` to `1` and emits huge literals no double-parsing implementation reproduces.

### Notes
- Portability round 4 returned YES/YES (independent implementation of verifier AND issuer). Last residual closed: an `as_of` carrying more than six fractional digits is REFUSED as an operational error (CLI exit 2), never truncated and never rounded — truncation and rounding each mint a different `verified_at`, so refusal is the only self-consistent behavior. Remaining named debt, unchanged: Unicode normalization is unspecified, and the optional `bindings` issuer policy is unspecified (issuer-direction only).
- Portability round 3 (issuer side): computed timestamps now have ONE normative spelling — UTC `Z`, fraction omitted when the microsecond field is zero, otherwise exactly six digits, normalized before the value enters `receipt_id`/`receipt_hash`. Fractional seconds are bounded to six digits in both schemas and the verifier grammar (a seventh digit is refused, not truncated), which makes exact instant comparison implementable in any language. Float refusal is scoped explicitly against `docs/CANONICAL_JSON.md` (claim artifacts refuse; conformance artifacts collapse). Keys-document prose aligned to the schema (optional free-text `comment`); duplicate `key_id` labeled as an operational refusal (exit 2). New goldens pin `issuer_mismatch`, `signature_invalid`, `bundle_malformed`, and a result-level `receipt_hash_mismatch` artifact — all ten bundle reason codes are now golden-pinned.
- Clean-room portability test (spec + fixtures only) reached 8/8 golden parity; the eight spec gaps it recorded are closed as normative text in `docs/CLAIM_GATE.md`: exact `receipt_id` derivation, explicit `as_of` clock, unmeasured-value encoding, normative refusal order (first failing check's code), both-direction `expiry_mismatch`, inclusive expiry boundary (`as_of >= valid_until`, with a boundary golden), refused-receipt `valid_until` rule, and the `bundle_mismatch` trigger (recomputed hash of the presented bundle).
- All-UNMEASURED evidence never yields a green receipt (`UNMEASURED / claims_unmeasured`).
- Deferred until earned: serving the HTTP surface and `.well-known` file, a TS verifier, authenticated (signed) receipts, authenticated supersession/revocation, key lifecycle (`status`) semantics, Unicode normalization rules for canonicalization, per-claim evidence narrowing.

### Added
- **`contracts/entity_lifecycle.yaml`** — the layer before the claim resolver. Claim governance defends against false positives: things a system asserts without evidence. It does not defend against false negatives: real things that vanish because one downstream layer had no answer. Both are authority failures, and the second is harder to see, because nothing was asserted — something was withdrawn, and a withdrawal leaves no artifact to audit. The contract separates entity identity, entity lifecycle, relationship lifecycle, claim state, and artifact state; gives `unknown` and `seasonal_inactive` first-class representation; and makes `retired` the only terminal state, reachable only through a transition carrying lifecycle authority, an evidence reference, a reason code, and an effective date. `410 Gone` is a semantic assertion that something was intentionally and permanently removed. It now requires that authority and nothing less.
- **`tests/test_entity_lifecycle_contract.py`** — an executable authority-collapse detector, not just contract prose. Five collapse patterns (`claim_absence_to_entity_absence`, `child_404_to_parent_410`, `claim_suppression_to_document_suppression`, `relationship_absence_to_entity_terminal`, `unknown_to_terminal`) with adversarial fixtures, plus the inverse case asserting an authorized retirement still produces `gone` — a repair that can no longer express a real removal has replaced one authority failure with another. Substitute any resolver for `reference_resolve` to audit an implementation.
- [`docs/MARTECH_CONTROL_LOOP.md`](docs/MARTECH_CONTROL_LOOP.md): MarTech English for the control loop. Resolver = permission engine; compiler = build step; channels = renderers. Does not add a `compile` CLI command.
- [`docs/CONSUMING_LAYER.md`](docs/CONSUMING_LAYER.md): Realm 4 essay. Consuming layer cannot invent truth; reduces unauthorized certainty (not all “slop”); write/read split; glosses. Not a new scheme.
- [`docs/PUBLISHING_HEURISTICS.md`](docs/PUBLISHING_HEURISTICS.md): law vs heuristic vs Chair gate; extraction method; `children_require_hub` as the inverse of `hub_to_children`. Not a CheckCatalog check and not a work-ordering scheme.
- `contracts/link_rules.yaml` rule `children_require_hub` (`soft_warn` only).

### Changed
- `contracts/page_health_resolver.yaml`: `unknown_is_not_unsupported` raised **P1 → P0**, and a new P0 `claim_suppression_is_not_document_suppression` added alongside it. The first rule was already correct and already published, and a production system violated it on 107 URLs against three authorized retirements, for months, while a green test asserted the collapse as intended behaviour. A rule that permanently removes public URLs when broken is not P1 — and a contract with no detector is a wish, which is why both rules now name their enforcing test.
- README first screen is the product page: verified clone + venv quickstart (PEP 668), live good-first issue links, one-line VIBEnet boundary. Long constitution moved to [`docs/CONSTITUTION.md`](docs/CONSTITUTION.md). Extra CLI flags live in [`docs/CLI.md`](docs/CLI.md). Do not promote `uvx` until PyPI serves 0.5.0.

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
