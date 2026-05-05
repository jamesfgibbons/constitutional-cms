# v0.2 Reference Patterns

This document captures the next layer of Constitutional CMS: not just what
contracts exist, but how teams make implicit contracts explicit over time.

These patterns were generalized from live agent-built publishing systems and
are intentionally portable. They describe methods and abstractions, not a
private implementation's exact internal contract set.

---

## Encode Implicit Contracts

The right framing is not "add Constitutional CMS to a thing."

The contracts already exist inside the codebase, whether or not they have
names yet. Constitutional CMS is the discipline of extracting those implicit
rules into explicit artifacts with:

- a stable name
- a declared authority surface
- a reviewable version history
- an audit or test surface
- a policy decision about what happens on failure

That is how a system stops depending on tribal memory.

---

## Contract-As-Test Methodology

The strongest operating pattern is simple:

> Every contract gap becomes a regression test.

When a production or audit failure reveals a hidden rule, the fix should not
end at repaired code. The team should also:

1. Name the rule explicitly.
2. State what failure it prevents.
3. Add one test or probe that would have failed before the fix.
4. Make future changes answer to that test.

Why this matters:

- it turns incidents into reusable governance
- it prevents the same class of drift from reappearing under a new surface
- it lets contract integrity strengthen through many small PRs instead of one large rewrite

This is one of the core self-healing behaviors of a constitutional system.

---

## Page-Family Render Tiers

Publishability tier is not the only useful tier axis.

Many systems also need a family-level render tier that answers a different
question:

> How ready is this page family across the surfaces that consume it?

That model generalizes well beyond travel. Any platform serving browsers,
crawlers, APIs, caches, and agents can benefit from it.

Suggested abstraction:

- `Tier 1`: canonical SSR for browser and crawler consumption
- `Tier 2`: Tier 1 plus governed readiness, discovery, and cache metadata
- `Tier 3`: Tier 2 plus stable derivative outputs for structured data and agent-facing reuse

Important distinction:

- publishability tier describes URL-level content sufficiency
- render tier describes family-level cross-surface obligations
- readiness state describes whether a specific URL is currently eligible
- lifecycle state describes how a real-world entity behaves across time

Those are separate concepts and should not be collapsed into one flag.

---

## Cache Write Authority

Read-side cache classification is not enough.

If a system waits until read time to discover that cached HTML has the wrong
status, wrong canonical path, wrong metadata, or ineligible schema, then bad
state has already been materialized.

The stronger pattern is a write-side cache authority contract:

- accept writes only from known authority surfaces
- normalize the canonical cache key before writing
- reject rendered bodies that are non-200, noindex, empty, or placeholder-only
- require metadata fields that readers depend on
- name rejection reasons as stable values so diagnostics and tests can assert them

This pattern generalizes to HTML caches, JSON caches, search snapshots, agent
summaries, and any artifact that becomes authoritative after materialization.

---

## Readiness Invariant Ladder

Not every readiness system becomes trustworthy in one design pass.

The durable pattern is a ratchet:

- one invariant tightening per PR
- one regression test per tightening
- cumulative hardening over daily or weekly cadence

Examples of ladder-style implications:

- canonical scope implies source-of-record backing
- sitemap eligibility implies a registered render path
- render-path registration implies data-layer support
- indexability implies publishability or explicitly degraded-indexable policy
- cacheability implies reader/writer parity

This is useful because readiness failures usually arrive as a sequence of
"almost right" states. A ladder gives teams a way to harden the system without
pretending the final doctrine appeared all at once.

---

## Why These Patterns Matter

These v0.2 patterns are the difference between "we have some governance docs"
and "our architecture learns from contact with production."

They make it easier to:

- turn implementation drift into named policy
- keep browser, crawler, cache, and agent surfaces aligned
- evolve contracts through small reviewable changes
- preserve a clean public framework while keeping domain-specific details private
