import unittest
from pathlib import Path

import yaml

from constitutional_cms.entity_lifecycle import evaluate_projection

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests/fixtures/lifecycle"


def load(name: str) -> dict:
    return yaml.safe_load((FIXTURES / name).read_text(encoding="utf-8"))


class EntityLifecycleTest(unittest.TestCase):
    def ids(self, name: str) -> set[str]:
        return {row["collapse_id"] for row in evaluate_projection(load(name))}

    def test_legal_concurrent_states_are_not_a_contradiction(self):
        self.assertEqual(evaluate_projection(load("legal_concurrent_states.yaml")), [])

    def test_lawful_410_with_terminal_authority_and_receipt(self):
        self.assertEqual(evaluate_projection(load("lawful_410.yaml")), [])

    def test_child_404_must_not_escalate_parent_410(self):
        self.assertIn("child_404_to_parent_410", self.ids("child_404_to_parent_410.yaml"))
        self.assertIn("410_without_terminal", self.ids("child_404_to_parent_410.yaml"))

    def test_withheld_claim_must_not_retire_subject(self):
        ids = self.ids("claim_absence_to_entity_absence.yaml")
        self.assertTrue(
            {"claim_absence_to_entity_absence", "410_without_terminal", "missing_evidence_deletes_entity"}
            & ids
        )

    def test_seasonal_inactive_is_not_retired(self):
        self.assertIn("seasonal_inactive_to_retired", self.ids("seasonal_inactive_to_retired.yaml"))

    def test_unknown_must_not_become_410(self):
        ids = self.ids("unknown_to_terminal.yaml")
        self.assertIn("unknown_to_absent", ids)
        self.assertIn("410_without_terminal", ids)

    def test_renderer_cannot_derive_lifecycle(self):
        self.assertIn("renderer_derived_lifecycle", self.ids("renderer_derived_lifecycle.yaml"))

    def test_contract_lists_ten_invariants(self):
        data = yaml.safe_load((ROOT / "contracts/entity_lifecycle_v1.yaml").read_text(encoding="utf-8"))
        self.assertEqual(len(data["invariants"]), 10)
        self.assertEqual(data["status"], "draft")
        self.assertFalse(data["scheme"]["orders"])
        self.assertFalse(data["scheme"]["certifies"])


if __name__ == "__main__":
    unittest.main()
