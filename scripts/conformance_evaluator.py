#!/usr/bin/env python3
"""Evaluate a normalized EvidenceBundleV1 against CheckCatalogV1.

The evaluator performs no network access. Private implementations remain private by
mapping their authorities into the public evidence shapes before invoking it.

This script is a thin re-export of :mod:`constitutional_cms.evaluator`, which is the
packaged home of the reference evaluator (schemas and the default catalog ship as
package data so installed environments need no repository checkout). Running it from
a checkout keeps the documented script path working unchanged.
"""

import sys
from pathlib import Path

_REPO_ROOT = str(Path(__file__).resolve().parents[1])
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from constitutional_cms.evaluator import (  # noqa: E402,F401
    EVALUATOR_VERSION,
    MISSING,
    REASON_CODES,
    canonical_json,
    canonical_value,
    digest,
    evaluate,
    evaluate_rule,
    evidence_problem,
    first_problem,
    is_https_url,
    load_data,
    load_default_catalog,
    load_schema,
    main,
    normalize_timestamp,
    origin_for,
    parse_timestamp,
    validate_instance,
    validate_link_graph,
    value_at,
)

if __name__ == "__main__":
    raise SystemExit(main())
