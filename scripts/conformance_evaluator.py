#!/usr/bin/env python3
"""Evaluate a normalized EvidenceBundleV1 against CheckCatalogV1.

The evaluator performs no network access. Private implementations remain private by
mapping their authorities into the public evidence shapes before invoking it.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import yaml
from jsonschema import Draft202012Validator, FormatChecker


ROOT = Path(__file__).resolve().parents[1]
MISSING = object()
EVALUATOR_VERSION = "constitutional-cms-reference/0.4.1"
REASON_CODES = {
    "evidence_missing",
    "evidence_stale",
    "evidence_invalid",
    "source_unavailable",
    "applicability_false",
    "rule_satisfied",
    "rule_falsified",
}


def load_data(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        if path.suffix.lower() == ".json":
            return json.load(handle)
        return yaml.safe_load(handle)


def canonical_json(value: Any) -> str:
    """Return the documented UTF-8 canonical JSON representation."""
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def parse_timestamp(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed.astimezone(timezone.utc)


def normalize_timestamp(value: str) -> str:
    parsed = parse_timestamp(value)
    if parsed is None:
        raise ValueError(f"Invalid RFC 3339 timestamp: {value}")
    return parsed.isoformat().replace("+00:00", "Z")


def value_at(document: dict[str, Any], dotted_path: str) -> Any:
    current: Any = document
    for part in dotted_path.split("."):
        if not isinstance(current, dict) or part not in current:
            return MISSING
        current = current[part]
    return current


def validate_instance(instance: dict[str, Any], schema_name: str, label: str) -> None:
    schema = json.loads((ROOT / "schemas" / schema_name).read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    errors = sorted(validator.iter_errors(instance), key=lambda error: list(error.path))
    if errors:
        details = "; ".join(
            f"{'.'.join(str(part) for part in error.path) or '<root>'}: {error.message}"
            for error in errors
        )
        raise ValueError(f"Invalid {label}: {details}")


def is_https_url(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    parsed = urlparse(value)
    return (
        parsed.scheme == "https"
        and bool(parsed.hostname)
        and parsed.username is None
        and parsed.password is None
    )


def origin_for(value: str) -> str | None:
    if not is_https_url(value):
        return None
    parsed = urlparse(value)
    port = f":{parsed.port}" if parsed.port else ""
    return f"{parsed.scheme}://{parsed.hostname}{port}"


def validate_link_graph(value: Any, evidence: dict[str, Any], as_of: datetime, max_age: int | None) -> str | None:
    """Return an evidence reason code when normalized link evidence is unusable."""
    if not isinstance(value, dict):
        return "evidence_invalid"
    try:
        validate_instance(value, "link_graph_evidence_v1.schema.json", "LinkGraphEvidenceV1")
        validate_instance(value["source"], "link_target_v1.schema.json", "LinkTargetV1 source")
        for index, target in enumerate(value["targets"]):
            validate_instance(target, "link_target_v1.schema.json", f"LinkTargetV1 target {index}")
    except ValueError:
        return "evidence_invalid"

    canonical_origin = value_at(evidence, "subject.canonical_origin")
    if canonical_origin is MISSING or not is_https_url(canonical_origin):
        return "evidence_invalid"
    expected_origin = origin_for(canonical_origin)
    if expected_origin != canonical_origin.rstrip("/"):
        return "evidence_invalid"

    records = [value["source"], *value["targets"]]
    for record in records:
        if origin_for(record["canonical_url"]) != expected_origin:
            return "evidence_invalid"
        observed_at = parse_timestamp(record["observed_at"])
        if observed_at is None or observed_at > as_of:
            return "evidence_invalid"
        if max_age is not None and (as_of - observed_at).total_seconds() > max_age:
            return "evidence_stale"
        redirect_chain = record.get("redirect_chain", [])
        if redirect_chain:
            if redirect_chain[-1] != record["canonical_url"]:
                return "evidence_invalid"
            if any(origin_for(url) != expected_origin for url in redirect_chain):
                return "evidence_invalid"

    seen: dict[str, str] = {}
    for target in value["targets"]:
        target_digest = digest(target)
        canonical_url = target["canonical_url"]
        if canonical_url in seen and seen[canonical_url] != target_digest:
            return "evidence_invalid"
        seen[canonical_url] = target_digest
    return None


def evidence_problem(
    path: str,
    contract: dict[str, Any],
    evidence: dict[str, Any],
    as_of: datetime,
) -> str | None:
    state = evidence.get("evidence_states", {}).get(path, {})
    status = state.get("status")
    value = value_at(evidence, path)

    if status == "unavailable":
        return "source_unavailable"
    if status == "stale":
        return "evidence_stale"
    if status == "invalid":
        return "evidence_invalid"
    if value is MISSING:
        return "evidence_missing"
    if status not in (None, "observed"):
        return "evidence_invalid"

    observed_at_value = state.get("observed_at", evidence["collected_at"])
    observed_at = parse_timestamp(observed_at_value)
    if observed_at is None or observed_at > as_of:
        return "evidence_invalid"
    max_age = contract.get("max_age_seconds")
    if max_age is not None and (as_of - observed_at).total_seconds() > max_age:
        return "evidence_stale"

    expected_type = contract["type"]
    valid = {
        "integer": isinstance(value, int) and not isinstance(value, bool),
        "number": isinstance(value, (int, float)) and not isinstance(value, bool),
        "string": isinstance(value, str),
        "boolean": isinstance(value, bool),
        "array": isinstance(value, list),
        "object": isinstance(value, dict),
        "https_url": is_https_url(value),
        "https_origin": isinstance(value, str) and is_https_url(value) and origin_for(value) == value.rstrip("/"),
        "link_graph": isinstance(value, dict),
    }.get(expected_type)
    if valid is not True:
        return "evidence_invalid"
    if expected_type == "link_graph":
        return validate_link_graph(value, evidence, as_of, max_age)
    return None


def evaluate_rule(rule: dict[str, Any], evidence: dict[str, Any]) -> bool:
    operator = rule["operator"]
    if operator == "all":
        return all(evaluate_rule(child, evidence) for child in rule.get("rules", []))

    value = value_at(evidence, rule.get("path", ""))
    if value is MISSING:
        return False
    if operator == "equals":
        return value == rule.get("expected")
    if operator == "nonempty":
        return isinstance(value, (str, list, dict)) and len(value) > 0
    if operator == "between":
        return isinstance(value, (int, float)) and not isinstance(value, bool) and rule["min"] <= value <= rule["max"]
    if operator == "lte":
        return isinstance(value, (int, float)) and not isinstance(value, bool) and value <= rule["expected"]
    if operator == "gte":
        return isinstance(value, (int, float)) and not isinstance(value, bool) and value >= rule["expected"]
    if operator == "https_url":
        return is_https_url(value)
    if operator == "link_graph_eligible":
        source = value["source"]
        unique_targets = {target["canonical_url"]: target for target in value["targets"]}
        return (
            source["outbound_eligible"] is True
            and all(
                target["exists"] is True
                and target["indexable"] is True
                and target["inbound_eligible"] is True
                and target["publication_tier"] != "SUPPRESS"
                for target in unique_targets.values()
            )
        )
    raise ValueError(f"Unsupported evaluator operator: {operator}")


def first_problem(paths: list[str], contracts: dict[str, Any], evidence: dict[str, Any], as_of: datetime) -> tuple[str, str] | None:
    for path in paths:
        problem = evidence_problem(path, contracts[path], evidence, as_of)
        if problem:
            return problem, path
    return None


def evaluate(catalog: dict[str, Any], evidence: dict[str, Any], as_of: str | None = None) -> dict[str, Any]:
    validate_instance(catalog, "check_catalog_v1.schema.json", "CheckCatalogV1")
    validate_instance(evidence, "evidence_bundle_v1.schema.json", "EvidenceBundleV1")

    as_of_value = normalize_timestamp(as_of or evidence["collected_at"])
    as_of_time = parse_timestamp(as_of_value)
    assert as_of_time is not None
    results: list[dict[str, Any]] = []
    profile_counts: dict[str, Counter[str]] = defaultdict(Counter)

    for check in catalog["checks"]:
        contracts = check["evidence_contracts"]
        applicability = check.get("applicability")
        if applicability:
            problem = first_problem(applicability["required_evidence"], contracts, evidence, as_of_time)
            if problem:
                reason_code, path = problem
                verdict = "UNMEASURED"
                detail = f"Applicability evidence is {reason_code}: {path}."
            elif not evaluate_rule(applicability["evaluation"], evidence):
                verdict = "NOT_APPLICABLE"
                reason_code = "applicability_false"
                detail = "Declared applicability condition is false."
            else:
                problem = first_problem(check["required_evidence"], contracts, evidence, as_of_time)
                if problem:
                    reason_code, path = problem
                    verdict = "UNMEASURED"
                    detail = f"Required evidence is {reason_code}: {path}."
                elif evaluate_rule(check["evaluation"], evidence):
                    verdict, reason_code, detail = "PASS", "rule_satisfied", "Required evidence satisfied the catalog rule."
                else:
                    verdict, reason_code, detail = "FAIL", "rule_falsified", "Required evidence falsified the catalog rule."
        else:
            problem = first_problem(check["required_evidence"], contracts, evidence, as_of_time)
            if problem:
                reason_code, path = problem
                verdict = "UNMEASURED"
                detail = f"Required evidence is {reason_code}: {path}."
            elif evaluate_rule(check["evaluation"], evidence):
                verdict, reason_code, detail = "PASS", "rule_satisfied", "Required evidence satisfied the catalog rule."
            else:
                verdict, reason_code, detail = "FAIL", "rule_falsified", "Required evidence falsified the catalog rule."

        assert reason_code in REASON_CODES
        profile_counts[check["profile"]][verdict] += 1
        results.append(
            {
                "check_id": check["check_id"],
                "profile": check["profile"],
                "verdict": verdict,
                "reason_code": reason_code,
                "certification_eligible": check["certification_eligible"],
                "evidence_scope": check["evidence_scope"],
                "remediation": check["remediation"],
                "detail": detail,
            }
        )

    summaries = {}
    for profile in catalog["profiles"]:
        counts = profile_counts[profile]
        summaries[profile] = {
            verdict: counts.get(verdict, 0)
            for verdict in ("PASS", "FAIL", "UNMEASURED", "NOT_APPLICABLE")
        }

    applicable = [item for item in results if item["verdict"] != "NOT_APPLICABLE"]
    measured = [item for item in applicable if item["verdict"] in {"PASS", "FAIL"}]
    evaluation_context = {
        "as_of": as_of_value,
        "catalog_digest": digest(catalog),
        "evidence_digest": digest(evidence),
        "evaluator_version": EVALUATOR_VERSION,
    }
    receipt = {
        "schema_version": "ConformanceReceiptV1",
        "framework_release": catalog["framework_release"],
        "catalog_version": catalog["catalog_version"],
        "subject": evidence["subject"],
        "evaluated_at": as_of_value,
        "evaluation_context": evaluation_context,
        "checks": results,
        "profile_summaries": summaries,
        "evidence_coverage": {
            "measured": len(measured),
            "total_applicable": len(applicable),
            "ratio": round(len(measured) / len(applicable), 6) if applicable else 0,
        },
        "limitations": evidence.get("limitations", []),
        "certified": False,
    }
    receipt["result_digest"] = digest(deepcopy(receipt))
    validate_instance(receipt, "conformance_receipt_v1.schema.json", "ConformanceReceiptV1")
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", default="contracts/check_catalog_v1.yaml")
    parser.add_argument("--evidence", required=True)
    parser.add_argument("--as-of", help="RFC 3339 evaluation clock; defaults to evidence collected_at")
    parser.add_argument("--out", help="Optional JSON receipt path")
    args = parser.parse_args()

    try:
        receipt = evaluate(load_data(Path(args.catalog)), load_data(Path(args.evidence)), args.as_of)
    except (KeyError, TypeError, ValueError) as error:
        parser.error(str(error))
    payload = json.dumps(receipt, indent=2, sort_keys=True) + "\n"
    if args.out:
        Path(args.out).write_text(payload, encoding="utf-8")
    else:
        print(payload, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
