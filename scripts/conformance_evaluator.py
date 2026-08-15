#!/usr/bin/env python3
"""Evaluate a normalized EvidenceBundleV1 against CheckCatalogV1.

The evaluator performs no network access. Private implementations remain private by
mapping their authorities into the public evidence shapes before invoking it.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import yaml


MISSING = object()


def load_data(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        if path.suffix.lower() == ".json":
            return json.load(handle)
        return yaml.safe_load(handle)


def value_at(document: dict[str, Any], dotted_path: str) -> Any:
    current: Any = document
    for part in dotted_path.split("."):
        if not isinstance(current, dict) or part not in current:
            return MISSING
        current = current[part]
    return current


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
        return isinstance(value, (int, float)) and rule["min"] <= value <= rule["max"]
    if operator == "lte":
        return isinstance(value, (int, float)) and value <= rule["expected"]
    if operator == "gte":
        return isinstance(value, (int, float)) and value >= rule["expected"]
    if operator == "https_url":
        if not isinstance(value, str):
            return False
        parsed = urlparse(value)
        return parsed.scheme == "https" and bool(parsed.netloc) and not parsed.username and not parsed.password
    if operator == "link_targets_eligible":
        if not isinstance(value, list) or not value:
            return False
        required = {
            "canonical_url",
            "exists",
            "page_family",
            "publication_tier",
            "indexable",
            "inbound_eligible",
            "outbound_eligible",
            "observed_at",
            "authority_id",
        }
        return all(
            isinstance(target, dict)
            and required.issubset(target)
            and target["exists"] is True
            and target["inbound_eligible"] is True
            and target["publication_tier"] != "SUPPRESS"
            and evaluate_rule(
                {"path": "target.canonical_url", "operator": "https_url"},
                {"target": target},
            )
            for target in value
        )
    raise ValueError(f"Unsupported evaluator operator: {operator}")


def evaluate(catalog: dict[str, Any], evidence: dict[str, Any]) -> dict[str, Any]:
    results: list[dict[str, Any]] = []
    profile_counts: dict[str, Counter[str]] = defaultdict(Counter)

    for check in catalog["checks"]:
        missing = [path for path in check["required_evidence"] if value_at(evidence, path) is MISSING]
        if missing:
            verdict = "UNMEASURED"
            detail = "Missing required evidence: " + ", ".join(missing)
        elif "applicability" in check and not evaluate_rule(check["applicability"], evidence):
            verdict = "NOT_APPLICABLE"
            detail = "Declared applicability condition is false."
        elif evaluate_rule(check["evaluation"], evidence):
            verdict = "PASS"
            detail = "Required evidence satisfied the catalog rule."
        else:
            verdict = "FAIL"
            detail = "Required evidence falsified the catalog rule."

        profile_counts[check["profile"]][verdict] += 1
        results.append(
            {
                "check_id": check["check_id"],
                "profile": check["profile"],
                "verdict": verdict,
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
    return {
        "schema_version": "ConformanceReceiptV1",
        "framework_release": catalog["framework_release"],
        "catalog_version": catalog["catalog_version"],
        "subject": evidence["subject"],
        "evaluated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
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


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", default="contracts/check_catalog_v1.yaml")
    parser.add_argument("--evidence", required=True)
    parser.add_argument("--out", help="Optional JSON receipt path")
    args = parser.parse_args()

    receipt = evaluate(load_data(Path(args.catalog)), load_data(Path(args.evidence)))
    payload = json.dumps(receipt, indent=2, sort_keys=True) + "\n"
    if args.out:
        Path(args.out).write_text(payload, encoding="utf-8")
    else:
        print(payload, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
