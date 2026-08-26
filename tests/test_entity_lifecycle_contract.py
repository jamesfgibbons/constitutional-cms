"""Conformance tests for contracts/entity_lifecycle.yaml.

Two halves, and the second is the one that matters.

The first half checks the contract says what it means to say. The second half
is an executable authority-collapse detector: a minimal reference resolver plus
the adversarial fixtures that a real production system failed. Any resolver can
be substituted for `reference_resolve` to audit an implementation against the
same cases.

The reason this file exists at all: page_health_resolver.yaml already carried
`unknown_is_not_unsupported`, and a production system violated it on 107 URLs
for months. The rule was right and unenforced. A contract with no detector is
a wish.
"""

import unittest
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
CONTRACTS = ROOT / "contracts"


def load_contract(name):
    with (CONTRACTS / name).open("r") as handle:
        return yaml.safe_load(handle)


# ---------------------------------------------------------------------------
# A minimal reference resolver.
#
# Deliberately tiny. Its whole job is to demonstrate that conformance is
# cheap once the layers are kept apart -- the entire defence is that
# `artifact_state` reads `lifecycle.terminal` and nothing else.
# ---------------------------------------------------------------------------
NON_TERMINAL = {
    "active",
    "seasonal_active",
    "seasonal_inactive",
    "launching",
    "suspended",
    "unknown",
}


def reference_resolve(entity):
    """entity -> {lifecycle_state, artifact_state, body_publishable, claims}

    `entity` carries a lifecycle block, zero or more relationships, zero or
    more claims, and optional failure injections.
    """
    lifecycle = entity.get("lifecycle") or {}
    state = lifecycle.get("state", "unknown")
    terminal = bool(lifecycle.get("terminal", False))

    # Terminality requires the full transition record. A state string alone is
    # not authority -- anyone can write "retired" into a dict.
    authorized_terminal = (
        state == "retired"
        and terminal
        and bool(lifecycle.get("lifecycle_authority"))
        and bool(lifecycle.get("evidence_reference"))
        and bool(lifecycle.get("reason_code"))
        and bool(lifecycle.get("effective_at"))
    )

    if authorized_terminal:
        artifact_state = "gone"
    elif state in NON_TERMINAL:
        artifact_state = "publish"
    else:
        # An unrecognised state is unknown, and unknown is never terminal.
        artifact_state = "publish"

    # Claim suppression is claim-scoped. It closes the claim it governs and no
    # sibling claim, and it never closes the document.
    claims = {
        name: claim
        for name, claim in (entity.get("claims") or {}).items()
        if claim.get("state") == "published"
    }
    body_publishable = artifact_state != "gone" and not entity.get("document_hold", False)

    return {
        "lifecycle_state": state,
        "artifact_state": artifact_state,
        "body_publishable": body_publishable,
        "claims": claims,
    }


# ---------------------------------------------------------------------------
# Fixtures. Each is a real shape from the 2026-08-26 incident, stripped of
# domain vocabulary.
# ---------------------------------------------------------------------------
def entity_with_everything():
    return {
        "id": "entity:reference",
        "lifecycle": {"state": "active", "terminal": False},
        "relationships": {"primary_service": {"state": "active"}},
        "claims": {
            "current_price": {"state": "published", "value": 812},
            "duration": {"state": "published", "value": 572},
            "distance": {"state": "published", "value": 4513},
            "endpoint_identity": {"state": "published", "value": "Reference City"},
        },
    }


def authorized_retirement():
    return {
        "id": "entity:retired",
        "lifecycle": {
            "state": "retired",
            "terminal": True,
            "lifecycle_authority": "entity_registry",
            "evidence_reference": "receipt:2026-08-26:retirement:0001",
            "reason_code": "withdrawn_by_operator",
            "effective_at": "2026-08-26T00:00:00Z",
        },
        "claims": {},
    }


class EntityLifecycleContractTest(unittest.TestCase):
    def setUp(self):
        self.contract = load_contract("entity_lifecycle.yaml")

    # -- the contract says what it means to say ----------------------------
    def test_retired_is_the_only_terminal_state(self):
        states = self.contract["lifecycle_states"]
        terminal = {name for name, cfg in states.items() if cfg.get("terminal")}
        self.assertEqual({"retired"}, terminal)

    def test_unknown_is_a_representable_state(self):
        # The state whose absence forces implementers to resolve every
        # unresolved lookup as either healthy or dead. They pick dead.
        self.assertIn("unknown", self.contract["lifecycle_states"])
        self.assertFalse(self.contract["lifecycle_states"]["unknown"]["terminal"])

    def test_terminal_transition_requires_authority_and_evidence(self):
        requires = self.contract["terminal_transition"]["requires"]
        required_keys = set()
        for item in requires:
            required_keys.update(item.keys() if isinstance(item, dict) else {item})
        for key in ("lifecycle_authority", "evidence_reference", "reason_code", "effective_at"):
            self.assertIn(key, required_keys)

    def test_evidence_failure_is_never_a_terminal_trigger(self):
        forbidden = set(self.contract["terminal_transition"]["forbidden_triggers"])
        for trigger in (
            "evidence_source_returned_404",
            "evidence_source_timeout",
            "relationship_absent",
            "relationship_seasonally_inactive",
            "lifecycle_state_unknown",
            "renderer_exception",
            "claim_suppressed",
        ):
            self.assertIn(trigger, forbidden)

    def test_only_retired_may_project_to_a_terminal_artifact(self):
        projection = self.contract["artifact_projection"]
        for state, cfg in projection.items():
            if state == "rules":
                continue
            with self.subTest(state=state):
                if state == "retired":
                    self.assertIn("gone", cfg["permitted"])
                else:
                    self.assertNotIn("gone", cfg["permitted"])

    def test_core_invariants_are_p0(self):
        severities = {inv["id"]: inv["severity"] for inv in self.contract["invariants"]}
        for invariant in (
            "identity_is_not_evidence",
            "entity_state_is_not_claim_state",
            "relationship_state_is_not_entity_state",
            "unknown_is_not_absent",
            "absent_is_not_terminal",
            "child_cannot_escalate_parent_to_terminal",
            "renderer_cannot_derive_lifecycle",
            "terminal_artifact_requires_terminal_authority",
        ):
            self.assertEqual("P0", severities[invariant], invariant)


class AuthorityCollapseDetectorTest(unittest.TestCase):
    """The adversarial half. Substitute your own resolver to audit it."""

    resolve = staticmethod(reference_resolve)

    # -- claim_absence_to_entity_absence -----------------------------------
    def test_removing_one_claim_does_not_retire_the_entity(self):
        entity = entity_with_everything()
        entity["claims"]["current_price"] = {"state": "withheld"}

        result = self.resolve(entity)

        self.assertEqual("active", result["lifecycle_state"])
        self.assertNotEqual("gone", result["artifact_state"])

    # -- claim_suppression_to_document_suppression -------------------------
    def test_suppressing_one_claim_does_not_suppress_its_siblings(self):
        """The EWR-BEG shape: a lapsed price silenced duration, distance and
        the destination's own name on a 200, indexable, 2,946-word page."""
        entity = entity_with_everything()
        entity["claims"]["current_price"] = {"state": "withheld"}

        result = self.resolve(entity)

        self.assertNotIn("current_price", result["claims"], "the suppressed claim must not leak")
        for sibling in ("duration", "distance", "endpoint_identity"):
            self.assertIn(sibling, result["claims"], f"{sibling} is governed elsewhere and must survive")
        self.assertTrue(result["body_publishable"])

    # -- child_404_to_parent_410 -------------------------------------------
    def test_child_source_failure_does_not_terminate_the_parent(self):
        for failure in ("http_404", "http_410", "timeout", "connection_error"):
            with self.subTest(failure=failure):
                entity = entity_with_everything()
                entity["claims"]["duration"] = {"state": "unavailable", "reason": failure}

                result = self.resolve(entity)

                self.assertNotEqual("gone", result["artifact_state"])
                self.assertEqual("active", result["lifecycle_state"])

    # -- relationship_absence_to_entity_terminal ---------------------------
    def test_absent_relationship_does_not_retire_either_endpoint(self):
        for relationship_state in ("absent", "seasonal_inactive", "suspended"):
            with self.subTest(relationship_state=relationship_state):
                entity = entity_with_everything()
                entity["relationships"]["primary_service"] = {"state": relationship_state}

                result = self.resolve(entity)

                self.assertNotEqual("gone", result["artifact_state"])
                self.assertTrue(result["body_publishable"])

    # -- unknown_to_terminal -----------------------------------------------
    def test_unknown_lifecycle_never_reaches_a_terminal_artifact(self):
        entity = entity_with_everything()
        entity["lifecycle"] = {"state": "unknown", "terminal": False}

        self.assertNotEqual("gone", self.resolve(entity)["artifact_state"])

    def test_unrecognised_lifecycle_state_is_treated_as_unknown_not_gone(self):
        # Fail-open on the ONE axis where fail-closed destroys something. A
        # resolver that has never heard of this state knows less than nothing
        # about it, and must not conclude removal.
        entity = entity_with_everything()
        entity["lifecycle"] = {"state": "state_invented_next_quarter", "terminal": False}

        self.assertNotEqual("gone", self.resolve(entity)["artifact_state"])

    def test_seasonal_inactive_is_dormant_not_dead(self):
        entity = entity_with_everything()
        entity["lifecycle"] = {"state": "seasonal_inactive", "terminal": False}

        result = self.resolve(entity)

        self.assertNotEqual("gone", result["artifact_state"])
        self.assertTrue(result["body_publishable"])

    # -- terminal_artifact_requires_terminal_authority ---------------------
    def test_authorized_retirement_does_produce_gone(self):
        """The inverse. A repair that can no longer express a real removal has
        replaced one authority failure with another."""
        self.assertEqual("gone", self.resolve(authorized_retirement())["artifact_state"])

    def test_retired_without_the_transition_record_is_not_terminal(self):
        for missing in ("lifecycle_authority", "evidence_reference", "reason_code", "effective_at"):
            with self.subTest(missing=missing):
                entity = authorized_retirement()
                del entity["lifecycle"][missing]

                self.assertNotEqual(
                    "gone",
                    self.resolve(entity)["artifact_state"],
                    f"terminality survived without {missing}; a state string is not authority",
                )

    def test_terminality_never_arrives_by_accumulation(self):
        """Every non-terminal failure at once. Severity does not become
        authority, however much of it there is."""
        entity = entity_with_everything()
        entity["lifecycle"] = {"state": "unknown", "terminal": False}
        entity["relationships"]["primary_service"] = {"state": "absent"}
        entity["claims"] = {
            "current_price": {"state": "withheld"},
            "duration": {"state": "unavailable", "reason": "http_404"},
            "distance": {"state": "stale"},
            "endpoint_identity": {"state": "unavailable", "reason": "timeout"},
        }

        self.assertNotEqual("gone", self.resolve(entity)["artifact_state"])


if __name__ == "__main__":
    unittest.main()
