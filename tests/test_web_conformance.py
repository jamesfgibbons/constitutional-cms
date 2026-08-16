import copy
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


def set_path(document, dotted_path, value):
    current = document
    parts = dotted_path.split(".")
    for part in parts[:-1]:
        current = current.setdefault(part, {})
    current[parts[-1]] = value


def delete_path(document, dotted_path):
    current = document
    parts = dotted_path.split(".")
    for part in parts[:-1]:
        current = current[part]
    current.pop(parts[-1], None)


class WebConformanceTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = load_yaml(ROOT / "contracts/check_catalog_v1.yaml")
        cls.registry = load_yaml(ROOT / "contracts/standards_registry_v1.yaml")
        cls.pass_evidence = load_yaml(ROOT / "tests/fixtures/conformance/pass_all.yaml")

    def evaluate_fixture(self, name, as_of=None):
        evidence = load_yaml(ROOT / f"tests/fixtures/conformance/{name}.yaml")
        return conformance_evaluator.evaluate(self.catalog, evidence, as_of)

    def verdict_for(self, receipt, check_id):
        return next(item for item in receipt["checks"] if item["check_id"] == check_id)

    def check_for(self, check_id):
        return next(check for check in self.catalog["checks"] if check["check_id"] == check_id)

    def falsify(self, evidence, rule):
        if rule["operator"] == "all":
            return self.falsify(evidence, rule["rules"][0])
        path = rule["path"]
        operator = rule["operator"]
        if operator == "equals":
            expected = rule.get("expected")
            value = not expected if isinstance(expected, bool) else expected + 1 if isinstance(expected, (int, float)) else "different"
        elif operator == "nonempty":
            value = ""
        elif operator == "between":
            value = rule["max"] + 1
        elif operator == "lte":
            value = rule["expected"] + 1
        elif operator == "gte":
            value = rule["expected"] - 1
        elif operator == "https_url":
            value = "/relative"
        elif operator == "link_graph_eligible":
            value = copy.deepcopy(conformance_evaluator.value_at(evidence, path))
            value["source"]["outbound_eligible"] = False
        else:
            self.fail(f"No falsifier for {operator}")
        set_path(evidence, path, value)

    def test_all_pass_fixture_passes_every_check(self):
        receipt = self.evaluate_fixture("pass_all")
        self.assertTrue(all(item["verdict"] == "PASS" for item in receipt["checks"]))
        self.assertTrue(all(item["reason_code"] == "rule_satisfied" for item in receipt["checks"]))
        self.assertEqual(receipt["evidence_coverage"]["ratio"], 1)
        self.assertFalse(receipt["certified"])

    def test_every_check_has_pass_fail_and_unmeasured_state_proofs(self):
        for check in self.catalog["checks"]:
            with self.subTest(check=check["check_id"], state="FAIL"):
                evidence = copy.deepcopy(self.pass_evidence)
                self.falsify(evidence, check["evaluation"])
                item = self.verdict_for(conformance_evaluator.evaluate(self.catalog, evidence), check["check_id"])
                self.assertEqual((item["verdict"], item["reason_code"]), ("FAIL", "rule_falsified"))

            path = next(path for path in check["required_evidence"] if path.startswith("observations."))
            for state, reason in (
                ("missing", "evidence_missing"),
                ("stale", "evidence_stale"),
                ("invalid", "evidence_invalid"),
                ("unavailable", "source_unavailable"),
            ):
                with self.subTest(check=check["check_id"], state=state):
                    evidence = copy.deepcopy(self.pass_evidence)
                    if state == "missing":
                        delete_path(evidence, path)
                    else:
                        evidence.setdefault("evidence_states", {})[path] = {"status": state}
                    item = self.verdict_for(conformance_evaluator.evaluate(self.catalog, evidence), check["check_id"])
                    self.assertEqual((item["verdict"], item["reason_code"]), ("UNMEASURED", reason))

    def test_wrong_typed_evidence_is_unmeasured_not_fail(self):
        for check in self.catalog["checks"]:
            path = next(path for path in check["required_evidence"] if path.startswith("observations."))
            evidence = copy.deepcopy(self.pass_evidence)
            set_path(evidence, path, None)
            item = self.verdict_for(conformance_evaluator.evaluate(self.catalog, evidence), check["check_id"])
            self.assertEqual((item["verdict"], item["reason_code"]), ("UNMEASURED", "evidence_invalid"))

    def test_false_applicability_precedes_missing_check_evidence(self):
        receipt = self.evaluate_fixture("not_applicable")
        for check_id in ("search.robots.indexable", "agent.webmcp.experimental"):
            item = self.verdict_for(receipt, check_id)
            self.assertEqual((item["verdict"], item["reason_code"]), ("NOT_APPLICABLE", "applicability_false"))

    def test_indeterminate_applicability_is_unmeasured(self):
        check_id = "agent.webmcp.experimental"
        for state, reason in (
            ("missing", "evidence_missing"),
            ("stale", "evidence_stale"),
            ("invalid", "evidence_invalid"),
            ("unavailable", "source_unavailable"),
        ):
            evidence = copy.deepcopy(self.pass_evidence)
            path = "observations.agent.webmcp_declared"
            if state == "missing":
                delete_path(evidence, path)
            else:
                evidence.setdefault("evidence_states", {})[path] = {"status": state}
            item = self.verdict_for(conformance_evaluator.evaluate(self.catalog, evidence), check_id)
            self.assertEqual((item["verdict"], item["reason_code"]), ("UNMEASURED", reason))

    def test_public_unmeasured_reason_fixtures(self):
        expected = {
            "unmeasured": "evidence_missing",
            "stale": "evidence_stale",
            "invalid": "evidence_invalid",
            "unavailable": "source_unavailable",
        }
        for fixture, reason in expected.items():
            with self.subTest(fixture=fixture):
                item = self.verdict_for(self.evaluate_fixture(fixture), "web.http.success")
                self.assertEqual((item["verdict"], item["reason_code"]), ("UNMEASURED", reason))

    def test_explicit_max_age_and_future_evidence(self):
        check_id = "web.http.success"
        path = "observations.http.status"
        stale = copy.deepcopy(self.pass_evidence)
        stale["evidence_states"] = {path: {"status": "observed", "observed_at": "2026-08-13T12:00:00Z"}}
        item = self.verdict_for(conformance_evaluator.evaluate(self.catalog, stale), check_id)
        self.assertEqual((item["verdict"], item["reason_code"]), ("UNMEASURED", "evidence_stale"))

        future = copy.deepcopy(self.pass_evidence)
        future["evidence_states"] = {path: {"status": "observed", "observed_at": "2026-08-16T12:00:00Z"}}
        item = self.verdict_for(conformance_evaluator.evaluate(self.catalog, future), check_id)
        self.assertEqual((item["verdict"], item["reason_code"]), ("UNMEASURED", "evidence_invalid"))

    def test_link_boundary_validates_authority_and_eligibility(self):
        check_id = "search.links.targets_eligible"
        cases = []

        source_ineligible = copy.deepcopy(self.pass_evidence)
        source_ineligible["observations"]["links"]["source"]["outbound_eligible"] = False
        cases.append(("source outbound", source_ineligible, "FAIL", "rule_falsified"))

        target_ineligible = copy.deepcopy(self.pass_evidence)
        target_ineligible["observations"]["links"]["targets"][0]["inbound_eligible"] = False
        cases.append(("target inbound", target_ineligible, "FAIL", "rule_falsified"))

        cross_origin = copy.deepcopy(self.pass_evidence)
        cross_origin["observations"]["links"]["targets"][0]["canonical_url"] = "https://other.example/docs"
        cases.append(("cross origin", cross_origin, "UNMEASURED", "evidence_invalid"))

        identical_duplicate = copy.deepcopy(self.pass_evidence)
        identical_duplicate["observations"]["links"]["targets"].append(
            copy.deepcopy(identical_duplicate["observations"]["links"]["targets"][0])
        )
        cases.append(("identical duplicate", identical_duplicate, "PASS", "rule_satisfied"))

        conflicting_duplicate = copy.deepcopy(identical_duplicate)
        conflicting_duplicate["observations"]["links"]["targets"][1]["page_family"] = "other"
        cases.append(("conflicting duplicate", conflicting_duplicate, "UNMEASURED", "evidence_invalid"))

        empty = copy.deepcopy(self.pass_evidence)
        empty["observations"]["links"]["targets"] = []
        cases.append(("empty corpus", empty, "UNMEASURED", "evidence_invalid"))

        stale = copy.deepcopy(self.pass_evidence)
        stale["observations"]["links"]["targets"][0]["observed_at"] = "2026-08-13T12:00:00Z"
        cases.append(("stale authority", stale, "UNMEASURED", "evidence_stale"))

        valid_redirect = copy.deepcopy(self.pass_evidence)
        valid_redirect["observations"]["links"]["targets"][0]["redirect_chain"] = [
            "https://example.com/old-docs", "https://example.com/docs"
        ]
        cases.append(("valid redirect", valid_redirect, "PASS", "rule_satisfied"))

        invalid_redirect = copy.deepcopy(valid_redirect)
        invalid_redirect["observations"]["links"]["targets"][0]["redirect_chain"][-1] = "https://example.com/wrong"
        cases.append(("invalid redirect", invalid_redirect, "UNMEASURED", "evidence_invalid"))

        unavailable = copy.deepcopy(self.pass_evidence)
        unavailable["evidence_states"] = {"observations.links": {"status": "unavailable"}}
        delete_path(unavailable, "observations.links")
        cases.append(("adapter unavailable", unavailable, "UNMEASURED", "source_unavailable"))

        for label, evidence, verdict, reason in cases:
            with self.subTest(case=label):
                item = self.verdict_for(conformance_evaluator.evaluate(self.catalog, evidence), check_id)
                self.assertEqual((item["verdict"], item["reason_code"]), (verdict, reason))

    def test_receipt_is_deterministic_and_digest_is_verifiable(self):
        first = self.evaluate_fixture("pass_all")
        second = self.evaluate_fixture("pass_all")
        self.assertEqual(first, second)
        self.assertEqual(first["evaluated_at"], self.pass_evidence["collected_at"])
        unsigned = copy.deepcopy(first)
        claimed = unsigned.pop("result_digest")
        self.assertEqual(claimed, conformance_evaluator.digest(unsigned))

        later = self.evaluate_fixture("pass_all", "2026-08-15T13:00:00Z")
        self.assertNotEqual(first["result_digest"], later["result_digest"])
        self.assertEqual(later["evaluation_context"]["as_of"], "2026-08-15T13:00:00Z")

    def test_canonical_json_normalizes_integral_floats_for_javascript_parity(self):
        self.assertEqual(conformance_evaluator.canonical_json({"ratio": 1.0, "threshold": 0.1}), '{"ratio":1,"threshold":0.1}')

    def test_python_evaluator_matches_public_golden_receipts(self):
        for path in sorted((ROOT / "tests/golden-receipts").glob("*.json")):
            with self.subTest(receipt=path.name):
                expected = json.loads(path.read_text(encoding="utf-8"))
                actual = self.evaluate_fixture(path.stem)
                self.assertEqual(actual, expected)

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

    def test_cli_writes_json_receipt_and_accepts_as_of(self):
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
                    "--as-of",
                    "2026-08-15T12:30:00Z",
                    "--out",
                    str(destination),
                ],
                check=True,
            )
            receipt = json.loads(destination.read_text())
            self.assertEqual(receipt["schema_version"], "ConformanceReceiptV1")
            self.assertEqual(receipt["evaluated_at"], "2026-08-15T12:30:00Z")

    def test_catalog_has_stable_unique_ids_and_complete_contracts(self):
        ids = [check["check_id"] for check in self.catalog["checks"]]
        self.assertEqual(len(ids), 18, "v0.4.1 must not add or remove checks")
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual({check["profile"] for check in self.catalog["checks"]}, set(self.catalog["profiles"]))
        for check in self.catalog["checks"]:
            declared = set(check["evidence_contracts"])
            required = set(check["required_evidence"])
            applicability = set(check.get("applicability", {}).get("required_evidence", []))
            self.assertTrue(required.union(applicability).issubset(declared), check["check_id"])


if __name__ == "__main__":
    unittest.main()
