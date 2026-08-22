#!/usr/bin/env python3
"""Command-line interface for Constitutional CMS.

``constitutional-cms audit <url>`` runs the public recreate-a-check path end to end:
static collector → EvidenceBundleV1 → reference evaluator → ConformanceReceiptV1.
Verdicts are reported exactly as the evaluator produced them — PASS, FAIL,
UNMEASURED, NOT_APPLICABLE — with no synthetic score. Exit code is 1 when any
check FAILs, 0 when none do, 2 on operational errors.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from . import __version__
from . import collector, contracts_validator, evaluator

VERDICT_ORDER = ("PASS", "FAIL", "UNMEASURED", "NOT_APPLICABLE")

EXIT_OK = 0
EXIT_FAIL = 1
EXIT_ERROR = 2


def _load_catalog(catalog_arg: str | None) -> dict[str, Any]:
    if catalog_arg:
        return evaluator.load_data(Path(catalog_arg))
    return evaluator.load_default_catalog()


def _exit_code_for(receipt: dict[str, Any]) -> int:
    verdicts = {check["verdict"] for check in receipt["checks"]}
    return EXIT_FAIL if "FAIL" in verdicts else EXIT_OK


def _write_receipt(receipt: dict[str, Any], out: str | None, to_stdout: bool) -> None:
    payload = json.dumps(receipt, indent=2, sort_keys=True) + "\n"
    if out:
        Path(out).write_text(payload, encoding="utf-8")
    if to_stdout:
        print(payload, end="")


def _print_summary(receipt: dict[str, Any], catalog: dict[str, Any], limitations: list[str]) -> None:
    profiles = catalog.get("profiles", {})
    print("Constitutional CMS conformance audit")
    print(f"Subject:   {receipt['subject']['url']}")
    print(
        f"Catalog:   {receipt['catalog_version']} "
        f"(framework {receipt['framework_release']}) · evaluated {receipt['evaluated_at']}"
    )
    print()

    totals = {verdict: 0 for verdict in VERDICT_ORDER}
    for profile_id, summary in receipt["profile_summaries"].items():
        title = profiles.get(profile_id, {}).get("title", profile_id)
        print(f"{title}")
        for check in receipt["checks"]:
            if check["profile"] != profile_id:
                continue
            verdict = check["verdict"]
            totals[verdict] += 1
            note = "" if verdict == "PASS" else f"  ({check['reason_code']})"
            print(f"  {verdict:<15}{check['check_id']}{note}")
        print()

    coverage = receipt["evidence_coverage"]
    print(
        "Summary: "
        + " · ".join(f"{totals[verdict]} {verdict}" for verdict in VERDICT_ORDER)
        + f"  (measured {coverage['measured']} of {coverage['total_applicable']} applicable)"
    )
    print(
        "UNMEASURED means no honest evidence was collected for the check — "
        "it is neither a pass nor a failure."
    )
    if limitations:
        print("\nCollector limitations:")
        for limitation in limitations:
            print(f"  - {limitation}")
    print("\nFull receipt: rerun with --json (or --out receipt.json).")


def audit_command(args: argparse.Namespace) -> int:
    if bool(args.url) == bool(args.evidence):
        print("audit: provide exactly one subject — a URL, or --evidence <path>.", file=sys.stderr)
        return EXIT_ERROR

    try:
        catalog = _load_catalog(args.catalog)
    except (OSError, ValueError) as error:
        print(f"audit: could not load catalog: {error}", file=sys.stderr)
        return EXIT_ERROR

    if args.evidence:
        try:
            evidence = evaluator.load_data(Path(args.evidence))
            receipt = evaluator.evaluate(catalog, evidence, args.as_of)
        except (OSError, KeyError, TypeError, ValueError) as error:
            print(f"audit: {error}", file=sys.stderr)
            return EXIT_ERROR
        # Evidence-file mode is the machine pathway: always emit the receipt itself.
        _write_receipt(receipt, args.out, to_stdout=not args.out or args.json)
        return _exit_code_for(receipt)

    try:
        evidence = collector.collect(args.url, timeout=args.timeout)
        receipt = evaluator.evaluate(catalog, evidence, args.as_of)
    except collector.CollectorError as error:
        print(f"audit: {error}", file=sys.stderr)
        return EXIT_ERROR
    except (KeyError, TypeError, ValueError) as error:
        print(f"audit: {error}", file=sys.stderr)
        return EXIT_ERROR

    if args.json:
        _write_receipt(receipt, args.out, to_stdout=True)
    else:
        _write_receipt(receipt, args.out, to_stdout=False)
        _print_summary(receipt, catalog, evidence.get("limitations", []))
    return _exit_code_for(receipt)


def validate_command(args: argparse.Namespace) -> int:
    print("Running contract validation (internal consistency + web conformance)...")
    return contracts_validator.run(args.path, args.check)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="constitutional-cms",
        description="Constitutional CMS — a governance framework for AI agents that build websites",
    )
    parser.add_argument("--version", action="version", version=f"constitutional-cms {__version__}")

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    audit_parser = subparsers.add_parser(
        "audit",
        help="Audit a URL (or an evidence bundle) against the check catalog and emit a ConformanceReceiptV1",
    )
    audit_parser.add_argument(
        "url",
        nargs="?",
        help="Subject https:// URL. One read-only GET; unrendered static evidence only.",
    )
    audit_parser.add_argument(
        "--evidence",
        help="Path to a prepared EvidenceBundleV1 (YAML or JSON) instead of fetching a URL",
    )
    audit_parser.add_argument(
        "--catalog",
        help="Path to a CheckCatalogV1 (defaults to the catalog bundled with this release)",
    )
    audit_parser.add_argument("--as-of", help="RFC 3339 evaluation timestamp (defaults to evidence collected_at)")
    audit_parser.add_argument("--out", help="Write the JSON receipt to this path")
    audit_parser.add_argument("--json", action="store_true", help="Print the full JSON receipt to stdout")
    audit_parser.add_argument(
        "--timeout",
        type=float,
        default=collector.DEFAULT_TIMEOUT,
        help=f"Fetch timeout in seconds for URL audits (default: {collector.DEFAULT_TIMEOUT:g})",
    )

    validate_parser = subparsers.add_parser(
        "validate",
        help="Validate a local contracts directory for internal consistency",
    )
    validate_parser.add_argument(
        "path",
        nargs="?",
        default="./contracts",
        help="Path to a contracts directory (default: ./contracts)",
    )
    validate_parser.add_argument(
        "--check",
        choices=contracts_validator.CHECK_CHOICES,
        default="all",
        help="Which contract to validate (default: all)",
    )

    args = parser.parse_args(argv)

    if args.command == "audit":
        return audit_command(args)
    if args.command == "validate":
        return validate_command(args)
    parser.print_help()
    return EXIT_ERROR


if __name__ == "__main__":
    sys.exit(main())
