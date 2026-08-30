"""Adapters that expose learning, conflict and provisional cases uniformly."""

from __future__ import annotations

from typing import Any, Iterable, Mapping

from .unified_case_lifecycle import CaseStatus, UnifiedCase


def from_learning(record: Mapping[str, Any]) -> UnifiedCase:
    return UnifiedCase(
        case_id=str(record.get("case_id") or ""),
        kind="learning",
        route=str(record.get("route") or "LEARNING_REVIEW"),
        status=CaseStatus(str(record.get("status") or "OPEN")),
        source_signal_id=str(record.get("signal_id") or "") or None,
        canonical_case_id=str(record.get("canonical_case_id") or "") or None,
        memory_ids=tuple(str(x) for x in record.get("memory_ids") or [] if str(x)),
        metadata=dict(record.get("metadata") or {}),
    )


def from_conflict(record: Mapping[str, Any]) -> UnifiedCase:
    return UnifiedCase(
        case_id=str(record.get("case_id") or ""),
        kind="conflict",
        route="CONFLICT_REVIEW",
        status=CaseStatus(str((record.get("review_state") or {}).get("state") or record.get("state") or "OPEN")),
        source_signal_id=str(record.get("signal_id") or "") or None,
        canonical_case_id=str(record.get("case_id") or "") or None,
        memory_ids=tuple(str(x) for x in record.get("memory_ids") or [] if str(x)),
        metadata=dict(record.get("metadata") or {}),
    )


def from_memory_case(record: Mapping[str, Any]) -> UnifiedCase:
    kind = str(record.get("kind") or "unknown")
    route = str(record.get("route") or "UNROUTED")
    status_text = str(record.get("status") or "OPEN")
    try:
        status = CaseStatus(status_text)
    except ValueError:
        status = CaseStatus.OPEN
    return UnifiedCase(
        case_id=str(record.get("case_id") or ""),
        kind=kind,
        route=route,
        status=status,
        source_signal_id=str(record.get("signal_id") or "") or None,
        canonical_case_id=str(record.get("canonical_case_id") or "") or None,
        memory_ids=tuple(str(x) for x in record.get("memory_ids") or [] if str(x)),
        metadata=dict(record.get("metadata") or {}),
    )


def merge_cases(*groups: Iterable[UnifiedCase]) -> list[UnifiedCase]:
    merged: dict[str, UnifiedCase] = {}
    for group in groups:
        for case in group:
            if case.case_id:
                merged[case.case_id] = case
    return [merged[key] for key in sorted(merged)]
