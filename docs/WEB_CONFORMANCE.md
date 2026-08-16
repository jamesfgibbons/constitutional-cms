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
does not know an implementation's private schema. If required evidence is absent, the verdict is `UNMEASURED`.
`NOT_APPLICABLE` is reserved for a declared applicability condition that is present and false.

```bash
python scripts/conformance_evaluator.py \
  --evidence tests/fixtures/conformance/pass_all.yaml
```

The receipt reports verdict counts and evidence coverage by profile. It deliberately does not create a universal
score. A page check remains diagnostic; G5 certification requires a complete page-family census and monitored proof.

## Performance language

Lighthouse and other synthetic browser measurements are lab evidence. LCP, INP, and CLS become field Core Web Vitals
only when supplied as sufficient real-user observations at the required percentile. Missing field data remains
`UNMEASURED`; it is never replaced with a lab value or zero.

## Recreating a check

1. Read the stable check definition in `contracts/check_catalog_v1.yaml`.
2. Collect the listed evidence scope without exceeding its declared mutation class.
3. Normalize observations into `EvidenceBundleV1`.
4. Run the reference evaluator.
5. Compare the receipt with the synthetic fixtures before integrating the evaluator into CI.

The JSON Schemas in `schemas/` are the portable wire contracts. YAML files in `contracts/` explain the associated
governance rules and vocabularies.
