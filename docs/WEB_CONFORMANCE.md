# Web Conformance

Constitutional CMS Web Conformance is one standard with four selectable profiles. Profiles group checks by the
evidence they consume; they are not levels, rankings, certifications, or a replacement for the protocol's G0-G5
page-family certification states.

| Profile | Governs |
| --- | --- |
| Web Foundation | Transport, semantics, accessibility, responsive behavior, security, lab performance, and field evidence |
| Search | Crawl, index, canonical, structured-data, corpus, and link-graph integrity |
| Answer and AI Retrieval | Extractable answers, primary entities, provenance, freshness, and crawler choice |
| Agentic Web | Typed actions, authority, consent, mutation classes, idempotency, failure behavior, and receipts |

## Authority posture

The standards registry distinguishes formal external standards, platform guidance, Constitutional CMS rules, and
experimental work. A platform-guidance PASS does not guarantee crawling, indexing, ranking, citation, or inclusion.
Experimental checks cannot block stable conformance or grant certification.

## Evidence before verdict

The reference evaluator accepts `EvidenceBundleV1` and produces `ConformanceReceiptV1`. It has no network access and
does not know an implementation's private schema. Required evidence that is missing, stale, invalid, or unavailable
is `UNMEASURED`, with a stable reason code. Invalid evidence is a measurement defect, not a policy failure.
`NOT_APPLICABLE` is reserved for valid declared applicability evidence that is false.

```bash
python scripts/conformance_evaluator.py \
  --evidence tests/fixtures/conformance/pass_all.yaml \
  --as-of 2026-08-15T12:00:00Z
```

Applicability evidence is evaluated before check evidence. If applicability cannot be determined, the result is
`UNMEASURED`; if it is valid and false, the result is `NOT_APPLICABLE` even when the check evidence is absent.

The receipt reports verdict counts and evidence coverage by profile. It deliberately does not create a universal
score. Its evaluation context and SHA-256 digests follow [`CANONICAL_JSON.md`](CANONICAL_JSON.md), so the same catalog,
evidence, and clock produce the same result identity. A page check remains diagnostic; G5 certification requires a
complete page-family census and monitored proof.

## Performance language

Lighthouse and other synthetic browser measurements are lab evidence. LCP, INP, and CLS become field Core Web Vitals
only when supplied as sufficient real-user observations at the required percentile. Missing field data remains
`UNMEASURED`; it is never replaced with a lab value or zero.

## Recreating a check

1. Read the stable check definition in `contracts/check_catalog_v1.yaml`.
2. Collect the listed evidence scope without exceeding its declared mutation class or freshness limit.
3. Normalize observations into `EvidenceBundleV1`.
4. Run the reference evaluator.
5. Verify reason codes and the receipt digest against the synthetic fixture matrix before integrating it into CI.

The JSON Schemas in `schemas/` are the portable wire contracts. YAML files in `contracts/` explain the associated
governance rules and vocabularies.
