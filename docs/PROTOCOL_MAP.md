# Canonical Protocol Map

Constitutional CMS uses several schemes because they govern different objects. This map is the consuming-layer rule:
identify the question first, then use only the scheme authoritative for that question.

> A taxonomy may not silently answer a question owned by another taxonomy.

| Scheme | Canonical question | Governs | Must not be used as |
| --- | --- | --- | --- |
| Five contract families | What part of publishing is governed? | Page types, enrichment stages, link graph, snapshot boundary, sprint acceptance | Maturity, severity, or work priority |
| Incident-learned invariants | What falsifiable condition must remain true? | Portable rules expressed through generalized failure scenarios | A second set of contract families |
| G0-G5 certification states | How completely has a page family adopted and evidenced the framework? | Implementation maturity and evidence coverage | A page publication tier or check-profile score |
| Eight release gates | What evidence must a release candidate pass? | Publication and verification sequence | Backlog ranking |
| Four-layer repair stack | Which dependent layer on one surface is repaired first? | Data truth → content truth → depth → experience | Portfolio-wide prioritization |
| Seven control priority classes | Which admissible intervention deserves attention next? | Constitutional blockers through theory work | A numeric score or repair layer |

Counts are labels, not identities. A five-item invariant release and the five contract families are unrelated sets. A
page tier is not conformance. A release gate is not priority. A repair layer is not a control class.

Only two schemes order work: the four-layer repair stack orders dependent repairs on one surface, and the seven
control priority classes order unlike interventions. Contract families, invariants, check profiles, publication tiers,
certification states, and release gates classify other objects; they do not create additional priority queues.

## Taxonomy admission rule

A proposed scheme does not enter the protocol until it declares all of the following:

1. the single canonical question it answers;
2. the object it governs;
3. whether it classifies, orders, or certifies;
4. its relationship to every existing scheme that could appear to answer the same question; and
5. which existing scheme, if any, it retires.

The four web-conformance profiles are selectable evidence groupings, not levels, scores, or an ordering scheme.
G0-G5 remains the only adoption and certification sequence.

## Adjacent awareness protocol

VIBEnet Signal Contract is a separate public protocol for renderer-facing
awareness events. It is not a fifth Constitutional CMS profile and it is not a
G0-G5 substitute.

- Canonical question: what may a renderer notice about agent or system state?
- Public source: [vibenet-signal-contract](https://github.com/jamesfgibbons/vibenet-signal-contract)
- Live schema: [vibenet.ai/protocol](https://vibenet.ai/protocol)

A conformance receipt may cite a Signal Contract event as evidence that a
human-facing renderer was honest. It may not treat sonification, attention
mix, or an adapter profile as page-family certification.

## Publishing heuristics (not a scheme)

[`docs/PUBLISHING_HEURISTICS.md`](PUBLISHING_HEURISTICS.md) classifies recurring
smells (for example: child URLs without a collection hub). Heuristics are not a
taxonomy admission. They do not order work, they are not CheckCatalogV1
checks, and they must not turn missing evidence into FAIL.

The inverse of `hub_to_children` is `children_require_hub` in
[`contracts/link_rules.yaml`](../contracts/link_rules.yaml), enforcement
`soft_warn` until a founder ratifies `hard_block`.

## Routing sequence

1. **Contract family:** which publishing boundary owns the change?
2. **Invariant:** what falsifiable condition must remain true?
3. **Probe:** what observation can falsify it, and what is the probe's `mutation_class`?
4. **Measurement state:** PASS, FAIL, or UNMEASURED. Missing required inputs never imply PASS.
5. **Ordering:** use the repair stack inside one surface; use a control priority class across unlike interventions.
6. **Release gate and receipt:** promotion depends on independently checkable evidence, not the priority label.

The framework does not yet publish a heavyweight control-decision receipt. The lightweight
[`outcome_record.yaml`](../contracts/outcome_record.yaml) comes first: it preserves append-only actuals and keeps
delivery proof distinct from external outcomes. Decision calibration waits until enough precommitted expectations and
observed actuals exist to evaluate it.
