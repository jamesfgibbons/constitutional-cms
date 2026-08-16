#!/usr/bin/env python3
"""Validate v0.4 web-conformance schemas, references, and public-safe examples."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator, FormatChecker


ROOT = Path(__file__).resolve().parents[1]


def load(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle) if path.suffix == ".json" else yaml.safe_load(handle)


def validate_schema(instance_path: Path, schema_path: Path) -> list[str]:
    validator = Draft202012Validator(load(schema_path), format_checker=FormatChecker())
    return [
        f"{instance_path.relative_to(ROOT)}: {error.message}"
        for error in sorted(validator.iter_errors(load(instance_path)), key=lambda item: list(item.path))
    ]


def walk_keys(value: Any, prefix: str = ""):
    if isinstance(value, dict):
        for key, child in value.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            yield path, str(key), child
            yield from walk_keys(child, path)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from walk_keys(child, f"{prefix}[{index}]")


def validate_manifest_public_safe(path: Path) -> list[str]:
    errors = []
    secret_pattern = re.compile(r"password|secret|token|api[_-]?key|private[_-]?key|connection[_-]?string", re.I)
    credential_pattern = re.compile(r"(?:postgres(?:ql)?|mysql|mongodb(?:\+srv)?|redis)://", re.I)
    for key_path, key, value in walk_keys(load(path)):
        if secret_pattern.search(key):
            errors.append(f"{path.relative_to(ROOT)}: secret-shaped key prohibited at {key_path}")
        if isinstance(value, str) and credential_pattern.search(value):
            errors.append(f"{path.relative_to(ROOT)}: connection material prohibited at {key_path}")
    return errors


def validate_catalog() -> list[str]:
    errors = []
    catalog = load(ROOT / "contracts/check_catalog_v1.yaml")
    registry = load(ROOT / "contracts/standards_registry_v1.yaml")
    source_ids = set(registry["sources"])
    check_ids = set()
    for check in catalog["checks"]:
        check_id = check["check_id"]
        if check_id in check_ids:
            errors.append(f"duplicate check_id: {check_id}")
        check_ids.add(check_id)
        unknown = set(check["authority_refs"]) - source_ids
        if unknown:
            errors.append(f"{check_id}: unknown authority refs {sorted(unknown)}")
        authority_classes = {
            registry["sources"][ref]["authority_class"] for ref in check["authority_refs"]
        }
        if "experimental" in authority_classes and check["certification_eligible"]:
            errors.append(f"{check_id}: experimental authority cannot be certification eligible")
        required = set(check["required_evidence"])
        applicability = set(check.get("applicability", {}).get("required_evidence", []))
        contracts = set(check["evidence_contracts"])
        missing_contracts = required.union(applicability) - contracts
        if missing_contracts:
            errors.append(f"{check_id}: evidence contracts missing {sorted(missing_contracts)}")
    return errors


def main() -> int:
    errors = []
    errors.extend(
        validate_schema(
            ROOT / "contracts/check_catalog_v1.yaml",
            ROOT / "schemas/check_catalog_v1.schema.json",
        )
    )
    for fixture in sorted((ROOT / "tests/fixtures/conformance").glob("*.yaml")):
        errors.extend(validate_schema(fixture, ROOT / "schemas/evidence_bundle_v1.schema.json"))
    for manifest in sorted((ROOT / "examples/manifests").glob("*.yaml")):
        errors.extend(validate_schema(manifest, ROOT / "schemas/constitutional_site_manifest_v1.schema.json"))
        errors.extend(validate_manifest_public_safe(manifest))
    link_target_schema = ROOT / "schemas/link_target_v1.schema.json"
    for target in load(ROOT / "examples/link-targets/static-routes.json"):
        validator = Draft202012Validator(load(link_target_schema), format_checker=FormatChecker())
        errors.extend(f"examples/link-targets/static-routes.json: {error.message}" for error in validator.iter_errors(target))
    errors.extend(
        validate_schema(
            ROOT / "examples/link-targets/link-graph.json",
            ROOT / "schemas/link_graph_evidence_v1.schema.json",
        )
    )
    link_graph = load(ROOT / "examples/link-targets/link-graph.json")
    target_validator = Draft202012Validator(load(link_target_schema), format_checker=FormatChecker())
    for record in [link_graph["source"], *link_graph["targets"]]:
        errors.extend(f"examples/link-targets/link-graph.json: {error.message}" for error in target_validator.iter_errors(record))
    errors.extend(validate_catalog())
    if errors:
        print("Web conformance validation failed:")
        for error in errors:
            print(f"  - {error}")
        return 1
    print("Web conformance schemas, references, and public-safe examples passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
