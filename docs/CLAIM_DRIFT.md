# Claim Drift application pack

**Status: DRAFT application / not ratified / not a released v0.5.0 feature.**

This pack is a bounded application of existing Constitutional CMS
governance. It is not a new platform, score, compiler, or fifth
web-conformance profile. Claim Gate v0.1 remains DRAFT on main. Default
`audit` success still means a receipt was generated, not that
publication is allowed.

> Constitutional CMS provides publishing-governance contracts and evidence
> receipts. We are applying that architecture to claim drift: the gap
> between what a product currently supports and what websites, comparison
> pages, and connected sales or AI systems continue to assert.

Do not yet claim automatic web-wide correction, guaranteed AI citation,
comprehensive contradiction detection, independent truth certification,
or control over competitor or customer speech.

```
Canonical question: for enrolled material claims, what may we currently
assert, and did each enrolled surface receive the current decision?
Governs: a companion assertion profile, frozen fixtures, and a reference
detector that maps into existing contracts
Must not be used as: a fifth web-conformance profile, a G0–G5 substitute,
a site compiler, a second permission authority, or truth certification
```

## Distinction

| Layer | Owns | This pack |
| --- | --- | --- |
| Constitutional CMS | Portable contracts, Claim Gate, catalog, entity lifecycle | Application mapping only |
| Claim Drift application | Finite enrolled inventory + three surfaces | Fixtures, profile, detector |
| High Command / live pilot | Production publication, source-registry, tagging | Out of scope |

## How existing schemes are reused

Identify the question, then use the scheme that already owns it
([`PROTOCOL_MAP.md`](PROTOCOL_MAP.md)).

| Question | Existing scheme | What this pack does |
| --- | --- | --- |
| Are the signed bytes intact? | Claim Gate v0.1 (`verify_bundle` / `verify_receipt`) | Call the existing verifier. Do not extend `ClaimBundleV0_1`. |
| Does inspectable evidence support the assertion? | Companion profile + frozen snapshots | Mechanical support verdict: `SUPPORTED` / `UNSUPPORTED` / `UNMEASURED` |
| What may we currently say? | [`claim_decision.yaml`](../contracts/claim_decision.yaml) | `publish` / `hold` / `suppress` only |
| Does the subject still exist? May we `410`? | [`entity_lifecycle.yaml`](../contracts/entity_lifecycle.yaml) | Withhold is a forbidden terminal trigger |
| Did a catalog audit finish? | CheckCatalogV1 / `evaluate` | Receipt generation is not permission |
| Did the wire change? | [`promotion_protocol_v1.yaml`](../contracts/promotion_protocol_v1.yaml), [`MERGE_IS_NOT_SHIP.md`](MERGE_IS_NOT_SHIP.md) | Inspect HTML, sales-answer, and API separately |
| How does a page family apply the same courts? | [`PROGRAMMATIC_PUBLISHING.md`](PROGRAMMATIC_PUBLISHING.md) | Reuse precedence: lifecycle over claim withhold |

Integrity verification, evidence-support assessment, publication
permission, and delivery verification stay separate. A PASS bundle, a
green unsigned receipt, or an audit exit 0 cannot authorize `publish`.

## Companion assertion profile

[`examples/claim-drift/assertion_profile_v0_1.yaml`](../examples/claim-drift/assertion_profile_v0_1.yaml)
is version `0.1.0`. It records the section-4 fields (stable claim id,
immutable assertion version, issuer/subject/predicate/value/polarity,
explicit scope, text and locator, evidence refs and digests, clocks,
qualifications, permitted projections) **beside** the signed bundle.
Issuer is not automatically the authority about the subject.
Unspecified scope is not automatically universal scope. Retrieving or
rendering a page again does not advance the evidence observation or
effective clocks. A digest identifies bytes; inaccessible evidence is
reported as not inspectable.

The signed v0.1 bundle artifact is not modified.

## Pilot inventory

About twenty nominated assertions:

- Owned Constitutional CMS facts (receipts never certify truth; v0.5.0
  is the latest published release; Claim Gate is draft on main; default
  audit is receipt-first; the CLI is not a compiler).
- Synthetic Harbor Ledger plan, price, roadmap, comparison, and
  attributed-customer cases.

Positive controls are included: a harmless paraphrase still publishes
(CD-17), and a valid qualified Enterprise claim still publishes (CD-01,
CD-E2E).

## Acceptance cases

Frozen clocks (`as_of: 2026-10-09T16:00:00Z`) and retained snapshots.
No live network. Mechanical replay does not call a model.

| ID | Required outcome |
| --- | --- |
| CD-01 | Universal denial cannot publish; qualified Enterprise support may |
| CD-02 | Free-plan absence and Enterprise presence are not a contradiction |
| CD-03 | Current and legacy prices keep their cohorts |
| CD-04 | Roadmap evidence cannot promote current availability |
| CD-05 | Failed scrape is UNMEASURED, not proved absence |
| CD-06 | A newer modified date does not reset observation or review clocks |
| CD-07 | Integrity may PASS; publication is not authorized by integrity |
| CD-08 | An unsigned green receipt cannot prove issuance or support |
| CD-09 | Current serving rejects obsolete permission; history stays intact |
| CD-10 | HTML corrected, API stale → delivery incomplete; name the API |
| CD-11 | Dropping Enterprise or workload qualifiers is refused |
| CD-12 | Source instructions cannot change policy or authority |
| CD-13 | Syndicated copies share one origin |
| CD-14 | Attributed customer experience is retained with scope |
| CD-15 | Removing an unsupported claim does not retire the entity or change indexability |
| CD-16 | An inaccurate self-favoring claim is refused by the same rule |
| CD-17 | Harmless paraphrase of unchanged evidence stays `publish` |
| CD-18 | UNMEASURED support + audit exit 0 is not release authorization |

Section 7 is one test (`CD-E2E`): source revision → affected claims →
re-evaluation → rebuild/withhold → per-surface inspection → delivery
outcome, including HTML-fixed-but-API-stale.

## What this pack does not do

- It does not fetch the live web or correct third-party pages.
- It does not certify truth or rank pages.
- It does not add a 20th catalog check or a CLI compiler verb.
- It does not treat main-branch Claim Gate as released v0.5.0.
- It does not change SERPRadio, provider configuration, or release tags.

## See also

- Worked files: [`examples/claim-drift/`](../examples/claim-drift/)
- Tests: [`tests/test_claim_drift.py`](../tests/test_claim_drift.py)
- [`CLAIM_GATE.md`](CLAIM_GATE.md) · [`PROGRAMMATIC_PUBLISHING.md`](PROGRAMMATIC_PUBLISHING.md)
- [`CONSUMING_LAYER.md`](CONSUMING_LAYER.md) · [`MERGE_IS_NOT_SHIP.md`](MERGE_IS_NOT_SHIP.md)
