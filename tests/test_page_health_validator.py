import importlib.util
import sys
import unittest
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "page_health_validator.py"
SPEC = importlib.util.spec_from_file_location("page_health_validator", SCRIPT_PATH)
page_health_validator = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules["page_health_validator"] = page_health_validator
SPEC.loader.exec_module(page_health_validator)


class PageHealthValidatorTest(unittest.TestCase):
    def codes_for(self, rows):
        findings = page_health_validator.analyze_rows(rows)
        return {finding.code for finding in findings}

    def test_degraded_indexable_shell_is_allowed(self):
        codes = self.codes_for(
            [
                {
                    "url": "https://example.com/entities/example-a",
                    "status": "200",
                    "quality_tier": "SHELL",
                    "indexable": "true",
                    "sitemap_eligible": "true",
                    "noindex": "false",
                    "visible_claim": "false",
                }
            ]
        )
        self.assertEqual(codes, set())

    def test_suppressed_page_is_excluded_from_sitemap(self):
        codes = self.codes_for(
            [
                {
                    "url": "https://example.com/entities/retired",
                    "status": "410",
                    "quality_tier": "SUPPRESS",
                    "sitemap_eligible": "true",
                }
            ]
        )
        self.assertIn("suppressed_url_in_sitemap", codes)

    def test_visible_claim_requires_validated_source_or_suppression(self):
        codes = self.codes_for(
            [
                {
                    "url": "https://example.com/entities/example-b",
                    "status": "200",
                    "visible_claim": "true",
                    "claim_publishable": "false",
                    "suppression_visible": "false",
                }
            ]
        )
        self.assertIn("visible_claim_without_validated_source", codes)

    def test_materialized_artifact_requires_metadata(self):
        codes = self.codes_for(
            [
                {
                    "url": "https://example.com/entities/example-c",
                    "status": "200",
                    "materialized": "true",
                    "rendered_at": "2026-05-02T12:00:00Z",
                    "build_id": "",
                    "deploy_id": "",
                    "content_hash": "abc123",
                    "template_family": "entity",
                }
            ]
        )
        self.assertIn("materialized_artifact_missing_metadata", codes)

    def test_internal_link_to_failed_target_is_p0(self):
        codes = self.codes_for(
            [
                {
                    "url": "https://example.com/entities/example-d",
                    "status": "200",
                    "internal_link_status": "404",
                }
            ]
        )
        self.assertIn("internal_link_to_non_200", codes)

    def test_mobile_table_layout_is_observe_finding(self):
        findings = page_health_validator.analyze_rows(
            [
                {
                    "url": "https://example.com/entities/example-e",
                    "status": "200",
                    "viewport_width": "390",
                    "layout_mode": "table",
                }
            ]
        )
        self.assertEqual(findings[0].code, "mobile_table_requires_card_layout")
        self.assertEqual(findings[0].severity, "P2")


if __name__ == "__main__":
    unittest.main()
