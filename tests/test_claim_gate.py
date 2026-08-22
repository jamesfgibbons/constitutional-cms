"""Claim Gate v0.1 — the technical constitution.

Each named test is one clause of the constitution for ClaimBundleV0_1 and
ClaimReceiptV0_1. The functionality is new in this change, so every clause is
fixture-proven (there is no prior behavior to be red against); the goldens
under tests/golden-claims/ freeze the bytes.

Signing clauses require the optional 'claims' extra (cryptography). They skip
honestly — not pass — when it is absent; CI installs the extra so the full
constitution runs there.
"""

from __future__ import annotations

import base64
import copy
import hashlib
import json
import math
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures" / "claims"
GOLDENS = ROOT / "tests" / "golden-claims"
AS_OF = "2026-08-15T12:30:00Z"

sys.path.insert(0, str(ROOT))

from constitutional_cms import claims, evaluator  # noqa: E402

try:
    import cryptography  # noqa: F401

    HAVE_CRYPTO = True
except ImportError:
    HAVE_CRYPTO = False

needs_crypto = unittest.skipUnless(HAVE_CRYPTO, "requires the optional 'claims' extra (cryptography)")


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_evidence(name: str) -> dict:
    return evaluator.load_data(ROOT / "tests" / "fixtures" / "conformance" / f"{name}.yaml")


KEYS = FIXTURES / "keys.json"


class ClaimBundleConstructionTest(unittest.TestCase):
    def test_a_determinism_same_input_identical_canonical_bytes_and_hash_twice(self):
        first = claims.build_bundle(load_evidence("pass_all"), issuer="example.com")
        second = claims.build_bundle(load_evidence("pass_all"), issuer="example.com")
        self.assertEqual(first, second)
        self.assertEqual(claims.bundle_signing_bytes(first), claims.bundle_signing_bytes(second))
        self.assertEqual(
            hashlib.sha256(claims.bundle_signing_bytes(first)).hexdigest(),
            hashlib.sha256(claims.bundle_signing_bytes(second)).hexdigest(),
        )

    def test_bundle_valid_until_equals_earliest_claim_valid_until(self):
        bundle = claims.build_bundle(load_evidence("pass_all"), issuer="example.com")
        self.assertEqual(bundle["valid_until"], min(c["valid_until"] for c in bundle["claims"]))

    def test_unsigned_core_contains_no_volatile_fields(self):
        bundle = claims.build_bundle(load_evidence("pass_all"), issuer="example.com")
        for forbidden in ("verdict", "verified_at", "superseded", "receipt_id", "certified"):
            self.assertNotIn(forbidden, bundle)

    def test_import_guard_names_the_extra_when_cryptography_is_missing(self):
        # Run in a subprocess that hides cryptography regardless of this
        # environment, and assert the error names the install command.
        code = (
            "import sys; sys.modules['cryptography']=None; sys.modules['cryptography.hazmat']=None;\n"
            "sys.path.insert(0, %r)\n"
            "from constitutional_cms import claims\n"
            "try:\n"
            "    claims.generate_keypair('/tmp/never-written.pem')\n"
            "except Exception as exc:\n"
            "    print(str(exc))\n"
        ) % str(ROOT)
        result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
        self.assertIn("constitutional-cms[claims]", result.stdout + result.stderr)


@needs_crypto
class ClaimConstitutionTest(unittest.TestCase):
    """Clauses b through j run against the committed TEST ONLY fixtures."""

    @classmethod
    def setUpClass(cls):
        cls.verified_bundle = load_json(GOLDENS / "verified.bundle.json")
        cls.verified_receipt = load_json(GOLDENS / "verified.receipt.json")

    def test_b_one_changed_byte_fails_verification(self):
        tampered = copy.deepcopy(self.verified_bundle)
        tampered["subject"]["id"] = tampered["subject"]["id"].replace("example", "exampla")
        result = claims.verify_bundle(tampered, KEYS, as_of=AS_OF)
        self.assertFalse(result.ok)
        self.assertEqual(result.reason_codes, ["hash_mismatch"])

    def test_c_expired_bundle_refused_with_typed_reason(self):
        result = claims.verify_bundle(self.verified_bundle, KEYS, as_of="2026-09-20T12:00:00Z")
        self.assertFalse(result.ok)
        self.assertEqual((result.verdict, result.reason_codes), ("FAIL", ["bundle_expired"]))

    def test_d_unknown_signing_key_fails_closed(self):
        unknown = load_json(GOLDENS / "unknown_key.bundle.json")
        result = claims.verify_bundle(unknown, KEYS, as_of=AS_OF)
        self.assertFalse(result.ok)
        self.assertEqual((result.verdict, result.reason_codes), ("FAIL", ["key_unknown"]))

    def test_e_superseded_receipt_cannot_masquerade_as_current(self):
        superseded = load_json(GOLDENS / "superseded.receipt.json")
        current = claims.verify_receipt(superseded, as_of=AS_OF, current=True)
        self.assertFalse(current.ok)
        self.assertEqual(current.reason_codes, ["receipt_superseded"])
        historical = claims.verify_receipt(superseded, as_of=AS_OF, current=False)
        self.assertTrue(historical.ok, historical.detail)

    def test_e_supersession_never_mutates_the_hashed_core(self):
        superseded = load_json(GOLDENS / "superseded.receipt.json")
        original = copy.deepcopy(self.verified_receipt)
        self.assertEqual(superseded["receipt_hash"], original["receipt_hash"])
        self.assertEqual(
            claims.receipt_core_bytes(superseded), claims.receipt_core_bytes(original)
        )

    def test_f_all_unmeasured_evidence_is_never_a_green_receipt(self):
        bundle = load_json(GOLDENS / "unmeasured.bundle.json")
        result = claims.verify_bundle(bundle, KEYS, as_of=AS_OF)
        self.assertFalse(result.ok)
        self.assertEqual(result.verdict, "UNMEASURED")
        self.assertEqual(result.reason_codes, ["claims_unmeasured"])
        self.assertEqual(result.receipt["verdict"], "UNMEASURED")

    def test_g_independent_reproduction_from_schema_docs_and_fixture_bytes(self):
        """Re-derive hash + signature decision through a separate minimal code
        path written only from docs/CLAIM_GATE.md + docs/CANONICAL_JSON.md —
        deliberately NOT using constitutional_cms.claims or evaluator."""

        def indep_canonical(value):
            if isinstance(value, dict):
                return {k: indep_canonical(v) for k, v in value.items()}
            if isinstance(value, list):
                return [indep_canonical(v) for v in value]
            if isinstance(value, float):
                if not math.isfinite(value):
                    raise ValueError("non-finite")
                return int(value) if value.is_integer() else value
            return value

        bundle = load_json(GOLDENS / "verified.bundle.json")
        core = {k: v for k, v in bundle.items() if k not in ("bundle_hash", "signature")}
        payload = json.dumps(
            indep_canonical(core), ensure_ascii=False, sort_keys=True,
            separators=(",", ":"), allow_nan=False,
        ).encode("utf-8")
        self.assertEqual("sha256:" + hashlib.sha256(payload).hexdigest(), bundle["bundle_hash"])

        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

        keys_doc = load_json(KEYS)
        entry = next(k for k in keys_doc["keys"] if k["key_id"] == bundle["signature"]["key_id"])
        public = Ed25519PublicKey.from_public_bytes(base64.b64decode(entry["public_key"]))
        public.verify(base64.b64decode(bundle["signature"]["sig"]), payload)  # raises on failure

    def test_h_key_rotation_done_correctly_keeps_old_bundles_verifying(self):
        keys_doc = load_json(KEYS)
        statuses = {k["key_id"]: k.get("status") for k in keys_doc["keys"]}
        self.assertEqual(statuses, {"test-2026-a": "retired", "test-2026-b": "active"})
        # verified.bundle.json is signed by the RETIRED key_id test-2026-a.
        self.assertEqual(self.verified_bundle["signature"]["key_id"], "test-2026-a")
        result = claims.verify_bundle(self.verified_bundle, KEYS, as_of=AS_OF)
        self.assertTrue(result.ok, result.detail)

    def test_i_golden_bundles_and_receipts_are_byte_stable(self):
        cases = [
            ("verified", AS_OF),
            ("tampered", AS_OF),
            ("expired", "2026-09-20T12:00:00Z"),
            ("unmeasured", AS_OF),
            ("unknown_key", AS_OF),
            ("expiry_mismatch", AS_OF),
        ]
        for name, as_of in cases:
            with self.subTest(golden=name):
                bundle = load_json(GOLDENS / f"{name}.bundle.json")
                expected = (GOLDENS / f"{name}.receipt.json").read_text(encoding="utf-8")
                result = claims.verify_bundle(bundle, KEYS, as_of=as_of)
                actual = json.dumps(result.receipt, indent=2, sort_keys=True) + "\n"
                self.assertEqual(actual, expected)
        # Supersession pair: annotating the verified receipt reproduces the
        # superseded golden byte-for-byte.
        superseding = load_json(GOLDENS / "superseding.receipt.json")
        annotated = claims.supersede_receipt(self.verified_receipt, superseding["receipt_id"])
        expected = (GOLDENS / "superseded.receipt.json").read_text(encoding="utf-8")
        self.assertEqual(json.dumps(annotated, indent=2, sort_keys=True) + "\n", expected)

    def test_j_earliest_expiry_governs_is_enforced_not_prose(self):
        bundle = load_json(GOLDENS / "expiry_mismatch.bundle.json")
        # The bundle is correctly signed — integrity alone would pass.
        result = claims.verify_bundle(bundle, KEYS, as_of=AS_OF)
        self.assertFalse(result.ok)
        self.assertEqual((result.verdict, result.reason_codes), ("FAIL", ["expiry_mismatch"]))

    def test_receipts_validate_against_the_public_schema(self):
        from jsonschema import Draft202012Validator, FormatChecker

        schema = load_json(ROOT / "schemas" / "claim_receipt_v0_1.schema.json")
        validator = Draft202012Validator(schema, format_checker=FormatChecker())
        for path in sorted(GOLDENS.glob("*.receipt.json")):
            with self.subTest(receipt=path.name):
                self.assertEqual(list(validator.iter_errors(load_json(path))), [])

    def test_bundles_validate_against_the_public_schema(self):
        from jsonschema import Draft202012Validator, FormatChecker

        schema = load_json(ROOT / "schemas" / "claim_bundle_v0_1.schema.json")
        validator = Draft202012Validator(schema, format_checker=FormatChecker())
        for path in sorted(GOLDENS.glob("*.bundle.json")):
            with self.subTest(bundle=path.name):
                self.assertEqual(list(validator.iter_errors(load_json(path))), [])

    def test_signature_valid_but_value_tampered_after_signing_fails(self):
        # Tamper then RE-hash (attacker fixes the hash but cannot re-sign).
        tampered = copy.deepcopy(self.verified_bundle)
        tampered["claims"][0]["value"]["verdict"] = "FAIL"
        tampered["bundle_hash"] = "sha256:" + hashlib.sha256(
            claims.bundle_signing_bytes(tampered)
        ).hexdigest()
        result = claims.verify_bundle(tampered, KEYS, as_of=AS_OF)
        self.assertFalse(result.ok)
        self.assertEqual(result.reason_codes, ["signature_invalid"])

    def test_receipt_hash_tamper_is_detected(self):
        forged = copy.deepcopy(self.verified_receipt)
        forged["verdict"] = "FAIL"
        result = claims.verify_receipt(forged, as_of=AS_OF)
        self.assertFalse(result.ok)
        self.assertEqual(result.reason_codes, ["receipt_hash_mismatch"])

    def test_verify_receipt_refuses_a_mismatched_bundle(self):
        other = load_json(GOLDENS / "unmeasured.bundle.json")
        result = claims.verify_receipt(self.verified_receipt, other, as_of=AS_OF)
        self.assertFalse(result.ok)
        self.assertEqual(result.reason_codes, ["bundle_mismatch"])


@needs_crypto
class ClaimCliTest(unittest.TestCase):
    """claim-bundle → claim-sign → claim-verify, fully offline, typed exits."""

    def run_cli(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, "-m", "constitutional_cms.cli", *args],
            capture_output=True,
            text=True,
            cwd=str(ROOT),
        )

    def test_cli_bundle_sign_verify_roundtrip_offline(self):
        with tempfile.TemporaryDirectory() as directory:
            core_path = Path(directory) / "core.json"
            signed_path = Path(directory) / "signed.json"
            receipt_path = Path(directory) / "receipt.json"

            built = self.run_cli(
                "claim-bundle",
                "--evidence", str(ROOT / "tests/fixtures/conformance/pass_all.yaml"),
                "--issuer", "example.com",
                "--out", str(core_path),
            )
            self.assertEqual(built.returncode, 0, built.stderr)

            signed = self.run_cli(
                "claim-sign",
                "--bundle", str(core_path),
                "--key", str(FIXTURES / "TEST_ONLY_key_b.pem"),
                "--key-id", "test-2026-b",
                "--out", str(signed_path),
            )
            self.assertEqual(signed.returncode, 0, signed.stderr)
            # Key material never appears in CLI output.
            self.assertNotIn("PRIVATE KEY", signed.stdout + signed.stderr)

            verified = self.run_cli(
                "claim-verify",
                "--bundle", str(signed_path),
                "--keys", str(KEYS),
                "--as-of", AS_OF,
                "--receipt-out", str(receipt_path),
            )
            self.assertEqual(verified.returncode, 0, verified.stderr)
            receipt = load_json(receipt_path)
            self.assertEqual(receipt["verdict"], "PASS")

    def test_cli_refusal_exits_1_with_typed_reason(self):
        result = self.run_cli(
            "claim-verify",
            "--bundle", str(GOLDENS / "tampered.bundle.json"),
            "--keys", str(KEYS),
            "--as-of", AS_OF,
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("hash_mismatch", result.stderr)

    def test_cli_operational_error_exits_2(self):
        result = self.run_cli(
            "claim-verify",
            "--bundle", str(GOLDENS / "verified.bundle.json"),
            "--keys", "/nonexistent/keys.json",
        )
        self.assertEqual(result.returncode, 2)

    def test_cli_receipt_mode_refuses_superseded_as_current(self):
        result = self.run_cli(
            "claim-verify",
            "--receipt", str(GOLDENS / "superseded.receipt.json"),
            "--as-of", AS_OF,
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("receipt_superseded", result.stderr)
        historical = self.run_cli(
            "claim-verify",
            "--receipt", str(GOLDENS / "superseded.receipt.json"),
            "--as-of", AS_OF,
            "--historical",
        )
        self.assertEqual(historical.returncode, 0, historical.stderr)


if __name__ == "__main__":
    unittest.main()
