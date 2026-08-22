#!/usr/bin/env python3
"""
Constitutional CMS Contract Validator

Validates that contract YAML files are internally consistent.
Does NOT validate live site compliance — that's your eval harness.
This validates the contracts themselves.

This script is a thin re-export of :mod:`constitutional_cms.contracts_validator`,
the packaged home of the validator (also exposed as ``constitutional-cms validate``).

Usage:
    python scripts/validate_contracts.py
    python scripts/validate_contracts.py --contracts-dir ./contracts
    python scripts/validate_contracts.py --check page_types
    python scripts/validate_contracts.py --check links
    python scripts/validate_contracts.py --check enrichment
    python scripts/validate_contracts.py --check boundary
"""

import sys
from pathlib import Path

_REPO_ROOT = str(Path(__file__).resolve().parents[1])
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from constitutional_cms.contracts_validator import (  # noqa: E402,F401
    CHECK_CHOICES,
    load_yaml,
    main,
    run,
    run_packaged,
    validate_packaged_release,
    validate_agent_operating_envelope,
    validate_cache_materialization,
    validate_claim_decision,
    validate_enrichment_stages,
    validate_link_rules,
    validate_page_health_resolver,
    validate_page_types,
    validate_proof_ledger,
    validate_sensor_integrity,
    validate_signal_projection,
    validate_snapshot_boundary,
    validate_web_conformance,
    validate_yaml_syntax,
)

if __name__ == "__main__":
    sys.exit(main())
