# Provenance

**Provenance mode: synthetic**

Everything under `examples/programmatic-publishing/` was authored for this
public repository as teaching material. It does not describe a customer, a
live catalogue, a production threshold, or a measured search outcome.

| Field | Value |
| --- | --- |
| Domain name | Northline Desk Co. |
| Kind | Synthetic ecommerce catalogue (desk goods) |
| Records | Fabricated product, collection, and comparison pages |
| Identifiers | `product:northline-*`, `collection:desk-essentials`, `catalog.example` |
| Sources | Named snapshot and feed ids that exist only in these fixtures |
| Thresholds | Teaching numbers (`64.00` USD, word-count floors). Not operational SLAs |
| Dates | Pinned to 2026-10-04 for determinism |

Do not copy these entity ids, prices, or hashes into a private implementation
and treat them as production authority. Replace the vocabulary; keep the
portable rules.

Forbidden in this directory (and absent here): customer records, private
receipts, High Command traces, SERPRadio / G5 / route-registry exports,
credentials, and connection strings.

Missing provenance on a later public example is a release blocker, not a
documentation nit. See [`docs/SOURCE_BOUNDARY.md`](../../docs/SOURCE_BOUNDARY.md).
