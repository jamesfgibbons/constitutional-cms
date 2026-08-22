# Claim Gate v0.1 — ClaimBundle + ClaimReceipt

**Status: DRAFT (pre-ratification).** v0.1 of the CLAIM objects is draft until
the founder tags a release. Five-minute read; the schemas and the constitution
tests in `tests/test_claim_gate.py` are the law when prose and code disagree.

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
receipts). A PASS receipt means: canonical bytes intact, signature valid
against the issuer's published key, expiry law satisfied, and at least one
claim carries a measured verdict.

## Canonicalization and hashing

Exactly `docs/CANONICAL_JSON.md` — the one house digest procedure, one code
path (`constitutional_cms.evaluator.canonical_json` / `digest`): keys sorted,
array order preserved, non-finite numbers rejected, integral floats emitted as
integers, separators `(",", ":")`, `ensure_ascii=False`, SHA-256 lowercase hex.

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

## Verification clock

Verification time is an explicit INPUT (`as_of`), never an implicit wall
clock. A verifier that is given no `as_of` MAY use the current UTC time, but
it MUST report the clock it used: the receipt's `verified_at` IS the `as_of`
of that verification. Two verifiers given the same bundle, keys, and `as_of`
MUST produce identical receipts.

## Expiry

**Earliest-expiry-governs, enforced by the verifier — not just prose.** The
bundle's `valid_until` MUST equal the earliest `claims[].valid_until`. ANY
inequality — later **or** earlier than the earliest claim — is refused with
the single code `expiry_mismatch`, even when correctly signed. There is no
second code for the earlier direction.

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

## Normative verification order

`verify_bundle` MUST run these checks in exactly this sequence and emit the
FIRST failing check's reason code (a v0.1 receipt carries exactly one):

1. schema validity → `bundle_malformed`
2. hash integrity (recompute over the canonical core bytes) → `hash_mismatch`
3. key lookup by `key_id` in the keys document → `key_unknown` (fail closed)
4. Ed25519 signature over the same bytes → `signature_invalid`
5. earliest-expiry-governs equality → `expiry_mismatch`
6. expiry (`as_of >= valid_until`) → `bundle_expired`
7. honest measurement (below) → `UNMEASURED` / `claims_unmeasured`
8. otherwise → `PASS` / `bundle_verified`

This order is a conformance requirement: implementations that check in a
different order can emit different reason codes for the same artifact and are
non-conformant even when their verdicts agree.

## Unmeasured claim values (normative encoding)

A claim's `value` may be any JSON. A claim is **unmeasured** if and only if
its `value` is a JSON object whose `"verdict"` member equals the string
`"UNMEASURED"` or `"NOT_APPLICABLE"`. Every other value — including scalars,
arrays, and objects without a `"verdict"` member — counts as measured.
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

## Reason codes

New, claim-gate codes (extending — never replacing — the evaluator
vocabulary): `bundle_verified`, `bundle_malformed`, `hash_mismatch`,
`signature_invalid`, `key_unknown`, `bundle_expired`, `expiry_mismatch`,
`claims_unmeasured`. Result-level receipt-verification codes (returned, never
stored): `receipt_verified`, `receipt_malformed`, `receipt_hash_mismatch`,
`receipt_superseded`, `receipt_expired`, `bundle_mismatch`.

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
    {"key_id": "2026-08-a", "alg": "Ed25519", "public_key": "<base64 raw 32 bytes>", "status": "retired"},
    {"key_id": "2026-08-b", "alg": "Ed25519", "public_key": "<base64 raw 32 bytes>", "status": "active"}
  ]
}
```

Rotation done correctly keeps every retired key in the document: old bundles
verify by `key_id` forever. Removing a key revokes it (verification fails
closed). No server for this file ships in v0.1 — the CLI reads the same shape
from a local `--keys` file, fully offline: no account, no network.

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

## v0.1-frozen vs deferred-until-earned

**Frozen in v0.1:** the two schemas; canonical hashing; Ed25519 signing rules;
earliest-expiry-governs; fail-closed key lookup; the never-overwrite
supersession law; the reason-code vocabulary above; CLI exit codes; the
keys.json document shape.

**Deferred until earned:** serving the HTTP surface and `.well-known` file; a
TypeScript/JavaScript verifier (parity discipline exists in
`tests/golden-receipts/`); key revocation semantics beyond removal; per-claim
evidence narrowing (v0.1 stamps every claim with the digest of the full
evidence bundle); non-Ed25519 algorithms; network key discovery in the CLI.

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
