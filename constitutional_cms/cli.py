#!/usr/bin/env python3
"""Command-line interface for Constitutional CMS.

The website inspects a public URL after publication. This CLI evaluates
normalized evidence (or an optional static GET) against the same catalog
and writes a ConformanceReceiptV1.

Default ``audit`` is receipt-first: it writes a valid receipt and exits 0.
CI that should block a release must pass ``--fail-on FAIL`` (or
``--fail-on FAIL,UNMEASURED``). Operational errors still exit 2.
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
FAIL_ON_CHOICES = set(VERDICT_ORDER)

EXIT_OK = 0
EXIT_FAIL = 1
EXIT_ERROR = 2


def _load_catalog(catalog_arg: str | None) -> dict[str, Any]:
    if catalog_arg:
        return evaluator.load_data(Path(catalog_arg))
    return evaluator.load_default_catalog()


def parse_fail_on(value: str | None) -> set[str]:
    """Parse ``--fail-on FAIL,UNMEASURED`` into a set of verdict names."""
    if not value:
        return set()
    items = {part.strip().upper() for part in value.split(",") if part.strip()}
    unknown = items - FAIL_ON_CHOICES
    if unknown:
        allowed = ", ".join(VERDICT_ORDER)
        raise ValueError(f"unknown --fail-on verdicts {sorted(unknown)}; allowed: {allowed}")
    return items


def exit_code_for(receipt: dict[str, Any], fail_on: set[str]) -> int:
    """Receipt-first: exit 0 unless an opted-in verdict is present."""
    if not fail_on:
        return EXIT_OK
    verdicts = {check["verdict"] for check in receipt["checks"]}
    return EXIT_FAIL if verdicts & fail_on else EXIT_OK


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
    print(f"Package:   constitutional-cms {__version__} · certified {receipt['certified']}")
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
        "it is neither a pass nor a failure, and not a composite rating."
    )
    if limitations:
        print("\nCollector limitations:")
        for limitation in limitations:
            print(f"  - {limitation}")
    print("\nFull receipt: rerun with --json (or --out receipt.json).")
    print("CI gate: add --fail-on FAIL to exit 1 when a catalog check fails.")


def audit_command(args: argparse.Namespace) -> int:
    if bool(args.url) == bool(args.evidence):
        print("audit: provide exactly one subject — --evidence <path>, or a URL.", file=sys.stderr)
        return EXIT_ERROR

    try:
        fail_on = parse_fail_on(args.fail_on)
    except ValueError as error:
        print(f"audit: {error}", file=sys.stderr)
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
        return exit_code_for(receipt, fail_on)

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
    return exit_code_for(receipt, fail_on)


def validate_command(args: argparse.Namespace) -> int:
    print("Validating bundled catalog and schemas...")
    packaged = contracts_validator.run_packaged()
    path = args.path
    if path is None:
        default = Path("contracts")
        path = str(default) if default.is_dir() else None
    if path is None:
        return packaged
    print("\nValidating local contracts directory...")
    local = contracts_validator.run(path, args.check)
    return EXIT_FAIL if packaged or local else EXIT_OK


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="constitutional-cms",
        description=(
            "Constitutional CMS — publishing governance for AI-built websites. "
            "Evaluate evidence against the public catalog and produce a receipt."
        ),
    )
    parser.add_argument("--version", action="version", version=f"constitutional-cms {__version__}")

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    audit_parser = subparsers.add_parser(
        "audit",
        help="Evaluate evidence (or a public URL) against the check catalog and emit a ConformanceReceiptV1",
    )
    audit_parser.add_argument(
        "url",
        nargs="?",
        help="Optional public https:// URL (one read-only GET; unrendered static evidence only).",
    )
    audit_parser.add_argument(
        "--evidence",
        help="Path to a prepared EvidenceBundleV1 (YAML or JSON). Preferred before-publication path.",
    )
    audit_parser.add_argument(
        "--catalog",
        help="Path to a CheckCatalogV1 (defaults to the catalog bundled with this release)",
    )
    audit_parser.add_argument("--as-of", help="RFC 3339 evaluation timestamp (defaults to evidence collected_at)")
    audit_parser.add_argument("--out", help="Write the JSON receipt to this path")
    audit_parser.add_argument("--json", action="store_true", help="Print the full JSON receipt to stdout")
    audit_parser.add_argument(
        "--fail-on",
        help=(
            "Comma-separated verdicts that should exit 1 (e.g. FAIL or FAIL,UNMEASURED). "
            "Default: write the receipt and exit 0."
        ),
    )
    audit_parser.add_argument(
        "--timeout",
        type=float,
        default=collector.DEFAULT_TIMEOUT,
        help=f"Fetch timeout in seconds for URL audits (default: {collector.DEFAULT_TIMEOUT:g})",
    )

    validate_parser = subparsers.add_parser(
        "validate",
        help="Check that the bundled catalog and schemas (and an optional contracts directory) are internally coherent",
    )
    validate_parser.add_argument(
        "path",
        nargs="?",
        default=None,
        help="Optional path to a contracts directory. When omitted, validate the bundled release; also validate ./contracts when present.",
    )
    validate_parser.add_argument(
        "--check",
        choices=contracts_validator.CHECK_CHOICES,
        default="all",
        help="Which local contract family to validate (default: all)",
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
