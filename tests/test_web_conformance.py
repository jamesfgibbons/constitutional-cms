import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator, FormatChecker


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "conformance_evaluator.py"
SPEC = importlib.util.spec_from_file_location("conformance_evaluator", SCRIPT)
conformance_evaluator = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(conformance_evaluator)


def load_yaml(path):
    with Path(path).open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


class WebConformanceTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = load_yaml(ROOT / "contracts/check_catalog_v1.yaml")
        cls.registry = load_yaml(ROOT / "contracts/standards_registry_v1.yaml")

    def evaluate_fixture(self, name):
        evidence = load_yaml(ROOT / f"tests/fixtures/conformance/{name}.yaml")
        return conformance_evaluator.evaluate(self.catalog, evidence)

    def test_all_pass_fixture_passes_every_check(self):
        receipt = self.evaluate_fixture("pass_all")
        self.assertTrue(all(item["verdict"] == "PASS" for item in receipt["checks"]))
        self.assertEqual(receipt["evidence_coverage"]["ratio"], 1)
        self.assertFalse(receipt["certified"])

    def test_each_profile_has_a_fail_fixture(self):
        receipt = self.evaluate_fixture("fail_each_profile")
        failing_profiles = {item["profile"] for item in receipt["checks"] if item["verdict"] == "FAIL"}
        self.assertEqual(failing_profiles, set(self.catalog["profiles"]))

    def test_missing_evidence_is_unmeasured_not_pass(self):
        receipt = self.evaluate_fixture("unmeasured")
        self.assertTrue(all(item["verdict"] == "UNMEASURED" for item in receipt["checks"]))
        self.assertEqual(receipt["evidence_coverage"]["measured"], 0)

    def test_false_applicability_is_not_applicable(self):
        receipt = self.evaluate_fixture("not_applicable")
        verdicts = {item["check_id"]: item["verdict"] for item in receipt["checks"]}
        self.assertEqual(verdicts["search.robots.indexable"], "NOT_APPLICABLE")
        self.assertEqual(verdicts["agent.webmcp.experimental"], "NOT_APPLICABLE")

    def test_experimental_authority_cannot_certify(self):
        experimental = {
            source_id
            for source_id, source in self.registry["sources"].items()
            if source["authority_class"] == "experimental"
        }
        for check in self.catalog["checks"]:
            if experimental.intersection(check["authority_refs"]):
                self.assertFalse(check["certification_eligible"], check["check_id"])

    def test_receipt_conforms_to_public_schema(self):
        schema = json.loads((ROOT / "schemas/conformance_receipt_v1.schema.json").read_text())
        receipt = self.evaluate_fixture("pass_all")
        errors = list(Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(receipt))
        self.assertEqual(errors, [])

    def test_cli_writes_json_receipt(self):
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "receipt.json"
            subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--catalog",
                    str(ROOT / "contracts/check_catalog_v1.yaml"),
                    "--evidence",
                    str(ROOT / "tests/fixtures/conformance/pass_all.yaml"),
                    "--out",
                    str(destination),
                ],
                check=True,
            )
            self.assertEqual(json.loads(destination.read_text())["schema_version"], "ConformanceReceiptV1")

    def test_catalog_has_stable_unique_ids_and_all_profiles(self):
        ids = [check["check_id"] for check in self.catalog["checks"]]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual({check["profile"] for check in self.catalog["checks"]}, set(self.catalog["profiles"]))


if __name__ == "__main__":
    unittest.main()
