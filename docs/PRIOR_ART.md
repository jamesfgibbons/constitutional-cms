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

## CI/CD & Quality Tools

| Tool | What It Checks | How Constitutional CMS Differs |
|------|---------------|-------------------------------|
| **GitHub Actions / GitLab CI** | Tests pass, build succeeds | Post-hoc verification. Constitutional CMS is pre-hoc governance — the rules exist before the code is written. |
| **Screaming Frog / Sitebulb** | Broken links, crawl errors | Audits after the fact. Constitutional CMS prevents broken links from being emitted. |
| **Google Search Console** | Indexation issues, crawl errors | Reports problems days/weeks later. Constitutional CMS prevents them at generation time. |

## The Gap This Fills

None of the tools above were designed for the workflow: "multiple AI agents producing web content from data pipelines at programmatic scale, where content quality directly affects search engine credibility."

Constitutional CMS sits in the gap between agent frameworks (which coordinate work) and content platforms (which manage human editorial workflows). It governs agent-produced content with the rigor of infrastructure policy and the domain awareness of SEO tooling.
