# Evidence hygiene

Provenance: public pattern library. Not a check catalog. Not a work-ordering scheme.

```
Canonical question: may this observation stand as evidence for the claim it is attached to?
Governs: probes, collectors, guards, coverage declarations, and the headers and metadata that report their results
Must not be used as: a CheckCatalogV1 check, a G0–G5 substitute, or a FAIL for UNMEASURED
```

Read [`PROTOCOL_MAP.md`](PROTOCOL_MAP.md) first. These rules classify evidence before it reaches a verdict. A verdict
that rests on dirty evidence is unauthorized certainty, which [`CONSUMING_LAYER.md`](CONSUMING_LAYER.md) forbids.

Each rule names the failure it prevents. Each rule applies the same law to the instrument instead of the page.

## 1. Absence in a partial map is unknown

**Rule:** A declaration covers only the families it names, and only when it says that it is complete. Outside that
scope, absence means unknown. It never means false.

**Failure it prevents:** A registry, allowlist, sitemap, or coverage map lists some families. A consumer reads "not
listed" as "not real" and suppresses, rejects, or retires a subject that the map never covered.

**Do:** Make every coverage declaration state its scope and its completeness, using the `coverage_state` vocabulary in
[`contracts/sensor_integrity.yaml`](../contracts/sensor_integrity.yaml): `complete`, `sampled`, `partial`, `unknown`,
`unavailable`. Only a `complete` declaration over a named family can support a negative claim about that family.
Everything else resolves to unknown, and unknown resolves to `UNMEASURED`. Absence is scoped
([`contracts/entity_lifecycle.yaml`](../contracts/entity_lifecycle.yaml)).

## 2. An always-red guard is a false signal

**Rule:** A guard must distinguish a governed claim from a leak. A guard that fails on every input carries no more
information than a guard that passes on every input.

**Failure it prevents:** A guard matches a token, such as a price pattern, a status word, or a header, without asking
whether policy authorized it. Lawful, governed output then fails the same way a leak fails. Operators learn to ignore
the red. The day a real leak arrives, it looks like every other day.

**Do:** Give every guard two fixtures and one test for each:

- a governed fixture, where the claim is present and authorized, which must pass; and
- a leak fixture, where the same claim is present without authority, which must fail.

A guard that has not passed both tests is unproven, in either color. It is the two-sided form of
[Partial Guards Are False Signal](INCIDENT_LEARNED_INVARIANTS.md): coverage must be complete, and the guard must also be
able to tell lawful from unlawful.

## 3. The instrument must observe the subject it reports on

**Rule:** The requested URL and the evaluated URL must match. If they diverge, or if the response fingerprints a bot
challenge, the observation is about the wall, not the page.

**Failure it prevents:** A probe is intercepted by a challenge page. The instrument then reports page findings (no
heading, no structured data, a near-empty body) about a document nobody asked about.

**Do:** Type the run as blocked when any of these signals is present: final URL differs from requested URL, the path
matches a known challenge vendor, or the body is trivial for the requested template. The typed state is
`BLOCKED_BY_TARGET` ([`CONSUMING_LAYER.md`](CONSUMING_LAYER.md)). Emit no page-tier verdict about the intercepted
document. A collector that sees these signals records the affected evidence as `unavailable`, which the evaluator
resolves to `UNMEASURED` with a reason code ([`contracts/evidence_bundle_v1.yaml`](../contracts/evidence_bundle_v1.yaml)).

## 4. Probes identify themselves

**Rule:** An internal probe never impersonates a crawler user agent. It carries a synthetic-probe marker, and every
report that counts traffic excludes traffic with that marker.

**Failure it prevents:** A probe borrows a search crawler's user agent to "see what the crawler sees." Its requests then
count as crawler visits in logs and dashboards. The team reports crawler attention that it generated itself. Edge rules
that treat crawlers differently may also serve the probe a path that no real crawler receives, so the probe still does
not see what the crawler sees.

**Do:**

- Use a user agent that names the tool and links to its owner. The reference collector does this
  (`constitutional-cms/<version>`).
- Add an explicit synthetic-probe marker, such as a request header, that names the probe. Reporting filters on the
  marker, not on a guess.
- Declare the probe in the sensor record as `synthetic_check` and declare its `mutation_class` before it runs
  ([`contracts/sensor_integrity.yaml`](../contracts/sensor_integrity.yaml)). A probe that fills a cache is
  `read_with_side_effect`, not `pure_read`.
- To test crawler-specific serving, use a declared test mechanism that the serving layer recognizes as a test. Do not
  use disguise.

## 5. A typed UNAVAILABLE beats a silent substitute

**Rule:** When a value cannot be observed, report it as unavailable with a reason. Never substitute a default, a zero,
a last-known value presented as current, or a value from another source.

**Failure it prevents:** A sensor fails and the report shows a flat zero. A source is stale and the page shows the last
value as if it were current. A substitute looks like knowledge, so nobody repairs the source.

**Do:** Use the honest absence states in [`contracts/signal_projection.yaml`](../contracts/signal_projection.yaml):
`not_observed`, `stale`, `pending`, `unavailable`, `invalid`. Keep them distinct. Carry a stable reason code. Sensor
failure is evidence of lost visibility, not evidence that the world is quiet
([`contracts/sensor_integrity.yaml`](../contracts/sensor_integrity.yaml)).

## 6. Failure is visible in headers and metadata

**Rule:** When a surface serves degraded output, its headers or metadata say so. Failure is never painted over with
stale data.

**Failure it prevents:** The origin fails and the edge serves an old copy with the same headers as a fresh one. Probes
and crawlers see success. The incident is invisible until a reader notices that the content is wrong.

**Do:** Derive response metadata from the same state that chose the body. A served artifact carries its build or
generation identity, its render time, and its state (`fresh`, `stale`, `fallback`). Standard fields such as `Age` and
`Cache-Status` (RFC 9211) help; they do not replace an explicit state. Fallback and placeholder artifacts are never
written as validated output ([`contracts/cache_materialization.yaml`](../contracts/cache_materialization.yaml)). Derived
headers, not asserted headers: the header and the body must not be able to drift apart.

## Checklist

Before an observation becomes a verdict, ask:

1. Does a declaration cover this subject, and does it say that it is complete?
2. Has the guard that produced this result passed a governed fixture and failed a leak fixture?
3. Is the evaluated URL the requested URL?
4. Did the probe identify itself, and is its traffic excluded from the counts it reports on?
5. If a value is missing, is it typed with a reason, or was something substituted?
6. If the surface degraded, do its headers and metadata say so?

Any "no" means the result is not yet evidence. Report it as `UNMEASURED` until it is fixed, never as `PASS` or `FAIL`.

## What this page is not

- Not new catalog checks. The catalog and the evaluator stay as released.
- Not a ban on synthetic monitoring. Synthetic probes are useful when they are declared.
- Not a substitute for [`INCIDENT_LEARNED_INVARIANTS.md`](INCIDENT_LEARNED_INVARIANTS.md). Those rules govern the page.
  These rules govern the evidence about the page.
