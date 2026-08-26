# Entity lifecycle and terminality

Companion to [`CONSUMING_LAYER.md`](CONSUMING_LAYER.md). Contract: [`entity_lifecycle_v1.yaml`](../contracts/entity_lifecycle_v1.yaml). Detector: `constitutional-cms lifecycle-check`.

**Status:** DRAFT until a founder tag. Not a CheckCatalogV1 check. Signal Contract v1 is unchanged.

```
Canonical question: Does this entity or relationship exist, and may its representation be gone?
Classifies: identity, lifecycle, terminal transitions, artifact 410
Must not be used as: claim state, page quality tier, Signal event meaning, work priority
```

## The gap

We governed the truth of **claims** without fully governing the truth of **entities** and their **lifecycle transitions**.

The first law stays:

> Do not let the consuming layer invent truth.

The companion law:

> **Do not let one truth domain revoke another truth domain's existence.**

Beneath it:

> **Absence is scoped. Terminality is explicit.**

Unknown is a state. **Gone is also a state — and it requires authority.** HTTP 410 is a semantic assertion: this representation has been intentionally and permanently removed. It needs at least as much authority as a public price.

## Five layers that must not collapse

| Layer | Question |
|---|---|
| Entity identity | What thing are we talking about? |
| Entity / relationship lifecycle | Does it exist, and in what state? |
| Claim state | What do we currently know and have the right to say? |
| Artifact state | Should this page/API/schema exist? |
| Perception state | Does a change deserve attention? (Signal Contract + VIBEnet) |

A market can **exist**, a service relationship can be **seasonally inactive**, current fare **unmeasured**, historical range **published**, timing **stale**, the page **200**, Offer schema **suppressed**. That is not a contradiction.

Category errors happen when one layer says “this fact is unavailable” and another concludes “the entity is gone.”

## Ten invariants

1. Identity is not evidence. Missing evidence does not delete an entity.
2. Entity state is not claim state. A withheld claim does not retire its subject.
3. Relationship state is not entity state.
4. Seasonal inactive is not retired.
5. Unknown is not absent.
6. Absent is not terminal.
7. A child fact cannot escalate the parent to terminal.
8. A renderer cannot derive lifecycle state.
9. 410 requires an explicit terminal authority.
10. Every lifecycle transition produces a receipt.

`410` must never be projected from: missing price, missing timing, child API 404, no current observation, season ended, inactive relationship, timeout, unknown, withheld, unmeasured — unless the **entity constitution** names that condition as terminal.

## Domain Adapter

Constitutional CMS does not know aviation, SKUs, dockets, or patients. It knows:

`entity · relationship · lifecycle · claim · authority · transition · artifact · projection`

The Domain Adapter supplies vertical vocabulary (airports and route markets, or products and inventory, or cases and filings). SERPRadio is one adapter. The protocol stays generic.

VIBEnet never decides whether an entity is seasonal or retired. It receives `entity` + `event` from governed state. The audio renderer may not turn `service.seasonal_pause` into `entity.retired`.

## Architecture pairing

> The Domain Ontology says what exists. Constitutional CMS says what may be asserted about it. Signal Contract says what changed. VIBEnet decides how that change becomes perceptible.

## Thought-leadership spine (not a bug post)

Do not publish this as “we found a 410 bug.” The piece is **Gone Is a Verdict**:

> We spent months teaching an AI publishing system not to make things up. Then we discovered it could still make things disappear.

Arc:

```
UNKNOWN IS A STATE
        ↓
ABSENCE IS TYPED
        ↓
TERMINALITY REQUIRES AUTHORITY
        ↓
GONE IS A VERDICT
```

False positives: unsupported things a model says. False negatives: real things that disappear because one downstream layer lacked evidence. Both are authority failures. The fix is not another prompt. It is ontology.

Chair owns whether and when that essay is posted.

## Detector

```bash
constitutional-cms lifecycle-check --projection tests/fixtures/lifecycle/legal_concurrent_states.yaml
constitutional-cms lifecycle-check --projection tests/fixtures/lifecycle/child_404_to_parent_410.yaml
```

Exit 0: no collapse detected. Exit 1: one or more invariant violations. Exit 2: operational error. This is not the catalog `audit` path and does not change `certified`.
