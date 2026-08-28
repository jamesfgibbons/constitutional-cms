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
from datetime import timedelta
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

    def test_c2_expiry_boundary_is_inclusive_at_valid_until(self):
        """Normative inclusivity (docs/CLAIM_GATE.md): expired when
        as_of >= valid_until; one second earlier still verifies."""
        boundary = self.verified_bundle["valid_until"]
        at_boundary = claims.verify_bundle(self.verified_bundle, KEYS, as_of=boundary)
        self.assertFalse(at_boundary.ok)
        self.assertEqual(at_boundary.reason_codes, ["bundle_expired"])
        just_before = boundary.replace("T12:00:00Z", "T11:59:59Z")
        self.assertNotEqual(just_before, boundary)
        before = claims.verify_bundle(self.verified_bundle, KEYS, as_of=just_before)
        self.assertTrue(before.ok, before.detail)

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
        self.assertEqual(
            [k["key_id"] for k in keys_doc["keys"]], ["test-2026-a", "test-2026-b"]
        )
        # verified.bundle.json is signed by the OLDER key_id test-2026-a; the
        # rotation keeps it in the document, so the old bundle keeps verifying.
        self.assertEqual(self.verified_bundle["signature"]["key_id"], "test-2026-a")
        result = claims.verify_bundle(self.verified_bundle, KEYS, as_of=AS_OF)
        self.assertTrue(result.ok, result.detail)

    def test_h2_keys_entries_advertise_no_inert_status_control(self):
        """v0.1 defines no key `status` semantics. A document carrying one is
        refused rather than silently ignored: shipping an inert field would
        advertise a revocation control that does not exist (a retired key would
        keep signing fresh long-lived bundles). Removal is documented in
        docs/CLAIM_GATE.md under deferred-until-earned."""
        keys_doc = load_json(KEYS)
        for entry in keys_doc["keys"]:
            self.assertEqual(set(entry), {"key_id", "alg", "public_key"})
        with_status = copy.deepcopy(keys_doc)
        with_status["keys"][0]["status"] = "retired"
        with self.assertRaises(claims.ClaimGateError):
            claims.verify_bundle(self.verified_bundle, with_status, as_of=AS_OF)

    def test_i_golden_bundles_and_receipts_are_byte_stable(self):
        cases = [
            ("verified", AS_OF),
            ("tampered", AS_OF),
            ("expired", "2026-09-20T12:00:00Z"),
            ("expired_boundary", "2026-08-16T12:00:00Z"),
            ("unmeasured", AS_OF),
            ("unknown_key", AS_OF),
            ("expiry_mismatch", AS_OF),
            ("issuer_mismatch", AS_OF),
            ("signature_invalid", AS_OF),
            ("bundle_malformed", AS_OF),
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

    def test_goldens_pin_every_bundle_reason_code(self):
        """An independent implementer must be able to pin each refusal path
        against shipped bytes rather than inventing a fixture."""
        pinned = set()
        for path in sorted(GOLDENS.glob("*.receipt.json")):
            pinned.update(load_json(path)["reason_codes"])
        self.assertEqual(claims.CLAIM_REASON_CODES - pinned, set())

    def test_result_level_receipt_golden_refuses(self):
        """receipt_hash_mismatch.receipt.json is the tampered artifact itself:
        verify_receipt mints no receipt for a refusal, so the golden is the
        input, and the shipped bytes pin the refusal."""
        forged = load_json(GOLDENS / "receipt_hash_mismatch.receipt.json")
        result = claims.verify_receipt(forged, as_of=AS_OF)
        self.assertFalse(result.ok)
        self.assertEqual(result.reason_codes, ["receipt_hash_mismatch"])

    def test_gap9_equivalent_as_of_spellings_produce_byte_identical_receipts(self):
        """Computed timestamps have ONE spelling: the same instant spelled any
        accepted way yields identical verified_at, receipt_id, and receipt_hash."""
        bundle = load_json(GOLDENS / "verified.bundle.json")
        spellings = [
            "2026-08-15T12:30:00Z",
            "2026-08-15T12:30:00.0Z",
            "2026-08-15T12:30:00.000Z",
            "2026-08-15T12:30:00.000000Z",
            "2026-08-15T08:30:00-04:00",
        ]
        receipts = [
            json.dumps(claims.verify_bundle(bundle, KEYS, as_of=s).receipt, sort_keys=True)
            for s in spellings
        ]
        self.assertEqual(len(set(receipts)), 1, receipts)
        first = json.loads(receipts[0])
        self.assertEqual(first["verified_at"], "2026-08-15T12:30:00Z")
        # A non-zero fraction is emitted with exactly six digits.
        fractional = claims.verify_bundle(bundle, KEYS, as_of="2026-08-15T12:30:00.5Z").receipt
        self.assertEqual(fractional["verified_at"], "2026-08-15T12:30:00.500000Z")

    def test_round4_as_of_finer_than_microsecond_is_refused_not_truncated(self):
        """as_of over-precision is an OPERATIONAL refusal (exit 2), never a
        silent truncation or a rounding: each choice would mint a different
        verified_at from the same instant."""
        for over_precise in (
            "2026-08-15T12:30:00.1234567Z",   # truncation would give .123456Z
            "2026-08-15T12:30:00.0000006Z",   # truncation → …00Z, rounding → .000001Z
        ):
            with self.subTest(as_of=over_precise):
                with self.assertRaises(claims.ClaimGateError):
                    claims.verify_bundle(self.verified_bundle, KEYS, as_of=over_precise)
        # Verifier input, not an artifact: exit 2, and no receipt on stdout.
        result = subprocess.run(
            [
                sys.executable, "-m", "constitutional_cms.cli", "claim-verify",
                "--bundle", str(GOLDENS / "verified.bundle.json"),
                "--keys", str(KEYS),
                "--as-of", "2026-08-15T12:30:00.1234567Z",
            ],
            capture_output=True, text=True, cwd=str(ROOT),
        )
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertNotIn("receipt_id", result.stdout)

    def test_round4_pinned_as_of_precision_rule_is_deterministic(self):
        """The pinned rule (refuse) leaves exactly one verified_at reachable
        per instant: six digits verify and round-trip, the seventh cannot
        produce a receipt at all, so no two conformant verifiers can disagree."""
        accepted = claims.verify_bundle(
            self.verified_bundle, KEYS, as_of="2026-08-15T12:30:00.123456Z"
        ).receipt
        self.assertEqual(accepted["verified_at"], "2026-08-15T12:30:00.123456Z")
        again = claims.verify_bundle(
            self.verified_bundle, KEYS, as_of="2026-08-15T12:30:00.123456Z"
        ).receipt
        self.assertEqual(accepted, again)
        # No spelling of a finer instant can reach a receipt, so neither a
        # truncating nor a rounding implementation is conformant.
        for finer in ("2026-08-15T12:30:00.1234560Z", "2026-08-15T12:30:00.1234561Z"):
            with self.assertRaises(claims.ClaimGateError):
                claims.verify_bundle(self.verified_bundle, KEYS, as_of=finer)

    def test_seventh_fractional_digit_is_refused_not_truncated(self):
        """Bounding the grammar to six digits is what makes exact comparison
        implementable in any language."""
        self.assertIsNone(claims.parse_instant("2026-08-15T12:30:00.0000001Z"))
        self.assertIsNone(claims.instant_key("2026-08-15T12:30:00.0000001Z"))
        bundle = copy.deepcopy(self.verified_bundle)
        bundle["generated_at"] = "2026-08-15T12:00:00.0000001Z"
        result = claims.verify_bundle(bundle, KEYS, as_of=AS_OF)
        self.assertFalse(result.ok)
        self.assertEqual(result.reason_codes, ["bundle_malformed"])

    def test_keys_document_comment_is_permitted_and_never_consulted(self):
        """Prose and schema agree: an optional free-text comment is allowed at
        document level and carries no semantics."""
        keys_doc = load_json(KEYS)
        self.assertIn("comment", keys_doc)
        stripped = {k: v for k, v in keys_doc.items() if k != "comment"}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "keys.json"
            path.write_text(json.dumps(stripped), encoding="utf-8")
            without = claims.verify_bundle(self.verified_bundle, str(path), as_of=AS_OF)
        with_comment = claims.verify_bundle(self.verified_bundle, KEYS, as_of=AS_OF)
        self.assertTrue(without.ok, without.detail)
        self.assertEqual(without.receipt, with_comment.receipt)

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
        """bundle_mismatch trigger is the RECOMPUTED hash of the presented
        bundle's core bytes, not its stated bundle_hash field."""
        other = load_json(GOLDENS / "unmeasured.bundle.json")
        result = claims.verify_receipt(self.verified_receipt, other, as_of=AS_OF)
        self.assertFalse(result.ok)
        self.assertEqual(result.reason_codes, ["bundle_mismatch"])
        # Tampering only the STATED bundle_hash does not trip the quote check
        # (that field's integrity belongs to verify_bundle).
        stated_tamper = copy.deepcopy(self.verified_bundle)
        stated_tamper["bundle_hash"] = "sha256:" + "0" * 64
        result = claims.verify_receipt(self.verified_receipt, stated_tamper, as_of=AS_OF)
        self.assertTrue(result.ok, result.detail)


@needs_crypto
class AdversarialRoundOneTest(unittest.TestCase):
    """Round-1 adversarial review: every clause here failed against the code as
    reviewed. Each test names the exploit it closes."""

    @classmethod
    def setUpClass(cls):
        cls.verified_bundle = load_json(GOLDENS / "verified.bundle.json")
        cls.verified_receipt = load_json(GOLDENS / "verified.receipt.json")
        cls.keys_doc = load_json(KEYS)

    @staticmethod
    def resign(bundle: dict, key_id: str = "test-2026-b", key_name: str = "TEST_ONLY_key_b.pem") -> dict:
        """Re-freeze a mutated core the way an ATTACKER would.

        Deliberately raw Ed25519 with no house guardrails: an attacker signs
        with a crypto library, not with our producer. Every specimen below is
        therefore correctly hashed and correctly signed, so INTEGRITY can never
        shield the policy defect under test.
        """
        from cryptography.hazmat.primitives import serialization

        core = {k: v for k, v in bundle.items() if k not in ("bundle_hash", "signature")}
        payload = claims.bundle_signing_bytes(core)
        private = serialization.load_pem_private_key(
            (FIXTURES / key_name).read_bytes(), password=None
        )
        signed = dict(core)
        signed["bundle_hash"] = "sha256:" + hashlib.sha256(payload).hexdigest()
        signed["signature"] = {
            "alg": "Ed25519",
            "key_id": key_id,
            "sig": base64.b64encode(private.sign(payload)).decode("ascii"),
        }
        return signed

    def test_sign_bundle_refuses_to_emit_what_no_verifier_accepts(self):
        """The producer is bound by the same structural law as the verifier —
        defence in depth, not a security control (see resign above)."""
        bundle = self.single_claim_bundle()
        duplicate = copy.deepcopy(bundle["claims"][0])
        bundle["claims"].append(duplicate)
        core = {k: v for k, v in bundle.items() if k not in ("bundle_hash", "signature")}
        with self.assertRaises(claims.ClaimGateError):
            claims.sign_bundle(core, key_id="test-2026-b", key_path=FIXTURES / "TEST_ONLY_key_b.pem")

    def single_claim_bundle(self, **overrides) -> dict:
        bundle = copy.deepcopy(self.verified_bundle)
        bundle["claims"] = bundle["claims"][:1]
        bundle["valid_until"] = bundle["claims"][0]["valid_until"]
        bundle.update(overrides)
        return bundle

    # ---- BLOCKING-1: earliest-expiry-governs compares INSTANTS, not strings --

    def test_instant_key_orders_chronologically_where_strings_do_not(self):
        """'.' (0x2E) sorts before 'Z' (0x5A), so the string minimum of these
        two is the LATER instant. The law is about instants."""
        earlier, later = "2026-08-16T12:00:00Z", "2026-08-16T12:00:00.999999Z"
        self.assertLess(later, earlier)  # lexical order is BACKWARDS here
        self.assertLess(claims.instant_key(earlier), claims.instant_key(later))
        self.assertEqual(min(earlier, later), later)
        self.assertEqual(min([earlier, later], key=claims.instant_key), earlier)

    def test_bundle_later_than_its_earliest_claim_is_refused(self):
        """Exploit: a bundle outliving its earliest claim VERIFIED, because the
        lexically smallest string was the chronologically latest instant."""
        bundle = self.single_claim_bundle()
        extra = copy.deepcopy(bundle["claims"][0])
        extra["claim_id"] = "claim:second"
        extra["valid_until"] = "2026-08-16T12:00:00.999999Z"
        bundle["claims"][0]["valid_until"] = "2026-08-16T12:00:00Z"
        bundle["claims"].append(extra)
        bundle["valid_until"] = "2026-08-16T12:00:00.999999Z"  # LATER than earliest
        result = claims.verify_bundle(self.resign(bundle), KEYS, as_of=AS_OF)
        self.assertFalse(result.ok, "a bundle may never outlive its earliest claim")
        self.assertEqual((result.verdict, result.reason_codes), ("FAIL", ["expiry_mismatch"]))

    def test_same_instant_in_a_different_lexical_form_verifies(self):
        """Exploit (the other direction): a LAW-CORRECT bundle was refused
        because '…12:00:00Z' and '…12:00:00.000Z' are the same instant spelled
        two ways."""
        bundle = self.single_claim_bundle()
        bundle["claims"][0]["valid_until"] = "2026-08-16T12:00:00.000Z"
        bundle["valid_until"] = "2026-08-16T12:00:00Z"
        result = claims.verify_bundle(self.resign(bundle), KEYS, as_of=AS_OF)
        self.assertTrue(result.ok, result.detail)

    def test_build_bundle_valid_until_is_the_earliest_instant(self):
        bundle = claims.build_bundle(load_evidence("pass_all"), issuer="example.com")
        earliest = min(c["valid_until"] for c in bundle["claims"])
        self.assertEqual(
            claims.instant_key(bundle["valid_until"]),
            claims.instant_key(min(bundle["claims"], key=lambda c: claims.instant_key(c["valid_until"]))["valid_until"]),
        )
        self.assertIsNotNone(claims.instant_key(earliest))

    # ---- BLOCKING-2: the issuer is BOUND to the keys document ---------------

    def test_cross_issuer_forgery_is_refused(self):
        """Exploit: example.com's own key signed a bundle claiming
        issuer 'victim-bank.example' and it VERIFIED against example.com's
        keys.json. A key proves possession, never identity."""
        forged = self.resign(dict(self.verified_bundle, issuer="victim-bank.example"))
        result = claims.verify_bundle(forged, KEYS, as_of=AS_OF)
        self.assertFalse(result.ok)
        self.assertEqual((result.verdict, result.reason_codes), ("FAIL", ["issuer_mismatch"]))
        self.assertEqual(result.receipt["verdict"], "FAIL")

    def test_matching_issuer_still_verifies(self):
        self.assertEqual(self.verified_bundle["issuer"], self.keys_doc["issuer"])
        result = claims.verify_bundle(self.verified_bundle, KEYS, as_of=AS_OF)
        self.assertTrue(result.ok, result.detail)

    def test_keys_document_without_an_issuer_is_refused_fail_closed(self):
        doc = copy.deepcopy(self.keys_doc)
        del doc["issuer"]
        with self.assertRaises(claims.ClaimGateError):
            claims.verify_bundle(self.verified_bundle, doc, as_of=AS_OF)

    # ---- BLOCKING-3: duplicate key_id in the keys document ------------------

    def test_duplicate_key_id_is_refused_in_either_order(self):
        """Exploit: with first-match lookup, an attacker-controlled entry sharing
        a legitimate key_id flipped the verdict by ORDER alone."""
        impostor = {
            "key_id": "test-2026-a",
            "alg": "Ed25519",
            "public_key": self.keys_doc["keys"][1]["public_key"],
        }
        for label, entries in (
            ("impostor first", [impostor] + self.keys_doc["keys"]),
            ("impostor last", self.keys_doc["keys"] + [impostor]),
        ):
            with self.subTest(order=label):
                doc = dict(self.keys_doc, keys=entries)
                with self.assertRaises(claims.ClaimGateError) as caught:
                    claims.verify_bundle(self.verified_bundle, doc, as_of=AS_OF)
                self.assertIn("duplicate key_id", str(caught.exception))

    def test_malformed_keys_entry_is_an_operational_refusal_not_a_crash(self):
        """Exploit: {"keys": ["oops"]} raised AttributeError and exited 1 — the
        documented code for a TYPED REFUSAL."""
        with self.assertRaises(claims.ClaimGateError):
            claims.verify_bundle(
                self.verified_bundle,
                {"schema_version": "ClaimKeysV0_1", "issuer": "example.com", "keys": ["oops"]},
                as_of=AS_OF,
            )

    def test_empty_keys_array_is_refused(self):
        with self.assertRaises(claims.ClaimGateError):
            claims.verify_bundle(
                self.verified_bundle,
                {"schema_version": "ClaimKeysV0_1", "issuer": "example.com", "keys": []},
                as_of=AS_OF,
            )

    # ---- BLOCKING-4: duplicate / contradictory claim_id ---------------------

    def test_duplicate_claim_id_is_bundle_malformed(self):
        """Exploit: one claim_id carrying both {"verdict":"PASS"} and
        {"verdict":"FAIL"} VERIFIED. Consumers key by claim_id and silently get
        last-wins."""
        bundle = self.single_claim_bundle()
        contradiction = copy.deepcopy(bundle["claims"][0])
        contradiction["value"] = {"verdict": "FAIL", "reason_code": "rule_falsified"}
        bundle["claims"][0]["value"] = {"verdict": "PASS", "reason_code": "rule_satisfied"}
        bundle["claims"].append(contradiction)
        result = claims.verify_bundle(self.resign(bundle), KEYS, as_of=AS_OF)
        self.assertFalse(result.ok)
        self.assertEqual((result.verdict, result.reason_codes), ("FAIL", ["bundle_malformed"]))
        self.assertIn("duplicate claim_id", result.detail)

    # ---- BLOCKING-5: verify_* are TOTAL over artifacts ----------------------

    def test_uppercase_hex_bundle_hash_is_bundle_malformed(self):
        """Exploit: an uppercase-hex quoted hash raised ValueError out of receipt
        schema validation. The spec mandates bundle_malformed."""
        bundle = dict(self.verified_bundle, bundle_hash="sha256:" + "A" * 64)
        result = claims.verify_bundle(bundle, KEYS, as_of=AS_OF)
        self.assertFalse(result.ok)
        self.assertEqual(result.reason_codes, ["bundle_malformed"])
        self.assertIsNone(result.receipt, "a non-canonical hash is never quoted into a receipt")
        # The refusal must come from the NORMATIVE schema step, not from the
        # totality safety net catching an exception the guard should have
        # prevented. Delete the guard and this assertion is what fails.
        self.assertIn("does not validate", result.detail)
        self.assertNotIn("could not be processed", result.detail)

    def test_unhashable_claim_value_counts_as_measured(self):
        """Exploit: {"verdict": ["UNMEASURED"]} raised TypeError (unhashable).
        The spec says a non-string verdict is MEASURED."""
        bundle = self.single_claim_bundle()
        bundle["claims"][0]["value"] = {"verdict": ["UNMEASURED"]}
        result = claims.verify_bundle(self.resign(bundle), KEYS, as_of=AS_OF)
        self.assertTrue(result.ok, result.detail)
        self.assertEqual(result.verdict, "PASS")

    def test_impossible_and_leap_second_timestamps_are_bundle_malformed(self):
        """Exploit: format: date-time is NOT enforced here, so the loose pattern
        admitted '2026-13-45T99:99:99Z' and the leap second
        '2026-06-30T23:59:60Z'; both then tripped a bare assert."""
        for stamp in ("2026-13-45T99:99:99Z", "2026-06-30T23:59:60Z"):
            with self.subTest(timestamp=stamp):
                bundle = self.single_claim_bundle()
                bundle["claims"][0]["valid_until"] = stamp
                bundle["valid_until"] = stamp
                result = claims.verify_bundle(self.resign(bundle), KEYS, as_of=AS_OF)
                self.assertFalse(result.ok)
                self.assertEqual(result.reason_codes, ["bundle_malformed"])

    def test_horizon_seconds_is_bounded(self):
        """Exploit: --horizon-seconds 999999999999 raised OverflowError."""
        with self.assertRaises(claims.ClaimGateError):
            claims.verify_bundle(self.verified_bundle, KEYS, as_of=AS_OF, horizon_seconds=999999999999)
        with self.assertRaises(claims.ClaimGateError):
            claims.verify_bundle(self.verified_bundle, KEYS, as_of=AS_OF, horizon_seconds=-1)
        ok = claims.verify_bundle(
            self.verified_bundle, KEYS, as_of=AS_OF,
            horizon_seconds=claims.MAX_RECEIPT_HORIZON_SECONDS,
        )
        self.assertTrue(ok.ok, ok.detail)

    def test_verify_bundle_is_total_over_arbitrary_json(self):
        for junk in ("hello", 7, [], None, True, {"claims": {"not": "a list"}}):
            with self.subTest(bundle=repr(junk)):
                result = claims.verify_bundle(junk, KEYS, as_of=AS_OF)
                self.assertFalse(result.ok)
                self.assertEqual(result.reason_codes, ["bundle_malformed"])

    def test_verify_receipt_is_total_over_arbitrary_json(self):
        for junk in ("hello", 7, [], None, {"schema_version": "ClaimReceiptV0_1"}):
            with self.subTest(receipt=repr(junk)):
                result = claims.verify_receipt(junk, as_of=AS_OF)
                self.assertFalse(result.ok)
                self.assertEqual(result.reason_codes, ["receipt_malformed"])

    def test_verify_receipt_refuses_a_non_object_bundle_without_crashing(self):
        """Exploit: --receipt <valid> --bundle <bare JSON string> raised
        AttributeError out of the CLI as exit 1."""
        result = claims.verify_receipt(self.verified_receipt, "hello", as_of=AS_OF)
        self.assertFalse(result.ok)
        self.assertEqual(result.reason_codes, ["bundle_mismatch"])

    def test_unusable_as_of_is_operational_not_a_verdict(self):
        for bad in ("not-a-time", "2026-13-45T99:99:99Z"):
            with self.subTest(as_of=bad):
                with self.assertRaises(claims.ClaimGateError):
                    claims.verify_bundle(self.verified_bundle, KEYS, as_of=bad)

    # ---- Portability MUST-rejects ------------------------------------------

    def test_duplicate_json_object_members_are_refused(self):
        """RFC 8259 leaves duplicates undefined; Python and JavaScript keep the
        LAST. A document whose meaning depends on that cannot be independently
        verified."""
        with self.assertRaises(claims.ClaimGateError):
            claims.load_json_strict('{"a": 1, "a": 2}', "test document")
        self.assertEqual(claims.load_json_strict('{"a": 1, "b": 2}', "test document"), {"a": 1, "b": 2})

    def test_non_interoperable_numbers_are_bundle_malformed(self):
        for label, value in (
            ("integral float collapses to an int", {"score": 1.0}),
            ("float", {"score": 0.5}),
            ("integer beyond the interoperable range", {"score": claims.MAX_SAFE_INTEGER + 1}),
        ):
            with self.subTest(case=label):
                bundle = self.single_claim_bundle()
                bundle["claims"][0]["value"] = value
                result = claims.verify_bundle(self.resign(bundle), KEYS, as_of=AS_OF)
                self.assertFalse(result.ok)
                self.assertEqual(result.reason_codes, ["bundle_malformed"])

    # ---- Checks a deletion experiment showed had NO failing test ------------

    def test_bundle_schema_validation_step_is_guarded(self):
        """Delete step 1 and this returns hash_mismatch instead."""
        bundle = copy.deepcopy(self.verified_bundle)
        del bundle["policy_digest"]
        result = claims.verify_bundle(bundle, KEYS, as_of=AS_OF)
        self.assertEqual(result.reason_codes, ["bundle_malformed"])

    def test_receipt_schema_validation_step_is_guarded(self):
        """Delete step 1 and this returns receipt_hash_mismatch instead."""
        receipt = dict(self.verified_receipt, verdict="MAYBE")
        result = claims.verify_receipt(receipt, as_of=AS_OF)
        self.assertEqual(result.reason_codes, ["receipt_malformed"])

    def test_receipt_expired_is_refused_for_current_state(self):
        result = claims.verify_receipt(self.verified_receipt, as_of="2026-09-20T12:00:00Z")
        self.assertFalse(result.ok)
        self.assertEqual(result.reason_codes, ["receipt_expired"])
        historical = claims.verify_receipt(
            self.verified_receipt, as_of="2026-09-20T12:00:00Z", current=False
        )
        self.assertTrue(historical.ok, historical.detail)

    def test_receipt_expiry_boundary_is_inclusive(self):
        boundary = self.verified_receipt["valid_until"]
        at_boundary = claims.verify_receipt(self.verified_receipt, as_of=boundary)
        self.assertEqual(at_boundary.reason_codes, ["receipt_expired"])
        one_second_earlier = claims._rfc3339(claims.parse_instant(boundary) - timedelta(seconds=1))
        before = claims.verify_receipt(self.verified_receipt, as_of=one_second_earlier)
        self.assertTrue(before.ok, before.detail)

    def test_verify_receipt_defaults_to_the_current_state_question(self):
        """The DEFAULT call must be the strict one: no `current=` kwarg."""
        superseded = load_json(GOLDENS / "superseded.receipt.json")
        result = claims.verify_receipt(superseded, as_of=AS_OF)
        self.assertFalse(result.ok)
        self.assertEqual(result.reason_codes, ["receipt_superseded"])

    def test_not_applicable_is_in_the_unmeasured_set(self):
        bundle = self.single_claim_bundle()
        bundle["claims"][0]["value"] = {"verdict": "NOT_APPLICABLE", "reason_code": "applicability_false"}
        result = claims.verify_bundle(self.resign(bundle), KEYS, as_of=AS_OF)
        self.assertFalse(result.ok)
        self.assertEqual((result.verdict, result.reason_codes), ("UNMEASURED", ["claims_unmeasured"]))

    # ---- The reason-code constants are LAW, not decoration ------------------

    def test_reason_code_constants_match_the_published_schema(self):
        schema = load_json(ROOT / "schemas" / "claim_receipt_v0_1.schema.json")
        enum = set(schema["properties"]["reason_codes"]["items"]["enum"])
        self.assertTrue(
            claims.CLAIM_REASON_CODES <= enum,
            f"codes the verifier can emit but the schema forbids: {sorted(claims.CLAIM_REASON_CODES - enum)}",
        )
        self.assertIn("issuer_mismatch", claims.CLAIM_REASON_CODES)

    def test_every_emitted_code_is_a_declared_code(self):
        declared = claims.CLAIM_REASON_CODES | claims.RECEIPT_RESULT_CODES
        observed = set()
        for bundle_path in sorted(GOLDENS.glob("*.bundle.json")):
            observed.update(claims.verify_bundle(load_json(bundle_path), KEYS, as_of=AS_OF).reason_codes)
        for receipt_path in sorted(GOLDENS.glob("*.receipt.json")):
            observed.update(claims.verify_receipt(load_json(receipt_path), as_of=AS_OF).reason_codes)
        self.assertTrue(observed, "no codes observed — the sweep is not exercising anything")
        self.assertTrue(observed <= declared, f"undeclared codes emitted: {sorted(observed - declared)}")


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

    def test_cli_receipt_only_mode_never_claims_VERIFIED(self):
        """A v0.1 receipt is UNAUTHENTICATED — anyone can mint a green-looking
        one. Printing "VERIFIED" for a receipt no key ever touched overclaims."""
        result = self.run_cli(
            "claim-verify", "--receipt", str(GOLDENS / "verified.receipt.json"), "--as-of", AS_OF
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("VERIFIED", result.stdout)
        self.assertIn("RECEIPT INTEGRITY OK", result.stdout)
        self.assertIn("unauthenticated", result.stdout)

    def test_cli_bundle_mode_still_says_VERIFIED(self):
        result = self.run_cli(
            "claim-verify",
            "--bundle", str(GOLDENS / "verified.bundle.json"),
            "--keys", str(KEYS),
            "--as-of", AS_OF,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("VERIFIED", result.stdout)

    def test_cli_never_exits_1_for_an_unexpected_condition(self):
        """Exit 1 is the documented code for a TYPED REFUSAL. Every case below
        crashed with a traceback and exit 1 before this change."""
        with tempfile.TemporaryDirectory() as directory:
            work = Path(directory)
            (work / "bare-string.json").write_text('"hello"', encoding="utf-8")
            (work / "bad-keys.json").write_text(
                json.dumps({"schema_version": "ClaimKeysV0_1", "issuer": "example.com", "keys": ["oops"]}),
                encoding="utf-8",
            )
            (work / "dup-member.json").write_text(
                '{"schema_version": "ClaimBundleV0_1", "issuer": "a.example", "issuer": "b.example"}',
                encoding="utf-8",
            )
            cases = {
                "malformed keys entry": (
                    "claim-verify", "--bundle", str(GOLDENS / "verified.bundle.json"),
                    "--keys", str(work / "bad-keys.json"), "--as-of", AS_OF,
                ),
                "bare JSON string presented as a bundle in receipt mode": (
                    "claim-verify", "--receipt", str(GOLDENS / "verified.receipt.json"),
                    "--bundle", str(work / "bare-string.json"), "--as-of", AS_OF,
                ),
                "unbounded horizon": (
                    "claim-verify", "--bundle", str(GOLDENS / "verified.bundle.json"),
                    "--keys", str(KEYS), "--as-of", AS_OF, "--horizon-seconds", "999999999999",
                ),
                "bare JSON string presented to claim-sign": (
                    "claim-sign", "--bundle", str(work / "bare-string.json"),
                    "--key", str(FIXTURES / "TEST_ONLY_key_b.pem"), "--key-id", "test-2026-b",
                ),
                "duplicate JSON object member": (
                    "claim-verify", "--bundle", str(work / "dup-member.json"),
                    "--keys", str(KEYS), "--as-of", AS_OF,
                ),
            }
            declared = claims.CLAIM_REASON_CODES | claims.RECEIPT_RESULT_CODES
            for label, argv in cases.items():
                with self.subTest(case=label):
                    result = self.run_cli(*argv)
                    self.assertNotIn("Traceback", result.stderr, f"{label}: traceback leaked")
                    self.assertEqual(
                        len(result.stderr.strip().splitlines()), 1,
                        f"{label}: must be exactly one line on stderr, got: {result.stderr}",
                    )
                    self.assertIn(result.returncode, (1, 2), f"{label}: {result.stderr}")
                    if result.returncode == 1:
                        # Exit 1 is permitted ONLY when a declared code is named.
                        self.assertTrue(
                            any(code in result.stderr for code in declared),
                            f"{label}: exit 1 without a typed reason code: {result.stderr}",
                        )

    def test_cli_cross_issuer_forgery_is_refused_with_a_typed_reason(self):
        with tempfile.TemporaryDirectory() as directory:
            forged_path = Path(directory) / "forged.json"
            bundle = load_json(GOLDENS / "verified.bundle.json")
            core = {k: v for k, v in bundle.items() if k not in ("bundle_hash", "signature")}
            core["issuer"] = "victim-bank.example"
            signed = claims.sign_bundle(core, key_id="test-2026-b", key_path=FIXTURES / "TEST_ONLY_key_b.pem")
            forged_path.write_text(json.dumps(signed), encoding="utf-8")
            result = self.run_cli(
                "claim-verify", "--bundle", str(forged_path), "--keys", str(KEYS), "--as-of", AS_OF
            )
            self.assertEqual(result.returncode, 1)
            self.assertIn("issuer_mismatch", result.stderr)


if __name__ == "__main__":
    unittest.main()
