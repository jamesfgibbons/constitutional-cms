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

## Expiry

**Earliest-expiry-governs, enforced by the verifier — not just prose.** The
bundle's `valid_until` MUST equal the earliest `claims[].valid_until`; a
bundle whose `valid_until` is later than any claim's is refused as malformed
(`expiry_mismatch`) even when correctly signed. An expired bundle is refused
(`bundle_expired`).

Receipt expiry: `valid_until = min(bundle valid_until, verified_at +
verification-policy horizon)`, never before `verified_at`. Default horizon:
604800 s (7 days).

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
