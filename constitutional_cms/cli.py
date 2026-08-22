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


def _read_json(path: str, label: str) -> dict[str, Any]:
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"could not read {label} from {path}: {error}") from error


def _write_json(document: dict[str, Any], out: str | None) -> None:
    payload = json.dumps(document, indent=2, sort_keys=True) + "\n"
    if out:
        Path(out).write_text(payload, encoding="utf-8")
    else:
        print(payload, end="")


def claim_bundle_command(args: argparse.Namespace) -> int:
    """Build an UNSIGNED ClaimBundle core from evidence. Exit 0 built, 2 error."""
    from . import claims

    try:
        catalog = _load_catalog(args.catalog)
        evidence = evaluator.load_data(Path(args.evidence))
        bundle = claims.build_bundle(
            evidence,
            catalog,
            issuer=args.issuer,
            generation_digest=args.generation_digest,
            default_claim_ttl_seconds=(
                args.default_claim_ttl
                if args.default_claim_ttl is not None
                else claims.DEFAULT_CLAIM_TTL_SECONDS
            ),
        )
    except (OSError, KeyError, TypeError, ValueError) as error:
        print(f"claim-bundle: {error}", file=sys.stderr)
        return EXIT_ERROR
    _write_json(bundle, args.out)
    return EXIT_OK


def claim_sign_command(args: argparse.Namespace) -> int:
    """Freeze a bundle core: bundle_hash + Ed25519 signature. Exit 0 signed, 2 error.

    The private key is read from --key (a file path) or the
    CONSTITUTIONAL_CMS_CLAIM_KEY environment variable (also a path).
    Key material is never printed.
    """
    from . import claims

    try:
        bundle = _read_json(args.bundle, "bundle")
        signed = claims.sign_bundle(bundle, key_id=args.key_id, key_path=args.key)
    except (KeyError, TypeError, ValueError) as error:
        print(f"claim-sign: {error}", file=sys.stderr)
        return EXIT_ERROR
    _write_json(signed, args.out)
    return EXIT_OK


def claim_verify_command(args: argparse.Namespace) -> int:
    """Verify a signed bundle (or a receipt) fully offline.

    Exit codes: 0 verified · 1 refused (typed reason on stderr) · 2 operational error.
    No account, no network: verification needs only the artifact and a local keys file.
    """
    from . import claims

    try:
        if args.receipt:
            receipt = _read_json(args.receipt, "receipt")
            bundle = _read_json(args.bundle, "bundle") if args.bundle else None
            result = claims.verify_receipt(
                receipt, bundle, current=not args.historical, as_of=args.as_of
            )
        else:
            if not args.bundle:
                print("claim-verify: provide --bundle (and --keys), or --receipt.", file=sys.stderr)
                return EXIT_ERROR
            if not args.keys:
                print("claim-verify: bundle verification requires --keys <keys.json>.", file=sys.stderr)
                return EXIT_ERROR
            bundle = _read_json(args.bundle, "bundle")
            result = claims.verify_bundle(
                bundle,
                args.keys,
                as_of=args.as_of,
                horizon_seconds=(
                    args.horizon_seconds
                    if args.horizon_seconds is not None
                    else claims.DEFAULT_RECEIPT_HORIZON_SECONDS
                ),
            )
            if result.receipt is not None and (args.receipt_out or args.json):
                _write_json(result.receipt, args.receipt_out)
    except (KeyError, TypeError, ValueError) as error:
        print(f"claim-verify: {error}", file=sys.stderr)
        return EXIT_ERROR

    if result.ok:
        print(f"VERIFIED · {result.verdict} · {', '.join(result.reason_codes)}")
        return EXIT_OK
    print(
        f"REFUSED · {result.verdict} · {', '.join(result.reason_codes)} · {result.detail}",
        file=sys.stderr,
    )
    return EXIT_FAIL


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

    bundle_parser = subparsers.add_parser(
        "claim-bundle",
        help="Build an UNSIGNED ClaimBundleV0_1 core from an EvidenceBundleV1 (sign it with claim-sign)",
    )
    bundle_parser.add_argument("--evidence", required=True, help="Path to a prepared EvidenceBundleV1 (YAML or JSON)")
    bundle_parser.add_argument("--catalog", help="Path to a CheckCatalogV1 (defaults to the bundled catalog)")
    bundle_parser.add_argument("--issuer", required=True, help="Issuer domain (e.g. example.com); keys are discovered under it")
    bundle_parser.add_argument("--generation-digest", help="Optional sha256:<hex> digest binding the bundle to a generation run")
    bundle_parser.add_argument(
        "--default-claim-ttl",
        type=int,
        default=None,
        help="Claim TTL in seconds when the catalog declares no max_age (default: 604800)",
    )
    bundle_parser.add_argument("--out", help="Write the bundle core to this path (default: stdout)")

    sign_parser = subparsers.add_parser(
        "claim-sign",
        help="Freeze a bundle core: compute bundle_hash and attach the Ed25519 signature",
    )
    sign_parser.add_argument("--bundle", required=True, help="Path to the unsigned bundle core (JSON)")
    sign_parser.add_argument(
        "--key",
        help="Path to the Ed25519 private key PEM (or set CONSTITUTIONAL_CMS_CLAIM_KEY to a path). Never printed.",
    )
    sign_parser.add_argument("--key-id", required=True, help="key_id the verifier will look up in the keys document")
    sign_parser.add_argument("--out", help="Write the signed bundle to this path (default: stdout)")

    verify_parser = subparsers.add_parser(
        "claim-verify",
        help="Verify a signed ClaimBundle (or a ClaimReceipt) fully offline. Exit 0 verified, 1 refused, 2 error.",
    )
    verify_parser.add_argument("--bundle", help="Path to a signed ClaimBundleV0_1 (JSON)")
    verify_parser.add_argument("--keys", help="Path to a local keys.json (the /.well-known/constitutional-cms/keys.json shape)")
    verify_parser.add_argument("--receipt", help="Verify this ClaimReceiptV0_1 instead (optionally against --bundle)")
    verify_parser.add_argument("--historical", action="store_true", help="Receipt mode: ask the historical question (supersession and expiry allowed)")
    verify_parser.add_argument("--as-of", help="RFC 3339 verification clock (defaults to now, UTC)")
    verify_parser.add_argument(
        "--horizon-seconds",
        type=int,
        default=None,
        help="Verification policy horizon for receipt expiry (default: 604800)",
    )
    verify_parser.add_argument("--receipt-out", help="Write the emitted ClaimReceipt to this path")
    verify_parser.add_argument("--json", action="store_true", help="Print the emitted ClaimReceipt to stdout")

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
    if args.command == "claim-bundle":
        return claim_bundle_command(args)
    if args.command == "claim-sign":
        return claim_sign_command(args)
    if args.command == "claim-verify":
        return claim_verify_command(args)
    if args.command == "validate":
        return validate_command(args)
    parser.print_help()
    return EXIT_ERROR


if __name__ == "__main__":
    sys.exit(main())
