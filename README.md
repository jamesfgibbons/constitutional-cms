# Constitutional CMS

Open-source **publishing governance for AI-built websites**.

**Constitutional CMS governs what AI agents are entitled to publish.**

The public checker inspects what reached the web.
The CLI runs the same evidence rules before publication.

[Run a public audit](https://constitutionalcms.com/check) · [CLI](#install-and-run-a-fixture) · [Protocol](docs/WEB_CONFORMANCE.md) · [Pilot](https://constitutionalcms.com/pilot)

CMS used to mean Content Management System — software for humans who write pages. Constitutional CMS manages the *contracts* that govern what AI agents are permitted to publish. Same acronym, different era.

WordPress, Webflow, Drupal, and Shopify were designed for human authors. They still work for that. Constitutional CMS is designed for the gap that opens when **agents become the authors** — and nobody is checking whether each generated page has valid data, working links, or enough substance to deserve publication.

## Website vs CLI

| | After publication | Before publication |
|---|---|---|
| **Surface** | [constitutionalcms.com/check](https://constitutionalcms.com/check) | `constitutional-cms` CLI |
| **Input** | A public URL | Normalized `EvidenceBundleV1` |
| **Question** | What did the outside world receive? | Can our own system run the same rules before the next page ships? |

Do not trust the hosted checker as the last word. Download the evidence and re-run the same verdict locally.

## Install and run a fixture

From a clone of this repository:

```bash
pip install -e .
constitutional-cms validate
constitutional-cms audit \
  --evidence examples/hello-site/evidence.yaml \
  --out receipt.json
```

After the v0.5.0 package is on PyPI:

```bash
uvx constitutional-cms audit \
  --evidence examples/hello-site/evidence.yaml \
  --out receipt.json
```

Default `audit` writes a receipt and exits `0`. That is intentional: the command is a receipt generator. CI that should block a release must opt in:

```bash
constitutional-cms audit \
  --evidence examples/hello-site/evidence.yaml \
  --out receipt.json \
  --fail-on FAIL
```

Stricter publication boundaries can also block missing evidence:

```bash
--fail-on FAIL,UNMEASURED
```

Optional: `constitutional-cms audit https://example.com` performs one read-only GET and leaves everything a static response cannot observe as `UNMEASURED`. Prefer `--evidence` in CI.

## Sample receipt (abridged)

Provenance: synthetic fixture. Not a live customer page. `certified` is always `false` on this public recreate-a-check path.

```json
{
  "schema_version": "ConformanceReceiptV1",
  "framework_release": "v0.5.0",
  "catalog_version": "1.0.2",
  "certified": false,
  "checks": [
    {
      "check_id": "web.http.success",
      "verdict": "PASS",
      "reason_code": "rule_satisfied"
    },
    {
      "check_id": "web.accessibility.automated",
      "verdict": "UNMEASURED",
      "reason_code": "evidence_missing"
    }
  ]
}
```

A score collapses “wrong,” “not applicable,” and “not observed” into one number. Constitutional CMS keeps them separate.

## What it does — and does not do

It does:

- evaluate normalized evidence against a versioned 19-check catalog
- keep `PASS`, `FAIL`, `UNMEASURED`, and `NOT_APPLICABLE` as distinct verdicts
- emit a `ConformanceReceiptV1` with evidence pointers and a result digest
- refuse to invent a pass, a fail, or a composite score

It is not:

- another SEO crawler
- another content generator
- a replacement for WordPress, Webflow, or a headless CMS
- general-purpose agent permission management
- a proprietary website score
- an observability dashboard

Agent-security products govern what tools an agent can call. Constitutional CMS governs what the resulting public surface is allowed to claim.

## Release identity

| Coordinate | Value |
|---|---|
| Framework release | `v0.5.0` |
| Python package | `0.5.0` |
| Check catalog | `1.0.2` (19 checks) |
| Git tag | `v0.5.0` |

The hosted checker, this repository, the Python package, and the changelog must name the same commit. See [CHANGELOG.md](CHANGELOG.md) and [ROADMAP.md](ROADMAP.md).

## Adoption ladder

1. Run a fixture.
2. Produce a receipt.
3. Change one evidence value.
4. See the verdict change.
5. Add your own collector or adapter.
6. Enforce the receipt in CI (`--fail-on FAIL` when you mean it).

## Three contribution paths

| Path | What you file | Template |
|---|---|---|
| **Incident** | What broke in a real publishing system | [production-incident](.github/ISSUE_TEMPLATE/production-incident.yml) |
| **Invariant** | The portable rule that failure generalizes to | [contribute-invariant](.github/ISSUE_TEMPLATE/contribute-invariant.yml) |
| **Adapter** | A translator from a public or private source into `EvidenceBundleV1` / `LinkTargetV1` | [contribute-adapter](.github/ISSUE_TEMPLATE/contribute-adapter.yml) |

Issues are for concrete work and reproducible failures. Implementation questions and adapter proposals belong in [Discussions](https://github.com/jamesfgibbons/constitutional-cms/discussions).

**Skills make agents capable. Contracts make agents trustworthy.**

---

## Contents

- [The problem](#the-problem)
- [The five contracts](#the-five-contracts)
- [Web conformance](docs/WEB_CONFORMANCE.md)
- [Canonical protocol map](docs/PROTOCOL_MAP.md)
- [Incident-learned invariants](#incident-learned-invariants)
- [Every crossing needs an authority](#every-crossing-needs-an-authority)
- [v0.2 reference patterns](#v02-reference-patterns)
- [Constitutional cybernetics](#constitutional-cybernetics)
- [The priority stack](#the-priority-stack)
- [Agent rules](#agent-rules)
- [Scope](#scope)
- [Release and source boundary](docs/SOURCE_BOUNDARY.md)
- [Runtime governance](#runtime-governance)
- [Production pattern](#production-pattern)
- [Getting started](#getting-started)
- [Roadmap](ROADMAP.md)
- [Prior art](#prior-art--honest-positioning)
- [License](#license)

---

## The problem

AI coding agents are remarkably good at additive feature development. They are remarkably bad at maintaining systemic coherence.

Give four agents access to the same codebase and tell them to build pages.

- Agent 1 adds a column to the database. Agent 3 adds a different column in the same sprint. Both changes are valid individually. Together they create a conflict that no unit test catches.
- Agent 2 emits an internal link to a page that Agent 1 deleted.
- Agent 4 generates schema markup on a page that does not have enough data to support it.

The site passes CI. The site is broken.

This is not a skill problem. The agents are skilled. It is a governance problem. Nobody told them what they *cannot* do.

---

## The five contracts

Each contract is a YAML file that agents read before writing code.

| # | Contract | File | What it decides |
|---|----------|------|-----------------|
| 1 | Page type | [`contracts/page_types.yaml`](contracts/page_types.yaml) | What a page needs at FULL, BASIC, SHELL, and SUPPRESS |
| 2 | Enrichment stage | [`contracts/enrichment_stages.yaml`](contracts/enrichment_stages.yaml) | Which stage writes which state, and the gate that must pass first |
| 3 | Link graph | [`contracts/link_rules.yaml`](contracts/link_rules.yaml) | What is allowed to link to what |
| 4 | Snapshot boundary | [`contracts/snapshot_boundary.yaml`](contracts/snapshot_boundary.yaml) | Write agents write. Read agents read. Drift fails safe. |
| 5 | Sprint | [`contracts/sprints/`](contracts/sprints/) | Scope, ownership, and what “done” means on the live site |

### 1. Page type contracts

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
        - validated_metric  # price, score, rating, availability
        - source_snapshot
        - narrative_block   # LLM-generated, source-backed
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
      schema_emission: false    # no structured data on thin pages
      internal_links: false     # no outbound links from shells

    SUPPRESS:
      description: "Page is removed from sitemap and returns 404"
      trigger: "Entity deprecated or data source permanently unavailable"
```

WordPress has “draft” and “published.” Constitutional CMS has a continuous quality spectrum. Pages graduate from SHELL → BASIC → FULL as data accumulates, and degrade back down when data goes stale. Transitions follow what data exists, not human editorial judgment.

Quality tier and indexability are separate dimensions. A degraded but legitimate URL can remain indexable while withholding schema, links, or richer narrative until it earns a higher tier. Emit `noindex` from explicit indexability policy, not from the mere fact that a page is currently in `SHELL`.

### 2. Enrichment stage contracts

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

Every stage has exactly one owner. No two agents write the same table. The quality gate runs before data is accepted. Bad data is rejected at ingestion, not discovered in production.

### 3. Link graph rules

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

The most common failure mode in programmatic SEO is broken internal links at scale. When agents generate hundreds of pages, link integrity must be enforced by contract, not by manual review.

### 4. Snapshot boundary contract

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

In multi-agent development, the #1 failure mode is contract drift — two agents making independent assumptions about the same data boundary. The snapshot boundary makes drift visible and forces safe degradation instead of silent corruption.

### 5. Sprint contracts

Define what work is in scope, who owns it, and what “done” means.

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

The sprint is not done when the code merges. It is done when the live site satisfies the contracts. This closes the gap between “CI passed” and “production works.”

---

## Incident-learned invariants

The invariant set expresses portable rules through generalized failure scenarios. Public documentation does not assert
private incident detail or implementation outcomes as public proof.

- [`docs/INCIDENT_LEARNED_INVARIANTS.md`](docs/INCIDENT_LEARNED_INVARIANTS.md) documents the sanitized invariant set
- The public repo shares the invariant pattern and implementation guidance, not any proprietary operating playbook

---

## Every crossing needs an authority

The governing doctrine of the framework is that **every crossing needs an authority**. A system may move from one valid state to another through many paths. The destination does not tell you which path was chosen, when the decision became irreversible, or whose judgment the transition contains.

Four public artifacts make the doctrine executable:

- **The Transition Authority Contract** names the authority for each crossing class: source to consumer, state to state, human to machine, private to public, production to certification. The source owns truth. The transition needs an author. The renderer owns expression, not semantics. The receipt owns proof.
- **The Troubadour Protocol** separates authorship from performance. Trobar authors. Canso preserves. Joglar performs. Razo proves. A machine that touches the artifact does not become its originating author.
- **Signal Contract vNext — Transition Record** is a proposed extension to Signal Contract v1 that makes the movement between states explicit. State equality does not imply transition equality.
- **The Receipt That Runs** is a sanitized demonstration of the receipt shape. Proof is a crossing, not a report. The producing layer cannot certify itself.

Each artifact publishes the grammar of a crossing. None publishes the tuning: the pivot functions, the selection heuristics, the thresholds, or the protected source material. The public sees the shape. The private repos hold the authored decisions.

Read them on [constitutionalcms.com](https://constitutionalcms.com):

- [Transition Record](https://constitutionalcms.com/transition-record)
- [Troubadour Protocol](https://constitutionalcms.com/troubadour-protocol)
- [Transition Authority](https://constitutionalcms.com/transition-authority)
- [Receipt Demonstration](https://constitutionalcms.com/receipt-demonstration)

---

## v0.2 reference patterns

The next layer of the framework is about method, not just contract categories.

- [`docs/V0_2_REFERENCE_PATTERNS.md`](docs/V0_2_REFERENCE_PATTERNS.md) explains how implicit contracts become explicit ones
- Four portable abstractions: contract-as-test, page-family render tiers, cache write authority, and the readiness invariant ladder
- These patterns are public-safe and implementation-agnostic. They are the reference layer, not a dump of one deployment’s internal contracts.

---

## Constitutional cybernetics

The next layer treats Constitutional CMS as a control system for the agentic web.

Traditional CMS software manages authored content. Constitutional CMS manages feedback loops between sensors, materialized state, contract controllers, renderers, discovery surfaces, agents, and human proof. This cybernetic frame is what lets the same governed state safely project into HTML, APIs, structured data, dashboards, agent manifests, audio, spatial interfaces, or other ambient renderers without letting any consuming layer invent truth.

- [`docs/CONSTITUTIONAL_CYBERNETICS.md`](docs/CONSTITUTIONAL_CYBERNETICS.md) defines the sensors / state / controllers / actuators / dampers / proof model
- `contracts/signal_projection.yaml` — one canonical state, many renderers
- `contracts/proof_ledger.yaml` — evidence-gated done
- `contracts/outcome_record.yaml` — append-only external outcomes, kept separate from delivery proof
- `contracts/sensor_integrity.yaml` — stale or failed sources cannot become false zeroes
- `contracts/agent_operating_envelope.yaml` — safe autonomy tiers and data-plane idempotency
- Every probe declares `mutation_class`; missing required inputs resolve to `UNMEASURED`, never PASS

VIBEnet-style sensory feedback is one inspiration for this layer: governed state can become sound, light, motion, or spatial atmosphere. It is not required for adoption. The public contract is medium-neutral.

---

## The priority stack

This stack orders dependent repairs inside one publishing surface. It is not the portfolio-wide controller for unlike
work. Read [`docs/PROTOCOL_MAP.md`](docs/PROTOCOL_MAP.md) before applying any numbered scheme.

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
  → Only after Levels 1–3 are stable.
```

---

## Agent rules

These apply to every agent in the system, regardless of role.

1. **Read the priority stack before starting work.** If Level 1 is broken, do not work on Level 3.
2. **Read the relevant contract before touching code.** The contract tells you what the system expects.
3. **Verify against the contract, not against your assumptions.** If `page_types.yaml` says a page needs `validated_metric` for BASIC tier, and your PR removes that check, you are wrong.
4. **Never bypass the snapshot boundary.** Write agents write. Read agents read. Never cross.
5. **Prepare work, do not apply it.** Agents write migrations and PRs. Humans review and merge. This is a security boundary.
6. **Aspirational language is excluded from specs.** “The page should feel alive” is not a spec. `BPM = 60 + (energy × 100)` is a spec. Every line maps 1:1 to shipped code.
7. **Cost awareness is mandatory.** Every pipeline that calls an LLM has a per-entity cost. Document it.

---

## Scope

Constitutional CMS governs **what agents publish**. It does not:

- **Orchestrate agents.** It does not route messages or manage tool access. Use CrewAI, LangGraph, Claude Code, Codex, or whatever you want. Constitutional CMS is the governance layer that sits above your agent framework.
- **Crawl or deploy your production system.** The public evaluator consumes normalized evidence without network access. Your collectors, CI/CD pipeline, and private adapters gather evidence and enforce promotion.
- **Depend on any specific tech stack.** The contracts are YAML. The agents can be Claude, GPT, Codex, local models, or humans. The backend, frontend, database, and hosting are your choice.

---

## Runtime governance

Contracts govern what agents are permitted to publish. Runtimes govern where agents are permitted to work.

The [`runtime/`](runtime/) directory defines the container isolation contract for constitutional workstreams. Three invariants address the failure modes observed in multi-agent production systems: dirty-worktree deploys, cross-workstream state contamination, and contract drift.

The specification is implementation-agnostic. Docker, Podman, Firecracker, and Cloudflare Worker isolates are all valid runtimes if they satisfy the invariants.

See [`runtime/SPEC.md`](runtime/SPEC.md) for the full specification.

---

## Production pattern

The public repository contains generalized, implementation-agnostic patterns:

- quality tiers that graduate and degrade from source evidence
- rendered-output validation for search and discovery surfaces
- materialized artifact metadata for cache safety
- claim decisions that separate visible facts, structured data, and agent APIs
- proof ledgers that make machine-readable evidence govern completion claims
- sensor integrity rules that distinguish world silence from source failure
- signal projection rules that keep ambient and agentic renderers downstream of canonical state
- observe-first validators that can later become blocking gates
- a versioned web-conformance catalog with Foundation, Search, Answer/AI Retrieval, and Agentic Web profiles
- evidence and receipt schemas that preserve `UNMEASURED` and keep lab performance distinct from field Core Web Vitals
- public adapter shapes that make private route and readiness authorities testable without publishing them

The agents write code and produce content. Humans write the contracts, review the changes, and decide what becomes public policy. The contracts prevent independent workstreams from breaking each other’s output.

---

## Run it

The website checks a page after it is public. The CLI lets your own system check itself before it publishes.

### Installation

**This repository:**

```bash
pip install -e .
```

**After the v0.5.0 PyPI release is published:**

```bash
pip install constitutional-cms
# or
uvx constitutional-cms validate
```

### Audit conformance

`audit` evaluates normalized evidence against the public catalog and writes a `ConformanceReceiptV1`. It does **not** block a release unless you pass `--fail-on`.

```bash
constitutional-cms audit \
  --evidence examples/hello-site/evidence.yaml \
  --out receipt.json
```

CI gate (opt-in):

```bash
constitutional-cms audit \
  --evidence examples/hello-site/evidence.yaml \
  --out receipt.json \
  --fail-on FAIL
```

Custom catalog or evaluation timestamp:

```bash
constitutional-cms audit \
  --catalog contracts/check_catalog_v1.yaml \
  --evidence examples/hello-site/evidence.yaml \
  --as-of 2026-08-15T12:00:00Z
```

Optional public-URL collection — one read-only GET, static evidence only, everything else honestly `UNMEASURED`:

```bash
constitutional-cms audit https://example.com
constitutional-cms audit https://example.com --json
```

### Validate contracts

With no arguments, `validate` checks that the **bundled** catalog and schemas are internally coherent. That works from a wheel, outside this clone. If `./contracts` exists, it is validated too.

```bash
constitutional-cms validate
constitutional-cms validate path/to/contracts --check links
```

### No-install path

If you prefer not to install the package, the original scripts still work:

```bash
# Validate contracts
python scripts/validate_contracts.py

# Validate web conformance
python scripts/validate_web_conformance.py

# Run conformance evaluator
python scripts/conformance_evaluator.py \
  --evidence tests/fixtures/conformance/pass_all.yaml

# Observe page health (no enforcement)
python scripts/page_health_validator.py
```

---

## Getting started

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
│   ├── proof_ledger.yaml              # Evidence-gated done
│   ├── outcome_record.yaml            # External outcomes, append-only
│   ├── signal_projection.yaml         # One state projected into many renderers
│   ├── sensor_integrity.yaml          # Sensor health before metric claims
│   ├── agent_operating_envelope.yaml  # Safe autonomy and idempotency tiers
│   ├── standards_registry_v1.yaml      # External, platform, constitutional, and experimental authorities
│   ├── check_catalog_v1.yaml           # Reproducible checks across four profiles
│   ├── evidence_bundle_v1.yaml         # Normalized observation boundary
│   ├── constitutional_site_manifest_v1.yaml # Public-safe implementation configuration
│   ├── conformance_receipt_v1.yaml     # Verdict and evidence-coverage grammar
│   ├── link_target_v1.yaml             # Public normalized link-authority boundary
│   └── sprints/                       # Sprint-scoped work contracts
│       └── example-sprint.yaml
├── examples/
│   ├── hello-site/                    # Synthetic evidence fixture for the CLI quickstart
│   ├── location-intelligence/         # Location intelligence example
│   ├── ecommerce-catalog/             # Product page example
│   ├── manifests/                     # Public-safe configuration examples
│   └── link-targets/                  # Normalized link-authority examples
├── schemas/                           # JSON Schemas for portable interfaces
├── tests/golden-receipts/             # Deterministic Python/JavaScript parity receipts
├── scripts/
│   ├── validate_contracts.py          # Validate contract consistency
│   ├── validate_web_conformance.py    # Validate schemas, authority refs, and public safety
│   ├── conformance_evaluator.py       # Offline reference evaluator
│   └── page_health_validator.py       # Observe-only crawl/render report
└── docs/
    ├── NOVELTY.md                     # What's new here and what isn't
    ├── INCIDENT_LEARNED_INVARIANTS.md # Portable rules and generalized scenarios
    ├── PROTOCOL_MAP.md                # Which scheme answers which question
    ├── SOURCE_BOUNDARY.md             # Public authority and private implementation boundary
    ├── WEB_CONFORMANCE.md             # Profiles, verdicts, and reproducible evaluation
    ├── ADAPTER_BOUNDARY.md             # Public normalized records/private authorities
    ├── CANONICAL_JSON.md               # Cross-language digest and receipt identity
    ├── V0_2_REFERENCE_PATTERNS.md     # Portable methods for explicit contract ratchets
    ├── CONSTITUTIONAL_CYBERNETICS.md  # Control-system frame for the agentic web
    ├── AGENT_COORDINATION.md          # How agents use these contracts
    └── PRIOR_ART.md                   # Honest comparison to existing tools
```

1. Copy or pin the released contracts and schemas.
2. Edit the domain contracts and create a public-safe `ConstitutionalSiteManifestV1`.
3. Point agents at the contracts before they write code.
4. Map collector output or a private authority into `EvidenceBundleV1`.
5. Run `constitutional-cms audit --evidence <bundle.yaml> --out receipt.json`. Add `--fail-on FAIL` in CI only when a catalog `FAIL` should block publication.

More detail lives in [`docs/WEB_CONFORMANCE.md`](docs/WEB_CONFORMANCE.md),
[`docs/ADAPTER_BOUNDARY.md`](docs/ADAPTER_BOUNDARY.md),
[`docs/AGENT_COORDINATION.md`](docs/AGENT_COORDINATION.md), and on
[constitutionalcms.com](https://constitutionalcms.com).

---

## Prior art & honest positioning

See [`docs/PRIOR_ART.md`](docs/PRIOR_ART.md) for the full comparison. The short version:

| Tool | What it governs | What Constitutional CMS adds |
|------|-----------------|------------------------------|
| Microsoft Agent Governance Toolkit | Agent runtime security (permissions, tool access, kill switches) | Content-specific governance: publish tiers, link graphs, schema emission |
| OPA / Rego | Infrastructure access policies | Content quality and publish-tier gating |
| OpenAPI | API response shapes | Full page lifecycle from ingestion to indexation |
| WordPress / Drupal | Human editorial workflow | Multi-agent production at programmatic scale |
| Anthropic Skills | What agents know how to do | What agents are *not allowed* to do |

The novelty claim is about the **continuous lifecycle** — pages that graduate and degrade between quality tiers based
on evidence freshness, governed by contracts that coordinate multiple agents through snapshot boundaries and link
graph rules. It is a framework claim, not a public performance claim.

An honest assessment of what is and is not new lives in [`docs/NOVELTY.md`](docs/NOVELTY.md).

---

## License

Apache 2.0. The spec and pattern are open. Your domain-specific contracts — which entities matter, what your compression axes are, what your narrative voice sounds like — are your competitive advantage.

---

*Targeted Impressions — [targetedimpressions.com](https://targetedimpressions.com)*
