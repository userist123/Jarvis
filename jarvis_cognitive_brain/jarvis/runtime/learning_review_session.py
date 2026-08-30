"""Read-only review dossier assembly for a persistent JARVIS learning case."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from .learning_confidence_snapshot import ConfidenceSnapshot, build_confidence_snapshot
from .learning_dedup import LearningCase
from .learning_review_queue import build_review_item
from .learning_store import PersistentLearningStore
from .temporal_learning import snapshot_case


@dataclass(frozen=True)
class LearningReviewSession:
    case: dict[str, Any]
    review_item: dict[str, Any]
    confidence_snapshot: dict[str, Any]
    temporal: dict[str, Any]
    evidence_ids: tuple[str, ...]
    proposed_actions: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "case": self.case,
            "review_item": self.review_item,
            "confidence_snapshot": self.confidence_snapshot,
            "temporal": self.temporal,
            "evidence_ids": list(self.evidence_ids),
            "proposed_actions": list(self.proposed_actions),
            "read_only": True,
        }


class LearningReviewSessionService:
    """Assemble a complete, read-only review dossier from persistent learning state."""

    def __init__(self, store: PersistentLearningStore):
        self.store = store

    @staticmethod
    def _case_from_record(record: Mapping[str, Any]) -> LearningCase:
        case = LearningCase(
            case_id=str(record["case_id"]),
            fingerprint=str(record["fingerprint"]),
            goal=str(record.get("goal", "")),
            lesson=str(record.get("lesson", "")),
            risk=str(record.get("risk", "low")),
        )
        for observation in record.get("observations") or []:
            case.add(observation)
        if not case.observations:
            case.occurrences = int(record.get("occurrences", 0))
            case.evidence_ids = {str(x) for x in record.get("evidence_ids", []) if x}
            case.execution_ids = {str(x) for x in record.get("execution_ids", []) if x}
            case.statuses = {str(x) for x in record.get("statuses", []) if x}
            case.outcome_counts = {str(k): int(v) for k, v in (record.get("outcome_counts") or {}).items()}
            case.first_observed_at = str(record.get("first_observed_at", ""))
            case.last_observed_at = str(record.get("last_observed_at", ""))
            case.knowledge_times = {str(x) for x in record.get("knowledge_times", []) if x}
        return case

    def open(
        self,
        case_id: str,
        *,
        as_of: str | None = None,
        known_as_of: str | None = None,
    ) -> LearningReviewSession:
        record = next((item for item in self.store.records() if str(item.get("case_id")) == case_id), None)
        if record is None:
            raise KeyError(f"Learning case not found: {case_id}")
        case = self._case_from_record(record)
        snap = snapshot_case(case, as_of=as_of, known_as_of=known_as_of)
        if snap is None:
            raise ValueError("Learning case has no observations visible in requested snapshot")
        confidence = build_confidence_snapshot(snap, as_of=as_of, known_as_of=known_as_of)
        review_item = build_review_item(snap, confidence.confidence)
        actions = ("OPEN_REVIEW",)
        if confidence.confidence.promotable:
            actions += ("REQUEST_AUTHORIZED_PROMOTION",)
        else:
            actions += ("COLLECT_MORE_EVIDENCE", "DEFER")
        temporal = {
            "as_of": confidence.as_of,
            "known_as_of": confidence.known_as_of,
            "first_observed_at": snap.first_observed_at,
            "last_observed_at": snap.last_observed_at,
            "visible_observations": len(snap.observations),
        }
        return LearningReviewSession(
            case=snap.as_dict(),
            review_item=review_item.as_dict(),
            confidence_snapshot=confidence.as_dict(),
            temporal=temporal,
            evidence_ids=tuple(sorted(snap.evidence_ids)),
            proposed_actions=actions,
        )
