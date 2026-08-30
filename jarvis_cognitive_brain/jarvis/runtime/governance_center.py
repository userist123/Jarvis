"""Unified read-only governance center projection."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .learning_review_dashboard import ReviewerDashboardService
from .learning_review_filters import build_filtered_queue
from .learning_store import PersistentLearningStore
from .memory_intelligence_store import MemoryIntelligenceStore
from .memory_intelligence_triage_service import MemoryIntelligenceTriageService
from .review_state_store import PersistentReviewStateStore


@dataclass(frozen=True)
class GovernanceCenter:
    identity: dict[str, Any]
    learning: dict[str, Any]
    conflicts: dict[str, Any]
    intelligence: dict[str, Any]
    pending_actions: tuple[dict[str, Any], ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "identity": dict(self.identity),
            "learning": dict(self.learning),
            "conflicts": dict(self.conflicts),
            "intelligence": dict(self.intelligence),
            "pending_actions": [dict(x) for x in self.pending_actions],
            "read_only": True,
        }


class GovernanceCenterService:
    """Build a unified, read-only view over learning, conflicts and memory intelligence."""

    def __init__(self, learning_store: PersistentLearningStore, review_states: PersistentReviewStateStore, intelligence_store: MemoryIntelligenceStore | None = None):
        self.learning_store = learning_store
        self.review_states = review_states
        self.learning_dashboard = ReviewerDashboardService(learning_store, review_states)
        self.intelligence = MemoryIntelligenceTriageService(intelligence_store or MemoryIntelligenceStore())

    def build(self, *, identity: dict[str, Any], risk: str | None = None, min_confidence: float | None = None, top_n: int = 10) -> GovernanceCenter:
        learning = self.learning_dashboard.build(risk=risk, min_confidence=min_confidence, top_n=top_n).as_dict()
        learning_items = build_filtered_queue(
            self.learning_store.records(),
            risk=risk,
            min_confidence=min_confidence,
        )

        states = self.review_states.all()
        conflicts_by_state: dict[str, int] = {}
        pending: list[dict[str, Any]] = []
        for state in states:
            value = str(state.get("state", "UNKNOWN"))
            conflicts_by_state[value] = conflicts_by_state.get(value, 0) + 1
            if value in {"EVIDENCE_PENDING", "VERIFIED", "DECISION_PENDING"}:
                pending.append({
                    "kind": "conflict",
                    "case_id": str(state.get("case_id", "")),
                    "state": value,
                    "can_apply_mutation": bool(state.get("can_apply_mutation", False)),
                })

        for item in learning_items[: max(0, int(top_n))]:
            pending.append({
                "kind": "learning",
                "case_id": str(item.case_id),
                "state": "REVIEW",
                "can_apply_mutation": False,
                "confidence": item.confidence_score,
                "risk": item.risk,
                "promotable": item.promotable,
            })

        intelligence = self.intelligence.summary()
        pending.sort(key=lambda item: (item["kind"], item["state"], item["case_id"]))
        return GovernanceCenter(
            identity=identity,
            learning=learning,
            conflicts={"total_cases": len(states), "by_state": conflicts_by_state},
            intelligence=intelligence,
            pending_actions=tuple(pending),
        )
