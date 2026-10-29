# Frozen excerpt — CHANGELOG.md / v0.5.0 (owned repository)

Frozen-at: 2026-10-01T12:00:00Z
Observed-at: 2026-08-22T00:00:00Z
Origin: constitutional-cms / CHANGELOG.md
Attribution: Constitutional CMS public repository, pinned for offline replay.

## [0.5.0] - 2026-08-22

Run the Constitution. This is the distribution release: one framework
identity, a wheel that works outside the clone, and a receipt-first CLI.

CheckCatalogV1 1.0.2 ships 19 checks. certified remains false on the
public recreate-a-check path. The evaluator performs no network access.
Default audit is receipt-first: it writes a valid receipt and exits 0.
A catalog FAIL does not block a release unless CI asks it to.

License: Apache-2.0. The public CLI evaluates evidence and writes
receipts. It is not a site compiler.
