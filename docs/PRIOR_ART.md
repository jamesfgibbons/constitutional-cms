# Prior Art & Comparisons

## Infrastructure Governance

| Tool | Domain | How Constitutional CMS Differs |
|------|--------|-------------------------------|
| **OPA/Rego** | API authorization, Kubernetes admission control | OPA answers "is this request allowed?" Constitutional CMS answers "is this page allowed to be published at this quality tier?" Different domain, different lifecycle. |
| **HashiCorp Sentinel** | Terraform plan validation | Sentinel gates infrastructure changes. Constitutional CMS gates content publication based on data quality, not policy compliance. |
| **AWS Service Control Policies** | Cloud account permissions | Account-level guardrails. No concept of content quality tiers or page-level governance. |

## Content Management Systems

| Tool | Model | How Constitutional CMS Differs |
|------|-------|-------------------------------|
| **WordPress** | Human writes in editor → draft → published | Binary state. No data-driven tier graduation/degradation. No agent coordination. No link graph governance. |
| **Drupal** | Human writes → editorial workflow → published | More workflow states than WordPress, but still human-initiated transitions. No concept of automatic degradation based on data freshness. |
| **Contentful / Sanity** | Headless CMS with structured content models | Closer in spirit (structured content, API-first), but designed for human authors managing content entries, not autonomous agents producing content from data pipelines. |
| **Webflow / Squarespace** | Visual builder → published | Design tools for humans. No programmatic content production. No agent governance. |

## Agent Frameworks

| Tool | Coordination Model | How Constitutional CMS Differs |
|------|-------------------|-------------------------------|
| **CrewAI** | Role-based agents with message passing | Coordinates agents through communication. Constitutional CMS coordinates through shared contracts — agents don't talk to each other. |
| **LangGraph** | Stateful graph with node transitions | Orchestrates agent workflows. Constitutional CMS doesn't orchestrate — it constrains. Use LangGraph for the workflow, Constitutional CMS for the rules. |
| **AutoGen** | Multi-agent conversation | Agents negotiate through conversation. Constitutional CMS removes the need for negotiation — the contract is the agreement. |
| **Anthropic Skills** | Packaged expertise folders | Skills teach agents what to do. Constitutional CMS teaches agents what they cannot do. Complementary, not competing. |

## Agent Governance

| Tool | What It Governs | How Constitutional CMS Differs |
|------|----------------|-------------------------------|
| **Microsoft Agent Governance Toolkit** (April 2026, MIT license) | Runtime security for autonomous agents: capability sandboxing, identity trust scoring, circuit breakers, kill switches. Maps to all 10 OWASP agentic AI risks. | Microsoft governs agent *actions* in infrastructure — what tools they can access, what permissions they have, when to kill a rogue process. Constitutional CMS governs agent *output* on the web — what content quality tier a page earns, what links it can emit, what schema it deserves. Different domain entirely. |
| **OWASP Top 10 for Agentic Applications** (Dec 2025) | Risk taxonomy: goal hijacking, tool misuse, cascading failures, rogue agents | A threat model, not an implementation. Constitutional CMS is an implementation pattern that addresses a subset of these risks (cascading failures, contract drift) specifically for web content production. |
| **Singapore IMDA Model AI Governance Framework** (Jan 2026) | Government-level framework for agentic AI governance: action-space scoping, autonomy levels, human oversight | Policy guidance for enterprises. Constitutional CMS is a concrete YAML-based spec that developers can clone and run today. Complementary layers — one is policy, the other is implementation. |

## Programmatic SEO Governance

| Tool | What It Does | How Constitutional CMS Differs |
|------|-------------|-------------------------------|
| **PrescientIQ** | Pre-flight checks that stop bad pages from reaching the sitemap. Dynamic indexing logic to preserve crawl budget. | Pass/fail at publish time. Constitutional CMS adds **continuous lifecycle** — a page published today as FULL can degrade to SHELL tomorrow when its data goes stale, and graduate back when the pipeline recovers. No human intervention. PrescientIQ gates once. Constitutional CMS governs continuously. |
| **Metaflow** | Multi-agent pSEO pipeline: separate agents for ingestion, generation, QA, and publish decisions. | Structurally similar pipeline, but Metaflow is a hosted platform for building those pipelines. Constitutional CMS is a governance spec you bring to your own stack. Metaflow also lacks snapshot boundary enforcement and declarative link graph rules. |
| **AirOps** | Workflow-based programmatic content generation with templates and quality thresholds. | Content factory, not governance spec. AirOps builds the pages. Constitutional CMS defines what the pages must satisfy to exist at each quality tier. |

## CI/CD & Quality Tools

| Tool | What It Checks | How Constitutional CMS Differs |
|------|---------------|-------------------------------|
| **GitHub Actions / GitLab CI** | Tests pass, build succeeds | Post-hoc verification. Constitutional CMS is pre-hoc governance — the rules exist before the code is written. |
| **Screaming Frog / Sitebulb** | Broken links, crawl errors | Audits after the fact. Constitutional CMS prevents broken links from being emitted. |
| **Google Search Console** | Indexation issues, crawl errors | Reports problems days/weeks later. Constitutional CMS prevents them at generation time. |

## The Gap This Fills

Agent governance toolkits (Microsoft) govern what agents are *allowed to do*. Programmatic SEO platforms (Metaflow, AirOps) govern content quality *at publish time*. Traditional CMS platforms (WordPress, Drupal) govern *human* editorial workflows.

Constitutional CMS fills the specific gap between these:

1. **Continuous lifecycle governance** — not just pass/fail at publish, but ongoing graduation and degradation as data freshness changes
2. **Snapshot boundaries** — structural rules preventing multi-agent contract drift on shared data, specific to web content production
3. **Declarative link graph rules** — preventing broken internal links at generation time, not auditing them after the fact
4. **A portable spec, not a platform** — YAML contracts you bring to your own stack, not a hosted service you depend on

The closest competitor to Constitutional CMS is a team that writes good internal documentation about how their agents should behave. The difference is that documentation is advisory. Contracts are enforceable.
