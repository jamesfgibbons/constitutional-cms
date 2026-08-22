"""Test the constitutional-cms CLI."""
import contextlib
import io
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from constitutional_cms import __version__, cli, collector


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
            self.assertEqual(receipt["framework_release"], "v0.5.0")
            self.assertEqual(receipt["catalog_version"], "1.0.2")
            self.assertFalse(receipt["certified"])
            self.assertTrue(all(
                check["verdict"] == "PASS" for check in receipt["checks"]
            ), "All checks should pass for pass_all fixture")
            self.assertEqual(receipt["evidence_coverage"]["ratio"], 1.0)

    def test_audit_receipt_first_does_not_fail_closed_without_flag(self):
        result = subprocess.run(
            [
                "constitutional-cms",
                "audit",
                "--evidence",
                str(ROOT / "tests/fixtures/conformance/fail_each_profile.yaml"),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
        receipt = json.loads(result.stdout)
        self.assertTrue(any(check["verdict"] == "FAIL" for check in receipt["checks"]))

    def test_audit_fail_on_fail_exits_one_for_failing_evidence(self):
        result = subprocess.run(
            [
                "constitutional-cms",
                "audit",
                "--evidence",
                str(ROOT / "tests/fixtures/conformance/fail_each_profile.yaml"),
                "--fail-on",
                "FAIL",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 1, f"stderr: {result.stderr}")
        receipt = json.loads(result.stdout)
        self.assertTrue(any(check["verdict"] == "FAIL" for check in receipt["checks"]))

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
            ["constitutional-cms", "validate", str(ROOT / "contracts")],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
        self.assertIn("bundled catalog", result.stdout.lower())
        self.assertIn("web conformance", result.stdout.lower())
        self.assertIn("internally consistent", result.stdout.lower())

    def test_version_flag(self):
        """Verify --version reports the package version."""
        result = subprocess.run(
            ["constitutional-cms", "--version"],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn(__version__, result.stdout)
        self.assertIn("0.5.0", result.stdout)

    def test_hello_site_example_produces_receipt(self):
        result = subprocess.run(
            [
                "constitutional-cms",
                "audit",
                "--evidence",
                str(ROOT / "examples/hello-site/evidence.yaml"),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
        receipt = json.loads(result.stdout)
        self.assertEqual(receipt["framework_release"], "v0.5.0")
        self.assertTrue(all(check["verdict"] == "PASS" for check in receipt["checks"]))

    def test_validate_without_checkout_uses_bundled_release(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            previous = os.getcwd()
            os.chdir(tmpdir)
            try:
                stdout, stderr = io.StringIO(), io.StringIO()
                with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                    code = cli.main(["validate"])
            finally:
                os.chdir(previous)
        self.assertEqual(code, 0, stderr.getvalue())
        self.assertIn("v0.5.0", stdout.getvalue())
        self.assertIn("1.0.2", stdout.getvalue())


FIXTURE_HTML = (ROOT / "tests/fixtures/audit_page.html").read_text(encoding="utf-8")


def _stub_fetch(body: str, status: int = 200):
    def _fetch(url: str, timeout: float) -> collector.FetchResult:
        return collector.FetchResult(
            url=url,
            final_url=url,
            status=status,
            headers={"content-type": "text/html; charset=utf-8"},
            body=body.encode("utf-8"),
        )

    return _fetch


class AuditUrlTest(unittest.TestCase):
    """Run `audit <url>` in-process against fixture HTML — no live network."""

    def run_cli(self, argv, fetch_fn):
        stdout, stderr = io.StringIO(), io.StringIO()
        with mock.patch.object(collector, "fetch", fetch_fn):
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                code = cli.main(argv)
        return code, stdout.getvalue(), stderr.getvalue()

    def test_audit_url_human_summary_no_fail_exits_zero(self):
        code, out, _ = self.run_cli(
            ["audit", "https://audit.example/guide"], _stub_fetch(FIXTURE_HTML)
        )
        self.assertEqual(code, 0)
        self.assertIn("PASS", out)
        self.assertIn("UNMEASURED", out)
        self.assertIn("web.http.success", out)
        self.assertNotIn("score", out.lower())

    def test_audit_url_json_receipt(self):
        code, out, _ = self.run_cli(
            ["audit", "https://audit.example/guide", "--json"], _stub_fetch(FIXTURE_HTML)
        )
        self.assertEqual(code, 0)
        receipt = json.loads(out)
        self.assertEqual(receipt["schema_version"], "ConformanceReceiptV1")
        self.assertEqual(receipt["subject"]["url"], "https://audit.example/guide")
        verdicts = {check["verdict"] for check in receipt["checks"]}
        self.assertIn("UNMEASURED", verdicts)
        self.assertNotIn("FAIL", verdicts)

    def test_audit_url_http_error_is_receipt_first_by_default(self):
        code, out, _ = self.run_cli(
            ["audit", "https://audit.example/missing", "--json"],
            _stub_fetch("<html></html>", status=404),
        )
        self.assertEqual(code, 0)
        receipt = json.loads(out)
        verdicts = {check["check_id"]: check["verdict"] for check in receipt["checks"]}
        self.assertEqual(verdicts["web.http.success"], "FAIL")

    def test_fail_on_fail_exits_one_when_catalog_fails(self):
        code, out, _ = self.run_cli(
            ["audit", "https://audit.example/missing", "--json", "--fail-on", "FAIL"],
            _stub_fetch("<html></html>", status=404),
        )
        self.assertEqual(code, 1)
        receipt = json.loads(out)
        verdicts = {check["check_id"]: check["verdict"] for check in receipt["checks"]}
        self.assertEqual(verdicts["web.http.success"], "FAIL")

    def test_fail_on_rejects_unknown_verdict(self):
        code, _, err = self.run_cli(
            ["audit", "https://audit.example/guide", "--fail-on", "SCORE"],
            _stub_fetch(FIXTURE_HTML),
        )
        self.assertEqual(code, 2)
        self.assertIn("unknown --fail-on", err)

    def test_audit_url_transport_failure_exits_two(self):
        def broken_fetch(url, timeout):
            raise collector.CollectorError("Could not fetch: name or service not known")

        code, _, err = self.run_cli(["audit", "https://audit.example/guide"], broken_fetch)
        self.assertEqual(code, 2)
        self.assertIn("Could not fetch", err)

    def test_audit_requires_exactly_one_subject(self):
        code, _, err = self.run_cli(["audit"], _stub_fetch(FIXTURE_HTML))
        self.assertEqual(code, 2)
        self.assertIn("exactly one subject", err)


if __name__ == "__main__":
    unittest.main()
