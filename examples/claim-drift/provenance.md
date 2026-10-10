# Claim Drift pack — provenance

**Provenance mode: mixed (owned-repo excerpts + synthetic).**

This directory is teaching material for the Claim Drift application pack.
It is not a customer corpus, a production deployment, or a measured outcome.

## Owned-site excerpts

Short passages under `sources/ccms-*.md` are frozen snapshots of public
Constitutional CMS repository text (README, CLAIM_GATE, CHANGELOG, catalog).
They are retained so replay does not fetch the live tree. Retrieval and
observation clocks are fixture fields. Re-reading these files must not
advance those clocks.

## Synthetic comparison and plan fixtures

Harbor Ledger, CompareStack, and the Free / Enterprise plan records are
fabricated. They exist so plan-scope, pricing-cohort, roadmap-versus-GA,
syndication, and customer-attribution cases can be replayed offline.

They are **not** Render, Railway, or any other vendor. The acceptance
packet listed public comparison URLs as observation sources; this pack
does not copy those pages and does not perform network retrieval.

## What this is not

- Not a released v0.5.0 feature.
- Not a live pilot.
- Not a public source-registry change.
- Not SERPRadio, tgflightsfromnyc, Railway, or production configuration.
