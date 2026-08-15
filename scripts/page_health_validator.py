#!/usr/bin/env python3
"""
Observe-only page health validator.

This script turns crawl, render, or audit rows into a small P0/P1/P2/P3 report.
It is intentionally domain-neutral: callers map their own crawler output into the
column names used here before running the validator.
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable


TRUE_VALUES = {"1", "true", "yes", "y", "on"}
FALSE_VALUES = {"0", "false", "no", "n", "off", ""}


@dataclass(frozen=True)
class Finding:
    severity: str
    code: str
    url: str
    message: str


@dataclass(frozen=True)
class Unmeasured:
    probe_id: str
    url: str
    missing_fields: tuple[str, ...]
    message: str


def parse_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    normalized = str(value or "").strip().lower()
    if normalized in TRUE_VALUES:
        return True
    if normalized in FALSE_VALUES:
        return False
    return False


def parse_int(value: object, default: int = 0) -> int:
    try:
        return int(str(value or "").strip())
    except ValueError:
        return default


def read_rows(paths: Iterable[Path]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for path in paths:
        with path.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                row["_source_file"] = str(path)
                rows.append(row)
    return rows


def missing_materialization_fields(row: dict[str, str]) -> list[str]:
    required = [
        "rendered_at",
        "build_id",
        "deploy_id",
        "content_hash",
        "template_family",
    ]
    return [field for field in required if not str(row.get(field, "")).strip()]


def analyze_rows(rows: Iterable[dict[str, str]]) -> list[Finding]:
    findings: list[Finding] = []

    for row in rows:
        url = row.get("url") or row.get("page_url") or "(unknown URL)"
        status = parse_int(row.get("status") or row.get("http_status"))
        quality_tier = str(row.get("quality_tier") or row.get("tier") or "").upper()
        indexable = parse_bool(row.get("indexable") or row.get("seo_indexable"))
        sitemap_eligible = parse_bool(row.get("sitemap_eligible"))
        noindex = parse_bool(row.get("noindex") or row.get("rendered_noindex"))
        visible_claim = parse_bool(row.get("visible_claim"))
        claim_publishable = parse_bool(row.get("claim_publishable"))
        suppression_visible = parse_bool(row.get("suppression_visible"))
        materialized = parse_bool(row.get("materialized"))
        fallback_served = parse_bool(row.get("fallback_served"))
        internal_link_status = parse_int(row.get("internal_link_status"))
        viewport_width = parse_int(row.get("viewport_width"))
        layout_mode = str(row.get("layout_mode") or row.get("table_layout") or "").lower()

        if quality_tier == "SUPPRESS" and sitemap_eligible:
            findings.append(
                Finding(
                    "P0",
                    "suppressed_url_in_sitemap",
                    url,
                    "Suppressed URLs must not appear in sitemap or discovery surfaces.",
                )
            )

        if sitemap_eligible and (status >= 400 or noindex):
            findings.append(
                Finding(
                    "P0",
                    "sitemap_disagrees_with_rendered_truth",
                    url,
                    "Sitemap-eligible URLs must render successfully without noindex.",
                )
            )

        if indexable and status >= 500:
            findings.append(
                Finding(
                    "P0",
                    "indexable_url_returns_server_error",
                    url,
                    "Indexable URLs must not return server errors.",
                )
            )

        if visible_claim and not claim_publishable and not suppression_visible:
            findings.append(
                Finding(
                    "P0",
                    "visible_claim_without_validated_source",
                    url,
                    "Visible public claims require a validated source or visible suppression language.",
                )
            )

        if materialized:
            missing = missing_materialization_fields(row)
            if missing:
                findings.append(
                    Finding(
                        "P0",
                        "materialized_artifact_missing_metadata",
                        url,
                        "Materialized artifacts are missing required metadata: "
                        + ", ".join(missing),
                    )
                )

        if fallback_served and materialized:
            findings.append(
                Finding(
                    "P0",
                    "fallback_written_as_materialized",
                    url,
                    "Fallback output must not be treated as validated materialized output.",
                )
            )

        if internal_link_status >= 400:
            findings.append(
                Finding(
                    "P0",
                    "internal_link_to_non_200",
                    url,
                    "Internal links must not target failed public URLs.",
                )
            )

        if viewport_width and viewport_width <= 480 and layout_mode == "table":
            findings.append(
                Finding(
                    "P2",
                    "mobile_table_requires_card_layout",
                    url,
                    "Table-like surfaces should become cards, grids, or blocks on narrow viewports.",
                )
            )

    return findings


def analyze_unmeasured(rows: Iterable[dict[str, str]]) -> list[Unmeasured]:
    """Name probe questions that cannot be answered from the supplied columns."""
    probe_fields = {
        "page_and_sitemap_state": ("status", "quality_tier", "sitemap_eligible", "noindex"),
        "indexability_state": ("status", "indexable"),
        "claim_integrity": ("visible_claim", "claim_publishable", "suppression_visible"),
        "materialization_state": ("materialized",),
        "fallback_state": ("fallback_served", "materialized"),
        "internal_link_state": ("internal_link_status",),
        "mobile_layout_state": ("viewport_width", "layout_mode"),
    }
    gaps: list[Unmeasured] = []
    for row in rows:
        url = row.get("url") or row.get("page_url") or "(unknown URL)"
        for probe_id, fields in probe_fields.items():
            missing = tuple(field for field in fields if not str(row.get(field, "")).strip())
            if missing:
                gaps.append(
                    Unmeasured(
                        probe_id,
                        url,
                        missing,
                        "Required probe inputs were not supplied; no pass state may be inferred.",
                    )
                )
        if parse_bool(row.get("materialized")):
            missing = tuple(missing_materialization_fields(row))
            if missing:
                gaps.append(
                    Unmeasured(
                        "materialization_identity",
                        url,
                        missing,
                        "Materialized identity cannot be fully measured from the supplied row.",
                    )
                )
    return gaps


def summarize(
    findings: Iterable[Finding], unmeasured: Iterable[Unmeasured] = ()
) -> dict[str, object]:
    finding_list = list(findings)
    unmeasured_list = list(unmeasured)
    counts = Counter(finding.severity for finding in finding_list)
    state = "FAIL" if finding_list else "UNMEASURED" if unmeasured_list else "PASS"
    return {
        "measurement_state": state,
        "total_findings": len(finding_list),
        "total_unmeasured": len(unmeasured_list),
        "counts": {severity: counts.get(severity, 0) for severity in ["P0", "P1", "P2", "P3"]},
        "findings": [asdict(finding) for finding in finding_list],
        "unmeasured": [asdict(gap) for gap in unmeasured_list],
    }


def write_markdown(summary: dict[str, object], path: Path) -> None:
    counts = summary["counts"]
    findings = summary["findings"]
    unmeasured = summary["unmeasured"]
    lines = [
        "# Page Health Validator Report",
        "",
        "Observe-only report. Finding counts are evidence for review, not an automatic deploy block.",
        f"Measurement state: **{summary['measurement_state']}**",
        "",
        "| Severity | Count |",
        "| --- | ---: |",
    ]
    for severity in ["P0", "P1", "P2", "P3"]:
        lines.append(f"| {severity} | {counts[severity]} |")
    lines.append("")
    lines.append("## Findings")
    lines.append("")
    if not findings:
        lines.append("No findings.")
    else:
        for finding in findings:
            lines.append(
                f"- **{finding['severity']} {finding['code']}** `{finding['url']}` - {finding['message']}"
            )
    lines.append("")
    lines.append("## Unmeasured probe questions")
    lines.append("")
    if not unmeasured:
        lines.append("None. All declared probe inputs were supplied.")
    else:
        for gap in unmeasured:
            missing = ", ".join(gap["missing_fields"])
            lines.append(
                f"- **UNMEASURED {gap['probe_id']}** `{gap['url']}` - missing: {missing}."
            )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Observe-only Constitutional CMS page health validator")
    parser.add_argument("--input", action="append", required=True, help="CSV audit/crawl input. May be repeated.")
    parser.add_argument("--out-dir", default="reports/page-health-validator", help="Report output directory")
    args = parser.parse_args()

    input_paths = [Path(value) for value in args.input]
    rows = read_rows(input_paths)
    findings = analyze_rows(rows)
    unmeasured = analyze_unmeasured(rows)
    report = summarize(findings, unmeasured)

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "latest.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    write_markdown(report, out_dir / "latest.md")

    print(
        "[page_health_validator] "
        f"rows={len(rows)} state={report['measurement_state']} "
        f"findings={report['total_findings']} unmeasured={report['total_unmeasured']} out_dir={out_dir}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
