# Publishing heuristics

Provenance: public pattern library. Not a check catalog. Not a work-ordering scheme.

Laws say what must never be false. Heuristics say what is usually true, with named exceptions. This file is the latter.

```
Canonical question: what smell should an agent notice before it becomes a law?
Governs: collection IA, parent/child URL shape, sitemap vs landing
Must not be used as: CheckCatalogV1 verdicts, G0–G5, repair-stack order, or a FAIL for UNMEASURED
```

Read [`PROTOCOL_MAP.md`](PROTOCOL_MAP.md) first. Heuristics **classify**. They do not order work and they do not certify.

## Law vs heuristic vs Chair gate

| Layer | Question | If it ships false | Enforcement |
|---|---|---|---|
| **Law** | What must never be false? | The system is broken | Contract + test; `hard_block` / fail-closed |
| **Heuristic** | What is usually true? | A smell, until ratified | `soft_warn` / gap list / UNMEASURED |
| **Chair gate** | What only the founder may flip? | Agent theater | YES / tag / merge / narrative |

Do not put heuristics in `CheckCatalogV1`. Missing evidence stays `UNMEASURED`, never FAIL.

## How to identify the next one

When an observation arrives, classify it **before** coding:

1. **Already a law?** Cite the invariant or contract. Do not duplicate it as a heuristic.
2. **Heuristic?** Recurring `if A then usually B`, with exceptions. Write the five fields below.
3. **One-off bug?** Fix the product. Do not promote it to doctrine.
4. **Ratchet.** A heuristic that keeps biting becomes a named rule plus one probe that would have failed ([contract-as-test](V0_2_REFERENCE_PATTERNS.md)).

Five fields for every heuristic:

| Field | Meaning |
|---|---|
| **Trigger** | The observed shape (`/{family}/{slug}` renders) |
| **Expected surface** | What should exist (`/{family}` 200, or typed absence) |
| **Failure mode** | What crawlers/users/agents actually receive |
| **Exception** | When the smell is allowed (suppressed family, not yet in sitemap) |
| **Ratchet test** | The probe that would have failed before the fix |

## Inverse of `hub_to_children`

[`contracts/link_rules.yaml`](../contracts/link_rules.yaml) already has `hub_to_children` (`soft_warn`): if a hub exists, it should link down.

The missing inverse is **`children_require_hub`** (also `soft_warn`): if child entity pages exist, the collection index should exist — or the family should be an explicit typed absence, not a naked 404.

A silent 404 on the parent while children and a family sitemap are public is the smell. It is not yet a `hard_block`. Ratifying it to `hard_block` is a Chair gate: it would make every live family without a hub unlawful overnight.

### H1 — Children require a hub

- **Trigger:** at least one `/{family}/{slug}` (or deeper child) returns 200.
- **Expected:** `/{family}` returns 200 as an index hub, **or** the family is documented `SUPPRESS` / typed absence with no public sitemap for that family.
- **Failure mode:** orphaned leaves. Users and crawlers who strip the slug hit 404. Internal links have nowhere honest to point “up.”
- **Exception:** a family that is not public yet; a leaf that is not in a collection; a URL that is an alias, not a child.
- **Ratchet:** rendered probe: for each public child prefix, GET the parent. Gap if parent is 404 while a sitemap lists that family.

### H2 — Sitemap implies a landing

- **Trigger:** `sitemap-{family}.xml` (or equivalent) is public and lists member URLs.
- **Expected:** the collection URL those members share is a 200 landing, not a 404.
- **Failure mode:** discovery advertises a family whose index does not exist. Rendered truth disagrees with sitemap intent ([incident invariant: rendered truth beats resolver intent](INCIDENT_LEARNED_INVARIANTS.md)).
- **Exception:** the sitemap is not public; members are listed only under another family's hub by design.
- **Ratchet:** every public sitemap prefix has a 200 parent or a documented suppress.

### H3 — Sibling families stay isomorphic

- **Trigger:** several collections on the same site use the same URL grammar (`/airports`, `/airlines`, `/flights`, …).
- **Expected:** each public collection has a hub, unless a named exception lists that family.
- **Failure mode:** one missing index looks like a hole in an otherwise regular IA. Agents copy the hole.
- **Exception:** a family Chair has explicitly parked; a family that is not a collection.
- **Ratchet:** a table of families × hub status. Gaps are UNMEASURED until a hub ships or an exception is named.

## What this file does not do

- It does not add a twentieth catalog check.
- It does not order the repair stack or invent G0–G5 substitutes.
- It does not tell a private product which hub to build first. Product repos keep their own gap lists.
- It does not treat a `soft_warn` as a ship-blocker.

Distribution, seating, and first-screen rules (working install, do not advertise 404 commands, one PR per intent) are operator doctrine. They use the same classify-before-coding method. They are not CheckCatalog checks.
