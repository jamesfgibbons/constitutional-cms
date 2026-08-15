# Contributing

Constitutional CMS is a governance spec, not a product feature. The public repo holds the portable pattern. Domain mappings, thresholds, and operating playbooks stay private.

## The security boundary

Agents prepare work. Humans review and merge.

- Open a pull request. Do not push directly to `main`.
- Keep PRs small and reviewable. One contract tightening per PR is the intended cadence.
- A change is not done when CI is green. It is done when the live surface still satisfies the contracts it claims to enforce.

## Before you write code

1. Read the [priority stack](README.md#the-priority-stack). If Level 1 is broken, do not work on Level 3.
2. Read the relevant contract in `contracts/` before touching anything it governs.
3. Identify your boundary in `contracts/snapshot_boundary.yaml`. Write agents write. Read agents read. Do not cross.

## What belongs here

**In scope**

- Clarifying the public contract model
- Adding or tightening portable YAML examples
- Improving validators and observe-first probes
- Documenting incident-learned invariants without leaking private mappings
- Domain-neutral examples that help someone adopt the pattern

**Out of scope**

- Proprietary entity registries, route maps, or threshold tables
- Prompt packs, voice controls, or enrichment recipes
- Internal eval baselines and scoring heuristics
- Aspirational language that does not map 1:1 to shipped behavior

## Contract changes

Every contract gap should become a regression test.

1. Name the rule.
2. State the failure it prevents.
3. Add one test or probe that would have failed before the fix.
4. Make future changes answer to that test.

See [`docs/V0_2_REFERENCE_PATTERNS.md`](docs/V0_2_REFERENCE_PATTERNS.md).

## Language

Aspirational copy is excluded from specs.

- Not a spec: “the page should feel alive”
- A spec: `BPM = 60 + (energy × 100)`

If a line cannot be verified against live output, it does not belong in a contract.

## Validation

```bash
python scripts/validate_contracts.py
python -m pytest
```

The page-health validator is observe-only by default. It reports. It does not silently become a blocking gate.

## Voice

Write as if the contract will be read by an agent that will follow it literally. Be specific. Prefer named states over adjectives. Prefer failure modes over slogans.
