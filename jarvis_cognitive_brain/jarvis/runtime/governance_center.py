"""Unified read-only governance center projection."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .learning_review_dashboard import ReviewerDashboardService
from .learning_review_filters import build_filtered_queue
from .learning_store import PersistentLearningStore
from .review_state_store import PersistentReviewStateStore


@dataclass(frozen=True)
class GovernanceCenter:
    identity: dict[str, Any]
    learning: dict[str, Any]
    conflicts: dict[str, Any]
    pending_actions: tuple[dict[str, Any], ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "identity": dict(self.identity),
            "learning": dict(self.learning),
            "conflicts": dict(self.conflicts),
            "pending_actions": [dict(x) for x in self.pending_actions],
            "read_only": True,
        }


class GovernanceCenterService:
    """Build a unified, read-only view over learning and conflict governance."""

    def __init__(self, learning_store: PersistentLearningStore, review_states: PersistentReviewStateStore):
        self.learning_store = learning_store
        self.review_states = review_states
        self.learning_dashboard = ReviewerDashboardService(learning_store, review_states)

    def build(self, *, identity: dict[str, Any], risk: str | None = None, min_confidence: float | None = None, top_n: int = 10) -> GovernanceCenter:
        learning = self.learning_dashboard.build(risk=risk, min_confidence=min_confidence, top_n=top_n).as_dict()
        states = self.review_states.all()
        conflicts_by_state: dict[str, int] = {}
        pending: list[dict[str, Any]] = []
        for state in states:
            value = str(state.get("state", "UNKNOWN"))
            conflicts_by_state[value] = conflicts_by_state.get(value, 0) + 1
            if value in {"EVIDENCE_PENDING", "VERIFIED", "DECISION_PENDING"}:
                pending.append({
                    "case_id": str(state.get("case_id", "")),
                    "state": value,
                    "can_apply_mutation": bool(state.get("can_apply_mutation", False)),
                })
        pending.sort(key=lambda item: (item["state"], item["case_id"]))
        return GovernanceCenter(
            identity=identity,
            learning=learning,
            conflicts={"total_cases": len(states), "by_state": conflicts_by_state},
            pending_actions=tuple(pending),
        )
