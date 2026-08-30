"""Read-only operational filters for the JARVIS learning review queue."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from .learning_dedup import LearningCase
from .learning_review_queue import LearningReviewItem, LearningReviewQueue
from .temporal_learning import filter_learning_cases


def case_from_record(record: dict[str, Any]) -> LearningCase:
    case = LearningCase(
        case_id=str(record["case_id"]),
        fingerprint=str(record["fingerprint"]),
        goal=str(record.get("goal", "")),
        lesson=str(record.get("lesson", "")),
        risk=str(record.get("risk", "low")),
    )
    observations = record.get("observations") or []
    if observations:
        for observation in observations:
            case.add(observation)
    else:
        case.occurrences = int(record.get("occurrences", 0))
        case.evidence_ids = {str(x) for x in record.get("evidence_ids", []) if x}
        case.execution_ids = {str(x) for x in record.get("execution_ids", []) if x}
        case.statuses = {str(x) for x in record.get("statuses", []) if x}
        case.outcome_counts = {str(k): int(v) for k, v in (record.get("outcome_counts") or {}).items()}
        case.first_observed_at = str(record.get("first_observed_at", ""))
        case.last_observed_at = str(record.get("last_observed_at", ""))
        case.knowledge_times = {str(x) for x in record.get("knowledge_times", []) if x}
    return case


def build_filtered_queue(
    records: list[dict[str, Any]],
    *,
    risk: str | None = None,
    promotable: bool | None = None,
    min_confidence: float | None = None,
    as_of: str | date | datetime | None = None,
    known_as_of: str | date | datetime | None = None,
) -> list[LearningReviewItem]:
    cases = [case_from_record(record) for record in records]
    cases, _ = filter_learning_cases(cases, as_of=as_of, known_as_of=known_as_of)
    items = LearningReviewQueue().build(cases)
    if risk is not None:
        items = [item for item in items if item.risk == risk]
    if promotable is not None:
        items = [item for item in items if item.promotable is promotable]
    if min_confidence is not None:
        if not 0.0 <= min_confidence <= 1.0:
            raise ValueError("min_confidence must be between 0 and 1")
        items = [item for item in items if item.confidence_score >= min_confidence]
    return items
