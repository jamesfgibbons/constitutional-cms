# Claim Gate v0.1 — ClaimBundle + ClaimReceipt

**Status: DRAFT (pre-ratification).** v0.1 of the CLAIM objects is draft until
the founder tags a release. Five-minute read. For external implementers, THIS
PROSE plus the schemas and the golden fixtures under `tests/golden-claims/`
are the law — everything needed for a fully independent implementation ships
in those files. `tests/test_claim_gate.py` is the reference implementation's
internal enforcement of the same law, not a normative source.

## The two objects

| | ClaimBundleV0_1 | ClaimReceiptV0_1 |
| --- | --- | --- |
| Role | Frozen, hashed, Ed25519-signed core | Volatile verification record |
| Identity | `bundle_hash` | `receipt_hash` (+ `receipt_id`) |
| May contain volatile facts | **Never** | Yes — that is its job |
| Refers to the other | — | QUOTES `bundle_hash` |

A **bundle** carries claims: `claim_id` (`claim:` prefix), any JSON `value`,
the `authority` (registry source id) that grounds it, `observed_at`,
`valid_until`, and an `evidence_digest`. Bundle-level fields: `issuer`
(a domain — keys are discovered under it), `subject {type, id}`,
`policy_digest` (digest of the governing catalog/contract), optional
`generation_digest`, `generated_at`, `valid_until`, `bundle_hash`,
`signature {alg: "Ed25519", key_id, sig}`.

A **receipt** records one verification: `receipt_id` (`cr_…`), the quoted
`bundle_hash`, a verdict from the house lattice
`PASS | FAIL | UNMEASURED | NOT_APPLICABLE`, typed `reason_codes`,
`verified_at`, `valid_until`, `evaluator {name, version}`, supersession
fields, optional `bindings {decision_hash, signal_id}`, and `receipt_hash`.

A receipt verifies **integrity and policy conformance of the bundle — never
"truth"** (the same honesty rule as `certified: false` on conformance
receipts). A PASS receipt means: canonical bytes intact, the bundle's `issuer`
is the issuer the keys document publishes keys for, the signature is valid
against that issuer's published key, the expiry law is satisfied, and at least
one claim carries a measured verdict.

## What a v0.1 receipt does NOT prove

Read this before treating a receipt as evidence of anything.

- **A v0.1 receipt is UNAUTHENTICATED.** It carries no signature. `receipt_hash`
  is a self-consistency check over the receipt's own core bytes — it proves the
  record has not been edited since *someone* computed the hash, and nothing
  about who that someone was. Anyone can mint a green-looking ClaimReceipt for
  any `bundle_hash` in a few lines of code.
- **A receipt is not evidence that an issuer ever verified anything.** It is not
  a counter-signature, an attestation, or a transferable proof.
- **Only the bundle + keys path is authoritative.** A consumer that needs a
  verified claim runs `claim-verify --bundle … --keys …` (or
  `claims.verify_bundle`) itself. Receipt-only verification answers a narrower
  question — "is this record internally consistent, current, and not
  superseded?" — and the CLI says so: receipt-only mode prints
  `RECEIPT INTEGRITY OK (unauthenticated …)`, never `VERIFIED`.
- **Supersession is an issuer-side assertion, not a revocation mechanism.** See
  "Supersession" below.

Authenticated (signed) receipts are deferred until earned; see the last
section.

## Canonicalization and hashing

Exactly `docs/CANONICAL_JSON.md` — the one house digest procedure, one code
path (`constitutional_cms.evaluator.canonical_json` / `digest`): keys sorted,
array order preserved, non-finite numbers rejected, integral floats emitted as
integers, separators `(",", ":")`, `ensure_ascii=False`, SHA-256 lowercase hex.

### Portability MUST-rejects

The whole point of a claim bundle is that an implementation you did not write
can reproduce the hash. Two JSON shapes make that impossible, so v0.1 refuses
them rather than hashing bytes another verifier cannot reproduce:

- **Duplicate object members.** RFC 8259 leaves duplicates undefined;
  implementations disagree (Python and JavaScript keep the LAST, some parsers
  keep the first, some error). A verifier MUST refuse a document that contains
  a duplicate member in any object — refused at parse time, before any hash is
  computed. The reference CLI does this on every file it reads.
- **Non-interoperable numbers.** Canonicalization collapses integral floats
  (`1.0` → `1`), and arbitrary-precision integers become 300-digit literals
  that no double-parsing implementation reproduces. A bundle or receipt
  containing a JSON float, or an integer whose magnitude exceeds `2^53 - 1`, is
  refused (`bundle_malformed` / `receipt_malformed`). v0.1 claim values that
  need a number carry it as a string.

  **Scope — this is not a contradiction of `docs/CANONICAL_JSON.md`.** The two
  documents govern different artifacts and both statements are in force:
  CANONICAL_JSON.md defines the digest procedure for ALL house artifacts, and
  under it an integral float COLLAPSES (`1.0` → `1`) — that remains the rule
  for the older conformance artifacts (`CheckCatalogV1`, `EvidenceBundleV1`,
  `ConformanceReceiptV1`), which may legitimately carry floats such as a
  coverage `ratio`. Claim bundles and claim receipts are the STRICTER
  artifacts: they refuse a float at the door rather than relying on the
  collapse, because a third-party verifier reproducing the hash must not have
  to reimplement the collapse rule correctly. Claim artifacts never reach the
  collapsing branch; conformance artifacts never reach this refusal.

Unicode normalization is NOT yet specified (see the debt list in the PR):
`ensure_ascii=False` means the exact code points are hashed, so a producer that
NFC-normalizes and one that does not will disagree. v0.1 hashes what it is
given.

Outer hashes are MANDATORY-prefixed `sha256:<64 lowercase hex>`:

- `bundle_hash` = sha256 over the canonical bundle with `bundle_hash` **and**
  `signature` omitted.
- `receipt_hash` = sha256 over the canonical receipt with `receipt_hash`,
  `superseded`, and `superseded_by` omitted (see supersession below).
- When QUOTING a legacy serpradio `decision_hash` in `bindings`, the prefix is
  optional: `^(sha256:)?[0-9a-f]{64}$`. Everywhere else the prefix is required.

## Signing

- Algorithm: Ed25519 only in v0.1. `sig` is base64 of the 64-byte signature.
- The signature covers **the same canonical bytes `bundle_hash` covers**.
- Private keys are files (PEM PKCS8), referenced by path or by the
  `CONSTITUTIONAL_CMS_CLAIM_KEY` environment variable (a path, never a value).
  No tool in this repository prints, logs, or returns private key material.
- Verification fails CLOSED: an unknown `key_id` is a refusal
  (`key_unknown`), never a skip.

## Issuer binding — a key proves possession, never identity

A signature proves someone held a private key. It does not, on its own, say
*whose* claim this is. The possessive in "the issuer's published key" is
therefore NORMATIVE and enforced:

- The keys document MUST declare the `issuer` it publishes keys for.
- A verifier MUST refuse a bundle whose `issuer` differs from the keys
  document's `issuer`, with the code `issuer_mismatch`, **even when the
  signature verifies**.

Without this rule, anyone holding any key listed in `example.com`'s keys.json
could mint a bundle claiming `issuer: victim-bank.example` and it would verify
green against example.com's own document.

Bindings are per-document, so an offline verifier holding several issuers' key
files uses the one for the issuer it is checking; a keys document is never a
generic trust store.

## Verification clock

Verification time is an explicit INPUT (`as_of`), never an implicit wall
clock. A verifier that is given no `as_of` MAY use the current UTC time, but
it MUST report the clock it used: the receipt's `verified_at` IS the `as_of`
of that verification. Two verifiers given the same bundle, keys, and `as_of`
MUST produce identical receipts.

**`as_of` obeys the same six-digit grammar as every other timestamp, and
over-precision is REFUSED, never truncated and never rounded:** an `as_of`
carrying more than six fractional digits (`2026-08-15T12:30:00.1234567Z`) is
rejected as an OPERATIONAL error — **CLI exit 2**, no receipt emitted — because
it is verifier input, not an artifact under test, so it earns no
`bundle_malformed` verdict. This closes the last determinism hole: truncation
would silently map `…00.1234567Z` to `…00.123456Z` and `…00.0000006Z` to
`…00Z`, while rounding would map the latter to `…00.000001Z`, and each choice
mints a different `verified_at` → different `receipt_id` → different
`receipt_hash`. Refusal is the only behavior that cannot disagree with itself.
A caller that genuinely holds a finer clock MUST decide its own rounding
BEFORE calling the verifier, and then owns that decision visibly. Pinned by
`test_round4_as_of_finer_than_microsecond_is_refused_not_truncated` and
`test_round4_pinned_as_of_precision_rule_is_deterministic`.

## Timestamps are INSTANTS, never strings

Every timestamp comparison, ordering, and equality test in this spec is on the
**instant** a timestamp names, never on its lexical form. This is normative and
it is not a detail:

- The schema permits fractional seconds (`(\.[0-9]+)?`), and `.` (0x2E) sorts
  before `Z` (0x5A). So `2026-08-16T12:00:00.999999Z` sorts BEFORE
  `2026-08-16T12:00:00Z` as a string while being LATER as an instant.
  A string `min()` therefore computes the wrong "earliest claim" and a string
  `!=` calls two spellings of one instant unequal.
- `2026-08-16T12:00:00Z` and `2026-08-16T12:00:00.000Z` are the SAME instant and
  MUST compare equal.
- The `format: date-time` annotation is **not** enforced by this project's
  validator (no `rfc3339-validator` in the dependency set), and the pattern is
  only a shape. A conformant verifier MUST parse-validate every timestamp:
  `2026-13-45T99:99:99Z` matches the pattern and is not a date, and the leap
  second `2026-06-30T23:59:60Z` names no representable instant. Both are
  `bundle_malformed` / `receipt_malformed`, never an exception.
- **Fractional seconds are bounded to six digits** (`(\.[0-9]{1,6})?`, in the
  schema pattern and in the verifier's grammar). A seventh digit is REFUSED
  (`bundle_malformed` / `receipt_malformed`), never truncated. This bound is
  what makes the next rule implementable: comparison is exact at the full
  precision the grammar admits, so the comparison resolution and the
  arithmetic resolution are the same microsecond and no host language's clock
  precision can change a verdict.

### Computed timestamps have ONE spelling (normative)

An accepted timestamp may be spelled many ways, but every timestamp a
verifier COMPUTES — `verified_at` and the receipt's `valid_until` — MUST be
serialized by this rule, because `receipt_hash` covers those strings and
`receipt_id` is derived from `verified_at` as a string:

1. Convert the instant to UTC. The zone is always the literal `Z`; a numeric
   offset MUST NOT appear in a computed timestamp.
2. Write `YYYY-MM-DDThh:mm:ss`, then the fractional part by this rule:
   **omit the fraction entirely when the microsecond field is zero;
   otherwise write exactly six digits.** No other digit count is emitted —
   never `.0`, never `.000`, never `.500`.
3. Normalize BEFORE the value enters the receipt: an `as_of` of
   `2026-08-15T12:30:00.000Z`, `2026-08-15T12:30:00Z`, or
   `2026-08-15T08:30:00-04:00` all name one instant and MUST produce
   `verified_at` `2026-08-15T12:30:00Z`, the same `receipt_id`, and the same
   `receipt_hash`. An `as_of` of `2026-08-15T12:30:00.5Z` produces
   `2026-08-15T12:30:00.500000Z`.

Without this rule the spec contradicts itself: "two verifiers given the same
bundle, keys, and `as_of` MUST produce identical receipts" is unsatisfiable if
one of them spells the same instant differently. Pinned by
`test_gap9_equivalent_as_of_spellings_produce_byte_identical_receipts`.

## Expiry

**Earliest-expiry-governs, enforced by the verifier — not just prose.** The
bundle's `valid_until` MUST name the same INSTANT as the earliest
`claims[].valid_until`, where "earliest" is the minimum over instants. ANY
inequality of instants — later **or** earlier than the earliest claim — is
refused with the single code `expiry_mismatch`, even when correctly signed.
There is no second code for the earlier direction. A bundle that spells the
correct instant differently from its claim (`…12:00:00Z` vs `…12:00:00.000Z`)
is CONFORMANT and MUST verify.

**Expiry boundary is inclusive:** an artifact is expired when
`as_of >= valid_until`. At the exact instant `as_of == valid_until` a bundle
is refused (`bundle_expired`) and a receipt no longer represents current
state (`receipt_expired`). One golden pins the boundary instant
(`tests/golden-claims/expired_boundary.*`).

Receipt expiry: `valid_until = min(bundle valid_until, verified_at +
verification-policy horizon)`, never before `verified_at`. Default horizon:
604800 s (7 days). **This rule applies to REFUSED receipts too**: the same
`min()` runs with the bundle's `valid_until` participating whenever it is
parseable (an expired bundle therefore clamps the refusal receipt's
`valid_until` to `verified_at` — immediately non-current); when the bundle's
`valid_until` is absent or unparseable, the receipt's `valid_until` is
`verified_at + horizon`.

The horizon is a policy dial and MUST be bounded: v0.1 accepts
`0 <= horizon_seconds <= 315360000` (10 years). A value outside that range is
an OPERATIONAL error (CLI exit 2), never a verdict — an unbounded value
overflows date arithmetic in every implementation and means nothing as policy.

## Normative verification order

`verify_bundle` MUST run these checks in exactly this sequence and emit the
FIRST failing check's reason code (a v0.1 receipt carries exactly one):

1. **validity** → `bundle_malformed`. This step is JSON Schema **plus** the
   rules JSON Schema cannot express, all emitting the same code:
   - `claims[].claim_id` MUST be unique within the bundle. Consumers key claims
     by `claim_id`, so two entries sharing one — say a `PASS` and a `FAIL` —
     make the bundle's meaning depend on which the consumer happens to keep.
   - every timestamp MUST parse to a real instant (see "Timestamps are
     INSTANTS" above).
   - no non-interoperable numbers and no duplicate object members (see
     "Portability MUST-rejects" above).
2. hash integrity (recompute over the canonical core bytes) → `hash_mismatch`
3. key lookup by `key_id` in the keys document → `key_unknown` (fail closed)
4. issuer binding: `bundle.issuer` vs the keys document's `issuer` →
   `issuer_mismatch`
5. Ed25519 signature over the same bytes → `signature_invalid`
6. earliest-expiry-governs equality, compared as INSTANTS → `expiry_mismatch`
7. expiry (`as_of >= valid_until`) → `bundle_expired`
8. honest measurement (below) → `UNMEASURED` / `claims_unmeasured`
9. otherwise → `PASS` / `bundle_verified`

This order is a conformance requirement: implementations that check in a
different order can emit different reason codes for the same artifact and are
non-conformant even when their verdicts agree.

`verify_bundle` is **TOTAL over artifacts**: no bundle value, however
malformed, may escape as an exception — every one is a typed refusal. The only
errors it may raise are OPERATIONAL ones about VERIFIER-side inputs (an
unusable `as_of`, an out-of-range `horizon_seconds`, a missing or malformed
keys document), and those are exit 2, never exit 1.

A bundle whose stated `bundle_hash` is not in canonical surface form
(`^sha256:[0-9a-f]{64}$` — lowercase hex) is refused at step 1, and that
non-canonical value is NEVER copied into a receipt.

`verify_receipt` MUST run its checks in exactly this sequence and return the
FIRST failing check's single result-level code — the same conformance
language as the bundle order above:

1. validity → `receipt_malformed` (schema, plus real-instant timestamps and the
   portability MUST-rejects)
2. receipt-hash integrity (recompute over the canonical core bytes, with
   `receipt_hash`, `superseded`, `superseded_by` omitted) → `receipt_hash_mismatch`
3. bundle quote check, only when a bundle is presented → `bundle_mismatch`. A
   presented value that is not a JSON object cannot hash to the quoted value
   and is refused here.
4. current-state only: supersession → `receipt_superseded`
5. current-state only: expiry (`as_of >= valid_until`) → `receipt_expired`
6. otherwise → `receipt_verified`

Steps 4-5 are skipped for the historical question (`current=False`). The
default is the STRICT question (`current=True`): a caller who does not ask gets
the current-state answer. `verify_receipt` is TOTAL on the same terms as
`verify_bundle`.

## Unmeasured claim values (normative encoding)

A claim's `value` may be any JSON. A claim is **unmeasured** if and only if
its `value` is a JSON object whose `"verdict"` member equals the string
`"UNMEASURED"` or `"NOT_APPLICABLE"`. Every other value — including scalars,
arrays, objects without a `"verdict"` member, and objects whose `"verdict"` is
not a string (e.g. `{"verdict": ["UNMEASURED"]}`) — counts as measured.
Detection depends on this rule alone, never on golden shapes. When every
claim in a bundle is unmeasured, the receipt is `UNMEASURED /
claims_unmeasured` and non-verified.

## Receipt identity (normative derivation)

`receipt_id` is deterministic — no randomness in identity:

```
receipt_id = "cr_" + sha256( canonical_json({
    "bundle_hash":       <the receipt's quoted bundle_hash>,
    "verified_at":       <the receipt's verified_at>,
    "evaluator_version": <the receipt's evaluator.version>
}) )[:16]
```

Exactly those three members, canonicalized per `docs/CANONICAL_JSON.md`,
SHA-256 lowercase hex, truncated to the first 16 hex characters.

## Supersession — the never-overwrite law

Superseding NEVER mutates the old receipt's hashed core. A new verification
produces a NEW receipt; the old one is annotated `superseded: true,
superseded_by: <receipt_id>`. Because `superseded`/`superseded_by` sit outside
`receipt_hash`, the superseded receipt **remains historically verifiable**
(`claim-verify --receipt … --historical` passes) but **cannot represent
current state** (the current-state question refuses with
`receipt_superseded`).

**Supersession is UNAUTHENTICATED, and that is a direct consequence of the
design above.** The annotation sits outside the hash so that marking a receipt
superseded does not break its historical verifiability. The same property means
a holder of a superseded receipt can simply STRIP the annotation — set
`superseded: false, superseded_by: null` — and the record verifies as current
with its `receipt_hash` intact.

Therefore, normatively:

- `superseded` / `superseded_by` are an **ISSUER-SIDE ASSERTION** — a
  convenience for anyone reading a receipt the issuer handed them.
- They are **NOT a revocation mechanism**. Absence of the annotation is not
  evidence that a receipt is current.
- A consumer that needs current state MUST consult the issuer's receipt
  endpoint (`GET /receipts/{id}`, normative future) rather than trusting the
  copy in its hand.

Authenticated supersession and revocation are deferred until earned.

## Reason codes

New, claim-gate codes (extending — never replacing — the evaluator
vocabulary): `bundle_verified`, `bundle_malformed`, `hash_mismatch`,
`signature_invalid`, `key_unknown`, `issuer_mismatch`, `bundle_expired`,
`expiry_mismatch`, `claims_unmeasured`. Result-level receipt-verification codes
(returned, never stored): `receipt_verified`, `receipt_malformed`,
`receipt_hash_mismatch`, `receipt_superseded`, `receipt_expired`,
`bundle_mismatch`.

All-UNMEASURED evidence is **never** a green receipt: a bundle whose every
claim value carries an unmeasured verdict yields `UNMEASURED /
claims_unmeasured` — integrity holds, nothing is attested.

`bundle_mismatch` (result-level) triggers precisely when `verify_receipt` is
given a bundle and the receipt's quoted `bundle_hash` differs from the hash
RECOMPUTED over the presented bundle's canonical core bytes. The presented
bundle's own stated `bundle_hash` field is ignored by this check — its
integrity belongs to `verify_bundle`.

## Key discovery convention (SPEC ONLY in v0.1)

An issuer publishes its verification keys at:

```
https://<issuer>/.well-known/constitutional-cms/keys.json
```

```json
{
  "schema_version": "ClaimKeysV0_1",
  "issuer": "example.com",
  "keys": [
    {"key_id": "2026-08-a", "alg": "Ed25519", "public_key": "<base64 raw 32 bytes>"},
    {"key_id": "2026-08-b", "alg": "Ed25519", "public_key": "<base64 raw 32 bytes>"}
  ]
}
```

The document is validated against `schemas/claim_keys_v0_1.schema.json`. Its
rules are normative:

- `issuer` is REQUIRED. It is what a bundle's `issuer` is checked against (see
  "Issuer binding" above); a document without it cannot bind anything and is
  refused fail-closed.
- A key ENTRY carries **exactly** `key_id`, `alg`, `public_key`. In particular
  there is **no `status`**. v0.1 defines no semantics for a key lifecycle
  field, and shipping an inert one advertises a control that does not exist — a
  `"status": "retired"` key would go on signing fresh, long-lived bundles. An
  entry carrying any other member is refused rather than silently ignored. Key
  lifecycle beyond presence/absence is deferred until earned.
- At DOCUMENT level the members are `schema_version`, `issuer`, `keys`, and an
  OPTIONAL free-text `comment` that carries no semantics and is never
  consulted by a verifier (the shipped `tests/fixtures/claims/keys.json` uses
  it to label the TEST ONLY keys). Any other document member is refused. The
  schema is the authority on this list; this prose restates it.
- **Duplicate `key_id` is refused.** With first-match lookup, two entries
  sharing a `key_id` let document ORDER decide the verdict: an attacker who can
  append one entry flips every legitimate bundle to `signature_invalid` (placed
  first) or gets their own bundles accepted (placed last). A verifier MUST
  refuse the whole document. Like every other keys-document defect this is an
  OPERATIONAL refusal — **CLI exit 2**, no receipt emitted — never a typed
  verdict about the bundle.
- A malformed keys document is an OPERATIONAL refusal (CLI exit 2), not a
  verdict about the bundle: the keys file is the verifier's own configuration,
  not the artifact under test.

Rotation done correctly keeps every older key in the document: old bundles
verify by `key_id` forever. Removing a key revokes it (verification fails
closed) — removal is the only revocation v0.1 has. No server for this file
ships in v0.1 — the CLI reads the same shape from a local `--keys` file, fully
offline: no account, no network.

## Minimal HTTP surface — NORMATIVE FUTURE, not yet served

When a Claim Gate service exists it MUST expose exactly:

- `GET /.well-known/constitutional-cms/keys.json`
- `GET /claims/{id}` → a ClaimBundleV0_1
- `GET /receipts/{id}` → a ClaimReceiptV0_1
- `POST /verify` → body: a bundle; response: a ClaimReceiptV0_1

Nothing in this repository serves these endpoints today, and nothing may claim
to until an implementation exists with its own receipts.

## Strict-consumer contract

Verify → use, else reject. A strict consumer:

1. runs `claim-verify` (or `claims.verify_bundle`) against the issuer's keys;
2. uses the claims only on a PASS receipt that is current (not expired, not
   superseded);
3. rejects on ANY refusal — it never repairs, re-derives, or partially trusts
   a bundle, and never treats `UNMEASURED` as pass or fail.

CLI exit codes: `0` verified · `1` refused (typed reason on stderr) · `2`
operational error.

Exit `1` means a TYPED REFUSAL and nothing else. An unexpected condition exits
`2` with a single line on stderr and never a traceback, so a crash can never be
read as "the artifact was refused". Receipt-only mode that succeeds prints
`RECEIPT INTEGRITY OK (unauthenticated — supply --bundle and --keys to verify
the claim)`; only the bundle path prints `VERIFIED`.

## v0.1-frozen vs deferred-until-earned

**Frozen in v0.1:** the three schemas (bundle, receipt, keys); canonical
hashing and the portability MUST-rejects; Ed25519 signing rules; issuer
binding; instant-based timestamp comparison; earliest-expiry-governs;
fail-closed key lookup and duplicate-`key_id` refusal; the never-overwrite
supersession law; the reason-code vocabulary above; CLI exit codes; the
keys.json document shape.

**Deferred until earned:** serving the HTTP surface and `.well-known` file; a
TypeScript/JavaScript verifier (parity discipline exists in
`tests/golden-receipts/`); **authenticated (signed) receipts**;
**authenticated supersession and revocation**; **key lifecycle/`status`
semantics** (v0.1 revokes by removal only); key revocation semantics beyond
removal; Unicode normalization rules for canonicalization; per-claim evidence
narrowing (v0.1 stamps every claim with the digest of the full evidence
bundle); non-Ed25519 algorithms; network key discovery in the CLI.

## House-style rulings applied (deviations from the advisor sketch)

- `generated_at`, never `issued_at`; `valid_until`, never `expires_at`;
  RFC 3339 UTC `Z` timestamps throughout.
- `schema_version` is the const type name: `ClaimBundleV0_1`,
  `ClaimReceiptV0_1`.
- `receipt_id` matches `^cr_[a-z0-9]{6,}$` and is derived deterministically
  from `bundle_hash + verified_at + evaluator version` — no randomness in
  identity.
- `receipt_hash` omits the supersession annotations as well as itself. A pure
  self-omitted hash would make marking a receipt superseded break its own
  historical verifiability, contradicting the never-overwrite law; the hashed
  core / volatile annotation split resolves the contradiction and is tested
  (`test_e_supersession_never_mutates_the_hashed_core`).
- The v0.1 CLI is offline-only: even the optional "explicit URL" path is
  deferred until the HTTP surface exists.
