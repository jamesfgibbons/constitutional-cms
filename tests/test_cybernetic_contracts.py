import re
import unittest
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
CONTRACTS = ROOT / "contracts"


def load_contract(name):
    with (CONTRACTS / name).open("r") as handle:
        return yaml.safe_load(handle)


class CyberneticContractsTest(unittest.TestCase):
    def test_proof_ledger_json_governs_markdown(self):
        contract = load_contract("proof_ledger.yaml")

        self.assertEqual(contract["authority"]["machine_readable_artifact"], "governs")
        self.assertEqual(contract["authority"]["markdown_summary"], "display_only")

        rule_ids = {rule["id"] for rule in contract["narrative_rules"]}
        self.assertIn("markdown_cannot_upgrade_status", rule_ids)
        self.assertIn("no_narrative_without_data", rule_ids)

    def test_sensor_integrity_blocks_false_zeroes_when_source_failed(self):
        contract = load_contract("sensor_integrity.yaml")
        statuses = contract["source_status_vocabulary"]

        self.assertFalse(statuses["failed"]["reporting_allowed"])
        self.assertFalse(statuses["unattributed"]["reporting_allowed"])

        rule_ids = {rule["id"] for rule in contract["reporting_rules"]}
        self.assertIn("no_silent_zeroes", rule_ids)
        self.assertIn("sensor_failure_not_world_silence", rule_ids)

        self.assertEqual(
            set(contract["mutation_class_vocabulary"]),
            {"pure_read", "read_with_side_effect", "active_perturbation"},
        )
        self.assertIn("UNMEASURED", contract["measurement_states"])
        measurement_rule_ids = {rule["id"] for rule in contract["measurement_rules"]}
        self.assertIn("missing_inputs_are_unmeasured", measurement_rule_ids)
        self.assertIn("observation_side_effects_are_declared", measurement_rule_ids)

    def test_signal_projection_surfaces_derive_from_canonical_state(self):
        contract = load_contract("signal_projection.yaml")

        for surface, config in contract["projection_surfaces"].items():
            with self.subTest(surface=surface):
                self.assertEqual(config["must_derive_from"], "canonical_state")

        absence_states = set(contract["honest_absence_states"])
        self.assertEqual(
            {"not_observed", "stale", "pending", "unavailable", "invalid"},
            absence_states,
        )

    def test_agent_envelope_requires_idempotent_data_plane(self):
        contract = load_contract("agent_operating_envelope.yaml")
        rules = {rule["id"] for rule in contract["data_plane_immutability"]["rules"]}

        self.assertIn("manifest_before_external_call", rules)
        self.assertIn("idempotency_ledger_required", rules)
        self.assertIn("no_ingestion_retry_on_verifier_failure", rules)
        self.assertIn("duplicate_observation_veto", rules)

    def test_public_docs_link_to_existing_repo_files(self):
        docs_to_check = [
            ROOT / "README.md",
            ROOT / "docs" / "STORY_BIBLE.md",
            ROOT / "docs" / "CONSTITUTIONAL_CYBERNETICS.md",
        ]
        link_pattern = re.compile(r"\[[^\]]+\]\((?!https?://)([^)#]+)")

        for doc_path in docs_to_check:
            text = doc_path.read_text()
            for match in link_pattern.finditer(text):
                target = match.group(1)
                resolved = (doc_path.parent / target).resolve()
                with self.subTest(doc=doc_path.name, target=target):
                    self.assertTrue(
                        resolved.exists(),
                        f"{doc_path.relative_to(ROOT)} links to missing {target}",
                    )

    def test_public_docs_do_not_reference_private_workspace_paths(self):
        docs_to_check = [
            ROOT / "README.md",
            ROOT / "docs" / "STORY_BIBLE.md",
            ROOT / "docs" / "CONSTITUTIONAL_CYBERNETICS.md",
        ]
        forbidden = [
            "/Users/",
            "/Documents/",
            ".env",
            "ADMIN_SECRET",
            "RAILWAY_TOKEN",
            "SUPABASE_SERVICE_ROLE",
        ]

        for doc_path in docs_to_check:
            text = doc_path.read_text()
            for token in forbidden:
                with self.subTest(doc=doc_path.name, token=token):
                    self.assertNotIn(token, text)


if __name__ == "__main__":
    unittest.main()
