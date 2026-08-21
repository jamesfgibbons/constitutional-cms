#!/usr/bin/env python3
"""CLI for Constitutional CMS."""

import argparse
import sys
from pathlib import Path


def audit_command(args):
    """Run conformance audit and produce a ConformanceReceiptV1."""
    # Import the evaluator module
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from scripts import conformance_evaluator
    
    try:
        receipt = conformance_evaluator.evaluate(
            conformance_evaluator.load_data(Path(args.catalog)),
            conformance_evaluator.load_data(Path(args.evidence)),
            args.as_of
        )
    except (KeyError, TypeError, ValueError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    
    import json
    payload = json.dumps(receipt, indent=2, sort_keys=True) + "\n"
    if args.out:
        Path(args.out).write_text(payload, encoding="utf-8")
    else:
        print(payload, end="")
    return 0


def validate_command(args):
    """Run contract validation checks."""
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from scripts import validate_contracts, validate_web_conformance
    
    print("Running contract validation...")
    result = validate_contracts.main()
    if result != 0:
        return result
    
    print("\nRunning web conformance validation...")
    result = validate_web_conformance.main()
    return result


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="constitutional-cms",
        description="Constitutional CMS - A governance framework for AI agents that build websites"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # audit command
    audit_parser = subparsers.add_parser(
        "audit",
        help="Evaluate evidence against conformance catalog and produce a receipt"
    )
    audit_parser.add_argument(
        "--catalog",
        default="contracts/check_catalog_v1.yaml",
        help="Path to check catalog (default: contracts/check_catalog_v1.yaml)"
    )
    audit_parser.add_argument(
        "--evidence",
        required=True,
        help="Path to evidence bundle (required)"
    )
    audit_parser.add_argument(
        "--as-of",
        help="RFC 3339 evaluation timestamp (defaults to evidence collected_at)"
    )
    audit_parser.add_argument(
        "--out",
        help="Output path for JSON receipt (prints to stdout if not specified)"
    )
    
    # validate command
    validate_parser = subparsers.add_parser(
        "validate",
        help="Validate contract consistency and web conformance schemas"
    )
    validate_parser.add_argument(
        "--contracts-dir",
        default="./contracts",
        help="Path to contracts directory (default: ./contracts)"
    )
    validate_parser.add_argument(
        "--check",
        choices=[
            'syntax', 'page_types', 'enrichment', 'links', 'boundary',
            'page_health', 'cache', 'claims', 'proof_ledger',
            'signal_projection', 'sensor_integrity', 'agent_envelope',
            'web_conformance', 'all'
        ],
        default='all',
        help='Which contract to validate (default: all)'
    )
    
    args = parser.parse_args()
    
    if args.command is None:
        parser.print_help()
        return 1
    
    if args.command == "audit":
        return audit_command(args)
    elif args.command == "validate":
        # Update sys.argv for validate_contracts/validate_web_conformance
        # which use argparse themselves
        sys.argv = ["validate_contracts.py", "--contracts-dir", args.contracts_dir]
        if args.check != "all":
            sys.argv.extend(["--check", args.check])
        return validate_command(args)
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
