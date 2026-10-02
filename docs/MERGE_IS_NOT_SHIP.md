# Merge is not ship

Provenance: public pattern library. Not a check catalog. Not a release-gate list.

```
Canonical question: when may a change be called done?
Governs: the claim that a change to code, contracts, content, or a package has reached the people and machines that read it
Must not be used as: a CheckCatalogV1 check, a G0–G5 substitute, a work-ordering scheme, or a FAIL for UNMEASURED
```

Read [`PROTOCOL_MAP.md`](PROTOCOL_MAP.md) first. This page classifies delivery claims. It does not order work.

## The law

> Merged is not served. Served is not accepted. A live receipt proves done.

Green CI proves that a candidate passed the checks that ran against it. It does not prove that any reader received the
change. The sprint contract already says this ("not when PRs merge — when production proves it"). This page names the
gaps between those two moments, so an agent cannot close one gap and report the whole chain.

## The relations are distinct

[`contracts/promotion_protocol_v1.yaml`](../contracts/promotion_protocol_v1.yaml) states the relation ladder: planned,
referenced, implemented, published, promoted, and served are distinct relations. None implies the next without an
artifact or an evaluation receipt. For a delivery claim, read the ladder like this:

| Relation | What proves it | What does not prove it |
|---|---|---|
| Accepted for merge | A queued merge request | Nothing about the target branch |
| Merged | The target branch contains the exact commit | An API response code, a closed PR, a bot comment |
| Built | An artifact with a build identity and a content hash | A green CI run on a different commit |
| Promoted | The one authoritative pointer names the new generation | A deploy log, a preview URL |
| Served | The wire returns the new identity on each surface | The origin alone, a cache-busted read alone |
| Accepted | The live surface satisfies the contracts it claims, in the same proof packet | Merge, deploy, or agent assertion |

The last row is the proof ledger's `live_verified` status
([`contracts/proof_ledger.yaml`](../contracts/proof_ledger.yaml)): done means authority-backed evidence, not merge,
deploy, or agent assertion. External outcomes are one step further again. Merge, deployment, promotion, and served
identity cannot substitute for outcome evidence ([`contracts/outcome_record.yaml`](../contracts/outcome_record.yaml)).

## Evidence binds to an exact head

Every review, test result, approval, and attestation is about one exact commit. It is not about a branch name and it is
not about a pull request number.

- **Record the head.** A proof packet names the exact commit it observed. "The PR is green" is not evidence.
- **Moving the head voids the evidence.** A new push, a rebase, or a base-branch change that alters the merge result
  creates a different object. Evidence about the old head is stale. Re-run it, or report the claim as `inconclusive`.
- **Merge the head you verified.** Where the merge interface accepts an expected head, pass it. A merge that lands a
  commit nobody reviewed is a new, unreviewed change.
- **Read open findings at the moment of signing.** Unresolved review findings on the exact head block an attestation.
  A finding resolved on an earlier head does not carry forward by default.

[`contracts/work_order_v1.yaml`](../contracts/work_order_v1.yaml) records `exact_base_commit` for the same reason:
exact-head ancestry, never a stale checkout.

## Accepted is not merged

Some merge interfaces answer before the merge happens. Merge queues, auto-merge, and asynchronous merge APIs can reply
`202 Accepted`. That reply means a request is queued. The request can still fail a required check, hit a conflict, or
leave the queue.

- Verify a merge by reading the target branch, not the response. The merge commit must be an ancestor of the trunk:

  ```bash
  git fetch origin
  git merge-base --is-ancestor <commit> origin/main && echo merged
  ```

- **Stacked pull requests.** Merging a base pull request does not merge the pull requests stacked on it. A child may be
  retargeted, left on a deleted branch, or closed. A child that merged into its parent branch is not on the trunk until
  the parent lands with it. Check each commit against the trunk, one at a time.
- A closed pull request is not a merged pull request. Read the merge state, not the status icon.

## Each delivery surface verifies on the wire

One change usually reaches readers through several surfaces. Each surface has its own pipeline, its own cache, and its
own clock. A deploy to one surface does not update another.

| Surface | Typical gap after merge |
|---|---|
| Origin HTML | The merge does not trigger a deploy, or the deploy picks up an older snapshot |
| Edge cache | Serves the previous body until purge or expiry |
| Structured data, headers, agent API | Emitted by a different code path from the body |
| Sitemap, feeds | Regenerated on a schedule, not on deploy |
| Package registry | A tag and a built wheel exist; the registry does not serve the package |
| Documentation site | Built from a different branch or a pinned release |

For each surface the change claims:

1. Request it from outside, the way a reader does. Check the cached path that readers receive, and use a cache-busted
   read only to tell the origin from the cache.
2. Compare identity, not appearance. Use the build or generation identity and the content hash that a served artifact
   carries ([`contracts/cache_materialization.yaml`](../contracts/cache_materialization.yaml)). Visual similarity is not
   identity.
3. Record one check per surface: the question, the authority, the observed value, and `checked_at`.
4. If a surface could not be observed, the claim is `blocked` or `inconclusive`. It is not done.

A tag is not a release. A release is not an install. A package is installable when `pip install` succeeds from a clean
environment against the public registry. A clean-wheel test inside CI proves that the wheel builds and runs. It does not
prove that a stranger can install it.

## For adopters of the CLI

`constitutional-cms audit` writes a receipt and exits `0` by default ([`CLI.md`](CLI.md)). With `--fail-on FAIL` in CI,
it blocks a candidate that fails the catalog. Both modes judge the evidence you collected before the merge. Neither
mode observes what is served after the merge.

To claim done, collect evidence from the served surfaces after promotion and audit that evidence again. A receipt from
the public recreate path stays `certified: false`. That is correct.

## What this page is not

- Not a deploy procedure. Pipelines differ. The relations do not.
- Not a ban on merging early. The error is to report the merge as the last step.
- Not a new receipt schema. A proof ledger packet with one check per surface is enough.
- Not a release-gate list and not G0–G5. Page-family certification remains the only adoption sequence.
