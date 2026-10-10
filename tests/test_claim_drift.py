"""Acceptance tests for the Claim Drift application pack.

Tests are written against constitutional_cms.claim_drift and the frozen
fixtures under examples/claim-drift/. They assert observable publication
decisions and rendered HTML / sales-answer / API text, not merely JSON
parsing. Mechanical replay must not call a model or the network.
"""

from __future__ import annotations

import json
import unittest
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / "examples" / "claim-drift"
DOCS = ROOT / "docs"
CONTRACTS = ROOT / "contracts"
SCHEMA = ROOT / "schemas" / "claim_bundle_v0_1.schema.json"

CASES = tuple(f"CD-{index:02d}" for index in range(1, 19))


def load_yaml(path: Path):
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


class ClaimDriftPackLawTest(unittest.TestCase):
    def test_required_files_exist(self):
        required = [
            DOCS / "CLAIM_DRIFT.md",
            PACK / "README.md",
            PACK / "provenance.md",
            PACK / "assertion_profile_v0_1.yaml",
            PACK / "inventory.yaml",
            PACK / "fixtures" / "cd-e2e.yaml",
        ]
        required.extend(PACK / "fixtures" / f"cd-{index:02d}.yaml" for index in range(1, 19))
        for path in required:
            with self.subTest(path=str(path.relative_to(ROOT))):
                self.assertTrue(path.is_file(), path)

    def test_profile_is_a_companion_not_a_new_authority(self):
        profile = load_yaml(PACK / "assertion_profile_v0_1.yaml")
        self.assertEqual(profile["version"], "0.1.0")
        self.assertEqual(profile["maps_into"]["publication_permission"]["contract"], "contracts/claim_decision.yaml")
        self.assertEqual(profile["maps_into"]["publication_permission"]["vocabulary"], ["publish", "hold", "suppress"])
        self.assertEqual(profile["maps_into"]["integrity_verification"]["verifier"], "constitutional_cms.claims.verify_bundle")
        self.assertTrue(profile["not_a"])
        for banned in (
            "fifth_web_conformance_profile",
            "new_permission_authority",
            "site_compiler",
            "score",
            "truth_certification",
            "released_v0_5_0_feature",
        ):
            self.assertIn(banned, profile["not_a"])
        self.assertEqual(
            set(profile["layers"]),
            {
                "integrity_verification",
                "evidence_support_assessment",
                "publication_permission",
                "delivery_verification",
            },
        )

    def test_inventory_nominates_about_twenty_assertions(self):
        inventory = load_yaml(PACK / "inventory.yaml")
        count = len(inventory["assertions"])
        self.assertGreaterEqual(count, 18)
        self.assertLessEqual(count, 24)
        kinds = {item["claim_kind"] for item in inventory["assertions"]}
        for kind in ("product_capability", "plan_entitlement", "release_status", "pricing_model"):
            self.assertIn(kind, kinds)
        subjects = {item["subject"] for item in inventory["assertions"]}
        self.assertIn("product:constitutional-cms", subjects)
        self.assertIn("product:harbor-ledger", subjects)

    def test_signed_v0_1_bundle_schema_is_unchanged(self):
        schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
        claim_props = schema["properties"]["claims"]["items"]["properties"]
        self.assertEqual(
            set(claim_props),
            {"claim_id", "value", "authority", "observed_at", "valid_until", "evidence_digest"},
        )
        self.assertFalse(schema["properties"]["claims"]["items"].get("additionalProperties", True))
        forbidden = {
            "polarity",
            "assertion_version",
            "retrieved_at",
            "decided_at",
            "last_served_verified_at",
            "publication_status",
        }
        self.assertTrue(forbidden.isdisjoint(claim_props))

    def test_docs_use_section_9_public_wording(self):
        text = (DOCS / "CLAIM_DRIFT.md").read_text(encoding="utf-8")
        self.assertIn(
            "Constitutional CMS provides publishing-governance contracts and evidence",
            text,
        )
        self.assertIn("the gap between what a product currently supports", text)
        self.assertIn("Do not yet claim automatic web-wide correction", text)
        self.assertIn("guaranteed AI citation", text)
        self.assertIn("comprehensive contradiction detection", text)
        self.assertIn("independent truth certification", text)
        self.assertIn("not a released v0.5.0 feature", text.lower())
        self.assertNotIn("Claim Gate is a released v0.5.0 feature", text)

    def test_docs_do_not_overclaim(self):
        blob = "\n".join(
            path.read_text(encoding="utf-8")
            for path in (
                DOCS / "CLAIM_DRIFT.md",
                PACK / "README.md",
                PACK / "provenance.md",
                PACK / "assertion_profile_v0_1.yaml",
            )
        )
        lowered = blob.lower()
        self.assertNotIn("automatic web-wide correction is provided", lowered)
        self.assertNotIn("guarantees ai citation", lowered)
        self.assertNotIn("certifies truth", lowered)
        self.assertNotIn("tgflightsfromnyc", lowered)
        self.assertNotIn("railway_token", lowered)
        self.assertIn("not a released v0.5.0 feature", lowered)

    def test_fixtures_freeze_clocks_and_retain_sources(self):
        for case_id in CASES:
            fixture = load_yaml(PACK / "fixtures" / f"{case_id.lower()}.yaml")
            self.assertEqual(fixture["as_of"], "2026-10-09T16:00:00Z")
            self.assertTrue(fixture.get("include_assertions"))
        for path in (PACK / "sources").glob("*.md"):
            text = path.read_text(encoding="utf-8")
            self.assertIn("Frozen-at:", text)
            self.assertIn("Observed-at:", text)

    def test_module_does_not_use_the_network_or_a_model(self):
        from constitutional_cms import claim_drift

        source = Path(claim_drift.__file__).read_text(encoding="utf-8")
        for token in ("urllib", "requests", "http.client", "openai", "anthropic", "httpx"):
            self.assertNotIn(token, source)


class ClaimDriftAcceptanceTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from constitutional_cms.claim_drift import evaluate_case, evaluate_revision

        cls.evaluate_case = staticmethod(evaluate_case)
        cls.evaluate_revision = staticmethod(evaluate_revision)

    def result(self, case_id: str):
        return self.evaluate_case(case_id)

    def pub(self, result, claim_id):
        return result["layers"]["publication"][claim_id]["status"]

    def support(self, result, claim_id):
        return result["layers"]["evidence_support"][claim_id]["verdict"]

    def test_cd_01_universal_denial_cannot_publish_qualified_may(self):
        result = self.result("CD-01")
        self.assertEqual(self.pub(result, "claim:harbor.sso.universal-absent"), "suppress")
        self.assertEqual(self.pub(result, "claim:harbor.sso.enterprise"), "publish")
        html = result["projections"]["html"]
        sales = result["projections"]["sales_answer"]
        api = result["projections"]["api"]
        self.assertIn("SAML SSO is available on the Enterprise plan", html)
        self.assertNotIn("Harbor Ledger has no SAML SSO", html)
        self.assertIn("SAML SSO is available on the Enterprise plan", sales)
        self.assertNotIn("Harbor Ledger has no SAML SSO", sales)
        self.assertEqual(api["claims"]["claim:harbor.sso.enterprise"]["status"], "publish")
        self.assertEqual(api["claims"]["claim:harbor.sso.universal-absent"]["status"], "suppress")
        self.assertNotIn("value", api["claims"]["claim:harbor.sso.universal-absent"])

    def test_cd_02_like_scopes_are_not_a_contradiction(self):
        result = self.result("CD-02")
        self.assertEqual(self.pub(result, "claim:harbor.sso.absent-free"), "publish")
        self.assertEqual(self.pub(result, "claim:harbor.sso.enterprise"), "publish")
        codes = result["layers"]["evidence_support"]["claim:harbor.sso.absent-free"]["reason_codes"]
        self.assertIn("scope_mismatch_not_contradiction", codes)
        html = result["projections"]["html"]
        self.assertIn("not included on the Free plan", html)
        self.assertIn("available on the Enterprise plan", html)

    def test_cd_03_prices_keep_their_cohorts(self):
        result = self.result("CD-03")
        self.assertEqual(self.pub(result, "claim:harbor.price.current"), "publish")
        self.assertEqual(self.pub(result, "claim:harbor.price.legacy-2024"), "publish")
        html = result["projections"]["html"]
        self.assertIn("USD 29", html)
        self.assertIn("USD 19", html)
        self.assertIn("2024 cohort", html)
        api = result["projections"]["api"]["claims"]
        self.assertEqual(api["claim:harbor.price.current"]["value"], "29")
        self.assertEqual(api["claim:harbor.price.legacy-2024"]["value"], "19")

    def test_cd_04_roadmap_is_not_current_availability(self):
        result = self.result("CD-04")
        self.assertNotEqual(self.pub(result, "claim:harbor.sso.ga"), "publish")
        self.assertIn(self.support(result, "claim:harbor.sso.ga"), {"UNSUPPORTED", "UNMEASURED"})
        self.assertIn(
            "roadmap_is_not_ga",
            result["layers"]["evidence_support"]["claim:harbor.sso.ga"]["reason_codes"],
        )
        self.assertEqual(self.pub(result, "claim:harbor.sso.roadmap"), "publish")
        html = result["projections"]["html"]
        self.assertIn("will launch next quarter", html)
        self.assertNotIn("SAML SSO is generally available.", html)

    def test_cd_05_failed_scrape_is_unmeasured_not_absence(self):
        result = self.result("CD-05")
        self.assertEqual(self.support(result, "claim:harbor.feature.absent-unmeasured"), "UNMEASURED")
        self.assertNotEqual(self.pub(result, "claim:harbor.feature.absent-unmeasured"), "publish")
        self.assertFalse(result["layers"]["evidence_support"]["claim:harbor.feature.absent-unmeasured"]["inspectable"])
        self.assertNotIn("has no audit-log export", result["projections"]["html"])

    def test_cd_06_modified_date_does_not_reset_observation(self):
        result = self.result("CD-06")
        clocks = result["clocks"]["evidence"]["ev:ccms-claim-gate"]
        self.assertEqual(clocks["observed_at"], "2026-10-01T12:00:00Z")
        self.assertEqual(clocks["effective_from"], "2026-08-15T00:00:00Z")
        self.assertEqual(clocks["retrieved_at"], "2026-10-09T16:00:00Z")
        self.assertEqual(clocks["page_modified_at"], "2026-10-09T15:59:00Z")
        self.assertNotEqual(clocks["observed_at"], clocks["page_modified_at"])
        self.assertEqual(result["clocks"]["review_deadline"], "2026-10-15T12:00:00Z")
        self.assertEqual(self.pub(result, "claim:ccms.receipts.never-truth"), "publish")

    def test_cd_07_integrity_pass_does_not_authorize_publication(self):
        result = self.result("CD-07")
        integrity = result["layers"]["integrity"]
        self.assertTrue(integrity["ok"])
        self.assertEqual(integrity["verdict"], "PASS")
        self.assertFalse(integrity["authorizes_publication"])
        self.assertNotEqual(self.pub(result, "claim:ccms.claim-gate.released-in-v0.5.0"), "publish")
        self.assertIn(
            "integrity_is_not_permission",
            result["layers"]["publication"]["claim:ccms.claim-gate.released-in-v0.5.0"]["reason_codes"],
        )
        self.assertNotIn("released v0.5.0 feature", result["projections"]["html"])

    def test_cd_08_unsigned_receipt_is_not_trusted_issuance(self):
        result = self.result("CD-08")
        integrity = result["layers"]["integrity"]
        self.assertFalse(integrity["authenticated"])
        self.assertFalse(integrity["authorizes_publication"])
        self.assertIn("receipt_unauthenticated", integrity["reason_codes"])
        self.assertNotEqual(self.pub(result, "claim:ccms.claim-gate.released-in-v0.5.0"), "publish")
        self.assertNotIn("released v0.5.0 feature", result["projections"]["sales_answer"])

    def test_cd_09_obsolete_permission_rejected_history_intact(self):
        result = self.result("CD-09")
        publication = result["layers"]["publication"]["claim:harbor.sso.ga"]
        self.assertNotEqual(publication["status"], "publish")
        self.assertIn("obsolete_permission", publication["reason_codes"])
        self.assertTrue(result["historical_artifact"]["intact"])
        self.assertTrue(result["historical_artifact"]["historically_verifiable"])
        self.assertFalse(result["historical_artifact"]["represents_current_state"])
        self.assertEqual(self.pub(result, "claim:harbor.sso.enterprise"), "publish")
        self.assertIn("Enterprise plan", result["projections"]["html"])

    def test_cd_10_html_fixed_api_stale_is_incomplete_delivery(self):
        result = self.result("CD-10")
        delivery = result["layers"]["delivery"]
        self.assertEqual(delivery["acceptance"], "incomplete")
        self.assertIn("api", delivery["failing_or_unmeasured_surfaces"])
        self.assertEqual(delivery["surfaces"]["html"]["status"], "verified")
        self.assertEqual(delivery["surfaces"]["sales_answer"]["status"], "verified")
        self.assertEqual(delivery["surfaces"]["api"]["status"], "stale")
        self.assertEqual(delivery["enrolled_denominator"], 3)
        self.assertIn("SAML SSO is available on the Enterprise plan", result["projections"]["html"])
        self.assertIn("delivery_surface_stale", delivery["reason_codes"])

    def test_cd_11_dropped_qualifier_is_refused(self):
        result = self.result("CD-11")
        self.assertNotEqual(self.pub(result, "claim:harbor.sso.enterprise-workload"), "publish")
        self.assertIn(
            "qualifier_dropped",
            result["layers"]["publication"]["claim:harbor.sso.enterprise-workload"]["reason_codes"],
        )
        html = result["projections"]["html"]
        self.assertNotIn(">SAML SSO is available.<", html.replace(" ", ""))
        self.assertNotEqual(result["projections"]["sales_answer"].strip(), "SAML SSO is available.")

    def test_cd_12_source_cannot_mutate_authority(self):
        result = self.result("CD-12")
        self.assertFalse(result["policy_authority"]["changed"])
        self.assertEqual(result["policy_authority"]["source_treated_as"], "untrusted_evidence")
        self.assertIn("source_instruction_untrusted", result["policy_authority"]["reason_codes"])
        self.assertNotEqual(self.pub(result, "claim:harbor.sso.universal-absent"), "publish")

    def test_cd_13_syndication_is_one_origin(self):
        result = self.result("CD-13")
        support = result["layers"]["evidence_support"]["claim:harbor.sso.universal-absent"]
        self.assertEqual(support["independent_source_count"], 1)
        self.assertIn("common_origin_not_independent", support["reason_codes"])
        self.assertNotEqual(self.pub(result, "claim:harbor.sso.universal-absent"), "publish")

    def test_cd_14_customer_experience_is_retained_with_scope(self):
        result = self.result("CD-14")
        self.assertEqual(self.pub(result, "claim:harbor.customer.outage-2026-03"), "publish")
        self.assertEqual(self.pub(result, "claim:harbor.sso.enterprise"), "publish")
        html = result["projections"]["html"]
        self.assertIn("Acme Corp", html)
        self.assertIn("2026-03-12", html)
        self.assertIn("Enterprise", html)
        self.assertIn(
            "attributed_experience_retained",
            result["layers"]["evidence_support"]["claim:harbor.customer.outage-2026-03"]["reason_codes"],
        )
        api = result["projections"]["api"]["claims"]["claim:harbor.customer.outage-2026-03"]
        self.assertEqual(api["status"], "publish")
        self.assertIn("Acme Corp", str(api.get("qualifications") or api.get("value")))

    def test_cd_15_withhold_does_not_retire_or_noindex(self):
        result = self.result("CD-15")
        self.assertNotEqual(self.pub(result, "claim:harbor.sso.universal-absent"), "publish")
        entity = result["entities"]["product:harbor-ledger"]
        self.assertFalse(entity["retired"])
        self.assertEqual(entity["lifecycle_state"], "active")
        self.assertEqual(entity["artifact_state"], "publish")
        self.assertTrue(entity["indexable"])
        self.assertIn("claim_withheld_entity_intact", entity["reason_codes"])
        self.assertNotIn("Harbor Ledger has no SAML SSO", result["projections"]["html"])

    def test_cd_16_self_favoring_inaccuracy_is_refused(self):
        result = self.result("CD-16")
        self.assertNotEqual(self.pub(result, "claim:ccms.claim-gate.released-in-v0.5.0"), "publish")
        self.assertEqual(self.pub(result, "claim:ccms.claim-gate.not-in-v0.5.0"), "publish")
        html = result["projections"]["html"]
        self.assertIn("draft on main", html)
        self.assertNotIn("Claim Gate is a released v0.5.0 feature.", html)
        self.assertIn(
            "same_evidentiary_standard",
            result["layers"]["publication"]["claim:ccms.claim-gate.released-in-v0.5.0"]["reason_codes"],
        )

    def test_cd_17_harmless_paraphrase_still_publishes(self):
        result = self.result("CD-17")
        self.assertEqual(self.pub(result, "claim:ccms.receipts.never-truth"), "publish")
        self.assertEqual(self.pub(result, "claim:ccms.receipts.never-truth.paraphrase"), "publish")
        self.assertIn(
            "paraphrase_without_strengthening",
            result["layers"]["publication"]["claim:ccms.receipts.never-truth.paraphrase"]["reason_codes"],
        )
        html = result["projections"]["html"]
        sales = result["projections"]["sales_answer"]
        self.assertIn("does not certify that a statement is true", html)
        self.assertIn("does not certify that a statement is true", sales)
        self.assertIn("never truth", html)

    def test_cd_18_unmeasured_support_plus_audit_exit_0_is_not_release(self):
        result = self.result("CD-18")
        self.assertEqual(self.support(result, "claim:harbor.feature.absent-unmeasured"), "UNMEASURED")
        self.assertEqual(result["audit"]["exit_code"], 0)
        self.assertTrue(result["audit"]["receipt_generated"])
        self.assertFalse(result["audit"]["authorizes_publication"])
        self.assertNotEqual(self.pub(result, "claim:harbor.feature.absent-unmeasured"), "publish")
        self.assertIn(
            "audit_is_not_permission",
            result["layers"]["publication"]["claim:harbor.feature.absent-unmeasured"]["reason_codes"],
        )
        self.assertNotIn("has no audit-log export", result["projections"]["html"])

    def test_e2e_source_revision_sequence_and_stale_api(self):
        result = self.evaluate_revision("CD-E2E")
        self.assertEqual(
            result["sequence"],
            [
                "source_revision",
                "affected_claims_identified",
                "permission_re_evaluated",
                "artifacts_rebuilt_or_withheld",
                "surfaces_inspected",
                "delivery_outcome_recorded",
            ],
        )
        self.assertIn("claim:harbor.sso.ga", result["affected_claims"])
        self.assertIn("claim:harbor.sso.enterprise", result["affected_claims"])
        after = result["after"]
        self.assertNotEqual(self.pub(after, "claim:harbor.sso.ga"), "publish")
        self.assertEqual(self.pub(after, "claim:harbor.sso.enterprise"), "publish")
        self.assertIn("SAML SSO is available on the Enterprise plan", after["projections"]["html"])
        self.assertIn("SAML SSO is available on the Enterprise plan", after["projections"]["sales_answer"])
        self.assertNotIn("generally available", after["projections"]["html"])
        delivery = after["layers"]["delivery"]
        self.assertEqual(delivery["acceptance"], "incomplete")
        self.assertEqual(delivery["surfaces"]["html"]["status"], "verified")
        self.assertEqual(delivery["surfaces"]["api"]["status"], "stale")
        self.assertIn("api", delivery["failing_or_unmeasured_surfaces"])
        self.assertEqual(result["owner"], "harbor-docs")
        self.assertEqual(result["enrolled_denominator"], 3)
        self.assertIn("ev:harbor-docs-sso", result["versions"]["evidence"])

    def test_layers_remain_separate_on_every_case(self):
        for case_id in CASES:
            with self.subTest(case_id=case_id):
                result = self.result(case_id)
                layers = result["layers"]
                self.assertIn("integrity", layers)
                self.assertIn("evidence_support", layers)
                self.assertIn("publication", layers)
                self.assertIn("delivery", layers)
                self.assertFalse(layers["integrity"]["authorizes_publication"])
                for claim_id, decision in layers["publication"].items():
                    self.assertIn(decision["status"], {"publish", "hold", "suppress"})
                    self.assertIn(layers["evidence_support"][claim_id]["verdict"], {"SUPPORTED", "UNSUPPORTED", "UNMEASURED"})

    def test_entity_lifecycle_contract_still_forbids_claim_withhold(self):
        contract = load_yaml(CONTRACTS / "entity_lifecycle.yaml")
        forbidden = set(contract["terminal_transition"]["forbidden_triggers"])
        for trigger in ("claim_withheld", "claim_suppressed", "claim_absent"):
            self.assertIn(trigger, forbidden)


class ClaimDriftIndexTest(unittest.TestCase):
    def test_indexes_list_the_pack(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        examples = (ROOT / "examples" / "README.md").read_text(encoding="utf-8")
        protocol = (DOCS / "PROTOCOL_MAP.md").read_text(encoding="utf-8")
        self.assertIn("CLAIM_DRIFT.md", readme)
        self.assertIn("claim-drift", examples)
        self.assertIn("CLAIM_DRIFT.md", protocol)
        self.assertIn("not a scheme", protocol.lower())


if __name__ == "__main__":
    unittest.main()
