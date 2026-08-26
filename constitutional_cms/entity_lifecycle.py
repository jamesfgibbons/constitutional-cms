"""Detect authority collapse: one truth domain revoking another.

Not a CheckCatalogV1 check. Companion to snapshot_boundary and CONSUMING_LAYER.
"""

from __future__ import annotations

from typing import Any

UNAVAILABLE_CLAIM = {"unavailable", "unmeasured", "withheld", "stale"}
NON_TERMINAL = {
    "active",
    "seasonal_active",
    "seasonal_inactive",
    "launching",
    "suspended",
    "unknown",
}


def _lifecycle(projection: dict[str, Any]) -> dict[str, Any]:
    entity = projection.get("entity") or {}
    return entity.get("lifecycle") or {}


def evaluate_projection(projection: dict[str, Any]) -> list[dict[str, str]]:
    """Return invariant violations. Empty list means no detected collapse."""
    if not isinstance(projection, dict):
        return [
            {
                "invariant_id": "identity_is_not_evidence",
                "collapse_id": "malformed_projection",
                "detail": "projection must be an object",
            }
        ]

    violations: list[dict[str, str]] = []
    life = _lifecycle(projection)
    state = str(life.get("state") or "")
    terminal = bool(life.get("terminal"))
    artifact = projection.get("artifact") or {}
    http = artifact.get("http_status")
    claims = projection.get("claims") or {}
    relationships = projection.get("relationships") or {}
    derived_by = str(life.get("derived_by") or artifact.get("lifecycle_derived_by") or "")

    claim_states = []
    if isinstance(claims, dict):
        for rec in claims.values():
            if isinstance(rec, dict):
                claim_states.append(str(rec.get("state") or ""))

    rel_states = []
    if isinstance(relationships, dict):
        for rec in relationships.values():
            if isinstance(rec, dict):
                rel_states.append(str(rec.get("state") or ""))

    any_claim_gap = any(s in UNAVAILABLE_CLAIM for s in claim_states)
    child_404 = any(
        isinstance(rec, dict) and rec.get("child_http_status") in (404, 410)
        for rec in (claims.values() if isinstance(claims, dict) else [])
    )

    if http == 410 and not terminal:
        violations.append(
            {
                "invariant_id": "gone_requires_terminal_authority",
                "collapse_id": "410_without_terminal",
                "detail": "HTTP 410 requires lifecycle.terminal true and a named authority",
            }
        )

    if http == 410 and terminal:
        if not life.get("authority"):
            violations.append(
                {
                    "invariant_id": "gone_requires_terminal_authority",
                    "collapse_id": "410_without_authority",
                    "detail": "HTTP 410 requires an explicit lifecycle authority",
                }
            )
        if not life.get("transition_receipt_id"):
            violations.append(
                {
                    "invariant_id": "lifecycle_transition_produces_receipt",
                    "collapse_id": "terminal_without_receipt",
                    "detail": "Every terminal transition requires a transition_receipt_id",
                }
            )

    if any_claim_gap and (terminal or http == 410) and not life.get("authority"):
        violations.append(
            {
                "invariant_id": "entity_state_is_not_claim_state",
                "collapse_id": "claim_absence_to_entity_absence",
                "detail": "A withheld, stale, unavailable, or unmeasured claim must not retire the subject",
            }
        )

    seasonal_marker = "seasonal_inactive" in rel_states or state == "seasonal_inactive"
    explicit = life.get("reason_code") == "explicit_retirement" and bool(life.get("authority"))
    if seasonal_marker and (http == 410 or (state == "retired" and terminal)) and not explicit:
        violations.append(
            {
                "invariant_id": "seasonal_inactive_is_not_retired",
                "collapse_id": "seasonal_inactive_to_retired",
                "detail": "Seasonal inactive is not retired",
            }
        )

    if any(s in {"seasonal_inactive", "suspended"} for s in rel_states) and (
        http == 410 and not terminal
    ):
        violations.append(
            {
                "invariant_id": "relationship_state_is_not_entity_state",
                "collapse_id": "relationship_inactive_to_entity_gone",
                "detail": "An inactive relationship must not delete the parent entity",
            }
        )

    if state == "unknown" and http in (404, 410):
        violations.append(
            {
                "invariant_id": "unknown_is_not_absent",
                "collapse_id": "unknown_to_absent",
                "detail": "Unknown must not collapse into 404 or 410",
            }
        )

    if http == 404 and terminal:
        violations.append(
            {
                "invariant_id": "absent_is_not_terminal",
                "collapse_id": "404_marked_terminal",
                "detail": "404 is absence of a representation, not a terminal verdict (use 410 only with authority)",
            }
        )

    if child_404 and http == 410:
        violations.append(
            {
                "invariant_id": "child_cannot_escalate_parent_terminal",
                "collapse_id": "child_404_to_parent_410",
                "detail": "A child evidence 404/410 must not escalate the parent artifact to 410",
            }
        )

    if derived_by.lower() in {"renderer", "ssr", "template", "frontend"}:
        violations.append(
            {
                "invariant_id": "renderer_cannot_derive_lifecycle",
                "collapse_id": "renderer_derived_lifecycle",
                "detail": "Lifecycle state must come from lifecycle authority, not the renderer",
            }
        )

    if http == 410 and any_claim_gap and not terminal:
        # already covered by 410_without_terminal; keep identity rule loud
        violations.append(
            {
                "invariant_id": "identity_is_not_evidence",
                "collapse_id": "missing_evidence_deletes_entity",
                "detail": "Missing evidence does not delete an entity",
            }
        )

    # Deduplicate by collapse_id
    seen: set[str] = set()
    unique: list[dict[str, str]] = []
    for row in violations:
        key = row["collapse_id"]
        if key in seen:
            continue
        seen.add(key)
        unique.append(row)
    return unique
