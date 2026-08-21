"""Test the constitutional-cms CLI."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class CLITest(unittest.TestCase):
    """Test the constitutional-cms command-line interface."""

    def test_cli_is_installed(self):
        """Verify the constitutional-cms command is available."""
        result = subprocess.run(
            ["constitutional-cms", "--help"],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("Constitutional CMS", result.stdout)
        self.assertIn("audit", result.stdout)
        self.assertIn("validate", result.stdout)

    def test_audit_produces_receipt_for_pass_all_fixture(self):
        """Verify audit command produces a valid receipt."""
        with tempfile.TemporaryDirectory() as tmpdir:
            receipt_path = Path(tmpdir) / "receipt.json"
            result = subprocess.run(
                [
                    "constitutional-cms",
                    "audit",
                    "--evidence",
                    str(ROOT / "tests/fixtures/conformance/pass_all.yaml"),
                    "--out",
                    str(receipt_path),
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
            self.assertTrue(receipt_path.exists(), "Receipt file was not created")
            
            receipt = json.loads(receipt_path.read_text())
            self.assertEqual(receipt["schema_version"], "ConformanceReceiptV1")
            self.assertEqual(receipt["framework_release"], "v0.4.1")
            self.assertEqual(receipt["catalog_version"], "1.0.1")
            self.assertTrue(all(
                check["verdict"] == "PASS" for check in receipt["checks"]
            ), "All checks should pass for pass_all fixture")
            self.assertEqual(receipt["evidence_coverage"]["ratio"], 1.0)

    def test_audit_respects_as_of_parameter(self):
        """Verify audit --as-of parameter is used in receipt."""
        result = subprocess.run(
            [
                "constitutional-cms",
                "audit",
                "--evidence",
                str(ROOT / "tests/fixtures/conformance/pass_all.yaml"),
                "--as-of",
                "2026-08-15T12:30:00Z",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
        receipt = json.loads(result.stdout)
        self.assertEqual(receipt["evaluated_at"], "2026-08-15T12:30:00Z")

    def test_audit_prints_to_stdout_without_out_parameter(self):
        """Verify audit command prints to stdout when --out is not specified."""
        result = subprocess.run(
            [
                "constitutional-cms",
                "audit",
                "--evidence",
                str(ROOT / "tests/fixtures/conformance/pass_all.yaml"),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
        self.assertIn('"schema_version": "ConformanceReceiptV1"', result.stdout)
        receipt = json.loads(result.stdout)
        self.assertEqual(receipt["schema_version"], "ConformanceReceiptV1")

    def test_audit_supports_custom_catalog(self):
        """Verify audit command accepts --catalog parameter."""
        result = subprocess.run(
            [
                "constitutional-cms",
                "audit",
                "--catalog",
                str(ROOT / "contracts/check_catalog_v1.yaml"),
                "--evidence",
                str(ROOT / "tests/fixtures/conformance/pass_all.yaml"),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
        receipt = json.loads(result.stdout)
        self.assertEqual(receipt["schema_version"], "ConformanceReceiptV1")

    def test_validate_command_runs_contract_validation(self):
        """Verify validate command runs successfully."""
        result = subprocess.run(
            ["constitutional-cms", "validate"],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
        self.assertIn("contract validation", result.stdout.lower())
        self.assertIn("conformance", result.stdout.lower())


if __name__ == "__main__":
    unittest.main()
