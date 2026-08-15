# Canonical Protocol Map

Constitutional CMS uses several schemes because they govern different objects. This map is the consuming-layer rule:
identify the question first, then use only the scheme authoritative for that question.

> A taxonomy may not silently answer a question owned by another taxonomy.

| Scheme | Canonical question | Governs | Must not be used as |
| --- | --- | --- | --- |
| Five contract families | What part of publishing is governed? | Page types, enrichment stages, link graph, snapshot boundary, sprint acceptance | Maturity, severity, or work priority |
| Incident-learned invariants | What falsifiable condition must remain true? | Portable rules expressed through generalized failure scenarios | A second set of contract families |
| Four conformance levels | How completely has an implementation adopted the framework? | Implementation maturity and evidence coverage | A page tier or release certificate |
| Eight release gates | What evidence must a release candidate pass? | Publication and verification sequence | Backlog ranking |
| Four-layer repair stack | Which dependent layer on one surface is repaired first? | Data truth → content truth → depth → experience | Portfolio-wide prioritization |
| Seven control priority classes | Which admissible intervention deserves attention next? | Constitutional blockers through theory work | A numeric score or repair layer |

Counts are labels, not identities. A five-item invariant release and the five contract families are unrelated sets. A
page tier is not conformance. A release gate is not priority. A repair layer is not a control class.

## Routing sequence

1. **Contract family:** which publishing boundary owns the change?
2. **Invariant:** what falsifiable condition must remain true?
3. **Probe:** what observation can falsify it, and what is the probe's `mutation_class`?
4. **Measurement state:** PASS, FAIL, or UNMEASURED. Missing required inputs never imply PASS.
5. **Ordering:** use the repair stack inside one surface; use a control priority class across unlike interventions.
6. **Release gate and receipt:** promotion depends on independently checkable evidence, not the priority label.

The framework does not yet publish a heavyweight control-decision receipt. Outcome capture should precede decision
calibration; otherwise an ex-ante form adds overhead without evidence that forecasts can be evaluated.
