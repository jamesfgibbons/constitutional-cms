# Constitutional CMS

**A governance framework for AI agents that build websites.**

CMS used to mean Content Management System — software for humans who write pages. Constitutional CMS manages the *contracts* that govern what AI agents are permitted to publish. Same acronym, different era.

WordPress, Webflow, Drupal, and Shopify were designed for human authors. They still work for that. Constitutional CMS is designed for the gap that opens when **agents become the authors** — and nobody is checking whether the 400th page they generated has valid data, working links, or enough substance to deserve a spot in Google's index.

This the framework for [httpss](https://serpradio.com/) is modeled after this repo.

---

## The Problem

AI coding agents are remarkably good at additive feature development. They are remarkably bad at maintaining systemic coherence.

Give four agents access to the same codebase and tell them to build pages. Agent 1 adds a column to the database. Agent 3 adds a different column in the same sprint. Both changes are valid individually. Together they create a conflict that no unit test catches.

Agent 2 emits an internal link to a page that Agent 1 deleted. Agent 4 generates a schema markup on a page that doesn't have enough data to support it. The site passes CI. The site is broken.

This isn't a skill problem. The agents are skilled. It's a governance problem. Nobody told them what they *can't* do.

**Skills make agents capable. Contracts make agents trustworthy.**

---

## The Five Contracts

Constitutional CMS defines five contract types. Each is a YAML file that agents read before writing code.

### 1. Page Type Contracts

Define what data a page requires to exist at each quality tier.

```yaml
# contracts/page_types.yaml
entity_page:
  description: "A page about a specific entity in your domain"
  url_pattern: "/entities/{entity-slug}"

  tiers:
    FULL:
      required_fields:
        - entity_name
        - validated_metric  # price, score, rating, availability, etc.
        - source_snapshot
        - narrative_block   # LLM-generated, source-backed content
        - json_ld_schema
      min_word_count: 800
      schema_emission: true
      internal_links: true

    BASIC:
      required_fields:
        - entity_name
        - validated_metric
      min_word_count: 200
      schema_emission: true
      internal_links: true

    SHELL:
      required_fields:
        - entity_name
      min_word_count: 0
      schema_emission: false    # No structured data on thin pages
      internal_links: false     # No outbound links from shells

    SUPPRESS:
      description: "Page is removed from sitemap and returns 404"
      trigger: "Entity deprecated or data source permanently unavailable"
```

**Why this matters:** WordPress has "draft" and "published." Constitutional CMS has a continuous quality spectrum. Pages graduate from SHELL -> BASIC -> FULL as data accumulates, and degrade back down when data goes stale. The system handles transitions automatically based on what data exists, not on human editorial judgment.

Quality tier and indexability are separate dimensions. A degraded but legitimate URL can remain indexable while withholding schema, links, or richer narrative until it earns a higher tier. Emit `noindex` from explicit indexability policy, not from the mere fact that a page is currently in `SHELL`.

### 2. Enrichment Stage Contracts

Define the pipeline stages that produce page data, and what each stage is responsible for.

```yaml
# contracts/enrichment_stages.yaml
stages:
  - name: telemetry_ingestion
    writes_to: raw_observations
    owner: agent_1
    schedule: "0 */6 * * *"
    quality_gate:
      - "carrier field is not 'Various' or 'Unknown'"
      - "price_usd > 0"
      - "observation has valid trip_type"

  - name: snapshot_materialization
    reads_from: [raw_observations, operational_data, weather_data]
    writes_to: entity_snapshots
    owner: agent_1
    schedule: "*/5 * * * *"
    quality_gate:
      - "snapshot updated_at < staleness_threshold"
      - "VET coordinates within valid range [0, 1]"

  - name: narrative_enrichment
    reads_from: entity_snapshots
    writes_to: entity_snapshots.narrative_block
    owner: agent_5
    schedule: "0 4 * * *"
    quality_gate:
      - "word_count >= 800"
      - "entity_density >= 3 named entities"
      - "no confabulated statistics"
      - "voice compliance check passes"

  - name: schema_assembly
    reads_from: entity_snapshots
    writes_to: entity_snapshots.json_ld
    owner: agent_1
    quality_gate:
      - "page must be BASIC tier or above"
      - "all schema fields sourced from snapshot, never computed at render time"
```

**Why this matters:** Every stage has exactly one owner. No two agents write the same table. The quality gate runs before data is accepted. Bad data is rejected at ingestion, not discovered in production.

### 3. Link Graph Rules

Define what pages are allowed to link to.

```yaml
# contracts/link_rules.yaml
rules:
  - name: "no_phantom_links"
    description: "Never emit a link to a URL that doesn't exist in the page registry"
    applies_to: all_page_types
    enforcement: hard_block

  - name: "shell_isolation"
    description: "SHELL-tier pages do not emit outbound internal links"
    applies_to: pages_at_tier_SHELL
    enforcement: hard_block

  - name: "hub_to_children"
    description: "Hub pages link to their child entity pages"
    applies_to: hub_page
    allowed_targets: [entity_page]
    constraint: "target.parent == source.id"

  - name: "entity_to_siblings"
    description: "Entity pages link to siblings in the same collection"
    applies_to: entity_page
    allowed_targets: [entity_page, hub_page]
    constraint: "target.collection == source.collection"

  - name: "no_upward_links_from_thin"
    description: "Pages below BASIC tier cannot link to FULL-tier pages"
    rationale: "Prevents thin pages from diluting authority of strong pages"
    enforcement: soft_warn
```

**Why this matters:** The most common failure mode in programmatic SEO is broken internal links at scale. When agents generate hundreds of pages, link integrity must be enforced by contract, not by manual review.

### 4. Snapshot Boundary Contract

The rule that prevents the most dangerous class of multi-agent bug.

```yaml
# contracts/snapshot_boundary.yaml
principle: "The database schema is the inter-agent contract"

boundaries:
  write_agents: [agent_1, agent_5]
  read_agents: [agent_2]
  verify_agents: [agent_3]

rules:
  - "Write agents produce snapshot rows. Read agents consume them."
  - "Read agents NEVER compute primary data. If it's not in the snapshot, it doesn't exist at render time."
  - "Schema changes require a migration. Migrations are reviewable."
  - "If a read agent needs data that isn't in the snapshot, the fix is 'write agent adds it to the snapshot' — NOT 'read agent computes it in the SSR loader.'"

staleness_guard:
  description: "If snapshot.updated_at is older than threshold, degrade gracefully"
  behavior:
    fresh: "Serve from snapshot (sub-50ms)"
    stale: "Fall through to live computation (logged as anomaly)"
    missing: "Render SHELL template"

failure_mode: "fail_safe_not_silent"
description: >
  If Agent 1 changes the snapshot schema, Agent 2's read breaks visibly.
  If Agent 2 expects a field that Agent 1 doesn't write, the publish gate
  degrades the page to SHELL. The system fails safe, not silent.
```

**Why this matters:** In multi-agent development, the #1 failure mode is contract drift — two agents making independent assumptions about the same data boundary. The snapshot boundary makes drift visible and forces safe degradation instead of silent corruption.

### 5. Sprint Contracts

Define what work is in scope, who owns it, and what "done" means.

```yaml
# contracts/sprints/example-quality-recovery.yaml
sprint:
  name: "Quality Recovery"
  date: "YYYY-MM-DD"

  scope:
    in:
      - "Fix public claim contradictions across page types"
      - "Restore source snapshot coverage"
      - "Fix broken internal links"
      - "Deploy resolver parity checks"
    out:
      - "New visual experience layer"
      - "New page types (deferred)"
      - "Infrastructure changes (deferred)"

  agent_assignments:
    agent_1_data:
      - "Unify claim authority"
      - "Materialize source snapshots"
    agent_2_rendering:
      - "Fix template status behavior"
      - "Stop fallback pages from leaking stale claims"
    agent_3_contracts:
      - "Validator baseline interpretation"
      - "Link graph validation"

  acceptance_gates:
    - "Same public claim shown across page types and APIs"
    - "Zero broken internal links emitted"
    - "Resolver and rendered output agree on indexability"
    - "Source snapshots are fresh enough for public claims"

  exit_criteria:
    - "All acceptance gates pass on LIVE SITE"
    - "Not when PRs merge — when production proves it"
```

**Why this matters:** The sprint is not done when the code merges. It's done when the live site satisfies the contracts. This prevents the gap between "CI passed" and "production works."

---

## Incident-Learned Invariants

Some of the most important rules in this framework were clarified by production failures and operational diagnostics in live multi-agent publishing systems, then generalized for public use.

- [docs/INCIDENT_LEARNED_INVARIANTS.md](docs/INCIDENT_LEARNED_INVARIANTS.md) documents the sanitized invariant set
- The public repo shares the invariant pattern and implementation guidance, not any proprietary operating playbook

---

## v0.2 Reference Patterns

The next layer of the framework is about method, not just contract categories.

- [docs/V0_2_REFERENCE_PATTERNS.md](docs/V0_2_REFERENCE_PATTERNS.md) explains how implicit contracts become explicit ones
- It introduces four portable abstractions: contract-as-test, page-family render tiers, cache write authority, and the readiness invariant ladder
- These patterns are intentionally public-safe and implementation-agnostic; they are the reference layer, not a dump of one deployment's internal contracts

---

## The Priority Stack

Not all contracts are equal. When multiple things are broken, this ordering prevents agents from working on the wrong layer.

```
LEVEL 1 — DATA TRUTH (blocks everything)
  Is the data pipeline running?
  Are observations being classified?
  Are snapshots materializing?
  → If broken: STOP ALL OTHER WORK.

LEVEL 2 — CONTENT TRUTH (blocks user trust)
  Do pages show accurate data?
  Do prices/facts match across surfaces?
  Do internal links resolve?
  Are stale pages degrading to SHELL?
  → Fix before any feature work.

LEVEL 3 — CONTENT DEPTH (blocks discoverability)
  Are intelligence views computing?
  Is narrative enrichment running?
  Is the eval baseline improving?
  → Build after truth is established.

LEVEL 4 — EXPERIENCE LAYER (the differentiator)
  Design polish, interactivity, advanced features.
  → Only after Levels 1-3 are stable.
```

---

## Agent Rules

These apply to every agent in the system, regardless of role.

1. **Read the priority stack before starting work.** If Level 1 is broken, don't work on Level 3.
2. **Read the relevant contract before touching code.** The contract tells you what the system expects.
3. **Verify against the contract, not against your assumptions.** If `page_types.yaml` says a page needs `validated_metric` for BASIC tier, and your PR removes that check, you're wrong.
4. **Never bypass the snapshot boundary.** Write agents write. Read agents read. Never cross.
5. **Prepare work, don't apply it.** Agents write migrations and PRs. Humans review and merge. This is a security boundary.
6. **Aspirational language is excluded from specs.** "The page should feel alive" is not a spec. `BPM = 60 + (energy × 100)` is a spec. Every line maps 1:1 to shipped code.
7. **Cost awareness is mandatory.** Every pipeline that calls an LLM has a per-entity cost. Document it.

---

## Scope

Constitutional CMS governs **what agents publish**. It does not:

- **Orchestrate agents.** It doesn't route messages or manage tool access. Use CrewAI, LangGraph, Claude Code, Codex, or whatever you want. Constitutional CMS is the governance layer that sits above your agent framework.
- **Run tests or deploy code.** It defines what the tests should verify and what "deployed correctly" means. Your CI/CD pipeline enforces it.
- **Depend on any specific tech stack.** The contracts are YAML. The agents can be Claude, GPT, Codex, local models, or humans. The backend, frontend, database, and hosting are your choice.

---

## Runtime Governance

Contracts govern what agents are permitted to publish. Runtimes govern where agents are permitted to work.

The `runtime/` directory defines the container isolation contract for constitutional workstreams. Three invariants address the failure modes observed in multi-agent production systems: dirty-worktree deploys, cross-workstream state contamination, and contract drift.

The specification is implementation-agnostic. Docker, Podman, Firecracker, and Cloudflare Worker isolates are all valid runtimes if they satisfy the invariants.

→ See [`runtime/SPEC.md`](runtime/SPEC.md) for the full specification.

---

## Production Pattern

This framework was extracted from production use in agent-built publishing systems. The public repository keeps only the generalized patterns:

- quality tiers that graduate and degrade from source evidence
- rendered-output validation for search and discovery surfaces
- materialized artifact metadata for cache safety
- claim decisions that separate visible facts, structured data, and agent APIs
- observe-first validators that can later become blocking gates

The agents write code and produce content. Humans write the contracts, review the changes, and decide what becomes public policy. The contracts prevent independent workstreams from breaking each other's output.

---

## Getting Started

```
constitutional-cms/
├── README.md                          # You are here
├── LICENSE                            # Apache 2.0
├── contracts/
│   ├── page_types.yaml                # What pages require at each tier
│   ├── enrichment_stages.yaml         # Pipeline stages and ownership
│   ├── link_rules.yaml                # What can link to what
│   ├── snapshot_boundary.yaml         # Write/read agent separation
│   ├── page_health_resolver.yaml      # URL health semantic split
│   ├── claim_decision.yaml            # Validated public claim policy
│   ├── cache_materialization.yaml     # Rendered artifact metadata
│   ├── mobile_table_card_layout.yaml  # Narrow viewport layout invariant
│   └── sprints/                       # Sprint-scoped work contracts
│       └── example-sprint.yaml
├── examples/
│   ├── location-intelligence/         # Location intelligence example
│   │   ├── page_types.yaml
│   │   ├── enrichment_stages.yaml
│   │   └── link_rules.yaml
│   └── ecommerce-catalog/            # Product page example
│       ├── page_types.yaml
│       ├── enrichment_stages.yaml
│       └── link_rules.yaml
├── scripts/
│   ├── validate_contracts.py          # Validate contract consistency
│   └── page_health_validator.py       # Observe-only crawl/render report
└── docs/
    ├── NOVELTY.md                     # What's new here and what isn't
    ├── INCIDENT_LEARNED_INVARIANTS.md # Sanitized production-learned rules
    ├── V0_2_REFERENCE_PATTERNS.md     # Portable methods for explicit contract ratchets
    ├── AGENT_COORDINATION.md          # How agents use these contracts
    └── PRIOR_ART.md                   # Honest comparison to existing tools
```

1. Copy the `contracts/` directory into your project
2. Edit the YAML files to match your domain (entity types, required fields, tier thresholds)
3. Point your agents at the contracts before they write code
4. Build validation scripts that check live output against contracts

---

## License

Apache 2.0. The spec and pattern are open. Your domain-specific contracts (which entities matter, what your compression axes are, what your narrative voice sounds like) are your competitive advantage.

---

## Prior Art & Honest Positioning

See [docs/PRIOR_ART.md](docs/PRIOR_ART.md) for a detailed comparison. The short version:

| Tool | What it governs | What Constitutional CMS adds |
|------|----------------|------------------------------|
| Microsoft Agent Governance Toolkit | Agent runtime security (permissions, tool access, kill switches) | Content-specific governance: publish tiers, link graphs, schema emission |
| OPA/Rego | Infrastructure access policies | Content quality and publish-tier gating |
| OpenAPI | API response shapes | Full page lifecycle from ingestion to indexation |
| WordPress/Drupal | Human editorial workflow | Multi-agent production at programmatic scale |
| Anthropic Skills | What agents know how to do | What agents are *not allowed* to do |

The novelty is not in any single component. It's in the **continuous lifecycle** — pages that automatically graduate and degrade between quality tiers based on data freshness, governed by contracts that coordinate multiple agents through snapshot boundaries and link graph rules, proven in production with measurable SEO outcomes.

---

*Targeted Impressions LLC — [targetedimpressions.com](https://targetedimpressions.com)*
