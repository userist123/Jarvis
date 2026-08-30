"""Read-only reviewer dashboard projection for JARVIS memory governance."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

from .learning_review_filters import build_filtered_queue
from .review_state_store import PersistentReviewStateStore


@dataclass(frozen=True)
class ReviewerDashboard:
    total_cases: int
    by_state: dict[str, int]
    by_risk: dict[str, int]
    promotable: int
    high_risk: int
    decision_pending: int
    top_priority: tuple[dict[str, Any], ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "total_cases": self.total_cases,
            "by_state": dict(self.by_state),
            "by_risk": dict(self.by_risk),
            "promotable": self.promotable,
            "high_risk": self.high_risk,
            "decision_pending": self.decision_pending,
            "top_priority": [dict(item) for item in self.top_priority],
            "read_only": True,
        }


class ReviewerDashboardService:
    """Build a deterministic dashboard projection without mutation capabilities."""

    def __init__(self, learning_store: Any, review_state_store: PersistentReviewStateStore | None = None) -> None:
        self.learning_store = learning_store
        self.review_states = review_state_store or PersistentReviewStateStore()

    def build(self, *, risk: str | None = None, promotable: bool | None = None, min_confidence: float | None = None, as_of: Any = None, known_as_of: Any = None, top_n: int = 10) -> ReviewerDashboard:
        records = self.learning_store.records()
        items = build_filtered_queue(records, risk=risk, promotable=promotable, min_confidence=min_confidence, as_of=as_of, known_as_of=known_as_of)
        states = self.review_states.all()
        by_state: dict[str, int] = {}
        for state in states:
            value = str(state.get("state", "UNKNOWN"))
            by_state[value] = by_state.get(value, 0) + 1
        by_risk: dict[str, int] = {}
        for item in items:
            by_risk[item.risk] = by_risk.get(item.risk, 0) + 1
        top_n = max(0, int(top_n))
        return ReviewerDashboard(
            total_cases=len(items),
            by_state=by_state,
            by_risk=by_risk,
            promotable=sum(1 for item in items if item.promotable),
            high_risk=sum(1 for item in items if item.risk == "high"),
            decision_pending=by_state.get("DECISION_PENDING", 0),
            top_priority=tuple(item.as_dict() for item in items[:top_n]),
        )
