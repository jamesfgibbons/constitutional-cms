#!/usr/bin/env python3
"""Regenerate the Claim Gate v0.1 golden bundles and receipts.

Deterministic given the committed TEST ONLY keys: Ed25519 signing is
deterministic, every timestamp is pinned, and canonicalization is the house
procedure. Run from the repository root:

    python scripts/generate_claim_goldens.py

The keys under tests/fixtures/claims/ are TEST ONLY. They sign public
example.com fixtures and protect nothing. Never reuse them outside tests.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from constitutional_cms import claims, evaluator  # noqa: E402

FIXTURES = ROOT / "tests" / "fixtures" / "claims"
GOLDENS = ROOT / "tests" / "golden-claims"

ISSUER = "example.com"
AS_OF = "2026-08-15T12:30:00Z"
AS_OF_LATER = "2026-08-15T13:00:00Z"
AS_OF_EXPIRED = "2026-09-20T12:00:00Z"

KEY_A = FIXTURES / "TEST_ONLY_key_a.pem"  # "old" key: rotation must keep verifying it
KEY_B = FIXTURES / "TEST_ONLY_key_b.pem"  # "new" key
KEY_C = FIXTURES / "TEST_ONLY_key_c.pem"  # stranger key: absent from keys.json


def ensure_keys() -> None:
    """Generate the TEST ONLY keypairs once; keep them stable afterwards."""
    entries = {}
    for path, key_id in ((KEY_A, "test-2026-a"), (KEY_B, "test-2026-b"), (KEY_C, "test-2026-c")):
        if not path.exists():
            entry = claims.generate_keypair(path, key_id=key_id)
            entries[key_id] = entry["public_key"]
            print(f"generated TEST ONLY key {key_id} -> {path.name}")
    if entries or not (FIXTURES / "keys.json").exists():
        # Rebuild keys.json from the private keys on disk (public halves only).
        from cryptography.hazmat.primitives import serialization
        import base64

        def public_b64(path: Path) -> str:
            key = serialization.load_pem_private_key(path.read_bytes(), password=None)
            raw = key.public_key().public_bytes(
                encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw
            )
            return base64.b64encode(raw).decode("ascii")

        keys_doc = {
            "schema_version": "ClaimKeysV0_1",
            "issuer": ISSUER,
            "comment": "TEST ONLY keys for constitutional-cms fixtures. They protect nothing.",
            "keys": [
                {"key_id": "test-2026-a", "alg": "Ed25519", "public_key": public_b64(KEY_A), "status": "retired"},
                {"key_id": "test-2026-b", "alg": "Ed25519", "public_key": public_b64(KEY_B), "status": "active"},
            ],
        }
        write(FIXTURES / "keys.json", keys_doc)


def write(path: Path, document: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {path.relative_to(ROOT)}")


def main() -> int:
    ensure_keys()
    keys_path = FIXTURES / "keys.json"

    pass_evidence = evaluator.load_data(ROOT / "tests/fixtures/conformance/pass_all.yaml")
    unmeasured_evidence = evaluator.load_data(ROOT / "tests/fixtures/conformance/unmeasured.yaml")

    # 1. verified — signed by the RETIRED key a: key rotation done correctly
    #    means historical bundles keep verifying by key_id.
    core = claims.build_bundle(pass_evidence, issuer=ISSUER)
    verified_bundle = claims.sign_bundle(core, key_id="test-2026-a", key_path=KEY_A)
    write(GOLDENS / "verified.bundle.json", verified_bundle)
    verified = claims.verify_bundle(verified_bundle, str(keys_path), as_of=AS_OF)
    assert verified.ok, verified
    write(GOLDENS / "verified.receipt.json", verified.receipt)

    # 2. tampered — one changed byte in a frozen claim value.
    tampered_bundle = json.loads(json.dumps(verified_bundle))
    tampered_bundle["claims"][0]["value"]["verdict"] = "FAIL"
    write(GOLDENS / "tampered.bundle.json", tampered_bundle)
    tampered = claims.verify_bundle(tampered_bundle, str(keys_path), as_of=AS_OF)
    assert tampered.reason_codes == ["hash_mismatch"], tampered
    write(GOLDENS / "tampered.receipt.json", tampered.receipt)

    # 3. expired — same honest bundle, verified after its valid_until.
    expired = claims.verify_bundle(verified_bundle, str(keys_path), as_of=AS_OF_EXPIRED)
    assert expired.reason_codes == ["bundle_expired"], expired
    write(GOLDENS / "expired.bundle.json", verified_bundle)
    write(GOLDENS / "expired.receipt.json", expired.receipt)

    # 3b. expiry boundary — inclusive: as_of EXACTLY valid_until is expired.
    boundary = claims.verify_bundle(
        verified_bundle, str(keys_path), as_of=verified_bundle["valid_until"]
    )
    assert boundary.reason_codes == ["bundle_expired"], boundary
    write(GOLDENS / "expired_boundary.bundle.json", verified_bundle)
    write(GOLDENS / "expired_boundary.receipt.json", boundary.receipt)

    # 4. unmeasured — all-UNMEASURED evidence is NEVER a green receipt.
    unmeasured_core = claims.build_bundle(unmeasured_evidence, issuer=ISSUER)
    unmeasured_bundle = claims.sign_bundle(unmeasured_core, key_id="test-2026-b", key_path=KEY_B)
    write(GOLDENS / "unmeasured.bundle.json", unmeasured_bundle)
    unmeasured = claims.verify_bundle(unmeasured_bundle, str(keys_path), as_of=AS_OF)
    assert unmeasured.verdict == "UNMEASURED" and not unmeasured.ok, unmeasured
    write(GOLDENS / "unmeasured.receipt.json", unmeasured.receipt)

    # 5. unknown key — signed by a key absent from keys.json: fail CLOSED.
    unknown_bundle = claims.sign_bundle(core, key_id="test-2026-c", key_path=KEY_C)
    write(GOLDENS / "unknown_key.bundle.json", unknown_bundle)
    unknown = claims.verify_bundle(unknown_bundle, str(keys_path), as_of=AS_OF)
    assert unknown.reason_codes == ["key_unknown"], unknown
    write(GOLDENS / "unknown_key.receipt.json", unknown.receipt)

    # 6. superseded — a later verification supersedes the first. The old
    #    receipt's hashed core is untouched (never-overwrite law).
    superseding = claims.verify_bundle(verified_bundle, str(keys_path), as_of=AS_OF_LATER)
    assert superseding.ok, superseding
    write(GOLDENS / "superseding.receipt.json", superseding.receipt)
    superseded = claims.supersede_receipt(verified.receipt, superseding.receipt["receipt_id"])
    write(GOLDENS / "superseded.receipt.json", superseded)

    # 7. expiry mismatch — correctly signed, but bundle valid_until is later
    #    than the earliest claim valid_until: refused as malformed policy.
    mismatch_core = json.loads(json.dumps(core))
    mismatch_core["valid_until"] = "2026-09-30T12:00:00Z"
    mismatch_bundle = claims.sign_bundle(mismatch_core, key_id="test-2026-b", key_path=KEY_B)
    write(GOLDENS / "expiry_mismatch.bundle.json", mismatch_bundle)
    mismatch = claims.verify_bundle(mismatch_bundle, str(keys_path), as_of=AS_OF)
    assert mismatch.reason_codes == ["expiry_mismatch"], mismatch
    write(GOLDENS / "expiry_mismatch.receipt.json", mismatch.receipt)

    print("claim goldens regenerated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
