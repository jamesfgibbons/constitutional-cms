"""Claim Drift reference detector — an application of existing contracts.

This module does not mint a second permission authority. Publication
permission is a ``claim_decision.yaml`` status (``publish`` / ``hold`` /
``suppress``). Integrity is Claim Gate. Existence is ``entity_lifecycle``.
Catalog audit is CheckCatalogV1. Delivery is per-surface inspection.

Mechanical replay only. No network. No model.
"""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import yaml

from .evaluator import evaluate as evaluate_catalog
from .evaluator import load_default_catalog


ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / "examples" / "claim-drift"
PROFILE_PATH = PACK / "assertion_profile_v0_1.yaml"
INVENTORY_PATH = PACK / "inventory.yaml"
FIXTURES = PACK / "fixtures"

PROFILE_VERSION = "0.1.0"
LIMITATION = "This claim is withheld pending current evidence."
REVIEW_HORIZON = timedelta(days=14)
SCOPE_KEYS = (
    "plan",
    "product_version",
    "region",
    "audience",
    "billing_period",
    "units",
    "release_stage",
)
NON_TERMINAL = {
    "active",
    "seasonal_active",
    "seasonal_inactive",
    "launching",
    "suspended",
    "unknown",
}
ADMITTED_SOURCE_CLASSES = {
    "canonical_snapshot",
    "verified_observation",
    "editorial_review",
}
FAILED_SOURCE = {"failed", "incomplete", "timeout", "error"}
GA_VALUES = {"ga", "current", "generally_available", "generally available"}
ROADMAP_VALUES = {"roadmap", "announced", "preview", "future"}


def _load_yaml(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def _load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def load_profile() -> dict[str, Any]:
    return _load_yaml(PROFILE_PATH)


def load_inventory() -> dict[str, Any]:
    return _load_yaml(INVENTORY_PATH)


def load_case(case_id: str) -> dict[str, Any]:
    slug = case_id.lower()
    path = FIXTURES / f"{slug}.yaml"
    if not path.is_file():
        path = FIXTURES / f"cd-{slug.removeprefix('cd-')}.yaml"
    return _load_yaml(path)


def _index(items: list[dict[str, Any]], key: str) -> dict[str, dict[str, Any]]:
    return {item[key]: item for item in items}


def _scope(item: dict[str, Any]) -> dict[str, Any]:
    return dict(item.get("scope") or {})


def _scopes_overlap(left: dict[str, Any], right: dict[str, Any]) -> bool:
    left_scope, right_scope = _scope(left), _scope(right)
    for key in SCOPE_KEYS:
        left_value, right_value = left_scope.get(key), right_scope.get(key)
        if left_value not in {None, ""} and right_value not in {None, ""} and left_value != right_value:
            return False
    return _intervals_overlap(left, right) and _intervals_overlap(left_scope, right_scope)


def _parse_time(value: Any) -> datetime | None:
    if not value or not isinstance(value, str):
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def _intervals_overlap(left: dict[str, Any], right: dict[str, Any]) -> bool:
    left_from = _parse_time(left.get("effective_from"))
    left_until = _parse_time(left.get("effective_until"))
    right_from = _parse_time(right.get("effective_from"))
    right_until = _parse_time(right.get("effective_until"))
    if left_from and right_until and left_from > right_until:
        return False
    if right_from and left_until and right_from > left_until:
        return False
    return True


def _needle(value: Any) -> str:
    return str(value).replace("_", " ").strip().lower()


def _read_evidence(item: dict[str, Any]) -> dict[str, Any]:
    record = deepcopy(item)
    path = item.get("path")
    text = ""
    digest = None
    inspectable = bool(item.get("inspectable")) and item.get("source_status") not in FAILED_SOURCE
    if path:
        source_path = PACK / path
        if source_path.is_file():
            raw = source_path.read_bytes()
            text = raw.decode("utf-8")
            digest = "sha256:" + hashlib.sha256(raw).hexdigest()
            inspectable = True and item.get("source_status") not in FAILED_SOURCE
        else:
            inspectable = False
    record["_text"] = text
    record["content_digest"] = digest
    record["inspectable"] = inspectable
    return record


def _mentions(evidence: dict[str, Any], value: Any) -> bool:
    needle = _needle(value)
    if not needle:
        return False
    text = (evidence.get("_text") or "").lower()
    return needle in text


def _authorized_terminal(lifecycle: dict[str, Any]) -> bool:
    return (
        lifecycle.get("state") == "retired"
        and bool(lifecycle.get("terminal"))
        and bool(lifecycle.get("lifecycle_authority"))
        and bool(lifecycle.get("evidence_reference"))
        and bool(lifecycle.get("reason_code"))
        and bool(lifecycle.get("effective_at"))
    )


def _resolve_entity(entity: dict[str, Any]) -> dict[str, Any]:
    lifecycle = entity.get("lifecycle") or {}
    state = lifecycle.get("state", "unknown")
    if _authorized_terminal(lifecycle):
        artifact_state = "gone"
    elif state in NON_TERMINAL or state != "retired":
        artifact_state = "publish"
    else:
        artifact_state = "publish"
    indexable = entity.get("indexability", "index") == "index"
    return {
        "lifecycle_state": state,
        "artifact_state": artifact_state,
        "retired": artifact_state == "gone",
        "indexable": indexable and artifact_state != "gone",
        "reason_codes": [],
    }


def _select(inventory: dict[str, Any], fixture: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    assertions = _index(inventory["assertions"], "claim_id")
    evidence = _index(inventory["evidence"], "evidence_id")
    entities = _index(inventory["entities"], "id")
    selected_assertions = [deepcopy(assertions[claim_id]) for claim_id in fixture["include_assertions"]]
    selected_evidence = [_read_evidence(evidence[evidence_id]) for evidence_id in fixture["include_evidence"]]
    for evidence_id, mutation in (fixture.get("evidence_mutations") or {}).items():
        for item in selected_evidence:
            if item["evidence_id"] == evidence_id:
                item.update({key: value for key, value in mutation.items() if key != "observed_at" and key != "effective_from"})
                # Re-apply frozen observation / effective clocks from inventory.
                item["observed_at"] = evidence[evidence_id].get("observed_at")
                item["effective_from"] = evidence[evidence_id].get("effective_from")
    mentioned_subjects = {item["subject"] for item in selected_assertions}
    selected_entities = [deepcopy(entities[entity_id]) for entity_id in mentioned_subjects if entity_id in entities]
    return selected_assertions, selected_evidence, selected_entities


def _verify_integrity(fixture: dict[str, Any]) -> dict[str, Any]:
    spec = fixture.get("integrity") or {}
    result = {
        "verdict": "NOT_PRESENTED",
        "ok": False,
        "reason_codes": [],
        "authenticated": False,
        "authorizes_publication": False,
    }
    mode = spec.get("mode")
    if not mode or mode == "none":
        return result
    from .claims import verify_bundle, verify_receipt

    as_of = spec.get("as_of")
    if mode == "bundle":
        bundle = _load_json(ROOT / spec["bundle_path"])
        keys = _load_json(ROOT / spec["keys_path"])
        verified = verify_bundle(bundle, keys, as_of=as_of)
        result.update(
            {
                "verdict": verified.verdict,
                "ok": verified.ok,
                "reason_codes": list(verified.reason_codes),
                "authenticated": verified.ok,
                "authorizes_publication": False,
                "detail": verified.detail,
            }
        )
        return result
    if mode == "receipt_only":
        receipt = _load_json(ROOT / spec["receipt_path"])
        verified = verify_receipt(receipt, current=True, as_of=as_of)
        result.update(
            {
                "verdict": verified.verdict,
                "ok": False,
                "reason_codes": ["receipt_unauthenticated", *list(verified.reason_codes)],
                "authenticated": False,
                "authorizes_publication": False,
                "detail": "v0.1 receipt is unauthenticated; it cannot prove issuance or support",
            }
        )
        return result
    return result


def _run_audit(fixture: dict[str, Any]) -> dict[str, Any]:
    spec = fixture.get("audit") or {}
    result = {"exit_code": None, "receipt_generated": False, "authorizes_publication": False}
    if not spec:
        return result
    evidence = _load_yaml(ROOT / spec["evidence_path"])
    receipt = evaluate_catalog(load_default_catalog(), evidence, as_of=spec.get("as_of"))
    result.update(
        {
            "exit_code": 0,
            "receipt_generated": receipt.get("schema_version") == "ConformanceReceiptV1",
            "authorizes_publication": False,
            "framework_release": receipt.get("framework_release"),
        }
    )
    return result


def _historical_artifact(fixture: dict[str, Any]) -> dict[str, Any] | None:
    spec = fixture.get("historical_artifact")
    if not spec:
        return None
    from .claims import verify_receipt

    receipt = _load_json(ROOT / spec["receipt_path"])
    original_hash = receipt.get("receipt_hash")
    verified = verify_receipt(receipt, current=bool(spec.get("current")), as_of=spec.get("as_of"))
    return {
        "intact": receipt.get("receipt_hash") == original_hash,
        "historically_verifiable": verified.ok or "receipt_verified" in verified.reason_codes or verified.verdict in {"PASS", "UNMEASURED"},
        "represents_current_state": False,
        "receipt_hash": original_hash,
    }


def _support_one(
    assertion: dict[str, Any],
    assertions: list[dict[str, Any]],
    evidence_items: list[dict[str, Any]],
) -> dict[str, Any]:
    reasons: list[str] = []
    by_id = _index(evidence_items, "evidence_id")
    supporting = [by_id[item] for item in assertion.get("supporting_evidence") or [] if item in by_id]
    conflicting = [by_id[item] for item in assertion.get("conflicting_evidence") or [] if item in by_id]
    observed = list(supporting)
    for item in evidence_items:
        if item in observed:
            continue
        if item.get("authority_class") == "competitor_marketing" and (
            _mentions(item, assertion.get("value")) or _mentions(item, assertion.get("assertion_text"))
        ):
            observed.append(item)
    inspectable_support = [item for item in supporting if item.get("inspectable") and item.get("source_status") not in FAILED_SOURCE]
    failed = [item for item in supporting if item.get("source_status") in FAILED_SOURCE or not item.get("inspectable")]

    origins = {item.get("origin_id") for item in observed if item.get("origin_id")}
    independent = len(origins)
    if independent == 1 and len(observed) > 1:
        reasons.append("common_origin_not_independent")

    if assertion.get("paraphrase_of"):
        original = next((item for item in assertions if item["claim_id"] == assertion["paraphrase_of"]), None)
        if original is not None:
            inherited = _support_one(original, [item for item in assertions if item["claim_id"] != assertion["claim_id"]], evidence_items)
            inherited["reason_codes"] = list(dict.fromkeys([*inherited["reason_codes"], "paraphrase_without_strengthening"]))
            return inherited

    if assertion.get("source_authority_policy") == "measured_reliability" and not assertion.get("reliability_method"):
        return {
            "verdict": "UNSUPPORTED",
            "reason_codes": ["insufficient_evidence"],
            "inspectable": bool(inspectable_support),
            "independent_source_count": independent,
        }

    wanted_stage = _needle((_scope(assertion).get("release_stage") or assertion.get("value") or ""))
    if wanted_stage in GA_VALUES or _needle(assertion.get("value")) in GA_VALUES:
        if supporting and all(
            _needle((_scope(item).get("release_stage"))) in ROADMAP_VALUES or _needle(item.get("scope", {}).get("release_stage")) in ROADMAP_VALUES
            for item in supporting
        ):
            reasons.append("roadmap_is_not_ga")
            return {
                "verdict": "UNSUPPORTED",
                "reason_codes": list(dict.fromkeys(reasons)),
                "inspectable": bool(inspectable_support),
                "independent_source_count": independent,
            }

    if failed and not inspectable_support:
        reasons.extend(["evidence_unmeasured", "source_missing"])
        if any(not item.get("inspectable") for item in supporting):
            reasons.append("evidence_not_inspectable")
        return {
            "verdict": "UNMEASURED",
            "reason_codes": list(dict.fromkeys(reasons)),
            "inspectable": False,
            "independent_source_count": independent,
        }

    product_docs = [
        item
        for item in evidence_items
        if item.get("authority_class") == "product_documentation" and item.get("inspectable")
    ]
    docs_contradict_universal = False
    if assertion.get("scope_explicitly_universal") and assertion.get("polarity") == "denies":
        for item in product_docs:
            if _mentions(item, assertion.get("value")) and ("available" in item.get("_text", "").lower() or "included" in item.get("_text", "").lower()):
                docs_contradict_universal = True
        for other in assertions:
            if other["claim_id"] == assertion["claim_id"]:
                continue
            if (
                other.get("subject") == assertion.get("subject")
                and other.get("predicate") == assertion.get("predicate")
                and other.get("value") == assertion.get("value")
                and other.get("polarity") == "affirms"
            ):
                docs_contradict_universal = True
        if docs_contradict_universal or conflicting:
            reasons.append("universal_denied_by_qualified_support")
            return {
                "verdict": "UNSUPPORTED",
                "reason_codes": list(dict.fromkeys(reasons)),
                "inspectable": True,
                "independent_source_count": independent,
            }

    if assertion.get("source_authority_policy") == "competitor_marketing":
        if conflicting or docs_contradict_universal:
            reasons.append("source_conflict")
            return {
                "verdict": "UNSUPPORTED",
                "reason_codes": list(dict.fromkeys(reasons)),
                "inspectable": bool(inspectable_support),
                "independent_source_count": independent,
            }
        reasons.append("evidence_unmeasured")
        return {
            "verdict": "UNMEASURED",
            "reason_codes": list(dict.fromkeys(reasons)),
            "inspectable": bool(inspectable_support),
            "independent_source_count": independent,
        }

    if assertion.get("source_authority_policy") == "customer_report" and inspectable_support:
        reasons.append("attributed_experience_retained")
        return {
            "verdict": "SUPPORTED",
            "reason_codes": list(dict.fromkeys(reasons)),
            "inspectable": True,
            "independent_source_count": independent,
        }

    if inspectable_support:
        for other in assertions:
            if other["claim_id"] == assertion["claim_id"]:
                continue
            if other.get("subject") == assertion.get("subject") and other.get("predicate") == assertion.get("predicate"):
                if not _scopes_overlap(assertion, other):
                    reasons.append("scope_mismatch_not_contradiction")
        return {
            "verdict": "SUPPORTED",
            "reason_codes": list(dict.fromkeys(reasons)),
            "inspectable": True,
            "independent_source_count": independent,
        }

    if conflicting:
        return {
            "verdict": "UNSUPPORTED",
            "reason_codes": list(dict.fromkeys([*reasons, "source_conflict"])),
            "inspectable": True,
            "independent_source_count": independent,
        }

    return {
        "verdict": "UNMEASURED",
        "reason_codes": list(dict.fromkeys([*reasons, "evidence_unmeasured"])),
        "inspectable": False,
        "independent_source_count": independent,
    }


def _qualifiers_present(text: str, required: list[str]) -> bool:
    lowered = text.lower()
    return all(part.lower() in lowered for part in required)


def _override_text(fixture: dict[str, Any], claim_id: str, surface: str) -> str | None:
    overrides = (fixture.get("projection_overrides") or {}).get(claim_id) or {}
    value = overrides.get(surface)
    return value if isinstance(value, str) else None


def _source_class_for(assertion: dict[str, Any], evidence_items: list[dict[str, Any]]) -> str:
    by_id = _index(evidence_items, "evidence_id")
    for evidence_id in assertion.get("supporting_evidence") or []:
        item = by_id.get(evidence_id)
        if item:
            return item.get("source_class") or "unknown"
    return "unknown"


def _decide_publication(
    assertion: dict[str, Any],
    support: dict[str, Any],
    fixture: dict[str, Any],
    integrity: dict[str, Any],
    audit: dict[str, Any],
    evidence_items: list[dict[str, Any]],
) -> dict[str, Any]:
    reasons: list[str] = []
    claim_id = assertion["claim_id"]
    source_class = _source_class_for(assertion, evidence_items)
    confidence = "high" if support["verdict"] == "SUPPORTED" else "unknown"
    decided_at = fixture["as_of"]

    serving = (fixture.get("serving_decision_ids") or {}).get(claim_id)
    current = (fixture.get("current_decision_ids") or {}).get(claim_id)
    if serving and current and serving != current:
        reasons.append("obsolete_permission")

    required = list(assertion.get("required_qualifications") or [])
    dropped = False
    for surface in ("html", "sales_answer", "api"):
        override = _override_text(fixture, claim_id, surface)
        if override is not None and required and not _qualifiers_present(override, required):
            dropped = True
    if dropped:
        reasons.append("qualifier_dropped")

    if assertion.get("favors_subject") and support["verdict"] != "SUPPORTED":
        reasons.append("same_evidentiary_standard")

    if integrity.get("ok") or integrity.get("verdict") == "PASS":
        reasons.append("integrity_is_not_permission")

    if audit.get("receipt_generated") and support["verdict"] == "UNMEASURED":
        reasons.append("audit_is_not_permission")

    if assertion.get("paraphrase_of") and support["verdict"] == "SUPPORTED" and not dropped:
        reasons.append("paraphrase_without_strengthening")

    status = "hold"
    if dropped or "obsolete_permission" in reasons:
        status = "suppress"
    elif support["verdict"] == "SUPPORTED" and source_class in ADMITTED_SOURCE_CLASSES and not dropped:
        status = "publish"
        confidence = "high"
    elif support["verdict"] == "UNSUPPORTED":
        status = "suppress"
        reasons.append("insufficient_evidence" if "source_conflict" not in support["reason_codes"] else "source_conflict")
    elif support["verdict"] == "UNMEASURED":
        status = "hold"
        reasons.append("editorial_hold")

    if status == "publish" and "obsolete_permission" in reasons:
        status = "suppress"

    return {
        "status": status,
        "reason_codes": list(dict.fromkeys(reasons)),
        "confidence": confidence,
        "source_class": source_class,
        "decided_at": decided_at,
        "source_id": (assertion.get("supporting_evidence") or [None])[0],
    }


def _render(assertions: list[dict[str, Any]], publication: dict[str, dict[str, Any]], fixture: dict[str, Any]) -> dict[str, Any]:
    html_parts = ["<article>"]
    sales_parts: list[str] = []
    api_claims: dict[str, Any] = {}
    for assertion in assertions:
        claim_id = assertion["claim_id"]
        decision = publication[claim_id]
        permitted = set(assertion.get("permitted_projections") or ["html", "sales_answer", "api"])
        text = assertion["assertion_text"]
        if decision["status"] == "publish":
            if "html" in permitted:
                html_parts.append(f'<p data-claim="{claim_id}">{text}</p>')
            if "sales_answer" in permitted:
                sales_parts.append(text)
            if "api" in permitted:
                payload = {
                    "status": "publish",
                    "value": assertion.get("value"),
                    "source_id": decision.get("source_id"),
                    "reason_codes": decision["reason_codes"],
                }
                if assertion.get("required_qualifications"):
                    payload["qualifications"] = list(assertion["required_qualifications"])
                api_claims[claim_id] = payload
        else:
            if assertion.get("expected_by_users") and "html" in permitted:
                html_parts.append(f'<p data-claim="{claim_id}" class="limitation">{LIMITATION}</p>')
            if "api" in permitted:
                api_claims[claim_id] = {
                    "status": decision["status"],
                    "reason_codes": decision["reason_codes"],
                    "source_id": decision.get("source_id"),
                }
    html_parts.append("</article>")
    return {
        "html": "\n".join(html_parts),
        "sales_answer": " ".join(sales_parts),
        "api": {"claims": api_claims},
    }


def _normalize(value: Any) -> str:
    if isinstance(value, (dict, list)):
        return json.dumps(value, sort_keys=True, separators=(",", ":"))
    return " ".join(str(value).split())


def _inspect_delivery(projections: dict[str, Any], fixture: dict[str, Any], publication: dict[str, dict[str, Any]], assertions: list[dict[str, Any]]) -> dict[str, Any]:
    served = fixture.get("served") or fixture.get("served_after") or {}
    enrolled = list(fixture.get("enrolled_surfaces") or ["html", "sales_answer", "api"])
    surfaces: dict[str, Any] = {}
    reasons: list[str] = []
    failing: list[str] = []
    by_id = _index(assertions, "claim_id")
    for surface in enrolled:
        expected = projections[surface]
        observed = served.get(surface) or {}
        body = observed.get("body", expected)
        status = "verified"
        if served:
            if surface == "api":
                observed_claims = (body or {}).get("claims") if isinstance(body, dict) else {}
                for claim_id, decision in publication.items():
                    shown = (observed_claims or {}).get(claim_id) or {}
                    if decision["status"] != "publish" and shown.get("status") == "publish":
                        status = "stale"
                    if decision["status"] == "publish":
                        assertion = by_id[claim_id]
                        if shown.get("status") not in {None, "publish"} and assertion["assertion_text"] not in _normalize(body):
                            status = "stale"
                if status == "verified" and _normalize(body) != _normalize(expected) and observed:
                    # A cached payload that still publishes a withheld claim is stale even if shapes differ.
                    if any(
                        (item.get("status") == "publish" and publication.get(claim_id, {}).get("status") != "publish")
                        for claim_id, item in (observed_claims or {}).items()
                    ):
                        status = "stale"
            else:
                text = _normalize(body)
                expected_text = _normalize(expected)
                if text != expected_text:
                    # Still verified if every published claim text is present and withheld texts are absent.
                    missing = [
                        assertion["assertion_text"]
                        for assertion in assertions
                        if publication[assertion["claim_id"]]["status"] == "publish"
                        and "html" in (assertion.get("permitted_projections") or ["html"])
                        and surface == "html"
                        and assertion["assertion_text"] not in text
                    ]
                    leaked = [
                        assertion["assertion_text"]
                        for assertion in assertions
                        if publication[assertion["claim_id"]]["status"] != "publish"
                        and assertion["assertion_text"] in text
                    ]
                    if surface == "sales_answer":
                        missing = [
                            assertion["assertion_text"]
                            for assertion in assertions
                            if publication[assertion["claim_id"]]["status"] == "publish"
                            and "sales_answer" in (assertion.get("permitted_projections") or [])
                            and assertion["assertion_text"] not in text
                        ]
                    if missing or leaked:
                        status = "stale"
                    elif expected_text in text or all(
                        assertion["assertion_text"] in text
                        for assertion in assertions
                        if publication[assertion["claim_id"]]["status"] == "publish"
                        and surface in (assertion.get("permitted_projections") or [])
                    ):
                        status = "verified"
                    else:
                        status = "stale"
        if status == "stale":
            failing.append(surface)
            reasons.append("delivery_surface_stale")
        surfaces[surface] = {"status": status, "body": body if served else expected}
    acceptance = "incomplete" if failing else "complete"
    return {
        "surfaces": surfaces,
        "acceptance": acceptance,
        "failing_or_unmeasured_surfaces": failing,
        "enrolled_denominator": len(enrolled),
        "reason_codes": list(dict.fromkeys(reasons)),
    }


def _clocks(fixture: dict[str, Any], evidence_items: list[dict[str, Any]]) -> dict[str, Any]:
    evidence_clocks = {}
    review_deadline = None
    for item in evidence_items:
        observed = item.get("observed_at")
        evidence_clocks[item["evidence_id"]] = {
            "observed_at": observed,
            "retrieved_at": item.get("retrieved_at"),
            "effective_from": item.get("effective_from"),
            "page_modified_at": fixture.get("page_modified_at") or item.get("page_modified_at"),
            "content_digest": item.get("content_digest"),
        }
        parsed = _parse_time(observed)
        if parsed is not None:
            deadline = (parsed + REVIEW_HORIZON).strftime("%Y-%m-%dT%H:%M:%SZ")
            if review_deadline is None:
                review_deadline = deadline
    if fixture.get("review_deadline_before"):
        review_deadline = fixture["review_deadline_before"]
    return {
        "evaluation": fixture["as_of"],
        "evidence": evidence_clocks,
        "page_modified_at": fixture.get("page_modified_at"),
        "rendered_at": fixture.get("render_again_at") or fixture["as_of"],
        "review_deadline": review_deadline,
    }


def _policy_authority(fixture: dict[str, Any]) -> dict[str, Any]:
    instruction = fixture.get("source_instruction")
    if not instruction:
        return {"changed": False, "source_treated_as": "untrusted_evidence", "reason_codes": []}
    return {
        "changed": False,
        "source_treated_as": "untrusted_evidence",
        "reason_codes": ["source_instruction_untrusted"],
        "text": instruction.get("text"),
    }


def evaluate_case(case: str | dict[str, Any], *, inventory: dict[str, Any] | None = None, profile: dict[str, Any] | None = None) -> dict[str, Any]:
    """Evaluate one frozen case. ``case`` is a CD id or a loaded fixture."""
    fixture = load_case(case) if isinstance(case, str) else deepcopy(case)
    inventory = inventory or load_inventory()
    profile = profile or load_profile()
    assertions, evidence_items, entities = _select(inventory, fixture)
    integrity = _verify_integrity(fixture)
    audit = _run_audit(fixture)
    support = {
        assertion["claim_id"]: _support_one(assertion, assertions, evidence_items) for assertion in assertions
    }
    publication = {
        assertion["claim_id"]: _decide_publication(
            assertion, support[assertion["claim_id"]], fixture, integrity, audit, evidence_items
        )
        for assertion in assertions
    }
    projections = _render(assertions, publication, fixture)
    delivery = _inspect_delivery(projections, fixture, publication, assertions)
    entity_results = {}
    for entity in entities:
        resolved = _resolve_entity(entity)
        withheld = any(
            publication[assertion["claim_id"]]["status"] in {"hold", "suppress"}
            and assertion["subject"] == entity["id"]
            for assertion in assertions
        )
        if withheld:
            resolved["reason_codes"].append("claim_withheld_entity_intact")
            resolved["retired"] = False
            resolved["lifecycle_state"] = entity.get("lifecycle", {}).get("state", "active")
            resolved["artifact_state"] = "publish"
            resolved["indexable"] = True
        entity_results[entity["id"]] = resolved
    historical = _historical_artifact(fixture)
    result = {
        "case_id": fixture["case_id"],
        "profile_version": profile.get("version", PROFILE_VERSION),
        "as_of": fixture["as_of"],
        "layers": {
            "integrity": integrity,
            "evidence_support": support,
            "publication": publication,
            "delivery": delivery,
        },
        "entities": entity_results,
        "projections": projections,
        "clocks": _clocks(fixture, evidence_items),
        "audit": audit,
        "policy_authority": _policy_authority(fixture),
    }
    if historical is not None:
        result["historical_artifact"] = historical
    return result


def evaluate_revision(case: str | dict[str, Any], *, inventory: dict[str, Any] | None = None, profile: dict[str, Any] | None = None) -> dict[str, Any]:
    """Section-7 sequence: source revision through per-surface delivery."""
    fixture = load_case(case) if isinstance(case, str) else deepcopy(case)
    inventory = inventory or load_inventory()
    profile = profile or load_profile()
    before_fix = {
        "case_id": f"{fixture['case_id']}-before",
        "as_of": fixture["as_of"],
        **fixture["before"],
    }
    after_fix = {
        "case_id": f"{fixture['case_id']}-after",
        "as_of": fixture["as_of"],
        **fixture["after"],
        "served": fixture.get("served_after"),
        "enrolled_surfaces": fixture.get("enrolled_surfaces"),
    }
    before = evaluate_case(before_fix, inventory=inventory, profile=profile)
    after = evaluate_case(after_fix, inventory=inventory, profile=profile)
    affected = []
    claim_ids = set(before["layers"]["publication"]) | set(after["layers"]["publication"])
    for claim_id in claim_ids:
        before_status = (before["layers"]["publication"].get(claim_id) or {}).get("status")
        after_status = (after["layers"]["publication"].get(claim_id) or {}).get("status")
        before_support = (before["layers"]["evidence_support"].get(claim_id) or {}).get("verdict")
        after_support = (after["layers"]["evidence_support"].get(claim_id) or {}).get("verdict")
        if before_status != after_status or before_support != after_support:
            affected.append(claim_id)
    revision = (fixture.get("after") or {}).get("source_revision") or {}
    return {
        "case_id": fixture["case_id"],
        "sequence": [
            "source_revision",
            "affected_claims_identified",
            "permission_re_evaluated",
            "artifacts_rebuilt_or_withheld",
            "surfaces_inspected",
            "delivery_outcome_recorded",
        ],
        "affected_claims": affected,
        "before": before,
        "after": after,
        "owner": fixture.get("owner"),
        "enrolled_denominator": len(fixture.get("enrolled_surfaces") or ["html", "sales_answer", "api"]),
        "versions": {
            "policy": (revision.get("artifact_versions") or {}).get("policy"),
            "evidence": (revision.get("artifact_versions") or {}).get("evidence") or revision.get("to"),
            "assertion": (revision.get("artifact_versions") or {}).get("assertion"),
        },
    }
