# Constitutional CMS

**A governance framework for AI agents that build websites.**

CMS used to mean Content Management System — software for humans who write pages. Constitutional CMS manages the *contracts* that govern what AI agents are permitted to publish. Same acronym, different era.

WordPress, Webflow, Drupal, and Shopify were designed for human authors. They still work for that. Constitutional CMS is designed for the gap that opens when **agents become the authors** — and nobody is checking whether the 400th page they generated has valid data, working links, or enough substance to deserve a spot in Google's index.

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
route_page:
  description: "A page about a specific origin→destination flight route"
  url_pattern: "/flights/{origin}-to-{dest}"

  tiers:
    FULL:
      required_fields:
        - price_usd
        - carriers[]       # at least one airline
        - flight_duration
        - narrative_block   # LLM-generated, 800+ words
        - json_ld_schema
      min_word_count: 800
      schema_emission: true
      internal_links: true

    BASIC:
      required_fields:
        - price_usd
        - carriers[]
      min_word_count: 200
      schema_emission: true
      internal_links: true

    SHELL:
      required_fields:
        - origin_code
        - destination_code
      min_word_count: 0
      schema_emission: false    # No structured data on thin pages
      internal_links: false     # No outbound links from shells
      noindex: true             # Don't waste crawl budget

    SUPPRESS:
      description: "Page is removed from sitemap and returns 404"
      trigger: "Entity deprecated or data source permanently unavailable"
```

**Why this matters:** WordPress has "draft" and "published." Constitutional CMS has a continuous quality spectrum. Pages graduate from SHELL → BASIC → FULL as data accumulates, and degrade back down when data goes stale. The system handles transitions automatically based on what data exists — not on human editorial judgment.

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

  - name: "hub_to_routes"
    description: "Hub pages link to their child route pages"
    applies_to: hub_page
    allowed_targets: [route_page]
    constraint: "target.origin == source.origin"

  - name: "route_to_siblings"
    description: "Route pages link to sibling routes in the same corridor"
    applies_to: route_page
    allowed_targets: [route_page, hub_page]
    constraint: "target.corridor == source.corridor OR target.origin == source.origin"

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
# contracts/sprints/2026-03-29-content-recovery.yaml
sprint:
  name: "Content Recovery"
  date: "2026-03-29"

  scope:
    in:
      - "Fix price contradictions across page types"
      - "Restore pricing pipeline coverage"
      - "Fix broken internal links"
      - "Deploy intelligence SQL views"
    out:
      - "Audio layer (deferred to next sprint)"
      - "New page types (deferred)"
      - "Infrastructure changes (deferred)"

  agent_assignments:
    agent_1_backend:
      - "PR #539: price authority single source"
      - "PR #541: intelligence SQL views"
    agent_2_frontend:
      - "PR #582: template 404 fix"
      - "PR #583: shell pages stop leaking stale prices"
    agent_3_contracts:
      - "Eval baseline interpretation"
      - "Link graph validation"

  acceptance_gates:
    - "Same price shown on route page and best-time page"
    - "Zero broken internal links emitted"
    - "Intelligence views return rows for 10+ entities"
    - "Pricing pipeline producing accepted observations"

  exit_criteria:
    - "All acceptance gates pass on LIVE SITE"
    - "Not when PRs merge — when production proves it"
```

**Why this matters:** The sprint is not done when the code merges. It's done when the live site satisfies the contracts. This prevents the gap between "CI passed" and "production works."

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
3. **Verify against the contract, not against your assumptions.** If `page_types.yaml` says a page needs `carriers[]` for BASIC tier, and your PR removes that check, you're wrong.
4. **Never bypass the snapshot boundary.** Write agents write. Read agents read. Never cross.
5. **Prepare work, don't apply it.** Agents write migrations and PRs. Humans review and merge. This is a security boundary.
6. **Aspirational language is excluded from specs.** "The page should feel alive" is not a spec. `BPM = 60 + (energy × 100)` is a spec. Every line maps 1:1 to shipped code.
7. **Cost awareness is mandatory.** Every pipeline that calls an LLM has a per-entity cost. Document it.

---

## Scope

Constitutional CMS governs **what agents publish**. It does not:

- **Orchestrate agents.** It doesn't route messages or manage tool access. Use CrewAI, LangGraph, Claude Code, Codex, or whatever you want. Constitutional CMS is the governance layer that sits above your agent framework.
- **Run tests or deploy code.** It defines what the tests should verify and what "deployed correctly" means. Your CI/CD pipeline enforces it.
- **Depend on any specific tech stack.** The contracts are YAML. The agents can be Claude, GPT, Codex, local models, or humans. The backend, frontend, and hosting are your choice. The production proof below runs on Railway + Supabase + Cloudflare, but nothing in the spec requires that.

---

## Production Proof

This framework governs [SERPRadio](https://serpradio.com), a programmatic flight intelligence platform:

- **851 pages** returning HTTP 200
- **54ms** median TTFB
- **Lighthouse** accessibility 100, SEO 100
- **~$107/month** total infrastructure (Railway + Supabase + Cloudflare)
- **Zero hand-written pages** — all agent-produced, human-reviewed, contract-governed
- **4 AI agents**, 7 repos, 19 PRs merged in a single session with zero audit failures

The agents write the code and produce the content. The human writes the contracts, reviews the PRs, and applies the migrations. The contracts prevent the agents from breaking each other's work.

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
│   └── validate_contracts.py          # Validate contract consistency
└── docs/
    ├── NOVELTY.md                     # What's new here and what isn't
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
| PrescientIQ / Metaflow | Pre-publish quality gates for pSEO | Continuous graduation/degradation + snapshot boundaries + link graph rules |

The novelty is not in any single component. It's in the **continuous lifecycle** — pages that automatically graduate and degrade between quality tiers based on data freshness, governed by contracts that coordinate multiple agents through snapshot boundaries and link graph rules, proven in production with measurable SEO outcomes.

---

*Targeted Impressions LLC — [targetedimpressions.com](https://targetedimpressions.com)*
