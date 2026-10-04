"""Acceptance tests for the Governed Programmatic Publishing pack.

Fixtures and expected verdicts live under examples/programmatic-publishing/.
This module is a reference detector for that synthetic catalogue. It is not a
site compiler and it does not call the public CLI as one.
"""

from __future__ import annotations

import unittest
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / "examples" / "programmatic-publishing"
DOCS = ROOT / "docs"
CONTRACTS = ROOT / "contracts"

NON_TERMINAL = {
    "active",
    "seasonal_active",
    "seasonal_inactive",
    "launching",
    "suspended",
    "unknown",
}

ABSENT_FIELD = {None, "", "absent", "withheld", "stale"}
CASES = (
    "baseline",
    "price_parity_contradiction",
    "inventory_feed_failed",
    "served_artifact_mismatch",
)


def load_yaml(path: Path):
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def load_domain():
    return load_yaml(PACK / "domain-example.yaml")


def load_case(case_id: str):
    return load_yaml(PACK / "fixtures" / f"{case_id}.yaml"), load_yaml(
        PACK / "expected" / f"{case_id}.yaml"
    )


def authorized_terminal(lifecycle: dict) -> bool:
    return (
        lifecycle.get("state") == "retired"
        and bool(lifecycle.get("terminal"))
        and bool(lifecycle.get("lifecycle_authority"))
        and bool(lifecycle.get("evidence_reference"))
        and bool(lifecycle.get("reason_code"))
        and bool(lifecycle.get("effective_at"))
    )


def resolve_lifecycle(entity: dict) -> dict:
    lifecycle = entity.get("lifecycle") or {}
    state = lifecycle.get("state", "unknown")
    if authorized_terminal(lifecycle):
        artifact_state = "gone"
    elif state in NON_TERMINAL or state not in {"retired"}:
        artifact_state = "publish"
    else:
        artifact_state = "publish"
    return {
        "lifecycle_state": state,
        "artifact_state": artifact_state,
        "body_publishable": artifact_state != "gone" and not entity.get("document_hold", False),
        "retired": artifact_state == "gone",
    }


def claims_by_id(fixture: dict) -> dict:
    return {claim["claim_id"]: claim for claim in fixture.get("claims") or []}


def claim_authority_ok(claim: dict, domain: dict) -> bool:
    admitted = set(domain["admitted_source_classes"])
    forbidden = set(domain["forbidden_source_classes_for_public_claims"])
    source_class = (claim.get("source") or {}).get("source_class")
    slot = domain["claim_slots"].get(claim["claim_type"], {})
    required = list(slot.get("required_qualifiers") or [])

    if claim.get("status") == "publish":
        if source_class in forbidden or source_class not in admitted:
            return False
        if claim.get("confidence") in {None, "unknown"}:
            return False
        for qualifier in required:
            if qualifier == "source_id" and not (claim.get("source") or {}).get("source_id"):
                return False
            if qualifier != "source_id" and not claim.get(qualifier):
                return False
        return True

    # Withheld / hold: honest absence is authorized when a reason exists.
    return bool(claim.get("reason_codes")) or claim.get("status") in {"withheld", "hold"}


def invented_zero(claim: dict, fixture: dict) -> bool:
    if claim.get("claim_type") != "availability":
        return False
    sensors = {
        sensor["sensor_id"]: sensor for sensor in fixture.get("sensors") or []
    }
    source_id = (claim.get("source") or {}).get("source_id", "")
    sensor = None
    for candidate in sensors.values():
        if candidate["sensor_id"] in source_id or source_id.startswith(candidate["sensor_id"]):
            sensor = candidate
            break
    if sensor is None:
        sensor = sensors.get("feed:inventory")
    failed = bool(sensor and sensor.get("source_status") == "failed")
    withheld = claim.get("status") in {"withheld", "hold"}
    value = claim.get("value")
    numeric_zero = value in {0, "0", "0.0"}
    if (failed or withheld) and numeric_zero:
        return True
    if failed:
        for page in fixture.get("pages") or []:
            for projection in (page.get("projections") or {}).values():
                shown = projection.get(claim["claim_id"])
                if shown in {0, "0", "0.0"}:
                    return True
    return False


def projection_values(fixture: dict, claim_id: str) -> dict:
    found = {}
    for page in fixture.get("pages") or []:
        for surface, projection in (page.get("projections") or {}).items():
            if claim_id in projection:
                found[f"{page['page_id']}:{surface}"] = str(projection[claim_id])
    return found


def parity_consistent(claim: dict, fixture: dict) -> bool:
    if claim.get("status") != "publish":
        shown = projection_values(fixture, claim["claim_id"])
        return not shown
    governed = str(claim.get("value"))
    shown = projection_values(fixture, claim["claim_id"])
    if not shown:
        return True
    return all(value == governed for value in shown.values())


def field_present(page: dict, name: str) -> bool:
    return page.get("fields", {}).get(name) not in ABSENT_FIELD


def raw_quality_tier(page: dict, domain: dict) -> str:
    family = page["family"]
    spec = domain["page_types"][family]
    word_count = int(page.get("word_count") or 0)
    for tier in ("FULL", "BASIC", "SHELL"):
        required = spec["tiers"][tier]["required_fields"]
        min_words = int(spec["tiers"][tier].get("min_word_count") or 0)
        if all(field_present(page, field) for field in required) and word_count >= min_words:
            return tier
    return "SHELL"


def apply_degradation(page: dict, claims: dict, raw_tier: str) -> str:
    family = page["family"]
    if family != "product_page":
        return raw_tier
    rank = {"SUPPRESS": 0, "SHELL": 1, "BASIC": 2, "FULL": 3}
    tier = raw_tier
    list_price = page.get("fields", {}).get("list_price")
    inventory = page.get("fields", {}).get("inventory_status")
    if list_price in {"withheld", "stale", "absent"} and not field_present(page, "list_price"):
        # Absent list_price already prevents BASIC/FULL via required_fields.
        if list_price in {"withheld", "stale"}:
            tier = "SHELL"
    if inventory == "withheld":
        if rank[tier] > rank["BASIC"]:
            tier = "BASIC"
    subject = page.get("entity_id")
    price_claim = next(
        (
            claim
            for claim in claims.values()
            if claim.get("subject_id") == subject and claim.get("claim_type") == "price"
        ),
        None,
    )
    if price_claim and price_claim.get("status") in {"withheld", "hold"}:
        tier = "SHELL"
    return tier


def quality_tier(page: dict, entity_result: dict, domain: dict, claims: dict) -> str:
    if entity_result["retired"]:
        return "SUPPRESS"
    return apply_degradation(page, claims, raw_quality_tier(page, domain))


def purpose_satisfied(page: dict, fixture: dict, claims: dict, domain: dict, tier: str) -> bool:
    family = domain["page_families"][page["family"]]
    if page["family"] == "product_page":
        if not page.get("fields", {}).get("product_name"):
            return False
        price_ok = field_present(page, "list_price") or any(
            claim.get("subject_id") == page["entity_id"]
            and claim.get("claim_type") == "price"
            and claim.get("status") in {"withheld", "hold"}
            for claim in claims.values()
        )
        inventory_ok = (
            field_present(page, "inventory_status")
            or page.get("fields", {}).get("inventory_status") in {"withheld", "absent"}
        )
        return price_ok and inventory_ok
    if page["family"] == "collection_page":
        children = page.get("child_entity_ids") or []
        return bool(page.get("fields", {}).get("collection_name")) and bool(children)
    if page["family"] == "comparison_page":
        return field_present(page, "product_a_snapshot") and field_present(
            page, "product_b_snapshot"
        ) and field_present(page, "spec_diff_table") and tier in {"FULL", "BASIC"}
    required = family.get("required_evidence") or []
    return bool(required)


def same_approved_inputs(page: dict, claims: dict) -> bool:
    for projection in (page.get("projections") or {}).values():
        for claim_id, shown in projection.items():
            claim = claims.get(claim_id)
            if claim is None:
                return False
            if claim.get("status") != "publish":
                return False
            if str(shown) != str(claim.get("value")):
                return False
    return True


def discovery_for(page: dict, domain: dict, tier: str) -> dict:
    family = domain["page_families"][page["family"]]
    index_policy = family["indexability_policy"][tier]
    sitemap_policy = family["sitemap_policy"][tier]
    return {
        "seo_indexable": index_policy == "index",
        "sitemap_eligible": sitemap_policy == "include",
    }


def evaluate(domain: dict, fixture: dict) -> dict:
    claims = claims_by_id(fixture)
    entities = {}
    for entity in fixture.get("entities") or []:
        entities[entity["id"]] = resolve_lifecycle(entity)

    claim_results = {}
    failures = []
    for claim_id, claim in claims.items():
        zero = invented_zero(claim, fixture)
        consistent = parity_consistent(claim, fixture)
        result = {
            "status": claim.get("status"),
            "authority_ok": claim_authority_ok(claim, domain),
            "parity_consistent": consistent,
            "invented_zero": zero,
        }
        claim_results[claim_id] = result
        if zero:
            failures.append("inventory_zero_invented")
        if claim.get("claim_type") == "price" and not consistent:
            failures.append("price_parity_contradiction")

    pages = {}
    for page in fixture.get("pages") or []:
        entity_result = entities[page["entity_id"]]
        tier = quality_tier(page, entity_result, domain, claims)
        disc = discovery_for(page, domain, tier)
        pages[page["page_id"]] = {
            "family": page["family"],
            "quality_tier": tier,
            "purpose_satisfied": purpose_satisfied(page, fixture, claims, domain, tier),
            "seo_indexable": disc["seo_indexable"],
            "sitemap_eligible": disc["sitemap_eligible"],
            "same_approved_inputs": same_approved_inputs(page, claims),
        }

    for entity_id, result in entities.items():
        entity = next(item for item in fixture["entities"] if item["id"] == entity_id)
        if result["retired"] and not authorized_terminal(entity.get("lifecycle") or {}):
            failures.append("entity_retired_without_authority")

    release = fixture.get("release") or {}
    served_matches = (
        release.get("candidate_generation_id") == release.get("served_generation_id")
        and release.get("candidate_content_hash") == release.get("served_content_hash")
    )
    if not served_matches:
        failures.append("served_artifact_mismatch")
    if release.get("proof_status_claimed") == "live_verified" and not served_matches:
        failures.append("live_verified_without_wire_match")

    blocking = {
        "price_parity_contradiction",
        "served_artifact_mismatch",
        "live_verified_without_wire_match",
        "inventory_zero_invented",
        "entity_retired_without_authority",
    }
    unique_failures = list(dict.fromkeys(failures))
    acceptance = "failed" if (set(unique_failures) & blocking or not served_matches) else "accepted"

    handling = []
    inventory_sensor = next(
        (
            sensor
            for sensor in fixture.get("sensors") or []
            if sensor.get("source_status") == "failed"
            and "inventory" in sensor.get("sensor_id", "")
        ),
        None,
    )
    if inventory_sensor:
        for claim in claims.values():
            if claim.get("claim_type") == "availability" and claim.get("status") == "withheld":
                subject = claim["subject_id"]
                if subject in entities and not entities[subject]["retired"]:
                    handling.append("inventory_withheld_entity_intact")

    delivery_used = False
    for record in fixture.get("outcomes") or []:
        if record.get("state") in {"not_observed", "unmeasured", "blocked"} and record.get("actual") not in {
            None,
            "",
        }:
            delivery_used = True

    return {
        "case_id": fixture["case_id"],
        "acceptance": acceptance,
        "failures": unique_failures,
        "handling": handling,
        "entities": entities,
        "pages": pages,
        "claims": claim_results,
        "release": {
            "served_matches_candidate": served_matches,
            "acceptance": acceptance,
            "live_verified_allowed": served_matches and acceptance == "accepted",
        },
        "outcomes": {"delivery_used_as_outcome": delivery_used},
    }


def subset_equal(expected, actual, path=""):
    """Assert expected is a subset of actual; return mismatch strings."""
    mismatches = []
    if isinstance(expected, dict):
        if not isinstance(actual, dict):
            return [f"{path}: expected mapping, got {type(actual).__name__}"]
        for key, value in expected.items():
            if key not in actual:
                mismatches.append(f"{path}.{key}: missing from result")
                continue
            mismatches.extend(subset_equal(value, actual[key], f"{path}.{key}" if path else key))
        return mismatches
    if isinstance(expected, list):
        if list(expected) != list(actual):
            mismatches.append(f"{path}: {actual!r} != {expected!r}")
        return mismatches
    if expected != actual:
        mismatches.append(f"{path}: {actual!r} != {expected!r}")
    return mismatches


class ProgrammaticPublishingPackTest(unittest.TestCase):
    def test_required_files_exist(self):
        required = [
            ROOT / "docs" / "PROGRAMMATIC_PUBLISHING.md",
            PACK / "README.md",
            PACK / "domain-example.yaml",
            PACK / "provenance.md",
            PACK / "fixtures" / "baseline.yaml",
            PACK / "fixtures" / "price_parity_contradiction.yaml",
            PACK / "fixtures" / "inventory_feed_failed.yaml",
            PACK / "fixtures" / "served_artifact_mismatch.yaml",
            PACK / "expected" / "baseline.yaml",
            PACK / "expected" / "price_parity_contradiction.yaml",
            PACK / "expected" / "inventory_feed_failed.yaml",
            PACK / "expected" / "served_artifact_mismatch.yaml",
        ]
        for path in required:
            with self.subTest(path=str(path.relative_to(ROOT))):
                self.assertTrue(path.is_file(), path)

    def test_provenance_is_synthetic_and_public_safe(self):
        text = (PACK / "provenance.md").read_text(encoding="utf-8")
        self.assertIn("Provenance mode: synthetic", text)
        domain = load_domain()
        self.assertEqual(domain["provenance_mode"], "synthetic")
        self.assertEqual(domain["domain"]["kind"], "ecommerce_catalogue")
        blob = "\n".join(
            path.read_text(encoding="utf-8")
            for path in [PACK / "provenance.md", PACK / "domain-example.yaml", DOCS / "PROGRAMMATIC_PUBLISHING.md"]
        ).lower()
        for token in (
            "tgflightsfromnyc",
            "/users/",
            "railway_token",
            "supabase_service_role",
        ):
            self.assertNotIn(token, blob, token)

    def test_domain_declares_lifecycle_over_page_types_for_existence(self):
        domain = load_domain()
        self.assertEqual(
            domain["precedence"]["existence_and_terminality"]["authority"],
            "contracts/entity_lifecycle.yaml",
        )
        self.assertIn("page_types", domain["precedence"]["existence_and_terminality"]["wins_over"])
        self.assertIn("forbidden terminal trigger", domain["precedence"]["rule"])
        self.assertTrue(domain["maps_to"]["not_a_fifth_profile"])
        self.assertTrue(domain["maps_to"]["not_a_site_compiler"])
        self.assertEqual(domain["maps_to"]["certification_sequence"], "G0-G5")
        self.assertEqual(
            domain["maps_to"]["web_conformance_profiles"],
            ["foundation", "search", "answer_and_ai_retrieval", "agentic_web"],
        )

    def test_product_suppress_requires_terminal_authority_not_source_failure(self):
        domain = load_domain()
        trigger = domain["page_types"]["product_page"]["tiers"]["SUPPRESS"]["trigger"]
        self.assertIn("entity_lifecycle", trigger)
        self.assertNotIn("unavailable", trigger.lower())
        self.assertIn(
            "do not emit 410 without terminal authority",
            domain["page_types"]["product_page"]["tiers"]["SUPPRESS"]["action"],
        )


class ProgrammaticPublishingFixtureTest(unittest.TestCase):
    def setUp(self):
        self.domain = load_domain()

    def test_each_case_matches_expected(self):
        for case_id in CASES:
            with self.subTest(case_id=case_id):
                fixture, expected = load_case(case_id)
                result = evaluate(self.domain, fixture)
                mismatches = subset_equal(expected, result)
                self.assertFalse(mismatches, "\n".join(mismatches))

    def test_price_mutation_does_not_retire_the_product(self):
        fixture, _ = load_case("price_parity_contradiction")
        result = evaluate(self.domain, fixture)
        self.assertIn("price_parity_contradiction", result["failures"])
        self.assertFalse(result["entities"]["product:northline-task-lamp"]["retired"])
        self.assertEqual(result["acceptance"], "failed")

    def test_inventory_failure_does_not_retire_or_invent_zero(self):
        fixture, _ = load_case("inventory_feed_failed")
        result = evaluate(self.domain, fixture)
        entity = result["entities"]["product:northline-task-lamp"]
        self.assertFalse(entity["retired"])
        self.assertEqual(entity["artifact_state"], "publish")
        self.assertEqual(result["claims"]["claim:task-lamp-inventory"]["status"], "withheld")
        self.assertFalse(result["claims"]["claim:task-lamp-inventory"]["invented_zero"])
        self.assertIn("inventory_withheld_entity_intact", result["handling"])
        self.assertTrue(result["pages"]["page:product:task-lamp"]["seo_indexable"])
        self.assertEqual(result["pages"]["page:product:task-lamp"]["quality_tier"], "BASIC")

    def test_invented_zero_stock_is_a_failure(self):
        fixture, _ = load_case("inventory_feed_failed")
        for claim in fixture["claims"]:
            if claim["claim_id"] == "claim:task-lamp-inventory":
                claim["value"] = "0"
                claim["status"] = "publish"
        result = evaluate(self.domain, fixture)
        self.assertIn("inventory_zero_invented", result["failures"])
        self.assertEqual(result["acceptance"], "failed")
        self.assertFalse(result["entities"]["product:northline-task-lamp"]["retired"])

    def test_missing_metric_does_not_auto_noindex(self):
        fixture, _ = load_case("inventory_feed_failed")
        result = evaluate(self.domain, fixture)
        page = result["pages"]["page:product:task-lamp"]
        self.assertEqual(page["quality_tier"], "BASIC")
        self.assertTrue(page["seo_indexable"])
        policy = self.domain["page_families"]["product_page"]["indexability_policy"]
        self.assertEqual(policy["SHELL"], "index")
        self.assertEqual(policy["BASIC"], "index")

    def test_served_mismatch_blocks_acceptance(self):
        fixture, _ = load_case("served_artifact_mismatch")
        result = evaluate(self.domain, fixture)
        self.assertFalse(result["release"]["served_matches_candidate"])
        self.assertEqual(result["release"]["acceptance"], "failed")
        self.assertFalse(result["release"]["live_verified_allowed"])
        self.assertIn("served_artifact_mismatch", result["failures"])
        self.assertIn("live_verified_without_wire_match", result["failures"])

    def test_delivery_does_not_fill_outcome_actuals(self):
        for case_id in CASES:
            with self.subTest(case_id=case_id):
                fixture, _ = load_case(case_id)
                result = evaluate(self.domain, fixture)
                self.assertFalse(result["outcomes"]["delivery_used_as_outcome"])
                for record in fixture.get("outcomes") or []:
                    if record.get("state") in {"not_observed", "unmeasured"}:
                        self.assertIn(record.get("actual"), {None, ""})

    def test_lifecycle_rows_are_all_demonstrated(self):
        baseline = evaluate(self.domain, load_case("baseline")[0])
        self.assertTrue(baseline["pages"]["page:product:task-lamp"]["purpose_satisfied"])
        self.assertTrue(baseline["pages"]["page:collection:desk-essentials"]["purpose_satisfied"])
        self.assertTrue(baseline["pages"]["page:compare:task-lamp-vs-clamp-lamp"]["purpose_satisfied"])

        inventory = evaluate(self.domain, load_case("inventory_feed_failed")[0])
        self.assertFalse(inventory["entities"]["product:northline-task-lamp"]["retired"])

        self.assertTrue(baseline["claims"]["claim:task-lamp-price"]["authority_ok"])
        self.assertTrue(baseline["claims"]["claim:task-lamp-price"]["parity_consistent"])
        self.assertFalse(
            evaluate(self.domain, load_case("price_parity_contradiction")[0])["claims"][
                "claim:task-lamp-price"
            ]["parity_consistent"]
        )

        self.assertTrue(baseline["pages"]["page:product:task-lamp"]["same_approved_inputs"])
        self.assertTrue(baseline["pages"]["page:product:task-lamp"]["seo_indexable"])
        self.assertTrue(baseline["release"]["served_matches_candidate"])
        self.assertFalse(baseline["outcomes"]["delivery_used_as_outcome"])

    def test_source_failure_cannot_authorize_gone(self):
        fixture, _ = load_case("inventory_feed_failed")
        fixture["entities"][0]["lifecycle"] = {
            "state": "retired",
            "terminal": True,
        }
        result = evaluate(self.domain, fixture)
        self.assertNotEqual(result["entities"]["product:northline-task-lamp"]["artifact_state"], "gone")
        self.assertFalse(result["entities"]["product:northline-task-lamp"]["retired"])


class ProgrammaticPublishingDocsTest(unittest.TestCase):
    def setUp(self):
        self.guide = (DOCS / "PROGRAMMATIC_PUBLISHING.md").read_text(encoding="utf-8")

    def test_guide_states_the_opening_promise(self):
        self.assertIn(
            "Turn structured business data into useful, searchable pages",
            self.guide,
        )
        self.assertIn("not “generate thousands of SEO pages.”", self.guide)
        self.assertIn("scaled-content policy", self.guide)

    def test_guide_does_not_imply_cli_is_a_compiler(self):
        self.assertIn("not compile pages", self.guide)
        self.assertIn("not a site compiler", self.guide.lower())
        self.assertIn("governed-publishing-starter", self.guide)
        self.assertIn("Deferred", self.guide)

    def test_guide_maps_to_existing_schemes_not_a_fifth_profile(self):
        self.assertIn("Not a fifth web-conformance profile", self.guide)
        self.assertIn("G0–G5 remains the only adoption sequence", self.guide)
        self.assertIn("TODO-PP-1", self.guide)
        self.assertIn("TODO-PP-2", self.guide)
        self.assertIn("TODO-PP-3", self.guide)
        self.assertIn("contracts/page_types.yaml", self.guide)
        self.assertIn("contracts/entity_lifecycle.yaml", self.guide)
        self.assertIn("contracts/claim_decision.yaml", self.guide)
        self.assertIn("contracts/promotion_protocol_v1.yaml", self.guide)
        self.assertIn("contracts/outcome_record.yaml", self.guide)

    def test_guide_states_portable_extraction_rules(self):
        self.assertIn("Indexability follows explicit page-family policy", self.guide)
        self.assertIn("Source failure cannot alone establish permanent", self.guide)
        self.assertIn("Not a portable rule", self.guide)
        self.assertIn("not “every page", self.guide)

    def test_guide_links_resolve(self):
        import re

        for match in re.finditer(r"\[[^\]]+\]\((?!https?://)([^)#]+)", self.guide):
            target = match.group(1)
            resolved = (DOCS / target).resolve()
            self.assertTrue(resolved.exists(), f"broken link {target}")

    def test_examples_index_lists_the_pack(self):
        index = (ROOT / "examples" / "README.md").read_text(encoding="utf-8")
        self.assertIn("programmatic-publishing", index)


class ExistingContractAlignmentTest(unittest.TestCase):
    def test_entity_lifecycle_still_forbids_source_failure_as_terminal(self):
        contract = load_yaml(CONTRACTS / "entity_lifecycle.yaml")
        forbidden = set(contract["terminal_transition"]["forbidden_triggers"])
        for trigger in (
            "evidence_source_returned_404",
            "evidence_source_timeout",
            "evidence_source_error",
            "no_recent_observation",
            "claim_absent",
        ):
            self.assertIn(trigger, forbidden)

    def test_page_health_still_separates_claim_suppression_from_body(self):
        contract = load_yaml(CONTRACTS / "page_health_resolver.yaml")
        ids = {item["id"] for item in contract["invariants"]}
        self.assertIn("claim_suppression_is_not_document_suppression", ids)
        self.assertIn("price_or_claim_suppression_not_noindex", ids)
        self.assertIn("unknown_is_not_unsupported", ids)

    def test_outcome_record_still_separates_delivery(self):
        contract = load_yaml(CONTRACTS / "outcome_record.yaml")
        ids = {item["id"] for item in contract["invariants"]}
        self.assertIn("delivery_is_not_outcome", ids)


if __name__ == "__main__":
    unittest.main()
